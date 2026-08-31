"""REST API Router for Phase 10I: FinOps, Cost Intelligence, Resource Governance,

Unit Economics & Financial Efficiency Control Plane.
"""

import logging
from typing import Annotated

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.rate_limiter import rate_limit_mutations, rate_limit_reads
from app.core.security import (
    AuthenticatedUser,
    require_admin,
    require_operator,
    require_viewer,
)
from app.schemas.finops import (
    BudgetConfigRequest,
    BudgetStatus,
    CostAllocation,
    CostAnomaly,
    CostCategoryBreakdown,
    CostForecast,
    FinOpsIncident,
    FinOpsIncidentActionRequest,
    FinOpsReadinessGate,
    FinOpsReport,
    FinOpsScoreBreakdown,
    FinOpsSummary,
    ForecastGenerateRequest,
    OptimizationApprovalRequest,
    OptimizationRecommendation,
    ResourceEfficiency,
    ServiceCostMetric,
    UnitEconomics,
    WasteFinding,
)
from app.services.finops_service import FinOpsService

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/recovery/intelligence/finops",
    tags=["finops-cost-governance"],
)


@router.get(
    "",
    response_model=FinOpsSummary,
    summary="Get FinOps Control Plane Summary",
    dependencies=[Depends(rate_limit_reads)],
)
@router.get(
    "/summary",
    response_model=FinOpsSummary,
    summary="Get FinOps Control Plane Summary (Alias)",
    dependencies=[Depends(rate_limit_reads)],
)
def get_finops_summary(
    user: Annotated[AuthenticatedUser, Depends(require_viewer)],
    db: Session = Depends(get_db),
) -> FinOpsSummary:
    """Retrieve executive posture summary of the FinOps Control Plane."""
    service = FinOpsService(db)
    return service.get_summary()


@router.get(
    "/score",
    response_model=FinOpsScoreBreakdown,
    summary="Get Deterministic FinOps Health Score Breakdown",
    dependencies=[Depends(rate_limit_reads)],
)
def get_finops_score(
    user: Annotated[AuthenticatedUser, Depends(require_viewer)],
    db: Session = Depends(get_db),
) -> FinOpsScoreBreakdown:
    """Retrieve 10-factor deterministic FinOps Health Score breakdown."""
    service = FinOpsService(db)
    return service.calculate_score_breakdown()


@router.get(
    "/costs",
    response_model=CostAllocation,
    summary="Get Complete Cluster Cost Allocation Matrix",
    dependencies=[Depends(rate_limit_reads)],
)
def get_cluster_cost_allocation(
    user: Annotated[AuthenticatedUser, Depends(require_viewer)],
    db: Session = Depends(get_db),
) -> CostAllocation:
    """Retrieve cluster-wide cost allocation report across all services and categories."""
    service = FinOpsService(db)
    return service.get_cost_allocation()


@router.get(
    "/costs/services",
    response_model=list[ServiceCostMetric],
    summary="Get Microservice Cost Attribution Breakdown",
    dependencies=[Depends(rate_limit_reads)],
)
def get_service_costs(
    user: Annotated[AuthenticatedUser, Depends(require_viewer)],
    db: Session = Depends(get_db),
) -> list[ServiceCostMetric]:
    """Retrieve cost metrics attributed to each of the 11 core microservices."""
    service = FinOpsService(db)
    return service.get_service_costs()


@router.get(
    "/costs/categories",
    response_model=list[CostCategoryBreakdown],
    summary="Get Infrastructure Cost Category Allocation",
    dependencies=[Depends(rate_limit_reads)],
)
def get_category_costs(
    user: Annotated[AuthenticatedUser, Depends(require_viewer)],
    db: Session = Depends(get_db),
) -> list[CostCategoryBreakdown]:
    """Retrieve cost breakdown by infrastructure category (Compute, DB, Cache, etc.)."""
    service = FinOpsService(db)
    return service.get_category_costs()


@router.get(
    "/unit-economics",
    response_model=UnitEconomics,
    summary="Get Unit Economics & Financial Efficiency Metrics",
    dependencies=[Depends(rate_limit_reads)],
)
def get_unit_economics(
    user: Annotated[AuthenticatedUser, Depends(require_viewer)],
    db: Session = Depends(get_db),
) -> UnitEconomics:
    """Retrieve unit economics metrics (Cost/Txn, Cost/Case, Cost/Prediction, Value Efficiency)."""
    service = FinOpsService(db)
    return service.get_unit_economics()


