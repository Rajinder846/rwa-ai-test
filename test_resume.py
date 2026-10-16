import asyncio
from app.graph.graph import graph
from langgraph.types import Command

async def main():
    config = {"configurable": {"thread_id": "test_thread"}}
    print("Invoking graph...")
    # First, run the graph to reach interrupt. We need to mock asset_data.
    try:
        res = await graph.ainvoke(
            {
                "user_id": "user1",
                "conversation_id": "test_thread",
                "status": "idle",
                "messages": [],
                "asset": {
                    "success": True, 
                    "data": {
                        "_id": "asset1", 
                        "basicInfo": {"assetName": "Asset 1"},
                        "financialDetails": {"minimumInvestment": 100},
                        "tokenEconomics": {"tokenPriceUSD": 10},
                        "investmentProgress": {"tokensAvailable": 1000}
                    }
                },
                "requested_token_amount": "10"
            },
            config=config,
        )
        print("Initial response:", res)
    except Exception as e:
        print("Error during initial run:", e)
        return

    print("Resuming graph...")
    try:
        res2 = await graph.ainvoke(
            Command(resume="confirm"),
            config=config,
        )
        print("Resume response:", res2)
    except Exception as e:
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())
