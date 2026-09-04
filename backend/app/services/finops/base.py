"""Abstract Base Class for Phase 10I FinOps Data Providers.

Defines the contract for both DemoFinOpsDataProvider (deterministic demo mode)
and RuntimeFinOpsDataProvider (live RecoverIQ database/runtime telemetry).
"""

from abc import ABC, abstractmethod

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


class FinOpsDataProvider(ABC):
    """Abstract interface defining all FinOps Control Plane analytical operations."""

    @abstractmethod
    def calculate_score_breakdown(self) -> FinOpsScoreBreakdown:
        """Calculate the 10-factor FinOps Health Score."""
        ...

    @abstractmethod
    def get_service_costs(self) -> list[ServiceCostMetric]:
        """Return granular cost attribution metrics for all core microservices."""
        ...

    @abstractmethod
    def get_category_costs(self) -> list[CostCategoryBreakdown]:
        """Return infrastructure cost allocations across infrastructure categories."""
        ...

    @abstractmethod
    def get_cost_allocation(self) -> CostAllocation:
        """Return aggregated cluster cost allocation report."""
        ...

    @abstractmethod
    def get_unit_economics(self) -> UnitEconomics:
        """Return unit economics and financial efficiency metrics."""
        ...

    @abstractmethod
    def get_resource_efficiency(self) -> ResourceEfficiency:
        """Return infrastructure resource efficiency and utilization."""
        ...

    @abstractmethod
    def get_budgets(self) -> list[BudgetStatus]:
        """Return governance status of active budgets (Daily, Weekly, Monthly, Quarterly)."""
        ...

    @abstractmethod
    def configure_budget(self, req: BudgetConfigRequest, actor_id: str) -> BudgetStatus:
        """Update a budget allocation and record an immutable AuditLog event."""
        ...

    @abstractmethod
    def get_forecasts(
        self,
        horizon_days: int = 30,
        traffic_multiplier: float = 1.0,
        include_stress: bool = True,
    ) -> CostForecast:
        """Generate cost forecasts across scenarios."""
        ...

    @abstractmethod
    def get_cost_anomalies(self) -> list[CostAnomaly]:
        """Detect and return cost anomalies."""
        ...

    @abstractmethod
    def get_waste_findings(self) -> list[WasteFinding]:
        """Return detected infrastructure waste and overprovisioning findings."""
        ...

    @abstractmethod
    def get_optimization_recommendations(self) -> list[OptimizationRecommendation]:
        """Return advisory optimization recommendations with governance tracking."""
        ...

    @abstractmethod
    def approve_optimization(
        self,
        recommendation_id: str,
        decision: str,
        notes: str,
        admin_user_id: str,
    ) -> OptimizationRecommendation:
        """Record human administrator approval or rejection of an advisory recommendation."""
        ...

    @abstractmethod
    def get_finops_incidents(self) -> list[FinOpsIncident]:
        """Return FinOps governance and budget incidents."""
        ...

    @abstractmethod
    def process_incident_action(
        self,
        incident_id: str,
        action_type: str,
        notes: str,
        operator_id: str,
    ) -> FinOpsIncident:
        """Process operator action (ACKNOWLEDGE, ESCALATE, RESOLVE) on an incident."""
        ...

    @abstractmethod
    def get_readiness_gates(self) -> list[FinOpsReadinessGate]:
        """Evaluate the 20 FinOps Readiness Gates (GATE-FIN-01 .. GATE-FIN-20)."""
        ...

    @abstractmethod
    def get_summary(self) -> FinOpsSummary:
        """Calculate executive FinOps posture summary."""
        ...

    @abstractmethod
    def generate_signed_report(self) -> FinOpsReport:
        """Generate a cryptographically signed executive FinOps report."""
        ...
