import httpx

from app.config.settings import settings


class RWAAPIClient:

    def __init__(self, investor_token: str):
        self.base_url = settings.rwa_api_url
        self.investor_token = investor_token

    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self.investor_token}",
            "Accept": "application/json",
        }

    async def get_asset(
        self,
        asset_id: str,
    ) -> dict:

        url = (
            f"{self.base_url}/investor/assets/{asset_id}"
        )

        async with httpx.AsyncClient(
            timeout=10.0
        ) as client:

            response = await client.get(
                url,
                headers=self._headers(),
            )

            response.raise_for_status()

            return response.json()

    async def search_assets(
        self,
        search: str = "",
        status: str = "",
        page: int = 1,
        limit: int = 10,
    ) -> dict:

        url = f"{self.base_url}/investor/assets"

        headers = {
            "Authorization": f"Bearer {self.investor_token}",
            "Accept": "application/json",
        }

        params = {
            "search": search,
            "status": status,
            "page": page,
            "limit": limit,
        }

        async with httpx.AsyncClient(
            timeout=10.0
        ) as client:

            response = await client.get(
                url,
                headers=headers,
                params=params,  
            )

            response.raise_for_status()

            return response.json()


    async def invest(
        self,
        asset_id: str,
        payment_method: str,
        token_quantity: str,
    ) -> dict:

        url = f"{self.base_url}/investor/invest"

        payload = {
            "assetId": asset_id,
            "paymentMethod": payment_method,
            "tokenAmount": token_quantity
        }

        headers = {
            "Authorization": f"Bearer {self.investor_token}",
            "Content-Type": "application/json",
        }

        async with httpx.AsyncClient(
            timeout=10.0
        ) as client:

            response = await client.post(
                url,
                headers=headers,
                json=payload,
            )

            response.raise_for_status()

            return response.json()


    async def get_payouts(
        self,
        tab: str,
        page: int = 1,
        limit: int = 10,
    ) -> dict:

        url = f"{self.base_url}/investor/payouts"
        headers = self._headers()
        params = {
            "page": page,
            "limit": limit,
            "sortBy": "Date (Newest)",
            "tab": tab,
        }

        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(url, headers=headers, params=params)
            response.raise_for_status()
            return response.json()

    async def get_my_stakings(
        self,
        status: str = "",
        page: int = 1,
        limit: int = 10,
    ) -> dict:

        url = f"{self.base_url}/investor/staking/my-stakings"
        headers = self._headers()
        params = {
            "status": status,
            "page": page,
            "limit": limit,
        }

        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(url, headers=headers, params=params)
            response.raise_for_status()
            return response.json()

    async def get_staking_pools(
        self,
        category_id: str = "",
        page: int = 1,
        limit: int = 10,
    ) -> dict:
        url = f"{self.base_url}/investor/staking/pools"
        headers = self._headers()
        params = {
            "page": page,
            "limit": limit,
        }
        if category_id:
            params["category"] = category_id

        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(url, headers=headers, params=params)
            response.raise_for_status()
            return response.json()

    async def get_asset_categories(self) -> dict:
        url = f"{self.base_url}/investor/assetCategory"
        headers = self._headers()
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(url, headers=headers)
            response.raise_for_status()
            return response.json()
