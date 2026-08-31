"""
Phase 10D — Fintech Observability, SRE, Incident Response & Production Operations Schemas.

Defines deterministic Pydantic schemas for telemetry, SLIs, SLOs, error budgets,
alerts, incident command, traces, deployment impact, readiness, and postmortems.
"""

from typing import Any

from pydantic import BaseModel, Field

from app.models.enums import (
    AlertStatus,
    DeploymentImpactStatus,
    ErrorBudgetStatus,
    MLObservabilityStatus,
    ObservabilityIncidentStatus,
    ObservabilityIncidentType,
    ObservabilitySeverity,
    OperationalReadinessStatus,
    OperationalState,
    PolicyEngineObservabilityStatus,
    QueueHealthStatus,
    RootCauseConfidence,
    SLIStatus,
    SLOStatus,
    SREIncidentSeverity,
    TraceStatus,
    WebhookHealthStatus,
    WorkerHealthStatus,
)


class SLIMetric(BaseModel):
    """Deterministic Service Level Indicator (SLI) metric."""

    sli_code: str = Field(..., description="Unique SLI code")
    service: str = Field(..., description="Service dependency name")
    window: str = Field(
        "5m", description="Aggregation rolling window (e.g. 5m, 1h, 24h)"
    )
    observed_value: float = Field(
        ..., description="Current observed quantitative metric value"
    )
    unit: str = Field(..., description="Unit of measurement (ms, %, rpm, count)")
    threshold: float = Field(..., description="SRE warning/critical threshold value")
    status: SLIStatus = Field(..., description="Operational status of this SLI")
    sample_size: int = Field(0, description="Total sample observations in window")
    timestamp: str = Field(..., description="ISO 8601 evaluation timestamp")


class SLODefinition(BaseModel):
    """Configurable Service Level Objective (SLO) definition."""

    slo_code: str = Field(..., description="Unique SLO code")
    name: str = Field(..., description="Human-readable SLO title")
    service: str = Field(..., description="Target service dependency")
    target_percentage: float = Field(
        ..., description="Objective target percentage (e.g. 99.9%)"
    )
    window: str = Field("30d", description="Compliance evaluation rolling window")
    metric_type: str = Field(
        "AVAILABILITY", description="Metric type (AVAILABILITY, LATENCY, ERROR_RATE)"
    )
    is_engineering_default: bool = Field(
        True, description="True if using RecoverIQ engineering defaults"
    )


class SLOEvaluation(BaseModel):
    """Real-time compliance evaluation for an individual SLO."""

    slo_code: str = Field(..., description="Target SLO code")
    name: str = Field(..., description="SLO name")
    service: str = Field(..., description="Target service")
    target_percentage: float = Field(
        ..., description="Configured SLO target percentage"
    )
    observed_percentage: float = Field(
        ..., description="Real-time observed compliance percentage"
    )
    status: SLOStatus = Field(
        ..., description="Compliance status (COMPLIANT, AT_RISK, BREACHED, UNKNOWN)"
    )
    error_budget_remaining_pct: float = Field(
        ..., description="Remaining error budget percentage"
    )
    burn_rate: float = Field(
        1.0, description="Current error budget burn rate (1.0 = nominal)"
    )
    compliance_delta: float = Field(
        0.0, description="Difference between observed and target"
    )


class ErrorBudget(BaseModel):
    """Multi-window error budget tracking and burn-rate telemetry."""

    slo_code: str = Field(..., description="Associated SLO code")
    name: str = Field(..., description="SLO display name")
    allowed_budget: float = Field(
        ..., description="Total allowable error budget (100 - target)"
    )
    consumed_budget: float = Field(
        ..., description="Currently consumed budget percentage"
    )
    remaining_budget: float = Field(
        ..., description="Remaining error budget percentage"
    )
    consumption_percentage: float = Field(
        ..., description="Budget consumption ratio (0-100%)"
    )
    burn_rate_1h: float = Field(1.0, description="1-hour rolling burn rate")
    burn_rate_6h: float = Field(1.0, description="6-hour rolling burn rate")
    burn_rate_24h: float = Field(1.0, description="24-hour rolling burn rate")
    status: ErrorBudgetStatus = Field(
        ..., description="Error budget health classification"
    )


