from app.graph.state import WorkflowState

DETERMINISTIC_ACTIONS = {
    "list_assets": "asset", "get_asset": "asset", "search_assets": "asset", "get_asset_details": "asset",
    "get_portfolio": "portfolio", "get_holdings": "portfolio", "get_portfolio_value": "portfolio", "get_portfolio_transactions": "portfolio",
    "get_transactions": "investment", "check_kyc": "investment", "invest": "investment", "sell": "investment",
    "get_payouts": "payout", "get_payout_history": "payout", "get_pending_payouts": "payout", "claim_payout": "payout",
    "get_loans": "loan", "get_loan_status": "loan", "apply_loan": "loan", "repay_loan": "loan", "get_loan_details": "loan",
    "stake": "staking", "unstake": "staking", "get_staking_positions": "staking", "get_staking_rewards": "staking", "get_staking_history": "staking", "list_staking_pools": "staking",
}
REASONING_ACTIONS = {"recommend_asset", "compare_assets", "analyze_investment", "analyze_portfolio", "analyze_risk", "compare_staking_options"}


def route_after_supervisor(state: WorkflowState) -> str:
    action, domain = state.get("action"), state.get("domain")
    if action in REASONING_ACTIONS:
        return "reasoning_agent"
    if state.get("requires_reasoning") or DETERMINISTIC_ACTIONS.get(action) != domain:
        return "clarification"
    return f"{domain}_workflow"


def route_after_investment(state: WorkflowState) -> str:
    return "execute_investment" if state.get("status") == "processing" and state.get("pending_investment") else "response_formatter"
