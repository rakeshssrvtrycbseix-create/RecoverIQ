import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.rate_limiter import rate_limit_mutations, rate_limit_reads
from app.core.security import (
    AuthenticatedUser,
    require_admin,
    require_operator,
    require_viewer,
)
from app.schemas.zero_trust_security import (
    AttackChain,
    BehavioralThreatScore,
    RuntimeSecurityPosture,
    SecretExposureFinding,
    SecurityEvidenceNode,
    SecurityIncident,
    SecurityIncidentActionRequest,
    ServiceAuthMatrix,
    ServiceIdentity,
    SignedSecurityReport,
    ThreatIndicator,
    TrustViolation,
    ZeroTrustGate,
    ZeroTrustSummary,
)
from app.services.zero_trust_security_service import ZeroTrustSecurityService

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/recovery/intelligence/zero-trust",
    tags=["zero-trust-security"],
)


@router.get(
    "",
    response_model=ZeroTrustSummary,
    summary="Get Zero-Trust Security Control Plane Summary",
    dependencies=[Depends(rate_limit_reads)],
)
@router.get(
    "/summary",
    response_model=ZeroTrustSummary,
    summary="Get Zero-Trust Security Control Plane Summary (Alias)",
    dependencies=[Depends(rate_limit_reads)],
)
def get_zero_trust_summary(
    user: Annotated[AuthenticatedUser, Depends(require_viewer)],
    db: Session = Depends(get_db),
) -> ZeroTrustSummary:
    """Retrieve executive summary posture of the Zero-Trust Security Control Plane."""
    service = ZeroTrustSecurityService(db)
    return service.get_summary()


@router.get(
    "/trust-matrix",
    response_model=list[ServiceIdentity],
    summary="Get Service Identity Trust Matrix",
    dependencies=[Depends(rate_limit_reads)],
)
@router.get(
    "/service-identities",
    response_model=list[ServiceIdentity],
    summary="Get Service Identities List",
    dependencies=[Depends(rate_limit_reads)],
)
def get_service_identities(
    user: Annotated[AuthenticatedUser, Depends(require_viewer)],
    db: Session = Depends(get_db),
) -> list[ServiceIdentity]:
    """Retrieve telemetry for the 11 core microservice identities."""
    service = ZeroTrustSecurityService(db)
    return service.get_service_identities()


@router.get(
    "/service-identities/{service_name}",
    response_model=ServiceIdentity,
    summary="Get Specific Service Identity Telemetry",
    dependencies=[Depends(rate_limit_reads)],
)
def get_service_identity_by_name(
    service_name: str,
    user: Annotated[AuthenticatedUser, Depends(require_viewer)],
    db: Session = Depends(get_db),
) -> ServiceIdentity:
    """Retrieve identity telemetry for a specific microservice."""
    service = ZeroTrustSecurityService(db)
    identities = service.get_service_identities()
    target = next(
        (i for i in identities if i.service_name.lower() == service_name.lower()), None
    )
    if not target:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Service identity '{service_name}' not found.",
        )
    return target


@router.get(
    "/authorization-matrix",
    response_model=ServiceAuthMatrix,
    summary="Get Service Authorization Matrix",
    dependencies=[Depends(rate_limit_reads)],
)
def get_authorization_matrix(
    user: Annotated[AuthenticatedUser, Depends(require_viewer)],
    db: Session = Depends(get_db),
) -> ServiceAuthMatrix:
    """Retrieve service-to-service authorization topology and matrix."""
    service = ZeroTrustSecurityService(db)
    return service.get_authorization_matrix()


@router.get(
    "/trust-violations",
    response_model=list[TrustViolation],
    summary="Get Active Trust Violations",
    dependencies=[Depends(rate_limit_reads)],
)
def get_trust_violations(
    user: Annotated[AuthenticatedUser, Depends(require_viewer)],
    db: Session = Depends(get_db),
) -> list[TrustViolation]:
    """Retrieve active zero-trust violations."""
    service = ZeroTrustSecurityService(db)
    return service.get_trust_violations()


