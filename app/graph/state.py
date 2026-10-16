from typing import Annotated, Any, Literal

from langchain_core.messages import AnyMessage
from langgraph.graph.message import add_messages
from typing_extensions import TypedDict


class WorkflowState(TypedDict, total=False):
    messages: Annotated[list[AnyMessage], add_messages]
    user_id: str
    conversation_id: str
    request_id: str
    user_message: str
    supervisor_decision: dict[str, Any]
    domain: str
    action: str
    parameters: dict[str, Any]
    requires_reasoning: bool
    tool_result: dict[str, Any]
    final_result: dict[str, Any]
    response: str
    error: dict[str, Any]
    status: Literal["idle", "processing", "waiting_for_confirmation", "completed", "failed", "cancelled"]
    asset: dict | None
    pending_investment: dict | None
