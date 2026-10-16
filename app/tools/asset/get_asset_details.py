# from langchain_core.runnables import RunnableConfig
from langchain_core.tools import tool, InjectedToolCallId
from langgraph.types import Command
from langchain_core.runnables import RunnableConfig
from typing import Annotated

from app.api_clients.rwa_api_client import RWAAPIClient



from langchain_core.messages import ToolMessage


@tool
async def get_asset_details(
    asset_id: str,
    config: RunnableConfig,
    tool_call_id: Annotated[str, InjectedToolCallId],
) -> Command:
    """
    Get details of a real-world asset by its asset ID.
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

    result = await client.get_asset(
        asset_id=asset_id,
    )

    return Command(
        update={
            "asset": result,
            "messages": [
                ToolMessage(
                    content="Asset details retrieved successfully.",
                    tool_call_id=tool_call_id,
                )
            ],
        }
    )