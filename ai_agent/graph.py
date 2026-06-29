import json
from typing import Literal
from langchain_core.messages import SystemMessage, ToolMessage
from langchain_groq import ChatGroq
from langgraph.graph import StateGraph, START, END
from langgraph.prebuilt import ToolNode

from .nodes import call_model
from .tools.handoff_tool import trigger_human_handoff

llm = ChatGroq(model_name="llama-3.3-70b-versatile", temperature=0)
tools = [trigger_human_handoff]
llm_with_tools = llm.bind_tools(tools)