class ServiceTelemetry(BaseModel):
    """Comprehensive real-time telemetry for a single monitored service dependency."""

    service_name: str = Field(..., description="Service dependency name")
    availability: float = Field(100.0, description="Availability percentage")
    p50_latency_ms: float = Field(0.0, description="50th percentile latency")
    p95_latency_ms: float = Field(0.0, description="95th percentile latency")
    p99_latency_ms: float = Field(0.0, description="99th percentile latency")
    error_rate_pct: float = Field(0.0, description="Error rate percentage")
    throughput_rpm: float = Field(0.0, description="Throughput in requests per minute")
    slo_compliance: SLOStatus = Field(
        SLOStatus.COMPLIANT, description="Overall SLO compliance"
    )
    error_budget_remaining_pct: float = Field(
        100.0, description="Remaining error budget"
    )
    status: SLIStatus = Field(
        SLIStatus.HEALTHY, description="Service health classification"
    )


class Alert(BaseModel):
    """Deterministic alert generated by the observability surveillance engine."""

    alert_id: str = Field(..., description="Deterministic alert identifier")
    fingerprint: str = Field(..., description="SHA-256 deduplication fingerprint")
    rule_code: str = Field(..., description="Alert rule code")
    severity: ObservabilitySeverity = Field(..., description="Alert severity level")
    service: str = Field(..., description="Source service dependency")
    observed_value: float = Field(
        ..., description="Observed metric value triggering alert"
    )
    threshold: float = Field(..., description="Breached threshold value")
    first_detected: str = Field(..., description="ISO 8601 first detection timestamp")
    last_detected: str = Field(..., description="ISO 8601 last detection timestamp")
    occurrence_count: int = Field(1, description="Deduplicated alert occurrence count")
    status: AlertStatus = Field(
        AlertStatus.ACTIVE, description="Alert operational state"
    )
    evidence: dict[str, Any] = Field(
        default_factory=dict, description="Sanitized diagnostic evidence"
    )


class IncidentTimelineEvent(BaseModel):
    """Immutable transition event within an SRE incident lifecycle."""

    event_id: str = Field(..., description="Unique timeline event identifier")
    timestamp: str = Field(..., description="ISO 8601 event timestamp")
    previous_state: str = Field(..., description="Previous incident status")
    new_state: str = Field(..., description="New incident status")
    actor_role: str = Field(
        "SYSTEM", description="Role of the actor triggering transition"
    )
    actor_id: str = Field("system", description="Sanitized user or system identifier")
    note: str = Field("", description="Operational context or resolution notes")


class Incident(BaseModel):
    """Correlated production SRE incident."""

    incident_id: str = Field(..., description="Deterministic incident identifier")
    severity: SREIncidentSeverity = Field(
        ..., description="SRE severity (SEV_1 to SEV_4)"
    )
    incident_type: ObservabilityIncidentType = Field(
        ..., description="Primary incident category"
    )
    title: str = Field(..., description="Human-readable incident summary")
    affected_services: list[str] = Field(
        default_factory=list, description="List of degraded services"
    )
    state: ObservabilityIncidentStatus = Field(
        ..., description="Current lifecycle state"
    )
    detected_at: str = Field(..., description="ISO 8601 detection timestamp")
    acknowledged_at: str | None = Field(
        None, description="ISO 8601 acknowledgment timestamp"
    )
    resolved_at: str | None = Field(None, description="ISO 8601 resolution timestamp")
    mtta_seconds: int | None = Field(
        None, description="Mean Time To Acknowledge in seconds"
    )
    mttr_seconds: int | None = Field(
        None, description="Mean Time To Resolve in seconds"
    )
    slo_impact: str = Field("NONE", description="Impact on service SLOs")
    error_budget_impact: float = Field(
        0.0, description="Percentage of error budget consumed"
    )
    root_cause_category: str = Field(
        "UNKNOWN", description="Primary classified root cause"
    )
    root_cause_confidence: RootCauseConfidence = Field(
        RootCauseConfidence.UNKNOWN, description="Confidence"
    )
    timeline: list[IncidentTimelineEvent] = Field(
        default_factory=list, description="Lifecycle history"
    )
    evidence: dict[str, Any] = Field(
        default_factory=dict, description="Sanitized technical evidence"
    )


