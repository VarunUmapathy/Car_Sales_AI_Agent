import os
import json
import asyncio
import grpc
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from aiokafka import AIOKafkaConsumer
from dotenv import load_dotenv

from protos import dealership_pb2
from protos import dealership_pb2_grpc

load_dotenv()

grpc_channels = {}
grpc_stubs = {}
active_websockets = []

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
    
@app.post("/api/auth/validate")
async def validate_agent_token(token: str):
    """Validates an Auth0 token using the Auth Pod."""
    try:
        req = dealership_pb2.TokenRequest(token=token)
        response = await grpc_stubs['auth'].ValidateToken(req)
        if not response.is_valid:
            raise HTTPException(status_code=401, detail=response.error_message)
        return {
            "agent_id": response.agent_id,
            "name": response.name,
            "role": response.role,
            "email": response.email
        }
    except grpc.aio.AioRpcError as e:
        raise HTTPException(status_code=500, detail=f"gRPC Error: {e.details()}")
    
@app.websocket("/ws/dashboard")
async def websocket_endpoint(websocket: WebSocket):
    """Allows the React dashboard to listen for live AI handoff events."""
    await websocket.accept()
    active_websockets.append(websocket)
    print("React Dashboard Connected via WebSocket")
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        active_websockets.remove(websocket)
        print("React Dashboard Disconnected")