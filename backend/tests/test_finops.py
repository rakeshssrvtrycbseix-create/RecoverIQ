"""Unit and integration tests for RecoverIQ Phase 10I: FinOps, Cost Intelligence,

Resource Governance, Unit Economics & Financial Efficiency Control Plane.
"""

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.security import UserRole, create_access_token
from app.models.enums import (
    BudgetState,
    CostCategory,
    FinOpsGateStatus,
    FinOpsGlobalState,
    FinOpsHealth,
    FinOpsIncidentStatus,
    OptimizationStatus,
    ResourceEfficiencyState,
)


def get_token(
    role: UserRole = UserRole.ADMIN, user_id: str = "test-finops-user"
) -> str:
    return create_access_token(user_id=user_id, role=role.value)


def test_finops_summary_and_scoring(client: TestClient, db_session: Session):
    token = get_token(UserRole.VIEWER)
    headers = {"Authorization": f"Bearer {token}"}

    response = client.get("/api/recovery/intelligence/finops/summary", headers=headers)
    assert response.status_code == 200
    data = response.json()

    assert 0.0 <= data["finops_score"] <= 100.0
    assert data["score_classification"] in [
        FinOpsHealth.EXCELLENT.value,
        FinOpsHealth.GOOD.value,
        FinOpsHealth.WARNING.value,
        FinOpsHealth.DEGRADED.value,
        FinOpsHealth.HIGH_RISK.value,
        FinOpsHealth.CRITICAL.value,
    ]
    assert data["global_finops_state"] in [
        FinOpsGlobalState.HEALTHY.value,
        FinOpsGlobalState.MONITORING.value,
        FinOpsGlobalState.COST_WARNING.value,
        FinOpsGlobalState.OPTIMIZATION_REQUIRED.value,
        FinOpsGlobalState.HIGH_COST_UTILIZATION.value,
        FinOpsGlobalState.FINOPS_DEGRADED.value,
        FinOpsGlobalState.SEVERE_COST_ANOMALY.value,
        FinOpsGlobalState.BUDGET_EXHAUSTION.value,
        FinOpsGlobalState.CRITICAL_FINOPS_FAILURE.value,
        FinOpsGlobalState.EMERGENCY_COST_BREACH.value,
    ]
    assert data["total_monthly_cost_inr"] > 0
    assert data["total_daily_cost_inr"] > 0
    assert data["monthly_budget_inr"] > 0
    assert data["passed_gates_count"] == 20
    assert data["total_gates_count"] == 20
    assert data["financial_isolation_verified"] is True
    assert data["automatic_financial_response"] == "DISABLED"
    assert "disclaimer" in data


def test_unauthenticated_request_rejected(client: TestClient):
    response = client.get("/api/recovery/intelligence/finops/summary")
    assert response.status_code == 401


def test_finops_score_breakdown(client: TestClient, db_session: Session):
    token = get_token(UserRole.VIEWER)
    headers = {"Authorization": f"Bearer {token}"}

    response = client.get("/api/recovery/intelligence/finops/score", headers=headers)
    assert response.status_code == 200
    data = response.json()

    assert 0.0 <= data["cost_allocation_score"] <= 100.0
    assert 0.0 <= data["budget_health_score"] <= 100.0
    assert 0.0 <= data["forecast_accuracy_score"] <= 100.0
    assert 0.0 <= data["resource_efficiency_score"] <= 100.0
    assert 0.0 <= data["unit_economics_score"] <= 100.0
    assert 0.0 <= data["cost_anomaly_score"] <= 100.0
    assert 0.0 <= data["capacity_efficiency_score"] <= 100.0
    assert 0.0 <= data["waste_detection_score"] <= 100.0
    assert 0.0 <= data["tagging_governance_score"] <= 100.0
    assert 0.0 <= data["optimization_readiness_score"] <= 100.0
    assert 0.0 <= data["composite_finops_score"] <= 100.0


def test_cluster_cost_allocation(client: TestClient, db_session: Session):
    token = get_token(UserRole.VIEWER)
    headers = {"Authorization": f"Bearer {token}"}

    response = client.get("/api/recovery/intelligence/finops/costs", headers=headers)
    assert response.status_code == 200
    data = response.json()

    assert data["total_monthly_cost_inr"] > 0
    assert data["total_daily_cost_inr"] > 0
    assert data["total_hourly_cost_inr"] > 0
    assert len(data["services"]) == 11
    assert len(data["categories"]) == 10

    # Verify sum of services matches total monthly spend
    svc_sum = sum(s["monthly_cost_inr"] for s in data["services"])
    assert round(svc_sum, 2) == round(data["total_monthly_cost_inr"], 2)


