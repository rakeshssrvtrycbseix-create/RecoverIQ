"""REST API Router for Phase 10I: FinOps, Cost Intelligence, Resource Governance,
Unit Economics & Financial Efficiency Control Plane.
"""

import logging
from typing import Annotated

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
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


def get_finops_service(
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
    mode: str | None = Query(None, description="FinOps data provider mode ('runtime' or 'demo')"),
) -> FinOpsService:
    """Resolve FinOpsService with active provider based on mode query param or settings."""
    active_mode = mode or settings.finops_data_mode
    return FinOpsService(db=db, mode=active_mode)


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
    service: Annotated[FinOpsService, Depends(get_finops_service)],
) -> FinOpsSummary:
    """Retrieve executive posture summary of the FinOps Control Plane."""
    return service.get_summary()


@router.get(
    "/score",
    response_model=FinOpsScoreBreakdown,
    summary="Get Deterministic FinOps Health Score Breakdown",
    dependencies=[Depends(rate_limit_reads)],
)
def get_finops_score(
    user: Annotated[AuthenticatedUser, Depends(require_viewer)],
    service: Annotated[FinOpsService, Depends(get_finops_service)],
) -> FinOpsScoreBreakdown:
    """Retrieve 10-factor deterministic FinOps Health Score breakdown."""
    return service.calculate_score_breakdown()


@router.get(
    "/costs",
    response_model=CostAllocation,
    summary="Get Complete Cluster Cost Allocation Matrix",
    dependencies=[Depends(rate_limit_reads)],
)
def get_cluster_cost_allocation(
    user: Annotated[AuthenticatedUser, Depends(require_viewer)],
    service: Annotated[FinOpsService, Depends(get_finops_service)],
) -> CostAllocation:
    """Retrieve cluster-wide cost allocation report across all services and categories."""
    return service.get_cost_allocation()


@router.get(
    "/costs/services",
    response_model=list[ServiceCostMetric],
    summary="Get Microservice Cost Attribution Breakdown",
    dependencies=[Depends(rate_limit_reads)],
)
def get_service_costs(
    user: Annotated[AuthenticatedUser, Depends(require_viewer)],
    service: Annotated[FinOpsService, Depends(get_finops_service)],
) -> list[ServiceCostMetric]:
    """Retrieve cost metrics attributed to each of the 11 core microservices."""
    return service.get_service_costs()


@router.get(
    "/costs/categories",
    response_model=list[CostCategoryBreakdown],
    summary="Get Infrastructure Cost Category Allocation",
    dependencies=[Depends(rate_limit_reads)],
)
def get_category_costs(
    user: Annotated[AuthenticatedUser, Depends(require_viewer)],
    service: Annotated[FinOpsService, Depends(get_finops_service)],
) -> list[CostCategoryBreakdown]:
    """Retrieve cost breakdown by infrastructure category (Compute, DB, Cache, etc.)."""
    return service.get_category_costs()


@router.get(
    "/unit-economics",
    response_model=UnitEconomics,
    summary="Get Unit Economics & Financial Efficiency Metrics",
    dependencies=[Depends(rate_limit_reads)],
)
def get_unit_economics(
    user: Annotated[AuthenticatedUser, Depends(require_viewer)],
    service: Annotated[FinOpsService, Depends(get_finops_service)],
) -> UnitEconomics:
    """Retrieve unit economics metrics (Cost/Txn, Cost/Case, Cost/Prediction, Value Efficiency)."""
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
    service: Annotated[FinOpsService, Depends(get_finops_service)],
) -> ResourceEfficiency:
    """Retrieve infrastructure utilization, headroom, and efficiency assessments."""
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
    service: Annotated[FinOpsService, Depends(get_finops_service)],
) -> list[BudgetStatus]:
    """Retrieve active budget allocations, burn rates, and threshold statuses."""
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
    service: Annotated[FinOpsService, Depends(get_finops_service)],
) -> BudgetStatus:
    """Configure or update budget limits (Admin authorization required)."""
    return service.configure_budget(payload, user.id)


