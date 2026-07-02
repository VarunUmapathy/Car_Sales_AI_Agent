import asyncio
import os
import re
from psycopg_pool import AsyncConnectionPool
from graph import LangGraphOrchestrator

async def main():
    # 1. Setup the exact same DB connection as your FastAPI app
    DB_URI = os.getenv("DATABASE_URL", "postgresql://admin:123@postgres:5432/dealership_crm")
    db_pool = AsyncConnectionPool(DB_URI, max_size=20, open=False, kwargs={"autocommit": True})
    
    orchestrator = LangGraphOrchestrator()
    
    # 2. Boot up the connections
    await db_pool.open()
    await orchestrator.compile_graph(db_pool)
    
    print("\n" + "="*50)
    print("🤖 AI Agent Local Terminal Activated!")
    print("Traces are being sent to LangSmith.")
    print("Type 'quit' or 'exit' to stop.")
    print("="*50 + "\n")
    
    # Use a dummy session ID for local testing
    session_id = "langsmith_test_user_05"
    
    try:
        while True:
            user_input = input("You: ")
            if user_input.lower() in ['quit', 'exit']:
                break
                
            input_state = {
                "messages": [("user", user_input)],
                "active_session_id": session_id
            }
            config = {"configurable": {"thread_id": session_id}}
            
            # This is the magic line that LangSmith is watching
            result = await orchestrator.invoke_agent(input_state, config)
            
            # Check for handoff
            handoff_triggered = False
            for message in result.get("messages", []):
                if hasattr(message, "tool_calls") and message.tool_calls:
                    for tc in message.tool_calls:
                        if tc["name"] == "trigger_human_handoff":
                            handoff_triggered = True
                            print(f"\nAI: ⚙️ [Handoff Event Triggered] Sent to Kafka topic.\n")
                            break
            
            if handoff_triggered:
                continue
                
            # Print the standard AI reply with hallucinated tags scrubbed
            ai_reply = result["messages"][-1].content
            ai_reply = re.sub(r"<[^>]+>", "", ai_reply).strip()
            
            print(f"AI: {ai_reply}\n")
            
    finally:
        # Clean up resources when you quit
        await orchestrator.mcp_client.cleanup()
        await db_pool.close()
        print("Agent shut down safely.")

if __name__ == "__main__":
    asyncio.run(main())