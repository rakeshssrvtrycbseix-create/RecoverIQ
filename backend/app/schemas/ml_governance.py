"""Pydantic schemas for Phase 10J: AI/ML Governance, Model Risk Management,

Explainability, Drift Detection & Responsible AI Control Plane.
"""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import (
    BiasStatus,
    CalibrationStatus,
    DriftStatus,
    ExplainabilityStatus,
    MLGateId,
    MLGateStatus,
    MLGlobalState,
    MLIncidentSeverity,
    MLIncidentStatus,
    ModelApprovalStatus,
    ModelDeploymentStatus,
    ModelEvaluationType,
    ModelHealth,
    ModelLifecycleState,
    ModelRiskCategory,
    ModelRiskLevel,
    PromotionRecommendation,
    RollbackReadinessStatus,
)


class ModelRegistryEntry(BaseModel):
    """Model catalog entry in the deterministic Model Registry."""

    model_config = ConfigDict(frozen=True)

    model_id: str = Field(
        ..., description="Unique model identifier, e.g. recovery_probability"
    )
    model_name: str = Field(..., description="Human-readable model name")
    model_family: str = Field(
        ...,
        description="Model architecture family, e.g. LogisticRegression, GradientBoostedTrees",
    )
    owner_role: str = Field(
        default="ML_ENGINEERING",
        description="Owner role responsible for model governance",
    )
    purpose: str = Field(
        ..., description="Deterministic business purpose and decision context"
    )
    lifecycle_state: ModelLifecycleState = Field(
        default=ModelLifecycleState.PRODUCTION, description="Current lifecycle state"
    )
    risk_level: ModelRiskLevel = Field(
        default=ModelRiskLevel.LOW, description="Aggregated model risk level"
    )
    health: ModelHealth = Field(
        default=ModelHealth.EXCELLENT, description="Operational and evaluation health"
    )
    current_version: str = Field(
        default="v1.0", description="Active production version tag"
    )
    deployment_status: ModelDeploymentStatus = Field(
        default=ModelDeploymentStatus.PRODUCTION, description="Deployment status"
    )
    created_at: datetime = Field(..., description="Registration timestamp")
    updated_at: datetime = Field(..., description="Last governance update timestamp")


class ModelVersion(BaseModel):
    """Immutable model version artifact metadata and cryptographic provenance."""

    model_config = ConfigDict(frozen=True)

    model_id: str = Field(..., description="Associated model identifier")
    version: str = Field(
        ..., description="Semantic version tag, e.g. v1.0, v1.1-candidate"
    )
    lifecycle_state: ModelLifecycleState = Field(
        default=ModelLifecycleState.PRODUCTION, description="Version lifecycle state"
    )
    artifact_hash: str = Field(
        ..., description="SHA-256 hash of serialized model artifact"
    )
    training_dataset_hash: str = Field(
        ..., description="SHA-256 hash of training dataset snapshot"
    )
    feature_schema_hash: str = Field(
        ..., description="SHA-256 hash of feature definition schema"
    )
    code_commit_hash: str = Field(
        ..., description="Git commit SHA-256 for training pipeline code"
    )
    framework: str = Field(
        default="RecoverIQ-Deterministic-ML/1.0", description="ML framework & runtime"
    )
    hyperparameters_hash: str = Field(
        ..., description="SHA-256 hash of hyperparameters configuration"
    )
    training_timestamp: datetime = Field(
        ..., description="Training completion timestamp"
    )
    evaluation_timestamp: datetime = Field(
        ..., description="Last validation evaluation timestamp"
    )


class ModelPerformanceMetrics(BaseModel):
    """Deterministic validation and live performance metrics."""

    model_config = ConfigDict(frozen=True)

    accuracy: float = Field(..., ge=0.0, le=1.0, description="Classification accuracy")
    precision: float = Field(..., ge=0.0, le=1.0, description="Precision score")
    recall: float = Field(..., ge=0.0, le=1.0, description="Recall / sensitivity score")
    f1: float = Field(..., ge=0.0, le=1.0, description="F1 harmonic mean score")
    roc_auc: float = Field(..., ge=0.0, le=1.0, description="Area under ROC curve")
    pr_auc: float = Field(
        ..., ge=0.0, le=1.0, description="Area under Precision-Recall curve"
    )
    log_loss: float = Field(..., ge=0.0, description="Cross-entropy / log loss")
    brier_score: float = Field(
        ..., ge=0.0, le=1.0, description="Brier calibration score"
    )
    latency_p50_ms: float = Field(
        ..., ge=0.0, description="Median inference latency in milliseconds"
    )
    latency_p95_ms: float = Field(
        ..., ge=0.0, description="95th percentile inference latency in milliseconds"
    )
    latency_p99_ms: float = Field(
        ..., ge=0.0, description="99th percentile inference latency in milliseconds"
    )
    throughput_rps: float = Field(
        ..., ge=0.0, description="Peak sustained inference throughput (req/sec)"
    )
    sample_count: int = Field(..., ge=0, description="Evaluation sample size")
    evaluation_timestamp: datetime = Field(..., description="Evaluation timestamp")