class TraceSpan(BaseModel):
    """Sanitized individual span within a distributed trace."""

    span_id: str = Field(..., description="Unique span identifier")
    trace_id: str = Field(..., description="Correlation trace identifier")
    parent_span_id: str | None = Field(None, description="Parent span identifier")
    service: str = Field(..., description="Executing service dependency")
    operation: str = Field(..., description="Executed operation name")
    start_time: str = Field(..., description="ISO 8601 start timestamp")
    duration_ms: float = Field(..., description="Execution duration in milliseconds")
    status: TraceStatus = Field(TraceStatus.OK, description="Span execution status")
    error_details: str | None = Field(None, description="Sanitized error description")


class TraceSummary(BaseModel):
    """Sanitized end-to-end distributed execution trace."""

    trace_id: str = Field(..., description="Correlation trace identifier")
    root_service: str = Field(..., description="Originating service entrypoint")
    total_duration_ms: float = Field(..., description="Total end-to-end trace latency")
    span_count: int = Field(..., description="Total spans in trace")
    status: TraceStatus = Field(TraceStatus.OK, description="Overall trace status")
    start_time: str = Field(..., description="ISO 8601 trace start time")
    spans: list[TraceSpan] = Field(
        default_factory=list, description="Ordered trace spans"
    )


class DeploymentTelemetry(BaseModel):
    """Observational telemetry for a production deployment change event."""

    deployment_id: str = Field(..., description="Deployment identifier")
    service: str = Field(..., description="Target service")
    version: str = Field(..., description="Deployed version tag")
    started_at: str = Field(..., description="ISO 8601 deployment start time")
    completed_at: str | None = Field(None, description="ISO 8601 completion time")
    duration_seconds: int = Field(0, description="Deployment duration")
    status: str = Field("SUCCESS", description="Deployment execution status")
    pre_latency_p95: float = Field(0.0, description="Pre-deployment P95 latency (ms)")
    post_latency_p95: float = Field(0.0, description="Post-deployment P95 latency (ms)")
    latency_delta_ms: float = Field(0.0, description="Latency delta")
    pre_error_rate: float = Field(0.0, description="Pre-deployment error rate (%)")
    post_error_rate: float = Field(0.0, description="Post-deployment error rate (%)")
    error_delta_pct: float = Field(0.0, description="Error rate delta")
    rollback_signal: str = Field(
        "STABLE", description="Advisory signal (STABLE, ROLLBACK_RECOMMENDED)"
    )


class DeploymentImpact(BaseModel):
    """Change-impact analysis comparing pre vs post deployment operational metrics."""

    deployment_id: str = Field(..., description="Deployment identifier")
    service: str = Field(..., description="Deployed service")
    version: str = Field(..., description="Version tag")
    impact_status: DeploymentImpactStatus = Field(
        ..., description="Impact classification"
    )
    latency_delta_pct: float = Field(0.0, description="Percentage change in latency")
    error_rate_delta_pct: float = Field(
        0.0, description="Percentage change in error rate"
    )
    slo_delta_pct: float = Field(0.0, description="Percentage change in SLO compliance")
    rollback_recommended: bool = Field(
        False, description="Advisory rollback recommendation signal"
    )
    evidence: dict[str, Any] = Field(
        default_factory=dict, description="Sanitized comparative telemetry"
    )


class OperationalReadinessGate(BaseModel):
    """Pre-flight operational readiness verification gate."""

    gate_code: str = Field(..., description="Gate identifier code")
    gate_name: str = Field(..., description="Human-readable gate title")
    status: OperationalReadinessStatus = Field(
        ..., description="Gate status (READY, CONDITIONAL, BLOCKED)"
    )
    observed_value: str = Field(..., description="Observed operational metric")
    threshold: str = Field(..., description="Required readiness threshold")
    severity: ObservabilitySeverity = Field(..., description="Severity if failing")
    evidence: str = Field(..., description="Verification evidence summary")
    remediation: str = Field("", description="Remediation instructions if not ready")


