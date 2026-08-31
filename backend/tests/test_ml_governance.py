"""Comprehensive Unit & Integration Test Suite for RecoverIQ Phase 10J:

AI/ML Governance, Model Risk Management, Explainability, Drift Detection & Responsible AI Control Plane.
"""

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.security import UserRole, create_access_token
from app.models.enums import (
    DriftStatus,
    MLGateStatus,
    MLGlobalState,
    MLIncidentStatus,
    ModelHealth,
    ModelLifecycleState,
    ModelRiskLevel,
    PromotionRecommendation,
    RollbackReadinessStatus,
)


def get_token(
    role: UserRole = UserRole.ADMIN, user_id: str = "test-ml-gov-user"
) -> str:
    return create_access_token(user_id=user_id, role=role.value)


# -----------------------------------------------------------------------------
# 1. Executive Summary & Health Posture Tests
# -----------------------------------------------------------------------------


def test_ml_governance_summary_and_scoring(client: TestClient, db_session: Session):
    token = get_token(UserRole.VIEWER)
    headers = {"Authorization": f"Bearer {token}"}

    response = client.get(
        "/api/recovery/intelligence/ml-governance/summary", headers=headers
    )
    assert response.status_code == 200
    data = response.json()

    assert 0.0 <= data["governance_score"] <= 100.0
    assert data["health"] in [h.value for h in ModelHealth]
    assert data["global_state"] in [s.value for s in MLGlobalState]
    assert data["active_models_count"] >= 5
    assert data["production_models_count"] >= 3
    assert data["high_risk_models_count"] == 0
    assert data["readiness_percentage"] == 100.0
    assert data["passed_gates_count"] == 22
    assert data["total_gates_count"] == 22
    assert data["financial_isolation_verified"] is True
    assert data["zero_pii_verified"] is True


def test_ml_governance_summary_root_alias(client: TestClient, db_session: Session):
    token = get_token(UserRole.VIEWER)
    headers = {"Authorization": f"Bearer {token}"}

    res_root = client.get("/api/recovery/intelligence/ml-governance", headers=headers)
    assert res_root.status_code == 200
    assert res_root.json()["governance_score"] > 90.0


# -----------------------------------------------------------------------------
# 2. Model Registry & Catalog Tests
# -----------------------------------------------------------------------------


def test_list_models_and_catalog(client: TestClient, db_session: Session):
    token = get_token(UserRole.VIEWER)
    headers = {"Authorization": f"Bearer {token}"}

    res = client.get("/api/recovery/intelligence/ml-governance/models", headers=headers)
    assert res.status_code == 200
    models = res.json()
    assert len(models) >= 5

    model_ids = [m["model_id"] for m in models]
    assert "recovery_probability" in model_ids
    assert "optimal_channel" in model_ids
    assert "optimal_timing" in model_ids
    assert "discount_sensitivity" in model_ids
    assert "urgency_scorer" in model_ids

    # Check individual model detail
    res_single = client.get(
        "/api/recovery/intelligence/ml-governance/models/recovery_probability",
        headers=headers,
    )
    assert res_single.status_code == 200
    single = res_single.json()
    assert single["model_name"] == "Recovery Likelihood Estimator"
    assert single["lifecycle_state"] == ModelLifecycleState.PRODUCTION.value
    assert single["risk_level"] == ModelRiskLevel.LOW.value


def test_model_version_provenance(client: TestClient, db_session: Session):
    token = get_token(UserRole.VIEWER)
    headers = {"Authorization": f"Bearer {token}"}

    res = client.get(
        "/api/recovery/intelligence/ml-governance/models/recovery_probability/versions",
        headers=headers,
    )
    assert res.status_code == 200
    versions = res.json()
    assert len(versions) >= 2

    v1 = versions[0]
    assert v1["version"] == "v1.0"
    assert len(v1["artifact_hash"]) == 64
    assert len(v1["training_dataset_hash"]) == 64
    assert len(v1["feature_schema_hash"]) == 64
    assert len(v1["code_commit_hash"]) == 64


# -----------------------------------------------------------------------------
# 3. Model Lineage DAG & Cryptographic Verification Tests
# -----------------------------------------------------------------------------