class ModelEvaluation(BaseModel):
    """Comprehensive evaluation record comparing candidate vs baseline."""

    model_config = ConfigDict(frozen=True)

    evaluation_id: str = Field(..., description="Unique evaluation execution ID")
    model_id: str = Field(..., description="Model identifier")
    version: str = Field(..., description="Evaluated version")
    evaluation_type: ModelEvaluationType = Field(
        ..., description="Methodology of evaluation"
    )
    metrics: ModelPerformanceMetrics = Field(
        ..., description="Observed performance metrics"
    )
    baseline_version: str | None = Field(
        default=None, description="Comparison baseline version"
    )
    baseline_metrics: ModelPerformanceMetrics | None = Field(
        default=None, description="Baseline performance metrics"
    )
    performance_regression_detected: bool = Field(
        default=False, description="Whether regression exceeds tolerance threshold"
    )
    result: str = Field(default="PASS", description="Evaluation result status")
    evidence_hash: str = Field(
        ..., description="SHA-256 hash of evaluation payload and test outputs"
    )
    timestamp: datetime = Field(..., description="Execution timestamp")


class FeatureGovernance(BaseModel):
    """Lineage, data classification, and sensitivity metadata for an ML feature."""

    model_config = ConfigDict(frozen=True)

    feature_name: str = Field(..., description="Feature variable identifier")
    data_domain: str = Field(
        ..., description="Business domain, e.g. CustomerProfile, PaymentHistory"
    )
    classification: str = Field(
        default="CONFIDENTIAL", description="Data classification level"
    )
    source: str = Field(..., description="Upstream origin service or table")
    lineage_hash: str = Field(
        ..., description="SHA-256 hash of feature extraction code & schema"
    )
    sensitivity: str = Field(
        default="NON_PII_SANITIZED", description="Sensitivity level (Strictly Zero-PII)"
    )
    allowed_for_training: bool = Field(
        default=True, description="Governance approval for training"
    )
    allowed_for_inference: bool = Field(
        default=True, description="Governance approval for inference"
    )


class FeatureDriftMetric(BaseModel):
    """Per-feature statistical drift metrics using Population Stability Index (PSI)."""

    model_config = ConfigDict(frozen=True)

    feature_name: str = Field(..., description="Feature identifier")
    baseline_distribution_hash: str = Field(
        ..., description="SHA-256 hash of baseline reference distribution"
    )
    current_distribution_hash: str = Field(
        ..., description="SHA-256 hash of observed production distribution"
    )
    psi_score: float = Field(
        ..., ge=0.0, description="Population Stability Index score"
    )
    ks_statistic: float = Field(
        default=0.02, ge=0.0, le=1.0, description="Kolmogorov-Smirnov test statistic"
    )
    js_divergence: float = Field(
        default=0.01, ge=0.0, le=1.0, description="Jensen-Shannon divergence"
    )
    threshold_warning: float = Field(
        default=0.10, description="Warning threshold for PSI"
    )
    threshold_critical: float = Field(
        default=0.20, description="Critical threshold for PSI"
    )
    status: DriftStatus = Field(..., description="Drift classification status")


class ModelDriftSummary(BaseModel):
    """Aggregate multi-dimensional drift surveillance report."""

    model_config = ConfigDict(frozen=True)

    model_id: str = Field(..., description="Model identifier")
    version: str = Field(..., description="Active version")
    data_drift_score: float = Field(
        ..., ge=0.0, description="Aggregated input feature data drift PSI"
    )
    feature_drift_score: float = Field(
        ..., ge=0.0, description="Maximum individual feature drift PSI"
    )
    prediction_drift_score: float = Field(
        ..., ge=0.0, description="Prediction probability distribution drift PSI"
    )
    concept_drift_score: float = Field(
        ..., ge=0.0, description="Concept/outcome performance divergence score"
    )
    features_monitored_count: int = Field(
        default=8, ge=0, description="Total features monitored"
    )
    features_drifted_count: int = Field(
        default=0, ge=0, description="Features exceeding warning threshold"
    )
    overall_status: DriftStatus = Field(
        default=DriftStatus.STABLE, description="Overall drift state"
    )
    sample_size: int = Field(
        default=5000, ge=0, description="Recent observation sample size"
    )
    confidence_note: str = Field(
        default="Sufficient statistical sample size for drift estimation",
        description="Confidence note",
    )
    feature_metrics: list[FeatureDriftMetric] = Field(
        default_factory=list, description="Per-feature drift breakdown"
    )
    timestamp: datetime = Field(..., description="Surveillance calculation timestamp")


