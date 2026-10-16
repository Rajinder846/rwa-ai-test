from langchain_core.tools import tool
from langchain_core.runnables import RunnableConfig
from langgraph.types import Command
from typing import Annotated

from app.api_clients.rwa_api_client import RWAAPIClient




@tool
async def invest_asset(
    asset_id: str,
    payment_method: str,
    token_quantity: str,
    config: RunnableConfig,
) -> Command:
    """
    Invest in a real-world asset by its asset ID.

    Args:
        asset_id: The ID of the asset to invest in.
        payment_method: The payment method.
        token_quantity: The number of tokens to invest.
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

    result = await client.invest(
        asset_id=asset_id,
        payment_method=payment_method,
        token_quantity=token_quantity,
    )

    return result