"""
Phase 10D — Fintech Observability, SRE, Incident Response & Production Operations API Router.

Provides 23 deterministic REST endpoints for real-time observability, SLIs, SLOs,
error budgets, deduplicated alerts, incident command, traces, deployment impact,
subsystem telemetry, readiness gates, and postmortems.
Protected by 3-tier JWT RBAC and sliding-window rate limiting.
"""

import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Path, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.rate_limiter import rate_limit_mutations, rate_limit_reads
from app.core.security import (
    AuthenticatedUser,
    require_admin,
    require_operator,
    require_viewer,
)
from app.schemas.observability import (
    Alert,
    DatabaseTelemetry,
    DeploymentImpact,
    ErrorBudget,
    FinancialPathTelemetry,
    Incident,
    MLTelemetry,
    ObservabilitySummary,
    OperationalReadiness,
    PolicyEngineTelemetry,
    PostIncidentReport,
    PostmortemCreateRequest,
    QueueTelemetry,
    ServiceTelemetry,
    SLIMetric,
    SLOEvaluation,
    TraceSummary,
    WebhookTelemetry,
    WorkerTelemetry,
)
from app.services.observability_service import ObservabilityService

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/recovery/intelligence/observability",
    tags=["fintech-observability"],
)


@router.get(
    "",
    response_model=ObservabilitySummary,
    summary="Get executive observability & SRE summary",
    dependencies=[Depends(rate_limit_reads)],
)
def get_observability_summary(
    current_user: Annotated[AuthenticatedUser, Depends(require_viewer)],
    db: Session = Depends(get_db),
) -> ObservabilitySummary:
    """Retrieve executive summary, 10-pillar score, global operational state, and active alerts."""
    service = ObservabilityService(db)
    return service.get_observability_summary()


@router.get(
    "/services",
    response_model=list[ServiceTelemetry],
    summary="Get telemetry matrix for all 11 dependencies",
    dependencies=[Depends(rate_limit_reads)],
)
def get_services_telemetry(
    current_user: Annotated[AuthenticatedUser, Depends(require_viewer)],
    db: Session = Depends(get_db),
) -> list[ServiceTelemetry]:
    """Retrieve real-time availability, latency, error rates, and throughput for all services."""
    service = ObservabilityService(db)
    return service.collect_service_telemetry()


@router.get(
    "/slis",
    response_model=list[SLIMetric],
    summary="Get the 17 deterministic Service Level Indicators",
    dependencies=[Depends(rate_limit_reads)],
)
def get_slis(
    current_user: Annotated[AuthenticatedUser, Depends(require_viewer)],
    db: Session = Depends(get_db),
) -> list[SLIMetric]:
    """Retrieve all 17 deterministic SLI evaluations with zero-denominator safety."""
    service = ObservabilityService(db)
    return service.calculate_slis()


@router.get(
    "/slos",
    response_model=list[SLOEvaluation],
    summary="Get the 8 Service Level Objectives and compliance evaluations",
    dependencies=[Depends(rate_limit_reads)],
)
def get_slos(
    current_user: Annotated[AuthenticatedUser, Depends(require_viewer)],
    db: Session = Depends(get_db),
) -> list[SLOEvaluation]:
    """Evaluate real-time compliance, compliance deltas, and burn rates for all SLOs."""
    service = ObservabilityService(db)
    return service.evaluate_slos()


@router.get(
    "/error-budget",
    response_model=list[ErrorBudget],
    summary="Get multi-window error budgets and burn rates",
    dependencies=[Depends(rate_limit_reads)],
)
def get_error_budgets(
    current_user: Annotated[AuthenticatedUser, Depends(require_viewer)],
    db: Session = Depends(get_db),
) -> list[ErrorBudget]:
    """Retrieve remaining error budgets and 1h/6h/24h burn rates for each SLO."""
    service = ObservabilityService(db)
    return service.calculate_error_budget()


@router.get(
    "/alerts",
    response_model=list[Alert],
    summary="Get active alerts with SHA-256 deduplication",
    dependencies=[Depends(rate_limit_reads)],
)
def get_alerts(
    current_user: Annotated[AuthenticatedUser, Depends(require_viewer)],
    db: Session = Depends(get_db),
) -> list[Alert]:
    """Retrieve deduplicated, fingerprinted active alerts across services and SLOs."""
    service = ObservabilityService(db)
    return service.detect_alerts()


