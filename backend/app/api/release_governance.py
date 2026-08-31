"""Phase 10G — Fintech Architecture Governance, Change Management, Release Safety

& Deployment Assurance REST API Router.
"""

import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.rate_limiter import rate_limit_mutations, rate_limit_reads
from app.core.security import (
    AuthenticatedUser,
    require_admin,
    require_operator,
    require_viewer,
)
from app.schemas.release_governance import (
    ApiCompatibilityReport,
    ArchitectureFinding,
    CanaryEvaluation,
    ChangeRequest,
    ChangeRequestCreate,
    ChangeRiskAssessment,
    ConfigurationDrift,
    DatabaseCompatibilityReport,
    DependencyImpact,
    FeatureFlag,
    FeatureFlagUpdate,
    ReleaseApproval,
    ReleaseApprovalRequest,
    ReleaseCandidate,
    ReleaseCandidateCreate,
    ReleaseGovernanceReport,
    ReleaseGovernanceSummary,
    ReleaseIncident,
    ReleaseLineageNode,
    ReleaseReadinessSummary,
    RollbackReadiness,
)
from app.services.release_governance_service import ReleaseGovernanceService

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/recovery/intelligence/release-governance",
    tags=["release-governance"],
)


@router.get(
    "",
    response_model=ReleaseGovernanceSummary,
    summary="Get Architecture & Release Governance Executive Summary",
    dependencies=[Depends(rate_limit_reads)],
)
@router.get(
    "/summary",
    response_model=ReleaseGovernanceSummary,
    summary="Get Architecture & Release Governance Executive Summary (Alias)",
    dependencies=[Depends(rate_limit_reads)],
)
def get_release_governance_summary(
    user: Annotated[AuthenticatedUser, Depends(require_viewer)],
    db: Session = Depends(get_db),
) -> ReleaseGovernanceSummary:
    """Retrieve the deterministic 10-factor architecture and release governance posture."""
    service = ReleaseGovernanceService(db)
    return service.get_governance_summary()


@router.get(
    "/changes",
    response_model=list[ChangeRequest],
    summary="List Governed Change Requests",
    dependencies=[Depends(rate_limit_reads)],
)
def list_change_requests(
    user: Annotated[AuthenticatedUser, Depends(require_viewer)],
    db: Session = Depends(get_db),
) -> list[ChangeRequest]:
    """Retrieve all governed change requests and their risk scores."""
    service = ReleaseGovernanceService(db)
    return service.get_change_requests()


@router.post(
    "/changes",
    response_model=ChangeRequest,
    status_code=status.HTTP_201_CREATED,
    summary="Create Governed Change Request",
    dependencies=[Depends(rate_limit_mutations)],
)
def create_change_request(
    payload: ChangeRequestCreate,
    user: Annotated[AuthenticatedUser, Depends(require_operator)],
    db: Session = Depends(get_db),
) -> ChangeRequest:
    """Submit a proposed change request for automated blast-radius and risk assessment."""
    service = ReleaseGovernanceService(db)
    return service.create_change_request(payload, user_id=user.id, user_role=user.role)


@router.get(
    "/changes/{change_id}",
    response_model=ChangeRequest,
    summary="Get Change Request Details",
    dependencies=[Depends(rate_limit_reads)],
)
def get_change_request_details(
    change_id: str,
    user: Annotated[AuthenticatedUser, Depends(require_viewer)],
    db: Session = Depends(get_db),
) -> ChangeRequest:
    """Retrieve specific change request details by ID."""
    service = ReleaseGovernanceService(db)
    change = service.get_change_request(change_id)
    if not change:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Change request {change_id} not found",
        )
    return change


@router.get(
    "/risk/{change_id}",
    response_model=ChangeRiskAssessment,
    summary="Get Change Risk Assessment",
    dependencies=[Depends(rate_limit_reads)],
)
def get_change_risk(
    change_id: str,
    user: Annotated[AuthenticatedUser, Depends(require_viewer)],
    db: Session = Depends(get_db),
) -> ChangeRiskAssessment:
    """Retrieve risk score, financial multiplier, and mitigation factors for a change."""
    service = ReleaseGovernanceService(db)
    change = service.get_change_request(change_id)
    if not change:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Change request {change_id} not found",
        )
    return change.risk_assessment


@router.get(
    "/dependencies",
    response_model=list[DependencyImpact],
    summary="Get 11-Service Dependency Coupling Graph",
    dependencies=[Depends(rate_limit_reads)],
)
def get_dependency_graph(
    user: Annotated[AuthenticatedUser, Depends(require_viewer)],
    db: Session = Depends(get_db),
) -> list[DependencyImpact]:
    """Retrieve service coupling matrix, blast radius, and failure propagation risks."""
    service = ReleaseGovernanceService(db)
    return service.get_dependency_impacts()


