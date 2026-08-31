"""Automated test suite for Phase 10F: Fintech Performance Engineering, Scalability, Capacity Planning & High-Load Resilience."""

import re

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.security import UserRole, create_access_token
from app.models.audit_log import AuditLog
from app.models.enums import (
    BottleneckType,
    CachePerformanceState,
    CapacityState,
    DatabasePerformanceState,
    LoadTestScenario,
    LoadTestStatus,
    PerformanceAuditEventType,
    PerformanceGlobalState,
    PerformanceHealth,
    PerformanceIncidentStatus,
    PerformanceIncidentType,
    PerformanceSeverity,
    QueueState,
    ScalingRecommendation,
)
from app.schemas.performance import (
    LoadTestRequest,
)
from app.services.performance_service import PerformanceService


@pytest.fixture
def viewer_token() -> str:
    """JWT token for viewer role."""
    return create_access_token(user_id="viewer_user", role=UserRole.VIEWER.value)


@pytest.fixture
def operator_token() -> str:
    """JWT token for operator role."""
    return create_access_token(user_id="operator_user", role=UserRole.OPERATOR.value)


@pytest.fixture
def admin_token() -> str:
    """JWT token for admin role."""
    return create_access_token(user_id="admin_user", role=UserRole.ADMIN.value)


# -------------------------------------------------------------------------
# 1. Performance Summary, Score Formula & State Hierarchy
# -------------------------------------------------------------------------


def test_performance_summary_score_and_breakdown(client: TestClient, viewer_token: str):
    """Test 0-100 Performance Score formula calculation, bounds, and classification."""
    response = client.get(
        "/api/recovery/intelligence/performance",
        headers={"Authorization": f"Bearer {viewer_token}"},
    )
    assert response.status_code == 200
    data = response.json()

    assert "score" in data
    assert 0.0 <= data["score"] <= 100.0
    assert data["classification"] in [e.value for e in PerformanceHealth]
    assert data["global_state"] in [e.value for e in PerformanceGlobalState]
    assert data["current_rpm"] > 0
    assert data["safe_rpm"] > data["current_rpm"]
    assert 0.0 <= data["capacity_utilization_pct"] <= 100.0
    assert 0.0 <= data["headroom_pct"] <= 100.0

    # Verify score breakdown
    bd = data["score_breakdown"]
    expected_score = (
        0.15 * bd["latency_score"]
        + 0.15 * bd["throughput_score"]
        + 0.15 * bd["database_score"]
        + 0.10 * bd["queue_score"]
        + 0.10 * bd["cache_score"]
        + 0.10 * bd["ml_score"]
        + 0.10 * bd["webhook_score"]
        + 0.05 * bd["cpu_score"]
        + 0.05 * bd["memory_score"]
        + 0.05 * bd["capacity_score"]
    )
    assert abs(data["score"] - round(expected_score, 1)) < 0.2


def test_global_performance_state_hierarchy(db_session: Session):
    """Test priority evaluation of global performance states."""
    service = PerformanceService(db_session)
    assert (
        service._evaluate_global_performance_state(15.0)
        == PerformanceGlobalState.EMERGENCY_CAPACITY_FAILURE
    )
    assert (
        service._evaluate_global_performance_state(35.0)
        == PerformanceGlobalState.PERFORMANCE_CRITICAL
    )
    assert (
        service._evaluate_global_performance_state(45.0)
        == PerformanceGlobalState.CAPACITY_EXHAUSTION
    )
    assert (
        service._evaluate_global_performance_state(52.0)
        == PerformanceGlobalState.SEVERE_DEGRADATION
    )
    assert (
        service._evaluate_global_performance_state(58.0)
        == PerformanceGlobalState.PERFORMANCE_DEGRADED
    )
    assert (
        service._evaluate_global_performance_state(68.0)
        == PerformanceGlobalState.HIGH_UTILIZATION
    )
    assert (
        service._evaluate_global_performance_state(72.0)
        == PerformanceGlobalState.SCALING_RECOMMENDED
    )
    assert (
        service._evaluate_global_performance_state(78.0)
        == PerformanceGlobalState.PERFORMANCE_WARNING
    )
    assert (
        service._evaluate_global_performance_state(95.0)
        == PerformanceGlobalState.HEALTHY
    )


