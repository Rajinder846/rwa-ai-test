from langchain_core.tools import tool
from langchain_core.runnables import RunnableConfig

from app.api_clients.rwa_api_client import RWAAPIClient

@tool
async def get_staking_categories(
    config: RunnableConfig,
) -> dict:
    """
    Get all available asset categories for staking pools.
    
    Use this to see what categories are available before fetching staking pools.
    Returns a list of categories.
    """
    
    if config is None:
        raise RuntimeError("Tool config is missing.")

    user_jwt = config.get("configurable", {}).get("user_jwt")

    if not user_jwt:
        raise RuntimeError("Investor authentication token is missing.")

    client = RWAAPIClient(investor_token=user_jwt)
    
    return await client.get_asset_categories()
