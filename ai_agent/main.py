import os
import httpx
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, BackgroundTasks
from psycopg_pool import AsyncConnectionPool

from .graph import LangGraphOrchestrator
from .agent_state import AgentState

DB_URI = os.getenv("DATABASE_URL")
db_pool = AsyncConnectionPool(DB_URI, max_size=20)

orchestrator = LangGraphOrchestrator()

@asynccontextmanager
async def lifespan(app: FastAPI):
    await db_pool.open()
    await orchestrator.compile_graph(db_pool)
    yield
    await orchestrator.mcp_client.cleanup()
    await db_pool.close()
app = FastAPI(lifespan = lifespan)

class AgentController:
    """HTTP Controller exposing the webhook for the API Gateway"""
    @staticmethod
    @app.post("/webhook/ai_agent")
    async def recieve_webhook(request: Request, background_tasks: BackgroundTasks):
        """Receives internal webhook from the API Gateway."""
        payload = await request.json()
        session_id = payload.get("session_id")
        text = payload.get("text")
        background_tasks.add_task(AgentController.process_message, session_id, text)
        return {"status": "processing"}
    
    @staticmethod
    async def process_message(session_id: str, text: str):
        """Invokes the LangGraph orchestrator with the new message."""
        input_state = {
            "messages" : [("user", text)],
            "active_session_id": session_id
        }
        config = {"configurable": {"thread_id": session_id}}
        result = await orchestrator.invoke_agent(input_state, config)
        if result.get("requires_handoff"):
            print(f"Session {session_id} has been handed off to Kafka. AI sleeping.")
            return
        ai_reply = result["messages"][-1].content
        print(f"AI Response to {session_id}: {ai_reply}")
        await AgentController.send_whatsapp_message(phone_number=session_id, text=ai_reply)

    @staticmethod
    async def send_whatsapp_message(phone_number: str, text: str):
        """Fires as HTTP Post request to the Meta graph API"""
        whatsapp_token = os.getenv("WHATSAPP_ACCESS_TOKEN")
        phone_number_id = os.getenv("WHATSAPP_PHONE_ID")
        url = f"https://graph.facebook.com/v17.0/{phone_number_id}/messages"
        
        headers = {
            "Authorization": f"Bearer {whatsapp_token}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "messaging_product": "whatsapp",
            "to": phone_number,
            "type": "text",
            "text": {"body": text}
        }
        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(url, headers=headers, json=payload)
                response.raise_for_status()
            except httpx.HTTPStatusError as e:
                print(f"Failed to send WhatsApp message: {e.response.text}")