def test_service_cost_attribution_all_11_services(
    client: TestClient, db_session: Session
):
    token = get_token(UserRole.VIEWER)
    headers = {"Authorization": f"Bearer {token}"}

    response = client.get(
        "/api/recovery/intelligence/finops/costs/services", headers=headers
    )
    assert response.status_code == 200
    services = response.json()

    assert len(services) == 11
    service_names = {s["service_name"] for s in services}
    expected_services = {
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
    }
    assert service_names == expected_services

    for s in services:
        assert s["monthly_cost_inr"] > 0
        assert 0.0 <= s["cost_share_pct"] <= 100.0
        assert s["rpm"] >= 0
        assert s["cost_per_1k_requests_inr"] >= 0
        assert 0.0 <= s["cpu_efficiency_pct"] <= 100.0
        assert 0.0 <= s["memory_efficiency_pct"] <= 100.0
        assert s["efficiency_status"] in [e.value for e in ResourceEfficiencyState]


def test_category_costs_all_10_categories(client: TestClient, db_session: Session):
    token = get_token(UserRole.VIEWER)
    headers = {"Authorization": f"Bearer {token}"}

    response = client.get(
        "/api/recovery/intelligence/finops/costs/categories", headers=headers
    )
    assert response.status_code == 200
    categories = response.json()

    assert len(categories) == 10
    cat_names = {c["category"] for c in categories}
    expected_categories = {c.value for c in CostCategory}
    assert cat_names == expected_categories

    for c in categories:
        assert c["hourly_cost_inr"] > 0
        assert c["daily_cost_inr"] > 0
        assert c["monthly_cost_inr"] > 0
        assert 0.0 <= c["cost_share_pct"] <= 100.0


def test_unit_economics_metrics(client: TestClient, db_session: Session):
    token = get_token(UserRole.VIEWER)
    headers = {"Authorization": f"Bearer {token}"}

    response = client.get(
        "/api/recovery/intelligence/finops/unit-economics", headers=headers
    )
    assert response.status_code == 200
    data = response.json()

    assert data["cost_per_transaction"]["cost_per_successful_txn_inr"] > 0
    assert data["cost_per_recovery_case"]["cost_per_case_inr"] > 0
    assert data["ml_inference_cost"]["cost_per_prediction_inr"] > 0
    assert data["database_cost"]["cost_per_100k_queries_inr"] > 0
    assert data["cache_cost"]["hit_rate_pct"] > 90.0
    assert data["webhook_cost"]["cost_per_1k_webhooks_inr"] > 0
    assert data["cost_per_1k_requests_inr"] > 0
    assert data["recovery_intelligence_value_efficiency"] > 0


def test_resource_efficiency_and_utilization(client: TestClient, db_session: Session):
    token = get_token(UserRole.VIEWER)
    headers = {"Authorization": f"Bearer {token}"}

    response = client.get(
        "/api/recovery/intelligence/finops/resources/efficiency", headers=headers
    )
    assert response.status_code == 200
    data = response.json()

    assert 0.0 <= data["overall_efficiency_pct"] <= 100.0
    assert data["total_waste_cost_inr"] >= 0
    assert len(data["resources"]) >= 8

    for r in data["resources"]:
        assert 0.0 <= r["utilization_pct"] <= 100.0
        assert 0.0 <= r["safe_capacity_pct"] <= 100.0
        assert 0.0 <= r["efficiency_pct"] <= 100.0


def test_budget_governance_statuses(client: TestClient, db_session: Session):
    token = get_token(UserRole.VIEWER)
    headers = {"Authorization": f"Bearer {token}"}

    response = client.get(
        "/api/recovery/intelligence/finops/budgets/status", headers=headers
    )
    assert response.status_code == 200
    budgets = response.json()

    assert len(budgets) == 4
    periods = {b["period"] for b in budgets}
    assert periods == {"DAILY", "WEEKLY", "MONTHLY", "QUARTERLY"}

    for b in budgets:
        assert b["budget_amount_inr"] > 0
        assert b["actual_amount_inr"] > 0
        assert b["burn_rate_pct"] >= 0
        assert b["state"] in [s.value for s in BudgetState]
        assert len(b["thresholds"]) == 5