def test_model_lineage_graph_structure(client: TestClient, db_session: Session):
    token = get_token(UserRole.VIEWER)
    headers = {"Authorization": f"Bearer {token}"}

    res = client.get(
        "/api/recovery/intelligence/ml-governance/models/recovery_probability/lineage",
        headers=headers,
    )
    assert res.status_code == 200
    data = res.json()

    assert data["model_id"] == "recovery_probability"
    assert data["verified"] is True
    assert len(data["root_hash"]) == 64
    assert len(data["nodes"]) >= 8

    node_types = [n["node_type"] for n in data["nodes"]]
    assert "DATASET" in node_types
    assert "FEATURES" in node_types
    assert "CODE" in node_types
    assert "HYPERPARAMETERS" in node_types
    assert "ARTIFACT" in node_types
    assert "EVALUATION" in node_types
    assert "APPROVAL" in node_types
    assert "DEPLOYMENT" in node_types


# -----------------------------------------------------------------------------
# 4. Model Performance & Evaluation Benchmark Tests
# -----------------------------------------------------------------------------


def test_model_performance_metrics(client: TestClient, db_session: Session):
    token = get_token(UserRole.VIEWER)
    headers = {"Authorization": f"Bearer {token}"}

    res = client.get(
        "/api/recovery/intelligence/ml-governance/models/recovery_probability/performance",
        headers=headers,
    )
    assert res.status_code == 200
    metrics = res.json()

    assert metrics["accuracy"] >= 0.85
    assert metrics["roc_auc"] >= 0.90
    assert metrics["brier_score"] <= 0.15
    assert metrics["latency_p95_ms"] <= 25.0
    assert metrics["latency_p99_ms"] <= 50.0
    assert metrics["throughput_rps"] >= 500.0


def test_model_evaluation_execution(client: TestClient, db_session: Session):
    op_token = get_token(UserRole.OPERATOR)
    headers = {"Authorization": f"Bearer {op_token}"}

    payload = {
        "evaluation_type": "OFFLINE",
        "sample_size": 2500,
        "notes": "Automated validation run",
    }
    res = client.post(
        "/api/recovery/intelligence/ml-governance/models/recovery_probability/evaluate",
        json=payload,
        headers=headers,
    )
    assert res.status_code == 201
    eval_data = res.json()

    assert eval_data["model_id"] == "recovery_probability"
    assert eval_data["result"] == "PASS"
    assert eval_data["performance_regression_detected"] is False
    assert len(eval_data["evidence_hash"]) == 64


# -----------------------------------------------------------------------------
# 5. Multi-Dimensional Drift Surveillance Tests
# -----------------------------------------------------------------------------


def test_model_drift_surveillance(client: TestClient, db_session: Session):
    token = get_token(UserRole.VIEWER)
    headers = {"Authorization": f"Bearer {token}"}

    res = client.get(
        "/api/recovery/intelligence/ml-governance/models/recovery_probability/drift",
        headers=headers,
    )
    assert res.status_code == 200
    drift = res.json()

    assert drift["overall_status"] == DriftStatus.STABLE.value
    assert drift["data_drift_score"] < 0.10
    assert drift["feature_drift_score"] < 0.10
    assert drift["prediction_drift_score"] < 0.10
    assert drift["features_drifted_count"] == 0
    assert len(drift["feature_metrics"]) >= 8

    for f in drift["feature_metrics"]:
        assert f["psi_score"] < 0.10
        assert f["status"] == DriftStatus.STABLE.value


def test_prediction_and_concept_drift(client: TestClient, db_session: Session):
    token = get_token(UserRole.VIEWER)
    headers = {"Authorization": f"Bearer {token}"}

    # Prediction drift
    res_pred = client.get(
        "/api/recovery/intelligence/ml-governance/models/recovery_probability/prediction-drift",
        headers=headers,
    )
    assert res_pred.status_code == 200
    assert res_pred.json()["prediction_psi"] < 0.10
    assert res_pred.json()["status"] == DriftStatus.STABLE.value

    # Concept drift
    res_conc = client.get(
        "/api/recovery/intelligence/ml-governance/models/recovery_probability/concept-drift",
        headers=headers,
    )
    assert res_conc.status_code == 200
    assert res_conc.json()["concept_drift_score"] < 0.05
    assert res_conc.json()["status"] == DriftStatus.STABLE.value