# -------------------------------------------------------------------------
# 2. 11-Service Performance Matrix
# -------------------------------------------------------------------------


def test_11_service_performance_matrix(client: TestClient, viewer_token: str):
    """Test telemetry metrics across all 11 core RecoverIQ services."""
    response = client.get(
        "/api/recovery/intelligence/performance/services",
        headers={"Authorization": f"Bearer {viewer_token}"},
    )
    assert response.status_code == 200
    services = response.json()

    assert len(services) == 11
    service_names = {s["service_name"] for s in services}
    expected_services = {
        "API Gateway",
        "Recovery Service",
        "PolicyEngine",
        "ML Prediction Service",
        "Agent Decision Service",
        "Recovery Worker",
        "Action Dispatcher",
        "Razorpay Provider",
        "PostgreSQL",
        "Redis",
        "Audit / Event Store",
    }
    assert expected_services.issubset(service_names)

    for s in services:
        assert s["rpm"] >= 0
        assert s["p50_latency_ms"] >= 0
        assert s["p95_latency_ms"] >= s["p50_latency_ms"]
        assert s["p99_latency_ms"] >= s["p95_latency_ms"]
        assert 0.0 <= s["error_rate_pct"] <= 100.0
        assert 0.0 <= s["cpu_utilization_pct"] <= 100.0
        assert 0.0 <= s["memory_utilization_pct"] <= 100.0
        assert 0.0 <= s["capacity_utilization_pct"] <= 100.0
        assert 0.0 <= s["remaining_headroom_pct"] <= 100.0
        assert s["status"] in ["HEALTHY", "WARNING", "DEGRADED", "CRITICAL"]


# -------------------------------------------------------------------------
# 3. Capacity Planning & Multiplier Forecasts
# -------------------------------------------------------------------------


def test_capacity_assessment_headroom_formula(client: TestClient, viewer_token: str):
    """Test headroom percentage formula: 100 * (1 - current/safe)."""
    response = client.get(
        "/api/recovery/intelligence/performance/capacity",
        headers={"Authorization": f"Bearer {viewer_token}"},
    )
    assert response.status_code == 200
    data = response.json()

    assert data["current_capacity_rpm"] == 1450.0
    assert data["safe_capacity_rpm"] == 5000.0
    expected_headroom = round(100.0 * (1.0 - (1450.0 / 5000.0)), 1)
    assert abs(data["headroom_pct"] - expected_headroom) < 0.1
    assert data["capacity_state"] == CapacityState.SAFE.value
    assert (
        data["scaling_recommendation"]
        == ScalingRecommendation.NO_SCALING_REQUIRED.value
    )


def test_capacity_forecast_multipliers(client: TestClient, viewer_token: str):
    """Test synthetic traffic projections for 1x, 2x, 5x, 10x, and 20x scenarios."""
    response = client.get(
        "/api/recovery/intelligence/performance/capacity/forecast",
        headers={"Authorization": f"Bearer {viewer_token}"},
    )
    assert response.status_code == 200
    data = response.json()

    scenarios = data["scenarios"]
    assert len(scenarios) == 5
    multipliers = [s["multiplier"] for s in scenarios]
    assert multipliers == ["1x", "2x", "5x", "10x", "20x"]

    # Verify scaling progression
    rpms = [s["expected_rpm"] for s in scenarios]
    assert rpms == [1450.0, 2900.0, 7250.0, 14500.0, 29000.0]
    assert data["bottleneck_under_20x"] == BottleneckType.DATABASE.value
    assert "headroom" in data["headroom_summary"].lower()


# -------------------------------------------------------------------------
# 4. Queue, Database, Cache & ML Surveillance
# -------------------------------------------------------------------------