def test_budget_configuration_admin_only(client: TestClient, db_session: Session):
    admin_token = get_token(UserRole.ADMIN)
    headers = {"Authorization": f"Bearer {admin_token}"}

    payload = {
        "period": "MONTHLY",
        "budget_amount_inr": 155000.0,
        "notes": "Q3 Infrastructure budget expansion for peak sales traffic.",
    }
    response = client.post(
        "/api/recovery/intelligence/finops/budgets/configure",
        json=payload,
        headers=headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["period"] == "MONTHLY"


def test_budget_configuration_viewer_forbidden(client: TestClient, db_session: Session):
    viewer_token = get_token(UserRole.VIEWER)
    headers = {"Authorization": f"Bearer {viewer_token}"}

    payload = {
        "period": "MONTHLY",
        "budget_amount_inr": 155000.0,
        "notes": "Unauthorized budget change.",
    }
    response = client.post(
        "/api/recovery/intelligence/finops/budgets/configure",
        json=payload,
        headers=headers,
    )
    assert response.status_code == 403


def test_cost_forecasts_scenarios(client: TestClient, db_session: Session):
    token = get_token(UserRole.VIEWER)
    headers = {"Authorization": f"Bearer {token}"}

    response = client.get(
        "/api/recovery/intelligence/finops/forecasts", headers=headers
    )
    assert response.status_code == 200
    data = response.json()

    assert data["baseline_monthly_cost_inr"] > 0
    assert len(data["scenarios"]) == 5
    scenario_names = {s["scenario_name"] for s in data["scenarios"]}
    assert scenario_names == {
        "BASELINE",
        "GROWTH",
        "HIGH_GROWTH",
        "TRAFFIC_SURGE",
        "STRESS",
    }

    for s in data["scenarios"]:
        assert s["forecast_7d_inr"] > 0
        assert s["forecast_30d_inr"] > 0
        assert s["forecast_90d_inr"] > 0
        assert 0.0 <= s["confidence_score"] <= 1.0


def test_custom_forecast_generation(client: TestClient, db_session: Session):
    operator_token = get_token(UserRole.OPERATOR)
    headers = {"Authorization": f"Bearer {operator_token}"}

    payload = {
        "horizon_days": 30,
        "traffic_multiplier": 1.5,
        "include_stress_scenario": True,
    }
    response = client.post(
        "/api/recovery/intelligence/finops/forecasts/generate",
        json=payload,
        headers=headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert len(data["scenarios"]) == 5


def test_cost_anomalies_and_evidence_hashes(client: TestClient, db_session: Session):
    token = get_token(UserRole.VIEWER)
    headers = {"Authorization": f"Bearer {token}"}

    response = client.get(
        "/api/recovery/intelligence/finops/anomalies", headers=headers
    )
    assert response.status_code == 200
    anomalies = response.json()

    assert len(anomalies) >= 3
    for a in anomalies:
        assert a["anomaly_id"].startswith("ANOM-")
        assert a["observed_cost_inr"] > 0
        assert len(a["evidence_hash"]) == 64
        assert len(a["recommended_action"]) > 0


def test_resource_waste_findings(client: TestClient, db_session: Session):
    token = get_token(UserRole.VIEWER)
    headers = {"Authorization": f"Bearer {token}"}

    response = client.get("/api/recovery/intelligence/finops/waste", headers=headers)
    assert response.status_code == 200
    findings = response.json()

    assert len(findings) >= 5
    for f in findings:
        assert f["finding_id"].startswith("WST-")
        assert f["estimated_monthly_savings_inr"] > 0
        assert f["human_approval_required"] is True


def test_optimization_recommendations_list(client: TestClient, db_session: Session):
    token = get_token(UserRole.VIEWER)
    headers = {"Authorization": f"Bearer {token}"}

    response = client.get(
        "/api/recovery/intelligence/finops/optimizations", headers=headers
    )
    assert response.status_code == 200
    recs = response.json()

    assert len(recs) >= 4
    for r in recs:
        assert r["recommendation_id"].startswith("OPT-")
        assert r["expected_monthly_savings_inr"] > 0
        assert r["status"] in [s.value for s in OptimizationStatus]
        assert "performance_impact" in r["impact"]
        assert "security_impact" in r["impact"]


def test_optimization_approval_admin_only(client: TestClient, db_session: Session):
    admin_token = get_token(UserRole.ADMIN)
    headers = {"Authorization": f"Bearer {admin_token}"}

    payload = {
        "decision": "APPROVE",
        "notes": "Approved in weekly FinOps architecture review.",
    }
    response = client.post(
        "/api/recovery/intelligence/finops/optimizations/OPT-5E6F7A8B/approve",
        json=payload,
        headers=headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == OptimizationStatus.APPROVED.value
    assert data["approved_by"] is not None


def test_optimization_approval_viewer_forbidden(
    client: TestClient, db_session: Session
):
    viewer_token = get_token(UserRole.VIEWER)
    headers = {"Authorization": f"Bearer {viewer_token}"}

    payload = {
        "decision": "APPROVE",
        "notes": "Attempted unauthorized approval.",
    }
    response = client.post(
        "/api/recovery/intelligence/finops/optimizations/OPT-5E6F7A8B/approve",
        json=payload,
        headers=headers,
    )
    assert response.status_code == 403


def test_finops_incidents_list(client: TestClient, db_session: Session):
    token = get_token(UserRole.VIEWER)
    headers = {"Authorization": f"Bearer {token}"}

    response = client.get(
        "/api/recovery/intelligence/finops/incidents", headers=headers
    )
    assert response.status_code == 200
    incidents = response.json()

    assert len(incidents) >= 2
    for i in incidents:
        assert i["incident_id"].startswith("INC-FIN-")
        assert i["status"] in [s.value for s in FinOpsIncidentStatus]
        assert len(i["evidence_fingerprint"]) == 64


def test_finops_incident_lifecycle_actions(client: TestClient, db_session: Session):
    operator_token = get_token(UserRole.OPERATOR)
    headers = {"Authorization": f"Bearer {operator_token}"}

    inc_id = "INC-FIN-2026-0801"

    # Acknowledge
    r_ack = client.post(
        f"/api/recovery/intelligence/finops/incidents/{inc_id}/acknowledge",
        json={"notes": "Triage started by FinOps SRE."},
        headers=headers,
    )
    assert r_ack.status_code == 200
    assert r_ack.json()["status"] == FinOpsIncidentStatus.ACKNOWLEDGED.value

    # Escalate
    r_esc = client.post(
        f"/api/recovery/intelligence/finops/incidents/{inc_id}/escalate",
        json={"notes": "Escalated to engineering leadership for approval."},
        headers=headers,
    )
    assert r_esc.status_code == 200
    assert r_esc.json()["status"] == FinOpsIncidentStatus.ESCALATED.value

    # Resolve
    r_res = client.post(
        f"/api/recovery/intelligence/finops/incidents/{inc_id}/resolve",
        json={"notes": "Telemetry sampling modified and verified in staging."},
        headers=headers,
    )
    assert r_res.status_code == 200
    assert r_res.json()["status"] == FinOpsIncidentStatus.RESOLVED.value


def test_20_finops_readiness_gates(client: TestClient, db_session: Session):
    token = get_token(UserRole.VIEWER)
    headers = {"Authorization": f"Bearer {token}"}

    response = client.get(
        "/api/recovery/intelligence/finops/readiness", headers=headers
    )
    assert response.status_code == 200
    gates = response.json()

    assert len(gates) == 20
    for i, g in enumerate(gates, start=1):
        expected_gate_id = f"GATE-FIN-{i:02d}"
        assert g["gate_id"] == expected_gate_id
        assert g["status"] == FinOpsGateStatus.PASS.value
        assert len(g["evidence"]) > 0
        assert len(g["remediation"]) > 0


def test_signed_finops_report_generation(client: TestClient, db_session: Session):
    token = get_token(UserRole.VIEWER)
    headers = {"Authorization": f"Bearer {token}"}

    response = client.get("/api/recovery/intelligence/finops/report", headers=headers)
    assert response.status_code == 200
    report = response.json()

    assert report["report_id"].startswith("REP-FIN-")
    assert report["finops_score"] > 0
    assert report["verification_signature"].startswith("sig_fin_hmac_sha256:")
    assert report["financial_isolation_verified"] is True
    assert len(report["readiness_gates"]) == 20
    assert len(report["cost_allocation"]["services"]) == 11


def test_zero_pii_in_finops_payloads(client: TestClient, db_session: Session):
    token = get_token(UserRole.VIEWER)
    headers = {"Authorization": f"Bearer {token}"}

    endpoints = [
        "/api/recovery/intelligence/finops/summary",
        "/api/recovery/intelligence/finops/costs",
        "/api/recovery/intelligence/finops/unit-economics",
        "/api/recovery/intelligence/finops/anomalies",
        "/api/recovery/intelligence/finops/waste",
        "/api/recovery/intelligence/finops/optimizations",
        "/api/recovery/intelligence/finops/incidents",
        "/api/recovery/intelligence/finops/readiness",
        "/api/recovery/intelligence/finops/report",
    ]

    forbidden_pii_terms = [
        "password=",
        "secret_key=",
        "rzp_live_",
        "private_key",
        "bearer ey",
        "customer_pan",
    ]

    for ep in endpoints:
        res = client.get(ep, headers=headers)
        assert res.status_code == 200
        text = res.text.lower()
        for term in forbidden_pii_terms:
            assert term not in text, (
                f"Forbidden PII/Secret term '{term}' leaked in endpoint {ep}"
            )


def test_deterministic_score_calculation_math(client: TestClient, db_session: Session):
    token = get_token(UserRole.VIEWER)
    headers = {"Authorization": f"Bearer {token}"}

    res_score = client.get("/api/recovery/intelligence/finops/score", headers=headers)
    assert res_score.status_code == 200
    s = res_score.json()

    expected_composite = (
        0.15 * s["cost_allocation_score"]
        + 0.10 * s["budget_health_score"]
        + 0.10 * s["forecast_accuracy_score"]
        + 0.10 * s["resource_efficiency_score"]
        + 0.10 * s["unit_economics_score"]
        + 0.10 * s["cost_anomaly_score"]
        + 0.10 * s["capacity_efficiency_score"]
        + 0.10 * s["waste_detection_score"]
        + 0.05 * s["tagging_governance_score"]
        + 0.10 * s["optimization_readiness_score"]
    )
    assert round(s["composite_finops_score"], 2) == round(expected_composite, 2)


def test_zero_automatic_financial_response_guarantee(
    client: TestClient, db_session: Session
):
    token = get_token(UserRole.VIEWER)
    headers = {"Authorization": f"Bearer {token}"}

    res_summary = client.get(
        "/api/recovery/intelligence/finops/summary", headers=headers
    )
    assert res_summary.status_code == 200
    assert res_summary.json()["automatic_financial_response"] == "DISABLED"


def test_global_state_hierarchy_precedence(client: TestClient, db_session: Session):
    token = get_token(UserRole.VIEWER)
    headers = {"Authorization": f"Bearer {token}"}

    res = client.get("/api/recovery/intelligence/finops/summary", headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert (
        data["global_finops_state"] == FinOpsGlobalState.HEALTHY.value
        or data["global_finops_state"] == FinOpsGlobalState.OPTIMIZATION_REQUIRED.value
    )


def test_forecast_confidence_bounds(client: TestClient, db_session: Session):
    token = get_token(UserRole.VIEWER)
    headers = {"Authorization": f"Bearer {token}"}

    res = client.get("/api/recovery/intelligence/finops/forecasts", headers=headers)
    assert res.status_code == 200
    data = res.json()
    for sc in data["scenarios"]:
        assert 0.70 <= sc["confidence_score"] <= 1.0


def test_cost_allocation_math_integrity(client: TestClient, db_session: Session):
    token = get_token(UserRole.VIEWER)
    headers = {"Authorization": f"Bearer {token}"}

    res = client.get("/api/recovery/intelligence/finops/costs", headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert data["total_daily_cost_inr"] == round(
        data["total_monthly_cost_inr"] / 30.0, 2
    )
    assert data["total_hourly_cost_inr"] == round(
        data["total_daily_cost_inr"] / 24.0, 2
    )


def test_incident_not_found_fallback(client: TestClient, db_session: Session):
    operator_token = get_token(UserRole.OPERATOR)
    headers = {"Authorization": f"Bearer {operator_token}"}

    r_ack = client.post(
        "/api/recovery/intelligence/finops/incidents/NON_EXISTENT_INCIDENT/acknowledge",
        json={"notes": "Fallback handling test."},
        headers=headers,
    )
    assert r_ack.status_code == 200
    assert r_ack.json()["status"] == FinOpsIncidentStatus.ACKNOWLEDGED.value


def test_recommendation_not_found_fallback(client: TestClient, db_session: Session):
    admin_token = get_token(UserRole.ADMIN)
    headers = {"Authorization": f"Bearer {admin_token}"}

    r_app = client.post(
        "/api/recovery/intelligence/finops/optimizations/NON_EXISTENT_OPT/approve",
        json={"decision": "APPROVE", "notes": "Fallback recommendation approval test."},
        headers=headers,
    )
    assert r_app.status_code == 200
    assert r_app.json()["status"] == OptimizationStatus.APPROVED.value
