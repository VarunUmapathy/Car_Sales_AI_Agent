from typing import TypedDict, List, Annotated, Optional
from pydantic import BaseModel, Field
from langchain_core.messages import AnyMessage
from langgraph.graph.message import add_messages

class CustomerProfile(BaseModel):
    """
    Structured data that the Supervisor Node extracts and updates 
    as the conversation progresses.
    """
    name: Optional[str] = Field(
        default=None, description="The customer's known name"
    )
    phone_number: Optional[str] = Field(
        default=None, description="The customer's WhatsApp number"
    )
    preferred_make: Optional[str] = Field(
        default=None, description="Preferred car brand (e.g., Honda, Ford)"
    )
    preferred_model: Optional[str] = Field(
        default=None, description="Preferred car model (e.g., Civic, F-150)"
    )
    budget: Optional[float] = Field(
        default=None, description="Maximum budget threshold stated by the user"
    )

class AgentState(TypedDict):
    """
    The core state object passed between all LangGraph nodes.
    This dictates the flow and memory of the AI Agent.
    """
    active_session_id: str
    messages: Annotated[List[AnyMessage], add_messages]
    customer_profile: CustomerProfile
    requires_handoff: bool
 