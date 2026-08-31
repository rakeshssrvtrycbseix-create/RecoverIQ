from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class SimulationRequest(BaseModel):
    """Parameters for counterfactual recovery strategy simulation."""

    model_config = ConfigDict(frozen=True)

    current_action_type: str = Field(
        default="RETRY_PAYMENT",
        description="Current/baseline recovery action type (e.g. RETRY_PAYMENT)",
    )
    current_delay_hours: int = Field(
        default=12,
        ge=0,
        le=168,
        description="Current/baseline retry delay cadence in hours",
    )
    alternative_action_type: str = Field(
        default="SEND_PAYMENT_LINK",
        description="Alternative candidate recovery action type (e.g. SEND_PAYMENT_LINK)",
    )
    alternative_delay_hours: int = Field(
        default=4,
        ge=0,
        le=168,
        description="Alternative candidate retry delay cadence in hours",
    )
    risk_tier: str | None = Field(
        default=None,
        description="Optional customer risk tier filter (LOW, STANDARD, HIGH, BLOCKED)",
    )
    failure_reason: str | None = Field(
        default=None,
        description="Optional failure reason code filter (e.g. insufficient_funds, network_timeout)",
    )
    attempt_number: int | None = Field(
        default=None,
        ge=1,
        le=10,
        description="Optional sequential failure attempt number (1, 2, 3, 4)",
    )
    amount_band: str | None = Field(
        default=None,
        description="Optional amount band filter ('< ₹1,000', '₹1,000–₹5,000', '₹5,000–₹10,000', '₹10,000–₹50,000', '> ₹50,000')",
    )
    amount_at_risk_paise: int | None = Field(
        default=None,
        ge=0,
        description="Hypothetical principal amount at risk in integer paise for ERV modeling",
    )


class StrategyMetrics(BaseModel):
    """Observed empirical and model metrics for a specific strategy in a comparable population."""

    model_config = ConfigDict(frozen=True)

    action_type: str
    delay_hours: int
    sample_size: int = Field(
        ge=0, description="Number of historical comparable observations"
    )
    recovered_count: int = Field(ge=0)
    failed_count: int = Field(ge=0)
    recovery_rate: float | None = Field(
        default=None, description="Observed recovery rate (0.0 to 1.0)"
    )
    financial_yield: float | None = Field(
        default=None, description="Ratio of recovered paise to at-risk paise"
    )
    average_recovery_probability: float | None = Field(default=None)
    amount_at_risk_paise: int = Field(
        ge=0, description="Total principal value in integer paise"
    )
    amount_recovered_paise: int = Field(
        ge=0, description="Total recovered value in integer paise"
    )
    expected_recovery_value_paise: int | None = Field(
        default=None, description="Estimated ERV in integer paise"
    )
    reliability: str = Field(
        description="'SUFFICIENT', 'LIMITED', or 'INSUFFICIENT_DATA'"
    )


class EstimatedStrategyUplift(BaseModel):
    """Estimated differential impact between alternative and current recovery strategies."""

    model_config = ConfigDict(frozen=True)

    recovery_rate_delta: float | None = Field(
        default=None,
        description="Absolute difference in recovery rate (alternative - current)",
    )
    relative_uplift_pct: float | None = Field(
        default=None,
        description="Percentage change in recovery rate ((alt - cur) / cur * 100)",
    )
    financial_yield_delta: float | None = Field(
        default=None, description="Difference in financial recovery yield"
    )
    estimated_incremental_erv_paise: int | None = Field(
        default=None,
        description="Estimated incremental Expected Recovery Value in integer paise",
    )
    confidence_assessment: str = Field(
        description="Assessment of evidence strength ('STRONG_POSITIVE_EVIDENCE', 'MODERATE_EVIDENCE', 'COMPARABLE_PERFORMANCE', 'NEGATIVE_OUTCOME_INDICATED', 'INSUFFICIENT_DATA')"
    )


class ComparablePopulationMetadata(BaseModel):
    """Metadata describing the historical reference dataset and filtering constraints used."""

    model_config = ConfigDict(frozen=True)

    total_cases_analyzed: int = Field(ge=0)
    matching_criteria: dict[str, Any] = Field(default_factory=dict)
    segmentation_level_used: str = Field(
        description="'EXACT_MATCH', 'RELAXED_MATCH', or 'GLOBAL_BASELINE'"
    )
    filter_summary: str


class SimulationDiagnostic(BaseModel):
    """Diagnostic note explaining sample constraints, fallback behavior, or empirical anomalies."""

    model_config = ConfigDict(frozen=True)

    code: str = Field(
        description="Diagnostic identifier (e.g. INSUFFICIENT_SAMPLE, FALLBACK_SEGMENTATION, STRONG_SIGNAL)"
    )
    severity: str = Field(description="'INFO', 'POSITIVE', or 'WARNING'")
    message: str


class CounterfactualSimulationResponse(BaseModel):
    """Comprehensive counterfactual recovery simulation report."""

    model_config = ConfigDict(frozen=True)

    generated_at: datetime
    request_parameters: SimulationRequest
    population: ComparablePopulationMetadata
    current_strategy: StrategyMetrics
    alternative_strategy: StrategyMetrics
    estimated_uplift: EstimatedStrategyUplift
    diagnostics: list[SimulationDiagnostic] = Field(default_factory=list)
    observational_disclaimer: str = Field(
        default="OBSERVATIONAL SIMULATION — This analysis is based on historical outcomes. It does not establish causal effects or guarantee future recovery. No financial action will be executed."
    )