@router.get(
    "/architecture-findings",
    response_model=list[ArchitectureFinding],
    summary="Get Active Architecture Risk Findings",
    dependencies=[Depends(rate_limit_reads)],
)
def get_architecture_findings(
    user: Annotated[AuthenticatedUser, Depends(require_viewer)],
    db: Session = Depends(get_db),
) -> list[ArchitectureFinding]:
    """Retrieve structural architecture findings and coupling anti-patterns."""
    service = ReleaseGovernanceService(db)
    return service.get_architecture_findings()


@router.get(
    "/api-compatibility",
    response_model=ApiCompatibilityReport,
    summary="Get API Contract Compatibility Report",
    dependencies=[Depends(rate_limit_reads)],
)
def get_api_compatibility(
    user: Annotated[AuthenticatedUser, Depends(require_viewer)],
    db: Session = Depends(get_db),
) -> ApiCompatibilityReport:
    """Evaluate backward compatibility across public API contracts."""
    service = ReleaseGovernanceService(db)
    return service.get_api_compatibility_report()


@router.get(
    "/database-compatibility",
    response_model=DatabaseCompatibilityReport,
    summary="Get Database Schema Compatibility Report",
    dependencies=[Depends(rate_limit_reads)],
)
def get_database_compatibility(
    user: Annotated[AuthenticatedUser, Depends(require_viewer)],
    db: Session = Depends(get_db),
) -> DatabaseCompatibilityReport:
    """Evaluate database schema compatibility under zero-migration invariant."""
    service = ReleaseGovernanceService(db)
    return service.get_database_compatibility_report()


@router.get(
    "/configuration-drift",
    response_model=list[ConfigurationDrift],
    summary="Get Configuration Drift & Parity Posture",
    dependencies=[Depends(rate_limit_reads)],
)
def get_configuration_drift(
    user: Annotated[AuthenticatedUser, Depends(require_viewer)],
    db: Session = Depends(get_db),
) -> list[ConfigurationDrift]:
    """Detect and list configuration drifts with masked/hashed secrets."""
    service = ReleaseGovernanceService(db)
    return service.get_configuration_drifts()


@router.get(
    "/feature-flags",
    response_model=list[FeatureFlag],
    summary="List Governed Feature Flags",
    dependencies=[Depends(rate_limit_reads)],
)
def get_feature_flags(
    user: Annotated[AuthenticatedUser, Depends(require_viewer)],
    db: Session = Depends(get_db),
) -> list[FeatureFlag]:
    """List feature flags with rollout percentage and financial risk tags."""
    service = ReleaseGovernanceService(db)
    return service.get_feature_flags()


@router.post(
    "/feature-flags/{flag_id}",
    response_model=FeatureFlag,
    summary="Update Feature Flag Rollout or Status",
    dependencies=[Depends(rate_limit_mutations)],
)
def update_feature_flag(
    flag_id: str,
    payload: FeatureFlagUpdate,
    user: Annotated[AuthenticatedUser, Depends(require_operator)],
    db: Session = Depends(get_db),
) -> FeatureFlag:
    """Update feature flag rollout percentage or lifecycle status."""
    service = ReleaseGovernanceService(db)
    try:
        return service.update_feature_flag(flag_id, payload, user_id=user.id)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )


@router.get(
    "/releases",
    response_model=list[ReleaseCandidate],
    summary="List Release Candidates",
    dependencies=[Depends(rate_limit_reads)],
)
def list_release_candidates(
    user: Annotated[AuthenticatedUser, Depends(require_viewer)],
    db: Session = Depends(get_db),
) -> list[ReleaseCandidate]:
    """Retrieve all release candidates and their readiness state."""
    service = ReleaseGovernanceService(db)
    return service.get_release_candidates()


@router.post(
    "/releases",
    response_model=ReleaseCandidate,
    status_code=status.HTTP_201_CREATED,
    summary="Create Release Candidate",
    dependencies=[Depends(rate_limit_mutations)],
)
def create_release_candidate(
    payload: ReleaseCandidateCreate,
    user: Annotated[AuthenticatedUser, Depends(require_operator)],
    db: Session = Depends(get_db),
) -> ReleaseCandidate:
    """Assemble and evaluate a new Release Candidate."""
    service = ReleaseGovernanceService(db)
    return service.create_release_candidate(payload, user_id=user.id)


