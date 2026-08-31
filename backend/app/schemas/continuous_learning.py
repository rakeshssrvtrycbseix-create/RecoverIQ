from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import (
    ContinuousLearningQualityGateCode,
    LearningTriggerType,
    ModelEvolutionDecision,
    RetrainingEligibilityDecision,
    TrainingRunStatus,
)


class DatasetVersion(BaseModel):
    """Immutable snapshot representation of a governed resolved training dataset."""

    model_config = ConfigDict(from_attributes=True)

    dataset_id: str
    dataset_version: str
    sample_count: int
    feature_schema_version: str
    label_definition: str
    first_case_timestamp: str | None = None
    last_case_timestamp: str | None = None
    source_case_count: int
    sha256_checksum: str
    positive_count: int
    negative_count: int
    class_balance: float
    created_at: str


class LearningTrigger(BaseModel):
    """Individual automated continuous learning trigger evaluation."""

    model_config = ConfigDict(from_attributes=True)

    trigger_type: LearningTriggerType
    triggered: bool
    severity: str
    threshold: Any = None
    observed_value: Any = None
    evidence: dict[str, Any] = Field(default_factory=dict)


class LearningDiagnostic(BaseModel):
    """Diagnostic detail or warning emitted during continuous learning monitoring."""

    model_config = ConfigDict(from_attributes=True)

    category: str
    code: str
    message: str
    severity: str
    timestamp: str


class RetrainingEligibility(BaseModel):
    """Deterministic evaluation of retraining eligibility and trigger telemetry."""

    model_config = ConfigDict(from_attributes=True)

    decision: RetrainingEligibilityDecision
    is_eligible: bool
    primary_trigger: LearningTriggerType | None = None
    primary_reason: str
    triggers: list[LearningTrigger] = Field(default_factory=list)
    diagnostics: list[LearningDiagnostic] = Field(default_factory=list)
    evaluated_at: str


class TrainingRun(BaseModel):
    """Immutable audit-backed record of an offline model training run."""

    model_config = ConfigDict(from_attributes=True)

    training_run_id: str
    dataset_id: str
    dataset_version: str
    model_version: str
    algorithm: str
    feature_schema: str
    training_sample_size: int
    validation_sample_size: int
    dataset_checksum: str
    artifact_checksum: str
    started_at: str
    completed_at: str | None = None
    status: TrainingRunStatus
    validation_result: dict[str, Any] | None = None
    governance_result: dict[str, Any] | None = None
    notes: str | None = None


class ModelLineageNode(BaseModel):
    """Complete provenance and lifecycle traceability node for a machine learning model."""

    model_config = ConfigDict(from_attributes=True)

    model_version: str
    parent_model_version: str | None = None
    dataset_version: str
    dataset_checksum: str
    artifact_checksum: str
    training_run_id: str
    validation_status: str
    governance_status: str
    deployment_status: str
    created_at: str


class ContinuousLearningSafetyGateResult(BaseModel):
    """Individual continuous learning readiness quality gate result."""

    model_config = ConfigDict(from_attributes=True)

    gate_code: ContinuousLearningQualityGateCode
    passed: bool
    observed_value: Any
    threshold: Any
    explanation: str


class ContinuousLearningReadiness(BaseModel):
    """Comprehensive 14-gate safety report governing model evolution."""

    model_config = ConfigDict(from_attributes=True)

    decision: ModelEvolutionDecision
    can_retrain: bool
    gates: list[ContinuousLearningSafetyGateResult] = Field(default_factory=list)
    blocking_reasons: list[str] = Field(default_factory=list)
    recommendations: list[str] = Field(default_factory=list)
    evaluated_at: str


class ContinuousLearningSummary(BaseModel):
    """Top-level telemetry and status for continuous learning dashboard."""

    model_config = ConfigDict(from_attributes=True)

    active_champion_version: str
    latest_dataset_version: str
    total_dataset_samples: int
    new_resolved_cases_since_last_training: int
    last_training_run_at: str | None = None
    retraining_eligibility: RetrainingEligibility
    evolution_decision: ModelEvolutionDecision
    recent_training_runs_count: int
    registered_datasets_count: int
    governance_disclaimer: str


class ManualTrainingTriggerRequest(BaseModel):
    """Request payload for initiating an offline governed training run."""

    dataset_version: str | None = None
    learning_rate: float | None = 0.05
    epochs: int | None = 50
    notes: str | None = None


class PaginatedDatasetsResponse(BaseModel):
    """Paginated collection of registered dataset versions."""

    items: list[DatasetVersion]
    total: int


class PaginatedTrainingRunsResponse(BaseModel):
    """Paginated collection of offline training runs."""

    items: list[TrainingRun]
    total: int


class ModelLineageResponse(BaseModel):
    """Lineage response showing model derivation tree."""

    lineage: list[ModelLineageNode]
    active_champion_version: str
