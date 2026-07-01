from typing import Literal
from langchain_core.messages import SystemMessage, ToolMessage
from langchain_groq import ChatGroq
from langgraph.graph import StateGraph, START, END
from langgraph.prebuilt import ToolNode
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver

from agent_state import AgentState
from mcp_client import MCPClientManager
from tools.handoff_tool import HandoffTool

class SupervisorNode:
    """The core reasoning node that executes the LLM."""
    def __init__(self, llm: ChatGroq, tools: list):
        self.llm = llm.bind_tools(tools)
        with open("System_instructions.txt", "r") as file:
            self.system_prompt = file.read()

    async def __call__(self, state: AgentState) -> dict:
        messages = state.get("messages", [])
        if not messages or not isinstance(messages[0], SystemMessage):
            messages = [SystemMessage(content=self.system_prompt)] + messages
        response = await self.llm.ainvoke(messages)
        return {"messages": [response]}

class LangGraphOrchestrator:
    """Constructs and manages the LangGraph execution environment."""
    def __init__(self):
        self.mcp_client = MCPClientManager()
        self.handoff_tool = HandoffTool(broker_url="kafka:9092")
        self.compiled_graph = None
    
    async def compile_graph(self, db_pool) -> StateGraph:
        """Discovers tools, builds the graph, and attaches the Postgres Checkpointer."""
        await self.mcp_client.connect_to_servers()
        mcp_tools = await self.mcp_client.discover_tools()
        all_tools = mcp_tools + [self.handoff_tool]
        llm = ChatGroq(model_name="llama-3.3-70b-versatile", temperature=0)
        self.supervisor = SupervisorNode(llm, all_tools)

        workflow = StateGraph(AgentState)
        workflow.add_node("supervisor", self.supervisor)
        workflow.add_node("tools", ToolNode(all_tools))
        workflow.add_edge(START, "supervisor")
        workflow.add_conditional_edges(
            "supervisor",
            self._route_after_supervisor,
            {"tools": "tools", "__end__": END}
        )
        workflow.add_edge("tools", "supervisor")
        self.checkpointer = AsyncPostgresSaver(db_pool)
        self.compiled_graph = workflow.compile(checkpointer =  self.checkpointer)
        return self.compiled_graph
    
    def _route_after_supervisor(self, state: AgentState) -> Literal["tools", "__end__"]:
        last_message = state["messages"][-1]
        if not hasattr(last_message, "tool_calls") or not last_message.tool_calls:
            return "__end__"
        if any(tc["name"] == "trigger_human_handoff" for tc in last_message.tool_calls):
            state["requires_handoff"] = True
        return "tools"
    
    async def invoke_agent(self, state: dict, config: dict) -> dict:
        return await self.compiled_graph.ainvoke(state, config)