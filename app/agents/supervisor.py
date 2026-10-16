import time

from langchain_core.messages import HumanMessage, SystemMessage

from app.agents.schemas import SupervisorDecision
from app.core.llm import get_llm
from app.core.logger import get_logger
from app.graph.state import WorkflowState

logger = get_logger("supervisor")

SUPERVISOR_SYSTEM_PROMPT = """
You are the request-understanding supervisor for an RWA investment platform.
Return only the structured decision. Select a high-level business action, never a
tool, API, calculation, or execution step. Parameters contain only facts stated
by the user; do not invent IDs, prices, balances, KYC state, or permissions.

Domains/actions: asset (list_assets, get_asset, search_assets, get_asset_details);
investment (invest, sell, get_transactions, check_kyc); portfolio (get_portfolio,
get_holdings, get_portfolio_value, get_portfolio_transactions); payout (get_payouts,
get_payout_history, get_pending_payouts, claim_payout); loan (get_loans,
get_loan_status, apply_loan, repay_loan, get_loan_details); staking (stake, unstake,
get_staking_positions, get_staking_rewards, get_staking_history, list_staking_pools);
reasoning (recommend_asset, compare_assets, analyze_investment, analyze_portfolio,
analyze_risk, compare_staking_options). Set requires_reasoning true only for reasoning.
For investments extract amount, currency, asset_name or asset_id if supplied.
"""


def _latest_user_message(state: WorkflowState) -> str:
    for message in reversed(state.get("messages", [])):
        if isinstance(message, HumanMessage):
            return str(message.content)
    return state.get("user_message", "")


async def supervisor_node(state: WorkflowState) -> dict:
    started = time.perf_counter()
    decision = await get_llm().with_structured_output(SupervisorDecision).ainvoke([
        SystemMessage(content=SUPERVISOR_SYSTEM_PROMPT), HumanMessage(content=_latest_user_message(state))
    ])
    logger.info("supervisor_decision", request_id=state.get("request_id"), user_id=state.get("user_id"), conversation_id=state.get("conversation_id"), decision=decision.model_dump(), llm_latency_ms=round((time.perf_counter() - started) * 1000, 2))
    return {"user_message": _latest_user_message(state), "supervisor_decision": decision.model_dump(), "domain": decision.domain, "action": decision.action, "parameters": decision.parameters, "requires_reasoning": decision.requires_reasoning, "status": "processing"}