class FeatureContribution(BaseModel):
    """Sanitized feature importance attribution for explainability."""

    model_config = ConfigDict(frozen=True)

    feature_name: str = Field(..., description="Sanitized feature name")
    contribution_weight: float = Field(
        ..., description="Attribution value / SHAP weight"
    )
    direction: str = Field(
        ..., description="POSITIVE or NEGATIVE impact on recovery likelihood"
    )
    relative_percentage: float = Field(
        ..., ge=0.0, le=100.0, description="Relative contribution percentage"
    )


class ExplainabilityRecord(BaseModel):
    """Sanitized explainability record for an individual ML prediction."""

    model_config = ConfigDict(frozen=True)

    prediction_reference: str = Field(
        ..., description="Reference ID of the prediction event"
    )
    model_id: str = Field(..., description="Model identifier")
    model_version: str = Field(..., description="Model version")
    explanation_method: str = Field(
        default="SHAP_COEFFICIENT_DECOMPOSITION", description="Explanation methodology"
    )
    top_features: list[FeatureContribution] = Field(
        default_factory=list, description="Top contributing features"
    )
    contribution_summary: str = Field(
        ..., description="Sanitized textual explanation summary"
    )
    explanation_status: ExplainabilityStatus = Field(
        default=ExplainabilityStatus.COMPLETE, description="Explanation status"
    )
    sanitized: bool = Field(
        default=True, description="Strict zero-PII sanitization verified"
    )
    disclaimer: str = Field(
        default="Explanation is informational and advisory only; does not override PolicyEngine authority.",
        description="Mandatory governance disclaimer",
    )
    evidence_hash: str = Field(
        ..., description="SHA-256 hash of explanation inputs and attributions"
    )
    timestamp: datetime = Field(..., description="Explanation generation timestamp")


class FairnessMetric(BaseModel):
    """Responsible AI fairness and demographic disparity metric."""

    model_config = ConfigDict(frozen=True)

    protected_group_hash: str = Field(
        ..., description="Anonymized synthetic group identifier (Zero PII)"
    )
    metric_name: str = Field(
        ...,
        description="Fairness metric name, e.g. DemographicParity, EqualOpportunity, DisparateImpact",
    )
    reference_metric: float = Field(
        ..., description="Baseline reference group metric value"
    )
    observed_metric: float = Field(
        ..., description="Target group observed metric value"
    )
    disparity: float = Field(..., description="Calculated absolute difference or ratio")
    threshold: float = Field(..., description="Maximum allowed disparity threshold")
    status: BiasStatus = Field(
        default=BiasStatus.FAIR, description="Fairness classification status"
    )
    sample_size: int = Field(default=1000, description="Synthetic cohort sample size")
    limitation_note: str = Field(
        default="Evaluated using synthetic non-identifying group proxies; zero customer PII inferred.",
        description="Responsible AI limitation note",
    )


class CalibrationMetric(BaseModel):
    """Model probability calibration metrics and reliability curve parameters."""

    model_config = ConfigDict(frozen=True)

    model_id: str = Field(..., description="Model identifier")
    version: str = Field(..., description="Model version")
    brier_score: float = Field(
        ..., ge=0.0, le=1.0, description="Brier score (mean squared calibration error)"
    )
    expected_calibration_error: float = Field(
        ..., ge=0.0, le=1.0, description="Expected Calibration Error (ECE)"
    )
    maximum_calibration_error: float = Field(
        ..., ge=0.0, le=1.0, description="Maximum Calibration Error (MCE)"
    )
    calibration_slope: float = Field(
        ..., description="Logistic calibration curve slope (ideal = 1.0)"
    )
    calibration_intercept: float = Field(
        ..., description="Logistic calibration curve intercept (ideal = 0.0)"
    )
    status: CalibrationStatus = Field(
        default=CalibrationStatus.CALIBRATED, description="Calibration status"
    )
    sample_size: int = Field(default=3500, description="Calibration sample size")
    bins_data: list[dict[str, Any]] = Field(
        default_factory=list, description="Reliability diagram bin distributions"
    )


class RiskDimensionScore(BaseModel):
    """Score breakdown for an individual model risk category."""

    model_config = ConfigDict(frozen=True)

    category: ModelRiskCategory = Field(..., description="Risk category dimension")
    weight: float = Field(
        ..., ge=0.0, le=1.0, description="Weight in total composite score"
    )
    raw_score: float = Field(
        ..., ge=0.0, le=100.0, description="Raw factor score (100 = best / lowest risk)"
    )
    weighted_score: float = Field(
        ..., ge=0.0, le=100.0, description="Weighted factor contribution"
    )
    risk_level: ModelRiskLevel = Field(..., description="Factor risk tier")
    finding: str = Field(..., description="Summary observation for this dimension")


