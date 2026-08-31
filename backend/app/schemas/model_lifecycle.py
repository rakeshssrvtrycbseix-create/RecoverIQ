from pydantic import BaseModel, Field

from app.models.enums import (
    ComparisonStatus,
    ModelLifecycleStatus,
    ModelQualityGateCode,
    ModelScorecardRecommendation,
)


class TrainingDatasetMetadata(BaseModel):
    """Metadata describing a historical training dataset."""

    sample_size: int = Field(..., ge=0)
    positive_count: int = Field(..., ge=0)
    negative_count: int = Field(..., ge=0)
    class_balance: float = Field(..., ge=0.0, le=1.0)
    feature_names: list[str]
    feature_schema_version: str = "v1"
    dataset_hash: str
    temporal_range_start: str | None = None
    temporal_range_end: str | None = None


class TrainingDatasetSplit(BaseModel):
    """Metadata describing deterministic train/validation dataset partitioning."""

    training_sample_size: int = Field(..., ge=0)
    validation_sample_size: int = Field(..., ge=0)
    training_dataset_hash: str
    validation_dataset_hash: str
    split_ratio: float = Field(0.70, ge=0.0, le=1.0)


class ModelTrainingRequest(BaseModel):
    """Request payload to initiate offline candidate model training."""

    model_name: str = Field("recovery_probability", min_length=1)
    parent_version: str = Field("v1.0", min_length=1)
    learning_rate: float = Field(0.05, gt=0.0, le=1.0)
    epochs: int = Field(50, ge=1, le=1000)
    notes: str | None = Field(None, max_length=500)


class ModelApprovalRequest(BaseModel):
    """Request payload to approve a model candidate into PROMOTION_READY."""

    notes: str | None = Field(None, max_length=500)


class ModelRejectionRequest(BaseModel):
    """Request payload to reject a candidate model."""

    reason: str = Field(..., min_length=1, max_length=500)


class ModelMetricsSnapshot(BaseModel):
    """Evaluation metrics for a model on a dataset."""

    sample_size: int = Field(..., ge=0)
    accuracy: float = Field(..., ge=0.0, le=1.0)
    precision: float = Field(..., ge=0.0, le=1.0)
    recall: float = Field(..., ge=0.0, le=1.0)
    f1_score: float = Field(..., ge=0.0, le=1.0)
    brier_score: float = Field(..., ge=0.0, le=1.0)
    calibration_error: float = Field(..., ge=0.0, le=1.0)
    roc_auc: float | None = Field(None, ge=0.0, le=1.0)
    pr_auc: float | None = Field(None, ge=0.0, le=1.0)
    log_loss: float | None = Field(None, ge=0.0)


class ModelQualityGateResult(BaseModel):
    """Individual validation quality gate evaluation."""

    gate_code: ModelQualityGateCode
    passed: bool
    observed_value: str | float | None = None
    threshold: str | float | None = None
    explanation: str


class MetricDelta(BaseModel):
    """Comparison metric delta between challenger and champion."""

    metric_name: str
    champion_value: float
    challenger_value: float
    delta: float
    status: ComparisonStatus


class ChampionChallengerComparison(BaseModel):
    """Side-by-side comparison between champion and challenger models."""

    champion_version: str
    challenger_version: str
    metrics_deltas: list[MetricDelta]
    overall_status: ComparisonStatus


class ModelScorecardResponse(BaseModel):
    """Comprehensive champion-challenger scorecard and governance recommendation."""

    model_name: str
    challenger_version: str
    parent_champion_version: str
    lifecycle_status: ModelLifecycleStatus
    champion_metrics: ModelMetricsSnapshot
    challenger_metrics: ModelMetricsSnapshot
    comparison: ChampionChallengerComparison
    gates: list[ModelQualityGateResult]
    recommendation: ModelScorecardRecommendation
    confidence: float = Field(..., ge=0.0, le=1.0)
    evidence_level: str
    dataset_metadata: TrainingDatasetMetadata
    training_split: TrainingDatasetSplit
    model_artifact_hash: str
    created_at: str
    evaluated_at: str
    disclaimer: str = "Offline governed machine learning evaluation. Approval does not authorize direct financial execution."


class ModelSummaryResponse(BaseModel):
    """Summary of a model registered in the governed model registry."""

    model_name: str
    model_version: str
    lifecycle_status: ModelLifecycleStatus
    model_type: str = "CALIBRATED_LOGISTIC_REGRESSION"
    feature_schema_version: str = "v1"
    training_sample_size: int = Field(0, ge=0)
    validation_sample_size: int = Field(0, ge=0)
    training_started_at: str | None = None
    validation_completed_at: str | None = None
    created_at: str
    approved_at: str | None = None
    activated_at: str | None = None
    retired_at: str | None = None
    training_dataset_hash: str
    model_artifact_hash: str
    parent_model_version: str | None = None
    approval_actor: str | None = None
    rejection_reason: str | None = None
    metrics_snapshot: ModelMetricsSnapshot | None = None
    recommendation: ModelScorecardRecommendation | None = None


class PaginatedModelsResponse(BaseModel):
    """Paginated list of models in the model registry."""

    items: list[ModelSummaryResponse]
    total: int = Field(..., ge=0)
    active_champion_version: str
    promotion_ready_version: str | None = None
