import pytest

pytestmark = pytest.mark.skip(reason="Investment is now a deterministic workflow, not an LLM agent.")

from langchain_core.messages import HumanMessage

from app.graph.graph import graph


@pytest.mark.asyncio
async def test_investment_agent():

    config = {
        "configurable": {
            "thread_id": "test-investment-agent",
        }
    }

    result = await graph.ainvoke(
        {
            "user_id": "test-user",
            "conversation_id": "test-investment-agent",
            "status": "idle",
            "messages": [
                HumanMessage(
                    content="I want to invest 10000 tokens in Property A"
                )
            ],
        },
        config=config,
    )

    assert result["active_agent"] == "investment_agent"

    assert result["status"] == "processing"

    assert result["result"]["agent"] == "investment_agent"

    assert "response" in result["result"]
