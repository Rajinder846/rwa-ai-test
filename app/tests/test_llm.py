import pytest

pytestmark = pytest.mark.skip(reason="External-provider connectivity is not a unit-test contract.")

from app.core.llm import get_llm


@pytest.mark.asyncio
async def test_gemini_connection():

    llm = get_llm()

    response = await llm.ainvoke(
        "Respond with exactly: Gemini connection successful"
    )

    assert response.content
