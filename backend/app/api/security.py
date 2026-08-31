from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.pii_scanner import scan_for_pii_and_secrets
from app.core.rate_limiter import rate_limit_mutations, rate_limit_reads
from app.core.security import (
    AuthenticatedUser,
    require_admin,
    require_operator,
    require_viewer,
)
from app.schemas.security import (
    PaginatedSecurityEventsResponse,
    PIIScanRequest,
    PIIScanResponse,
    TokenRevocationRequest,
    TokenRevocationResponse,
    TrustCenterOverviewResponse,
)
from app.services.security_threat_service import SecurityThreatService

router = APIRouter(prefix="/api/recovery/security", tags=["security-trust-center"])


@router.get(
    "/trust-center",
    response_model=TrustCenterOverviewResponse,
    summary="Get Fintech Trust Center posture, control statuses, and threat telemetry",
    dependencies=[Depends(rate_limit_reads)],
)
def get_trust_center(
    current_user: Annotated[AuthenticatedUser, Depends(require_viewer)],
    db: Session = Depends(get_db),
) -> TrustCenterOverviewResponse:
    """
    Returns executive fintech trust posture, health of all 7 active security controls,
    real-time threat counts, and strict financial isolation guarantees.
    """
    service = SecurityThreatService(db=db)
    return service.get_trust_center_overview()


@router.get(
    "/events",
    response_model=PaginatedSecurityEventsResponse,
    summary="List chronological security audit and threat events",
    dependencies=[Depends(rate_limit_reads)],
)
def get_security_events(
    current_user: Annotated[AuthenticatedUser, Depends(require_operator)],
    db: Session = Depends(get_db),
    limit: int = Query(default=50, ge=1, le=200),
    page: int = Query(default=1, ge=1),
    severity: str = Query(default="ALL"),
    event_type: str = Query(default="ALL"),
) -> PaginatedSecurityEventsResponse:
    """
    Query immutable security audit logs with filtering by severity and event type.
    """
    service = SecurityThreatService(db=db)
    return service.list_security_events(
        limit=limit,
        page=page,
        severity_filter=severity if severity != "ALL" else None,
        event_type_filter=event_type if event_type != "ALL" else None,
    )


@router.post(
    "/revoke-token",
    response_model=TokenRevocationResponse,
    status_code=status.HTTP_200_OK,
    summary="Emergency revoke an active JWT token identifier (JTI)",
    dependencies=[Depends(rate_limit_mutations)],
)
def revoke_jwt_token(
    payload: TokenRevocationRequest,
    current_user: Annotated[AuthenticatedUser, Depends(require_admin)],
    db: Session = Depends(get_db),
) -> TokenRevocationResponse:
    """
    Admin-only emergency tripwire to immediately blacklist and revoke an active JWT token JTI.
    """
    service = SecurityThreatService(db=db)
    return service.revoke_token(
        jti=payload.jti,
        actor_id=current_user.id,
        reason=payload.reason,
    )


@router.post(
    "/scan",
    response_model=PIIScanResponse,
    status_code=status.HTTP_200_OK,
    summary="On-demand payload scan for PII and cryptographic secrets",
    dependencies=[Depends(rate_limit_reads)],
)
def scan_payload(
    payload: PIIScanRequest,
    current_user: Annotated[AuthenticatedUser, Depends(require_operator)],
) -> PIIScanResponse:
    """
    Test and verify redaction of card PANs (Luhn-checked), Aadhaar, CVV, phones, emails, and API keys.
    """
    res = scan_for_pii_and_secrets(payload.payload)
    return PIIScanResponse(
        has_pii=res["has_pii"],
        has_secrets=res["has_secrets"],
        findings_count=res["findings_count"],
        findings=res["findings"],
        sanitized_payload=res["sanitized_payload"],
        scan_timestamp=datetime.now(UTC).isoformat(),
    )