class ModelRiskAssessment(BaseModel):
    """Comprehensive 10-factor Model Risk Management assessment."""

    model_config = ConfigDict(frozen=True)

    model_id: str = Field(..., description="Model identifier")
    version: str = Field(..., description="Model version")
    dimensions: list[RiskDimensionScore] = Field(
        ..., description="10 risk dimension scores"
    )
    total_score: float = Field(
        ...,
        ge=0.0,
        le=100.0,
        description="Composite model governance score [0.0, 100.0]",
    )
    risk_level: ModelRiskLevel = Field(
        ..., description="Composite risk level classification"
    )
    remediation_recommendations: list[str] = Field(
        default_factory=list, description="Advisory remediation recommendations"
    )
    evidence_hash: str = Field(
        ..., description="SHA-256 hash of risk calculation inputs"
    )
    assessed_at: datetime = Field(..., description="Assessment timestamp")


class ModelApproval(BaseModel):
    """Human-in-the-loop governance approval record."""

    model_config = ConfigDict(frozen=True)

    approval_id: str = Field(..., description="Unique approval record ID")
    model_id: str = Field(..., description="Model identifier")
    version: str = Field(..., description="Approved model version")
    status: ModelApprovalStatus = Field(
        default=ModelApprovalStatus.APPROVED, description="Approval status"
    )
    approver_role: str = Field(
        default="ML_GOVERNANCE_ADMIN", description="Role of the human approver"
    )
    approver_id: str = Field(
        default="admin@recoveriq.internal", description="Sanitized actor identifier"
    )
    approval_reason: str = Field(
        ..., description="Governance justification for promotion/activation"
    )
    evidence_hash: str = Field(
        ..., description="SHA-256 hash of approval authorization"
    )
    timestamp: datetime = Field(..., description="Approval timestamp")


class ModelRollbackReadiness(BaseModel):
    """Advisory rollback readiness evaluation."""

    model_config = ConfigDict(frozen=True)

    model_id: str = Field(..., description="Model identifier")
    active_version: str = Field(..., description="Current active production version")
    previous_version: str = Field(
        ..., description="Previous known stable rollback target"
    )
    artifact_integrity: bool = Field(
        default=True, description="Previous artifact SHA-256 hash verified"
    )
    rollback_tested: bool = Field(
        default=True, description="Rollback drill validated in staging"
    )
    rollback_time_seconds: int = Field(
        default=12, description="Estimated automated switchover latency in seconds"
    )
    data_compatibility: bool = Field(
        default=True, description="Feature schema backward compatibility verified"
    )
    readiness_status: RollbackReadinessStatus = Field(
        default=RollbackReadinessStatus.READY, description="Overall rollback readiness"
    )
    authorization_path: str = Field(
        default="HUMAN_ADMIN_REQUIRED", description="Authorization requirement"
    )


class MLIncident(BaseModel):
    """Event-sourced ML governance incident."""

    model_config = ConfigDict(frozen=True)

    incident_id: str = Field(
        ..., description="Unique incident identifier, e.g. ML-INC-2026-001"
    )
    severity: MLIncidentSeverity = Field(..., description="Incident severity level")
    status: MLIncidentStatus = Field(..., description="Current lifecycle state")
    model_id: str = Field(..., description="Affected model identifier")
    affected_version: str = Field(..., description="Affected model version")
    trigger: str = Field(
        ...,
        description="Root trigger description, e.g. Feature drift anomaly, Latency spike",
    )
    root_cause_category: ModelRiskCategory = Field(
        ..., description="Root cause dimension"
    )
    impact: str = Field(
        ..., description="Operational impact assessment (Financially Isolated)"
    )
    evidence_hash: str = Field(..., description="SHA-256 hash of incident telemetry")
    detected_at: datetime = Field(..., description="Detection timestamp")
    acknowledged_at: datetime | None = Field(
        default=None, description="Acknowledgment timestamp"
    )
    resolved_at: datetime | None = Field(
        default=None, description="Resolution timestamp"
    )
    mtta_minutes: float | None = Field(
        default=None, description="Mean Time to Acknowledge in minutes"
    )
    mttr_minutes: float | None = Field(
        default=None, description="Mean Time to Resolve in minutes"
    )


class MLIncidentActionRequest(BaseModel):
    """Payload for operator/admin incident acknowledgment and resolution."""

    decision: str = Field(..., description="ACKNOWLEDGE or RESOLVE")
    notes: str = Field(
        ..., min_length=5, description="Governance justification and action notes"
    )