# -----------------------------------------------------------------------------
# 6. Explainability & Sanitization Tests
# -----------------------------------------------------------------------------


def test_model_explainability_sanitization(client: TestClient, db_session: Session):
    token = get_token(UserRole.VIEWER)
    headers = {"Authorization": f"Bearer {token}"}

    res = client.get(
        "/api/recovery/intelligence/ml-governance/models/recovery_probability/explainability",
        headers=headers,
    )
    assert res.status_code == 200
    record = res.json()

    assert record["model_id"] == "recovery_probability"
    assert record["sanitized"] is True
    assert "PolicyEngine" in record["disclaimer"]
    assert len(record["top_features"]) >= 4

    # Verify zero PII in explainability
    for feat in record["top_features"]:
        assert feat["direction"] in ["POSITIVE", "NEGATIVE"]
        assert 0.0 <= feat["relative_percentage"] <= 100.0


def test_on_demand_explanation_generation(client: TestClient, db_session: Session):
    op_token = get_token(UserRole.OPERATOR)
    headers = {"Authorization": f"Bearer {op_token}"}

    payload = {
        "prediction_reference": "PRED-TXN-998811",
        "feature_vector": {
            "historical_recovery_rate": 0.85,
            "days_past_due_binned": 15.0,
        },
    }
    res = client.post(
        "/api/recovery/intelligence/ml-governance/models/recovery_probability/explain",
        json=payload,
        headers=headers,
    )
    assert res.status_code == 201
    assert res.json()["prediction_reference"] == "PRED-TXN-998811"
    assert res.json()["sanitized"] is True


# -----------------------------------------------------------------------------
# 7. Responsible AI & Calibration Tests
# -----------------------------------------------------------------------------


def test_responsible_ai_fairness(client: TestClient, db_session: Session):
    token = get_token(UserRole.VIEWER)
    headers = {"Authorization": f"Bearer {token}"}

    res = client.get(
        "/api/recovery/intelligence/ml-governance/models/recovery_probability/fairness",
        headers=headers,
    )
    assert res.status_code == 200
    metrics = res.json()
    assert len(metrics) >= 3

    for m in metrics:
        assert m["status"] == "FAIR"
        assert m["disparity"] <= m["threshold"]
        assert len(m["protected_group_hash"]) == 64


def test_model_calibration_and_reliability(client: TestClient, db_session: Session):
    token = get_token(UserRole.VIEWER)
    headers = {"Authorization": f"Bearer {token}"}

    res = client.get(
        "/api/recovery/intelligence/ml-governance/models/recovery_probability/calibration",
        headers=headers,
    )
    assert res.status_code == 200
    calib = res.json()

    assert calib["expected_calibration_error"] <= 0.05
    assert calib["brier_score"] <= 0.15
    assert calib["status"] == "CALIBRATED"
    assert len(calib["bins_data"]) == 5


# -----------------------------------------------------------------------------
# 8. Model Risk Assessment (MRM) Tests
# -----------------------------------------------------------------------------


def test_model_risk_assessment_dimensions(client: TestClient, db_session: Session):
    token = get_token(UserRole.VIEWER)
    headers = {"Authorization": f"Bearer {token}"}

    res = client.get(
        "/api/recovery/intelligence/ml-governance/models/recovery_probability/risk",
        headers=headers,
    )
    assert res.status_code == 200
    risk = res.json()

    assert risk["total_score"] >= 90.0
    assert risk["risk_level"] == ModelRiskLevel.LOW.value
    assert len(risk["dimensions"]) == 10

    # Ensure weights sum to 1.0
    total_weight = sum(d["weight"] for d in risk["dimensions"])
    assert round(total_weight, 2) == 1.0


# -----------------------------------------------------------------------------
# 9. 22 ML Readiness Gates Tests
# -----------------------------------------------------------------------------


def test_all_22_ml_readiness_gates(client: TestClient, db_session: Session):
    token = get_token(UserRole.VIEWER)
    headers = {"Authorization": f"Bearer {token}"}

    res = client.get(
        "/api/recovery/intelligence/ml-governance/readiness-gates", headers=headers
    )
    assert res.status_code == 200
    gates = res.json()
    assert len(gates) == 22

    gate_codes = [g["gate_code"] for g in gates]
    for i in range(1, 23):
        expected_code = f"GATE-ML-{i:02d}"
        assert expected_code in gate_codes

    for g in gates:
        assert g["status"] == MLGateStatus.PASS.value
        assert len(g["evidence"]) > 0