@router.get(
    "/incidents",
    response_model=list[Incident],
    summary="Get correlated SRE production incidents",
    dependencies=[Depends(rate_limit_reads)],
)
def get_incidents(
    current_user: Annotated[AuthenticatedUser, Depends(require_viewer)],
    db: Session = Depends(get_db),
) -> list[Incident]:
    """Retrieve correlated incidents, MTTA/MTTR metrics, and lifecycle timelines."""
    service = ObservabilityService(db)
    return service.get_incidents()


@router.get(
    "/incidents/{incident_id}",
    response_model=Incident,
    summary="Get single incident detail",
    dependencies=[Depends(rate_limit_reads)],
)
def get_incident_detail(
    incident_id: Annotated[str, Path(..., description="Target incident identifier")],
    current_user: Annotated[AuthenticatedUser, Depends(require_viewer)],
    db: Session = Depends(get_db),
) -> Incident:
    """Retrieve complete details, evidence, and timeline for a specific incident."""
    service = ObservabilityService(db)
    incidents = service.get_incidents()
    for inc in incidents:
        if inc.incident_id == incident_id:
            return inc
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"Incident {incident_id} not found",
    )


@router.get(
    "/traces",
    response_model=list[TraceSummary],
    summary="Get sanitized distributed execution traces",
    dependencies=[Depends(rate_limit_reads)],
)
def get_traces(
    current_user: Annotated[AuthenticatedUser, Depends(require_viewer)],
    db: Session = Depends(get_db),
) -> list[TraceSummary]:
    """Retrieve sanitized end-to-end distributed execution traces with 100% PII redaction."""
    service = ObservabilityService(db)
    return service.get_traces()


@router.get(
    "/deployments",
    response_model=list[DeploymentImpact],
    summary="Get production change-impact telemetry",
    dependencies=[Depends(rate_limit_reads)],
)
def get_deployments(
    current_user: Annotated[AuthenticatedUser, Depends(require_viewer)],
    db: Session = Depends(get_db),
) -> list[DeploymentImpact]:
    """Compare pre vs post deployment performance metrics and view advisory rollback signals."""
    service = ObservabilityService(db)
    return service.analyze_deployment_impact()


@router.get(
    "/readiness",
    response_model=OperationalReadiness,
    summary="Get the 18 operational readiness verification gates",
    dependencies=[Depends(rate_limit_reads)],
)
def get_operational_readiness(
    current_user: Annotated[AuthenticatedUser, Depends(require_viewer)],
    db: Session = Depends(get_db),
) -> OperationalReadiness:
    """Evaluate the 18 operational readiness gates before critical production workflows."""
    service = ObservabilityService(db)
    return service.evaluate_operational_readiness()


@router.get(
    "/postmortems",
    response_model=list[PostIncidentReport],
    summary="Get post-incident review reports",
    dependencies=[Depends(rate_limit_reads)],
)
def get_postmortems(
    current_user: Annotated[AuthenticatedUser, Depends(require_viewer)],
    db: Session = Depends(get_db),
) -> list[PostIncidentReport]:
    """Retrieve historical post-incident review reports from AuditLog."""
    service = ObservabilityService(db)
    return service.get_postmortems()


@router.get(
    "/financial-path",
    response_model=list[FinancialPathTelemetry],
    summary="Get observational financial pipeline telemetry",
    dependencies=[Depends(rate_limit_reads)],
)
def get_financial_path(
    current_user: Annotated[AuthenticatedUser, Depends(require_viewer)],
    db: Session = Depends(get_db),
) -> list[FinancialPathTelemetry]:
    """Retrieve observational latency, success rates, and throughput across the 11 pipeline stages."""
    service = ObservabilityService(db)
    return service.get_financial_path_telemetry()


@router.get(
    "/queues",
    response_model=QueueTelemetry,
    summary="Get queue processing telemetry",
    dependencies=[Depends(rate_limit_reads)],
)
def get_queue_telemetry(
    current_user: Annotated[AuthenticatedUser, Depends(require_viewer)],
    db: Session = Depends(get_db),
) -> QueueTelemetry:
    """Retrieve queue backlog depth, processing latency, and health status."""
    service = ObservabilityService(db)
    return service.evaluate_queue_health()


@router.get(
    "/workers",
    response_model=WorkerTelemetry,
    summary="Get worker pool health telemetry",
    dependencies=[Depends(require_viewer)],
)
def get_worker_telemetry(
    current_user: Annotated[AuthenticatedUser, Depends(require_viewer)],
    db: Session = Depends(get_db),
) -> WorkerTelemetry:
    """Retrieve worker utilization, action success rate, and heartbeat telemetry."""
    service = ObservabilityService(db)
    return service.evaluate_worker_health()