class MLReadinessGate(BaseModel):
    """Deterministic evaluation gate for ML deployment and governance readiness."""

    model_config = ConfigDict(frozen=True)

    gate_code: MLGateId = Field(
        ..., description="Deterministic gate code (GATE-ML-01 to GATE-ML-22)"
    )
    category: str = Field(..., description="Governance category")
    title: str = Field(..., description="Gate title")
    status: MLGateStatus = Field(
        ..., description="Evaluation status (PASS, WARN, FAIL, BLOCKED)"
    )
    observed_value: str = Field(..., description="Measured telemetry or evidence value")
    threshold: str = Field(..., description="Required threshold criteria")
    evidence: str = Field(
        ..., description="Cryptographic or telemetry evidence reference"
    )
    remediation: str | None = Field(
        default=None, description="Remediation steps if gate is WARN or FAIL"
    )


class ModelLineageNode(BaseModel):
    """Node in the cryptographic model provenance and lineage graph."""

    model_config = ConfigDict(frozen=True)

    node_id: str = Field(..., description="Node unique identifier")
    node_type: str = Field(
        ...,
        description="MODEL, VERSION, DATASET, FEATURES, CODE, ARTIFACT, EVALUATION, APPROVAL, DEPLOYMENT",
    )
    label: str = Field(..., description="Display label")
    hash_sha256: str = Field(..., description="Cryptographic SHA-256 digest")
    metadata: dict[str, Any] = Field(
        default_factory=dict, description="Sanitized metadata"
    )
    parent_ids: list[str] = Field(
        default_factory=list, description="Upstream parent node IDs"
    )


class ModelLineageGraph(BaseModel):
    """Complete end-to-end cryptographic lineage graph for an ML model."""

    model_config = ConfigDict(frozen=True)

    model_id: str = Field(..., description="Model identifier")
    version: str = Field(..., description="Version identifier")
    root_hash: str = Field(
        ..., description="Composite SHA-256 root hash of the lineage graph"
    )
    nodes: list[ModelLineageNode] = Field(
        ..., description="All lineage nodes in chronological order"
    )
    verified: bool = Field(
        default=True, description="Cryptographic chain integrity verified"
    )


class ModelPromotionEvaluation(BaseModel):
    """Advisory promotion readiness evaluation for a candidate model version."""

    model_config = ConfigDict(frozen=True)

    model_id: str = Field(..., description="Model identifier")
    current_version: str = Field(..., description="Active production version")
    candidate_version: str = Field(..., description="Candidate version for promotion")
    recommendation: PromotionRecommendation = Field(
        ..., description="Advisory promotion recommendation"
    )
    performance_passed: bool = Field(
        ..., description="Whether performance gates passed"
    )
    drift_passed: bool = Field(..., description="Whether drift gates passed")
    fairness_passed: bool = Field(..., description="Whether fairness gates passed")
    calibration_passed: bool = Field(
        ..., description="Whether calibration gates passed"
    )
    explainability_passed: bool = Field(
        ..., description="Whether explainability gates passed"
    )
    security_passed: bool = Field(..., description="Whether security scan passed")
    lineage_verified: bool = Field(
        ..., description="Whether dataset and feature lineage are complete"
    )
    rollback_ready: bool = Field(..., description="Whether rollback plan is validated")
    human_approval_required: bool = Field(
        default=True, description="Strict requirement for human admin sign-off"
    )
    findings: list[str] = Field(
        default_factory=list, description="Advisory observations and gate findings"
    )
    evidence_hash: str = Field(..., description="SHA-256 hash of promotion evaluation")
    evaluated_at: datetime = Field(..., description="Evaluation timestamp")


class FinancialPathForensicsNode(BaseModel):
    """Observational trace of an ML prediction in the recovery decision chain."""

    model_config = ConfigDict(frozen=True)

    stage: str = Field(
        ...,
        description="Stage name (RecoveryCase -> MLPrediction -> AgentDecision -> PolicyDecision -> RecoveryAction -> ActionResult)",
    )
    entity_id: str = Field(..., description="Entity identifier")
    status: str = Field(..., description="Stage status")
    latency_ms: float = Field(
        ..., ge=0.0, description="Stage processing latency in milliseconds"
    )
    evidence_hash: str = Field(..., description="SHA-256 hash of stage state")
    timestamp: datetime = Field(..., description="Stage execution timestamp")


