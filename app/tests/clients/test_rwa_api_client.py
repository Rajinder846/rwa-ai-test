import pytest
import respx

from httpx import Response

from app.api_clients.rwa_api_client import RWAAPIClient


@pytest.mark.asyncio
@respx.mock
async def test_get_asset():

    route = respx.get(
        "https://development.tokenitize.com/api/investor/assets/asset-123"
    ).mock(
        return_value=Response(
            200,
            json={
                "id": "asset-123",
                "name": "Test Property",
                "status": "approved",
            },
        )
    )

    client = RWAAPIClient("test-investor-token")

    result = await client.get_asset(
        "asset-123"
    )

    assert route.called

    assert result["id"] == "asset-123"

    assert result["status"] == "approved"