@router.get(
    "/resources",
    response_model=ResourceEfficiency,
    summary="Get Infrastructure Resource Efficiency & Utilization",
    dependencies=[Depends(rate_limit_reads)],
)
@router.get(
    "/resources/efficiency",
    response_model=ResourceEfficiency,
    summary="Get Infrastructure Resource Efficiency (Alias)",
    dependencies=[Depends(rate_limit_reads)],
)
def get_resource_efficiency(
    user: Annotated[AuthenticatedUser, Depends(require_viewer)],
    db: Session = Depends(get_db),
) -> ResourceEfficiency:
    """Retrieve infrastructure utilization, headroom, and efficiency assessments."""
    service = FinOpsService(db)
    return service.get_resource_efficiency()


@router.get(
    "/budgets",
    response_model=list[BudgetStatus],
    summary="Get Budget Governance Status",
    dependencies=[Depends(rate_limit_reads)],
)
@router.get(
    "/budgets/status",
    response_model=list[BudgetStatus],
    summary="Get Budget Governance Status (Alias)",
    dependencies=[Depends(rate_limit_reads)],
)
def get_budget_statuses(
    user: Annotated[AuthenticatedUser, Depends(require_viewer)],
    db: Session = Depends(get_db),
) -> list[BudgetStatus]:
    """Retrieve active budget allocations, burn rates, and threshold statuses."""
    service = FinOpsService(db)
    return service.get_budgets()


@router.post(
    "/budgets/configure",
    response_model=BudgetStatus,
    summary="Configure Budget Limit (Admin Only)",
    dependencies=[Depends(rate_limit_mutations)],
    status_code=status.HTTP_200_OK,
)
def configure_budget(
    payload: BudgetConfigRequest,
    user: Annotated[AuthenticatedUser, Depends(require_admin)],
    db: Session = Depends(get_db),
) -> BudgetStatus:
    """Configure or update budget limits (Admin authorization required)."""
    service = FinOpsService(db)
    return service.configure_budget(payload, user.id)


@router.get(
    "/forecasts",
    response_model=CostForecast,
    summary="Get Cost Forecasting Scenarios",
    dependencies=[Depends(rate_limit_reads)],
)
def get_cost_forecasts(
    user: Annotated[AuthenticatedUser, Depends(require_viewer)],
    db: Session = Depends(get_db),
) -> CostForecast:
    """Retrieve deterministic 7D, 30D, 90D cost forecasts across 5 scenarios."""
    service = FinOpsService(db)
    return service.get_forecasts()


@router.post(
    "/forecasts/generate",
    response_model=CostForecast,
    summary="Generate Custom Cost Forecast",
    dependencies=[Depends(rate_limit_mutations)],
)
def generate_custom_forecast(
    payload: ForecastGenerateRequest,
    user: Annotated[AuthenticatedUser, Depends(require_operator)],
    db: Session = Depends(get_db),
) -> CostForecast:
    """Generate customized cost projections with simulated traffic multiplier."""
    service = FinOpsService(db)
    return service.get_forecasts(
        horizon_days=payload.horizon_days,
        traffic_multiplier=payload.traffic_multiplier,
        include_stress=payload.include_stress_scenario,
    )


@router.get(
    "/anomalies",
    response_model=list[CostAnomaly],
    summary="Get Cost Anomalies & Spikes",
    dependencies=[Depends(rate_limit_reads)],
)
def get_cost_anomalies(
    user: Annotated[AuthenticatedUser, Depends(require_viewer)],
    db: Session = Depends(get_db),
) -> list[CostAnomaly]:
    """Retrieve detected cost anomalies with cryptographic evidence hashes."""
    service = FinOpsService(db)
    return service.get_cost_anomalies()


@router.get(
    "/waste",
    response_model=list[WasteFinding],
    summary="Get Resource Waste & Overprovisioning Findings",
    dependencies=[Depends(rate_limit_reads)],
)
def get_waste_findings(
    user: Annotated[AuthenticatedUser, Depends(require_viewer)],
    db: Session = Depends(get_db),
) -> list[WasteFinding]:
    """Retrieve identified infrastructure waste items with potential savings."""
    service = FinOpsService(db)
    return service.get_waste_findings()


@router.get(
    "/optimizations",
    response_model=list[OptimizationRecommendation],
    summary="Get Optimization Recommendations",
    dependencies=[Depends(rate_limit_reads)],
)
def get_optimization_recommendations(
    user: Annotated[AuthenticatedUser, Depends(require_viewer)],
    db: Session = Depends(get_db),
) -> list[OptimizationRecommendation]:
    """Retrieve advisory resource optimization recommendations."""
    service = FinOpsService(db)
    return service.get_optimization_recommendations()


