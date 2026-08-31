"""Phase 10F — Fintech Performance Engineering, Scalability & Capacity Planning REST API Router.

Provides 16 deterministic REST endpoints for performance summary, 11-service matrix,
capacity assessment & forecasting, queue surveillance, database/cache/ML/webhook intelligence,
bottleneck detection, readiness safety gates, governed synthetic load testing, and signed reports.
Protected by 3-tier JWT RBAC and sliding-window rate limiting.
"""

import logging
from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.rate_limiter import rate_limit_mutations, rate_limit_reads
from app.core.security import (
    AuthenticatedUser,
    require_operator,
    require_viewer,
)
from app.schemas.performance import (
    BottleneckFinding,
    CachePerformance,
    CapacityAssessment,
    CapacityForecast,
    DatabasePerformance,
    LoadTestRequest,
    LoadTestRun,
    MLPerformance,
    PerformanceIncident,
    PerformanceReadinessGate,
    PerformanceRegression,
    PerformanceReport,
    PerformanceServiceMetric,
    PerformanceSummary,
    QueuePerformance,
    WebhookPerformance,
)
from app.services.performance_service import PerformanceService

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/recovery/intelligence/performance",
    tags=["performance"],
)


@router.get(
    "",
    response_model=PerformanceSummary,
    summary="Get Performance Health Score & Executive Summary",
    dependencies=[Depends(rate_limit_reads)],
)
def get_performance_overview(
    user: Annotated[AuthenticatedUser, Depends(require_viewer)],
    db: Session = Depends(get_db),
) -> PerformanceSummary:
    """Retrieve executive performance score (0-100), global state, and SLIs."""
    service = PerformanceService(db)
    return service.get_performance_summary()


@router.get(
    "/services",
    response_model=list[PerformanceServiceMetric],
    summary="Get 11-Service Performance Matrix",
    dependencies=[Depends(rate_limit_reads)],
)
def get_performance_services(
    user: Annotated[AuthenticatedUser, Depends(require_viewer)],
    db: Session = Depends(get_db),
) -> list[PerformanceServiceMetric]:
    """Retrieve telemetry, throughput, P50/P95/P99 latency, and saturation for all 11 core services."""
    service = PerformanceService(db)
    return service.get_service_performance_matrix()


@router.get(
    "/capacity",
    response_model=CapacityAssessment,
    summary="Get Capacity Planning & Headroom Assessment",
    dependencies=[Depends(rate_limit_reads)],
)
def get_capacity_assessment(
    user: Annotated[AuthenticatedUser, Depends(require_viewer)],
    db: Session = Depends(get_db),
) -> CapacityAssessment:
    """Retrieve current vs safe capacity, utilization, and remaining headroom percentage."""
    service = PerformanceService(db)
    return service.get_capacity_assessment()


@router.get(
    "/capacity/forecast",
    response_model=CapacityForecast,
    summary="Get Capacity Multiplier Forecasts (1x-20x)",
    dependencies=[Depends(rate_limit_reads)],
)
def get_capacity_forecast(
    user: Annotated[AuthenticatedUser, Depends(require_viewer)],
    db: Session = Depends(get_db),
) -> CapacityForecast:
    """Retrieve projected system behavior under 1x, 2x, 5x, 10x, and 20x traffic surges."""
    service = PerformanceService(db)
    return service.get_capacity_forecast()


@router.get(
    "/queues",
    response_model=list[QueuePerformance],
    summary="Get Queue Surveillance & Drain Time Intelligence",
    dependencies=[Depends(rate_limit_reads)],
)
def get_queue_performance(
    user: Annotated[AuthenticatedUser, Depends(require_viewer)],
    db: Session = Depends(get_db),
) -> list[QueuePerformance]:
    """Retrieve queue depths, arrival/processing rates, backlog growth, and drain times."""
    service = PerformanceService(db)
    return service.get_queue_performance()


@router.get(
    "/database",
    response_model=DatabasePerformance,
    summary="Get Relational Database Performance Intelligence",
    dependencies=[Depends(rate_limit_reads)],
)
def get_database_performance(
    user: Annotated[AuthenticatedUser, Depends(require_viewer)],
    db: Session = Depends(get_db),
) -> DatabasePerformance:
    """Retrieve query latency distribution, connection pool usage, lock wait times, and DB risk state."""
    service = PerformanceService(db)
    return service.get_database_performance()


@router.get(
    "/cache",
    response_model=CachePerformance,
    summary="Get Redis & Cache Performance Intelligence",
    dependencies=[Depends(rate_limit_reads)],
)
def get_cache_performance(
    user: Annotated[AuthenticatedUser, Depends(require_viewer)],
    db: Session = Depends(get_db),
) -> CachePerformance:
    """Retrieve Redis hit/miss ratio, command latency, memory utilization, and pressure status."""
    service = PerformanceService(db)
    return service.get_cache_performance()


