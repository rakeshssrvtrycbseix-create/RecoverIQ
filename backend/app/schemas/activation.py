from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field, field_validator

ALLOWED_ROLLOUT_PERCENTAGES = {0, 5, 10, 25, 50, 100}
CANARY_ROLLOUT_PERCENTAGES = {5, 10, 25, 50}


class ExperimentMetrics(BaseModel):
    """Granular operational and financial recovery metrics for control or treatment cohort."""

    sample_size: int = Field(description="Total number of evaluated cases in cohort")
    recovered_count: int = Field(description="Total successfully recovered cases")
    failed_count: int = Field(description="Total terminal failed or closed cases")
    recovery_rate: float | None = Field(
        default=None, description="Recovery rate ratio (0.0 to 1.0)"
    )
    amount_at_risk_paise: int = Field(
        description="Total monetary exposure in integer paise"
    )
    amount_recovered_paise: int = Field(
        description="Total monetary value successfully recovered in integer paise"
    )
    financial_yield: float | None = Field(
        default=None, description="Monetary yield ratio (0.0 to 1.0)"
    )
    expected_recovery_value_paise: int | None = Field(
        default=None, description="Expected Recovery Value in integer paise"
    )
    mean_time_to_recovery_hours: float | None = Field(
        default=None, description="Average MTTR in decimal hours"
    )
    median_time_to_recovery_hours: float | None = Field(
        default=None, description="Median MTTR in decimal hours"
    )


class UpliftMetrics(BaseModel):
    """Comparative differential and uplift statistics between treatment and control."""

    absolute_uplift: float | None = Field(
        default=None, description="Treatment rate minus control rate (e.g. +0.05)"
    )
    relative_uplift_pct: float | None = Field(
        default=None, description="Percentage relative uplift (e.g. +15.5%)"
    )
    incremental_recovered_amount_paise: int | None = Field(
        default=None,
        description="Incremental actual recovered amount in integer paise",
    )
    incremental_expected_recovery_value_paise: int | None = Field(
        default=None,
        description="Incremental Expected Recovery Value (ERV) in integer paise",
    )


class ConfidenceInterval(BaseModel):
    """Conservative 95% confidence interval for rate delta."""

    lower_bound: float | None = Field(
        default=None, description="Lower bound of difference interval"
    )
    upper_bound: float | None = Field(
        default=None, description="Upper bound of difference interval"
    )
    confidence_level: float = Field(
        default=0.95, description="Statistical confidence level"
    )
    is_significant: bool = Field(
        default=False,
        description="True if confidence interval strictly excludes zero",
    )


class StrategyComparison(BaseModel):
    """Complete experimental comparison between control and treatment cohorts."""

    control_metrics: ExperimentMetrics
    treatment_metrics: ExperimentMetrics
    uplift: UpliftMetrics
    confidence_interval: ConfidenceInterval
    reliability: str = Field(
        description="Statistical sample reliability (SUFFICIENT, LIMITED, INSUFFICIENT_DATA)"
    )


class RolloutHealth(BaseModel):
    """Automated safety and health assessment of an active canary experiment."""

    status: str = Field(
        description="Rollout health state (SAFE, WARNING, ROLLBACK_RECOMMENDED)"
    )
    diagnostics: list[str] = Field(
        default_factory=list,
        description="Human-readable safety diagnostic indicators",
    )
    evaluated_at: datetime = Field(description="Timestamp when health was evaluated")


class ActivationDiagnostic(BaseModel):
    """Granular activation diagnostic code and message."""

    code: str
    severity: str
    message: str


class CreateActivationRequest(BaseModel):
    """Payload to initiate a new strategy activation draft from an approved recommendation."""

    recommendation_id: str = Field(
        ..., description="Public identifier of approved strategy recommendation"
    )
    target_segment: dict[str, Any] | None = Field(
        default=None, description="Optional customer/failure segment filters"
    )
    notes: str | None = Field(
        default=None, max_length=512, description="Optional creation audit notes"
    )