class OperationalReadiness(BaseModel):
    """Comprehensive evaluation of all 18 operational readiness gates."""

    overall_status: OperationalReadinessStatus = Field(
        ..., description="Overall readiness status"
    )
    gates: list[OperationalReadinessGate] = Field(
        default_factory=list, description="18 evaluated gates"
    )
    ready_count: int = Field(0, description="Number of passing gates")
    conditional_count: int = Field(0, description="Number of conditional gates")
    blocked_count: int = Field(0, description="Number of blocked gates")
    readiness_percentage: float = Field(0.0, description="Readiness percentage score")


class IncidentResponseSLA(BaseModel):
    """Operational MTTA, MTTI, and MTTR compliance metrics."""

    mtta_observed_seconds: int = Field(
        0, description="Mean Time To Acknowledge (seconds)"
    )
    mtta_target_seconds: int = Field(300, description="MTTA Target SLA (300s = 5 min)")
    mtta_status: SLOStatus = Field(SLOStatus.COMPLIANT, description="MTTA SLA status")
    mtti_observed_seconds: int = Field(
        0, description="Mean Time To Investigate (seconds)"
    )
    mtti_target_seconds: int = Field(900, description="MTTI Target SLA (900s = 15 min)")
    mtti_status: SLOStatus = Field(SLOStatus.COMPLIANT, description="MTTI SLA status")
    mttr_observed_seconds: int = Field(0, description="Mean Time To Resolve (seconds)")
    mttr_target_seconds: int = Field(3600, description="MTTR Target SLA (3600s = 1 hr)")
    mttr_status: SLOStatus = Field(SLOStatus.COMPLIANT, description="MTTR SLA status")


class PostmortemCreateRequest(BaseModel):
    """Operator request body to create a post-incident review report."""

    incident_id: str = Field(..., description="Target incident identifier")
    title: str = Field(..., description="Postmortem title")
    impact_summary: str = Field(..., description="Executive operational impact summary")
    root_cause_category: str = Field(..., description="Identified root cause category")
    contributing_factors: list[str] = Field(
        default_factory=list, description="Contributing technical factors"
    )
    corrective_actions: list[str] = Field(
        default_factory=list, description="Remediation steps completed"
    )
    preventive_actions: list[str] = Field(
        default_factory=list, description="Action items to prevent recurrence"
    )


class PostIncidentReport(BaseModel):
    """Structured post-incident review (postmortem) report."""

    postmortem_id: str = Field(..., description="Unique postmortem identifier")
    incident_id: str = Field(..., description="Target incident identifier")
    title: str = Field(..., description="Postmortem title")
    timeline: list[IncidentTimelineEvent] = Field(
        default_factory=list, description="Complete incident timeline"
    )
    impact_summary: str = Field(..., description="Impact summary")
    affected_services: list[str] = Field(
        default_factory=list, description="Affected services"
    )
    root_cause_category: str = Field(..., description="Classified root cause category")
    root_cause_confidence: RootCauseConfidence = Field(
        RootCauseConfidence.CONFIRMED, description="Confidence"
    )
    contributing_factors: list[str] = Field(
        default_factory=list, description="Contributing factors"
    )
    detection_gap: str = Field(
        "None detected", description="Gap in detection mechanisms"
    )
    response_gap: str = Field("None detected", description="Gap in response procedures")
    resolution_summary: str = Field(..., description="Technical resolution summary")
    slo_impact: str = Field("None", description="Impact on SLO metrics")
    error_budget_impact: float = Field(
        0.0, description="Consumed error budget percentage"
    )
    corrective_actions: list[str] = Field(
        default_factory=list, description="Immediate corrective actions"
    )
    preventive_actions: list[str] = Field(
        default_factory=list, description="Preventive architectural items"
    )
    author_id: str = Field("operator", description="Author operator identifier")
    approved_by: str | None = Field(None, description="Admin approver identifier")
    status: str = Field(
        "DRAFT", description="Report status (DRAFT, APPROVED, PUBLISHED)"
    )
    created_at: str = Field(..., description="ISO 8601 creation timestamp")


