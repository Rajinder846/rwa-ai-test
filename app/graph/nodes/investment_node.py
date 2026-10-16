from decimal import Decimal, InvalidOperation

from langchain_core.runnables import RunnableConfig
from langchain_core.runnables.config import var_child_runnable_config
from langgraph.types import interrupt

from app.api_clients.rwa_api_client import RWAAPIClient
from app.graph.state import WorkflowState
from app.workflows import _error, _ok


def _asset_payload(response: dict) -> dict | None:
    return response.get("data") if response.get("success") else None


async def investment_workflow(state: WorkflowState, config: RunnableConfig) -> dict:
    """Prepare an investment deterministically; execution requires confirmation."""
    params = state.get("parameters", {})
    token = config.get("configurable", {}).get("user_jwt")
    if not token:
        result = _error("AUTHENTICATION_REQUIRED", "Investor authentication token is missing.")
        return {"tool_result": result, "final_result": result, "status": "failed"}
    client = RWAAPIClient(token)
    try:
        asset_id = params.get("asset_id")
        if not asset_id and params.get("asset_name"):
            search = await client.search_assets(search=str(params["asset_name"]))
            candidates = search.get("data", search.get("assets", []))
            if isinstance(candidates, dict):
                candidates = candidates.get("items", candidates.get("assets", []))
            if not isinstance(candidates, list) or len(candidates) != 1:
                result = _error("ASSET_SELECTION_REQUIRED", "Please provide the exact asset ID so the investment can be prepared.")
                return {"tool_result": result, "final_result": result, "status": "failed"}
            asset_id = candidates[0].get("_id") or candidates[0].get("id")
        if not asset_id:
            result = _error("MISSING_PARAMETER", "Please provide the asset you want to invest in.")
            return {"tool_result": result, "final_result": result, "status": "failed"}
        asset_response = await client.get_asset(str(asset_id))
    except Exception:
        result = _error("BACKEND_REQUEST_FAILED", "Unable to retrieve the requested asset.")
        return {"tool_result": result, "final_result": result, "status": "failed"}

    asset = _asset_payload(asset_response)
    if not asset:
        result = _error("ASSET_NOT_FOUND", "The requested asset was not found.")
        return {"tool_result": result, "final_result": result, "status": "failed"}
    try:
        economics, details, progress = asset.get("tokenEconomics", {}), asset.get("financialDetails", {}), asset.get("investmentProgress", {})
        price = Decimal(str(economics.get("tokenPriceSAR", economics.get("tokenPriceUSD"))))
        minimum, available = Decimal(str(details["minimumInvestment"])), int(progress["tokensAvailable"])
        amount = Decimal(str(params.get("amount")))
        if params.get("currency", "SAR") != "SAR":
            raise InvalidOperation
        quantity = amount / price
        if quantity != quantity.to_integral_value():
            result = _error("INVALID_INVESTMENT_AMOUNT", "The amount must purchase a whole number of tokens at the current price.")
            return {"tool_result": result, "final_result": result, "status": "failed"}
        quantity = int(quantity)
        if quantity <= 0 or amount < minimum:
            result = _error("INVESTMENT_LIMIT_EXCEEDED", f"The minimum investment is {minimum} SAR.")
            return {"tool_result": result, "final_result": result, "status": "failed"}
        if quantity > available:
            result = _error("INSUFFICIENT_TOKENS", f"Only {available} tokens are currently available.")
            return {"tool_result": result, "final_result": result, "status": "failed"}
    except (KeyError, TypeError, InvalidOperation, ValueError):
        result = _error("INVALID_INVESTMENT_REQUEST", "Provide a valid SAR amount and an asset with current token information.")
        return {"tool_result": result, "final_result": result, "status": "failed"}

    pending = {"asset_id": str(asset_id), "asset_name": asset.get("basicInfo", {}).get("assetName", "the asset"), "token_quantity": str(quantity), "total_amount": str(amount), "currency": "SAR"}

    # Python 3.10 needs the graph config reattached before an interrupt can
    # retrieve its runnable context. Without this, LangGraph raises
    # "Called get_config outside of a runnable context" at confirmation time.
    var_child_runnable_config.set(config)
    confirmation = interrupt({"type": "investment_confirmation", "message": f"Confirm investment of {amount} SAR in {pending['asset_name']} for {quantity} tokens.", "investment": pending, "actions": ["confirm", "cancel"]})
    if confirmation == "confirm":
        return {"pending_investment": pending, "status": "processing"}
    result = _error("INVESTMENT_CANCELLED", "The investment was cancelled.")
    return {"tool_result": result, "final_result": result, "status": "cancelled"}
