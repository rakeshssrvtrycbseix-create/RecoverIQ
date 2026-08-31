from typing import Any

from pydantic import BaseModel, Field

from app.models.enums import (
    ControlPlaneDiagnosticSeverity,
    GlobalSystemState,
    IncidentSeverity,
    IncidentState,
    LineageStageType,
    SubsystemHealthStatus,
)


class SubsystemHealth(BaseModel):
    """Health status and operational telemetry for an individual intelligence subsystem."""

    subsystem: str
    status: SubsystemHealthStatus
    score: float = Field(..., ge=0.0, le=100.0)
    summary: str
    metrics: dict[str, Any] = Field(default_factory=dict)


class IntelligenceHealthScoreBreakdown(BaseModel):
    """Deterministic intelligence health score composed of 8 weighted component dimensions.

    Formula:
    Score = 0.15*Model + 0.10*Calibration + 0.15*Drift + 0.10*DataQuality +
            0.15*Strategy + 0.10*Experiment + 0.15*Deployment + 0.10*ContinuousLearning
    """

    overall_score: float = Field(..., ge=0.0, le=100.0)
    model_score: float = Field(..., ge=0.0, le=100.0)
    calibration_score: float = Field(..., ge=0.0, le=100.0)
    drift_score: float = Field(..., ge=0.0, le=100.0)
    data_quality_score: float = Field(..., ge=0.0, le=100.0)
    strategy_score: float = Field(..., ge=0.0, le=100.0)
    experiment_score: float = Field(..., ge=0.0, le=100.0)
    deployment_score: float = Field(..., ge=0.0, le=100.0)
    continuous_learning_score: float = Field(..., ge=0.0, le=100.0)
    weights: dict[str, float] = Field(
        default_factory=lambda: {
            "model": 0.15,
            "calibration": 0.10,
            "drift": 0.15,
            "data_quality": 0.10,
            "strategy": 0.15,
            "experiment": 0.10,
            "deployment": 0.15,
            "continuous_learning": 0.10,
        }
    )
    formula_explanation: str = (
        "Deterministic weighted average of 8 operational dimensions: Model Performance (15%), "
        "Calibration Reliability (10%), Population Drift (15%), Data Quality Integrity (10%), "
        "Strategy Optimization Yield (15%), Causal Experiment Validity (10%), Deployment Safety (15%), "
        "and Continuous Learning Readiness (10%)."
    )


class ControlPlaneDiagnostic(BaseModel):
    """Detailed diagnostic observation emitted by the unified safety controller."""

    code: str
    severity: ControlPlaneDiagnosticSeverity
    source_phase: str
    observed_value: Any = None
    threshold: Any = None
    explanation: str
    recommended_operator_action: str


class IntelligenceIncident(BaseModel):
    """Deterministic, correlated incident detected by multi-signal surveillance rules."""

    incident_id: str
    severity: IncidentSeverity
    state: IncidentState
    source_phases: list[str]
    diagnostic_codes: list[str]
    title: str
    first_detected: str
    last_detected: str
    evidence: dict[str, Any] = Field(default_factory=dict)
    recommended_action: str
    requires_human_review: bool = True


class UnifiedIntelligenceHealth(BaseModel):
    """Complete unified intelligence health response across all subsystems."""

    model_health: SubsystemHealth
    model_version: str
    calibration_health: SubsystemHealth
    strategy_health: SubsystemHealth
    experiment_health: SubsystemHealth
    deployment_health: SubsystemHealth
    continuous_learning_health: SubsystemHealth
    data_quality_health: SubsystemHealth
    drift_health: SubsystemHealth
    rollback_health: SubsystemHealth

    pending_human_reviews: int = Field(0, ge=0)
    global_system_state: GlobalSystemState
    intelligence_health_score: IntelligenceHealthScoreBreakdown
    diagnostics: list[ControlPlaneDiagnostic] = Field(default_factory=list)
    generated_at: str


class UnifiedLineageNode(BaseModel):
    """Node in the end-to-end model and strategy provenance progression DAG."""

    stage: LineageStageType
    identifier: str
    status: str
    metadata: dict[str, Any] = Field(default_factory=dict)
    parent_stage: str | None = None
    parent_identifier: str | None = None
    created_at: str