def test_queue_performance_drain_time_calculation(
    client: TestClient, viewer_token: str
):
    """Test queue depth, arrival/processing rates, and drain time calculations."""
    response = client.get(
        "/api/recovery/intelligence/performance/queues",
        headers={"Authorization": f"Bearer {viewer_token}"},
    )
    assert response.status_code == 200
    queues = response.json()

    assert len(queues) == 4
    for q in queues:
        assert q["queue_depth"] >= 0
        assert q["arrival_rate_per_sec"] >= 0
        assert q["processing_rate_per_sec"] >= 0
        assert q["drain_time_sec"] >= 0
        assert q["state"] in [e.value for e in QueueState]


def test_database_performance_metrics_and_state(client: TestClient, viewer_token: str):
    """Test database latency distribution, pool utilization, and risk state."""
    response = client.get(
        "/api/recovery/intelligence/performance/database",
        headers={"Authorization": f"Bearer {viewer_token}"},
    )
    assert response.status_code == 200
    data = response.json()

    assert data["p50_latency_ms"] >= 0
    assert data["p95_latency_ms"] >= data["p50_latency_ms"]
    assert data["p99_latency_ms"] >= data["p95_latency_ms"]
    assert data["slow_query_count"] == 0
    assert data["active_connections"] > 0
    assert data["waiting_connections"] == 0
    assert 0.0 <= data["pool_utilization_pct"] <= 100.0
    assert data["state"] == DatabasePerformanceState.DB_HEALTHY.value
    assert len(data["recommendations"]) > 0


def test_cache_performance_efficiency_and_pressure(
    client: TestClient, viewer_token: str
):
    """Test Redis hit ratio, cache efficiency, and pressure flag."""
    response = client.get(
        "/api/recovery/intelligence/performance/cache",
        headers={"Authorization": f"Bearer {viewer_token}"},
    )
    assert response.status_code == 200
    data = response.json()

    assert 0.0 <= data["hit_ratio_pct"] <= 100.0
    assert 0.0 <= data["miss_ratio_pct"] <= 100.0
    assert abs((data["hit_ratio_pct"] + data["miss_ratio_pct"]) - 100.0) < 0.1
    assert data["command_latency_ms"] >= 0
    assert data["cache_efficiency_pct"] == data["hit_ratio_pct"]
    assert data["state"] == CachePerformanceState.CACHE_HEALTHY.value
    assert data["cache_pressure"] is False


def test_ml_performance_inference_metrics(client: TestClient, viewer_token: str):
    """Test ML inference throughput, latency, queue delay, and failure rate."""
    response = client.get(
        "/api/recovery/intelligence/performance/ml",
        headers={"Authorization": f"Bearer {viewer_token}"},
    )
    assert response.status_code == 200
    data = response.json()

    assert data["inference_rpm"] > 0
    assert data["throughput_rps"] > 0
    assert data["p50_latency_ms"] >= 0
    assert data["p95_latency_ms"] >= data["p50_latency_ms"]
    assert data["queue_delay_ms"] >= 0
    assert 0.0 <= data["prediction_failure_rate_pct"] <= 100.0
    assert data["state"] == "HEALTHY"


def test_webhook_burst_resilience_scenarios(client: TestClient, viewer_token: str):
    """Test webhook burst resilience simulation across 5 traffic patterns."""
    response = client.get(
        "/api/recovery/intelligence/performance/webhooks",
        headers={"Authorization": f"Bearer {viewer_token}"},
    )
    assert response.status_code == 200
    data = response.json()

    assert data["ingestion_latency_ms"] >= 0
    assert data["processing_latency_ms"] >= 0
    assert data["ingestion_throughput_tps"] > 0

    bursts = data["burst_scenarios"]
    for pattern in ["NORMAL", "BURST_2X", "BURST_5X", "BURST_10X", "BURST_20X"]:
        assert pattern in bursts
        assert bursts[pattern]["absorption_rate_pct"] >= 95.0
        assert bursts[pattern]["status"] == "PASS"


# -------------------------------------------------------------------------
# 5. Bottleneck Findings & Performance Incidents
# -------------------------------------------------------------------------