@router.get(
    "/threat-intelligence",
    response_model=list[ThreatIndicator],
    summary="Get Threat Intelligence Indicators",
    dependencies=[Depends(rate_limit_reads)],
)
@router.get(
    "/threat-indicators",
    response_model=list[ThreatIndicator],
    summary="Get Threat Indicators List",
    dependencies=[Depends(rate_limit_reads)],
)
def get_threat_indicators(
    user: Annotated[AuthenticatedUser, Depends(require_viewer)],
    db: Session = Depends(get_db),
) -> list[ThreatIndicator]:
    """Retrieve sanitized/pseudonymized threat indicator fingerprints."""
    service = ZeroTrustSecurityService(db)
    return service.get_threat_indicators()


@router.get(
    "/threat-score",
    response_model=BehavioralThreatScore,
    summary="Get Behavioral Threat Score Evaluation",
    dependencies=[Depends(rate_limit_reads)],
)
def get_behavioral_threat_score(
    user: Annotated[AuthenticatedUser, Depends(require_viewer)],
    db: Session = Depends(get_db),
) -> BehavioralThreatScore:
    """Retrieve composite behavioral threat score evaluation."""
    service = ZeroTrustSecurityService(db)
    return service.get_behavioral_threat_score()


@router.get(
    "/attack-chains",
    response_model=list[AttackChain],
    summary="Get Correlated Attack Chains List",
    dependencies=[Depends(rate_limit_reads)],
)
def get_attack_chains(
    user: Annotated[AuthenticatedUser, Depends(require_viewer)],
    db: Session = Depends(get_db),
) -> list[AttackChain]:
    """Retrieve correlated 8-stage attack propagation chains."""
    service = ZeroTrustSecurityService(db)
    return service.get_attack_chains()


@router.get(
    "/attack-chains/{chain_id}",
    response_model=AttackChain,
    summary="Get Attack Chain Details by ID",
    dependencies=[Depends(rate_limit_reads)],
)
def get_attack_chain_by_id(
    chain_id: str,
    user: Annotated[AuthenticatedUser, Depends(require_viewer)],
    db: Session = Depends(get_db),
) -> AttackChain:
    """Retrieve specific attack chain by ID."""
    service = ZeroTrustSecurityService(db)
    chains = service.get_attack_chains()
    target = next((c for c in chains if c.chain_id == chain_id), None)
    if not target:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Attack chain '{chain_id}' not found.",
        )
    return target


@router.get(
    "/runtime-security",
    response_model=RuntimeSecurityPosture,
    summary="Get Runtime Security Surveillance Posture",
    dependencies=[Depends(rate_limit_reads)],
)
def get_runtime_security_posture(
    user: Annotated[AuthenticatedUser, Depends(require_viewer)],
    db: Session = Depends(get_db),
) -> RuntimeSecurityPosture:
    """Retrieve runtime security surveillance metrics."""
    service = ZeroTrustSecurityService(db)
    return service.get_runtime_security_posture()


@router.get(
    "/secret-exposure",
    response_model=list[SecretExposureFinding],
    summary="Get Secret Exposure Findings",
    dependencies=[Depends(rate_limit_reads)],
)
def get_secret_exposures(
    user: Annotated[AuthenticatedUser, Depends(require_viewer)],
    db: Session = Depends(get_db),
) -> list[SecretExposureFinding]:
    """Retrieve secret exposure surveillance findings."""
    service = ZeroTrustSecurityService(db)
    return service.get_secret_exposures()


@router.get(
    "/security-incidents",
    response_model=list[SecurityIncident],
    summary="Get Security Incidents Queue",
    dependencies=[Depends(rate_limit_reads)],
)
def get_security_incidents(
    user: Annotated[AuthenticatedUser, Depends(require_viewer)],
    db: Session = Depends(get_db),
) -> list[SecurityIncident]:
    """Retrieve active and historical security incidents."""
    service = ZeroTrustSecurityService(db)
    return service.get_security_incidents()