class RootCauseAnalysis(BaseModel):
    """Deterministic ranking of potential incident root causes."""

    incident_id: str = Field(..., description="Target incident identifier")
    primary_category: str = Field(..., description="Top ranked root cause category")
    confidence: RootCauseConfidence = Field(..., description="Confidence ranking")
    secondary_factors: list[str] = Field(
        default_factory=list, description="Secondary contributing factors"
    )
    evidence_score: float = Field(
        100.0, description="Calculated evidence strength score (0-100)"
    )


class FinancialPathTelemetry(BaseModel):
    """Observational telemetry for one stage in the financial recovery pipeline."""

    stage_name: str = Field(..., description="Pipeline stage name")
    latency_ms: float = Field(0.0, description="Stage processing latency (ms)")
    success_rate_pct: float = Field(100.0, description="Stage execution success rate")
    error_rate_pct: float = Field(0.0, description="Stage error rate")
    throughput_rpm: float = Field(
        0.0, description="Throughput rate in requests per minute"
    )
    health_status: SLIStatus = Field(
        SLIStatus.HEALTHY, description="Stage health status"
    )


class QueueTelemetry(BaseModel):
    """Observational telemetry for background task and action queues."""

    queue_depth: int = Field(0, description="Current pending jobs/actions count")
    oldest_job_age_seconds: int = Field(
        0, description="Age of oldest pending job in queue"
    )
    jobs_processed_last_hour: int = Field(
        0, description="Total jobs processed in last hour"
    )
    jobs_failed_last_hour: int = Field(0, description="Total jobs failed in last hour")
    processing_latency_ms: float = Field(
        0.0, description="Average queue processing latency"
    )
    health_status: QueueHealthStatus = Field(
        QueueHealthStatus.QUEUE_HEALTHY, description="Queue status"
    )


class WorkerTelemetry(BaseModel):
    """Observational telemetry for background recovery workers."""

    active_workers: int = Field(1, description="Active worker process count")
    utilization_pct: float = Field(
        0.0, description="Worker pool CPU/capacity utilization"
    )
    success_rate_pct: float = Field(100.0, description="Worker action success rate")
    processing_latency_ms: float = Field(
        0.0, description="Average action execution latency"
    )
    last_heartbeat: str = Field(..., description="ISO 8601 last heartbeat timestamp")
    health_status: WorkerHealthStatus = Field(
        WorkerHealthStatus.HEALTHY, description="Worker status"
    )


class WebhookTelemetry(BaseModel):
    """Observational telemetry for Razorpay webhook ingestion."""

    webhooks_received: int = Field(0, description="Total webhooks received")
    webhooks_verified: int = Field(0, description="HMAC-verified webhooks count")
    webhooks_rejected: int = Field(0, description="Signature failed/rejected count")
    webhooks_failed: int = Field(0, description="Processing error count")
    processing_latency_ms: float = Field(0.0, description="Average ingestion latency")
    duplicate_rate_pct: float = Field(0.0, description="Duplicate webhook rate")
    replay_rejection_rate_pct: float = Field(0.0, description="Replay rejection rate")
    health_status: WebhookHealthStatus = Field(
        WebhookHealthStatus.HEALTHY, description="Webhook status"
    )


class MLTelemetry(BaseModel):
    """Observational telemetry for ML scoring and model inference."""

    prediction_count: int = Field(0, description="Total ML predictions served")
    p95_latency_ms: float = Field(0.0, description="P95 inference latency (ms)")
    error_rate_pct: float = Field(0.0, description="Model inference error rate")
    drift_status: str = Field("STABLE", description="Model drift detection status")
    calibration_status: str = Field(
        "CALIBRATED", description="Probability calibration status"
    )
    active_model_version: str = Field(
        "v1.0", description="Active champion model version"
    )
    health_status: MLObservabilityStatus = Field(
        MLObservabilityStatus.MODEL_HEALTHY, description="Status"
    )


