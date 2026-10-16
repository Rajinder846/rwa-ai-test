import asyncio
import uuid
from httpx import AsyncClient

async def test():
    async with AsyncClient(base_url="http://127.0.0.1:8000") as client:
        res = await client.post("/chat", params={"message": "i want to invest 200 sar in NEW Luxury Asset", "conversation_id": str(uuid.uuid4())})
        print(res.status_code)
        print(res.text)

asyncio.run(test())