@router.get(
    "/security-incidents/{incident_id}",
    response_model=SecurityIncident,
    summary="Get Security Incident Details by ID",
    dependencies=[Depends(rate_limit_reads)],
)
def get_security_incident_by_id(
    incident_id: str,
    user: Annotated[AuthenticatedUser, Depends(require_viewer)],
    db: Session = Depends(get_db),
) -> SecurityIncident:
    """Retrieve specific security incident by ID."""
    service = ZeroTrustSecurityService(db)
    incidents = service.get_security_incidents()
    target = next((i for i in incidents if i.incident_id == incident_id), None)
    if not target:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Security incident '{incident_id}' not found.",
        )
    return target


@router.post(
    "/security-incidents/{incident_id}/acknowledge",
    response_model=SecurityIncident,
    summary="Acknowledge Security Incident",
    dependencies=[Depends(rate_limit_mutations)],
)
def acknowledge_security_incident(
    incident_id: str,
    user: Annotated[AuthenticatedUser, Depends(require_operator)],
    notes: str | None = Query(None),
    db: Session = Depends(get_db),
) -> SecurityIncident:
    """Acknowledge an active security incident."""
    service = ZeroTrustSecurityService(db)
    req = SecurityIncidentActionRequest(
        action="ACKNOWLEDGE", operator_id=user.id, notes=notes
    )
    return service.update_security_incident(incident_id, req, actor_id=user.id)


@router.post(
    "/security-incidents/{incident_id}/escalate",
    response_model=SecurityIncident,
    summary="Escalate Security Incident",
    dependencies=[Depends(rate_limit_mutations)],
)
def escalate_security_incident(
    incident_id: str,
    user: Annotated[AuthenticatedUser, Depends(require_operator)],
    notes: str | None = Query(None),
    db: Session = Depends(get_db),
) -> SecurityIncident:
    """Escalate a security incident to senior SecOps leadership."""
    service = ZeroTrustSecurityService(db)
    req = SecurityIncidentActionRequest(
        action="ESCALATE", operator_id=user.id, notes=notes
    )
    return service.update_security_incident(incident_id, req, actor_id=user.id)


@router.post(
    "/security-incidents/{incident_id}/resolve",
    response_model=SecurityIncident,
    summary="Resolve Security Incident",
    dependencies=[Depends(rate_limit_mutations)],
)
def resolve_security_incident(
    incident_id: str,
    user: Annotated[AuthenticatedUser, Depends(require_admin)],
    notes: str | None = Query(None),
    db: Session = Depends(get_db),
) -> SecurityIncident:
    """Resolve a security incident following human verification."""
    service = ZeroTrustSecurityService(db)
    req = SecurityIncidentActionRequest(
        action="RESOLVE", operator_id=user.id, notes=notes
    )
    return service.update_security_incident(incident_id, req, actor_id=user.id)


@router.get(
    "/readiness",
    response_model=list[ZeroTrustGate],
    summary="Get 22 Zero-Trust Security Readiness Gates",
    dependencies=[Depends(rate_limit_reads)],
)
def get_readiness_gates(
    user: Annotated[AuthenticatedUser, Depends(require_viewer)],
    db: Session = Depends(get_db),
) -> list[ZeroTrustGate]:
    """Evaluate the 22 deterministic Zero-Trust Security Readiness Gates."""
    service = ZeroTrustSecurityService(db)
    return service.get_readiness_gates()


@router.get(
    "/evidence",
    response_model=list[SecurityEvidenceNode],
    summary="Get Cryptographic Evidence Chain",
    dependencies=[Depends(rate_limit_reads)],
)
def get_security_evidence(
    user: Annotated[AuthenticatedUser, Depends(require_viewer)],
    db: Session = Depends(get_db),
) -> list[SecurityEvidenceNode]:
    """Retrieve tamper-evident cryptographic evidence nodes."""
    service = ZeroTrustSecurityService(db)
    return service.get_security_evidence()


@router.get(
    "/report",
    response_model=SignedSecurityReport,
    summary="Generate Signed Zero-Trust Security Report",
    dependencies=[Depends(rate_limit_reads)],
)
def generate_signed_security_report(
    user: Annotated[AuthenticatedUser, Depends(require_viewer)],
    db: Session = Depends(get_db),
) -> SignedSecurityReport:
    """Generate a cryptographically signed Zero-Trust Security Report."""
    service = ZeroTrustSecurityService(db)
    return service.generate_signed_report()