class FinancialPathForensics(BaseModel):
    """Observational forensics verifying ML pipeline execution without financial mutation."""

    model_config = ConfigDict(frozen=True)

    trace_id: str = Field(..., description="Unique forensics trace ID")
    stages: list[FinancialPathForensicsNode] = Field(
        ..., description="6-stage execution chain"
    )
    total_latency_ms: float = Field(
        ..., ge=0.0, description="Total pipeline latency in ms"
    )
    financial_isolation_verified: bool = Field(
        default=True,
        description="Strict invariant verified: ΔRecoveryAction=0, ΔPayment=0",
    )
    delta_recovery_actions: int = Field(
        default=0, description="Count of recovery actions created (Strictly 0)"
    )
    delta_payments: int = Field(
        default=0, description="Count of payments mutated (Strictly 0)"
    )
    delta_case_financial_state: int = Field(
        default=0, description="Financial state balance changes (Strictly 0)"
    )
    action_dispatcher_calls: int = Field(
        default=0, description="ActionDispatcher calls (Strictly 0)"
    )
    razorpay_provider_calls: int = Field(
        default=0, description="Razorpay Provider calls (Strictly 0)"
    )
    policy_engine_supremacy_verified: bool = Field(
        default=True, description="PolicyEngine verified as sole decision authority"
    )


class MLGovernanceSummary(BaseModel):
    """High-level executive posture of the AI/ML Governance Control Plane."""

    model_config = ConfigDict(frozen=True)

    governance_score: float = Field(
        ..., ge=0.0, le=100.0, description="Composite ML Governance Health Score"
    )
    health: ModelHealth = Field(..., description="Overall model health classification")
    global_state: MLGlobalState = Field(..., description="Global ML governance state")
    active_models_count: int = Field(
        ..., ge=0, description="Total registered ML models"
    )
    production_models_count: int = Field(
        ..., ge=0, description="Models currently active in production"
    )
    high_risk_models_count: int = Field(
        ..., ge=0, description="Models evaluated at HIGH or CRITICAL risk"
    )
    drift_alerts_count: int = Field(
        ..., ge=0, description="Active drift warnings and detections"
    )
    fairness_alerts_count: int = Field(
        ..., ge=0, description="Active responsible-AI fairness alerts"
    )
    calibration_alerts_count: int = Field(
        ..., ge=0, description="Active calibration alerts"
    )
    open_incidents_count: int = Field(
        ..., ge=0, description="Open ML governance incidents"
    )
    readiness_percentage: float = Field(
        ..., ge=0.0, le=100.0, description="Percentage of ML readiness gates passed"
    )
    passed_gates_count: int = Field(
        ..., ge=0, description="Count of passing readiness gates"
    )
    total_gates_count: int = Field(
        default=22, ge=0, description="Total evaluated readiness gates"
    )
    financial_isolation_verified: bool = Field(
        default=True, description="Strict financial isolation verified"
    )
    zero_pii_verified: bool = Field(
        default=True, description="Zero PII and secret leakage verified"
    )
    last_evaluated_at: datetime = Field(
        ..., description="Summary calculation timestamp"
    )


class MLGovernanceReport(BaseModel):
    """Cryptographically signed, audit-grade ML Governance Report."""

    model_config = ConfigDict(frozen=True)

    report_id: str = Field(
        ..., description="Unique signed report ID, e.g. ML-GOV-REP-2026-001"
    )
    generated_at: datetime = Field(..., description="Report generation timestamp")
    summary: MLGovernanceSummary = Field(..., description="Executive summary snapshot")
    model_inventory: list[ModelRegistryEntry] = Field(
        ..., description="Complete model inventory"
    )
    risk_assessments: list[ModelRiskAssessment] = Field(
        ..., description="Risk assessments for all active models"
    )
    drift_summary: list[ModelDriftSummary] = Field(
        ..., description="Drift surveillance reports"
    )
    fairness_summary: list[FairnessMetric] = Field(
        ..., description="Fairness and responsible AI metrics"
    )
    calibration_summary: list[CalibrationMetric] = Field(
        ..., description="Calibration and reliability metrics"
    )
    readiness_gates: list[MLReadinessGate] = Field(
        ..., description="All 22 ML readiness gates"
    )
    incidents: list[MLIncident] = Field(
        ..., description="All open and resolved ML incidents"
    )
    forensics: FinancialPathForensics = Field(
        ..., description="Financial path observational forensics"
    )
    evidence_hash: str = Field(
        ..., description="SHA-256 HMAC digest of all included governance evidence"
    )
    signature: str = Field(
        ...,
        description="Cryptographic SHA-256 signature guaranteeing audit immutability",
    )


class EvaluationRequest(BaseModel):
    """Payload to trigger offline/shadow model evaluation."""

    evaluation_type: ModelEvaluationType = Field(
        default=ModelEvaluationType.OFFLINE, description="Evaluation methodology"
    )
    sample_size: int = Field(
        default=2000, ge=100, le=50000, description="Evaluation sample size"
    )
    notes: str | None = Field(default=None, description="Optional evaluation context")


class ExplanationRequest(BaseModel):
    """Payload to generate a sanitized prediction explanation."""

    prediction_reference: str = Field(..., description="Prediction event ID to explain")
    feature_vector: dict[str, float] = Field(
        default_factory=dict, description="Sanitized numerical feature vector"
    )


