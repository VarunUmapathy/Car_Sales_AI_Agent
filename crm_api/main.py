import os
import json
import asyncio
import grpc
from contextlib import asynccontextmanager
from pydantic import BaseModel
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.middleware.cors import CORSMiddleware
from aiokafka import AIOKafkaConsumer
from dotenv import load_dotenv

from protos import dealership_pb2
from protos import dealership_pb2_grpc

load_dotenv()

grpc_channels = {}
grpc_stubs = {}
active_websockets = []

class SendMessagePayload(BaseModel):
    message_text: str

async def consume_kafka_events():
    """Background task to listen to Kafka and push events to the React Dashboard."""
    consumer = AIOKafkaConsumer(
        'handoff_events',
        bootstrap_servers=os.getenv('KAFKA_BROKER_URL', 'localhost:9092'),
        value_deserializer=lambda m: json.loads(m.decode('utf-8')),
        auto_offset_reset='latest'
    )
    try:
        await consumer.start()
        print("🎧 Kafka Consumer listening to 'handoff_events'...")
        async for msg in consumer:
            event = msg.value
            print(f"🚨 Handoff Event Received: {event}")
            for ws in active_websockets:
                await ws.send_json(event)
    except Exception as e:
        print(f"⚠️ Kafka connection failed (is the container running?): {e}")
    finally:
        await consumer.stop()

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manages startup and shutdown of database connections and background tasks."""
    grpc_channels['auth'] = grpc.aio.insecure_channel(os.getenv('AUTH_SERVICE_URL', 'localhost:50051'))
    grpc_channels['inventory'] = grpc.aio.insecure_channel(os.getenv('INVENTORY_SERVICE_URL', 'localhost:50052'))
    grpc_channels['chat'] = grpc.aio.insecure_channel(os.getenv('CHAT_SERVICE_URL', 'localhost:50053'))

    grpc_stubs['auth'] = dealership_pb2_grpc.AuthServiceStub(grpc_channels['auth'])
    grpc_stubs['inventory'] = dealership_pb2_grpc.InventoryServiceStub(grpc_channels['inventory'])
    grpc_stubs['chat'] = dealership_pb2_grpc.ChatServiceStub(grpc_channels['chat'])

    print("gRPC Channels established to Microservices")
    kafka_task = asyncio.create_task(consume_kafka_events())
    yield
    kafka_task.cancel()
    for channel in grpc_channels.values():
        await channel.close()
    print("gRPC Channels closed.")

app = FastAPI(title="CRM API", lifespan=lifespan)
security = HTTPBearer()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/api/inventory/search")
async def search_inventory(model_id: str = "", color: str = "", status: str = ""):
    """REST endpoint that translates an HTTP GET into a gRPC call to the Inventory Pod."""
    try:
        req = dealership_pb2.InventorySearchRequest(
            model_id=model_id,
            color=color,
            status=status
        )
        response = await grpc_stubs['inventory'].SearchInventory(req)
        return {
            "units": [
                {
                    "vin": unit.vin,
                    "model_id": unit.model_id,
                    "color": unit.color,
                    "actual_price": unit.actual_price,
                    "status": unit.status,
                    "image_url": unit.image_url
                } for unit in response.units
            ]
        }
    except grpc.aio.AioRpcError as e:
        raise HTTPException(status_code=500, detail=f"gRPC Error: {e.details()}")
    
async def get_current_agent(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Validates the JWT via gRPC and returns the agent profile for use in other endpoints."""
    try:
        req = dealership_pb2.TokenRequest(token=credentials.credentials)
        response = await grpc_stubs['auth'].ValidateToken(req)
        
        if not response.is_valid:
            raise HTTPException(status_code=401, detail=response.error_message)
            
        return response
    except grpc.aio.AioRpcError as e:
        raise HTTPException(status_code=500, detail=f"Auth gRPC Error: {e.details()}")

@app.get("/api/auth/me")
async def get_auth_me(agent=Depends(get_current_agent)):
    """Returns the profile of the currently authenticated agent."""
    return {
        "agent_id": agent.agent_id,
        "sso_user_id": agent.sso_user_id,
        "name": agent.name,
        "email": agent.email,
        "role": agent.role
    }

@app.get("/api/sessions/{session_id}/status")
async def get_session_status(session_id: str, agent=Depends(get_current_agent)):
    """Checks if a session is BOT_ACTIVE, HUMAN_REQUESTED, or HUMAN_ACTIVE."""
    try:
        req = dealership_pb2.SessionRequest(session_id=session_id)
        response = await grpc_stubs['chat'].GetSessionStatus(req)
        status_name = dealership_pb2.SessionStatusResponse.Status.Name(response.status)
        
        return {
            "session_id": session_id,
            "status": status_name,
            "assigned_agent_id": response.assigned_agent_id
        }
    except grpc.aio.AioRpcError as e:
        if e.code() == grpc.StatusCode.NOT_FOUND:
            raise HTTPException(status_code=404, detail="Session not found")
        raise HTTPException(status_code=500, detail=f"gRPC Error: {e.details()}")

