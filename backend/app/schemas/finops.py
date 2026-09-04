"""Pydantic schemas for Phase 10I: FinOps, Cost Intelligence, Resource Governance,

Unit Economics & Financial Efficiency Control Plane.
"""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import (
    BudgetState,
    CostAnomalySeverity,
    CostAnomalyType,
    CostCategory,
    CostSource,
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


class FinOpsScoreBreakdown(BaseModel):
    """Breakdown of the 10-factor deterministic FinOps Health Score."""

    model_config = ConfigDict(frozen=True)

    cost_allocation_score: float = Field(
        ..., ge=0.0, le=100.0, description="Cost Allocation Coverage (15%)"
    )
    budget_health_score: float = Field(
        ..., ge=0.0, le=100.0, description="Budget Health & Burn Rate (10%)"
    )
    forecast_accuracy_score: float = Field(
        ..., ge=0.0, le=100.0, description="Forecast Accuracy & Confidence (10%)"
    )
    resource_efficiency_score: float = Field(
        ..., ge=0.0, le=100.0, description="Resource Efficiency & Utilization (10%)"
    )
    unit_economics_score: float = Field(
        ..., ge=0.0, le=100.0, description="Unit Economics (10%)"
    )
    cost_anomaly_score: float = Field(
        ..., ge=0.0, le=100.0, description="Cost Anomaly Radar Health (10%)"
    )
    capacity_efficiency_score: float = Field(
        ..., ge=0.0, le=100.0, description="Capacity Headroom & Safe Bounds (10%)"
    )
    waste_detection_score: float = Field(
        ..., ge=0.0, le=100.0, description="Resource Waste Elimination (10%)"
    )
    tagging_governance_score: float = Field(
        ..., ge=0.0, le=100.0, description="Tagging & Attribution Governance (5%)"
    )
    optimization_readiness_score: float = Field(
        ...,
        ge=0.0,
        le=100.0,
        description="Optimization Readiness & Actionability (10%)",
    )
    composite_finops_score: float = Field(
        ..., ge=0.0, le=100.0, description="Deterministic 10-Factor Composite Score"
    )
    classification: FinOpsHealth = Field(..., description="Classification category")
    component_sources: dict[str, str] = Field(
        default_factory=dict,
        description="Data provenance source for each score component ('runtime' | 'demo' | 'derived')",
    )


class ServiceCostMetric(BaseModel):
    """Cost attribution metric for a single core microservice."""

    model_config = ConfigDict(frozen=True)

    service_name: str = Field(..., description="Name of the core microservice")
    monthly_cost_inr: float = Field(
        ..., ge=0.0, description="Estimated monthly cost in INR"
    )
    cost_share_pct: float = Field(
        ..., ge=0.0, le=100.0, description="Percentage of total infrastructure cost"
    )
    rpm: float = Field(..., ge=0.0, description="Requests per minute")
    cost_per_1k_requests_inr: float = Field(
        ..., ge=0.0, description="Cost per 1,000 requests in INR"
    )
    cpu_efficiency_pct: float = Field(
        ..., ge=0.0, le=100.0, description="CPU efficiency percentage"
    )
    memory_efficiency_pct: float = Field(
        ..., ge=0.0, le=100.0, description="Memory efficiency percentage"
    )
    compute_cost_inr: float = Field(
        ..., ge=0.0, description="Compute allocation in INR"
    )
    database_cost_inr: float = Field(
        ..., ge=0.0, description="Database allocation in INR"
    )
    cache_cost_inr: float = Field(..., ge=0.0, description="Cache allocation in INR")
    network_cost_inr: float = Field(
        ..., ge=0.0, description="Network egress/ingress allocation in INR"
    )
    ml_cost_inr: float = Field(
        ..., ge=0.0, description="ML inference/training allocation in INR"
    )
    efficiency_status: ResourceEfficiencyState = Field(
        ..., description="Current efficiency state"
    )
    source: str = Field(
        default="demo",
        description="Data provenance: 'runtime' | 'demo' | 'derived' | 'estimated' | 'unavailable'",
    )
    provider: str = Field(
        default="DemoFinOpsDataProvider",
        description="Data provider identifier",
    )
    confidence: float = Field(
        default=1.0,
        description="Confidence score for this metric",
    )


class CostCategoryBreakdown(BaseModel):
    """Cost allocation for a single infrastructure category."""

    model_config = ConfigDict(frozen=True)

    category: CostCategory = Field(..., description="Infrastructure category")
    hourly_cost_inr: float = Field(..., ge=0.0, description="Hourly cost in INR")
    daily_cost_inr: float = Field(..., ge=0.0, description="Daily cost in INR")
    monthly_cost_inr: float = Field(..., ge=0.0, description="Monthly cost in INR")
    cost_share_pct: float = Field(
        ..., ge=0.0, le=100.0, description="Percentage share of total spend"
    )
    trend_pct: float = Field(
        ..., description="Cost growth trend percentage compared to previous period"
    )
    source: CostSource = Field(..., description="Origin of telemetry")
    provider: str = Field(
        default="DemoFinOpsDataProvider",
        description="Provider identifier",
    )
    disclaimer: str | None = Field(
        default=None,
        description="Notice if unmetered or estimated",
    )


class CostAllocation(BaseModel):
    """Complete infrastructure cost allocation breakdown."""

    model_config = ConfigDict(frozen=True)

    total_monthly_cost_inr: float = Field(
        ..., ge=0.0, description="Total monthly infrastructure cost in INR"
    )
    total_daily_cost_inr: float = Field(
        ..., ge=0.0, description="Total daily infrastructure cost in INR"
    )
    total_hourly_cost_inr: float = Field(
        ..., ge=0.0, description="Total hourly infrastructure cost in INR"
    )
    services: list[ServiceCostMetric] = Field(
        ..., description="Cost metrics for all 11 core services"
    )
    categories: list[CostCategoryBreakdown] = Field(
        ..., description="Cost allocation across all 10 infrastructure categories"
    )
    evaluated_at: datetime = Field(..., description="Timestamp of evaluation")
    data_mode: str = Field(
        default="demo",
        description="Data mode: 'runtime' | 'demo'",
    )
    provider: str = Field(
        default="DemoFinOpsDataProvider",
        description="Data provider identifier",
    )


class BudgetThreshold(BaseModel):
    """Status of a specific budget threshold notification tier."""

    model_config = ConfigDict(frozen=True)

    threshold_pct: float = Field(
        ...,
        ge=0.0,
        le=100.0,
        description="Threshold percentage (50%, 70%, 85%, 95%, 100%)",
    )
    threshold_amount_inr: float = Field(
        ..., ge=0.0, description="Threshold limit in INR"
    )
    breached: bool = Field(..., description="Whether threshold is currently breached")
    breached_at: datetime | None = Field(
        None, description="Timestamp when threshold was breached"
    )


class BudgetStatus(BaseModel):
    """Governance status of an active budget tier."""

    model_config = ConfigDict(frozen=True)

    period: str = Field(
        ..., description="Budget period: DAILY, WEEKLY, MONTHLY, QUARTERLY"
    )
    budget_amount_inr: float = Field(..., ge=0.0, description="Allocated budget in INR")
    actual_amount_inr: float = Field(
        ..., ge=0.0, description="Actual observed/estimated spend in INR"
    )
    committed_amount_inr: float = Field(
        ..., ge=0.0, description="Committed infrastructure reservations in INR"
    )
    forecast_amount_inr: float = Field(
        ..., ge=0.0, description="Projected period spend in INR"
    )
    remaining_amount_inr: float = Field(..., description="Remaining budget in INR")
    burn_rate_pct: float = Field(..., ge=0.0, description="Percentage of budget burned")
    projected_overrun_inr: float = Field(
        ..., ge=0.0, description="Projected overrun in INR if any"
    )
    state: BudgetState = Field(..., description="Budget governance state")
    thresholds: list[BudgetThreshold] = Field(
        ..., description="Configured budget thresholds"
    )


class BudgetConfigRequest(BaseModel):
    """Payload to configure or update a budget limit."""

    period: str = Field(
        ..., description="Budget period: DAILY, WEEKLY, MONTHLY, QUARTERLY"
    )
    budget_amount_inr: float = Field(..., ge=100.0, description="Budget amount in INR")
    alert_thresholds: list[float] = Field(
        default_factory=lambda: [50.0, 70.0, 85.0, 95.0, 100.0]
    )
    notes: str | None = Field(
        None, max_length=500, description="Audit justification for budget modification"
    )


class ForecastScenario(BaseModel):
    """Cost projection under a specific operational scenario."""

    model_config = ConfigDict(frozen=True)

    scenario_name: str = Field(
        ..., description="BASELINE, GROWTH, HIGH_GROWTH, TRAFFIC_SURGE, STRESS"
    )
    growth_rate_pct: float = Field(..., description="Assumed traffic growth rate")
    forecast_7d_inr: float = Field(
        ..., ge=0.0, description="7-day projected cost in INR"
    )
    forecast_30d_inr: float = Field(
        ..., ge=0.0, description="30-day projected cost in INR"
    )
    forecast_90d_inr: float = Field(
        ..., ge=0.0, description="90-day projected cost in INR"
    )
    confidence_score: float = Field(
        ..., ge=0.0, le=1.0, description="Statistical confidence score"
    )
    budget_variance_pct: float = Field(
        ..., description="Projected variance against monthly budget"
    )
    assumptions: list[str] = Field(..., description="Key mathematical assumptions")


class CostForecast(BaseModel):
    """Complete cost forecast intelligence output."""

    model_config = ConfigDict(frozen=True)

    forecast_id: str = Field(..., description="Deterministic forecast identifier")
    generated_at: datetime = Field(..., description="Timestamp of generation")
    baseline_monthly_cost_inr: float = Field(
        ..., ge=0.0, description="Current baseline monthly spend"
    )
    forecast_state: ForecastState = Field(..., description="Overall trajectory state")
    scenarios: list[ForecastScenario] = Field(
        ..., description="Projections across all 5 operational scenarios"
    )


class ForecastGenerateRequest(BaseModel):
    """Request payload to generate on-demand cost forecasts."""

    horizon_days: int = Field(
        default=30, ge=7, le=90, description="Forecast horizon in days"
    )
    traffic_multiplier: float = Field(
        default=1.0, ge=0.5, le=10.0, description="Simulated traffic load multiplier"
    )
    include_stress_scenario: bool = Field(
        default=True, description="Whether to include stress testing scenario"
    )


class CostAnomaly(BaseModel):
    """Detected infrastructure cost anomaly."""

    model_config = ConfigDict(frozen=True)

    anomaly_id: str = Field(
        ..., description="Deterministic anomaly identifier: ANOM-<SHA256>"
    )
    anomaly_type: CostAnomalyType = Field(..., description="Type of cost anomaly")
    severity: CostAnomalySeverity = Field(..., description="Severity tier")
    affected_service: str = Field(..., description="Service primarily responsible")
    affected_category: CostCategory = Field(..., description="Cost category")
    detected_at: datetime = Field(..., description="Timestamp of detection")
    baseline_cost_inr: float = Field(..., ge=0.0, description="Expected baseline cost")
    observed_cost_inr: float = Field(
        ..., ge=0.0, description="Observed cost during spike"
    )
    deviation_pct: float = Field(..., description="Percentage deviation above baseline")
    confidence_score: float = Field(
        ..., ge=0.0, le=1.0, description="Confidence in anomaly classification"
    )
    evidence_hash: str = Field(
        ..., description="Cryptographic SHA-256 evidence fingerprint"
    )
    recommended_action: str = Field(
        ..., description="Advisory remediation recommendation"
    )


class ResourceUtilization(BaseModel):
    """Utilization and capacity metrics for a specific infrastructure resource."""

    model_config = ConfigDict(frozen=True)

    resource_type: ResourceType = Field(..., description="Infrastructure resource type")
    allocated_units: str = Field(
        ..., description="Allocated capacity description (e.g. 16 vCPU, 64 GB)"
    )
    utilization_pct: float = Field(
        ..., ge=0.0, le=100.0, description="Current average utilization percentage"
    )
    safe_capacity_pct: float = Field(
        ..., ge=0.0, le=100.0, description="Safe operating ceiling (e.g. 80%)"
    )
    headroom_pct: float = Field(..., description="Available capacity headroom")
    efficiency_pct: float = Field(
        ..., ge=0.0, le=100.0, description="Calculated efficiency percentage"
    )
    waste_pct: float = Field(
        ..., ge=0.0, le=100.0, description="Estimated unutilized waste percentage"
    )
    state: ResourceEfficiencyState = Field(..., description="Efficiency state")
    source: str = Field(
        default="demo",
        description="Data provenance: 'runtime' | 'demo' | 'derived' | 'estimated' | 'unavailable'",
    )
    provider: str = Field(
        default="DemoFinOpsDataProvider",
        description="Data provider identifier",
    )
    confidence: float = Field(
        default=1.0,
        description="Confidence score for this metric",
    )


class ResourceEfficiency(BaseModel):
    """Complete infrastructure resource efficiency report."""

    model_config = ConfigDict(frozen=True)

    overall_efficiency_pct: float = Field(
        ..., ge=0.0, le=100.0, description="Composite resource efficiency percentage"
    )
    total_waste_cost_inr: float = Field(
        ..., ge=0.0, description="Estimated monthly unutilized cost in INR"
    )
    resources: list[ResourceUtilization] = Field(
        ..., description="Utilization breakdowns per resource type"
    )
    evaluated_at: datetime = Field(..., description="Timestamp of evaluation")
    data_mode: str = Field(
        default="demo",
        description="Data mode: 'runtime' | 'demo'",
    )
    provider: str = Field(
        default="DemoFinOpsDataProvider",
        description="Data provider identifier",
    )


class WasteFinding(BaseModel):
    """Identified infrastructure overprovisioning or waste item."""

    model_config = ConfigDict(frozen=True)

    finding_id: str = Field(..., description="Deterministic finding identifier")
    waste_type: str = Field(
        ..., description="Category of waste (e.g. IDLE_COMPUTE, OVERSIZED_DATABASE)"
    )
    resource_name: str = Field(..., description="Identifier of the resource")
    service_name: str = Field(..., description="Owning microservice")
    estimated_monthly_savings_inr: float = Field(
        ..., ge=0.0, description="Potential monthly savings in INR"
    )
    risk_tier: OptimizationRisk = Field(
        ..., description="Risk of rightsizing this resource"
    )
    confidence_score: float = Field(
        ..., ge=0.0, le=1.0, description="Confidence in finding"
    )
    recommended_change: str = Field(..., description="Recommended configuration change")
    rollback_strategy: str = Field(
        ..., description="Rollback plan if rightsizing impacts SLA"
    )
    human_approval_required: bool = Field(
        default=True, description="Strictly true for all optimizations"
    )


class CostPerTransaction(BaseModel):
    """Unit economics for financial transactions."""

    model_config = ConfigDict(frozen=True)

    cost_per_successful_txn_inr: float = Field(
        ..., ge=0.0, description="Cost per successful payment transaction in INR"
    )
    cost_per_attempted_txn_inr: float = Field(
        ..., ge=0.0, description="Cost per attempted transaction in INR"
    )
    monthly_transaction_volume: int = Field(
        ..., ge=0, description="Monthly transaction volume"
    )
    total_transaction_infrastructure_cost_inr: float = Field(
        ..., ge=0.0, description="Attributed transaction infrastructure cost"
    )


class CostPerRecoveryCase(BaseModel):
    """Unit economics for debt and revenue recovery cases."""

    model_config = ConfigDict(frozen=True)

    cost_per_case_inr: float = Field(
        ..., ge=0.0, description="Infrastructure cost per managed recovery case in INR"
    )
    cost_per_resolved_case_inr: float = Field(
        ..., ge=0.0, description="Infrastructure cost per resolved case in INR"
    )
    monthly_case_volume: int = Field(
        ..., ge=0, description="Monthly active recovery case volume"
    )
    total_case_infrastructure_cost_inr: float = Field(
        ..., ge=0.0, description="Attributed case infrastructure cost"
    )


class MLInferenceCost(BaseModel):
    """Unit economics for ML model predictions and training."""

    model_config = ConfigDict(frozen=True)

    cost_per_prediction_inr: float = Field(
        ...,
        ge=0.0,
        description="Compute cost per ML recovery strategy prediction in INR",
    )
    cost_per_training_run_inr: float = Field(
        ..., ge=0.0, description="Cost per offline model training run in INR"
    )
    monthly_prediction_volume: int = Field(
        ..., ge=0, description="Monthly prediction count"
    )
    total_ml_infrastructure_cost_inr: float = Field(
        ..., ge=0.0, description="Total ML infrastructure cost"
    )


class DatabaseCost(BaseModel):
    """Unit economics and cost breakdown for database operations."""

    model_config = ConfigDict(frozen=True)

    cost_per_100k_queries_inr: float = Field(
        ..., ge=0.0, description="Cost per 100,000 DB queries in INR"
    )
    storage_cost_per_gb_inr: float = Field(
        ..., ge=0.0, description="Storage cost per GB in INR"
    )
    iops_cost_inr: float = Field(..., ge=0.0, description="Allocated IOPS cost in INR")
    monthly_database_cost_inr: float = Field(
        ..., ge=0.0, description="Total database cost in INR"
    )


class CacheCost(BaseModel):
    """Unit economics for Redis cache operations."""

    model_config = ConfigDict(frozen=True)

    cost_per_1m_ops_inr: float = Field(
        ..., ge=0.0, description="Cost per 1,000,000 Redis operations in INR"
    )
    hit_rate_pct: float = Field(
        ..., ge=0.0, le=100.0, description="Cache hit rate percentage"
    )
    monthly_cache_cost_inr: float = Field(
        ..., ge=0.0, description="Total Redis cache cost in INR"
    )


class WebhookCost(BaseModel):
    """Unit economics for Razorpay webhook ingestion and processing."""

    model_config = ConfigDict(frozen=True)

    cost_per_1k_webhooks_inr: float = Field(
        ..., ge=0.0, description="Cost per 1,000 Razorpay webhooks in INR"
    )
    monthly_webhook_volume: int = Field(..., ge=0, description="Monthly webhook volume")
    total_webhook_infrastructure_cost_inr: float = Field(
        ..., ge=0.0, description="Total webhook infrastructure cost"
    )


class UnitEconomics(BaseModel):
    """Complete unit economics and financial efficiency model."""

    model_config = ConfigDict(frozen=True)

    cost_per_transaction: CostPerTransaction = Field(
        ..., description="Transaction unit economics"
    )
    cost_per_recovery_case: CostPerRecoveryCase = Field(
        ..., description="Recovery case unit economics"
    )
    ml_inference_cost: MLInferenceCost = Field(
        ..., description="ML inference cost breakdown"
    )
    database_cost: DatabaseCost = Field(..., description="Database cost breakdown")
    cache_cost: CacheCost = Field(..., description="Cache cost breakdown")
    webhook_cost: WebhookCost = Field(..., description="Webhook cost breakdown")
    cost_per_1k_requests_inr: float = Field(
        ..., ge=0.0, description="Average infrastructure cost per 1,000 API requests"
    )
    recovery_intelligence_value_efficiency: float = Field(
        ...,
        ge=0.0,
        description="Engineering analytics proxy: Recovered Operational Value Proxy / Infrastructure Cost (Advisory Only)",
    )
    evaluated_at: datetime = Field(..., description="Timestamp of evaluation")
    data_mode: str = Field(
        default="demo",
        description="Data mode: 'runtime' | 'demo'",
    )
    provider: str = Field(
        default="DemoFinOpsDataProvider",
        description="Data provider identifier",
    )
    provenance: dict[str, str] = Field(
        default_factory=dict,
        description="Provenance breakdown per sub-metric",
    )


class OptimizationRiskAssessment(BaseModel):
    """Detailed risk assessment for an advisory optimization recommendation."""

    model_config = ConfigDict(frozen=True)

    risk_tier: OptimizationRisk = Field(
        ..., description="Overall risk level (LOW, MEDIUM, HIGH, CRITICAL)"
    )
    confidence_score: float = Field(
        ..., ge=0.0, le=1.0, description="Statistical confidence score"
    )
    rollback_complexity: str = Field(
        ..., description="Rollback complexity (LOW, MEDIUM, HIGH)"
    )
    sla_impact_risk: str = Field(
        ..., description="Risk of violating service level agreements"
    )


class OptimizationImpact(BaseModel):
    """Cross-domain impact assessment for an advisory optimization."""

    model_config = ConfigDict(frozen=True)

    performance_impact: str = Field(
        ...,
        description="Expected impact on latency and throughput (e.g. NEGLIGIBLE_LATENCY_DELTA)",
    )
    security_impact: str = Field(
        ...,
        description="Expected impact on zero-trust posture (e.g. ZERO_SECURITY_BOUNDARY_CHANGE)",
    )
    resilience_impact: str = Field(
        ...,
        description="Expected impact on redundancy and SLA (e.g. PRESERVES_HA_REDUNDANCY)",
    )
    rollback_complexity: str = Field(
        ..., description="Complexity of reverting change (LOW, MEDIUM, HIGH)"
    )


class OptimizationRecommendation(BaseModel):
    """Advisory resource optimization recommendation (strictly human-approved)."""

    model_config = ConfigDict(frozen=True)

    recommendation_id: str = Field(
        ..., description="Deterministic identifier: OPT-<SHA256>"
    )
    optimization_type: OptimizationType = Field(..., description="Type of optimization")
    target_resource: str = Field(..., description="Resource to optimize")
    affected_service: str = Field(..., description="Owning microservice")
    expected_monthly_savings_inr: float = Field(
        ..., ge=0.0, description="Estimated monthly savings in INR"
    )
    implementation_risk: OptimizationRisk = Field(..., description="Risk tier")
    confidence_score: float = Field(
        ..., ge=0.0, le=1.0, description="Statistical confidence score"
    )
    impact: OptimizationImpact = Field(
        ..., description="Cross-domain impact assessment"
    )
    status: OptimizationStatus = Field(..., description="Current governance status")
    created_at: datetime = Field(..., description="Timestamp of generation")
    approved_by: str | None = Field(
        None, description="Admin user who approved recommendation"
    )
    approved_at: datetime | None = Field(None, description="Timestamp of approval")
    approval_notes: str | None = Field(
        None, description="Justification recorded during approval"
    )


class OptimizationApprovalRequest(BaseModel):
    """Payload to approve or reject an optimization recommendation."""

    decision: str = Field(
        ..., pattern="^(APPROVE|REJECT)$", description="Decision: APPROVE or REJECT"
    )
    notes: str = Field(
        ..., min_length=5, max_length=500, description="Mandatory audit justification"
    )


class FinOpsIncident(BaseModel):
    """FinOps cost governance or budget breach incident."""

    model_config = ConfigDict(frozen=True)

    incident_id: str = Field(
        ..., description="Deterministic incident identifier: INC-FIN-<ID>"
    )
    title: str = Field(..., description="Incident summary title")
    incident_type: FinOpsIncidentType = Field(
        ..., description="Incident classification"
    )
    severity: FinOpsSeverity = Field(..., description="Severity tier")
    status: FinOpsIncidentStatus = Field(..., description="Operational status")
    affected_service: str = Field(..., description="Service primarily affected")
    detected_at: datetime = Field(..., description="Detection timestamp")
    updated_at: datetime = Field(..., description="Last updated timestamp")
    cost_impact_inr: float = Field(
        ..., ge=0.0, description="Calculated or projected cost impact in INR"
    )
    assigned_operator: str = Field(
        ..., description="Assigned FinOps operator or SRE lead"
    )
    recommended_action: str = Field(..., description="Remediation recommendation")
    evidence_fingerprint: str = Field(
        ..., description="Cryptographic SHA-256 evidence fingerprint"
    )
    timeline: list[dict[str, Any]] = Field(
        default_factory=list, description="Chronological audit timeline"
    )


class FinOpsIncidentActionRequest(BaseModel):
    """Payload for operator actions on a FinOps incident."""

    notes: str = Field(
        ...,
        min_length=5,
        max_length=500,
        description="Operator action notes for audit log",
    )


class FinOpsReadinessGate(BaseModel):
    """One of the 20 deterministic FinOps Readiness Gates."""

    model_config = ConfigDict(frozen=True)

    gate_id: FinOpsGateId = Field(
        ..., description="Gate identifier: GATE-FIN-01 .. GATE-FIN-20"
    )
    name: str = Field(..., description="Human-readable gate name")
    category: str = Field(
        ..., description="Category (Allocation, Budget, Forecast, Efficiency, etc.)"
    )
    status: FinOpsGateStatus = Field(..., description="Pass, Warn, Fail, Blocked")
    observed_value: str = Field(..., description="Measured telemetry value")
    threshold: str = Field(..., description="Required threshold criteria")
    severity: FinOpsSeverity = Field(..., description="Severity if gate fails")
    evidence: str = Field(..., description="Evidence verification details")
    remediation: str = Field(
        ..., description="Guidance to remediate if warning/failure"
    )
    evaluated_at: datetime = Field(..., description="Timestamp of evaluation")


class FinOpsSummary(BaseModel):
    """Executive summary of the FinOps Control Plane."""

    model_config = ConfigDict(frozen=True)

    finops_score: float = Field(
        ..., ge=0.0, le=100.0, description="Deterministic FinOps Health Score"
    )
    score_classification: FinOpsHealth = Field(..., description="Health classification")
    global_finops_state: FinOpsGlobalState = Field(
        ..., description="Global state hierarchy"
    )
    total_monthly_cost_inr: float = Field(
        ..., ge=0.0, description="Total monthly spend in INR"
    )
    total_daily_cost_inr: float = Field(
        ..., ge=0.0, description="Total daily spend in INR"
    )
    monthly_budget_inr: float = Field(
        ..., ge=0.0, description="Monthly budget limit in INR"
    )
    monthly_budget_remaining_inr: float = Field(
        ..., description="Remaining monthly budget in INR"
    )
    monthly_burn_rate_pct: float = Field(
        ..., ge=0.0, description="Percentage of monthly budget burned"
    )
    cost_growth_rate_pct: float = Field(
        ..., description="30-day cost growth percentage"
    )
    potential_monthly_savings_inr: float = Field(
        ..., ge=0.0, description="Identified optimization savings in INR"
    )
    active_anomalies_count: int = Field(
        ..., ge=0, description="Number of active cost anomalies"
    )
    active_incidents_count: int = Field(
        ..., ge=0, description="Number of open FinOps incidents"
    )
    passed_gates_count: int = Field(
        ..., ge=0, le=20, description="Number of passing readiness gates"
    )
    total_gates_count: int = Field(
        default=20, description="Total readiness gates count (20)"
    )
    financial_isolation_verified: bool = Field(
        default=True, description="Always true: delta recovery actions = 0"
    )
    automatic_financial_response: str = Field(
        default="DISABLED", description="Always DISABLED: advisory only"
    )
    evaluated_at: datetime = Field(..., description="Evaluation timestamp")
    data_mode: str = Field(
        default="demo",
        description="Data mode: 'runtime' | 'demo'",
    )
    provider: str = Field(
        default="DemoFinOpsDataProvider",
        description="Data provider identifier",
    )
    provenance: dict[str, str] = Field(
        default_factory=dict,
        description="Metric provenance map",
    )
    disclaimer: str = Field(
        default="RecoverIQ FinOps Control Plane provides observational engineering cost analytics and advisory optimization recommendations. PolicyEngine remains the sole authoritative financial recovery gatekeeper.",
        description="Mandatory advisory disclaimer",
    )


class FinOpsReport(BaseModel):
    """Cryptographically signed executive FinOps report."""

    model_config = ConfigDict(frozen=True)

    report_id: str = Field(
        ..., description="Deterministic report identifier: REP-FIN-<ID>"
    )
    generated_at: datetime = Field(..., description="Generation timestamp")
    finops_score: float = Field(
        ..., ge=0.0, le=100.0, description="FinOps Health Score"
    )
    score_classification: FinOpsHealth = Field(..., description="Score classification")
    global_finops_state: FinOpsGlobalState = Field(..., description="Global state")
    summary: FinOpsSummary = Field(..., description="Executive summary snapshot")
    cost_allocation: CostAllocation = Field(
        ..., description="Full cost allocation matrix"
    )
    unit_economics: UnitEconomics = Field(..., description="Unit economics breakdown")
    budget_status: list[BudgetStatus] = Field(..., description="Active budget statuses")
    forecast: CostForecast = Field(..., description="Cost forecast intelligence")
    resource_efficiency: ResourceEfficiency = Field(
        ..., description="Resource efficiency report"
    )
    waste_findings: list[WasteFinding] = Field(
        ..., description="Resource waste findings"
    )
    anomalies: list[CostAnomaly] = Field(
        ..., description="Active and historical cost anomalies"
    )
    optimizations: list[OptimizationRecommendation] = Field(
        ..., description="Optimization recommendations"
    )
    incidents: list[FinOpsIncident] = Field(..., description="FinOps incidents")
    readiness_gates: list[FinOpsReadinessGate] = Field(
        ..., description="20 FinOps Readiness Gates"
    )
    verification_signature: str = Field(
        ..., description="SHA-256 HMAC cryptographic signature"
    )
    financial_isolation_verified: bool = Field(
        default=True, description="Strictly true"
    )
    data_mode: str = Field(
        default="DEMO",
        description="DATA MODE: RUNTIME / DEMO",
    )
    provider: str = Field(
        default="DemoFinOpsDataProvider",
        description="Data provider identifier",
    )
    metric_provenance_summary: dict[str, int] = Field(
        default_factory=dict,
        description="Counts of Observed, Derived, Estimated, Demo, Unavailable metrics",
    )


class FinOpsSnapshot(BaseModel):
    """Point-in-time state snapshot persisted into AuditLog."""

    model_config = ConfigDict(frozen=True)

    snapshot_id: str = Field(..., description="Unique snapshot identifier")
    timestamp: datetime = Field(..., description="Snapshot timestamp")
    finops_score: float = Field(..., ge=0.0, le=100.0)
    total_monthly_cost_inr: float = Field(..., ge=0.0)
    active_anomalies: int = Field(..., ge=0)
    open_incidents: int = Field(..., ge=0)
    evidence_hash: str = Field(..., description="SHA-256 state digest")
