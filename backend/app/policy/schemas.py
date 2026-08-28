from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import PolicyEvaluationResult


class PolicyEvaluationOutcome(BaseModel):
    """Structured result produced by the deterministic Policy Engine."""

    model_config = ConfigDict(frozen=True)

    evaluation_result: PolicyEvaluationResult = Field(
        description="Policy outcome (ALLOWED, BLOCKED, or HUMAN_REVIEW)",
    )
    policy_engine_version: str = Field(
        default="policy_v1.0",
        description="Version identifier of the active policy engine rule set",
    )
    triggered_rule_code: str | None = Field(
        default=None,
        description="Code of the highest-precedence rule triggered, if any",
    )
    rule_name: str | None = Field(
        default=None,
        description="Human-readable rule name, if any",
    )
    decision_reason: str = Field(
        description="Authoritative justification for the policy evaluation result",
    )
    evaluation_details: dict[str, Any] = Field(
        default_factory=dict,
        description="Snapshot of evaluated domain attributes and thresholds",
    )
