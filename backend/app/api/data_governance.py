"""Phase 10E — Data Governance, Privacy Engineering & Data Lineage REST API Router.

Provides 16 deterministic REST endpoints for data asset discovery, classification,
PII discovery scanning, data lineage graphs, data quality metrics, retention governance,
privacy controls, privacy incidents, and privacy request workflows.
Protected by 3-tier JWT RBAC and sliding-window rate limiting.
"""

import logging
from typing import Annotated

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
from app.schemas.data_governance import (
    DataAsset,
    DataGovernanceReport,
    DataGovernanceSummary,
    DataLineageGraph,
    DataLineageNode,
    DataQualityMetric,
    ErasureEligibilityEvaluation,
    PIIScanRequest,
    PIIScanResponse,
    PrivacyControl,
    PrivacyIncident,
    PrivacyRequest,
    PrivacyRequestComplete,
    PrivacyRequestCreate,
    PrivacyRequestReview,
    RetentionAssetStatus,
)
from app.services.data_governance_service import DataGovernanceService

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/recovery/intelligence/data-governance",
    tags=["data-governance"],
)


@router.get(
    "",
    response_model=DataGovernanceSummary,
    summary="Get executive Data Governance & Privacy posture summary",
    dependencies=[Depends(rate_limit_reads)],
)
def get_governance_summary(
    current_user: Annotated[AuthenticatedUser, Depends(require_viewer)],
    db: Annotated[Session, Depends(get_db)],
) -> DataGovernanceSummary:
    """Returns top-level data governance score, breakdown, and posture metrics."""
    service = DataGovernanceService(db)
    return service.get_summary()


@router.get(
    "/assets",
    response_model=list[DataAsset],
    summary="List all discovered RecoverIQ data assets and classification tiers",
    dependencies=[Depends(rate_limit_reads)],
)
def list_data_assets(
    current_user: Annotated[AuthenticatedUser, Depends(require_viewer)],
    db: Annotated[Session, Depends(get_db)],
) -> list[DataAsset]:
    """Returns catalog of registered data assets with field-level classification."""
    service = DataGovernanceService(db)
    return service.get_data_assets()


@router.get(
    "/assets/{asset_id}",
    response_model=DataAsset,
    summary="Get data asset details and field sensitivity classifications",
    dependencies=[Depends(rate_limit_reads)],
)
def get_data_asset_detail(
    asset_id: Annotated[str, Path(..., description="Data asset ID")],
    current_user: Annotated[AuthenticatedUser, Depends(require_viewer)],
    db: Annotated[Session, Depends(get_db)],
) -> DataAsset:
    """Returns specific data asset by ID."""
    service = DataGovernanceService(db)
    return service.get_data_asset_by_id(asset_id)


@router.get(
    "/controls",
    response_model=list[PrivacyControl],
    summary="List all 25 automated privacy, lineage, and governance controls",
    dependencies=[Depends(rate_limit_reads)],
)
def list_privacy_controls(
    current_user: Annotated[AuthenticatedUser, Depends(require_viewer)],
    db: Annotated[Session, Depends(get_db)],
    category: str | None = Query(None, description="Filter by control category"),
    status: str | None = Query(None, description="Filter by PASS/WARNING/FAIL"),
    severity: str | None = Query(None, description="Filter by severity"),
) -> list[PrivacyControl]:
    """Returns 25 automated privacy and data governance verification controls."""
    service = DataGovernanceService(db)
    return service.get_privacy_controls(
        category_filter=category,
        status_filter=status,
        severity_filter=severity,
    )


@router.get(
    "/data-quality",
    response_model=DataQualityMetric,
    summary="Get data quality, completeness, validity, and freshness metrics",
    dependencies=[Depends(rate_limit_reads)],
)
def get_data_quality_metrics(
    current_user: Annotated[AuthenticatedUser, Depends(require_viewer)],
    db: Annotated[Session, Depends(get_db)],
) -> DataQualityMetric:
    """Returns 6-dimension data quality score and hygiene breakdown."""
    service = DataGovernanceService(db)
    return service.evaluate_data_quality()


@router.get(
    "/lineage",
    response_model=DataLineageGraph,
    summary="Get end-to-end data transformation and provenance lineage graph",
    dependencies=[Depends(rate_limit_reads)],
)
def get_data_lineage_graph(
    current_user: Annotated[AuthenticatedUser, Depends(require_viewer)],
    db: Annotated[Session, Depends(get_db)],
) -> DataLineageGraph:
    """Returns source-to-outcome data transformation lineage graph with checksums."""
    service = DataGovernanceService(db)
    return service.get_lineage_graph()


@router.get(
    "/lineage/{asset_id}",
    response_model=DataLineageNode,
    summary="Get lineage node detail by ID",
    dependencies=[Depends(rate_limit_reads)],
)
def get_lineage_node_detail(
    asset_id: Annotated[str, Path(..., description="Lineage node or asset ID")],
    current_user: Annotated[AuthenticatedUser, Depends(require_viewer)],
    db: Annotated[Session, Depends(get_db)],
) -> DataLineageNode:
    """Returns a specific lineage node from the graph."""
    service = DataGovernanceService(db)
    graph = service.get_lineage_graph()
    for node in graph.nodes:
        if node.node_id == asset_id or node.name.lower() == asset_id.lower():
            return node
    # Return first node as fallback
    return graph.nodes[0]


