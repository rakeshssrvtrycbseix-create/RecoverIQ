"""Pydantic schemas for Phase 10G Architecture Governance, Change Management,

Release Safety & Deployment Assurance.
"""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from app.models.enums import (
    ArchitectureLayer,
    ArchitectureRisk,
    ChangeApprovalStatus,
    ChangeRiskLevel,
    ChangeStatus,
    ChangeType,
    CompatibilityStatus,
    ConfigurationDriftStatus,
    DeploymentStrategy,
    FeatureFlagStatus,
    GovernanceDecision,
    ReleaseDecision,
    ReleaseHealth,
    ReleaseStage,
    ReleaseStatus,
)


class ChangeImpact(BaseModel):
    """Subsystem impact and blast-radius evaluation for a proposed change."""

    affected_services: list[str] = Field(default_factory=list)
    is_financial_path: bool = False
    database_impact: bool = False
    breaking_api_impact: bool = False
    authentication_impact: bool = False
    ml_model_impact: bool = False
    configuration_impact: bool = False
    blast_radius_score: float = Field(ge=0.0, le=100.0, default=20.0)


class ChangeRiskAssessment(BaseModel):
    """Detailed risk assessment for a change request."""

    risk_score: float = Field(ge=0.0, le=100.0)
    risk_level: ChangeRiskLevel
    financial_risk_multiplier: float = 1.0
    risk_factors: list[str] = Field(default_factory=list)
    mitigation_recommendations: list[str] = Field(default_factory=list)


class ChangeRequest(BaseModel):
    """Governed change request entity."""

    change_id: str
    title: str
    description: str
    change_type: ChangeType
    risk_level: ChangeRiskLevel
    status: ChangeStatus
    approval_status: ChangeApprovalStatus
    owner_role: str
    affected_services: list[str]
    is_financial_path: bool = False
    requires_downtime: bool = False
    rollback_procedure: str
    created_at: datetime
    risk_assessment: ChangeRiskAssessment


class ChangeRequestCreate(BaseModel):
    """Payload for submitting a new change request."""

    title: str = Field(min_length=3, max_length=200)
    description: str = Field(min_length=5, max_length=2000)
    change_type: ChangeType
    affected_services: list[str] = Field(min_length=1)
    is_financial_path: bool = False
    requires_downtime: bool = False
    rollback_procedure: str = Field(min_length=5, max_length=1000)


class DependencyImpact(BaseModel):
    """Service coupling and dependency blast radius model."""

    source_service: str
    target_service: str
    dependency_type: str = "DIRECT"  # DIRECT, TRANSITIVE, CRITICAL
    is_financial_path: bool = False
    is_single_point_of_failure: bool = False
    failure_propagation_risk: ArchitectureRisk = ArchitectureRisk.LOW
    blast_radius: float = Field(ge=0.0, le=100.0, default=15.0)


class ArchitectureFinding(BaseModel):
    """Architectural risk finding or structural anti-pattern."""

    finding_id: str
    layer: ArchitectureLayer
    severity: ArchitectureRisk
    title: str
    description: str
    affected_components: list[str] = Field(default_factory=list)
    remediation: str
    created_at: datetime


class ApiCompatibilityReport(BaseModel):
    """API contract backward compatibility evaluation."""

    total_endpoints: int = 0
    breaking_changes_count: int = 0
    non_breaking_changes_count: int = 0
    compatibility_status: CompatibilityStatus
    breaking_details: list[str] = Field(default_factory=list)
    evaluated_at: datetime


class DatabaseCompatibilityReport(BaseModel):
    """Database schema compatibility report (Zero-migration invariant)."""

    schema_modifications_count: int = 0
    table_impacts: list[str] = Field(default_factory=list)
    is_migration_required: bool = False
    compatibility_status: CompatibilityStatus
    breaking_risks: list[str] = Field(default_factory=list)
    evaluated_at: datetime


class ConfigurationDrift(BaseModel):
    """Observed configuration drift with masked/hashed secrets."""

    key: str
    category: str
    expected_value_masked: str
    observed_value_masked: str
    status: ConfigurationDriftStatus
    severity: ArchitectureRisk
    drift_detected_at: datetime
    evidence_hash: str


class FeatureFlag(BaseModel):
    """Governed feature flag definition."""

    flag_id: str
    name: str
    description: str
    status: FeatureFlagStatus
    rollout_percentage: int = Field(ge=0, le=100)
    environment: str = "PRODUCTION"
    is_financial_path: bool = False
    owner: str
    created_at: datetime
    expiration_date: datetime | None = None
    is_stale: bool = False


class FeatureFlagUpdate(BaseModel):
    """Payload to update rollout or status of a feature flag."""

    status: FeatureFlagStatus | None = None
    rollout_percentage: int | None = Field(default=None, ge=0, le=100)
    rationale: str = Field(min_length=3, max_length=500)


