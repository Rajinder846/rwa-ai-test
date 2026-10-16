from langchain_core.tools import tool
from langchain_core.runnables import RunnableConfig

from app.api_clients.rwa_api_client import RWAAPIClient

@tool
async def get_user_stakes(
    config: RunnableConfig,
    status: str = "",
) -> dict:
    """
    Get the investor's current staking positions.
    
    Returns a list of the user's staked assets, amounts, and lock-period progress.
    """
    
    if config is None:
        raise RuntimeError("Tool config is missing.")

    user_jwt = config.get("configurable", {}).get("user_jwt")

    if not user_jwt:
        raise RuntimeError("Investor authentication token is missing.")

    client = RWAAPIClient(investor_token=user_jwt)
    
    return await client.get_my_stakings(status=status)
