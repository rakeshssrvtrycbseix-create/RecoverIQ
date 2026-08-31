from typing import Any

from pydantic import BaseModel, Field

from app.models.enums import (
    SecurityControlStatus,
    SecurityEventType,
    SecurityThreatSeverity,
)


class SecurityControlHealth(BaseModel):
    """Health and enforcement telemetry for a specific security control."""

    control_name: str
    status: SecurityControlStatus
    description: str
    enforcement_type: str
    metrics: dict[str, Any] = Field(default_factory=dict)


class SecurityEventResponse(BaseModel):
    """Normalized security audit event logged in the immutable audit trail."""

    id: int
    event_type: SecurityEventType
    severity: SecurityThreatSeverity
    actor_id: str
    actor_type: str
    details: dict[str, Any] = Field(default_factory=dict)
    created_at: str


class PaginatedSecurityEventsResponse(BaseModel):
    """Paginated list of security audit events."""

    items: list[SecurityEventResponse]
    total: int
    page: int = 1
    page_size: int = 50


class TrustCenterOverviewResponse(BaseModel):
    """Executive Fintech Trust Center telemetry and security posture overview."""

    trust_score: float = Field(
        ...,
        ge=0.0,
        le=100.0,
        description="Overall security posture trust score (0-100)",
    )
    threat_level: str = Field(
        "NOMINAL", description="Current threat level: NOMINAL | ELEVATED | CRITICAL"
    )
    active_controls_count: int
    controls: list[SecurityControlHealth]
    total_security_events_24h: int
    blocked_attacks_count: int
    pii_leak_count: int = Field(
        0, description="PII leaks detected in responses/logs (Target: strictly 0)"
    )
    financial_isolation_guaranteed: bool = Field(
        True,
        description="Strict guarantee that security layer never mutates financials",
    )
    policy_engine_supremacy: bool = Field(
        True, description="Confirmation that PolicyEngine is sole financial authority"
    )
    disclaimer: str
    generated_at: str


class TokenRevocationRequest(BaseModel):
    """Request to revoke an active JWT token identifier (jti)."""

    jti: str = Field(
        ...,
        min_length=8,
        max_length=64,
        description="JWT Unique Identifier (jti) to revoke",
    )
    reason: str = Field("Operator manual revocation", min_length=3, max_length=256)


class TokenRevocationResponse(BaseModel):
    """Confirmation of token revocation."""

    jti: str
    revoked: bool
    revoked_at: str
    revoked_by: str
    message: str


class PIIScanRequest(BaseModel):
    """On-demand payload scan request for testing PII and secret redaction."""

    payload: Any


class PIIScanResponse(BaseModel):
    """Scan and sanitization report for a tested payload."""

    has_pii: bool
    has_secrets: bool
    findings_count: int
    findings: list[dict[str, Any]] = Field(default_factory=list)
    sanitized_payload: Any
    scan_timestamp: str