class PolicyEngineTelemetry(BaseModel):
    """Observational telemetry for PolicyEngine safety gatekeeper."""

    evaluation_count: int = Field(0, description="Total policy evaluations executed")
    allow_rate_pct: float = Field(
        100.0, description="Percentage of evaluations resulting in ALLOWED"
    )
    deny_rate_pct: float = Field(
        0.0, description="Percentage of evaluations resulting in DENIED"
    )
    error_rate_pct: float = Field(0.0, description="Evaluation error rate")
    p95_latency_ms: float = Field(0.0, description="P95 policy evaluation latency")
    timeout_rate_pct: float = Field(0.0, description="Evaluation timeout rate")
    health_status: PolicyEngineObservabilityStatus = Field(
        PolicyEngineObservabilityStatus.POLICY_HEALTHY,
        description="PolicyEngine status",
    )


class DatabaseTelemetry(BaseModel):
    """Observational telemetry for relational database health."""

    connection_health: str = Field(
        "CONNECTED", description="Database connection pool status"
    )
    query_p95_latency_ms: float = Field(0.0, description="P95 query latency (ms)")
    transaction_failure_rate_pct: float = Field(
        0.0, description="Transaction rollback/failure rate"
    )
    slow_query_count: int = Field(0, description="Queries exceeding 100ms in window")
    pool_utilization_pct: float = Field(
        0.0, description="Connection pool utilization percentage"
    )
    health_status: SLIStatus = Field(
        SLIStatus.HEALTHY, description="Database health status"
    )


class ObservabilityScoreBreakdown(BaseModel):
    """Deterministic component breakdown of the unified Observability Health Score."""

    availability_score: float = Field(
        100.0, description="Availability pillar (Weight: 0.15)"
    )
    latency_score: float = Field(100.0, description="Latency pillar (Weight: 0.15)")
    error_rate_score: float = Field(
        100.0, description="Error rate pillar (Weight: 0.15)"
    )
    throughput_score: float = Field(
        100.0, description="Throughput pillar (Weight: 0.10)"
    )
    slo_compliance_score: float = Field(
        100.0, description="SLO compliance pillar (Weight: 0.10)"
    )
    error_budget_score: float = Field(
        100.0, description="Error budget pillar (Weight: 0.10)"
    )
    dependency_score: float = Field(
        100.0, description="Dependency health pillar (Weight: 0.10)"
    )
    queue_health_score: float = Field(
        100.0, description="Queue health pillar (Weight: 0.05)"
    )
    worker_health_score: float = Field(
        100.0, description="Worker health pillar (Weight: 0.05)"
    )
    incident_stability_score: float = Field(
        100.0, description="Incident stability pillar (Weight: 0.05)"
    )


class ObservabilitySummary(BaseModel):
    """Executive summary response for the Fintech Observability & SRE Control Plane."""

    observability_score: float = Field(..., description="Overall score [0.0 - 100.0]")
    global_state: OperationalState = Field(
        ..., description="Priority-evaluated global operational state"
    )
    score_breakdown: ObservabilityScoreBreakdown = Field(
        ..., description="Component scores"
    )
    services: list[ServiceTelemetry] = Field(
        default_factory=list, description="Service dependency telemetry"
    )
    active_incidents_count: int = Field(0, description="Active SRE incidents count")
    critical_incidents_count: int = Field(
        0, description="SEV_1 and SEV_2 critical incidents count"
    )
    slo_compliance_pct: float = Field(
        100.0, description="Aggregate SLO compliance percentage"
    )
    remaining_error_budget_pct: float = Field(
        100.0, description="Average remaining error budget"
    )
    p95_latency_ms: float = Field(
        0.0, description="Aggregate P95 latency across all APIs"
    )
    aggregate_error_rate_pct: float = Field(
        0.0, description="Aggregate error rate across all requests"
    )
    operational_readiness_pct: float = Field(
        100.0, description="Operational readiness percentage"
    )
    last_evaluated_at: str = Field(..., description="ISO 8601 evaluation timestamp")
    disclaimer: str = Field(
        "This dashboard provides automated engineering observability and SRE telemetry. "
        "It does not constitute third-party legal, regulatory, or operational certification. "
        "PolicyEngine remains the sole authoritative gatekeeper for recovery actions. "
        "The observability subsystem is strictly observational and produces zero financial mutations.",
        description="Mandatory engineering evidence notice",
    )
