import asyncio
import uuid
from app.graph.graph import graph
from langchain_core.messages import HumanMessage

async def test():
    thread_id = str(uuid.uuid4())
    config = {"configurable": {"thread_id": thread_id, "user_jwt": "test_token"}}
    
    # Simulate an active asset agent
    state = {
        "user_id": "user1",
        "conversation_id": thread_id,
        "status": "idle",
        "active_agent": "asset_agent",
        "messages": [
            HumanMessage(content="i want to invest 200 sar in NEW Luxury Asset")
        ]
    }
    
    print("Invoking graph...")
    result = await graph.ainvoke(state, config=config)
    
    if "__interrupt__" in result:
        print("Interrupt:", result["__interrupt__"][0].value)
    else:
        messages = result.get("messages", [])
        if messages:
            print("Last message:", messages[-1].content)
        else:
            print("No messages in output")
            
    print("Final status:", result.get("status"))

asyncio.run(test())
