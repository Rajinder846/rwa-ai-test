from langchain_core.tools import tool
from langchain_core.runnables import RunnableConfig
from typing import Annotated

from app.api_clients.rwa_api_client import RWAAPIClient


@tool
async def search_assets(
    config: RunnableConfig,
    search: str = "",
    status: str = "",
) -> dict:
    """
    Search or list investor-accessible assets.

    Use an empty search value when the user wants
    to list assets without searching by name.

    Examples:
    - Search by name:
      search="Al Yasmin Luxury Villa"

    - List all assets:
      search=""

    - List approved assets:
      search=""
    """

    if config is None:
        raise RuntimeError(
            "Tool config is missing."
        )

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
        investor_token=user_jwt
    )

    return await client.search_assets(
        search=search,
        status=status,
        page=1,
        limit=10,
    )