# -----------------------------------------------------------------------------
# 10. Promotion Evaluation & Rollback Readiness Tests
# -----------------------------------------------------------------------------


def test_promotion_evaluation_and_rollback(client: TestClient, db_session: Session):
    op_token = get_token(UserRole.OPERATOR)
    viewer_token = get_token(UserRole.VIEWER)

    # 1. Advisory promotion evaluation
    promo_payload = {
        "candidate_version": "v1.1-candidate",
        "justification": "Quarterly ROC-AUC optimization",
    }
    res_promo = client.post(
        "/api/recovery/intelligence/ml-governance/models/recovery_probability/promotion-evaluation",
        json=promo_payload,
        headers={"Authorization": f"Bearer {op_token}"},
    )
    assert res_promo.status_code == 201
    promo = res_promo.json()
    assert promo["recommendation"] == PromotionRecommendation.PROMOTE_RECOMMENDED.value
    assert promo["human_approval_required"] is True

    # 2. Rollback readiness evaluation
    res_rb = client.get(
        "/api/recovery/intelligence/ml-governance/models/recovery_probability/rollback",
        headers={"Authorization": f"Bearer {viewer_token}"},
    )
    assert res_rb.status_code == 200
    rb = res_rb.json()
    assert rb["readiness_status"] == RollbackReadinessStatus.READY.value
    assert rb["rollback_time_seconds"] <= 30


# -----------------------------------------------------------------------------
# 11. ML Incidents Lifecycle Tests
# -----------------------------------------------------------------------------