def test_bottleneck_detection_findings(client: TestClient, viewer_token: str):
    """Test identified primary and secondary bottlenecks."""
    response = client.get(
        "/api/recovery/intelligence/performance/bottlenecks",
        headers={"Authorization": f"Bearer {viewer_token}"},
    )
    assert response.status_code == 200
    findings = response.json()

    assert len(findings) >= 1
    primary_count = sum(1 for f in findings if f["is_primary"])
    assert primary_count == 1
    for f in findings:
        assert f["bottleneck_id"].startswith("BTN-")
        assert f["subsystem"] in [e.value for e in BottleneckType]
        assert f["severity"] in [e.value for e in PerformanceSeverity]
        assert len(f["recommended_action"]) > 0


def test_performance_incidents_list_and_details(client: TestClient, viewer_token: str):
    """Test performance incident surveillance and mitigation timeline."""
    response = client.get(
        "/api/recovery/intelligence/performance/incidents",
        headers={"Authorization": f"Bearer {viewer_token}"},
    )
    assert response.status_code == 200
    incidents = response.json()

    assert len(incidents) >= 1
    for inc in incidents:
        assert inc["incident_id"].startswith("PERF-INC-")
        assert inc["incident_type"] in [e.value for e in PerformanceIncidentType]
        assert inc["status"] in [e.value for e in PerformanceIncidentStatus]
        assert len(inc["recommended_mitigation"]) > 0
        assert len(inc["lifecycle_events"]) > 0


def test_performance_regression_detection(client: TestClient, viewer_token: str):
    """Test performance regression telemetry."""
    response = client.get(
        "/api/recovery/intelligence/performance/regressions",
        headers={"Authorization": f"Bearer {viewer_token}"},
    )
    assert response.status_code == 200
    regressions = response.json()

    assert len(regressions) >= 1
    for reg in regressions:
        assert reg["regression_id"].startswith("REG-")
        assert reg["current_value"] >= 0
        assert reg["delta_pct"] >= 0


# -------------------------------------------------------------------------
# 6. 18 Performance Readiness Gates
# -------------------------------------------------------------------------


def test_18_performance_readiness_gates(client: TestClient, viewer_token: str):
    """Test evaluation of all 18 deterministic performance readiness safety gates."""
    response = client.get(
        "/api/recovery/intelligence/performance/gates",
        headers={"Authorization": f"Bearer {viewer_token}"},
    )
    assert response.status_code == 200
    gates = response.json()

    assert len(gates) == 18
    codes = [g["code"] for g in gates]
    expected_codes = [f"GATE-PERF-{i:02d}" for i in range(1, 19)]
    assert codes == expected_codes

    for g in gates:
        assert g["status"] in ["PASS", "WARN", "FAIL"]
        assert g["severity"] in [e.value for e in PerformanceSeverity]
        assert len(g["observed_value"]) > 0
        assert len(g["threshold"]) > 0
        assert len(g["evidence"]) > 0
        assert len(g["remediation"]) > 0


# -------------------------------------------------------------------------
# 7. Governed Synthetic Load Testing
# -------------------------------------------------------------------------


def test_execute_synthetic_load_test_operator(client: TestClient, operator_token: str):
    """Test operator initiating a controlled synthetic load test."""
    payload = {
        "scenario": LoadTestScenario.API_5X.value,
        "duration_seconds": 30,
        "target_rpm": 5000,
        "notes": "Automated operator load test execution",
    }
    response = client.post(
        "/api/recovery/intelligence/performance/load-tests",
        json=payload,
        headers={"Authorization": f"Bearer {operator_token}"},
    )
    assert response.status_code == 200
    data = response.json()

    assert data["test_id"].startswith("LTR-API_5X-")
    assert data["scenario"] == LoadTestScenario.API_5X.value
    assert data["status"] == LoadTestStatus.COMPLETED.value
    assert data["duration_seconds"] == 30
    assert data["target_throughput_rpm"] == 5000
    assert data["achieved_throughput_rpm"] > 0
    assert data["p50_latency_ms"] > 0
    assert data["p95_latency_ms"] >= data["p50_latency_ms"]
    assert data["financial_isolation_verified"] is True
    assert data["safety_result"] == "PASSED_ZERO_FINANCIAL_WRITES"
    assert data["initiated_by"] == "operator_user"


