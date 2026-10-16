from langchain_core.tools import tool
from langchain_core.runnables import RunnableConfig

from app.api_clients.rwa_api_client import RWAAPIClient


@tool
async def get_payout_history(
    config: RunnableConfig,
    page: int = 1,
    limit: int = 10,
) -> dict:
    """
    Get the investor's historical (past) payouts.
    This includes payouts that have already been paid.
    The response contains the total records count and a list of payouts for the requested page.
    Use `page` and `limit` to paginate through records if needed.
    """

    user_jwt = (
        config
        .get("configurable", {})
        .get("user_jwt")
    )

    if not user_jwt:
        raise RuntimeError(
            "Investor authentication token is missing."
        )

    client = RWAAPIClient(
        investor_token=user_jwt,
    )

    return await client.get_payouts(
        tab="history",
        page=page,
        limit=limit,
    )