@router.post(
    "/optimizations/{recommendation_id}/approve",
    response_model=OptimizationRecommendation,
    summary="Approve or Reject Optimization Recommendation (Admin Only)",
    dependencies=[Depends(rate_limit_mutations)],
)
def approve_optimization_recommendation(
    recommendation_id: str,
    payload: OptimizationApprovalRequest,
    user: Annotated[AuthenticatedUser, Depends(require_admin)],
    db: Session = Depends(get_db),
) -> OptimizationRecommendation:
    """Record human admin approval for an optimization recommendation (Admin only)."""
    service = FinOpsService(db)
    return service.approve_optimization(
        recommendation_id=recommendation_id,
        decision=payload.decision,
        notes=payload.notes,
        admin_user_id=user.id,
    )


@router.get(
    "/incidents",
    response_model=list[FinOpsIncident],
    summary="Get FinOps Governance Incidents",
    dependencies=[Depends(rate_limit_reads)],
)
def get_finops_incidents(
    user: Annotated[AuthenticatedUser, Depends(require_viewer)],
    db: Session = Depends(get_db),
) -> list[FinOpsIncident]:
    """Retrieve event-sourced FinOps cost and budget governance incidents."""
    service = FinOpsService(db)
    return service.get_finops_incidents()


@router.post(
    "/incidents/{incident_id}/acknowledge",
    response_model=FinOpsIncident,
    summary="Acknowledge FinOps Incident",
    dependencies=[Depends(rate_limit_mutations)],
)
def acknowledge_finops_incident(
    incident_id: str,
    user: Annotated[AuthenticatedUser, Depends(require_operator)],
    db: Session = Depends(get_db),
    payload: FinOpsIncidentActionRequest | None = None,
    notes: str | None = Query(None, description="Action notes (query fallback)"),
) -> FinOpsIncident:
    """Acknowledge a FinOps cost incident."""
    action_notes = (
        payload.notes if payload else (notes or "Acknowledged by FinOps operator.")
    )
    service = FinOpsService(db)
    return service.process_incident_action(
        incident_id=incident_id,
        action_type="ACKNOWLEDGE",
        notes=action_notes,
        operator_id=user.id,
    )


@router.post(
    "/incidents/{incident_id}/escalate",
    response_model=FinOpsIncident,
    summary="Escalate FinOps Incident",
    dependencies=[Depends(rate_limit_mutations)],
)
def escalate_finops_incident(
    incident_id: str,
    user: Annotated[AuthenticatedUser, Depends(require_operator)],
    db: Session = Depends(get_db),
    payload: FinOpsIncidentActionRequest | None = None,
    notes: str | None = Query(None, description="Action notes (query fallback)"),
) -> FinOpsIncident:
    """Escalate a FinOps cost incident to SRE/FinOps Lead."""
    action_notes = (
        payload.notes if payload else (notes or "Escalated for budget impact review.")
    )
    service = FinOpsService(db)
    return service.process_incident_action(
        incident_id=incident_id,
        action_type="ESCALATE",
        notes=action_notes,
        operator_id=user.id,
    )


@router.post(
    "/incidents/{incident_id}/resolve",
    response_model=FinOpsIncident,
    summary="Resolve FinOps Incident",
    dependencies=[Depends(rate_limit_mutations)],
)
def resolve_finops_incident(
    incident_id: str,
    user: Annotated[AuthenticatedUser, Depends(require_operator)],
    db: Session = Depends(get_db),
    payload: FinOpsIncidentActionRequest | None = None,
    notes: str | None = Query(None, description="Action notes (query fallback)"),
) -> FinOpsIncident:
    """Mark a FinOps incident as resolved."""
    action_notes = (
        payload.notes if payload else (notes or "Cost anomaly mitigated and verified.")
    )
    service = FinOpsService(db)
    return service.process_incident_action(
        incident_id=incident_id,
        action_type="RESOLVE",
        notes=action_notes,
        operator_id=user.id,
    )


@router.get(
    "/readiness",
    response_model=list[FinOpsReadinessGate],
    summary="Get 20 Deterministic FinOps Readiness Gates",
    dependencies=[Depends(rate_limit_reads)],
)
def get_finops_readiness_gates(
    user: Annotated[AuthenticatedUser, Depends(require_viewer)],
    db: Session = Depends(get_db),
) -> list[FinOpsReadinessGate]:
    """Evaluate and return the 20 deterministic FinOps Readiness Gates."""
    service = FinOpsService(db)
    return service.get_readiness_gates()


@router.get(
    "/report",
    response_model=FinOpsReport,
    summary="Generate Cryptographically Signed FinOps Report",
    dependencies=[Depends(rate_limit_reads)],
)
def get_signed_finops_report(
    user: Annotated[AuthenticatedUser, Depends(require_viewer)],
    db: Session = Depends(get_db),
) -> FinOpsReport:
    """Generate authoritative executive FinOps report with SHA-256 HMAC signature."""
    service = FinOpsService(db)
    return service.generate_signed_report()
