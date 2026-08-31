from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class PromotionCheckItem(BaseModel):
    """Evaluation result for an individual promotion safety gate rule."""

    rule: str = Field(
        description="Safety rule identifier (e.g. MIN_SAMPLE_SIZE, POSITIVE_UPLIFT)"
    )
    passed: bool = Field(description="True if safety criterion is fully satisfied")
    value: Any | None = Field(
        default=None, description="Observed empirical metric value"
    )
    required: Any | None = Field(
        default=None, description="Required threshold for promotion readiness"
    )
    message: str | None = Field(
        default=None, description="Human-readable explanation of check outcome"
    )


class PromotionReadinessResponse(BaseModel):
    """Comprehensive readiness assessment report evaluating strategy promotion eligibility."""

    activation_id: str = Field(description="Unique public activation identifier")
    strategy_type: str = Field(description="Recovery strategy action type")
    strategy_version: str = Field(
        default="strategy-v1.0", description="Immutable strategy version tag"
    )
    model_version: str = Field(description="Governing ML model version")
    eligible: bool = Field(description="True only if all 8 safety gates are satisfied")
    status: str = Field(
        description="Promotion status (PROMOTION_READY, PROMOTION_BLOCKED, NOT_ELIGIBLE)"
    )
    sample_size: int = Field(
        description="Total empirical sample size evaluated across cohorts"
    )
    treatment_recovery_rate: float | None = Field(
        default=None, description="Observed treatment recovery rate"
    )
    control_recovery_rate: float | None = Field(
        default=None, description="Observed control baseline recovery rate"
    )
    absolute_uplift: float | None = Field(
        default=None, description="Treatment minus control recovery rate delta"
    )
    relative_uplift_pct: float | None = Field(
        default=None, description="Percentage relative recovery uplift"
    )
    incremental_erv_paise: int | None = Field(
        default=None, description="Incremental Expected Recovery Value in integer paise"
    )
    confidence_interval_low: float | None = Field(
        default=None, description="95% CI lower bound"
    )
    confidence_interval_high: float | None = Field(
        default=None, description="95% CI upper bound"
    )
    model_health: str = Field(
        description="Governing ML model health status (HEALTHY, WARNING, DEGRADED)"
    )
    data_quality: str = Field(description="Data quality status from model governance")
    rollback_recommended: bool = Field(
        description="True if rollback is recommended on active canary"
    )
    checks: list[PromotionCheckItem] = Field(
        default_factory=list,
        description="Detailed breakdown of all 8 promotion safety rules",
    )
    blockers: list[str] = Field(
        default_factory=list,
        description="Explicit blocker codes preventing production promotion",
    )
    evaluated_at: datetime = Field(
        description="Timestamp when promotion readiness was evaluated"
    )
    disclaimer: str = Field(
        default=(
            "PROMOTION GATE EVALUATION — Observational safety assessment only. Promotion evaluates "
            "empirical evidence against deterministic guardrails. It does NOT move funds or execute transactions."
        ),
        description="Mandatory non-causal governance disclaimer",
    )


class PromoteProductionRequest(BaseModel):
    """Operator/Admin metadata submitted with a promotion request."""

    reason: str | None = Field(
        default=None,
        max_length=512,
        description="Audited operator rationale for promotion",
    )
    notes: str | None = Field(
        default=None, max_length=512, description="Additional governance decision notes"
    )


class ProductionMonitoringResponse(BaseModel):
    """Continuous telemetry monitoring report for active production recovery strategy."""

    status: str = Field(
        description="Overall production strategy health status (HEALTHY, WARNING, DEGRADED, ROLLBACK_RECOMMENDED, NO_ACTIVE_STRATEGY)"
    )
    strategy_id: str | None = Field(
        default=None, description="Active strategy identifier"
    )
    strategy_name: str | None = Field(
        default=None, description="Active recovery action type name"
    )
    strategy_version: str | None = Field(
        default="strategy-v1.0", description="Immutable strategy version tag"
    )
    model_version: str | None = Field(
        default=None, description="Governing ML model version"
    )
    activation_id: str | None = Field(
        default=None, description="Associated activation identifier"
    )
    recommendation_id: str | None = Field(
        default=None, description="Associated recommendation identifier"
    )
    rollout_percentage: int = Field(
        default=0, description="Active traffic rollout percentage"
    )
    sample_size: int = Field(
        default=0, description="Total cases evaluated across cohorts"
    )
    treatment_sample_size: int = Field(
        default=0, description="Cases in treatment cohort"
    )
    control_sample_size: int = Field(default=0, description="Cases in control cohort")
    recovery_rate: float | None = Field(
        default=None, description="Production recovery rate"
    )
    control_recovery_rate: float | None = Field(
        default=None, description="Control baseline recovery rate"
    )
    absolute_uplift: float | None = Field(
        default=None, description="Absolute recovery rate uplift"
    )
    relative_uplift_pct: float | None = Field(
        default=None, description="Percentage relative recovery uplift"
    )
    incremental_erv_paise: int | None = Field(
        default=None, description="Incremental Expected Recovery Value in integer paise"
    )
    financial_yield: float | None = Field(
        default=None, description="Monetary yield ratio (recovered / risk)"
    )
    mttr_hours: float | None = Field(
        default=None, description="Mean time to recovery in decimal hours"
    )
    model_health: str = Field(
        default="HEALTHY", description="ML model governance health"
    )
    prediction_psi: float | None = Field(
        default=None, description="Population Stability Index drift"
    )
    drift_status: str = Field(
        default="LOW", description="Prediction drift classification"
    )
    rollback_recommended: bool = Field(
        default=False,
        description="True if automatic guardrails recommend strategy rollback",
    )
    diagnostics: list[str] = Field(
        default_factory=list,
        description="Automated continuous monitoring safety diagnostics",
    )
    promoted_at: datetime | None = Field(
        default=None, description="Promotion timestamp"
    )
    promoted_by: str | None = Field(
        default=None, description="Admin who authorized production promotion"
    )
    last_evaluated: datetime = Field(
        description="Timestamp when monitoring was evaluated"
    )
    disclaimer: str = Field(
        default=(
            "CONTINUOUS PRODUCTION MONITORING — Observational strategy telemetry. "
            "PolicyEngine remains authoritative. System does not autonomously mutate financial state."
        ),
        description="Mandatory non-causal governance disclaimer",
    )
