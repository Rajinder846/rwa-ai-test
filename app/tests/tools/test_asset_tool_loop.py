import pytest

pytestmark = pytest.mark.skip(reason="Asset tool-loop behavior was replaced by a deterministic workflow.")

from langchain_core.messages import HumanMessage

from app.graph.graph import graph


@pytest.mark.asyncio
async def test_asset_agent_calls_asset_tool():

    config = {
        "configurable": {
            "thread_id": "test-investment-tool-loop",
        }
    }

    result = await graph.ainvoke(
        {
            "user_id": "test-user",
            "conversation_id": "test-investment-tool-loop",
            "status": "idle",
            "messages": [
                HumanMessage(
                    content=(
                        "Tell me the details of asset asset-123"
                    )
                )
            ],
        },
        config=config,
    )

    assert result["active_agent"] == "asset_agent"

    assert result["status"] == "processing"

    assert len(result["messages"]) > 0  

    for message in result["messages"]:
        print(type(message).__name__)
        print(message)