class StartCanaryRequest(BaseModel):
    """Payload to start or adjust a canary rollout stage."""

    rollout_percentage: int = Field(
        ...,
        description="Canary rollout percentage. Allowed values: 5, 10, 25, 50",
    )
    notes: str | None = Field(
        default=None, max_length=512, description="Optional operator audit notes"
    )

    @field_validator("rollout_percentage")
    @classmethod
    def validate_canary_percentage(cls, v: int) -> int:
        if v not in CANARY_ROLLOUT_PERCENTAGES:
            raise ValueError(
                f"Invalid canary rollout percentage '{v}'. Allowed canary stages: {sorted(CANARY_ROLLOUT_PERCENTAGES)}"
            )
        return v


class ActivationActionRequest(BaseModel):
    """Payload for pause, rollback, approve, and activate actions."""

    notes: str | None = Field(
        default=None, max_length=512, description="Operator audit rationale"
    )


class StrategyActivationResponse(BaseModel):
    """Complete governed strategy activation and canary experiment report."""

    activation_id: str = Field(description="Unique public activation identifier")
    recommendation_id: str = Field(
        description="Associated strategy recommendation identifier"
    )
    strategy_type: str = Field(description="Recovery action category under activation")
    status: str = Field(
        description="Activation lifecycle state (DRAFT, APPROVED, CANARY, ACTIVE, PAUSED, ROLLED_BACK, EXPIRED)"
    )
    rollout_percentage: int = Field(
        description="Current traffic allocation percentage (0, 5, 10, 25, 50, 100)"
    )
    target_segment: dict[str, Any] | None = Field(
        default=None, description="Segment matching criteria"
    )
    model_version: str = Field(description="ML model version governing this activation")
    governance_version: str = Field(
        default="v1.0", description="Governance rules version"
    )
    effective_from: datetime = Field(description="Activation effective start timestamp")
    expires_at: datetime = Field(description="Activation expiration timestamp")
    approved_by: str | None = Field(
        default=None, description="Operator who approved the activation"
    )
    approved_at: datetime | None = Field(default=None, description="Approval timestamp")
    activated_by: str | None = Field(
        default=None, description="Admin who promoted activation to ACTIVE (100%)"
    )
    activated_at: datetime | None = Field(
        default=None, description="Promotion timestamp"
    )
    paused_by: str | None = Field(
        default=None, description="Operator who paused activation"
    )
    paused_at: datetime | None = Field(default=None, description="Pause timestamp")
    rolled_back_by: str | None = Field(
        default=None, description="Operator who rolled back activation"
    )
    rolled_back_at: datetime | None = Field(
        default=None, description="Rollback timestamp"
    )
    created_at: datetime = Field(description="Record creation timestamp")
    updated_at: datetime = Field(description="Last status modification timestamp")
    comparison: StrategyComparison | None = Field(
        default=None, description="Telemetry comparison between control & treatment"
    )
    health: RolloutHealth = Field(
        description="Automated rollout safety health evaluation"
    )
    notes: str | None = Field(
        default=None, description="Latest operator decision notes"
    )
    observational_disclaimer: str = Field(
        default=(
            "CONTROLLED CANARY EXPERIMENT — AI recommendations do not directly execute "
            "financial actions. Strategy eligibility is evaluated deterministically by the "
            "authoritative Policy Engine. Results reflect observational experimental evidence."
        ),
        description="Mandatory non-causal governance disclaimer",
    )


class PaginatedActivationsResponse(BaseModel):
    """Paginated collection of strategy activations with active proposal."""

    items: list[StrategyActivationResponse] = Field(
        default_factory=list, description="List of activation records"
    )
    total: int = Field(description="Total count of activation records")
    active_activation: StrategyActivationResponse | None = Field(
        default=None,
        description="Current active or canary activation if present",
    )
