"""Deterministic Development & Demo Mode Data Provider for RecoverIQ FinOps Control Plane.

Encapsulates 100% of the baseline deterministic simulation logic for local demonstrations,
architectural proofs, and regression test suites.
"""

import hashlib
import hmac
import logging
from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy.orm import Session

from app.models.audit_log import AuditLog
from app.models.enums import (
    BudgetState,
    CostAnomalySeverity,
    CostAnomalyType,
    CostCategory,
    CostSource,
    FinOpsAuditEventType,
    FinOpsGateId,
    FinOpsGateStatus,
    FinOpsGlobalState,
    FinOpsHealth,
    FinOpsIncidentStatus,
    FinOpsIncidentType,
    FinOpsSeverity,
    ForecastState,
    OptimizationRisk,
    OptimizationStatus,
    OptimizationType,
    ResourceEfficiencyState,
    ResourceType,
)
from app.schemas.finops import (
    BudgetConfigRequest,
    BudgetStatus,
    BudgetThreshold,
    CacheCost,
    CostAllocation,
    CostAnomaly,
    CostCategoryBreakdown,
    CostForecast,
    CostPerRecoveryCase,
    CostPerTransaction,
    DatabaseCost,
    FinOpsIncident,
    FinOpsReadinessGate,
    FinOpsReport,
    FinOpsScoreBreakdown,
    FinOpsSummary,
    ForecastScenario,
    MLInferenceCost,
    OptimizationImpact,
    OptimizationRecommendation,
    ResourceEfficiency,
    ResourceUtilization,
    ServiceCostMetric,
    UnitEconomics,
    WasteFinding,
    WebhookCost,
)
from app.services.finops.base import FinOpsDataProvider

logger = logging.getLogger(__name__)

# List of all 11 Core RecoverIQ Microservices
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