class PromotionEvaluationRequest(BaseModel):
    """Payload to request advisory promotion evaluation."""

    candidate_version: str = Field(..., description="Target candidate version tag")
    justification: str = Field(
        ..., min_length=5, description="Business justification for candidate version"
    )


# =============================================================================
# Compatibility / Extended Schemas for Legacy & Specialized ML Endpoints
# =============================================================================


class MLGovernanceScoreBreakdown(BaseModel):
    """Component breakdown for composite ML governance score."""

    model_config = ConfigDict(frozen=True)

    weights_sum: float = Field(default=1.0, description="Sum of factor weights")
    performance_score: float = Field(
        default=96.0, description="Performance factor score"
    )
    calibration_score: float = Field(
        default=98.0, description="Calibration factor score"
    )
    drift_score: float = Field(default=94.0, description="Drift factor score")
    fairness_score: float = Field(default=97.0, description="Fairness factor score")
    explainability_score: float = Field(
        default=95.0, description="Explainability factor score"
    )
    security_score: float = Field(default=99.0, description="Security factor score")
    lineage_score: float = Field(default=100.0, description="Lineage factor score")
    gates_score: float = Field(default=100.0, description="Gates factor score")
    rollback_score: float = Field(default=98.0, description="Rollback factor score")
    human_oversight_score: float = Field(
        default=100.0, description="Human oversight factor score"
    )


class ModelInventoryItem(BaseModel):
    """Item in model inventory catalog."""

    model_config = ConfigDict(frozen=True)

    model_id: str = Field(..., description="Model identifier")
    model_name: str = Field(..., description="Human-readable model name")
    version: str = Field(default="v1.0", description="Active model version")
    tier: str = Field(default="tier_1_mission_critical", description="Criticality tier")
    operational_status: str = Field(default="active", description="Operational status")
    stage: str = Field(default="production", description="Governance stage")
    owner: str = Field(default="ML_ENGINEERING", description="Owner role")
    purpose: str = Field(..., description="Model business purpose")
    risk_level: str = Field(default="LOW", description="Risk level")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Update timestamp")


class EvaluationRunRequest(BaseModel):
    """Payload to trigger offline validation run."""

    model_id: str = Field(..., description="Model identifier")
    evaluation_type: str = Field(
        default="offline_validation", description="Type of evaluation"
    )
    dataset_name: str = Field(default="val_dataset", description="Dataset name")
    dataset_row_count: int = Field(default=1000, description="Dataset sample size")
    notes: str | None = Field(default=None, description="Optional evaluation notes")


class DriftAnalysisRequest(BaseModel):
    """Payload to execute statistical drift analysis."""

    model_id: str = Field(..., description="Model identifier")
    psi_threshold: float = Field(default=0.20, description="PSI warning threshold")
    dataset_name: str | None = Field(default=None, description="Dataset name")


class DriftAnalysis(BaseModel):
    """Drift test evaluation report."""

    model_config = ConfigDict(frozen=True)

    analysis_id: str = Field(..., description="Analysis ID")
    model_id: str = Field(..., description="Model ID")
    drift_type: str = Field(default="FEATURE_DRIFT", description="Drift category")
    psi_score: float = Field(default=0.032, description="PSI score")
    ks_statistic: float = Field(default=0.015, description="KS test statistic")
    status: str = Field(default="STABLE", description="Drift classification")
    sample_size: int = Field(default=5000, description="Sample size")
    analyzed_at: datetime = Field(..., description="Analysis timestamp")


class FairnessAuditRequest(BaseModel):
    """Payload to trigger responsible-AI fairness audit."""

    model_id: str = Field(..., description="Model identifier")
    protected_attribute: str = Field(
        default="synthetic_cohort", description="Protected proxy attribute"
    )


class FairnessAudit(BaseModel):
    """Responsible AI fairness audit result."""

    model_config = ConfigDict(frozen=True)

    audit_id: str = Field(..., description="Audit record ID")
    model_id: str = Field(..., description="Model ID")
    metric_type: str = Field(default="disparate_impact", description="Metric type")
    disparate_impact_ratio: float = Field(
        default=0.96, description="Disparate impact ratio"
    )
    demographic_parity_diff: float = Field(
        default=0.02, description="Demographic parity difference"
    )
    status: str = Field(default="FAIR", description="Fairness status")
    audited_at: datetime = Field(..., description="Audit timestamp")


class ExplainabilityGenerateRequest(BaseModel):
    """Payload to generate SHAP prediction attribution report."""

    model_id: str = Field(..., description="Model identifier")
    method: str = Field(default="TreeSHAP", description="Attribution method")
    prediction_id: str | None = Field(
        default=None, description="Prediction reference ID"
    )


