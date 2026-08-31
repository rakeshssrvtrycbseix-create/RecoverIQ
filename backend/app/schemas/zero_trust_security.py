from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from app.models.enums import (
    AttackChainStage,
    AuthMatrixStatus,
    GlobalSecurityState,
    SecurityIncidentStatus,
    SecurityResponseType,
    ServiceIdentityStatus,
    ThreatScoreClassification,
    ThreatSeverity,
    ZeroTrustGateId,
    ZeroTrustGateStatus,
    ZeroTrustScoreClassification,
)


class ServiceIdentity(BaseModel):
    """Identity, trust posture, and credentials telemetry for a core microservice."""

    service_name: str
    identity_status: ServiceIdentityStatus
    authentication_method: str
    authorization_status: str
    certificate_status: str
    credential_age_days: int
    last_verified: datetime
    trust_score: float = Field(..., ge=0.0, le=100.0)
    privilege_level: str
    network_zone: str
    runtime_status: str
    configuration_integrity: str


class ServiceAuthPair(BaseModel):
    """Service-to-service authorization matrix link."""

    source_service: str
    target_service: str
    status: AuthMatrixStatus
    is_financial_path: bool
    requires_mutual_tls: bool
    permission_boundary: str
    last_evaluated: datetime
    violation_id: str | None = None


class ServiceAuthMatrix(BaseModel):
    """Complete service-to-service authorization topology."""

    total_pairs: int
    allowed_pairs: int
    denied_pairs: int
    conditional_pairs: int
    review_required_pairs: int
    violations_count: int
    pairs: list[ServiceAuthPair]


class TrustViolation(BaseModel):
    """Detected zero-trust boundary or authorization violation."""

    violation_id: str
    severity: ThreatSeverity
    violation_type: str
    source_service: str
    target_service: str
    description: str
    detected_at: datetime
    mitigation_recommendation: SecurityResponseType


class ThreatIndicator(BaseModel):
    """Hashed/pseudonymized threat indicator fingerprint."""

    indicator_id: str
    fingerprint: str
    indicator_type: str
    severity: ThreatSeverity
    confidence_score: float = Field(..., ge=0.0, le=1.0)
    source_component: str
    first_seen: datetime
    last_seen: datetime
    affected_services: list[str]
    description: str


class BehavioralThreatScore(BaseModel):
    """Behavioral threat score composite evaluation."""

    overall_threat_score: float = Field(..., ge=0.0, le=100.0)
    classification: ThreatScoreClassification
    auth_anomaly_score: float
    frequency_anomaly_score: float
    privilege_anomaly_score: float
    service_anomaly_score: float
    config_anomaly_score: float
    runtime_anomaly_score: float
    evaluated_at: datetime


class AttackChainStageItem(BaseModel):
    """Specific stage in a correlated attack chain."""

    stage: AttackChainStage
    timestamp: datetime
    component: str
    summary: str
    evidence_hash: str


class AttackChain(BaseModel):
    """Correlated 8-stage attack propagation chain."""

    chain_id: str
    title: str
    severity: ThreatSeverity
    confidence_score: float = Field(..., ge=0.0, le=1.0)
    first_seen: datetime
    last_seen: datetime
    stages: list[AttackChainStageItem]
    evidence_hashes: list[str]
    affected_services: list[str]
    blast_radius_score: float = Field(..., ge=0.0, le=100.0)
    recommended_action: SecurityResponseType
    human_review_required: bool = True


class RuntimeSecurityPosture(BaseModel):
    """Runtime security surveillance and posture evaluation."""

    process_integrity_status: str
    container_workload_posture: str
    dependency_cve_count_critical: int
    dependency_cve_count_high: int
    filesystem_integrity_status: str
    unexpected_open_ports_count: int
    unauthorized_process_count: int
    evaluated_at: datetime


class SecretExposureFinding(BaseModel):
    """Sanitized secret exposure scanner finding."""

    finding_id: str
    secret_type: str
    masked_value: str
    location: str
    severity: ThreatSeverity
    fingerprint: str
    detected_at: datetime


class SecurityIncident(BaseModel):
    """Cross-domain correlated security incident record."""

    incident_id: str
    title: str
    severity: ThreatSeverity
    status: SecurityIncidentStatus
    affected_services: list[str]
    attack_chain_id: str | None = None
    detected_at: datetime
    updated_at: datetime
    mtta_seconds: float
    mttr_seconds: float
    assigned_operator: str
    recommended_action: SecurityResponseType
    human_authorization_required: bool = True
    evidence_fingerprint: str
    timeline: list[dict[str, Any]]


class SecurityIncidentActionRequest(BaseModel):
    """Request schema for operator actions on security incidents."""

    action: str  # ACKNOWLEDGE, ESCALATE, RESOLVE, INVESTIGATE
    operator_id: str
    notes: str | None = None


class ZeroTrustGate(BaseModel):
    """Deterministic Zero-Trust Security Readiness Gate."""

    gate_id: ZeroTrustGateId
    name: str
    category: str
    status: ZeroTrustGateStatus
    observed_value: str
    threshold: str
    severity: ThreatSeverity
    evidence: str
    remediation: str
    evaluated_at: datetime


class SecurityEvidenceNode(BaseModel):
    """Cryptographic evidence chain entry."""

    evidence_id: str
    evidence_hash: str
    event_type: str
    source_service: str
    timestamp: datetime
    sanitized_payload: dict[str, Any]
    signature: str


class ZeroTrustSummary(BaseModel):
    """Executive summary posture of the Zero-Trust Security Control Plane."""

    zero_trust_score: float = Field(..., ge=0.0, le=100.0)
    score_classification: ZeroTrustScoreClassification
    global_security_state: GlobalSecurityState
    behavioral_threat_score: float = Field(..., ge=0.0, le=100.0)
    threat_classification: ThreatScoreClassification
    trusted_services_count: int
    total_services_count: int
    active_threat_indicators_count: int
    trust_violations_count: int
    active_attack_chains_count: int
    critical_incidents_count: int
    security_readiness_score: float = Field(..., ge=0.0, le=100.0)
    secret_exposures_count: int
    financial_isolation_verified: bool = True
    automatic_financial_response: str = "DISABLED"
    evaluated_at: datetime
    disclaimer: str


class SignedSecurityReport(BaseModel):
    """Tamper-evident signed Zero-Trust Security Report."""

    report_id: str
    generated_at: datetime
    zero_trust_score: float
    score_classification: ZeroTrustScoreClassification
    global_security_state: GlobalSecurityState
    summary: ZeroTrustSummary
    service_identities: list[ServiceIdentity]
    authorization_matrix: ServiceAuthMatrix
    trust_violations: list[TrustViolation]
    threat_indicators: list[ThreatIndicator]
    attack_chains: list[AttackChain]
    runtime_posture: RuntimeSecurityPosture
    secret_exposures: list[SecretExposureFinding]
    incidents: list[SecurityIncident]
    readiness_gates: list[ZeroTrustGate]
    verification_signature: str
    financial_isolation_verified: bool = True
