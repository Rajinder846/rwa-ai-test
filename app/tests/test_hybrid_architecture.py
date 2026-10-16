import pytest
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph

from app.graph.nodes.investment_node import investment_workflow
from app.graph.state import WorkflowState
from app.graph.router import route_after_investment, route_after_supervisor
from app.workflows import _format_asset_details, _format_asset_list, _message_text, asset_workflow, loan_workflow, payout_workflow, portfolio_workflow, reasoning_agent, response_formatter, staking_workflow


@pytest.mark.parametrize(("state", "expected"), [
    ({"domain": "asset", "action": "list_assets", "requires_reasoning": False}, "asset_workflow"),
    ({"domain": "investment", "action": "invest", "requires_reasoning": False}, "investment_workflow"),
    ({"domain": "reasoning", "action": "recommend_asset", "requires_reasoning": True}, "reasoning_agent"),
    ({"domain": "asset", "action": "invest", "requires_reasoning": False}, "clarification"),
])
def test_router_is_deterministic(state, expected):
    assert route_after_supervisor(state) == expected


def test_investment_only_executes_after_confirmed_pending_state():
    assert route_after_investment({"status": "processing", "pending_investment": {"asset_id": "1"}}) == "execute_investment"
    assert route_after_investment({"status": "failed"}) == "response_formatter"


@pytest.mark.asyncio
@pytest.mark.parametrize("workflow", [portfolio_workflow, loan_workflow])
async def test_unavailable_domain_api_is_a_structured_error(workflow):
    result = await workflow({"action": "get_portfolio"}, {"configurable": {}})
    assert result["final_result"] == {
        "success": False,
        "error_code": "ACTION_NOT_AVAILABLE",
        "data": None,
        "message": result["final_result"]["message"],
    }


@pytest.mark.asyncio
async def test_formatter_never_uses_an_llm_for_normal_error():
    result = await response_formatter({"final_result": {"success": False, "error_code": "KYC_NOT_COMPLETED", "data": None, "message": None}})
    assert result["response"] == "KYC verification is required before investing."


def test_list_assets_is_rendered_as_deterministic_bullets():
    response = _format_asset_list({"success": True, "data": {"assets": [
        {"_id": "asset-1", "status": "approved", "basicInfo": {"assetName": "ABC Property", "location": "Riyadh"}},
        {"_id": "asset-2", "basicInfo": {"assetName": "XYZ Villa"}},
    ]}})
    assert response == (
        "Available assets:\n\n"
        "- **ABC Property** — Riyadh — Status: approved — ID: asset-1\n"
        "- **XYZ Villa** — ID: asset-2"
    )


def test_provider_content_blocks_do_not_leak_into_the_response():
    assert _message_text([
        {"type": "text", "text": "Recommended asset."},
        {"type": "image", "data": "provider-metadata"},
    ]) == "Recommended asset."


def test_asset_details_are_rendered_from_backend_data():
    response = _format_asset_details({"success": True, "data": {
        "_id": "asset-1",
        "status": "approved",
        "basicInfo": {"assetName": "ABC Property", "assetType": "Residential", "location": "Riyadh"},
        "financialDetails": {"minimumInvestment": "200", "expectedROI": "12%"},
        "tokenEconomics": {"tokenPriceSAR": "100"},
        "investmentProgress": {"tokensAvailable": 500},
    }})
    assert response == (
        "## ABC Property\n\n"
        "### Overview\n"
        "- **Asset ID:** asset-1\n"
        "- **Status:** approved\n"
        "- **Type:** Residential\n"
        "- **Location:** Riyadh\n\n"
        "### Investment\n"
        "- **Minimum investment:** 200\n"
        "- **Expected ROI:** 12%\n"
        "- **Token price:** 100\n"
        "- **Available tokens:** 500"
    )


@pytest.mark.asyncio
@pytest.mark.parametrize(("workflow", "state"), [
    (asset_workflow, {"action": "list_assets", "parameters": {}}),
    (payout_workflow, {"action": "get_payouts", "parameters": {}}),
    (staking_workflow, {"action": "get_staking_positions", "parameters": {}}),
    (investment_workflow, {"action": "invest", "parameters": {}}),
    (reasoning_agent, {"action": "recommend_asset", "parameters": {}}),
])
async def test_api_backed_workflows_require_authenticated_backend_access(workflow, state):
    result = await workflow(state, {"configurable": {}})
    assert result["final_result"]["success"] is False
    assert result["final_result"]["error_code"] == "AUTHENTICATION_REQUIRED"


@pytest.mark.asyncio
async def test_investment_confirmation_interrupt_has_runnable_context(monkeypatch):
    class FakeClient:
        def __init__(self, _: str):
            pass

        async def get_asset(self, _: str):
            return {"success": True, "data": {
                "basicInfo": {"assetName": "ABC Property"},
                "tokenEconomics": {"tokenPriceSAR": "100"},
                "financialDetails": {"minimumInvestment": "100"},
                "investmentProgress": {"tokensAvailable": 10},
            }}

    monkeypatch.setattr("app.graph.nodes.investment_node.RWAAPIClient", FakeClient)
    builder = StateGraph(WorkflowState)
    builder.add_node("investment", investment_workflow)
    builder.add_edge(START, "investment")
    builder.add_edge("investment", END)
    graph = builder.compile(checkpointer=MemorySaver())

    result = await graph.ainvoke(
        {"parameters": {"asset_id": "asset-1", "amount": 200, "currency": "SAR"}},
        {"configurable": {"thread_id": "investment-interrupt-test", "user_jwt": "test-token"}},
    )

    assert result["__interrupt__"][0].value["type"] == "investment_confirmation"
