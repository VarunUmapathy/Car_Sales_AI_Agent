import json
from typing import List, Any
from contextlib import AsyncExitStack
from langchain_core.tools import StructuredTool
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

class MCPClientManager:
    """
    Manages connections to external MCP Servers, dynamically discovers 
    their tools, and translates them into LangChain-compatible tools.
    """
    def __init__(self):
        self.mcp_server_endpoints = [
            StdioServerParameters(
                command = "python3",
                args = ["-u", "/app/mcp_servers/postgres_mcp/main.py"]
            )
        ]
        self.sessions: List[ClientSession] = []
        self._exit_stack = AsyncExitStack()

    async def connect_to_servers(self):
        """Initializes JSON-RPC connections to all configured MCP servers."""
        for server_params in self.mcp_server_endpoints:
            transport = await self._exit_stack.enter_async_context(stdio_client(server_params))
            read_stream, write_stream = transport
            session = await self._exit_stack.enter_async_context(ClientSession(read_stream, write_stream))
            await session.initialize()
            self.sessions.append(session)
            print(f"Connected to MCP Server: {server_params.args}")
    
    async def discover_tools(self) -> List[StructuredTool]:
        """Fetches available tools from all connected MCP servers and wraps them for LangChain."""
        langchain_tools = []
        for session in self.sessions:
            mcp_tools_response = await session.list_tools()
            for mcp_tool in mcp_tools_response.tools:
                langchain_tools.append(self._create_langchain_tool(session, mcp_tool))
        return langchain_tools
    
    def _create_langchain_tool(self, session: ClientSession, mcp_tool: Any) -> StructuredTool:
            """Helper to convert an MCP Tool definition into a LangChain callable tool."""
            async def _execute_mcp_tool(**kwargs) -> str:
                result = await session.call_tool(mcp_tool.name, arguements = kwargs)
                return "\n".join([content.text for content in result.content if hasattr(content, 'text')])

            return StructuredTool.from_function(
                func = None,
                coroutine=_execute_mcp_tool,
                name=mcp_tool.name,
                description=mcp_tool.description,
                args_schema=mcp_tool.inputSchema
            )

    async def cleanup(self):
        """Closes all MCP connections safely."""
        await self._exit_stack.aclose()