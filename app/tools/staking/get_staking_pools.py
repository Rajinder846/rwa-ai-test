from langchain_core.tools import tool
from langchain_core.runnables import RunnableConfig

from app.api_clients.rwa_api_client import RWAAPIClient

@tool
async def get_staking_pools(
    config: RunnableConfig,
    category_id: str = "",
) -> dict:
    """
    Get the available staking pools.
    
    Requires a valid category_id (e.g. '69d3622cacf6c8f0a60ed485').
    Returns a list of staking pools, their APY, lock periods, and capacities.
    """
    
    if config is None:
        raise RuntimeError("Tool config is missing.")

    user_jwt = config.get("configurable", {}).get("user_jwt")

    if not user_jwt:
        raise RuntimeError("Investor authentication token is missing.")

    client = RWAAPIClient(investor_token=user_jwt)
    
    if not category_id:
        try:
            categories_response = await client.get_asset_categories()
            print(categories_response)
            return {
                "message": "A category_id is required. The available categories and their IDs are listed below. DO NOT ask the user for an ID. You MUST STOP executing tools right now. Send a message to the user asking which category *name* they want to view, and list the available category names in your response. Do NOT call this tool again until the user replies.",
                "available_categories": categories_response
            }
        except Exception as e:
            return {
                "error": "A category id is required, but failed to fetch available categories."
            }
        
    return await client.get_staking_pools(category_id=category_id)
