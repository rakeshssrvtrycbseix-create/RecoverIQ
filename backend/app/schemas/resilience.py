from typing import Any

from pydantic import BaseModel, Field


class ResilienceServiceHealth(BaseModel):
    """Health status of an individual service dependency."""

    service_name: str
    status: str  # ServiceHealthStatus value
    latency_ms: int = Field(default=0, ge=0)
    last_success_timestamp: str | None = None
    last_failure_timestamp: str | None = None
    consecutive_failures: int = Field(default=0, ge=0)
    availability_percentage: float = Field(default=100.0, ge=0.0, le=100.0)
    severity: str  # ResilienceSeverity value
    diagnostic_code: str = Field(default="OK")


class ResilienceIncident(BaseModel):
    """Operational resilience incident with lifecycle tracking."""

    incident_id: str
    incident_type: str  # ResilienceIncidentType value
    severity: str  # ResilienceSeverity value
    state: str  # ResilienceIncidentStatus value
    detected_at: str
    acknowledged_at: str | None = None
    resolved_at: str | None = None
    affected_services: list[str] = Field(default_factory=list)
    root_cause_category: str = ""
    evidence: dict[str, Any] = Field(default_factory=dict)
    operator: str | None = None
    rto_impact_seconds: int | None = None
    rpo_impact_seconds: int | None = None
    escalation_level: str = "NONE"
    recommended_action: str = ""


class ResilienceReadinessGate(BaseModel):
    """Individual disaster recovery readiness gate evaluation."""

    gate_code: str
    gate_name: str
    status: str  # ReadinessStatus value
    observed_value: str = ""
    threshold: str = ""
    severity: str  # ResilienceSeverity value
    evidence: str = ""
    remediation: str = ""


class ResilienceReadiness(BaseModel):
    """Aggregate disaster recovery readiness across all 15 gates."""

    overall_status: str  # ReadinessStatus value
    gates: list[ResilienceReadinessGate]
    ready_count: int = Field(default=0, ge=0)
    conditional_count: int = Field(default=0, ge=0)
    blocked_count: int = Field(default=0, ge=0)
    unknown_count: int = Field(default=0, ge=0)
    readiness_percentage: float = Field(default=0.0, ge=0.0, le=100.0)


class BackupVerification(BaseModel):
    """Backup integrity and restore readiness verification."""

    backup_id: str
    backup_timestamp: str
    backup_age_seconds: int = Field(default=0, ge=0)
    freshness_status: str  # BackupFreshnessStatus value
    integrity_status: str  # BackupIntegrityStatus value
    checksum_sha256: str = ""
    restore_test_status: str  # RestoreVerificationStatus value
    restore_test_timestamp: str | None = None
    restore_duration_seconds: int | None = None
    restore_validation_status: str = "UNVERIFIED"
    rpo_impact_assessment: str = ""


class RTORPOStatus(BaseModel):
    """Recovery Time Objective and Recovery Point Objective compliance status."""

    rto_target_seconds: int
    rto_observed_seconds: int
    rto_compliance: str  # RTORPOComplianceStatus value
    rpo_target_seconds: int
    rpo_observed_seconds: int
    rpo_compliance: str  # RTORPOComplianceStatus value
    historical_rto_breaches: int = Field(default=0, ge=0)
    historical_rpo_breaches: int = Field(default=0, ge=0)
    last_rto_breach_at: str | None = None
    last_rpo_breach_at: str | None = None


class DisasterSimulationRequest(BaseModel):
    """Request payload for running an observational disaster simulation."""

    scenario_type: str  # DisasterScenarioType value
    severity_override: str | None = None  # ResilienceSeverity value


class BlastRadiusAnalysis(BaseModel):
    """Dependency graph impact analysis for a disaster scenario."""

    directly_affected_services: list[str] = Field(default_factory=list)
    indirectly_affected_services: list[str] = Field(default_factory=list)
    critical_path_dependencies: list[str] = Field(default_factory=list)
    financial_path_dependencies: list[str] = Field(default_factory=list)
    non_financial_dependencies: list[str] = Field(default_factory=list)
    blast_radius_percentage: float = Field(default=0.0, ge=0.0, le=100.0)


class DisasterSimulationResult(BaseModel):
    """Result of a safe observational disaster simulation."""

    scenario_id: str
    scenario_type: str  # DisasterScenarioType value
    severity: str  # ResilienceSeverity value
    affected_services: list[str] = Field(default_factory=list)
    blast_radius: BlastRadiusAnalysis
    estimated_rto_seconds: int = Field(default=0, ge=0)
    estimated_rpo_seconds: int = Field(default=0, ge=0)
    recovery_steps: list[str] = Field(default_factory=list)
    financial_isolation_status: str = "VERIFIED"
    readiness_status: str  # ReadinessStatus value
    recommended_human_actions: list[str] = Field(default_factory=list)
    simulation_type: str = "OBSERVATIONAL"
    disclaimer: str = (
        "OBSERVATIONAL SIMULATION — No production services are disabled. "
        "No financial actions are executed. No payment state is modified."
    )


class RecoveryRunbook(BaseModel):
    """Structured recovery runbook for a specific disaster scenario."""

    runbook_id: str
    scenario: str
    preconditions: list[str] = Field(default_factory=list)
    ordered_steps: list[str] = Field(default_factory=list)
    verification_steps: list[str] = Field(default_factory=list)
    rollback_steps: list[str] = Field(default_factory=list)
    required_role: str = "operator"
    estimated_duration_minutes: int = Field(default=0, ge=0)
    rto_target_seconds: int = Field(default=0, ge=0)
    rpo_target_seconds: int = Field(default=0, ge=0)


class ResilienceScoreBreakdown(BaseModel):
    """Weighted component scores contributing to the overall resilience score."""

    availability_score: float = Field(default=100.0, ge=0.0, le=100.0)
    dependency_health_score: float = Field(default=100.0, ge=0.0, le=100.0)
    recovery_readiness_score: float = Field(default=100.0, ge=0.0, le=100.0)
    rto_compliance_score: float = Field(default=100.0, ge=0.0, le=100.0)
    rpo_compliance_score: float = Field(default=100.0, ge=0.0, le=100.0)
    queue_health_score: float = Field(default=100.0, ge=0.0, le=100.0)
    audit_continuity_score: float = Field(default=100.0, ge=0.0, le=100.0)
    incident_stability_score: float = Field(default=100.0, ge=0.0, le=100.0)


class ResilienceSummary(BaseModel):
    """Executive operational resilience summary and intelligence."""

    resilience_score: float = Field(..., ge=0.0, le=100.0)
    global_state: str  # ResilienceState value
    score_breakdown: ResilienceScoreBreakdown
    services: list[ResilienceServiceHealth]
    active_incidents_count: int = Field(default=0, ge=0)
    critical_incidents_count: int = Field(default=0, ge=0)
    dr_readiness_percentage: float = Field(default=0.0, ge=0.0, le=100.0)
    rto_compliance: str  # RTORPOComplianceStatus value
    rpo_compliance: str  # RTORPOComplianceStatus value
    service_availability_percentage: float = Field(default=100.0, ge=0.0, le=100.0)
    dependency_health_status: str  # DependencyStatus value
    backup_freshness: str  # BackupFreshnessStatus value
    last_evaluated_at: str
    disclaimer: str = (
        "This dashboard provides automated engineering resilience evidence "
        "and operational governance. It does not constitute legal, regulatory, "
        "disaster-recovery, business-continuity, or third-party certification."
    )