@router.get(
    "/ml",
    response_model=MLPerformance,
    summary="Get ML Model Inference Performance",
    dependencies=[Depends(rate_limit_reads)],
)
def get_ml_performance(
    user: Annotated[AuthenticatedUser, Depends(require_viewer)],
    db: Session = Depends(get_db),
) -> MLPerformance:
    """Retrieve ML inference throughput, P50/P95/P99 latency, queue delay, and failure rates."""
    service = PerformanceService(db)
    return service.get_ml_performance()


@router.get(
    "/webhooks",
    response_model=WebhookPerformance,
    summary="Get Webhook Burst Resilience & Queue Growth",
    dependencies=[Depends(rate_limit_reads)],
)
def get_webhook_performance(
    user: Annotated[AuthenticatedUser, Depends(require_viewer)],
    db: Session = Depends(get_db),
) -> WebhookPerformance:
    """Retrieve webhook ingestion/processing latency, throughput, queue depth, and burst scenario results."""
    service = PerformanceService(db)
    return service.get_webhook_performance()


@router.get(
    "/bottlenecks",
    response_model=list[BottleneckFinding],
    summary="Get Primary & Secondary Bottleneck Findings",
    dependencies=[Depends(rate_limit_reads)],
)
def get_bottlenecks(
    user: Annotated[AuthenticatedUser, Depends(require_viewer)],
    db: Session = Depends(get_db),
) -> list[BottleneckFinding]:
    """Retrieve identified system bottlenecks with quantitative evidence and recommended actions."""
    service = PerformanceService(db)
    return service.get_bottlenecks()


@router.get(
    "/incidents",
    response_model=list[PerformanceIncident],
    summary="Get Performance Incidents & Anomaly Surveillance",
    dependencies=[Depends(rate_limit_reads)],
)
def get_performance_incidents(
    user: Annotated[AuthenticatedUser, Depends(require_viewer)],
    db: Session = Depends(get_db),
) -> list[PerformanceIncident]:
    """Retrieve active and historical performance degradation incidents and mitigation steps."""
    service = PerformanceService(db)
    return service.get_performance_incidents()


@router.get(
    "/gates",
    response_model=list[PerformanceReadinessGate],
    summary="Get 18 Performance Readiness Safety Gates",
    dependencies=[Depends(rate_limit_reads)],
)
def get_performance_gates(
    user: Annotated[AuthenticatedUser, Depends(require_viewer)],
    db: Session = Depends(get_db),
) -> list[PerformanceReadinessGate]:
    """Retrieve deterministic evaluation of all 18 performance and capacity readiness gates."""
    service = PerformanceService(db)
    return service.get_performance_readiness_gates()


@router.get(
    "/regressions",
    response_model=list[PerformanceRegression],
    summary="Get Performance Regression Detections",
    dependencies=[Depends(rate_limit_reads)],
)
def get_performance_regressions(
    user: Annotated[AuthenticatedUser, Depends(require_viewer)],
    db: Session = Depends(get_db),
) -> list[PerformanceRegression]:
    """Retrieve detected latency or throughput regressions against baseline."""
    service = PerformanceService(db)
    return service.get_performance_regressions()


@router.get(
    "/load-tests",
    response_model=list[LoadTestRun],
    summary="List Synthetic Load Test Runs",
    dependencies=[Depends(rate_limit_reads)],
)
def list_load_tests(
    user: Annotated[AuthenticatedUser, Depends(require_viewer)],
    db: Session = Depends(get_db),
) -> list[LoadTestRun]:
    """Retrieve past synthetic benchmark and load test results from AuditLog."""
    service = PerformanceService(db)
    return service.list_load_tests()


@router.post(
    "/load-tests",
    response_model=LoadTestRun,
    summary="Execute Controlled Synthetic Load Test",
    dependencies=[Depends(rate_limit_mutations)],
)
def run_load_test(
    request: LoadTestRequest,
    user: Annotated[AuthenticatedUser, Depends(require_operator)],
    db: Session = Depends(get_db),
) -> LoadTestRun:
    """Execute a controlled synthetic load test in isolated memory with guaranteed zero financial writes."""
    logger.info(
        "Initiating synthetic load test scenario=%s target_rpm=%d by user=%s",
        request.scenario.value,
        request.target_rpm,
        user.id,
    )
    service = PerformanceService(db)
    return service.execute_synthetic_load_test(
        request=request,
        actor_id=user.id,
        actor_role=user.role.value if hasattr(user.role, "value") else str(user.role),
    )


@router.get(
    "/report",
    response_model=PerformanceReport,
    summary="Generate Cryptographically Signed Performance Report",
    dependencies=[Depends(rate_limit_reads)],
)
def get_performance_report(
    user: Annotated[AuthenticatedUser, Depends(require_viewer)],
    db: Session = Depends(get_db),
) -> PerformanceReport:
    """Generate a complete, cryptographically verified performance audit report with SHA-256 signature."""
    service = PerformanceService(db)
    return service.generate_performance_report()
