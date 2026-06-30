import json
from datetime import datetime
from aiokafka import AIOKafkaProducer
from langchain_core.tools import BaseTool
from pydantic import BaseModel, Field

class HandoffInput(BaseModel):
    is_frustrated: bool = Field(default = False, description = "Is the user angry or frustrated")
    budget: float = Field(default = None, description="The customer's max budget.")
    preferred_model: str = Field(default=None, description="The car model they want.")

class HandoffTool(BaseModel):
    """
    Triggers a handoff to a human agent and publishes the event to Kafka.
    """
    name: str = "trigger_human_handoff"
    description: str = "Use this immediately if the user asks for a human, agent, or gets frustrated."
    args_schema: type[BaseModel] = HandoffInput
    broker_url: str = "kafka:9092"

    def _run(self, *args, **kwargs) -> str:
        raise NotImplementedError("Use async _arun instead.")

    async def _arun(self, is_frustrated: bool = False, budget: float = None, preferred_model: str = None) -> str:
        payload = {
            "event_type": "HUMAN_REQUESTED",
            "timestamp": datetime.utcnow().isoformat(),
            "priority": "HIGH" if is_frustrated else "NORMAL",
            "customer_context": {
                "is_frustrated": is_frustrated,
                "budget": budget,
                "preferred_model": preferred_model
            }
        }
        await self._publish_to_broker("chat.handoff.events", payload)
        return "Handoff initiated. A human agent has been notified. Stop responding."
    
    async def _publish_to_broker(self, topic: str, payload: dict):
        producer =  AIOKafkaProducer(bootstrap_servers = self.broker_url)
        await producer.start()
        try:
            message_bytes = json.dumps(payload).encode('utf-8')
            await producer.send_and_wait(topic, message_bytes)
        finally:
            await producer.stop()
