import pytest

pytestmark = pytest.mark.skip(reason="Legacy ToolNode test replaced by deterministic workflow tests.")

from app.tools.asset.get_asset_details import (
    get_asset_details,
)


@pytest.mark.asyncio
async def test_get_asset_details():

    result = await get_asset_details.ainvoke(
        {
            "asset_id": "asset-123",
        }
    )

    assert result["asset_id"] == "asset-123"

    assert result["status"] == "approved"

    assert result["token_price"] == 100