def test_load_test_scenarios_variety(db_session: Session):
    """Test execution of various synthetic load test scenarios."""
    service = PerformanceService(db_session)
    for scenario in [
        LoadTestScenario.WEBHOOK_10X,
        LoadTestScenario.RECOVERY_5X,
        LoadTestScenario.ML_5X,
        LoadTestScenario.DATABASE_PRESSURE,
        LoadTestScenario.CACHE_PRESSURE,
    ]:
        req = LoadTestRequest(scenario=scenario, duration_seconds=15, target_rpm=2000)
        run = service.execute_synthetic_load_test(
            req, actor_id="test_runner", actor_role="operator"
        )
        assert run.scenario == scenario
        assert run.status == LoadTestStatus.COMPLETED
        assert run.financial_isolation_verified is True


def test_load_test_audit_log_persistence(
    client: TestClient, admin_token: str, db_session: Session
):
    """Verify load test executions are appended to AuditLog with entity_type='load_test'."""
    payload = {
        "scenario": LoadTestScenario.API_2X.value,
        "duration_seconds": 20,
        "target_rpm": 2000,
        "notes": "Audit verification load test",
    }
    response = client.post(
        "/api/recovery/intelligence/performance/load-tests",
        json=payload,
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 200
    test_id = response.json()["test_id"]

    # Verify AuditLog row
    log_entry = (
        db_session.query(AuditLog)
        .filter(
            AuditLog.entity_type == "load_test",
        )
        .order_by(AuditLog.created_at.desc())
        .first()
    )

    assert log_entry is not None
    assert log_entry.event_type == PerformanceAuditEventType.LOAD_TEST_COMPLETED.value
    assert log_entry.actor_id == "admin_user"
    assert log_entry.new_state["test_id"] == test_id
    assert log_entry.new_state["financial_isolation_verified"] is True


def test_list_load_tests_history(client: TestClient, viewer_token: str):
    """Test retrieving history of past synthetic load test executions."""
    response = client.get(
        "/api/recovery/intelligence/performance/load-tests",
        headers={"Authorization": f"Bearer {viewer_token}"},
    )
    assert response.status_code == 200
    runs = response.json()
    assert len(runs) >= 1
    for r in runs:
        assert r["test_id"].startswith("LTR-")
        assert r["financial_isolation_verified"] is True


# -------------------------------------------------------------------------
# 8. Cryptographically Signed Performance Report
# -------------------------------------------------------------------------


def test_generate_performance_report_with_signature(
    client: TestClient, viewer_token: str
):
    """Test generating full performance audit report with SHA-256 integrity signature."""
    response = client.get(
        "/api/recovery/intelligence/performance/report",
        headers={"Authorization": f"Bearer {viewer_token}"},
    )
    assert response.status_code == 200
    report = response.json()

    assert report["report_id"].startswith("RPT-PERF-")
    assert 0.0 <= report["performance_score"] <= 100.0
    assert report["global_state"] in [e.value for e in PerformanceGlobalState]
    assert len(report["services"]) == 11
    assert len(report["gates"]) == 18
    assert report["verification_signature"].startswith("sha256:")
    assert len(report["verification_signature"]) == 71  # "sha256:" + 64 hex chars


# -------------------------------------------------------------------------
# 9. RBAC, Rate Limiting & Zero-PII Security
# -------------------------------------------------------------------------


def test_rbac_unauthenticated_requests(client: TestClient):
    """Verify unauthenticated requests return 401 Unauthorized."""
    endpoints = [
        ("GET", "/api/recovery/intelligence/performance"),
        ("GET", "/api/recovery/intelligence/performance/services"),
        ("GET", "/api/recovery/intelligence/performance/capacity"),
        ("GET", "/api/recovery/intelligence/performance/queues"),
        ("GET", "/api/recovery/intelligence/performance/database"),
        ("GET", "/api/recovery/intelligence/performance/cache"),
        ("GET", "/api/recovery/intelligence/performance/ml"),
        ("GET", "/api/recovery/intelligence/performance/webhooks"),
        ("GET", "/api/recovery/intelligence/performance/bottlenecks"),
        ("GET", "/api/recovery/intelligence/performance/incidents"),
        ("GET", "/api/recovery/intelligence/performance/gates"),
        ("GET", "/api/recovery/intelligence/performance/report"),
        ("POST", "/api/recovery/intelligence/performance/load-tests"),
    ]
    for method, path in endpoints:
        if method == "GET":
            res = client.get(path)
        else:
            res = client.post(path, json={"scenario": "API_NORMAL"})
        assert res.status_code == 401


def test_rbac_viewer_vs_operator_permissions(
    client: TestClient, viewer_token: str, operator_token: str
):
    """Verify viewer can read but cannot trigger load tests (403), while operator can."""
    payload = {"scenario": "API_NORMAL", "duration_seconds": 10, "target_rpm": 1000}

    # Viewer should be forbidden
    res_viewer = client.post(
        "/api/recovery/intelligence/performance/load-tests",
        json=payload,
        headers={"Authorization": f"Bearer {viewer_token}"},
    )
    assert res_viewer.status_code == 403

    # Operator should succeed
    res_operator = client.post(
        "/api/recovery/intelligence/performance/load-tests",
        json=payload,
        headers={"Authorization": f"Bearer {operator_token}"},
    )
    assert res_operator.status_code == 200


def test_zero_pii_in_performance_telemetry(client: TestClient, viewer_token: str):
    """Verify zero unmasked emails, phone numbers, or credit cards in performance responses."""
    endpoints = [
        "/api/recovery/intelligence/performance",
        "/api/recovery/intelligence/performance/services",
        "/api/recovery/intelligence/performance/capacity",
        "/api/recovery/intelligence/performance/queues",
        "/api/recovery/intelligence/performance/database",
        "/api/recovery/intelligence/performance/cache",
        "/api/recovery/intelligence/performance/ml",
        "/api/recovery/intelligence/performance/webhooks",
        "/api/recovery/intelligence/performance/bottlenecks",
        "/api/recovery/intelligence/performance/incidents",
        "/api/recovery/intelligence/performance/gates",
        "/api/recovery/intelligence/performance/report",
    ]

    email_regex = re.compile(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+")
    card_regex = re.compile(r"\b(?:4[0-9]{12}(?:[0-9]{3})?|5[1-5][0-9]{14})\b")

    for path in endpoints:
        res = client.get(path, headers={"Authorization": f"Bearer {viewer_token}"})
        assert res.status_code == 200
        text = res.text
        assert not email_regex.search(text), f"Plaintext email found in {path}"
        assert not card_regex.search(text), f"Plaintext credit card found in {path}"
        assert "rzp_live_" not in text
        assert "rzp_test_" not in text


def test_deterministic_ids_and_clamping(db_session: Session):
    """Test deterministic test run ID generation and score boundary clamping."""
    service = PerformanceService(db_session)
    summary = service.get_performance_summary()
    assert 0.0 <= summary.score <= 100.0
    assert summary.headroom_pct == 71.0

    report = service.generate_performance_report()
    assert report.report_id.startswith("RPT-PERF-")
    assert report.verification_signature.startswith("sha256:")


def test_performance_rate_limiting_headers(client: TestClient, viewer_token: str):
    """Verify rate limit headers on performance reads."""
    res = client.get(
        "/api/recovery/intelligence/performance",
        headers={"Authorization": f"Bearer {viewer_token}"},
    )
    assert res.status_code == 200
    assert "X-RateLimit-Limit" in res.headers or "x-ratelimit-limit" in res.headers


def test_policy_engine_supremacy_and_isolation(db_session: Session):
    """Verify PolicyEngine supremacy invariant is documented and maintained in service responses."""
    service = PerformanceService(db_session)
    summary = service.get_performance_summary()
    assert "PolicyEngine" in summary.disclaimer
    assert "observational" in summary.disclaimer.lower()
