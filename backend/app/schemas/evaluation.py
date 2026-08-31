from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class ModelMetadata(BaseModel):
    """Metadata identifying the evaluated ML and decision models."""

    model_config = ConfigDict(frozen=True)

    model_name: str = Field(description="Name of the prediction model")
    model_version: str = Field(description="Version of the prediction model")


class ClassificationMetrics(BaseModel):
    """Confusion matrix and classification performance metrics."""

    model_config = ConfigDict(frozen=True)

    sample_size: int = Field(ge=0, description="Total resolved cases evaluated")
    threshold: float = Field(
        default=0.50, description="Binary classification decision threshold"
    )
    true_positive: int = Field(
        ge=0, description="Predicted recovery & actually recovered"
    )
    false_positive: int = Field(
        ge=0, description="Predicted recovery & failed to recover"
    )
    true_negative: int = Field(
        ge=0, description="Predicted failure & failed to recover"
    )
    false_negative: int = Field(
        ge=0, description="Predicted failure & actually recovered"
    )
    accuracy: float | None = Field(
        default=None, description="Proportion of correct predictions (TP + TN) / total"
    )
    precision: float | None = Field(
        default=None, description="Positive predictive value TP / (TP + FP)"
    )
    recall: float | None = Field(
        default=None, description="Sensitivity / true positive rate TP / (TP + FN)"
    )
    f1_score: float | None = Field(
        default=None, description="Harmonic mean of precision and recall"
    )
    brier_score: float | None = Field(
        default=None,
        description="Mean squared error of probabilities vs binary outcomes",
    )


class CalibrationBucket(BaseModel):
    """Probability calibration bucket comparing predicted probability against empirical recovery rate."""

    model_config = ConfigDict(frozen=True)

    bucket_min: float = Field(ge=0.0, le=1.0)
    bucket_max: float = Field(ge=0.0, le=1.0)
    sample_size: int = Field(ge=0)
    predicted_probability_avg: float | None = Field(default=None)
    actual_recovery_rate: float | None = Field(default=None)
    calibration_error: float | None = Field(default=None)


class ActionAttributionItem(BaseModel):
    """Recovery outcome attribution grouped by AI proposed action type."""

    model_config = ConfigDict(frozen=True)

    action_type: str = Field(description="Recovery action category proposed by AI")
    sample_size: int = Field(ge=0)
    recovered_count: int = Field(ge=0)
    failed_count: int = Field(ge=0)
    recovery_rate: float | None = Field(default=None)
    average_confidence: float | None = Field(default=None)
    average_recovery_probability: float | None = Field(default=None)


class ConfidenceOutcomeMetrics(BaseModel):
    """Relationship between AI confidence scores and actual recovery outcomes."""

    model_config = ConfigDict(frozen=True)

    sample_size: int = Field(ge=0)
    average_confidence_recovered: float | None = Field(default=None)
    average_confidence_failed: float | None = Field(default=None)
    confidence_difference: float | None = Field(default=None)
    correlation: float | None = Field(
        default=None,
        description="Point-biserial correlation between confidence and recovery",
    )


class PolicyAlignmentItem(BaseModel):
    """Recovery outcomes grouped by deterministic policy evaluation result."""

    model_config = ConfigDict(frozen=True)

    policy_outcome: str = Field(description="ALLOWED, BLOCKED, or HUMAN_REVIEW")
    sample_size: int = Field(ge=0)
    recovered_count: int = Field(ge=0)
    failed_count: int = Field(ge=0)
    recovery_rate: float | None = Field(default=None)


class RiskSegmentItem(BaseModel):
    """Recovery performance segmented by customer risk tier."""

    model_config = ConfigDict(frozen=True)

    risk_tier: str = Field(description="LOW, STANDARD, HIGH, BLOCKED")
    sample_size: int = Field(ge=0)
    recovered_count: int = Field(ge=0)
    failed_count: int = Field(ge=0)
    recovery_rate: float | None = Field(default=None)
    average_recovery_probability: float | None = Field(default=None)


class FailureReasonSegmentItem(BaseModel):
    """Recovery performance segmented by initial failure reason."""

    model_config = ConfigDict(frozen=True)

    failure_reason: str = Field(description="Initial gateway/issuer failure code")
    sample_size: int = Field(ge=0)
    recovered_count: int = Field(ge=0)
    failed_count: int = Field(ge=0)
    recovery_rate: float | None = Field(default=None)
    average_recovery_probability: float | None = Field(default=None)


class ActionDurationItem(BaseModel):
    """Recovery time latency grouped by proposed action type."""

    model_config = ConfigDict(frozen=True)

    action_type: str
    sample_size: int = Field(ge=0)
    average_hours: float | None = Field(default=None)
    median_hours: float | None = Field(default=None)


class PriorityDurationItem(BaseModel):
    """Recovery time latency grouped by ML prediction priority."""

    model_config = ConfigDict(frozen=True)

    priority: str
    sample_size: int = Field(ge=0)
    average_hours: float | None = Field(default=None)
    median_hours: float | None = Field(default=None)


class RecoveryDurationMetrics(BaseModel):
    """Mean and median time to recovery metrics (hours) for successfully recovered cases."""

    model_config = ConfigDict(frozen=True)

    sample_size: int = Field(
        ge=0, description="Total successfully recovered cases evaluated"
    )
    overall_average_hours: float | None = Field(default=None)
    overall_median_hours: float | None = Field(default=None)
    by_action_type: list[ActionDurationItem] = Field(default_factory=list)
    by_priority: list[PriorityDurationItem] = Field(default_factory=list)


class IntelligenceEvaluationResponse(BaseModel):
    """Comprehensive recovery intelligence evaluation report."""

    model_config = ConfigDict(frozen=True)

    generated_at: datetime
    model: ModelMetadata
    classification: ClassificationMetrics
    calibration: list[CalibrationBucket] = Field(default_factory=list)
    action_attribution: list[ActionAttributionItem] = Field(default_factory=list)
    confidence_outcomes: ConfidenceOutcomeMetrics
    policy_alignment: list[PolicyAlignmentItem] = Field(default_factory=list)
    risk_segments: list[RiskSegmentItem] = Field(default_factory=list)
    failure_reason_segments: list[FailureReasonSegmentItem] = Field(
        default_factory=list
    )
    recovery_duration: RecoveryDurationMetrics
