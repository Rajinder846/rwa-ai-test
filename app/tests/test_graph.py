import pytest

pytestmark = pytest.mark.skip(reason="The previous placeholder graph contract was replaced by workflow tests.")

from app.graph.graph import graph


@pytest.mark.asyncio
async def test_graph():

    config = {
        "configurable": {
            "thread_id": "test-conversation-001",
        }
    }

    result = await graph.ainvoke(
        {
            "user_id": "test-user",
            "conversation_id": "test-conversation",
            "status": "idle",
            "messages": [],
        },
        config=config,
    )

    assert result["status"] == "processing"

    assert result["result"]["message"] == "LangGraph is working"


@pytest.mark.asyncio
async def test_graph_checkpoint():

    thread_id = "test-conversation-checkpoint"

    config = {
        "configurable": {
            "thread_id": thread_id,
        }
    }

    result = await graph.ainvoke(
        {
            "user_id": "test-user",
            "conversation_id": thread_id,
            "status": "idle",
            "messages": [],
        },
        config=config,
    )

    assert result["status"] == "processing"

    checkpoint = await graph.aget_state(config)

    assert checkpoint.values["user_id"] == "test-user"

    assert checkpoint.values["conversation_id"] == thread_id

    assert checkpoint.values["status"] == "processing"

    assert checkpoint.values["result"]["message"] == "LangGraph is working"