@router.get(
    "/forecasts",
    response_model=CostForecast,
    summary="Get Cost Forecasting Scenarios",
    dependencies=[Depends(rate_limit_reads)],
)
def get_cost_forecasts(
    user: Annotated[AuthenticatedUser, Depends(require_viewer)],
    service: Annotated[FinOpsService, Depends(get_finops_service)],
) -> CostForecast:
    """Retrieve deterministic 7D, 30D, 90D cost forecasts across 5 scenarios."""
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
    service: Annotated[FinOpsService, Depends(get_finops_service)],
) -> CostForecast:
    """Generate customized cost projections with simulated traffic multiplier."""
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
    service: Annotated[FinOpsService, Depends(get_finops_service)],
) -> list[CostAnomaly]:
    """Retrieve detected cost anomalies with cryptographic evidence hashes."""
    return service.get_cost_anomalies()


@router.get(
    "/waste",
    response_model=list[WasteFinding],
    summary="Get Resource Waste & Overprovisioning Findings",
    dependencies=[Depends(rate_limit_reads)],
)
def get_waste_findings(
    user: Annotated[AuthenticatedUser, Depends(require_viewer)],
    service: Annotated[FinOpsService, Depends(get_finops_service)],
) -> list[WasteFinding]:
    """Retrieve identified infrastructure waste items with potential savings."""
    return service.get_waste_findings()


@router.get(
    "/optimizations",
    response_model=list[OptimizationRecommendation],
    summary="Get Optimization Recommendations",
    dependencies=[Depends(rate_limit_reads)],
)
def get_optimization_recommendations(
    user: Annotated[AuthenticatedUser, Depends(require_viewer)],
    service: Annotated[FinOpsService, Depends(get_finops_service)],
) -> list[OptimizationRecommendation]:
    """Retrieve advisory resource optimization recommendations."""
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
    service: Annotated[FinOpsService, Depends(get_finops_service)],
) -> OptimizationRecommendation:
    """Record human admin approval for an optimization recommendation (Admin only)."""
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
    service: Annotated[FinOpsService, Depends(get_finops_service)],
) -> list[FinOpsIncident]:
    """Retrieve event-sourced FinOps cost and budget governance incidents."""
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
    service: Annotated[FinOpsService, Depends(get_finops_service)],
    payload: FinOpsIncidentActionRequest | None = None,
    notes: str | None = Query(None, description="Action notes (query fallback)"),
) -> FinOpsIncident:
    """Acknowledge a FinOps cost incident."""
    action_notes = (
        payload.notes if payload else (notes or "Acknowledged by FinOps operator.")
    )
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
    service: Annotated[FinOpsService, Depends(get_finops_service)],
    payload: FinOpsIncidentActionRequest | None = None,
    notes: str | None = Query(None, description="Action notes (query fallback)"),
) -> FinOpsIncident:
    """Escalate a FinOps cost incident to SRE/FinOps Lead."""
    action_notes = (
        payload.notes if payload else (notes or "Escalated for budget impact review.")
    )
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
    service: Annotated[FinOpsService, Depends(get_finops_service)],
    payload: FinOpsIncidentActionRequest | None = None,
    notes: str | None = Query(None, description="Action notes (query fallback)"),
) -> FinOpsIncident:
    """Mark a FinOps incident as resolved."""
    action_notes = (
        payload.notes if payload else (notes or "Cost anomaly mitigated and verified.")
    )
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
    service: Annotated[FinOpsService, Depends(get_finops_service)],
) -> list[FinOpsReadinessGate]:
    """Evaluate and return the 20 deterministic FinOps Readiness Gates."""
    return service.get_readiness_gates()


@router.get(
    "/report",
    response_model=FinOpsReport,
    summary="Generate Cryptographically Signed FinOps Report",
    dependencies=[Depends(rate_limit_reads)],
)
def get_signed_finops_report(
    user: Annotated[AuthenticatedUser, Depends(require_viewer)],
    service: Annotated[FinOpsService, Depends(get_finops_service)],
) -> FinOpsReport:
    """Generate authoritative executive FinOps report with SHA-256 HMAC signature."""
    return service.generate_signed_report()
