from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class EvaluationEvidence(BaseModel):
    """Immutable evaluation metrics snapshot from Phase 9A."""

    model_config = ConfigDict(frozen=True)

    sample_size: int = Field(ge=0)
    accuracy: float | None = None
    precision: float | None = None
    recall: float | None = None
    f1_score: float | None = None
    brier_score: float | None = None


class GovernanceEvidence(BaseModel):
    """Immutable governance and drift snapshot from Phase 9B."""

    model_config = ConfigDict(frozen=True)

    model_health: str
    drift_status: str
    prediction_psi: float | None = None
    data_quality_status: str
    model_version: str


class OptimizationEvidence(BaseModel):
    """Immutable champion strategy optimization snapshot from Phase 9C."""

    model_config = ConfigDict(frozen=True)

    champion_strategy: str | None = None
    champion_recovery_rate: float | None = None
    champion_financial_yield: float | None = None
    champion_erv_paise: int | None = None
    strategy_sample_size: int = Field(ge=0)


class SimulationEvidence(BaseModel):
    """Immutable counterfactual simulation snapshot from Phase 9D."""

    model_config = ConfigDict(frozen=True)

    baseline_strategy: str
    alternative_strategy: str
    comparable_population_size: int = Field(ge=0)
    population_match_type: str
    baseline_recovery_rate: float | None = None
    alternative_recovery_rate: float | None = None
    rate_delta: float | None = None
    relative_uplift_pct: float | None = None
    incremental_erv_paise: int | None = None
    simulation_reliability: str


class EvidenceBundle(BaseModel):
    """Comprehensive, immutable evidence trail synthesized across intelligence phases."""

    model_config = ConfigDict(frozen=True)

    evaluation: EvaluationEvidence
    governance: GovernanceEvidence
    optimization: OptimizationEvidence
    simulation: SimulationEvidence


class StrategyRecommendationResponse(BaseModel):
    """Governed strategy recommendation with evidence bundle, confidence, and review lifecycle state."""

    model_config = ConfigDict(from_attributes=True)

    recommendation_id: str
    strategy_type: str
    retry_delay_hours: int
    status: str = Field(
        description="'NO_RECOMMENDATION', 'OBSERVATIONAL', 'REVIEW_REQUIRED', 'APPROVED', 'REJECTED', 'EXPIRED'"
    )
    created_at: datetime
    expires_at: datetime
    model_version: str
    sample_size: int
    reliability: str = Field(
        description="'SUFFICIENT', 'LIMITED', or 'INSUFFICIENT_DATA'"
    )
    recommendation_confidence: float = Field(
        ge=0.0,
        le=1.0,
        description="Deterministic synthesized recommendation confidence score",
    )
    confidence_level: str = Field(description="'HIGH', 'MEDIUM', or 'LOW'")
    baseline_recovery_rate: float | None = None
    alternative_recovery_rate: float | None = None
    rate_delta: float | None = None
    relative_uplift_pct: float | None = None
    baseline_erv_paise: int | None = None
    alternative_erv_paise: int | None = None
    incremental_erv_paise: int | None = None
    governance_status: str
    reasoning: str
    diagnostics: list[str] = Field(default_factory=list)
    evidence: EvidenceBundle
    reviewed_by: str | None = None
    reviewed_at: datetime | None = None
    review_notes: str | None = None
    observational_disclaimer: str = Field(
        default="OBSERVATIONAL / GOVERNED RECOMMENDATION — Approval records operator endorsement but does not execute or schedule financial actions."
    )


class RecommendationReviewRequest(BaseModel):
    """Payload for human operator approval or rejection."""

    notes: str | None = Field(
        default=None,
        max_length=512,
        description="Optional operator justification / review notes",
    )


class PaginatedRecommendationsResponse(BaseModel):
    """List of versioned strategy recommendations and active proposed recommendation."""

    items: list[StrategyRecommendationResponse]
    total: int
    active_recommendation: StrategyRecommendationResponse | None = None