@router.get(
    "/retention",
    response_model=list[RetentionAssetStatus],
    summary="List data retention statuses, legal holds, and advisory expiration",
    dependencies=[Depends(rate_limit_reads)],
)
def list_retention_statuses(
    current_user: Annotated[AuthenticatedUser, Depends(require_viewer)],
    db: Annotated[Session, Depends(get_db)],
) -> list[RetentionAssetStatus]:
    """Returns domain retention compliance, legal hold protections, and expiration status."""
    service = DataGovernanceService(db)
    return service.evaluate_retention()


@router.get(
    "/erasure-eligibility/{subject_id}",
    response_model=ErasureEligibilityEvaluation,
    summary="Evaluate advisory subject erasure eligibility and statutory retention blockers",
    dependencies=[Depends(rate_limit_reads)],
)
def evaluate_erasure_eligibility(
    subject_id: Annotated[
        str, Path(..., description="Subject / Customer ID to evaluate")
    ],
    current_user: Annotated[AuthenticatedUser, Depends(require_viewer)],
    db: Annotated[Session, Depends(get_db)],
) -> ErasureEligibilityEvaluation:
    """Evaluates whether subject data is eligible for erasure under regulatory constraints."""
    service = DataGovernanceService(db)
    return service.evaluate_erasure_eligibility(subject_id)


@router.get(
    "/incidents",
    response_model=list[PrivacyIncident],
    summary="List privacy, secret-leakage, and data-lineage incidents",
    dependencies=[Depends(rate_limit_reads)],
)
def list_privacy_incidents(
    current_user: Annotated[AuthenticatedUser, Depends(require_viewer)],
    db: Annotated[Session, Depends(get_db)],
) -> list[PrivacyIncident]:
    """Returns deduplicated privacy and data governance incidents."""
    service = DataGovernanceService(db)
    return service.get_privacy_incidents()


@router.get(
    "/privacy-requests",
    response_model=list[PrivacyRequest],
    summary="List all subject rights and data governance requests",
    dependencies=[Depends(rate_limit_reads)],
)
def list_privacy_requests(
    current_user: Annotated[AuthenticatedUser, Depends(require_viewer)],
    db: Annotated[Session, Depends(get_db)],
) -> list[PrivacyRequest]:
    """Returns event-sourced privacy requests and their lifecycle state."""
    service = DataGovernanceService(db)
    return service.get_privacy_requests()


@router.post(
    "/privacy-requests",
    response_model=PrivacyRequest,
    summary="Create a new subject rights privacy or governance request",
    dependencies=[Depends(rate_limit_mutations)],
)
def create_privacy_request(
    payload: PrivacyRequestCreate,
    current_user: Annotated[AuthenticatedUser, Depends(require_operator)],
    db: Annotated[Session, Depends(get_db)],
) -> PrivacyRequest:
    """Creates a new privacy request with HMAC pseudonymization and audit trail."""
    service = DataGovernanceService(db)
    return service.create_privacy_request(
        payload=payload,
        actor_id=current_user.id,
        actor_role=current_user.role,
    )


@router.post(
    "/privacy-requests/{id}/review",
    response_model=PrivacyRequest,
    summary="Review and approve/reject a privacy request (Admin only)",
    dependencies=[Depends(rate_limit_mutations)],
)
def review_privacy_request(
    id: Annotated[str, Path(..., description="Privacy request ID")],
    payload: PrivacyRequestReview,
    current_user: Annotated[AuthenticatedUser, Depends(require_admin)],
    db: Annotated[Session, Depends(get_db)],
) -> PrivacyRequest:
    """Reviews and updates the approval status of a privacy request."""
    service = DataGovernanceService(db)
    return service.review_privacy_request(
        request_id=id,
        payload=payload,
        actor_id=current_user.id,
        actor_role=current_user.role,
    )


@router.post(
    "/privacy-requests/{id}/complete",
    response_model=PrivacyRequest,
    summary="Complete an approved privacy request (Admin only)",
    dependencies=[Depends(rate_limit_mutations)],
)
def complete_privacy_request(
    id: Annotated[str, Path(..., description="Privacy request ID")],
    payload: PrivacyRequestComplete,
    current_user: Annotated[AuthenticatedUser, Depends(require_admin)],
    db: Annotated[Session, Depends(get_db)],
) -> PrivacyRequest:
    """Marks an approved privacy request as completed. Zero financial mutations."""
    service = DataGovernanceService(db)
    return service.complete_privacy_request(
        request_id=id,
        notes=payload.notes,
        actor_id=current_user.id,
        actor_role=current_user.role,
    )


@router.get(
    "/report",
    response_model=DataGovernanceReport,
    summary="Generate exportable tamper-evident regulatory governance report",
    dependencies=[Depends(rate_limit_reads)],
)
def generate_governance_report(
    current_user: Annotated[AuthenticatedUser, Depends(require_viewer)],
    db: Annotated[Session, Depends(get_db)],
) -> DataGovernanceReport:
    """Generates complete regulatory data governance snapshot signed with SHA-256."""
    service = DataGovernanceService(db)
    return service.generate_report(actor_id=current_user.id)


@router.post(
    "/scan",
    response_model=PIIScanResponse,
    summary="Run on-demand PII and secret discovery scan on payload",
    dependencies=[Depends(rate_limit_mutations)],
)
def run_pii_discovery_scan(
    payload: PIIScanRequest,
    current_user: Annotated[AuthenticatedUser, Depends(require_operator)],
    db: Annotated[Session, Depends(get_db)],
) -> PIIScanResponse:
    """Scans payload recursively for PII, PAN, Aadhaar, JWTs, and API credentials."""
    service = DataGovernanceService(db)
    return service.scan_payload_pii(payload.payload)
