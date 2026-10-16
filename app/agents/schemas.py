from typing import Any, Literal

from pydantic import BaseModel, Field

Domain = Literal["asset", "investment", "portfolio", "payout", "loan", "staking", "reasoning"]


class SupervisorDecision(BaseModel):
    """The only LLM-produced control-plane value in a normal request."""

    domain: Domain
    action: str = Field(min_length=1)
    requires_reasoning: bool = False
    parameters: dict[str, Any] = Field(default_factory=dict)
