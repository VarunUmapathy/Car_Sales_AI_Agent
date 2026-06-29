from langchain_core.messages import SystemMessage, ToolMessage

from agent_state import AgentState

SYSTEM_PROMPT = ""
with open('requirements.txt', 'r', encoding='utf-8') as file:
    SYSTEM_PROMPT = file.read()

def call_model(state: AgentState, llm_with_tools) -> dict:
    """
    The main reasoning node. Passes the conversation history to the LLM.
    """
    messages = state.get("messages", [])
    if not messages or not isinstance(messages[0], SystemMessage):
        messages = [SystemMessage(content=SYSTEM_PROMPT)] + messages
    response = llm_with_tools.invoke(messages)
    return {"messages" : [response]}