def test_ml_incidents_lifecycle(client: TestClient, db_session: Session):
    viewer_token = get_token(UserRole.VIEWER)
    op_token = get_token(UserRole.OPERATOR)
    admin_token = get_token(UserRole.ADMIN)

    # 1. List incidents
    res_list = client.get(
        "/api/recovery/intelligence/ml-governance/incidents",
        headers={"Authorization": f"Bearer {viewer_token}"},
    )
    assert res_list.status_code == 200
    incidents = res_list.json()
    assert len(incidents) >= 1

    inc_id = incidents[0]["incident_id"]

    # 2. Get detail
    res_detail = client.get(
        f"/api/recovery/intelligence/ml-governance/incidents/{inc_id}",
        headers={"Authorization": f"Bearer {viewer_token}"},
    )
    assert res_detail.status_code == 200
    assert res_detail.json()["incident_id"] == inc_id

    # 3. Acknowledge (Operator)
    res_ack = client.post(
        f"/api/recovery/intelligence/ml-governance/incidents/{inc_id}/acknowledge?notes=Acknowledged+by+test+suite",
        headers={"Authorization": f"Bearer {op_token}"},
    )
    assert res_ack.status_code == 200
    assert res_ack.json()["status"] == MLIncidentStatus.ACKNOWLEDGED.value

    # 4. Resolve (Admin)
    res_res = client.post(
        f"/api/recovery/intelligence/ml-governance/incidents/{inc_id}/resolve?notes=Resolved+drift+after+recalibration",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert res_res.status_code == 200
    assert res_res.json()["status"] == MLIncidentStatus.RESOLVED.value


# -----------------------------------------------------------------------------
# 12. Financial Path Observational Forensics Tests
# -----------------------------------------------------------------------------


def test_financial_path_observational_forensics(
    client: TestClient, db_session: Session
):
    token = get_token(UserRole.VIEWER)
    headers = {"Authorization": f"Bearer {token}"}

    res = client.get(
        "/api/recovery/intelligence/ml-governance/forensics", headers=headers
    )
    assert res.status_code == 200
    forensics = res.json()

    assert forensics["financial_isolation_verified"] is True
    assert forensics["delta_recovery_actions"] == 0
    assert forensics["delta_payments"] == 0
    assert forensics["delta_case_financial_state"] == 0
    assert forensics["action_dispatcher_calls"] == 0
    assert forensics["razorpay_provider_calls"] == 0
    assert forensics["policy_engine_supremacy_verified"] is True
    assert len(forensics["stages"]) == 6


# -----------------------------------------------------------------------------
# 13. Signed Governance Report Tests
# -----------------------------------------------------------------------------


def test_signed_governance_report(client: TestClient, db_session: Session):
    token = get_token(UserRole.VIEWER)
    headers = {"Authorization": f"Bearer {token}"}

    res = client.get("/api/recovery/intelligence/ml-governance/report", headers=headers)
    assert res.status_code == 200
    report = res.json()

    assert report["summary"]["governance_score"] > 90.0
    assert len(report["signature"]) == 64
    assert len(report["evidence_hash"]) == 64
    assert len(report["model_inventory"]) >= 5
    assert len(report["readiness_gates"]) == 22


# -----------------------------------------------------------------------------
# 14. Zero PII & Security Sanitization Tests
# -----------------------------------------------------------------------------


def test_zero_pii_across_all_governance_payloads(
    client: TestClient, db_session: Session
):
    token = get_token(UserRole.VIEWER)
    headers = {"Authorization": f"Bearer {token}"}

    endpoints = [
        "/api/recovery/intelligence/ml-governance/summary",
        "/api/recovery/intelligence/ml-governance/models",
        "/api/recovery/intelligence/ml-governance/models/recovery_probability/explainability",
        "/api/recovery/intelligence/ml-governance/models/recovery_probability/drift",
        "/api/recovery/intelligence/ml-governance/models/recovery_probability/fairness",
        "/api/recovery/intelligence/ml-governance/readiness-gates",
        "/api/recovery/intelligence/ml-governance/forensics",
    ]

    for ep in endpoints:
        res = client.get(ep, headers=headers)
        assert res.status_code == 200
        text = res.text.lower()
        assert "password" not in text
        assert "card_number" not in text
        assert "secret_key" not in text
        assert "aadhaar" not in text


# -----------------------------------------------------------------------------
# 15. RBAC & Security Boundary Enforcement Tests
# -----------------------------------------------------------------------------


def test_rbac_unauthenticated_access_rejected(client: TestClient, db_session: Session):
    res = client.get("/api/recovery/intelligence/ml-governance/summary")
    assert res.status_code in [401, 403]


def test_rbac_viewer_cannot_mutate_governance_state(
    client: TestClient, db_session: Session
):
    viewer_token = get_token(UserRole.VIEWER)
    headers = {"Authorization": f"Bearer {viewer_token}"}

    # Viewer cannot trigger model evaluation
    res_eval = client.post(
        "/api/recovery/intelligence/ml-governance/models/recovery_probability/evaluate",
        json={"evaluation_type": "OFFLINE", "sample_size": 1000},
        headers=headers,
    )
    assert res_eval.status_code == 403

    # Viewer cannot resolve incidents (requires ADMIN)
    res_resolve = client.post(
        "/api/recovery/intelligence/ml-governance/incidents/ML-INC-2026-001/resolve",
        headers=headers,
    )
    assert res_resolve.status_code == 403


# -----------------------------------------------------------------------------
# 16. Mathematical & Algorithm Unit Tests
# -----------------------------------------------------------------------------


def test_psi_calculation_mathematics():
    from app.services.ml_governance_service import MLGovernanceService

    # Identical distributions -> PSI == 0.0
    d1 = [0.2, 0.3, 0.5]
    psi_identical = MLGovernanceService.calculate_psi(d1, d1)
    assert psi_identical == 0.0

    # Slight shift -> small positive PSI
    d2 = [0.18, 0.32, 0.50]
    psi_shifted = MLGovernanceService.calculate_psi(d1, d2)
    assert 0.0 <= psi_shifted < 0.10

    # With zero values protected by epsilon
    d_zero = [0.0, 0.4, 0.6]
    psi_zero = MLGovernanceService.calculate_psi(d1, d_zero)
    assert psi_zero >= 0.0


def test_governance_score_normalization():
    from app.services.ml_governance_service import MLGovernanceService

    score = MLGovernanceService.compute_governance_score()
    assert isinstance(score, float)
    assert 0.0 <= score <= 100.0


def test_all_canonical_models_governance_profiles(
    client: TestClient, db_session: Session
):
    token = get_token(UserRole.VIEWER)
    headers = {"Authorization": f"Bearer {token}"}

    models = [
        "optimal_channel",
        "optimal_timing",
        "discount_sensitivity",
        "urgency_scorer",
    ]
    for m in models:
        res_p = client.get(
            f"/api/recovery/intelligence/ml-governance/models/{m}/performance",
            headers=headers,
        )
        assert res_p.status_code == 200
        assert res_p.json()["accuracy"] > 0.80

        res_d = client.get(
            f"/api/recovery/intelligence/ml-governance/models/{m}/drift",
            headers=headers,
        )
        assert res_d.status_code == 200
        assert res_d.json()["overall_status"] == "STABLE"

        res_r = client.get(
            f"/api/recovery/intelligence/ml-governance/models/{m}/risk", headers=headers
        )
        assert res_r.status_code == 200
        assert res_r.json()["total_score"] >= 80.0


def test_lineage_graph_dag_connectivity(client: TestClient, db_session: Session):
    token = get_token(UserRole.VIEWER)
    headers = {"Authorization": f"Bearer {token}"}

    res = client.get(
        "/api/recovery/intelligence/ml-governance/models/recovery_probability/lineage",
        headers=headers,
    )
    assert res.status_code == 200
    nodes = res.json()["nodes"]
    node_ids = {n["node_id"] for n in nodes}

    # Verify all parents exist in the node set
    for n in nodes:
        for p in n["parent_ids"]:
            assert p in node_ids, f"Orphan parent node reference: {p}"


def test_explainability_feature_attribution_weights(
    client: TestClient, db_session: Session
):
    token = get_token(UserRole.VIEWER)
    headers = {"Authorization": f"Bearer {token}"}

    res = client.get(
        "/api/recovery/intelligence/ml-governance/models/recovery_probability/explainability",
        headers=headers,
    )
    assert res.status_code == 200
    features = res.json()["top_features"]
    total_pct = sum(f["relative_percentage"] for f in features)
    assert 95.0 <= total_pct <= 105.0


def test_calibration_reliability_diagram_bins(client: TestClient, db_session: Session):
    token = get_token(UserRole.VIEWER)
    headers = {"Authorization": f"Bearer {token}"}

    res = client.get(
        "/api/recovery/intelligence/ml-governance/models/recovery_probability/calibration",
        headers=headers,
    )
    assert res.status_code == 200
    bins = res.json()["bins_data"]
    assert len(bins) == 5
    for b in bins:
        assert "bin" in b
        assert 0.0 <= b["mean_predicted"] <= 1.0
        assert 0.0 <= b["observed_fraction"] <= 1.0


def test_promotion_advisory_invariants(client: TestClient, db_session: Session):
    token = get_token(UserRole.OPERATOR)
    headers = {"Authorization": f"Bearer {token}"}

    res = client.post(
        "/api/recovery/intelligence/ml-governance/models/recovery_probability/promotion-evaluation",
        json={"candidate_version": "v1.2-rc", "justification": "Test promotion"},
        headers=headers,
    )
    assert res.status_code == 201
    data = res.json()
    assert data["human_approval_required"] is True
    assert data["rollback_ready"] is True


def test_rollback_switchover_timing_sla(client: TestClient, db_session: Session):
    token = get_token(UserRole.VIEWER)
    headers = {"Authorization": f"Bearer {token}"}

    res = client.get(
        "/api/recovery/intelligence/ml-governance/models/recovery_probability/rollback",
        headers=headers,
    )
    assert res.status_code == 200
    data = res.json()
    assert data["readiness_status"] == "READY"
    assert data["rollback_time_seconds"] <= 30
    assert data["authorization_path"] == "HUMAN_ADMIN_REQUIRED"


def test_financial_path_forensics_all_stages_isolated(
    client: TestClient, db_session: Session
):
    token = get_token(UserRole.VIEWER)
    headers = {"Authorization": f"Bearer {token}"}

    res = client.get(
        "/api/recovery/intelligence/ml-governance/forensics", headers=headers
    )
    assert res.status_code == 200
    data = res.json()
    assert data["financial_isolation_verified"] is True
    assert data["policy_engine_supremacy_verified"] is True
    assert data["action_dispatcher_calls"] == 0
    assert data["razorpay_provider_calls"] == 0
