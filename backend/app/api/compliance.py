import logging
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.rate_limiter import rate_limit_reads
from app.core.security import (
    AuthenticatedUser,
    require_viewer,
)
from app.schemas.compliance import (
    AuditCoverage,
    ComplianceControl,
    ComplianceIncident,
    ComplianceReport,
    ComplianceSummary,
)
from app.services.compliance_governance_service import ComplianceGovernanceService

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/recovery/intelligence/compliance", tags=["compliance-governance"]
)


@router.get(
    "",
    response_model=ComplianceSummary,
    summary="Get executive compliance summary, governance risk score, and posture",
    dependencies=[Depends(rate_limit_reads)],
)
def get_compliance_summary(
    current_user: Annotated[AuthenticatedUser, Depends(require_viewer)],
    db: Session = Depends(get_db),
) -> ComplianceSummary:
    """
    Retrieve deterministic executive compliance summary and governance risk score.
    Accessible to all authenticated roles (VIEWER, OPERATOR, ADMIN).
    """
    service = ComplianceGovernanceService(db)
    return service.get_compliance_summary()


@router.get(
    "/controls",
    response_model=list[ComplianceControl],
    summary="Get compliance control matrix with optional filters",
    dependencies=[Depends(rate_limit_reads)],
)
def get_compliance_controls(
    current_user: Annotated[AuthenticatedUser, Depends(require_viewer)],
    db: Session = Depends(get_db),
    category: str | None = Query(
        None,
        description="Filter by control category (SECURITY, FINANCIAL_CONTROL, etc.)",
    ),
    status: str | None = Query(
        None, description="Filter by status (PASS, WARNING, FAIL, etc.)"
    ),
    severity: str | None = Query(
        None, description="Filter by severity (LOW, MEDIUM, HIGH, CRITICAL)"
    ),
) -> list[ComplianceControl]:
    """
    Retrieve full list of 18 deterministic engineering compliance controls with optional filtering.
    """
    service = ComplianceGovernanceService(db)
    return service.get_compliance_controls(
        category_filter=category,
        status_filter=status,
        severity_filter=severity,
    )


@router.get(
    "/incidents",
    response_model=list[ComplianceIncident],
    summary="Get detected compliance incidents and audit gaps",
    dependencies=[Depends(rate_limit_reads)],
)
def get_compliance_incidents(
    current_user: Annotated[AuthenticatedUser, Depends(require_viewer)],
    db: Session = Depends(get_db),
    severity: str | None = Query(
        None, description="Filter by severity (LOW, MEDIUM, HIGH, CRITICAL)"
    ),
    category: str | None = Query(None, description="Filter by category"),
    status: str | None = Query(
        None, description="Filter by incident status (OPEN, RESOLVED)"
    ),
) -> list[ComplianceIncident]:
    """
    Retrieve detected compliance incidents and audit gaps.
    """
    service = ComplianceGovernanceService(db)
    return service.get_compliance_incidents(
        severity_filter=severity,
        category_filter=category,
        status_filter=status,
    )


@router.get(
    "/audit-coverage",
    response_model=AuditCoverage,
    summary="Get AuditLog completeness and lifecycle coverage metrics",
    dependencies=[Depends(rate_limit_reads)],
)
def get_audit_coverage(
    current_user: Annotated[AuthenticatedUser, Depends(require_viewer)],
    db: Session = Depends(get_db),
) -> AuditCoverage:
    """
    Retrieve AuditLog completeness metrics across required lifecycle event types.
    """
    service = ComplianceGovernanceService(db)
    return service.get_audit_coverage()


@router.get(
    "/report",
    response_model=ComplianceReport,
    summary="Generate exportable structured JSON compliance snapshot",
    dependencies=[Depends(rate_limit_reads)],
)
def get_compliance_report(
    current_user: Annotated[AuthenticatedUser, Depends(require_viewer)],
    db: Session = Depends(get_db),
) -> ComplianceReport:
    """
    Generate an exportable comprehensive JSON snapshot of the compliance state.
    """
    service = ComplianceGovernanceService(db)
    return service.get_compliance_report()