class ExplainabilityReport(BaseModel):
    """Sanitized explainability report."""

    model_config = ConfigDict(frozen=True)

    report_id: str = Field(..., description="Report ID")
    model_id: str = Field(..., description="Model ID")
    method: str = Field(default="TreeSHAP", description="Explanation methodology")
    top_features: list[FeatureContribution] = Field(
        default_factory=list, description="Feature attributions"
    )
    summary: str = Field(..., description="Sanitized explanation narrative")
    generated_at: datetime = Field(..., description="Generation timestamp")


class ShadowComparisonRequest(BaseModel):
    """Payload to execute champion vs challenger shadow comparison."""

    champion_model_id: str = Field(..., description="Champion model ID")
    challenger_model_id: str = Field(..., description="Challenger model ID")
    sample_size: int = Field(default=2000, description="Comparison sample size")


class ShadowComparison(BaseModel):
    """Champion vs challenger shadow deployment comparison."""

    model_config = ConfigDict(frozen=True)

    comparison_id: str = Field(..., description="Comparison ID")
    champion_model_id: str = Field(..., description="Champion model ID")
    challenger_model_id: str = Field(..., description="Challenger model ID")
    champion_version: str = Field(default="v1.0", description="Champion version")
    challenger_version: str = Field(
        default="v1.1-candidate", description="Challenger version"
    )
    champion_accuracy: float = Field(default=0.884, description="Champion accuracy")
    challenger_accuracy: float = Field(default=0.892, description="Challenger accuracy")
    delta_accuracy: float = Field(default=0.008, description="Accuracy delta")
    status: str = Field(default="IMPROVED", description="Comparison status")
    evaluated_at: datetime = Field(..., description="Evaluation timestamp")


class PromotionRequest(BaseModel):
    """Promotion request payload."""

    model_id: str = Field(..., description="Model identifier")
    target_version: str = Field(default="v1.1", description="Target version")
    reason: str = Field(
        default="Performance validation passed", description="Justification"
    )


class PromotionApprovalRequest(BaseModel):
    """Promotion approval record."""

    model_config = ConfigDict(frozen=True)

    promotion_id: str = Field(..., description="Promotion ID")
    model_id: str = Field(..., description="Model ID")
    current_version: str = Field(default="v1.0", description="Current version")
    target_version: str = Field(default="v1.1", description="Target version")
    status: str = Field(default="APPROVED", description="Promotion status")
    risk_level: str = Field(default="LOW", description="Assessed risk")
    reason: str = Field(..., description="Justification")
    requested_at: datetime = Field(..., description="Request timestamp")


class PromotionApprovalActionRequest(BaseModel):
    """Payload to review promotion request."""

    decision: str = Field(..., description="APPROVE or REJECT")
    notes: str = Field(..., min_length=3, description="Governance justification")


class KillSwitchToggleRequest(BaseModel):
    """Payload to arm or toggle model kill switch."""

    model_id: str = Field(..., description="Model identifier")
    state: str = Field(default="ACTIVE", description="Target state")
    reason: str = Field(..., min_length=5, description="Governance reason")


class ModelKillSwitch(BaseModel):
    """Model kill switch state record."""

    model_config = ConfigDict(frozen=True)

    model_id: str = Field(..., description="Model ID")
    state: str = Field(default="INACTIVE", description="Kill switch state")
    reason: str = Field(default="Normal operating conditions", description="Reason")
    updated_by: str = Field(default="admin@recoveriq.internal", description="Actor")
    updated_at: datetime = Field(..., description="Timestamp")


class ComplianceCardGenerateRequest(BaseModel):
    """Payload to generate regulatory AI model compliance card."""

    model_id: str = Field(..., description="Model identifier")
    framework: str = Field(default="EU_AI_ACT", description="Compliance framework")


class ModelComplianceCard(BaseModel):
    """Regulatory AI model compliance card."""

    model_config = ConfigDict(frozen=True)

    card_id: str = Field(..., description="Card ID")
    model_id: str = Field(..., description="Model ID")
    framework: str = Field(default="EU_AI_ACT", description="Regulatory framework")
    compliance_score: float = Field(default=98.5, description="Compliance rating")
    status: str = Field(default="COMPLIANT", description="Compliance status")
    generated_at: datetime = Field(..., description="Generation timestamp")


class MLReportGenerateRequest(BaseModel):
    """Payload to generate signed ML governance report."""

    notes: str | None = Field(default=None, description="Optional notes")


class ModelLineage(BaseModel):
    """Cryptographic lineage graph summary."""

    model_config = ConfigDict(frozen=True)

    model_id: str = Field(..., description="Model ID")
    version: str = Field(default="v1.0", description="Version")
    nodes: list[ModelLineageNode] = Field(
        default_factory=list, description="Lineage nodes"
    )
    root_hash: str = Field(..., description="Cryptographic root hash")