@app.post("/api/sessions/{session_id}/claim")
async def claim_chat_session(session_id: str, agent=Depends(get_current_agent)):
    """Atomically assigns the currently authenticated agent to a chat session."""
    try:
        req = dealership_pb2.ClaimRequest(
            session_id=session_id,
            agent_id=agent.agent_id
        )
        response = await grpc_stubs['chat'].UpdateSessionAgent(req)
        
        if not response.success:
            # 409 Conflict implies another agent beat them to the click
            raise HTTPException(status_code=409, detail=response.error_message)
            
        return {"success": True, "message": f"Session {session_id} successfully claimed"}
    except grpc.aio.AioRpcError as e:
        raise HTTPException(status_code=500, detail=f"gRPC Error: {e.details()}")

@app.post("/api/sessions/{session_id}/messages")
async def send_human_message(session_id: str, payload: SendMessagePayload, agent=Depends(get_current_agent)):
    """Saves a message sent by the human agent to the database."""
    try:
        req = dealership_pb2.MessageRequest(
            session_id=session_id,
            agent_id=agent.agent_id, 
            message_text=payload.message_text
        )
        response = await grpc_stubs['chat'].SaveHumanMessage(req)
        
        if not response.success:
            raise HTTPException(status_code=400, detail="Failed to save message")
            
        return {
            "success": True,
            "message_id": response.message_id,
            "timestamp": response.timestamp
        }
    except grpc.aio.AioRpcError as e:
        raise HTTPException(status_code=500, detail=f"gRPC Error: {e.details()}")
    
@app.websocket("/ws/notifications")
async def websocket_endpoint(websocket: WebSocket, token: str = None):
    """
    Secure WebSocket connection. Allows authenticated React dashboards 
    to listen for live AI handoff events from Kafka.
    """
    if not token:
        await websocket.close(code=1008, reason="Missing authentication token")
        return
    try:
        req = dealership_pb2.TokenRequest(token=token)
        auth_response = await grpc_stubs['auth'].ValidateToken(req)
        if not auth_response.is_valid:
            await websocket.close(code=1008, reason="Invalid or expired token")
            return
    except Exception as e:
        print(f"WebSocket Auth Error: {e}")
        await websocket.close(code=1011, reason="Internal authentication error")
        return
    await websocket.accept()
    active_websockets.append(websocket)
    print(f"Agent {auth_response.name} connected to live notifications.")
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        active_websockets.remove(websocket)
        print(f"Agent {auth_response.name} disconnected.")

@app.get("/api/sessions")
async def list_chat_sessions(status: str = "", assigned_agent_id: str = "", agent=Depends(get_current_agent)):
    """
    Fetches a list of chat sessions. 
    Use ?status=HUMAN_REQUESTED for the global queue.
    Use ?assigned_agent_id=123 for an agent's personal queue.
    """
    try:
        req = dealership_pb2.SessionListRequest(
            status=status,
            assigned_agent_id=assigned_agent_id
        )
        response = await grpc_stubs['chat'].GetSessionsList(req)
        
        return {
            "sessions": [
                {
                    "session_id": s.session_id,
                    "contact_id": s.contact_id,
                    "status": s.status,
                    "assigned_agent_id": s.assigned_agent_id,
                    "updated_at": s.updated_at
                } for s in response.sessions
            ]
        }
    except grpc.aio.AioRpcError as e:
        raise HTTPException(status_code=500, detail=f"gRPC Error: {e.details()}")

@app.get("/api/sessions/{session_id}/messages")
async def get_session_messages(session_id: str, agent=Depends(get_current_agent)):
    """Fetches the full chronological chat history for a specific session."""
    try:
        req = dealership_pb2.SessionMessagesRequest(session_id=session_id)
        response = await grpc_stubs['chat'].GetSessionMessages(req)
        
        return {
            "messages": [
                {
                    "message_id": m.message_id,
                    "sender_type": m.sender_type,
                    "sender_id": m.sender_id,
                    "message_text": m.message_text,
                    "timestamp": m.timestamp
                } for m in response.messages
            ]
        }
    except grpc.aio.AioRpcError as e:
        raise HTTPException(status_code=500, detail=f"gRPC Error: {e.details()}")