@router.get(
    "/releases/{rc_id}",
    response_model=ReleaseCandidate,
    summary="Get Release Candidate Details",
    dependencies=[Depends(rate_limit_reads)],
)
def get_release_candidate(
    rc_id: str,
    user: Annotated[AuthenticatedUser, Depends(require_viewer)],
    db: Session = Depends(get_db),
) -> ReleaseCandidate:
    """Retrieve specific release candidate details by ID."""
    service = ReleaseGovernanceService(db)
    rc = service.get_release_candidate(rc_id)
    if not rc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Release candidate {rc_id} not found",
        )
    return rc


@router.get(
    "/readiness",
    response_model=ReleaseReadinessSummary,
    summary="Get 18 Release Readiness Safety Gates",
    dependencies=[Depends(rate_limit_reads)],
)
def get_readiness_gates(
    user: Annotated[AuthenticatedUser, Depends(require_viewer)],
    db: Session = Depends(get_db),
) -> ReleaseReadinessSummary:
    """Evaluate the 18 deterministic release readiness verification gates."""
    service = ReleaseGovernanceService(db)
    return service.get_release_readiness_gates()


@router.get(
    "/canary",
    response_model=CanaryEvaluation,
    summary="Get Canary Release Observation & Recommendation",
    dependencies=[Depends(rate_limit_reads)],
)
def get_canary_evaluation(
    user: Annotated[AuthenticatedUser, Depends(require_viewer)],
    db: Session = Depends(get_db),
) -> CanaryEvaluation:
    """Evaluate observational telemetry comparing canary vs baseline deployments."""
    service = ReleaseGovernanceService(db)
    return service.get_canary_evaluation()


@router.get(
    "/rollback-readiness",
    response_model=RollbackReadiness,
    summary="Get Rollback Safety & Reversibility Posture",
    dependencies=[Depends(rate_limit_reads)],
)
def get_rollback_readiness(
    user: Annotated[AuthenticatedUser, Depends(require_viewer)],
    db: Session = Depends(get_db),
) -> RollbackReadiness:
    """Evaluate rollback safety and reversibility guarantees."""
    service = ReleaseGovernanceService(db)
    return service.get_rollback_readiness()


@router.get(
    "/lineage",
    response_model=list[ReleaseLineageNode],
    summary="Get 10-Stage Release Lineage Cryptographic DAG",
    dependencies=[Depends(rate_limit_reads)],
)
def get_release_lineage(
    user: Annotated[AuthenticatedUser, Depends(require_viewer)],
    db: Session = Depends(get_db),
) -> list[ReleaseLineageNode]:
    """Retrieve the 10-stage cryptographic release lineage DAG with SHA-256 digests."""
    service = ReleaseGovernanceService(db)
    return service.get_release_lineage()


@router.get(
    "/incidents",
    response_model=list[ReleaseIncident],
    summary="List Release-Correlated Incidents",
    dependencies=[Depends(rate_limit_reads)],
)
def get_release_incidents(
    user: Annotated[AuthenticatedUser, Depends(require_viewer)],
    db: Session = Depends(get_db),
) -> list[ReleaseIncident]:
    """List active and historical release-related incidents."""
    service = ReleaseGovernanceService(db)
    return service.get_release_incidents()


@router.post(
    "/approve/{rc_id}",
    response_model=ReleaseApproval,
    summary="Human Governance Sign-off on Release Candidate",
    dependencies=[Depends(rate_limit_mutations)],
)
def approve_release_candidate(
    rc_id: str,
    payload: ReleaseApprovalRequest,
    user: Annotated[AuthenticatedUser, Depends(require_admin)],
    db: Session = Depends(get_db),
) -> ReleaseApproval:
    """Record human governance sign-off or rejection for a release candidate."""
    service = ReleaseGovernanceService(db)
    rc = service.get_release_candidate(rc_id)
    if not rc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Release candidate {rc_id} not found",
        )
    return service.approve_release(rc_id, payload, user_id=user.id, user_role=user.role)


@router.get(
    "/report",
    response_model=ReleaseGovernanceReport,
    summary="Generate Signed Release Governance Audit Report",
    dependencies=[Depends(rate_limit_reads)],
)
def generate_release_governance_report(
    user: Annotated[AuthenticatedUser, Depends(require_viewer)],
    db: Session = Depends(get_db),
) -> ReleaseGovernanceReport:
    """Generate a cryptographically signed SHA-256 Release Governance Report."""
    service = ReleaseGovernanceService(db)
    return service.generate_governance_report()