class DemoFinOpsDataProvider(FinOpsDataProvider):
    """Deterministic demo and test data provider returning verified baseline models."""

    def __init__(self, db: Session):
        self.db = db
        self._secret_key = b"recoveriq_finops_governance_hmac_sha256_key_v1"
        self.provider_name = "DemoFinOpsDataProvider"
        self.data_mode = "demo"

    def calculate_score_breakdown(self) -> FinOpsScoreBreakdown:
        """Calculate the 10-factor deterministic FinOps Health Score."""
        cost_alloc = 98.5
        budget_health = 92.0
        forecast_acc = 94.0
        res_eff = 88.5
        unit_econ = 96.0
        cost_anomaly = 95.0
        cap_eff = 91.0
        waste_det = 89.0
        tagging_gov = 99.0
        opt_readiness = 94.0

        composite = (
            0.15 * cost_alloc
            + 0.10 * budget_health
            + 0.10 * forecast_acc
            + 0.10 * res_eff
            + 0.10 * unit_econ
            + 0.10 * cost_anomaly
            + 0.10 * cap_eff
            + 0.10 * waste_det
            + 0.05 * tagging_gov
            + 0.10 * opt_readiness
        )
        composite = round(min(100.0, max(0.0, composite)), 2)

        if composite >= 90.0:
            classification = FinOpsHealth.EXCELLENT
        elif composite >= 80.0:
            classification = FinOpsHealth.GOOD
        elif composite >= 70.0:
            classification = FinOpsHealth.WARNING
        elif composite >= 60.0:
            classification = FinOpsHealth.DEGRADED
        elif composite >= 45.0:
            classification = FinOpsHealth.HIGH_RISK
        else:
            classification = FinOpsHealth.CRITICAL

        return FinOpsScoreBreakdown(
            cost_allocation_score=cost_alloc,
            budget_health_score=budget_health,
            forecast_accuracy_score=forecast_acc,
            resource_efficiency_score=res_eff,
            unit_economics_score=unit_econ,
            cost_anomaly_score=cost_anomaly,
            capacity_efficiency_score=cap_eff,
            waste_detection_score=waste_det,
            tagging_governance_score=tagging_gov,
            optimization_readiness_score=opt_readiness,
            composite_finops_score=composite,
            classification=classification,
            component_sources={
                "cost_allocation": "demo",
                "budget_health": "demo",
                "forecast_accuracy": "demo",
                "resource_efficiency": "demo",
                "unit_economics": "demo",
                "cost_anomaly": "demo",
                "capacity_efficiency": "demo",
                "waste_detection": "demo",
                "tagging_governance": "demo",
                "optimization_readiness": "demo",
            },
        )

    def get_service_costs(self) -> list[ServiceCostMetric]:
        """Return granular cost attribution metrics for all 11 core microservices."""
        service_data = [
            ("API Gateway", 18500.0, 15.0, 4800.0, 3.85, 78.0, 72.0, 10500.0, 2000.0, 1500.0, 4500.0, 0.0, ResourceEfficiencyState.OPTIMAL),
            ("PolicyEngine", 14200.0, 11.5, 2100.0, 6.76, 74.0, 80.0, 8500.0, 3200.0, 1500.0, 1000.0, 0.0, ResourceEfficiencyState.OPTIMAL),
            ("Intelligence Control Plane", 16800.0, 13.6, 1850.0, 9.08, 82.0, 85.0, 7200.0, 3100.0, 1500.0, 1200.0, 3800.0, ResourceEfficiencyState.OPTIMAL),
            ("ActionDispatcher", 9400.0, 7.6, 950.0, 9.89, 65.0, 68.0, 5200.0, 2400.0, 1000.0, 800.0, 0.0, ResourceEfficiencyState.ACCEPTABLE),
            ("Razorpay Action Provider", 12300.0, 10.0, 1400.0, 8.79, 70.0, 75.0, 6500.0, 2800.0, 1200.0, 1800.0, 0.0, ResourceEfficiencyState.OPTIMAL),
            ("ZeroTrustSecurityService", 8900.0, 7.2, 3200.0, 2.78, 68.0, 70.0, 5800.0, 1200.0, 900.0, 1000.0, 0.0, ResourceEfficiencyState.ACCEPTABLE),
            ("Observability Engine", 15400.0, 12.5, 2900.0, 5.31, 75.0, 82.0, 6800.0, 4200.0, 1800.0, 2600.0, 0.0, ResourceEfficiencyState.OPTIMAL),
            ("Performance Service", 7200.0, 5.8, 850.0, 8.47, 60.0, 64.0, 4200.0, 1500.0, 800.0, 700.0, 0.0, ResourceEfficiencyState.ACCEPTABLE),
            ("Data Governance Engine", 6800.0, 5.5, 620.0, 10.97, 58.0, 62.0, 3800.0, 1800.0, 600.0, 600.0, 0.0, ResourceEfficiencyState.UNDERUTILIZED),
            ("Release Safety Service", 5900.0, 4.8, 410.0, 14.39, 52.0, 58.0, 3500.0, 1400.0, 500.0, 500.0, 0.0, ResourceEfficiencyState.UNDERUTILIZED),
            ("AuditLog Ledger Service", 8100.0, 6.5, 3800.0, 2.13, 72.0, 78.0, 4200.0, 3100.0, 400.0, 400.0, 0.0, ResourceEfficiencyState.OPTIMAL),
        ]

        return [
            ServiceCostMetric(
                service_name=s[0],
                monthly_cost_inr=s[1],
                cost_share_pct=s[2],
                rpm=s[3],
                cost_per_1k_requests_inr=s[4],
                cpu_efficiency_pct=s[5],
                memory_efficiency_pct=s[6],
                compute_cost_inr=s[7],
                database_cost_inr=s[8],
                cache_cost_inr=s[9],
                network_cost_inr=s[10],
                ml_cost_inr=s[11],
                efficiency_status=s[12],
                source="demo",
                provider=self.provider_name,
                confidence=1.0,
            )
            for s in service_data
        ]

    def get_category_costs(self) -> list[CostCategoryBreakdown]:
        """Return infrastructure cost allocations across all 10 categories."""
        categories = [
            (CostCategory.COMPUTE, 45.0, 1080.0, 32400.0, 26.2, 1.8, CostSource.AWS_ESTIMATED),
            (CostCategory.DATABASE, 38.0, 912.0, 27360.0, 22.1, 2.1, CostSource.AWS_ESTIMATED),
            (CostCategory.CACHE, 16.0, 384.0, 11520.0, 9.3, -0.5, CostSource.AWS_ESTIMATED),
            (CostCategory.STORAGE, 12.0, 288.0, 8640.0, 7.0, 3.2, CostSource.AWS_ESTIMATED),
            (CostCategory.NETWORK, 18.0, 432.0, 12960.0, 10.5, 1.2, CostSource.AWS_ESTIMATED),
            (CostCategory.WEBHOOK_PROCESSING, 14.0, 336.0, 10080.0, 8.2, 0.8, CostSource.DERIVED_METRIC),
            (CostCategory.ML_INFERENCE, 12.5, 300.0, 9000.0, 7.3, 4.5, CostSource.DERIVED_METRIC),
            (CostCategory.QUEUE_PROCESSING, 7.5, 180.0, 5400.0, 4.4, -1.0, CostSource.DERIVED_METRIC),
            (CostCategory.MONITORING, 5.0, 120.0, 3600.0, 2.9, 0.0, CostSource.OBSERVED_TELEMETRY),
            (CostCategory.EXTERNAL_APIS, 3.5, 84.0, 2520.0, 2.1, 0.5, CostSource.OBSERVED_TELEMETRY),
        ]

        return [
            CostCategoryBreakdown(
                category=c[0],
                hourly_cost_inr=c[1],
                daily_cost_inr=c[2],
                monthly_cost_inr=c[3],
                cost_share_pct=c[4],
                trend_pct=c[5],
                source=c[6],
                provider=self.provider_name,
                disclaimer="Simulated demo cloud billing metric",
            )
            for c in categories
        ]

    def get_cost_allocation(self) -> CostAllocation:
        """Return aggregated cluster cost allocation report."""
        services = self.get_service_costs()
        categories = self.get_category_costs()
        total_monthly = sum(s.monthly_cost_inr for s in services)
        total_daily = round(total_monthly / 30.0, 2)
        total_hourly = round(total_daily / 24.0, 2)

        return CostAllocation(
            total_monthly_cost_inr=total_monthly,
            total_daily_cost_inr=total_daily,
            total_hourly_cost_inr=total_hourly,
            services=services,
            categories=categories,
            evaluated_at=datetime.now(UTC),
            data_mode="demo",
            provider=self.provider_name,
        )

    def get_unit_economics(self) -> UnitEconomics:
        """Return unit economics and financial efficiency metrics."""
        return UnitEconomics(
            cost_per_transaction=CostPerTransaction(
                cost_per_successful_txn_inr=0.48,
                cost_per_attempted_txn_inr=0.18,
                monthly_transaction_volume=185000,
                total_transaction_infrastructure_cost_inr=33300.0,
            ),
            cost_per_recovery_case=CostPerRecoveryCase(
                cost_per_case_inr=14.20,
                cost_per_resolved_case_inr=22.80,
                monthly_case_volume=8700,
                total_case_infrastructure_cost_inr=123540.0,
            ),
            ml_inference_cost=MLInferenceCost(
                cost_per_prediction_inr=0.035,
                cost_per_training_run_inr=420.0,
                monthly_prediction_volume=257000,
                total_ml_infrastructure_cost_inr=9000.0,
            ),
            database_cost=DatabaseCost(
                cost_per_100k_queries_inr=4.20,
                storage_cost_per_gb_inr=12.50,
                iops_cost_inr=8500.0,
                monthly_database_cost_inr=27360.0,
            ),
            cache_cost=CacheCost(
                cost_per_1m_ops_inr=1.85,
                hit_rate_pct=96.4,
                monthly_cache_cost_inr=11520.0,
            ),
            webhook_cost=WebhookCost(
                cost_per_1k_webhooks_inr=2.45,
                monthly_webhook_volume=411000,
                total_webhook_infrastructure_cost_inr=10080.0,
            ),
            cost_per_1k_requests_inr=5.42,
            recovery_intelligence_value_efficiency=18.65,
            evaluated_at=datetime.now(UTC),
            data_mode="demo",
            provider=self.provider_name,
            provenance={"all_metrics": "demo"},
        )

    def get_resource_efficiency(self) -> ResourceEfficiency:
        """Return comprehensive infrastructure resource efficiency and utilization."""
        resources = [
            ResourceUtilization(
                resource_type=ResourceType.CPU,
                allocated_units="32 vCPU",
                utilization_pct=71.5,
                safe_capacity_pct=80.0,
                headroom_pct=28.5,
                efficiency_pct=89.4,
                waste_pct=8.5,
                state=ResourceEfficiencyState.OPTIMAL,
                source="demo",
                provider=self.provider_name,
            ),
            ResourceUtilization(
                resource_type=ResourceType.MEMORY,
                allocated_units="128 GB",
                utilization_pct=74.2,
                safe_capacity_pct=85.0,
                headroom_pct=25.8,
                efficiency_pct=87.3,
                waste_pct=10.8,
                state=ResourceEfficiencyState.OPTIMAL,
                source="demo",
                provider=self.provider_name,
            ),
            ResourceUtilization(
                resource_type=ResourceType.DATABASE_IOPS,
                allocated_units="6000 IOPS",
                utilization_pct=62.0,
                safe_capacity_pct=75.0,
                headroom_pct=38.0,
                efficiency_pct=82.6,
                waste_pct=13.0,
                state=ResourceEfficiencyState.ACCEPTABLE,
                source="demo",
                provider=self.provider_name,
            ),
            ResourceUtilization(
                resource_type=ResourceType.DATABASE_STORAGE,
                allocated_units="500 GB SSD",
                utilization_pct=48.0,
                safe_capacity_pct=80.0,
                headroom_pct=52.0,
                efficiency_pct=60.0,
                waste_pct=32.0,
                state=ResourceEfficiencyState.OVERPROVISIONED,
                source="demo",
                provider=self.provider_name,
            ),
            ResourceUtilization(
                resource_type=ResourceType.REDIS_MEMORY,
                allocated_units="32 GB Redis Cluster",
                utilization_pct=58.5,
                safe_capacity_pct=75.0,
                headroom_pct=41.5,
                efficiency_pct=78.0,
                waste_pct=16.5,
                state=ResourceEfficiencyState.ACCEPTABLE,
                source="demo",
                provider=self.provider_name,
            ),
            ResourceUtilization(
                resource_type=ResourceType.QUEUE_CAPACITY,
                allocated_units="1000 msg/sec Queue",
                utilization_pct=42.0,
                safe_capacity_pct=80.0,
                headroom_pct=58.0,
                efficiency_pct=52.5,
                waste_pct=38.0,
                state=ResourceEfficiencyState.UNDERUTILIZED,
                source="demo",
                provider=self.provider_name,
            ),
            ResourceUtilization(
                resource_type=ResourceType.DISK_STORAGE,
                allocated_units="1 TB EBS",
                utilization_pct=36.0,
                safe_capacity_pct=80.0,
                headroom_pct=64.0,
                efficiency_pct=45.0,
                waste_pct=44.0,
                state=ResourceEfficiencyState.OVERPROVISIONED,
                source="demo",
                provider=self.provider_name,
            ),
            ResourceUtilization(
                resource_type=ResourceType.EGRESS_BANDWIDTH,
                allocated_units="1 Gbps Dedicated",
                utilization_pct=28.0,
                safe_capacity_pct=70.0,
                headroom_pct=72.0,
                efficiency_pct=40.0,
                waste_pct=42.0,
                state=ResourceEfficiencyState.UNDERUTILIZED,
                source="demo",
                provider=self.provider_name,
            ),
            ResourceUtilization(
                resource_type=ResourceType.ML_GPU_COMPUTE,
                allocated_units="2x NVIDIA T4",
                utilization_pct=78.0,
                safe_capacity_pct=85.0,
                headroom_pct=22.0,
                efficiency_pct=91.8,
                waste_pct=7.0,
                state=ResourceEfficiencyState.OPTIMAL,
                source="demo",
                provider=self.provider_name,
            ),
            ResourceUtilization(
                resource_type=ResourceType.WEBHOOK_WORKER_PODS,
                allocated_units="8 Replicas HPA",
                utilization_pct=68.0,
                safe_capacity_pct=80.0,
                headroom_pct=32.0,
                efficiency_pct=85.0,
                waste_pct=12.0,
                state=ResourceEfficiencyState.OPTIMAL,
                source="demo",
                provider=self.provider_name,
            ),
        ]

        avg_eff = round(sum(r.efficiency_pct for r in resources) / len(resources), 2)
        total_waste_cost = 14850.0

        return ResourceEfficiency(
            overall_efficiency_pct=avg_eff,
            total_waste_cost_inr=total_waste_cost,
            resources=resources,
            evaluated_at=datetime.now(UTC),
            data_mode="demo",
            provider=self.provider_name,
        )

    def get_budgets(self) -> list[BudgetStatus]:
        """Return governance status of active budgets (Daily, Weekly, Monthly, Quarterly)."""
        now = datetime.now(UTC)
        threshold_defs = [50.0, 70.0, 85.0, 95.0, 100.0]

        def build_thresholds(budget_amt: float, actual_amt: float) -> list[BudgetThreshold]:
            pct = (actual_amt / budget_amt) * 100.0 if budget_amt > 0 else 0.0
            return [
                BudgetThreshold(
                    threshold_pct=t,
                    threshold_amount_inr=round(budget_amt * (t / 100.0), 2),
                    breached=pct >= t,
                    breached_at=now if pct >= t else None,
                )
                for t in threshold_defs
            ]

        monthly_budget = 145000.0
        monthly_actual = 123500.0
        monthly_committed = 15000.0
        monthly_forecast = 138000.0

        daily_budget = round(monthly_budget / 30.0, 2)
        daily_actual = 4116.0
        weekly_budget = round(monthly_budget / 4.0, 2)
        weekly_actual = 28816.0
        quarterly_budget = round(monthly_budget * 3.0, 2)
        quarterly_actual = 360000.0

        return [
            BudgetStatus(
                period="DAILY",
                budget_amount_inr=daily_budget,
                actual_amount_inr=daily_actual,
                committed_amount_inr=500.0,
                forecast_amount_inr=4600.0,
                remaining_amount_inr=round(daily_budget - daily_actual, 2),
                burn_rate_pct=round((daily_actual / daily_budget) * 100.0, 1),
                projected_overrun_inr=0.0,
                state=BudgetState.HEALTHY,
                thresholds=build_thresholds(daily_budget, daily_actual),
            ),
            BudgetStatus(
                period="WEEKLY",
                budget_amount_inr=weekly_budget,
                actual_amount_inr=weekly_actual,
                committed_amount_inr=3500.0,
                forecast_amount_inr=32200.0,
                remaining_amount_inr=round(weekly_budget - weekly_actual, 2),
                burn_rate_pct=round((weekly_actual / weekly_budget) * 100.0, 1),
                projected_overrun_inr=0.0,
                state=BudgetState.HEALTHY,
                thresholds=build_thresholds(weekly_budget, weekly_actual),
            ),
            BudgetStatus(
                period="MONTHLY",
                budget_amount_inr=monthly_budget,
                actual_amount_inr=monthly_actual,
                committed_amount_inr=monthly_committed,
                forecast_amount_inr=monthly_forecast,
                remaining_amount_inr=round(monthly_budget - monthly_actual, 2),
                burn_rate_pct=round((monthly_actual / monthly_budget) * 100.0, 1),
                projected_overrun_inr=0.0,
                state=BudgetState.HEALTHY,
                thresholds=build_thresholds(monthly_budget, monthly_actual),
            ),
            BudgetStatus(
                period="QUARTERLY",
                budget_amount_inr=quarterly_budget,
                actual_amount_inr=quarterly_actual,
                committed_amount_inr=45000.0,
                forecast_amount_inr=414000.0,
                remaining_amount_inr=round(quarterly_budget - quarterly_actual, 2),
                burn_rate_pct=round((quarterly_actual / quarterly_budget) * 100.0, 1),
                projected_overrun_inr=0.0,
                state=BudgetState.HEALTHY,
                thresholds=build_thresholds(quarterly_budget, quarterly_actual),
            ),
        ]

    def configure_budget(self, req: BudgetConfigRequest, actor_id: str) -> BudgetStatus:
        """Update a budget allocation and record an immutable AuditLog event."""
        logger.info(
            f"Budget updated for period {req.period} by actor {actor_id}: {req.budget_amount_inr} INR"
        )

        audit_entry = AuditLog(
            entity_type="budget_event",
            event_type="BUDGET_CONFIGURED",
            action="BUDGET_CONFIGURED",
            actor_type="USER",
            actor_id=actor_id,
            new_state=req.model_dump(mode="json"),
            metadata_json={
                "period": req.period,
                "budget_amount_inr": req.budget_amount_inr,
                "notes": req.notes,
            },
        )
        self.db.add(audit_entry)
        self.db.commit()

        budgets = self.get_budgets()
        for b in budgets:
            if b.period == req.period.upper():
                return b
        return budgets[2]

    def get_forecasts(
        self,
        horizon_days: int = 30,
        traffic_multiplier: float = 1.0,
        include_stress: bool = True,
    ) -> CostForecast:
        """Generate deterministic cost forecasts across 5 scenarios."""
        now = datetime.now(UTC)
        baseline_cost = 123500.0

        scenarios = [
            ForecastScenario(
                scenario_name="BASELINE",
                growth_rate_pct=2.5,
                forecast_7d_inr=round(baseline_cost * (7 / 30) * 1.025 * traffic_multiplier, 2),
                forecast_30d_inr=round(baseline_cost * 1.025 * traffic_multiplier, 2),
                forecast_90d_inr=round(baseline_cost * 3 * 1.05 * traffic_multiplier, 2),
                confidence_score=0.96,
                budget_variance_pct=-12.7,
                assumptions=[
                    "Normal organic traffic",
                    "No infrastructure resizing",
                    "Stable cloud pricing",
                ],
            ),
            ForecastScenario(
                scenario_name="GROWTH",
                growth_rate_pct=15.0,
                forecast_7d_inr=round(baseline_cost * (7 / 30) * 1.15 * traffic_multiplier, 2),
                forecast_30d_inr=round(baseline_cost * 1.15 * traffic_multiplier, 2),
                forecast_90d_inr=round(baseline_cost * 3 * 1.30 * traffic_multiplier, 2),
                confidence_score=0.91,
                budget_variance_pct=-2.1,
                assumptions=[
                    "15% month-over-month volume increase",
                    "HPA autoscaling enabled",
                    "Predictable cache ratio",
                ],
            ),
            ForecastScenario(
                scenario_name="HIGH_GROWTH",
                growth_rate_pct=35.0,
                forecast_7d_inr=round(baseline_cost * (7 / 30) * 1.35 * traffic_multiplier, 2),
                forecast_30d_inr=round(baseline_cost * 1.35 * traffic_multiplier, 2),
                forecast_90d_inr=round(baseline_cost * 3 * 1.70 * traffic_multiplier, 2),
                confidence_score=0.86,
                budget_variance_pct=15.0,
                assumptions=[
                    "35% surge in payment retries",
                    "Database IOPS scale-up",
                    "Additional ML worker pods",
                ],
            ),
            ForecastScenario(
                scenario_name="TRAFFIC_SURGE",
                growth_rate_pct=75.0,
                forecast_7d_inr=round(baseline_cost * (7 / 30) * 1.75 * traffic_multiplier, 2),
                forecast_30d_inr=round(baseline_cost * 1.75 * traffic_multiplier, 2),
                forecast_90d_inr=round(baseline_cost * 3 * 2.20 * traffic_multiplier, 2),
                confidence_score=0.82,
                budget_variance_pct=49.1,
                assumptions=[
                    "E-commerce festival peak load",
                    "3x webhook ingestion volume",
                    "Burst cache cluster scaling",
                ],
            ),
        ]

        if include_stress:
            scenarios.append(
                ForecastScenario(
                    scenario_name="STRESS",
                    growth_rate_pct=150.0,
                    forecast_7d_inr=round(baseline_cost * (7 / 30) * 2.50 * traffic_multiplier, 2),
                    forecast_30d_inr=round(baseline_cost * 2.50 * traffic_multiplier, 2),
                    forecast_90d_inr=round(baseline_cost * 3 * 3.50 * traffic_multiplier, 2),
                    confidence_score=0.75,
                    budget_variance_pct=112.9,
                    assumptions=[
                        "Simulated extreme 5x throughput stress",
                        "Maximum pod replication",
                        "High memory saturation",
                    ],
                )
            )

        return CostForecast(
            forecast_id=f"FC-FIN-{now.strftime('%Y%m%d%H%M')}",
            generated_at=now,
            baseline_monthly_cost_inr=baseline_cost,
            forecast_state=ForecastState.ON_TRACK,
            scenarios=scenarios,
        )

    def get_cost_anomalies(self) -> list[CostAnomaly]:
        """Detect and return statistical cost anomalies."""
        now = datetime.now(UTC)
        anomalies_data = [
            (
                "ANOM-8F10A2C1",
                CostAnomalyType.DATABASE_COST_SPIKE,
                CostAnomalySeverity.MEDIUM,
                "Observability Engine",
                CostCategory.DATABASE,
                4200.0,
                5800.0,
                38.1,
                0.94,
                "High metric retention index rebuild. Consider adjusting raw telemetry TTL from 90d to 30d.",
            ),
            (
                "ANOM-3C9D4E2F",
                CostAnomalyType.UNEXPECTED_SERVICE_GROWTH,
                CostAnomalySeverity.LOW,
                "Razorpay Action Provider",
                CostCategory.NETWORK,
                1200.0,
                1800.0,
                50.0,
                0.89,
                "Webhook replay burst during gateway maintenance window. Egress stabilized.",
            ),
            (
                "ANOM-7B5A1D9C",
                CostAnomalyType.IDLE_RESOURCE_WASTE,
                CostAnomalySeverity.LOW,
                "Data Governance Engine",
                CostCategory.STORAGE,
                2400.0,
                2400.0,
                0.0,
                0.92,
                "Unattached backup snapshots detected. Automated lifecycle pruning recommended.",
            ),
        ]

        result = []
        for a in anomalies_data:
            evid_str = f"{a[0]}|{a[1].value}|{a[3]}|{a[4].value}|{a[6]}"
            evid_hash = hashlib.sha256(evid_str.encode()).hexdigest()
            result.append(
                CostAnomaly(
                    anomaly_id=a[0],
                    anomaly_type=a[1],
                    severity=a[2],
                    affected_service=a[3],
                    affected_category=a[4],
                    detected_at=now,
                    baseline_cost_inr=a[5],
                    observed_cost_inr=a[6],
                    deviation_pct=a[7],
                    confidence_score=a[8],
                    evidence_hash=evid_hash,
                    recommended_action=a[9],
                )
            )
        return result

    def get_waste_findings(self) -> list[WasteFinding]:
        """Return detected infrastructure waste and overprovisioning findings."""
        findings = [
            ("WST-01", "OVERSIZED_DATABASE", "Aurora PostgreSQL Storage (500 GB)", "Performance Service", 3200.0, OptimizationRisk.LOW, 0.95, "Downsize pre-allocated volume to 250 GB with automated storage tiering.", "Instant dynamic auto-expansion trigger on 80% volume fill."),
            ("WST-02", "LOW_CPU_UTILIZATION", "Data Governance Engine Pods", "Data Governance Engine", 1800.0, OptimizationRisk.LOW, 0.92, "Reduce baseline replica count from 4 to 2 with CPU-based HPA scaling.", "Fast scale-up policy configured at 60% CPU threshold."),
            ("WST-03", "EXCESS_QUEUE_CAPACITY", "Background Task Queue Consumer Cluster", "Release Safety Service", 1450.0, OptimizationRisk.LOW, 0.90, "Scale idle queue workers to 0 during off-peak windows (22:00 - 06:00 IST).", "Queue depth trigger spawns workers when message count > 10."),
            ("WST-04", "EXCESSIVE_LOG_RETENTION", "CloudWatch / OpenSearch Log Volume", "Observability Engine", 4200.0, OptimizationRisk.MEDIUM, 0.88, "Archive raw trace payloads older than 14 days to cold S3 Glacier storage.", "On-demand rehydration script restores traces within 15 minutes."),
            ("WST-05", "OVERPROVISIONED_CACHE", "Redis Cluster Primary Node Memory (32 GB)", "ActionDispatcher", 4200.0, OptimizationRisk.LOW, 0.94, "Switch Redis instance family from cache.r6g.xlarge to cache.r6g.large (16 GB).", "Cross-zone replication snapshot restored in under 2 minutes if needed."),
        ]

        return [
            WasteFinding(
                finding_id=f[0],
                waste_type=f[1],
                resource_name=f[2],
                service_name=f[3],
                estimated_monthly_savings_inr=f[4],
                risk_tier=f[5],
                confidence_score=f[6],
                recommended_change=f[7],
                rollback_strategy=f[8],
                human_approval_required=True,
            )
            for f in findings
        ]

    def get_optimization_recommendations(self) -> list[OptimizationRecommendation]:
        """Return advisory optimization recommendations with governance and approval tracking."""
        now = datetime.now(UTC)
        recs = [
            ("OPT-9A8B7C1D", OptimizationType.RIGHTSIZE_DATABASE, "Database Storage Allocation", "Performance Service", 3200.0, OptimizationRisk.LOW, 0.95, OptimizationImpact(performance_impact="NEGLIGIBLE_LATENCY_DELTA (< 1ms)", security_impact="ZERO_SECURITY_BOUNDARY_CHANGE", resilience_impact="PRESERVES_MULTI_AZ_REDUNDANCY", rollback_complexity="LOW"), OptimizationStatus.APPROVED, "admin@recoveriq.internal", now, "Approved in FinOps review cycle. Change scheduled during maintenance window."),
            ("OPT-5E6F7A8B", OptimizationType.ADJUST_AUTOSCALING, "Data Governance Pod HPA", "Data Governance Engine", 1800.0, OptimizationRisk.LOW, 0.92, OptimizationImpact(performance_impact="NO_PERFORMANCE_IMPACT", security_impact="ZERO_SECURITY_BOUNDARY_CHANGE", resilience_impact="PRESERVES_SLA_BOUNDS", rollback_complexity="LOW"), OptimizationStatus.RECOMMENDED, None, None, None),
            ("OPT-2C3D4E5F", OptimizationType.REDUCE_LOG_RETENTION, "Observability Telemetry Log Retention", "Observability Engine", 4200.0, OptimizationRisk.MEDIUM, 0.88, OptimizationImpact(performance_impact="ZERO_RUNTIME_IMPACT", security_impact="COMPLIANCE_ARCHIVAL_PRESERVED_IN_S3", resilience_impact="NO_IMPACT_ON_ACTIVE_OBSERVABILITY", rollback_complexity="LOW"), OptimizationStatus.RECOMMENDED, None, None, None),
            ("OPT-1B2C3D4E", OptimizationType.RIGHTSIZE_CACHE, "Redis Cluster Memory Tier", "ActionDispatcher", 4200.0, OptimizationRisk.LOW, 0.94, OptimizationImpact(performance_impact="SLIGHT_CACHE_HIT_DELTA (< 0.2%)", security_impact="ZERO_SECURITY_BOUNDARY_CHANGE", resilience_impact="PRESERVES_REPLICATION_FAILOVER", rollback_complexity="LOW"), OptimizationStatus.RECOMMENDED, None, None, None),
        ]

        return [
            OptimizationRecommendation(
                recommendation_id=r[0],
                optimization_type=r[1],
                target_resource=r[2],
                affected_service=r[3],
                expected_monthly_savings_inr=r[4],
                implementation_risk=r[5],
                confidence_score=r[6],
                impact=r[7],
                status=r[8],
                created_at=now,
                approved_by=r[9],
                approved_at=r[10],
                approval_notes=r[11],
            )
            for r in recs
        ]

    def approve_optimization(
        self,
        recommendation_id: str,
        decision: str,
        notes: str,
        admin_user_id: str,
    ) -> OptimizationRecommendation:
        """Record human administrator approval or rejection of an advisory optimization recommendation."""
        now = datetime.now(UTC)
        recs = self.get_optimization_recommendations()
        target = next((r for r in recs if r.recommendation_id == recommendation_id), None)
        if not target:
            target = recs[1]

        status = (
            OptimizationStatus.APPROVED
            if decision.upper() == "APPROVE"
            else OptimizationStatus.REJECTED
        )

        audit_entry = AuditLog(
            entity_type="optimization_recommendation",
            event_type=FinOpsAuditEventType.OPTIMIZATION_APPROVED.value
            if decision.upper() == "APPROVE"
            else FinOpsAuditEventType.OPTIMIZATION_REJECTED.value,
            action=FinOpsAuditEventType.OPTIMIZATION_APPROVED.value
            if decision.upper() == "APPROVE"
            else FinOpsAuditEventType.OPTIMIZATION_REJECTED.value,
            actor_type="USER",
            actor_id=admin_user_id,
            new_state={"status": status.value, "decision": decision, "notes": notes},
            metadata_json={
                "recommendation_id": recommendation_id,
                "decision": decision,
                "notes": notes,
                "status": status.value,
            },
        )
        self.db.add(audit_entry)
        self.db.commit()

        return OptimizationRecommendation(
            recommendation_id=target.recommendation_id,
            optimization_type=target.optimization_type,
            target_resource=target.target_resource,
            affected_service=target.affected_service,
            expected_monthly_savings_inr=target.expected_monthly_savings_inr,
            implementation_risk=target.implementation_risk,
            confidence_score=target.confidence_score,
            impact=target.impact,
            status=status,
            created_at=target.created_at,
            approved_by=admin_user_id,
            approved_at=now,
            approval_notes=notes,
        )

    def get_finops_incidents(self) -> list[FinOpsIncident]:
        """Return event-sourced FinOps governance and budget incidents."""
        now = datetime.now(UTC)
        incidents_data = [
            (
                "INC-FIN-2026-0801",
                "Observability Telemetry Indexing Cost Acceleration",
                FinOpsIncidentType.COST_ANOMALY,
                FinOpsSeverity.MEDIUM,
                FinOpsIncidentStatus.ACKNOWLEDGED,
                "Observability Engine",
                1600.0,
                "sre_lead@recoveriq.internal",
                "Adjust telemetry sampling rate on test environment to reduce index volume.",
            ),
            (
                "INC-FIN-2026-0802",
                "Database Storage Allocation Headroom Waste",
                FinOpsIncidentType.RESOURCE_WASTE,
                FinOpsSeverity.LOW,
                FinOpsIncidentStatus.DETECTED,
                "Performance Service",
                3200.0,
                "finops_analyst@recoveriq.internal",
                "Review rightsizing recommendation OPT-9A8B7C1D.",
            ),
        ]

        result = []
        for i in incidents_data:
            evid_hash = hashlib.sha256(
                f"{i[0]}|{i[1]}|{i[2].value}|{i[4].value}".encode()
            ).hexdigest()
            result.append(
                FinOpsIncident(
                    incident_id=i[0],
                    title=i[1],
                    incident_type=i[2],
                    severity=i[3],
                    status=i[4],
                    affected_service=i[5],
                    detected_at=now,
                    updated_at=now,
                    cost_impact_inr=i[6],
                    assigned_operator=i[7],
                    recommended_action=i[8],
                    evidence_fingerprint=evid_hash,
                    timeline=[
                        {
                            "timestamp": now.isoformat(),
                            "action": "INCIDENT_CREATED",
                            "operator": "system:finops_engine",
                            "notes": "Automated incident generated from cost anomaly trigger.",
                        }
                    ],
                )
            )
        return result

    def process_incident_action(
        self,
        incident_id: str,
        action_type: str,
        notes: str,
        operator_id: str,
    ) -> FinOpsIncident:
        """Process operator action (ACKNOWLEDGE, ESCALATE, RESOLVE) on a FinOps incident."""
        now = datetime.now(UTC)
        incidents = self.get_finops_incidents()
        target = next((i for i in incidents if i.incident_id == incident_id), None)
        if not target:
            target = incidents[0]

        new_status = FinOpsIncidentStatus.ACKNOWLEDGED
        if action_type.upper() == "ESCALATE":
            new_status = FinOpsIncidentStatus.ESCALATED
        elif action_type.upper() == "RESOLVE":
            new_status = FinOpsIncidentStatus.RESOLVED

        audit_entry = AuditLog(
            entity_type="finops_incident",
            event_type=FinOpsAuditEventType.FINOPS_INCIDENT_UPDATED.value,
            action=FinOpsAuditEventType.FINOPS_INCIDENT_UPDATED.value,
            actor_type="USER",
            actor_id=operator_id,
            new_state={
                "incident_id": incident_id,
                "action_type": action_type,
                "new_status": new_status.value,
            },
            metadata_json={
                "incident_id": incident_id,
                "action_type": action_type,
                "new_status": new_status.value,
                "notes": notes,
            },
        )
        self.db.add(audit_entry)
        self.db.commit()

        updated_timeline = list(target.timeline)
        updated_timeline.append(
            {
                "timestamp": now.isoformat(),
                "action": f"INCIDENT_{action_type.upper()}",
                "operator": operator_id,
                "notes": notes,
            }
        )

        return FinOpsIncident(
            incident_id=target.incident_id,
            title=target.title,
            incident_type=target.incident_type,
            severity=target.severity,
            status=new_status,
            affected_service=target.affected_service,
            detected_at=target.detected_at,
            updated_at=now,
            cost_impact_inr=target.cost_impact_inr,
            assigned_operator=operator_id,
            recommended_action=target.recommended_action,
            evidence_fingerprint=target.evidence_fingerprint,
            timeline=updated_timeline,
        )

    def get_readiness_gates(self) -> list[FinOpsReadinessGate]:
        """Evaluate all 20 deterministic FinOps Readiness Gates (GATE-FIN-01 .. GATE-FIN-20)."""
        now = datetime.now(UTC)
        gate_defs = [
            (FinOpsGateId.GATE_FIN_01, "Cost Allocation Coverage", "Allocation", FinOpsGateStatus.PASS, "100% of 11 core microservices mapped", "100% Core Services", FinOpsSeverity.CRITICAL, "Verified via service cost registry.", "Ensure new services register with FinOps allocator."),
            (FinOpsGateId.GATE_FIN_02, "Cost Attribution Integrity", "Allocation", FinOpsGateStatus.PASS, "Sum of service allocations matches 100% cluster spend", "100% spend reconciled", FinOpsSeverity.CRITICAL, "Zero unallocated cost delta.", "Check unallocated infrastructure tags."),
            (FinOpsGateId.GATE_FIN_03, "Budget Configuration", "Budget", FinOpsGateStatus.PASS, "Daily, Weekly, Monthly, Quarterly budgets active", "4/4 Active Budgets", FinOpsSeverity.HIGH, "All budget periods configured.", "Set missing budget thresholds via /budgets endpoint."),
            (FinOpsGateId.GATE_FIN_04, "Budget Burn Monitoring", "Budget", FinOpsGateStatus.PASS, "Monthly burn rate 85.2% (Target < 95%)", "Burn rate < 95%", FinOpsSeverity.HIGH, "Active burn rate within safe corridor.", "Review budget alerts and optimize underutilized services."),
            (FinOpsGateId.GATE_FIN_05, "Forecast Availability", "Forecast", FinOpsGateStatus.PASS, "7D, 30D, 90D forecasts generated across 5 scenarios", "5 Active Scenarios", FinOpsSeverity.MEDIUM, "Forecast engine online.", "Re-run forecast generation pipeline."),
            (FinOpsGateId.GATE_FIN_06, "Forecast Confidence", "Forecast", FinOpsGateStatus.PASS, "Forecast confidence score 0.94", "Confidence >= 0.85", FinOpsSeverity.MEDIUM, "High regression confidence.", "Incorporate recent traffic surge history."),
            (FinOpsGateId.GATE_FIN_07, "Resource Utilization", "Efficiency", FinOpsGateStatus.PASS, "Average compute & memory utilization 72.8%", "Utilization >= 50%", FinOpsSeverity.MEDIUM, "Compute utilization healthy.", "Consolidate low-traffic pods."),
            (FinOpsGateId.GATE_FIN_08, "Capacity Efficiency", "Efficiency", FinOpsGateStatus.PASS, "Capacity headroom 27.2% within safe corridor", "Headroom 20% - 40%", FinOpsSeverity.MEDIUM, "Safe operating ceiling respected.", "Adjust HPA min/max limits."),
            (FinOpsGateId.GATE_FIN_09, "Waste Detection", "Waste", FinOpsGateStatus.PASS, "Resource waste 12.0% of total spend (Target < 15%)", "Waste < 15%", FinOpsSeverity.MEDIUM, "Waste detection radar active.", "Implement advisory rightsizing recommendations."),
            (FinOpsGateId.GATE_FIN_10, "Unit Economics", "Unit Economics", FinOpsGateStatus.PASS, "Cost per transaction: ₹0.48, Cost per case: ₹14.20", "Valid metrics calculated", FinOpsSeverity.HIGH, "All 6 unit economics metrics active.", "Validate transaction volume denominator."),
            (FinOpsGateId.GATE_FIN_11, "Service Cost Visibility", "Visibility", FinOpsGateStatus.PASS, "11/11 services have compute/db/cache/ml breakdowns", "11/11 Services", FinOpsSeverity.MEDIUM, "Granular cost attribution verified.", "Ensure tag propagation on container workloads."),
            (FinOpsGateId.GATE_FIN_12, "Database Cost Visibility", "Visibility", FinOpsGateStatus.PASS, "DB IOPS and storage cost attributed (₹27,360/mo)", "Attributed & Monitored", FinOpsSeverity.MEDIUM, "Aurora metrics synced.", "Review slow query log storage."),
            (FinOpsGateId.GATE_FIN_13, "ML Cost Visibility", "Visibility", FinOpsGateStatus.PASS, "ML compute & inference cost tracked (₹0.035/pred)", "Attributed & Monitored", FinOpsSeverity.MEDIUM, "GPU telemetry active.", "Optimize batch inference size."),
            (FinOpsGateId.GATE_FIN_14, "Webhook Cost Visibility", "Visibility", FinOpsGateStatus.PASS, "Razorpay webhook worker cost attributed (₹2.45/1k)", "Attributed & Monitored", FinOpsSeverity.MEDIUM, "Worker telemetry active.", "Evaluate webhook queue batching."),
            (FinOpsGateId.GATE_FIN_15, "Cost Anomaly Detection", "Anomaly", FinOpsGateStatus.PASS, "0 Critical unmitigated cost anomalies active", "0 Critical Anomalies", FinOpsSeverity.HIGH, "Statistical anomaly detector active.", "Acknowledge or resolve open anomalies."),
            (FinOpsGateId.GATE_FIN_16, "PII/Secret Sanitization", "Security", FinOpsGateStatus.PASS, "Zero PAN, CVV, Aadhaar, JWT secrets in FinOps telemetry", "0 Secrets / PII", FinOpsSeverity.CRITICAL, "PII scanner audit clean.", "Run emergency PII scrub if detected."),
            (FinOpsGateId.GATE_FIN_17, "Financial Isolation", "Safety", FinOpsGateStatus.PASS, "Delta RecoveryAction = 0, Delta Payment = 0 (100% Isolated)", "100% Financial Isolation", FinOpsSeverity.CRITICAL, "PolicyEngine supremacy enforced.", "Immediate security lockdown if financial mutation occurs."),
            (FinOpsGateId.GATE_FIN_18, "RBAC Enforcement", "Security", FinOpsGateStatus.PASS, "Viewer, Operator, Admin role matrix enforced", "100% Endpoints Protected", FinOpsSeverity.HIGH, "JWT authorization active.", "Review endpoint security dependencies."),
            (FinOpsGateId.GATE_FIN_19, "Optimization Governance", "Governance", FinOpsGateStatus.PASS, "100% of optimizations require human approval", "Zero Auto-Execution", FinOpsSeverity.HIGH, "Advisory governance active.", "Ensure approval audit trail intact."),
            (FinOpsGateId.GATE_FIN_20, "Report Integrity", "Audit", FinOpsGateStatus.PASS, "SHA-256 HMAC digest verifies against cryptographic key", "HMAC Verified", FinOpsSeverity.HIGH, "Cryptographic proof generated.", "Re-sign report with authoritative key."),
        ]

        return [
            FinOpsReadinessGate(
                gate_id=g[0],
                name=g[1],
                category=g[2],
                status=g[3],
                observed_value=g[4],
                threshold=g[5],
                severity=g[6],
                evidence=g[7],
                remediation=g[8],
                evaluated_at=now,
            )
            for g in gate_defs
        ]

    def get_summary(self) -> FinOpsSummary:
        """Calculate executive FinOps posture summary."""
        now = datetime.now(UTC)
        scores = self.calculate_score_breakdown()
        gates = self.get_readiness_gates()
        passed_gates = sum(1 for g in gates if g.status == FinOpsGateStatus.PASS)
        anomalies = self.get_cost_anomalies()
        incidents = self.get_finops_incidents()
        open_incidents = [i for i in incidents if i.status != FinOpsIncidentStatus.RESOLVED]

        if any(i.severity == FinOpsSeverity.CRITICAL for i in open_incidents):
            global_state = FinOpsGlobalState.EMERGENCY_COST_BREACH
        elif any(g.status == FinOpsGateStatus.FAIL for g in gates):
            global_state = FinOpsGlobalState.CRITICAL_FINOPS_FAILURE
        elif scores.composite_finops_score < 60.0:
            global_state = FinOpsGlobalState.FINOPS_DEGRADED
        elif len(anomalies) > 0 and any(a.severity == CostAnomalySeverity.HIGH for a in anomalies):
            global_state = FinOpsGlobalState.SEVERE_COST_ANOMALY
        elif len(anomalies) > 0:
            global_state = FinOpsGlobalState.OPTIMIZATION_REQUIRED
        else:
            global_state = FinOpsGlobalState.HEALTHY

        total_monthly = 123500.0
        total_daily = round(total_monthly / 30.0, 2)
        monthly_budget = 145000.0
        monthly_remaining = round(monthly_budget - total_monthly, 2)
        burn_rate = round((total_monthly / monthly_budget) * 100.0, 1)

        return FinOpsSummary(
            finops_score=scores.composite_finops_score,
            score_classification=scores.classification,
            global_finops_state=global_state,
            total_monthly_cost_inr=total_monthly,
            total_daily_cost_inr=total_daily,
            monthly_budget_inr=monthly_budget,
            monthly_budget_remaining_inr=monthly_remaining,
            monthly_burn_rate_pct=burn_rate,
            cost_growth_rate_pct=2.5,
            potential_monthly_savings_inr=13400.0,
            active_anomalies_count=len(anomalies),
            active_incidents_count=len(open_incidents),
            passed_gates_count=passed_gates,
            total_gates_count=len(gates),
            financial_isolation_verified=True,
            automatic_financial_response="DISABLED",
            evaluated_at=now,
            data_mode="demo",
            provider=self.provider_name,
            provenance={"all_metrics": "demo"},
        )

    def generate_signed_report(self) -> FinOpsReport:
        """Generate a cryptographically signed executive FinOps report."""
        now = datetime.now(UTC)
        summary = self.get_summary()
        allocation = self.get_cost_allocation()
        unit_econ = self.get_unit_economics()
        budgets = self.get_budgets()
        forecast = self.get_forecasts()
        efficiency = self.get_resource_efficiency()
        waste = self.get_waste_findings()
        anomalies = self.get_cost_anomalies()
        optimizations = self.get_optimization_recommendations()
        incidents = self.get_finops_incidents()
        gates = self.get_readiness_gates()

        report_id = f"REP-FIN-{now.strftime('%Y%m%d')}-{uuid4().hex[:8].upper()}"

        sig_payload = f"{report_id}|{summary.finops_score}|{summary.total_monthly_cost_inr}|{summary.global_finops_state.value}|{now.isoformat()}"
        sig = hmac.new(self._secret_key, sig_payload.encode(), hashlib.sha256).hexdigest()

        audit_entry = AuditLog(
            entity_type="finops_report",
            event_type=FinOpsAuditEventType.FINOPS_REPORT_GENERATED.value,
            action=FinOpsAuditEventType.FINOPS_REPORT_GENERATED.value,
            actor_type="SYSTEM",
            actor_id="system:finops_service",
            new_state={"report_id": report_id, "finops_score": summary.finops_score},
            metadata_json={
                "report_id": report_id,
                "finops_score": summary.finops_score,
                "global_state": summary.global_finops_state.value,
                "signature": sig,
            },
        )
        self.db.add(audit_entry)
        self.db.commit()

        return FinOpsReport(
            report_id=report_id,
            generated_at=now,
            finops_score=summary.finops_score,
            score_classification=summary.score_classification,
            global_finops_state=summary.global_finops_state,
            summary=summary,
            cost_allocation=allocation,
            unit_economics=unit_econ,
            budget_status=budgets,
            forecast=forecast,
            resource_efficiency=efficiency,
            waste_findings=waste,
            anomalies=anomalies,
            optimizations=optimizations,
            incidents=incidents,
            readiness_gates=gates,
            verification_signature=f"sig_fin_hmac_sha256:{sig}",
            financial_isolation_verified=True,
            data_mode="DEMO",
            provider=self.provider_name,
            metric_provenance_summary={
                "Observed": 2,
                "Derived": 8,
                "Estimated": 5,
                "Demo": 35,
                "Unavailable": 0,
            },
        )
