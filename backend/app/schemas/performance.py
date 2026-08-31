"""Pydantic schemas for Phase 10F: Fintech Performance Engineering, Scalability, Capacity Planning & High-Load Resilience."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from app.models.enums import (
    BottleneckType,
    CachePerformanceState,
    CapacityState,
    DatabasePerformanceState,
    LoadTestScenario,
    LoadTestStatus,
    PerformanceGlobalState,
    PerformanceHealth,
    PerformanceIncidentStatus,
    PerformanceIncidentType,
    PerformanceSeverity,
    QueueState,
    ScalingRecommendation,
)


class PerformanceScoreBreakdown(BaseModel):
    """Component score breakdown for overall 0-100 performance health."""

    latency_score: float = Field(
        ..., ge=0.0, le=100.0, description="P50/P95/P99 latency score (15%)"
    )
    throughput_score: float = Field(
        ..., ge=0.0, le=100.0, description="Throughput & RPM score (15%)"
    )
    database_score: float = Field(
        ..., ge=0.0, le=100.0, description="Database connection & latency score (15%)"
    )
    queue_score: float = Field(
        ..., ge=0.0, le=100.0, description="Queue drain & backpressure score (10%)"
    )
    cache_score: float = Field(
        ...,
        ge=0.0,
        le=100.0,
        description="Redis cache hit-ratio & efficiency score (10%)",
    )
    ml_score: float = Field(
        ..., ge=0.0, le=100.0, description="ML inference latency & queue score (10%)"
    )
    webhook_score: float = Field(
        ..., ge=0.0, le=100.0, description="Webhook ingestion & burst score (10%)"
    )
    cpu_score: float = Field(
        ..., ge=0.0, le=100.0, description="CPU headroom score (5%)"
    )
    memory_score: float = Field(
        ..., ge=0.0, le=100.0, description="Memory headroom score (5%)"
    )
    capacity_score: float = Field(
        ..., ge=0.0, le=100.0, description="Safe capacity headroom score (5%)"
    )


class PerformanceSummary(BaseModel):
    """Executive summary of RecoverIQ fintech performance and system headroom."""

    score: float = Field(
        ..., ge=0.0, le=100.0, description="Overall deterministic performance score"
    )
    classification: PerformanceHealth = Field(
        ..., description="Categorical health grade"
    )
    global_state: PerformanceGlobalState = Field(
        ..., description="Highest-priority global performance state"
    )
    current_rpm: float = Field(
        ..., ge=0.0, description="Current aggregate requests per minute"
    )
    peak_rpm: float = Field(..., ge=0.0, description="Historical peak aggregate RPM")
    safe_rpm: float = Field(
        ..., ge=0.0, description="Maximum safe operating RPM before degradation"
    )
    current_latency_ms: float = Field(
        ..., ge=0.0, description="Current aggregate P50 latency"
    )
    p95_latency_ms: float = Field(
        ..., ge=0.0, description="Current aggregate P95 latency"
    )
    p99_latency_ms: float = Field(
        ..., ge=0.0, description="Current aggregate P99 latency"
    )
    error_rate: float = Field(
        ..., ge=0.0, le=1.0, description="Current aggregate error rate [0, 1]"
    )
    capacity_utilization_pct: float = Field(
        ..., ge=0.0, le=100.0, description="Percentage of safe capacity in use"
    )
    headroom_pct: float = Field(
        ...,
        ge=0.0,
        le=100.0,
        description="Remaining safe operating headroom percentage",
    )
    active_bottlenecks_count: int = Field(
        ..., ge=0, description="Count of identified performance bottlenecks"
    )
    scaling_recommendation: ScalingRecommendation = Field(
        ..., description="Advisory scaling recommendation"
    )
    active_incidents_count: int = Field(
        ..., ge=0, description="Active performance incidents count"
    )
    score_breakdown: PerformanceScoreBreakdown = Field(
        ..., description="10-component score breakdown"
    )
    evaluated_at: datetime = Field(..., description="Evaluation timestamp")
    disclaimer: str = Field(
        ..., description="Non-mutating observational engineering control disclaimer"
    )


class PerformanceServiceMetric(BaseModel):
    """Telemetry and performance metrics for an individual RecoverIQ service."""

    service_name: str = Field(
        ..., description="Name of the service (e.g. PolicyEngine, Recovery Service)"
    )
    rpm: float = Field(..., ge=0.0, description="Requests per minute processed")
    throughput_tps: float = Field(..., ge=0.0, description="Transactions per second")
    p50_latency_ms: float = Field(
        ..., ge=0.0, description="Median latency in milliseconds"
    )
    p95_latency_ms: float = Field(
        ..., ge=0.0, description="95th percentile latency in milliseconds"
    )
    p99_latency_ms: float = Field(
        ..., ge=0.0, description="99th percentile latency in milliseconds"
    )
    error_rate_pct: float = Field(..., ge=0.0, le=100.0, description="Error percentage")
    timeout_rate_pct: float = Field(
        ..., ge=0.0, le=100.0, description="Timeout percentage"
    )
    cpu_utilization_pct: float = Field(
        ..., ge=0.0, le=100.0, description="CPU usage percentage"
    )
    memory_utilization_pct: float = Field(
        ..., ge=0.0, le=100.0, description="Memory usage percentage"
    )
    queue_depth: int = Field(..., ge=0, description="Pending queue backlog depth")
    saturation_pct: float = Field(
        ..., ge=0.0, le=100.0, description="Service saturation percentage"
    )
    concurrency: int = Field(
        ..., ge=0, description="Active concurrent worker threads/tasks"
    )
    capacity_utilization_pct: float = Field(
        ..., ge=0.0, le=100.0, description="Capacity utilized percentage"
    )
    remaining_headroom_pct: float = Field(
        ..., ge=0.0, le=100.0, description="Remaining headroom percentage"
    )
    status: str = Field(
        ..., description="Operational status: HEALTHY, WARNING, DEGRADED, CRITICAL"
    )


class CapacityAssessment(BaseModel):
    """Capacity headroom and safe operating limits evaluation."""

    current_capacity_rpm: float = Field(
        ..., ge=0.0, description="Current operating RPM"
    )
    peak_capacity_rpm: float = Field(..., ge=0.0, description="Demonstrated peak RPM")
    safe_capacity_rpm: float = Field(
        ..., ge=0.0, description="Engineered safe operating limit RPM"
    )
    theoretical_capacity_rpm: float = Field(
        ..., ge=0.0, description="Theoretical maximum capacity RPM"
    )
    current_utilization_pct: float = Field(
        ..., ge=0.0, le=100.0, description="Current utilization vs safe limit"
    )
    peak_utilization_pct: float = Field(
        ..., ge=0.0, le=100.0, description="Peak utilization vs safe limit"
    )
    headroom_pct: float = Field(
        ...,
        ge=0.0,
        le=100.0,
        description="100 * (1 - CurrentUtilization / SafeCapacity)",
    )
    capacity_state: CapacityState = Field(..., description="Categorical capacity state")
    scaling_recommendation: ScalingRecommendation = Field(
        ..., description="Advisory scaling recommendation"
    )
    evaluated_at: datetime = Field(..., description="Evaluation timestamp")


class TrafficProjectionScenario(BaseModel):
    """Projected system metrics under synthetic traffic multiplication."""

    multiplier: str = Field(..., description="Traffic multiplier: 1x, 2x, 5x, 10x, 20x")
    expected_rpm: float = Field(
        ..., ge=0.0, description="Projected requests per minute"
    )
    expected_latency_ms: float = Field(
        ..., ge=0.0, description="Projected P95 latency in ms"
    )
    expected_cpu_pct: float = Field(
        ..., ge=0.0, le=100.0, description="Projected CPU usage percentage"
    )
    expected_memory_pct: float = Field(
        ..., ge=0.0, le=100.0, description="Projected memory usage percentage"
    )
    expected_db_load_pct: float = Field(
        ..., ge=0.0, le=100.0, description="Projected database pool utilization"
    )
    expected_queue_depth: int = Field(..., ge=0, description="Projected queue depth")
    expected_ml_load_pct: float = Field(
        ..., ge=0.0, le=100.0, description="Projected ML inference load"
    )
    expected_cache_load_pct: float = Field(
        ..., ge=0.0, le=100.0, description="Projected Redis memory load"
    )
    expected_saturation_pct: float = Field(
        ..., ge=0.0, le=100.0, description="Projected aggregate saturation"
    )
    projected_state: PerformanceGlobalState = Field(
        ..., description="Projected global performance state"
    )
    scaling_recommendation: ScalingRecommendation = Field(
        ..., description="Recommended scaling action for scenario"
    )


class CapacityForecast(BaseModel):
    """Multi-tier traffic load forecasting and capacity projection."""

    scenarios: list[TrafficProjectionScenario] = Field(
        ..., description="Projections for 1x, 2x, 5x, 10x, 20x"
    )
    forecast_timestamp: datetime = Field(
        ..., description="Forecast generation timestamp"
    )
    bottleneck_under_20x: BottleneckType = Field(
        ..., description="First bottleneck reached at 20x scale"
    )
    headroom_summary: str = Field(..., description="Executive capacity narrative")


class QueuePerformance(BaseModel):
    """Queue surveillance, arrival/processing rates, and drain time."""

    queue_name: str = Field(..., description="Identifier of the queue")
    queue_depth: int = Field(..., ge=0, description="Pending unconsumed items")
    arrival_rate_per_sec: float = Field(
        ..., ge=0.0, description="Inbound jobs per second"
    )
    processing_rate_per_sec: float = Field(
        ..., ge=0.0, description="Outbound processed jobs per second"
    )
    oldest_job_age_sec: float = Field(
        ..., ge=0.0, description="Age of oldest job in seconds"
    )
    backlog_growth_pct: float = Field(..., description="Rate of backlog growth (+/- %)")
    worker_utilization_pct: float = Field(
        ..., ge=0.0, le=100.0, description="Active worker concurrency usage"
    )
    drain_time_sec: float = Field(
        ..., ge=0.0, description="Estimated seconds to drain current backlog"
    )
    state: QueueState = Field(..., description="Queue health state")
    recommendation: str = Field(
        ..., description="Advisory queue optimization recommendation"
    )


class DatabasePerformance(BaseModel):
    """Relational database connection, latency, and query intelligence."""

    p50_latency_ms: float = Field(..., ge=0.0, description="Median query latency in ms")
    p95_latency_ms: float = Field(
        ..., ge=0.0, description="95th percentile query latency in ms"
    )
    p99_latency_ms: float = Field(
        ..., ge=0.0, description="99th percentile query latency in ms"
    )
    slow_query_count: int = Field(
        ..., ge=0, description="Count of queries exceeding 100ms threshold"
    )
    active_connections: int = Field(
        ..., ge=0, description="Currently active connections"
    )
    waiting_connections: int = Field(
        ..., ge=0, description="Connections waiting in pool queue"
    )
    pool_utilization_pct: float = Field(
        ..., ge=0.0, le=100.0, description="Connection pool utilization percentage"
    )
    lock_wait_time_ms: float = Field(
        ..., ge=0.0, description="Total lock wait time in ms"
    )
    transaction_duration_ms: float = Field(
        ..., ge=0.0, description="Average transaction duration in ms"
    )
    query_throughput_qps: float = Field(
        ..., ge=0.0, description="Queries executed per second"
    )
    saturation_pct: float = Field(
        ..., ge=0.0, le=100.0, description="Database saturation percentage"
    )
    state: DatabasePerformanceState = Field(..., description="Database risk assessment")
    recommendations: list[str] = Field(
        ..., description="Advisory database optimizations"
    )


class CachePerformance(BaseModel):
    """Redis / memory cache hit ratio, latency, and pressure analysis."""

    hit_ratio_pct: float = Field(
        ..., ge=0.0, le=100.0, description="Cache hit percentage"
    )
    miss_ratio_pct: float = Field(
        ..., ge=0.0, le=100.0, description="Cache miss percentage"
    )
    command_latency_ms: float = Field(
        ..., ge=0.0, description="Average Redis command latency in ms"
    )
    memory_utilization_pct: float = Field(
        ..., ge=0.0, le=100.0, description="Redis maxmemory utilization percentage"
    )
    eviction_rate_per_sec: float = Field(
        ..., ge=0.0, description="Key evictions per second"
    )
    connection_utilization_pct: float = Field(
        ..., ge=0.0, le=100.0, description="Connection pool utilization"
    )
    cache_efficiency_pct: float = Field(
        ..., ge=0.0, le=100.0, description="Hit rate * 100"
    )
    state: CachePerformanceState = Field(..., description="Cache health state")
    cache_pressure: bool = Field(
        ..., description="True if memory > 80% or evictions > 0"
    )
    recommendations: list[str] = Field(
        ..., description="Advisory caching recommendations"
    )


class MLPerformance(BaseModel):
    """ML model inference throughput, latency, and queue delay."""

    inference_rpm: float = Field(
        ..., ge=0.0, description="Predictions requested per minute"
    )
    throughput_rps: float = Field(
        ..., ge=0.0, description="Predictions served per second"
    )
    p50_latency_ms: float = Field(
        ..., ge=0.0, description="Median inference latency in ms"
    )
    p95_latency_ms: float = Field(
        ..., ge=0.0, description="95th percentile inference latency in ms"
    )
    p99_latency_ms: float = Field(
        ..., ge=0.0, description="99th percentile inference latency in ms"
    )
    queue_delay_ms: float = Field(
        ..., ge=0.0, description="Time spent waiting for model inference slot"
    )
    model_load_time_ms: float = Field(
        ..., ge=0.0, description="Model cold-start load time in ms"
    )
    prediction_failure_rate_pct: float = Field(
        ..., ge=0.0, le=100.0, description="Prediction fallback/error rate"
    )
    cpu_utilization_pct: float = Field(
        ..., ge=0.0, le=100.0, description="Inference engine CPU usage"
    )
    memory_utilization_pct: float = Field(
        ..., ge=0.0, le=100.0, description="Inference engine memory usage"
    )
    state: str = Field(
        ..., description="Operational state: HEALTHY, DEGRADED, SATURATED"
    )
    recommendations: list[str] = Field(
        ..., description="Advisory ML performance recommendations"
    )


class WebhookPerformance(BaseModel):
    """Webhook burst ingestion, queue growth, and resilience analysis."""

    ingestion_latency_ms: float = Field(
        ..., ge=0.0, description="Webhook ingestion acknowledgment latency"
    )
    processing_latency_ms: float = Field(
        ..., ge=0.0, description="End-to-end webhook processing latency"
    )
    ingestion_throughput_tps: float = Field(
        ..., ge=0.0, description="Inbound webhooks per second"
    )
    processing_throughput_tps: float = Field(
        ..., ge=0.0, description="Processed webhooks per second"
    )
    queue_depth: int = Field(..., ge=0, description="Unprocessed webhook queue depth")
    duplicate_rate_pct: float = Field(
        ..., ge=0.0, le=100.0, description="Duplicate webhook arrival rate"
    )
    backlog_age_sec: float = Field(
        ..., ge=0.0, description="Age of oldest unconsumed webhook in queue"
    )
    drain_time_sec: float = Field(
        ..., ge=0.0, description="Estimated seconds to drain webhook backlog"
    )
    burst_scenarios: dict[str, Any] = Field(
        ..., description="Simulated burst absorption results (NORMAL, 2X, 5X, 10X, 20X)"
    )


class BottleneckFinding(BaseModel):
    """Identified system bottleneck with quantitative evidence and severity."""

    bottleneck_id: str = Field(
        ..., description="Unique bottleneck identifier (e.g. BTN-DB-01)"
    )
    subsystem: BottleneckType = Field(..., description="Affected subsystem")
    severity: PerformanceSeverity = Field(..., description="Bottleneck severity level")
    observed_metric: str = Field(..., description="Observed quantitative metric")
    threshold: str = Field(..., description="Engineering threshold breached")
    evidence: str = Field(..., description="Factual evidence explanation")
    impact: str = Field(..., description="Downstream impact description")
    recommended_action: str = Field(..., description="Advisory mitigation step")
    is_primary: bool = Field(..., description="True if primary system constraint")


class PerformanceIncident(BaseModel):
    """Performance anomaly or degradation incident record."""

    incident_id: str = Field(
        ..., description="Unique incident identifier (e.g. PERF-INC-2026-001)"
    )
    incident_type: PerformanceIncidentType = Field(
        ..., description="Categorical incident type"
    )
    severity: PerformanceSeverity = Field(..., description="Incident severity level")
    status: PerformanceIncidentStatus = Field(..., description="Lifecycle state")
    detection_timestamp: datetime = Field(..., description="Detection timestamp")
    affected_subsystem: str = Field(..., description="Subsystem affected")
    observed_metrics: dict[str, Any] = Field(
        ..., description="Quantitative telemetry snapshot"
    )
    threshold: str = Field(..., description="Threshold breached")
    impact: str = Field(..., description="System and client impact description")
    probable_cause: str = Field(..., description="Root cause hypothesis")
    recommended_mitigation: str = Field(..., description="Mitigation steps")
    lifecycle_events: list[dict[str, Any]] = Field(
        default_factory=list, description="Chronological audit history"
    )


class LoadTestRequest(BaseModel):
    """Request payload to initiate a controlled synthetic load test."""

    scenario: LoadTestScenario = Field(..., description="Scenario to execute")
    duration_seconds: int = Field(
        default=30, ge=5, le=300, description="Test duration in seconds"
    )
    target_rpm: int = Field(
        default=1000, ge=100, le=50000, description="Target simulated RPM"
    )
    notes: str | None = Field(
        default=None, max_length=500, description="Operator notes or test justification"
    )


class LoadTestRun(BaseModel):
    """Executed synthetic load test results and safety verification."""

    test_id: str = Field(
        ..., description="Unique test run identifier (e.g. LTR-API-NORMAL-001)"
    )
    scenario: LoadTestScenario = Field(..., description="Executed scenario")
    status: LoadTestStatus = Field(..., description="Final status")
    start_timestamp: datetime = Field(..., description="Start timestamp")
    duration_seconds: int = Field(..., ge=0, description="Executed duration in seconds")
    target_throughput_rpm: int = Field(..., ge=0, description="Target RPM")
    achieved_throughput_rpm: int = Field(
        ..., ge=0, description="Actual achieved simulated RPM"
    )
    p50_latency_ms: float = Field(..., ge=0.0, description="Median latency in ms")
    p95_latency_ms: float = Field(
        ..., ge=0.0, description="95th percentile latency in ms"
    )
    p99_latency_ms: float = Field(
        ..., ge=0.0, description="99th percentile latency in ms"
    )
    error_rate_pct: float = Field(
        ..., ge=0.0, le=100.0, description="Simulated error percentage"
    )
    timeout_rate_pct: float = Field(
        ..., ge=0.0, le=100.0, description="Simulated timeout percentage"
    )
    peak_cpu_pct: float = Field(
        ..., ge=0.0, le=100.0, description="Peak CPU utilization"
    )
    peak_memory_pct: float = Field(
        ..., ge=0.0, le=100.0, description="Peak memory utilization"
    )
    db_utilization_pct: float = Field(
        ..., ge=0.0, le=100.0, description="Database connection pool utilization"
    )
    queue_utilization_pct: float = Field(
        ..., ge=0.0, le=100.0, description="Queue capacity utilization"
    )
    cache_utilization_pct: float = Field(
        ..., ge=0.0, le=100.0, description="Cache memory utilization"
    )
    bottleneck: BottleneckType = Field(..., description="Identified limiting subsystem")
    capacity_result: str = Field(..., description="Capacity headroom outcome")
    safety_result: str = Field(
        ..., description="Safety and isolation validation outcome"
    )
    financial_isolation_verified: bool = Field(
        ..., description="True if verified delta financial mutations == 0"
    )
    initiated_by: str = Field(..., description="Actor username or identifier")


class PerformanceRegression(BaseModel):
    """Detected performance regression compared to baseline or previous release."""

    regression_id: str = Field(..., description="Unique regression identifier")
    metric_name: str = Field(..., description="Metric exhibiting regression")
    current_value: float = Field(..., description="Current observed value")
    baseline_value: float = Field(..., description="Baseline reference value")
    delta_pct: float = Field(..., description="Percentage change (+/-)")
    regression_type: str = Field(
        ..., description="LATENCY_REGRESSION, THROUGHPUT_REGRESSION, etc."
    )
    severity: PerformanceSeverity = Field(..., description="Severity level")
    detected_at: datetime = Field(..., description="Detection timestamp")


class PerformanceReadinessGate(BaseModel):
    """Deterministic readiness safety gate evaluation."""

    code: str = Field(..., description="Gate code (e.g. GATE-PERF-01)")
    name: str = Field(..., description="Human-readable gate name")
    status: str = Field(..., description="PASS, WARN, FAIL")
    observed_value: str = Field(..., description="Observed metric value")
    threshold: str = Field(..., description="Required engineering threshold")
    severity: PerformanceSeverity = Field(..., description="Severity if gate fails")
    evidence: str = Field(..., description="Quantitative proof")
    remediation: str = Field(..., description="Corrective action if failing")


class PerformanceReport(BaseModel):
    """Comprehensive cryptographically signed performance audit and capacity report."""

    report_id: str = Field(..., description="Unique report identifier")
    generated_at: datetime = Field(..., description="Generation timestamp")
    performance_score: float = Field(
        ..., ge=0.0, le=100.0, description="Overall performance score"
    )
    global_state: PerformanceGlobalState = Field(
        ..., description="Global performance state"
    )
    summary: PerformanceSummary = Field(
        ..., description="Executive performance summary"
    )
    services: list[PerformanceServiceMetric] = Field(
        ..., description="11 service metrics"
    )
    capacity: CapacityAssessment = Field(
        ..., description="Capacity planning assessment"
    )
    bottlenecks: list[BottleneckFinding] = Field(
        ..., description="Active bottleneck findings"
    )
    incidents: list[PerformanceIncident] = Field(
        ..., description="Performance incidents"
    )
    gates: list[PerformanceReadinessGate] = Field(..., description="18 readiness gates")
    verification_signature: str = Field(..., description="SHA-256 integrity checksum")
