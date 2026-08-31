from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class GovernanceFinding(BaseModel):
    """Specific governance observation or anomaly finding."""

    model_config = ConfigDict(frozen=True)

    code: str = Field(
        description="Finding category code, e.g. PERFORMANCE_DEGRADATION, FEATURE_DRIFT"
    )
    severity: str = Field(description="INFO, WARNING, or CRITICAL")
    message: str = Field(
        description="Human-readable description of the governance finding"
    )
    metric_name: str | None = Field(
        default=None, description="Related metric name if applicable"
    )
    baseline_value: float | None = Field(default=None)
    recent_value: float | None = Field(default=None)
    delta: float | None = Field(default=None)


class PerformanceWindow(BaseModel):
    """Model classification and calibration performance within a specific time window."""

    model_config = ConfigDict(frozen=True)

    window_name: str = Field(
        description="Window identifier, e.g. 7d, 30d, 90d, historical"
    )
    window_days: int | None = Field(
        default=None, description="Duration in days, or None for historical"
    )
    sample_size: int = Field(
        ge=0, description="Total resolved cases with predictions in this window"
    )
    accuracy: float | None = Field(default=None)
    precision: float | None = Field(default=None)
    recall: float | None = Field(default=None)
    f1_score: float | None = Field(default=None)
    brier_score: float | None = Field(default=None)
    recovery_rate: float | None = Field(default=None)


class PerformanceComparison(BaseModel):
    """Comparative performance delta between historical baseline and recent operational window."""

    model_config = ConfigDict(frozen=True)

    baseline_window: str = Field(default="historical")
    recent_window: str = Field(default="30d")
    baseline_sample_size: int = Field(ge=0)
    recent_sample_size: int = Field(ge=0)
    accuracy_delta: float | None = Field(default=None)
    precision_delta: float | None = Field(default=None)
    recall_delta: float | None = Field(default=None)
    f1_delta: float | None = Field(default=None)
    brier_delta: float | None = Field(
        default=None,
        description="Positive delta indicates worse Brier score; negative indicates improvement",
    )
    recovery_rate_delta: float | None = Field(default=None)


class FeatureDrift(BaseModel):
    """Population Stability Index (PSI) and distribution shift for a specific feature."""

    model_config = ConfigDict(frozen=True)

    feature_name: str
    feature_type: str = Field(description="'numerical' or 'categorical'")
    psi: float | None = Field(default=None, description="Population Stability Index")
    drift_level: str = Field(
        description="'LOW', 'MODERATE', 'SIGNIFICANT', or 'INSUFFICIENT_DATA'"
    )
    reference_sample_size: int = Field(ge=0)
    recent_sample_size: int = Field(ge=0)
    details: dict[str, Any] = Field(default_factory=dict)


class PredictionBucketDrift(BaseModel):
    """Drift within a specific probability bucket."""

    model_config = ConfigDict(frozen=True)

    bucket_min: float
    bucket_max: float
    historical_percentage: float | None = Field(default=None)
    recent_percentage: float | None = Field(default=None)
    delta: float | None = Field(default=None)


class PredictionDistributionDrift(BaseModel):
    """Shift in model predicted probability distribution over time."""

    model_config = ConfigDict(frozen=True)

    psi: float | None = Field(default=None)
    drift_level: str = Field(
        description="'LOW', 'MODERATE', 'SIGNIFICANT', or 'INSUFFICIENT_DATA'"
    )
    buckets: list[PredictionBucketDrift] = Field(default_factory=list)


class OutcomeDrift(BaseModel):
    """Empirical recovery outcome rate shift between historical and recent periods."""

    model_config = ConfigDict(frozen=True)

    historical_recovery_rate: float | None = Field(default=None)
    recent_recovery_rate: float | None = Field(default=None)
    delta: float | None = Field(default=None)
    drift_level: str = Field(
        description="'LOW', 'MODERATE', 'SIGNIFICANT', or 'INSUFFICIENT_DATA'"
    )


class CalibrationBucketDrift(BaseModel):
    """Calibration error shift for a specific predicted probability bucket."""

    model_config = ConfigDict(frozen=True)

    bucket_min: float
    bucket_max: float
    historical_pred_avg: float | None = Field(default=None)
    historical_recovery_rate: float | None = Field(default=None)
    historical_calibration_error: float | None = Field(default=None)
    recent_pred_avg: float | None = Field(default=None)
    recent_recovery_rate: float | None = Field(default=None)
    recent_calibration_error: float | None = Field(default=None)
    calibration_error_delta: float | None = Field(default=None)


class ModelVersionSummary(BaseModel):
    """Historical performance footprint of a specific registered model version."""

    model_config = ConfigDict(frozen=True)

    model_name: str
    model_version: str
    sample_size: int = Field(ge=0)
    first_seen: datetime | None = Field(default=None)
    last_seen: datetime | None = Field(default=None)
    accuracy: float | None = Field(default=None)
    brier_score: float | None = Field(default=None)
    recovery_rate: float | None = Field(default=None)


class ModelVersionComparison(BaseModel):
    """Comparative performance evidence between two distinct model versions."""

    model_config = ConfigDict(frozen=True)

    baseline_version: str
    comparison_version: str
    baseline_sample_size: int = Field(ge=0)
    comparison_sample_size: int = Field(ge=0)
    accuracy_delta: float | None = Field(default=None)
    f1_delta: float | None = Field(default=None)
    brier_delta: float | None = Field(default=None)
    evidence_statement: str = Field(description="Neutral comparative finding statement")


class DataQualitySummary(BaseModel):
    """Integrity and validity audit of recorded model prediction vectors."""

    model_config = ConfigDict(frozen=True)

    total_predictions: int = Field(ge=0)
    valid_predictions: int = Field(ge=0)
    invalid_predictions: int = Field(ge=0)
    missing_feature_vectors: int = Field(ge=0)
    missing_model_versions: int = Field(ge=0)
    invalid_probability_count: int = Field(ge=0)
    missing_timestamps: int = Field(ge=0)


class ModelGovernanceResponse(BaseModel):
    """Comprehensive, read-only model governance, drift, and intelligence health report."""

    model_config = ConfigDict(frozen=True)

    status: str = Field(
        description="'HEALTHY', 'WARNING', 'DEGRADED', or 'INSUFFICIENT_DATA'"
    )
    model_name: str
    model_version: str
    sample_size: int = Field(ge=0)
    minimum_required_sample_size: int = Field(ge=1, default=30)
    first_prediction_at: datetime | None = Field(default=None)
    last_prediction_at: datetime | None = Field(default=None)
    performance_windows: list[PerformanceWindow] = Field(default_factory=list)
    performance_comparison: PerformanceComparison
    feature_drift: list[FeatureDrift] = Field(default_factory=list)
    prediction_drift: PredictionDistributionDrift
    outcome_drift: OutcomeDrift
    calibration_drift: list[CalibrationBucketDrift] = Field(default_factory=list)
    model_versions: list[ModelVersionSummary] = Field(default_factory=list)
    version_comparisons: list[ModelVersionComparison] = Field(default_factory=list)
    data_quality: DataQualitySummary
    findings: list[GovernanceFinding] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    critical_findings: list[str] = Field(default_factory=list)
    generated_at: datetime