class UnifiedLineageResponse(BaseModel):
    """End-to-end model + strategy provenance lineage graph."""

    nodes: list[UnifiedLineageNode] = Field(default_factory=list)
    active_champion_model: str
    active_production_strategy: str
    active_deployment_id: str | None = None
    generated_at: str


class DecisionTraceFeatureSnapshot(BaseModel):
    """Sanitized feature snapshot used for ML inference during case decisioning."""

    payment_amount_paise: int
    currency: str = "INR"
    attempt_number: int = 1
    customer_total_payments: int = 0
    customer_success_rate: float = 0.0
    error_code: str = "UNKNOWN"
    error_reason: str = "unknown"


class DecisionTraceStage(BaseModel):
    """Individual execution stage within a case decision trace."""

    stage_name: str
    timestamp: str | None = None
    status: str
    details: dict[str, Any] = Field(default_factory=dict)


class CaseDecisionTrace(BaseModel):
    """Complete end-to-end reconstructed decision trace for an individual recovery case."""

    case_id: str
    payment_id: str
    case_status: str
    amount_at_risk_paise: int
    recovered_amount_paise: int
    opened_at: str
    resolved_at: str | None = None
    failure_event: dict[str, Any] = Field(default_factory=dict)
    feature_snapshot: DecisionTraceFeatureSnapshot
    model_version: str
    prediction_probability: float = Field(..., ge=0.0, le=1.0)
    prediction_timestamp: str | None = None
    agent_decision: dict[str, Any] | None = None
    policy_decision: dict[str, Any] | None = None
    selected_strategy: dict[str, Any] | None = None
    experiment_assignment: dict[str, Any] | None = None
    rollout_assignment: dict[str, Any] | None = None
    action_metadata: dict[str, Any] | None = None
    final_action_result: dict[str, Any] | None = None
    final_recovery_outcome: str
    stages: list[DecisionTraceStage] = Field(default_factory=list)
    traced_at: str
    disclaimer: str = (
        "Read-only operational decision trace. Zero PII and zero gateway credentials exposed. "
        "Authoritative financial state transitions governed exclusively by PolicyEngine."
    )


class GovernanceCenterResponse(BaseModel):
    """Centralized governance action queue aggregating all pending reviews and alerts."""

    pending_strategy_recommendations_count: int = Field(0, ge=0)
    pending_strategy_recommendations: list[dict[str, Any]] = Field(default_factory=list)
    pending_model_reviews_count: int = Field(0, ge=0)
    pending_model_reviews: list[dict[str, Any]] = Field(default_factory=list)
    pending_deployment_reviews_count: int = Field(0, ge=0)
    pending_deployment_reviews: list[dict[str, Any]] = Field(default_factory=list)
    rollback_alerts: list[dict[str, Any]] = Field(default_factory=list)
    learning_alerts: list[dict[str, Any]] = Field(default_factory=list)
    critical_diagnostics: list[ControlPlaneDiagnostic] = Field(default_factory=list)
    recent_audit_events: list[dict[str, Any]] = Field(default_factory=list)
    required_operator_actions: list[str] = Field(default_factory=list)
    generated_at: str


class ControlPlaneSummaryResponse(BaseModel):
    """High-level summary of the Intelligence Control Plane for dashboard overview."""

    global_state: GlobalSystemState
    health_score: IntelligenceHealthScoreBreakdown
    subsystems: list[SubsystemHealth] = Field(default_factory=list)
    active_incidents_count: int = Field(0, ge=0)
    pending_reviews_count: int = Field(0, ge=0)
    active_champion_version: str
    active_strategy_action: str
    deployment_status: str
    learning_status: str
    top_diagnostics: list[ControlPlaneDiagnostic] = Field(default_factory=list)
    governance_disclaimer: str = (
        "Authoritative financial execution is strictly gated by PolicyEngine. "
        "The Intelligence Control Plane is an observational governance and safety orchestration layer."
    )
    generated_at: str


class IncidentsResponse(BaseModel):
    """Paginated or complete list of detected correlated intelligence incidents."""

    incidents: list[IntelligenceIncident] = Field(default_factory=list)
    total: int = Field(0, ge=0)
    active_count: int = Field(0, ge=0)
    generated_at: str
