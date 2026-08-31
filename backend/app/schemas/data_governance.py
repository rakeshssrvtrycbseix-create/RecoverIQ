"""Pydantic schemas for Phase 10E Data Governance, Privacy Engineering & Data Lineage."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from app.models.enums import (
    DataClassification,
    DataDomain,
    DataOwnerRole,
    DataQualityStatus,
    GovernanceScoreClassification,
    LineageNodeType,
    PrivacyControlStatus,
    PrivacyIncidentSeverity,
    PrivacyRequestStatus,
    PrivacyRequestType,
    ProcessingPurpose,
    RetentionStatus,
)


class DataFieldClassification(BaseModel):
    """Schema for individual field-level sensitivity classification."""

    field_name: str
    asset_name: str
    classification: DataClassification
    sensitivity: str
    pii_category: str | None = None
    financial_sensitivity: bool = False
    masking_requirement: str = "NONE"
    encryption_requirement: str = "IN_TRANSIT_AND_AT_REST"
    retention_requirement: str = "POLICY_DEFAULT"


class DataAsset(BaseModel):
    """Schema for registered data assets across RecoverIQ."""

    asset_id: str
    asset_name: str
    domain: DataDomain
    classification: DataClassification
    owner_role: DataOwnerRole
    processing_purpose: ProcessingPurpose
    contains_pii: bool
    contains_financial_data: bool
    contains_credentials: bool
    retention_policy: str
    record_count: int = 0
    storage_type: str = "RELATIONAL_SQL"
    encryption_status: str = "ENCRYPTED_AT_REST"
    created_at: datetime
    last_scanned_at: datetime
    fields: list[DataFieldClassification] = Field(default_factory=list)


class DataAssetSummary(BaseModel):
    """Summary record for data asset registry view."""

    asset_id: str
    asset_name: str
    domain: DataDomain
    classification: DataClassification
    owner_role: DataOwnerRole
    processing_purpose: ProcessingPurpose
    contains_pii: bool
    contains_financial_data: bool
    contains_credentials: bool
    retention_status: RetentionStatus
    record_count: int
    last_scanned_at: datetime


class DataLineageNode(BaseModel):
    """Node in the end-to-end data transformation lineage graph."""

    node_id: str
    node_type: LineageNodeType
    name: str
    domain: DataDomain
    source_system: str
    transformation: str
    schema_version: str
    checksum: str
    timestamp: datetime
    metadata: dict[str, Any] = Field(default_factory=dict)


class DataLineageEdge(BaseModel):
    """Directed edge representing data flow or transformation between lineage nodes."""

    edge_id: str
    source_node_id: str
    destination_node_id: str
    transformation_type: str
    transformation_hash: str
    timestamp: datetime


class DataLineageGraph(BaseModel):
    """End-to-end provenance and data transformation lineage graph."""

    graph_id: str
    nodes: list[DataLineageNode] = Field(default_factory=list)
    edges: list[DataLineageEdge] = Field(default_factory=list)
    integrity_status: str = "VERIFIED"
    orphan_nodes_count: int = 0
    broken_links_count: int = 0
    coverage_pct: float = 100.0
    generated_at: datetime


class RetentionPolicy(BaseModel):
    """Governance retention policy definition for a data domain."""

    policy_id: str
    domain: DataDomain
    retention_duration_days: int
    legal_hold_active: bool = False
    statutory_basis: str
    deletion_workflow: str = "ADVISORY_GOVERNED_REVIEW"


class RetentionAssetStatus(BaseModel):
    """Retention status and expiration evaluation for an individual asset or dataset."""

    asset_id: str
    asset_name: str
    domain: DataDomain
    policy_id: str
    retention_duration_days: int
    oldest_record_at: datetime
    expiration_at: datetime
    status: RetentionStatus
    legal_hold: bool
    deletion_eligible: bool
    reason: str


class PrivacyControl(BaseModel):
    """Automated privacy, classification, or data-governance verification control."""

    control_id: str
    name: str
    category: str
    status: PrivacyControlStatus
    severity: PrivacyIncidentSeverity
    observed_value: str
    threshold: str
    evidence: str
    remediation: str


class PrivacyIncident(BaseModel):
    """Privacy, secret-leakage, or data-lineage incident."""

    incident_id: str
    severity: PrivacyIncidentSeverity
    category: str
    title: str
    affected_asset: str
    detection_timestamp: datetime
    status: str
    evidence_hash: str
    remediation_state: str
    details: str


class PrivacyRequest(BaseModel):
    """Subject rights and data governance request record."""

    request_id: str
    request_type: PrivacyRequestType
    status: PrivacyRequestStatus
    subject_pseudonym: str
    scope: str
    received_at: datetime
    reviewed_at: datetime | None = None
    completed_at: datetime | None = None
    actor_id: str
    actor_role: str
    erasure_eligible: bool = False
    evidence_reference: str
    notes: str | None = None


class PrivacyRequestCreate(BaseModel):
    """Payload to create a new privacy/governance request."""

    request_type: PrivacyRequestType
    subject_id: str
    scope: str = "FULL_RECOVERIQ_DATASET"
    notes: str | None = None


class PrivacyRequestReview(BaseModel):
    """Payload to review/approve/reject a privacy request."""

    decision: str = Field(..., pattern="^(APPROVE|REJECT)$")
    notes: str


class PrivacyRequestComplete(BaseModel):
    """Payload to complete an approved privacy request."""

    notes: str


class DataQualityMetric(BaseModel):
    """Data quality, freshness, and consistency metrics."""

    completeness_pct: float
    validity_pct: float
    uniqueness_pct: float
    consistency_pct: float
    freshness_seconds: int
    anomaly_rate_pct: float
    score: float
    status: DataQualityStatus
    details: dict[str, Any] = Field(default_factory=dict)


class PIIScanFinding(BaseModel):
    """Individual PII or secret discovery finding with masked representation."""

    field_path: str
    detected_category: str
    severity: PrivacyIncidentSeverity
    masked_value: str
    evidence_hash: str


class PIIScanRequest(BaseModel):
    """Request payload for on-demand PII and secret discovery scan."""

    payload: dict[str, Any] | list[Any] | str


class PIIScanResponse(BaseModel):
    """Sanitized response from PII scanner containing zero raw secrets."""

    findings_count: int
    findings: list[PIIScanFinding] = Field(default_factory=list)
    has_critical_findings: bool
    scanned_fields_count: int
    scan_duration_ms: float
    disclaimer: str = "Purely observational PII discovery scan. Zero payload data is persisted or returned in raw form."


class ErasureEligibilityEvaluation(BaseModel):
    """Advisory evaluation for subject erasure eligibility."""

    subject_pseudonym: str
    eligible_for_erasure: bool
    legal_hold_active: bool
    financial_record_retention_required: bool
    audit_retention_required: bool
    blocker_reasons: list[str] = Field(default_factory=list)
    advisory_notice: str = "Advisory evaluation only. Phase 10E does not execute automated deletions on financial or audit ledgers."


class DataGovernanceScoreBreakdown(BaseModel):
    """Score breakdown across the 8 data governance pillars."""

    privacy_controls_score: float
    data_quality_score: float
    data_lineage_score: float
    retention_score: float
    access_governance_score: float
    security_controls_score: float
    audit_coverage_score: float
    data_minimization_score: float


class DataGovernanceSummary(BaseModel):
    """Top-level governance posture and metrics summary."""

    governance_score: float
    classification: GovernanceScoreClassification
    score_breakdown: DataGovernanceScoreBreakdown
    total_assets_count: int
    sensitive_assets_count: int
    lineage_coverage_pct: float
    retention_compliance_pct: float
    data_quality_score: float
    data_quality_status: DataQualityStatus
    active_privacy_incidents_count: int
    pending_privacy_requests_count: int
    controls_passed_count: int
    controls_total_count: int
    last_scanned_at: datetime
    disclaimer: str = (
        "Engineering data-governance and operational privacy evidence only. "
        "This system does not constitute legal, regulatory, privacy, or third-party certification. "
        "PolicyEngine remains the sole authoritative gatekeeper. Phase 10E produces zero financial mutations."
    )


class DataGovernanceReport(BaseModel):
    """Deterministic exportable snapshot of complete data governance posture."""

    report_id: str
    generated_at: datetime
    generated_by: str
    summary: DataGovernanceSummary
    assets: list[DataAssetSummary]
    controls: list[PrivacyControl]
    data_quality: DataQualityMetric
    retention_statuses: list[RetentionAssetStatus]
    incidents: list[PrivacyIncident]
    privacy_requests: list[PrivacyRequest]
    remediation_roadmap: list[str]
    verification_signature: str
