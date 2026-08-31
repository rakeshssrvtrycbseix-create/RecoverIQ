from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field


class ComplianceControlCategory(StrEnum):
    """Categories of engineering compliance controls."""

    SECURITY = "SECURITY"
    FINANCIAL_CONTROL = "FINANCIAL_CONTROL"
    ML_GOVERNANCE = "ML_GOVERNANCE"
    DATA_GOVERNANCE = "DATA_GOVERNANCE"
    HUMAN_GOVERNANCE = "HUMAN_GOVERNANCE"


class ComplianceControlStatus(StrEnum):
    """Verification status of a compliance control."""

    PASS = "PASS"
    WARNING = "WARNING"
    FAIL = "FAIL"
    NOT_ASSESSED = "NOT_ASSESSED"


class ComplianceSeverity(StrEnum):
    """Risk severity for compliance findings or control failures."""

    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class CompliancePosture(StrEnum):
    """Overall organizational compliance rating."""

    EXCELLENT = "EXCELLENT"
    GOOD = "GOOD"
    WARNING = "WARNING"
    HIGH_RISK = "HIGH_RISK"
    CRITICAL = "CRITICAL"


class ComplianceControl(BaseModel):
    """Deterministic engineering compliance control evidence model."""

    control_id: str = Field(..., description="Unique control identifier, e.g. SEC-01")
    control_category: ComplianceControlCategory
    control_name: str
    description: str
    status: ComplianceControlStatus
    severity: ComplianceSeverity
    evidence_count: int = Field(default=0)
    last_verified_at: str
    first_detected_at: str
    owner_role: str = Field(default="admin")
    remediation_required: bool = Field(default=False)
    evidence_summary: str


class ComplianceFinding(BaseModel):
    """Specific governance discrepancy or audit anomaly detected."""

    finding_id: str
    control_id: str
    severity: ComplianceSeverity
    category: ComplianceControlCategory
    entity_reference: str
    description: str
    recommended_remediation: str
    detected_at: str


class ComplianceCategoryScore(BaseModel):
    """Score breakdown for a specific compliance domain."""

    category: ComplianceControlCategory
    weight_percentage: float
    score: float = Field(..., ge=0.0, le=100.0)
    controls_count: int
    passing_controls_count: int
    warning_controls_count: int
    failing_controls_count: int


class AuditCoverage(BaseModel):
    """AuditLog completeness telemetry across all required lifecycle event types."""

    total_required_event_categories: int
    observed_event_categories: int
    missing_categories: list[str] = Field(default_factory=list)
    audit_coverage_percentage: float = Field(..., ge=0.0, le=100.0)
    lifecycle_chains_status: dict[str, str] = Field(default_factory=dict)
    total_audit_events_count: int = Field(default=0)
    orphaned_records_count: int = Field(default=0)


class DecisionTraceCompliance(BaseModel):
    """Validation of end-to-end case decision trace provenance."""

    total_resolved_cases_sampled: int
    trace_completeness_rate: float = Field(..., ge=0.0, le=100.0)
    complete_traces_count: int
    partial_traces_count: int
    broken_traces_count: int
    untraced_cases_count: int
    pii_exposed_in_traces: bool = Field(default=False)


class FinancialGovernanceAudit(BaseModel):
    """Audit verifying strict PolicyEngine supremacy and financial isolation."""

    policy_engine_supremacy_verified: bool = Field(default=True)
    unauthorized_financial_mutations_count: int = Field(default=0)
    untracked_actions_count: int = Field(default=0)
    gateway_calls_from_governance_count: int = Field(default=0)
    actions_with_policy_decision_percentage: float = Field(default=100.0)
    status: ComplianceControlStatus = Field(default=ComplianceControlStatus.PASS)


class RBACComplianceAudit(BaseModel):
    """Audit of authentication, role boundaries, and privilege escalation defense."""

    privilege_escalation_attempts_count: int = Field(default=0)
    unauthorized_access_attempts_count: int = Field(default=0)
    revoked_token_rejections_count: int = Field(default=0)
    authoritative_identity_enforced: bool = Field(default=True)
    findings: list[ComplianceFinding] = Field(default_factory=list)
    status: ComplianceControlStatus = Field(default=ComplianceControlStatus.PASS)


class ModelGovernanceCompliance(BaseModel):
    """Validation of the ML Model & Strategy governance progression."""

    dataset_lineage_coverage_pct: float = Field(default=100.0)
    active_champion_has_approved_gates: bool = Field(default=True)
    unapproved_deployments_count: int = Field(default=0)
    active_canary_monitoring_healthy: bool = Field(default=True)
    strategy_recommendations_governed_pct: float = Field(default=100.0)
    status: ComplianceControlStatus = Field(default=ComplianceControlStatus.PASS)


class DataProtectionAudit(BaseModel):
    """Audit verifying zero PII exposure and credential redaction."""

    pii_scanner_active: bool = Field(default=True)
    unmasked_cards_detected_count: int = Field(default=0)
    unmasked_aadhaar_detected_count: int = Field(default=0)
    unmasked_tokens_detected_count: int = Field(default=0)
    unmasked_emails_detected_count: int = Field(default=0)
    status: ComplianceControlStatus = Field(default=ComplianceControlStatus.PASS)


class ComplianceIncident(BaseModel):
    """Deterministic governance incident detected from audit log analysis."""

    incident_id: str
    severity: ComplianceSeverity
    category: ComplianceControlCategory
    title: str
    description: str
    evidence: dict[str, Any] = Field(default_factory=dict)
    affected_entity_type: str
    affected_entity_id: str | None = None
    detected_at: str
    status: str = Field(default="OPEN")
    recommended_action: str


class ComplianceSummary(BaseModel):
    """Executive Compliance & Regulatory Governance Intelligence Summary."""

    compliance_score: float = Field(..., ge=0.0, le=100.0)
    compliance_posture: CompliancePosture
    audit_coverage_percentage: float = Field(..., ge=0.0, le=100.0)
    category_scores: list[ComplianceCategoryScore]
    total_controls_count: int
    passing_controls_count: int
    warning_controls_count: int
    failing_controls_count: int
    open_incidents_count: int
    critical_findings_count: int
    financial_governance: FinancialGovernanceAudit
    rbac_compliance: RBACComplianceAudit
    model_governance: ModelGovernanceCompliance
    data_protection: DataProtectionAudit
    audit_coverage: AuditCoverage
    decision_trace_compliance: DecisionTraceCompliance
    disclaimer: str
    generated_at: str


class ComplianceReport(BaseModel):
    """Exportable comprehensive JSON snapshot of the compliance state."""

    report_id: str
    generated_at: str
    compliance_score: float
    compliance_posture: CompliancePosture
    executive_summary: str
    disclaimer: str
    category_scores: list[ComplianceCategoryScore]
    controls: list[ComplianceControl]
    findings: list[ComplianceFinding]
    incidents: list[ComplianceIncident]
    audit_coverage: AuditCoverage
    decision_trace_compliance: DecisionTraceCompliance
    financial_governance: FinancialGovernanceAudit
    rbac_compliance: RBACComplianceAudit
    model_governance: ModelGovernanceCompliance
    data_protection: DataProtectionAudit
    remediation_roadmap: list[dict[str, Any]] = Field(default_factory=list)
