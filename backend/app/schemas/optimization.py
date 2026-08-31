from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class ExpectedRecoveryValue(BaseModel):
    """Monetary expected recovery calculation in integer minor units (paise)."""

    model_config = ConfigDict(frozen=True)

    amount_at_risk: int = Field(
        ge=0, description="Total principal value at risk in integer paise"
    )
    recovery_probability: float = Field(
        ge=0.0, le=1.0, description="Model estimated recovery likelihood"
    )
    expected_recovery_value: int = Field(
        ge=0,
        description="Expected value = amount_at_risk * probability in integer paise",
    )


class StrategyPerformance(BaseModel):
    """Empirical performance metrics for a specific recovery action channel."""

    model_config = ConfigDict(frozen=True)

    action_type: str = Field(
        description="Recovery action type (e.g. RETRY_PAYMENT, SEND_PAYMENT_LINK)"
    )
    sample_size: int = Field(
        ge=0, description="Total resolved cases employing this action type"
    )
    recovered_count: int = Field(ge=0)
    failed_count: int = Field(ge=0)
    recovery_rate: float | None = Field(
        default=None, description="Proportion of cases successfully recovered"
    )
    average_recovery_probability: float | None = Field(default=None)
    average_confidence: float | None = Field(default=None)
    amount_at_risk: int = Field(ge=0, description="Total amount at risk in paise")
    amount_recovered: int = Field(ge=0, description="Total amount recovered in paise")
    recovery_amount_rate: float | None = Field(
        default=None, description="Ratio of amount recovered to amount at risk"
    )
    reliability: str = Field(
        description="'SUFFICIENT', 'LIMITED', or 'INSUFFICIENT_DATA'"
    )


class DelayPerformance(BaseModel):
    """Empirical recovery effectiveness across retry cadence delay intervals."""

    model_config = ConfigDict(frozen=True)

    delay_hours: int = Field(
        ge=0, description="Delay interval in hours (e.g. 2, 4, 12, 24)"
    )
    sample_size: int = Field(ge=0)
    recovered_count: int = Field(ge=0)
    recovery_rate: float | None = Field(default=None)
    average_recovery_probability: float | None = Field(default=None)
    amount_at_risk: int = Field(ge=0, description="Amount at risk in paise")
    amount_recovered: int = Field(ge=0, description="Amount recovered in paise")
    reliability: str = Field(
        description="'SUFFICIENT', 'LIMITED', or 'INSUFFICIENT_DATA'"
    )


class SegmentStrategyRecommendation(BaseModel):
    """Recommended champion recovery strategy for a specific operational or customer segment."""

    model_config = ConfigDict(frozen=True)

    segment_type: str = Field(
        description="'risk_tier', 'failure_reason', 'attempt_number', or 'amount_band'"
    )
    segment_value: str = Field(
        description="Value identifier (e.g. 'HIGH', 'insufficient_funds', '1', '₹1,000–₹5,000')"
    )
    sample_size: int = Field(ge=0)
    best_action_type: str | None = Field(default=None)
    best_delay_hours: int | None = Field(default=None)
    recovery_rate: float | None = Field(default=None)
    amount_at_risk: int = Field(ge=0, description="Segment amount at risk in paise")
    expected_recovery_value: int = Field(
        ge=0, description="Segment expected recovery value in paise"
    )
    reliability: str = Field(
        description="'SUFFICIENT', 'LIMITED', or 'INSUFFICIENT_DATA'"
    )
    recommendation_reason: str = Field(
        description="Deterministic justification for the recommendation"
    )


class OptimizationRecommendation(BaseModel):
    """Overall champion recovery strategy recommendation."""

    model_config = ConfigDict(frozen=True)

    action_type: str | None = Field(
        default=None, description="Recommended champion action type"
    )
    recommended_delay_hours: int | None = Field(
        default=None, description="Recommended retry delay in hours"
    )
    sample_size: int = Field(ge=0)
    recovery_probability: float | None = Field(default=None)
    recovery_rate: float | None = Field(default=None)
    average_confidence: float | None = Field(default=None)
    expected_recovery_value: int = Field(ge=0, description="Expected value in paise")
    confidence_level: str = Field(
        description="'SUFFICIENT', 'LIMITED', or 'INSUFFICIENT_DATA'"
    )
    recommendation_reason: str = Field(
        description="Deterministic explanation of selection criteria"
    )


class OptimizationFinding(BaseModel):
    """Deterministic analytical optimization finding or observation."""

    model_config = ConfigDict(frozen=True)

    code: str = Field(
        description="Finding code (e.g. INSUFFICIENT_DATA, STRATEGY_PERFORMING_WELL, DELAY_EFFECT_DETECTED)"
    )
    severity: str = Field(description="'INFO', 'POSITIVE', or 'WARNING'")
    message: str = Field(description="Human-readable optimization diagnostic message")


class StrategyOptimizationResponse(BaseModel):
    """Comprehensive intelligent recovery strategy optimization report."""

    model_config = ConfigDict(frozen=True)

    generated_at: datetime
    sample_size: int = Field(
        ge=0, description="Total resolved historical cases analyzed"
    )
    overall_recommendation: OptimizationRecommendation
    expected_recovery_value_summary: ExpectedRecoveryValue
    strategies: list[StrategyPerformance] = Field(default_factory=list)
    delay_analysis: list[DelayPerformance] = Field(default_factory=list)
    segment_recommendations: list[SegmentStrategyRecommendation] = Field(
        default_factory=list
    )
    diagnostic_findings: list[OptimizationFinding] = Field(default_factory=list)
