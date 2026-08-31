import logging
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Path, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.rate_limiter import rate_limit_mutations, rate_limit_reads
from app.core.security import (
    AuthenticatedUser,
    require_admin,
    require_operator,
    require_viewer,
)
from app.schemas.resilience import (
    BackupVerification,
    DisasterSimulationRequest,
    DisasterSimulationResult,
    RecoveryRunbook,
    ResilienceIncident,
    ResilienceReadiness,
    ResilienceServiceHealth,
    ResilienceSummary,
    RTORPOStatus,
)
from app.services.resilience_service import ResilienceService

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/recovery/intelligence/resilience",
    tags=["operational-resilience"],
)


@router.get(
    "",
    response_model=ResilienceSummary,
    summary="Get executive operational resilience summary",
    dependencies=[Depends(rate_limit_reads)],
)
def get_resilience_summary(
    current_user: Annotated[AuthenticatedUser, Depends(require_viewer)],
    db: Session = Depends(get_db),
) -> ResilienceSummary:
    """Retrieve deterministic executive resilience summary, score, and global state."""
    service = ResilienceService(db)
    return service.get_resilience_summary()


@router.get(
    "/services",
    response_model=list[ResilienceServiceHealth],
    summary="Get service health matrix for all 11 dependencies",
    dependencies=[Depends(rate_limit_reads)],
)
def get_service_health(
    current_user: Annotated[AuthenticatedUser, Depends(require_viewer)],
    db: Session = Depends(get_db),
) -> list[ResilienceServiceHealth]:
    """Retrieve health status of all monitored service dependencies."""
    service = ResilienceService(db)
    return service.evaluate_service_health()


@router.get(
    "/incidents",
    response_model=list[ResilienceIncident],
    summary="Get active operational resilience incidents",
    dependencies=[Depends(rate_limit_reads)],
)
def get_resilience_incidents(
    current_user: Annotated[AuthenticatedUser, Depends(require_viewer)],
    db: Session = Depends(get_db),
    severity: str | None = Query(None, description="Filter by severity"),
) -> list[ResilienceIncident]:
    """Retrieve active and historical resilience incidents."""
    service = ResilienceService(db)
    incidents = service.get_incidents()
    if severity and severity != "ALL":
        incidents = [i for i in incidents if i.severity == severity]
    return incidents


@router.get(
    "/readiness",
    response_model=ResilienceReadiness,
    summary="Get disaster recovery readiness across all 15 gates",
    dependencies=[Depends(rate_limit_reads)],
)
def get_dr_readiness(
    current_user: Annotated[AuthenticatedUser, Depends(require_viewer)],
    db: Session = Depends(get_db),
) -> ResilienceReadiness:
    """Evaluate all 15 disaster recovery readiness gates."""
    service = ResilienceService(db)
    return service.evaluate_dr_readiness()


@router.get(
    "/backups",
    response_model=BackupVerification,
    summary="Get backup verification and restore readiness",
    dependencies=[Depends(rate_limit_reads)],
)
def get_backup_verification(
    current_user: Annotated[AuthenticatedUser, Depends(require_viewer)],
    db: Session = Depends(get_db),
) -> BackupVerification:
    """Retrieve backup integrity, freshness, and restore verification status."""
    service = ResilienceService(db)
    return service.evaluate_backup_readiness()


@router.get(
    "/rto-rpo",
    response_model=RTORPOStatus,
    summary="Get RTO/RPO compliance dashboard",
    dependencies=[Depends(rate_limit_reads)],
)
def get_rto_rpo_status(
    current_user: Annotated[AuthenticatedUser, Depends(require_viewer)],
    db: Session = Depends(get_db),
) -> RTORPOStatus:
    """Retrieve Recovery Time/Point Objective compliance status."""
    service = ResilienceService(db)
    return service.evaluate_rto_rpo()


@router.get(
    "/runbooks",
    response_model=list[RecoveryRunbook],
    summary="Get structured recovery runbooks",
    dependencies=[Depends(rate_limit_reads)],
)
def get_recovery_runbooks(
    current_user: Annotated[AuthenticatedUser, Depends(require_viewer)],
    db: Session = Depends(get_db),
) -> list[RecoveryRunbook]:
    """Retrieve 9 structured recovery runbooks for disaster scenarios."""
    service = ResilienceService(db)
    return service.get_runbooks()


@router.get(
    "/simulations",
    response_model=list[dict[str, Any]],
    summary="Get past disaster simulation results",
    dependencies=[Depends(rate_limit_reads)],
)
def get_past_simulations(
    current_user: Annotated[AuthenticatedUser, Depends(require_viewer)],
    db: Session = Depends(get_db),
) -> list[dict[str, Any]]:
    """Retrieve historical disaster simulation results from AuditLog."""
    service = ResilienceService(db)
    return service.get_simulations()


@router.post(
    "/simulate",
    response_model=DisasterSimulationResult,
    summary="Run observational disaster simulation",
    dependencies=[Depends(rate_limit_mutations)],
)
def run_disaster_simulation(
    request: DisasterSimulationRequest,
    current_user: Annotated[AuthenticatedUser, Depends(require_operator)],
    db: Session = Depends(get_db),
) -> DisasterSimulationResult:
    """
    Execute a safe observational disaster simulation.
    No production services are disabled. No financial actions are executed.
    """
    service = ResilienceService(db)
    return service.simulate_disaster(
        scenario_type=request.scenario_type,
        severity_override=request.severity_override,
    )


@router.post(
    "/incidents/{incident_id}/acknowledge",
    response_model=ResilienceIncident,
    summary="Acknowledge a resilience incident",
    dependencies=[Depends(rate_limit_mutations)],
)
def acknowledge_incident(
    incident_id: Annotated[str, Path(description="Incident ID to acknowledge")],
    current_user: Annotated[AuthenticatedUser, Depends(require_operator)],
    db: Session = Depends(get_db),
) -> ResilienceIncident:
    """Acknowledge an operational resilience incident (immutable AuditLog event)."""
    service = ResilienceService(db)
    return service.acknowledge_incident(incident_id, current_user.id)


@router.post(
    "/incidents/{incident_id}/escalate",
    response_model=ResilienceIncident,
    summary="Escalate a critical resilience incident",
    dependencies=[Depends(rate_limit_mutations)],
)
def escalate_incident(
    incident_id: Annotated[str, Path(description="Incident ID to escalate")],
    current_user: Annotated[AuthenticatedUser, Depends(require_admin)],
    db: Session = Depends(get_db),
) -> ResilienceIncident:
    """Escalate a critical incident for Admin emergency review (immutable AuditLog event)."""
    service = ResilienceService(db)
    return service.escalate_incident(incident_id, current_user.id)


@router.post(
    "/recovery/verify",
    response_model=dict[str, Any],
    summary="Verify recovery completion",
    dependencies=[Depends(rate_limit_mutations)],
)
def verify_recovery(
    current_user: Annotated[AuthenticatedUser, Depends(require_operator)],
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """Run recovery verification across all services and log immutable audit event."""
    service = ResilienceService(db)
    return service.verify_recovery(current_user.id)