@router.get(
    "/webhooks",
    response_model=WebhookTelemetry,
    summary="Get webhook ingestion telemetry",
    dependencies=[Depends(rate_limit_reads)],
)
def get_webhook_telemetry(
    current_user: Annotated[AuthenticatedUser, Depends(require_viewer)],
    db: Session = Depends(get_db),
) -> WebhookTelemetry:
    """Retrieve Razorpay webhook verification rates and processing latency."""
    service = ObservabilityService(db)
    return service.evaluate_webhook_health()


@router.get(
    "/ml",
    response_model=MLTelemetry,
    summary="Get ML inference observability telemetry",
    dependencies=[Depends(rate_limit_reads)],
)
def get_ml_telemetry(
    current_user: Annotated[AuthenticatedUser, Depends(require_viewer)],
    db: Session = Depends(get_db),
) -> MLTelemetry:
    """Retrieve prediction volume, P95 latency, drift status, and calibration health."""
    service = ObservabilityService(db)
    return service.evaluate_ml_health()


@router.get(
    "/policy",
    response_model=PolicyEngineTelemetry,
    summary="Get PolicyEngine gatekeeper telemetry",
    dependencies=[Depends(rate_limit_reads)],
)
def get_policy_telemetry(
    current_user: Annotated[AuthenticatedUser, Depends(require_viewer)],
    db: Session = Depends(get_db),
) -> PolicyEngineTelemetry:
    """Retrieve PolicyEngine evaluation rates, allow/deny ratios, and decision latency."""
    service = ObservabilityService(db)
    return service.evaluate_policyengine_health()


@router.get(
    "/database",
    response_model=DatabaseTelemetry,
    summary="Get database health telemetry",
    dependencies=[Depends(rate_limit_reads)],
)
def get_database_telemetry(
    current_user: Annotated[AuthenticatedUser, Depends(require_viewer)],
    db: Session = Depends(get_db),
) -> DatabaseTelemetry:
    """Retrieve database connection health, query latency percentiles, and pool status."""
    service = ObservabilityService(db)
    return service.evaluate_database_health()


@router.post(
    "/incidents/{incident_id}/acknowledge",
    response_model=Incident,
    summary="Acknowledge an active SRE incident",
    dependencies=[Depends(rate_limit_mutations)],
)
def acknowledge_incident(
    incident_id: Annotated[str, Path(..., description="Target incident identifier")],
    current_user: Annotated[AuthenticatedUser, Depends(require_operator)],
    db: Session = Depends(get_db),
) -> Incident:
    """Transition incident state to ACKNOWLEDGED and record an immutable audit event."""
    service = ObservabilityService(db)
    return service.acknowledge_incident(incident_id, operator_id=current_user.id)


@router.post(
    "/incidents/{incident_id}/escalate",
    response_model=Incident,
    summary="Escalate incident to Admin / SEV_1 review",
    dependencies=[Depends(rate_limit_mutations)],
)
def escalate_incident(
    incident_id: Annotated[str, Path(..., description="Target incident identifier")],
    current_user: Annotated[AuthenticatedUser, Depends(require_admin)],
    db: Session = Depends(get_db),
) -> Incident:
    """Escalate incident severity to SEV_1 and record an immutable audit event."""
    service = ObservabilityService(db)
    return service.escalate_incident(incident_id, admin_id=current_user.id)


@router.post(
    "/incidents/{incident_id}/resolve",
    response_model=Incident,
    summary="Resolve an active SRE incident",
    dependencies=[Depends(rate_limit_mutations)],
)
def resolve_incident(
    incident_id: Annotated[str, Path(..., description="Target incident identifier")],
    current_user: Annotated[AuthenticatedUser, Depends(require_operator)],
    db: Session = Depends(get_db),
) -> Incident:
    """Transition incident state to RESOLVED and record an immutable audit event."""
    service = ObservabilityService(db)
    return service.resolve_incident(incident_id, operator_id=current_user.id)


@router.post(
    "/postmortems",
    response_model=PostIncidentReport,
    summary="Create a post-incident review report",
    dependencies=[Depends(rate_limit_mutations)],
)
def create_postmortem(
    request: PostmortemCreateRequest,
    current_user: Annotated[AuthenticatedUser, Depends(require_operator)],
    db: Session = Depends(get_db),
) -> PostIncidentReport:
    """Create and persist a structured post-incident report into immutable AuditLog."""
    service = ObservabilityService(db)
    return service.generate_postmortem(request, author_id=current_user.id)
