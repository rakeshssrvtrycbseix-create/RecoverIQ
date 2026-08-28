from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import RecoveryActionType


class AgentDecisionOutput(BaseModel):
    """
    Strict schema for validated AI Agent recovery strategy recommendations.
    Matches attributes stored in the agent_decisions database model.
    """

    model_config = ConfigDict(frozen=True)

    proposed_action_type: RecoveryActionType = Field(
        description="The operational recovery action proposed by the agent",
    )
    confidence_score: float = Field(
        ge=0.0,
        le=1.0,
        description="Confidence score in [0.0, 1.0]",
    )
    reasoning_summary: str = Field(
        min_length=10,
        max_length=2000,
        description="Concise rationale explaining why this action was selected",
    )
    suggested_payload: dict[str, Any] = Field(
        default_factory=dict,
        description="Action-specific execution parameters",
    )
    recommended_delay_hours: int = Field(
        ge=0,
        le=168,
        default=0,
        description="Recommended delay in hours before action dispatch",
    )
    agent_name: str = Field(
        default="RecoveryOrchestrator",
        max_length=64,
        description="Name identifier of the decision agent",
    )
    agent_version: str = Field(
        default="v1.0",
        max_length=32,
        description="Semantic version of agent logic",
    )
    prompt_template_version: str = Field(
        default="recovery_agent_v1.0",
        max_length=32,
        description="Version of prompt template utilized",
    )
    token_usage: dict[str, Any] | None = Field(
        default=None,
        description="Token accounting telemetry (prompt, completion, total)",
    )


class RecoveryCaseContext(BaseModel):
    """Sanitized operational telemetry for an active RecoveryCase."""

    model_config = ConfigDict(frozen=True)

    case_id: str
    status: str
    recovery_stage: str
    amount_at_risk: int = Field(ge=0)
    currency: str
    total_attempts_count: int = Field(ge=0)
    max_allowed_attempts: int = Field(ge=1)
    opened_at: str
    latest_failure_reason: str | None = None
    hours_since_failure: float = Field(ge=0.0)


class PaymentContext(BaseModel):
    """Sanitized transaction parameters for the failed Payment."""

    model_config = ConfigDict(frozen=True)

    payment_id: str
    amount: int = Field(ge=0)
    currency: str
    is_subscription: bool
    billing_cadence: str | None = None


class CustomerProfileContext(BaseModel):
    """Anonymized historical payment performance statistics for the Customer."""

    model_config = ConfigDict(frozen=True)

    customer_id: str
    risk_tier: str
    total_payments_count: int = Field(ge=0)
    successful_payments_count: int = Field(ge=0)
    failed_payments_count: int = Field(ge=0)
    historical_success_rate: float = Field(ge=0.0, le=1.0)


class MLPredictionContext(BaseModel):
    """Pre-computed Phase 5 ML recovery probability telemetry."""

    model_config = ConfigDict(frozen=True)

    prediction_id: str
    model_name: str
    model_version: str
    recovery_probability: float = Field(ge=0.0, le=1.0)
    risk_score: float = Field(ge=0.0, le=1.0)
    confidence: float = Field(ge=0.0, le=1.0)
    priority: str
    predicted_channel: str | None = None
    predicted_delay_hours: int | None = None


class PaymentAttemptContext(BaseModel):
    """Sanitized historical attempt record."""

    model_config = ConfigDict(frozen=True)

    attempt_number: int = Field(ge=1)
    amount: int = Field(ge=0)
    status: str
    error_code: str | None = None
    error_source: str | None = None
    error_step: str | None = None
    error_reason: str | None = None
    error_description: str | None = None
    initiated_at: str | None = None


class AgentContextPayload(BaseModel):
    """
    Zero-PII aggregated input context ready for prompt formatting.
    Strictly free from sensitive personal identifiers or credentials.
    """

    model_config = ConfigDict(frozen=True)

    recovery_case: RecoveryCaseContext
    payment: PaymentContext
    customer_profile: CustomerProfileContext
    ml_prediction: MLPredictionContext | None = None
    attempt_history: list[PaymentAttemptContext] = Field(default_factory=list)
    subscription_age_days: int = Field(ge=0, default=0)
