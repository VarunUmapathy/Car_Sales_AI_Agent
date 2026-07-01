import os
import httpx
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, BackgroundTasks, Response
from psycopg_pool import AsyncConnectionPool

# Note: Adjust these imports if your linter prefers the relative '.' syntax
from graph import LangGraphOrchestrator
from agent_state import AgentState

# Setup the DB Pool for the LangGraph Checkpointer
DB_URI = os.getenv("DATABASE_URL", "postgresql://admin:123@pg_bouncer:6432/dealership_crm")
db_pool = AsyncConnectionPool(DB_URI, max_size=20)

orchestrator = LangGraphOrchestrator()

@asynccontextmanager
async def lifespan(app: FastAPI):
    await db_pool.open()
    await orchestrator.compile_graph(db_pool)
    yield
    await orchestrator.mcp_client.cleanup()
    await db_pool.close()

app = FastAPI(lifespan=lifespan)

# ---------------------------------------------------------
# FASTAPI ROUTES (Flattened out of the class)
# ---------------------------------------------------------

@app.get("/webhook/ai_agent")
async def verify_webhook(request: Request):
    """Required by Meta to verify the webhook URL during setup."""
    mode = request.query_params.get("hub.mode")
    token = request.query_params.get("hub.verify_token")
    challenge = request.query_params.get("hub.challenge")
    
    if mode == "subscribe" and token == "dealership_secret":
        return Response(content=challenge, media_type="text/plain")
        
    return {"error": "Invalid token"}

@app.post("/webhook/ai_agent")
async def receive_webhook(request: Request, background_tasks: BackgroundTasks):
    """Receives WhatsApp messages from Meta."""
    payload = await request.json()
    
    # Meta's payload structure is deeply nested; we'll assume a simplified extraction for now
    # You will likely need to adjust this extraction logic based on Meta's exact JSON shape
    session_id = payload.get("session_id", "default_user") 
    text = payload.get("text", "")
    
    background_tasks.add_task(process_message, session_id, text)
    return {"status": "processing"}

# ---------------------------------------------------------
# BACKGROUND TASKS
# ---------------------------------------------------------

async def process_message(session_id: str, text: str):
    """Invokes the LangGraph orchestrator with the new message."""
    input_state = {
        "messages": [("user", text)],
        "active_session_id": session_id
    }
    
    config = {"configurable": {"thread_id": session_id}}
    result = await orchestrator.invoke_agent(input_state, config)
    
    if result.get("requires_handoff"):
        print(f"Session {session_id} has been handed off to Kafka. AI sleeping.")
        return
        
    ai_reply = result["messages"][-1].content
    print(f"AI Response to {session_id}: {ai_reply}")
    
    await send_whatsapp_message(phone_number=session_id, text=ai_reply)

async def send_whatsapp_message(phone_number: str, text: str):
    """Fires an HTTP POST request to the Meta Graph API."""
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