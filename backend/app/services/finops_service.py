"""RecoverIQ Phase 10I: FinOps, Cost Intelligence, Resource Governance,
Unit Economics & Financial Efficiency Service.

Acts as a facade delegating to the configured FinOpsDataProvider
(DemoFinOpsDataProvider or RuntimeFinOpsDataProvider).

Strict Invariants Enforced:
1. PolicyEngine Supremacy: Sole authoritative financial decision gate.
2. Mandatory Financial Isolation: Delta RecoveryAction = 0, Delta Payment = 0, Delta RecoveryCase = 0.
3. Zero Database Migrations: Reuses append-only AuditLog.
4. Zero Automatic Financial Response: Strictly advisory optimization recommendations.
5. Strict Separation: Infrastructure cost telemetry contains zero customer PII / secrets.
"""

import logging
from sqlalchemy.orm import Session

from app.schemas.finops import (
    BudgetConfigRequest,
    BudgetStatus,
    CostAllocation,
    CostAnomaly,
    CostCategoryBreakdown,
    CostForecast,
    FinOpsIncident,
    FinOpsReadinessGate,
    FinOpsReport,
    FinOpsScoreBreakdown,
    FinOpsSummary,
    OptimizationRecommendation,
    ResourceEfficiency,
    ServiceCostMetric,
    UnitEconomics,
    WasteFinding,
)
from app.services.finops.base import FinOpsDataProvider
from app.services.finops.factory import get_finops_provider

logger = logging.getLogger(__name__)

# List of all 11 Core RecoverIQ Microservices (retained for backward compatibility)
CORE_SERVICES: list[str] = [
    "API Gateway",
    "PolicyEngine",
    "Intelligence Control Plane",
    "ActionDispatcher",
    "Razorpay Action Provider",
    "ZeroTrustSecurityService",
    "Observability Engine",
    "Performance Service",
    "Data Governance Engine",
    "Release Safety Service",
    "AuditLog Ledger Service",
]


class FinOpsService:
    """Enterprise FinOps, Cost Intelligence and Resource Governance Service Facade."""

    def __init__(self, db: Session, mode: str | None = None):
        self.db = db
        self.provider: FinOpsDataProvider = get_finops_provider(db=db, mode=mode)
        self._secret_key = getattr(self.provider, "_secret_key", b"recoveriq_finops_governance_hmac_sha256_key_v1")

    def calculate_score_breakdown(self) -> FinOpsScoreBreakdown:
        """Calculate the 10-factor FinOps Health Score."""
        return self.provider.calculate_score_breakdown()

    def get_summary(self) -> FinOpsSummary:
        """Return executive FinOps Summary."""
        return self.provider.get_summary()

    def get_service_costs(self) -> list[ServiceCostMetric]:
        """Return cost metrics across all services."""
        return self.provider.get_service_costs()

    def get_category_costs(self) -> CostCategoryBreakdown:
        """Return breakdown by cost categories."""
        return self.provider.get_category_costs()

    def get_cost_allocation(self) -> CostAllocation:
        """Return cost allocation across departments, environments, and tags."""
        return self.provider.get_cost_allocation()

    def get_budgets(self) -> list[BudgetStatus]:
        """Return enterprise budget status across dimensions."""
        return self.provider.get_budgets()

    def configure_budget(self, req: BudgetConfigRequest, actor_id: str = "SYSTEM_ADMIN") -> BudgetStatus:
        """Configure budget limits and alert thresholds."""
        return self.provider.configure_budget(req=req, actor_id=actor_id)

    def get_cost_anomalies(self) -> list[CostAnomaly]:
        """Return detected cost anomalies."""
        return self.provider.get_cost_anomalies()

    def get_forecasts(
        self,
        horizon_days: int = 30,
        traffic_multiplier: float = 1.0,
        include_stress: bool = True,
    ) -> CostForecast:
        """Return cost forecasts."""
        return self.provider.get_forecasts(
            horizon_days=horizon_days,
            traffic_multiplier=traffic_multiplier,
            include_stress=include_stress,
        )

    def get_resource_efficiency(self) -> ResourceEfficiency:
        """Return resource utilization and efficiency metrics."""
        return self.provider.get_resource_efficiency()

    def get_waste_findings(self) -> list[WasteFinding]:
        """Return detected idle and waste findings."""
        return self.provider.get_waste_findings()

    def get_optimization_recommendations(self) -> list[OptimizationRecommendation]:
        """Return optimization recommendations."""
        return self.provider.get_optimization_recommendations()

    def approve_optimization(
        self,
        recommendation_id: str,
        decision: str = "APPROVE",
        notes: str = "",
        admin_user_id: str = "SYSTEM_ADMIN",
    ) -> OptimizationRecommendation:
        """Approve an advisory optimization recommendation."""
        return self.provider.approve_optimization(
            recommendation_id=recommendation_id,
            decision=decision,
            notes=notes,
            admin_user_id=admin_user_id,
        )

    def get_unit_economics(self) -> UnitEconomics:
        """Return granular unit economics metrics."""
        return self.provider.get_unit_economics()

    def get_finops_incidents(self) -> list[FinOpsIncident]:
        """Return active and resolved FinOps incidents."""
        return self.provider.get_finops_incidents()

    def process_incident_action(
        self,
        incident_id: str,
        action_type: str,
        notes: str = "",
        operator_id: str = "SYSTEM_OPERATOR",
    ) -> FinOpsIncident:
        """Process an action on a FinOps incident."""
        return self.provider.process_incident_action(
            incident_id=incident_id,
            action_type=action_type,
            notes=notes,
            operator_id=operator_id,
        )

    def get_readiness_gates(self) -> list[FinOpsReadinessGate]:
        """Return production readiness gate evaluation results."""
        return self.provider.get_readiness_gates()

    def generate_signed_report(self) -> FinOpsReport:
        """Generate a cryptographically signed FinOps governance report."""
        return self.provider.generate_signed_report()
