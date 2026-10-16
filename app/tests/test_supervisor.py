import pytest

pytestmark = pytest.mark.skip(reason="Replaced by deterministic hybrid architecture routing tests.")

from langchain_core.messages import HumanMessage

from app.graph.graph import graph


@pytest.mark.asyncio
async def test_supervisor_routes_portfolio():

    config = {
        "configurable": {
            "thread_id": "test-supervisor-portfolio",
        }
    }

    result = await graph.ainvoke(
        {
            "user_id": "test-user",
            "conversation_id": "test-supervisor-portfolio",
            "status": "idle",
            "messages": [
                HumanMessage(
                    content="Show me my portfolio"
                )
            ],
        },
        config=config,
    )

    print("\nGRAPH RESULT:")
    print(result)

    print("\nACTIVE AGENT:")
    print(result.get("active_agent"))

    assert result["active_agent"] == "portfolio_agent"

    assert result["status"] == "completed"

    assert (
        result["result"]["agent"]
        == "portfolio_agent"
    )


# @pytest.mark.asyncio
# async def test_supervisor_routes_loan():

#     config = {
#         "configurable": {
#             "thread_id": "test-supervisor-loan",
#         }
#     }

#     result = await graph.ainvoke(
#         {
#             "user_id": "test-user",
#             "conversation_id": "test-supervisor-loan",
#             "status": "idle",
#             "messages": [
#                 HumanMessage(
#                     content="Can I take a loan against my property?"
#                 )
#             ],
#         },
#         config=config,
#     )

#     # print("\nGRAPH RESULT:")
#     # print(result)

#     # print("\nACTIVE AGENT:")
#     # print(result.get("active_agent"))

#     assert result["active_agent"] == "loan_agent"

# @pytest.mark.asyncio
# async def test_supervisor_routes_staking():

#     config = {
#         "configurable": {
#             "thread_id": "test-supervisor-staking",
#         }
#     }

#     result = await graph.ainvoke(
#         {
#             "user_id": "test-user",
#             "conversation_id": "test-supervisor-staking",
#             "status": "idle",
#             "messages": [
#                 HumanMessage(
#                     content="How can I stake my tokens?"
#                 )
#             ],
#         },
#         config=config,
#     )
#     # print("\nGRAPH RESULT:")
#     # print(result)

#     # print("\nACTIVE AGENT:")
#     # print(result.get("active_agent"))

#     assert result["active_agent"] == "staking_agent"

# @pytest.mark.asyncio
# async def test_supervisor_routes_investment():

#     config = {
#         "configurable": {
#             "thread_id": "test-supervisor-investment",
#         }
#     }

#     result = await graph.ainvoke(
#         {
#             "user_id": "test-user",
#             "conversation_id": "test-supervisor-investment",
#             "status": "idle",
#             "messages": [
#                 HumanMessage(
#                     content="I want to invest 10000 tokens in Property A"
#                 )
#             ],
#         },
#         config=config,
#     )

#     # print("\nGRAPH RESULT:")
#     # print(result)

#     # print("\nACTIVE AGENT:")
#     # print(result.get("active_agent"))

#     assert result["active_agent"] == "investment_agent"
