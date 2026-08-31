"""Pydantic schemas for causal experimentation, statistical testing, and decision intelligence (Phase 9H)."""

from pydantic import BaseModel, Field, field_validator


class PopulationDefinition(BaseModel):
    """Filters defining the eligible cohort population."""

    risk_tier: str | None = None
    failure_reason: str | None = None
    amount_band: str | None = None
    attempt_number: int | None = None
    model_version: str | None = None
    strategy_version: str | None = None


class ExperimentRequest(BaseModel):
    """Request payload to create a new causal experiment."""

    name: str = Field(..., min_length=3, max_length=120)
    description: str | None = None
    treatment_strategy: str = Field(..., min_length=2, max_length=64)
    control_strategy: str = Field(..., min_length=2, max_length=64)
    allocation_percentage: int = Field(
        default=50,
        description="Treatment traffic allocation percentage (50, 60, 70, 80, 90)",
    )
    population_definition: PopulationDefinition | None = None
    model_version: str | None = "v1.0"
    notes: str | None = None

    @field_validator("allocation_percentage")
    @classmethod
    def validate_allocation(cls, v: int) -> int:
        if v not in (50, 60, 70, 80, 90):
            raise ValueError(
                "allocation_percentage must be one of {50, 60, 70, 80, 90}"
            )
        return v


class ExperimentActionRequest(BaseModel):
    """Payload for experiment state transitions."""

    notes: str | None = None


class ExperimentCohortMetrics(BaseModel):
    """Empirical cohort statistics."""

    cohort_type: str
    sample_size: int
    recovered_count: int
    failed_count: int
    recovery_rate: float | None
    amount_at_risk_paise: int
    amount_recovered_paise: int
    financial_yield: float | None
    expected_recovery_value_paise: int
    mttr_hours: float | None
    failure_rate: float | None
    average_attempts: float | None


class CausalEffectEstimate(BaseModel):
    """Estimated treatment effects and financial yield impact."""

    absolute_treatment_effect: float | None = None
    relative_uplift_pct: float | None = None
    incremental_recovered_cases_estimate: float | None = None
    incremental_erv_paise: int | None = None


class StatisticalTestResult(BaseModel):
    """Hypothesis testing metrics and Wilson/Newcombe confidence bounds."""

    test_name: str = "TWO_PROPORTION_Z_TEST"
    test_statistic: float | None = None
    p_value: float | None = None
    alpha: float = 0.05
    statistically_significant: bool = False
    confidence_interval_low: float | None = None
    confidence_interval_high: float | None = None
    confidence_level: float = 0.95


class BalanceFeatureMetric(BaseModel):
    """Covariate balance metric across experimental cohorts."""

    feature_name: str
    control_dist: dict[str, float]
    treatment_dist: dict[str, float]
    standardized_difference: float
    status: str


class BalanceDiagnostics(BaseModel):
    """Randomization balance assessment across all covariates."""

    overall_status: str
    is_confounded: bool
    features: list[BalanceFeatureMetric]
    diagnostics: list[str]


class DataQualityReport(BaseModel):
    """Data quality and missing outcome telemetry."""

    data_quality_status: str
    missing_outcomes: int
    missing_predictions: int
    diagnostics: list[str]


class OverlapDiagnostics(BaseModel):
    """Multi-experiment interference and overlap detection."""

    has_overlap: bool
    conflicting_experiment_ids: list[str]
    diagnostics: list[str]


class StoppingDiagnostics(BaseModel):
    """Safety guardrail stopping rules."""

    stop_recommended: bool
    reasons: list[str]


class ExperimentDecisionResult(BaseModel):
    """Deterministic governance decision and causal evidence classification."""

    decision: str
    evidence_level: str
    statistically_significant: bool
    absolute_uplift: float | None
    p_value: float | None
    confidence_interval: dict[str, float | None]
    diagnostics: list[str]


class ExperimentAnalysisResponse(BaseModel):
    """Full causal and statistical evaluation of an experiment."""

    experiment_id: str
    experiment_name: str
    status: str
    allocation_percentage: int
    assignment_method: str = "SHA256_DETERMINISTIC"
    sample_size: int
    control_cohort: ExperimentCohortMetrics
    treatment_cohort: ExperimentCohortMetrics
    causal_effect: CausalEffectEstimate
    statistical_test: StatisticalTestResult
    balance_diagnostics: BalanceDiagnostics
    data_quality: DataQualityReport
    overlap_diagnostics: OverlapDiagnostics
    stopping_diagnostics: StoppingDiagnostics
    decision: ExperimentDecisionResult
    evaluated_at: str
    disclaimer: str


class ExperimentResponse(BaseModel):
    """DTO representing an experiment lifecycle entity."""

    experiment_id: str
    name: str
    description: str | None
    status: str
    treatment_strategy: str
    control_strategy: str
    allocation_percentage: int
    population_definition: PopulationDefinition
    model_version: str
    created_by: str
    created_at: str
    started_at: str | None
    ended_at: str | None
    runtime_hours: float | None
    sample_size: int
    notes: str | None
    observational_disclaimer: str


class PaginatedExperimentsResponse(BaseModel):
    """List response for experiments."""

    items: list[ExperimentResponse]
    total: int
    active_count: int
