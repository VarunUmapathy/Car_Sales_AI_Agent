import os
import httpx
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, BackgroundTasks, Response, Form
from psycopg_pool import AsyncConnectionPool
from graph import LangGraphOrchestrator
from agent_state import AgentState

# Setup the DB Pool for the LangGraph Checkpointer
DB_URI = os.getenv("DATABASE_URL", "postgresql://admin:123@postgres:5432/dealership_crm")
db_pool = AsyncConnectionPool(DB_URI, max_size=20, open=False, kwargs={"autocommit": True})

orchestrator = LangGraphOrchestrator()

@asynccontextmanager
async def lifespan(app: FastAPI):
    await db_pool.open()
    await orchestrator.compile_graph(db_pool)
    yield
    await orchestrator.mcp_client.cleanup()
    await db_pool.close()

app = FastAPI(lifespan=lifespan)

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
    form_data = await request.form()
    session_id = form_data.get("From") 
    text = form_data.get("Body")
    if not session_id or not text:
        return {"status": "ignored"}
    background_tasks.add_task(process_message, session_id, text)
    return Response(content="<Response></Response>", media_type="application/xml")


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
    account_sid = os.getenv("TWILIO_ACCOUNT_SID")
    auth_token = os.getenv("TWILIO_AUTH_TOKEN")
    twilio_number = "whatsapp:+14155238886"
    url = f"https://api.twilio.com/2010-04-01/Accounts/{account_sid}/Messages.json"
    payload = {
        "From": twilio_number,
        "To": phone_number,
        "Body": text
    }
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                url, 
                auth=(account_sid, auth_token), 
                data=payload
            )
            response.raise_for_status()
        except httpx.HTTPStatusError as e:
            print(f"Failed to send WhatsApp message via Twilio: {e.response.text}") 