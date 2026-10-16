from langchain_core.runnables import RunnableConfig

from app.api_clients.rwa_api_client import RWAAPIClient
from app.graph.state import WorkflowState
from app.workflows import _error, _ok


async def execute_investment_node(state: WorkflowState, config: RunnableConfig) -> dict:
    pending = state.get("pending_investment")
    token = config.get("configurable", {}).get("user_jwt")
    if not pending or not token:
        result = _error("TRANSACTION_FAILED", "No authorized pending investment was found.")
        return {"tool_result": result, "final_result": result, "status": "failed"}
    try:
        data = await RWAAPIClient(token).invest(asset_id=pending["asset_id"], payment_method="CRYPTO_WALLET", token_quantity=pending["token_quantity"])
    except Exception:
        result = _error("TRANSACTION_FAILED", "The investment transaction could not be completed.")
        return {"tool_result": result, "final_result": result, "status": "failed"}
    result = _ok({**(data if isinstance(data, dict) else {"result": data}), "message": f"Your investment of {pending['total_amount']} SAR in {pending['asset_name']} was completed successfully."})
    return {"tool_result": result, "final_result": result, "pending_investment": None, "status": "completed"}