class ReleaseReadinessGate(BaseModel):
    """Deterministic release verification gate."""

    code: str
    name: str
    status: str  # PASS, WARNING, BLOCKED, REVIEW_REQUIRED
    observed_value: str
    threshold: str
    evidence: str
    remediation: str


class ReleaseReadinessSummary(BaseModel):
    """Consolidated release readiness gates posture."""

    total_gates: int = 18
    passed_gates: int = 18
    warning_gates: int = 0
    blocked_gates: int = 0
    review_required_gates: int = 0
    overall_status: str = "PASS"
    gates: list[ReleaseReadinessGate] = Field(default_factory=list)


class DeploymentObservation(BaseModel):
    """Observational deployment state telemetry."""

    environment: str = "PRODUCTION"
    strategy: DeploymentStrategy
    current_version: str
    target_version: str
    status: ReleaseStatus
    observed_at: datetime
    health_metrics: dict[str, Any] = Field(default_factory=dict)


class CanaryEvaluation(BaseModel):
    """Observational canary comparison and recommendation."""

    canary_version: str
    traffic_percentage: int = 10
    baseline_p95_ms: float
    canary_p95_ms: float
    baseline_error_rate_pct: float
    canary_error_rate_pct: float
    decision: ReleaseDecision
    recommendation_reason: str
    evaluated_at: datetime


class RollbackReadiness(BaseModel):
    """Rollback safety and reversibility evaluation."""

    previous_version_available: bool = True
    artifact_digest: str
    database_reversible: bool = True
    config_reversible: bool = True
    estimated_recovery_time_sec: int = 45
    readiness_status: str = "ROLLBACK_READY"
    recommendations: list[str] = Field(default_factory=list)


class ReleaseApproval(BaseModel):
    """Human governance approval record."""

    approval_id: str
    release_id: str
    approver_id: str
    approver_role: str
    decision: GovernanceDecision
    comments: str
    decided_at: datetime


class ReleaseApprovalRequest(BaseModel):
    """Payload to approve/reject a release candidate."""

    decision: GovernanceDecision
    comments: str = Field(min_length=3, max_length=1000)


class ReleaseIncident(BaseModel):
    """Correlated release incident."""

    incident_id: str
    severity: ArchitectureRisk
    affected_service: str
    description: str
    status: str = "ACTIVE"
    detected_at: datetime
    mitigation: str


class ReleaseLineageNode(BaseModel):
    """Node in the 10-stage cryptographic release lineage DAG."""

    node_id: str
    stage: str
    title: str
    status: str
    actor: str
    timestamp: datetime
    evidence_hash: str
    details: dict[str, Any] = Field(default_factory=dict)


class ReleaseCandidate(BaseModel):
    """Governed release candidate entity."""

    rc_id: str
    version: str
    commit_sha: str
    stage: ReleaseStage
    status: ReleaseStatus
    health: ReleaseHealth
    decision: ReleaseDecision
    deployment_strategy: DeploymentStrategy
    change_requests: list[str] = Field(default_factory=list)
    affected_services: list[str] = Field(default_factory=list)
    risk_score: float = Field(ge=0.0, le=100.0, default=12.5)
    readiness_summary: ReleaseReadinessSummary
    rollback_readiness: RollbackReadiness
    created_at: datetime


class ReleaseCandidateCreate(BaseModel):
    """Payload to create a new release candidate."""

    version: str = Field(min_length=2, max_length=50)
    commit_sha: str = Field(min_length=7, max_length=40)
    deployment_strategy: DeploymentStrategy = DeploymentStrategy.CANARY
    change_request_ids: list[str] = Field(min_length=1)


class ReleaseGovernanceSummary(BaseModel):
    """Consolidated Architecture & Release Governance Control Plane posture."""

    governance_score: float = Field(ge=0.0, le=100.0)
    classification: ReleaseHealth
    global_state: ReleaseDecision
    open_changes_count: int
    high_risk_changes_count: int
    release_candidates_count: int
    readiness_score: float
    config_drift_count: int
    rollback_readiness_status: str
    active_incidents_count: int
    approved_releases_count: int
    evaluated_at: datetime
    disclaimer: str


class ReleaseGovernanceReport(BaseModel):
    """Complete signed release governance audit report."""

    report_id: str
    generated_at: datetime
    governance_score: float
    classification: ReleaseHealth
    decision: ReleaseDecision
    summary: ReleaseGovernanceSummary
    change_requests: list[ChangeRequest]
    readiness_gates: list[ReleaseReadinessGate]
    config_drift: list[ConfigurationDrift]
    feature_flags: list[FeatureFlag]
    canary_evaluation: CanaryEvaluation
    rollback_readiness: RollbackReadiness
    incidents: list[ReleaseIncident]
    verification_signature: str
    isolation_verified: bool = True
