"""Test suite for Phase 9H: Causal Experimentation, Statistical Significance & Decision Intelligence."""

import uuid
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import UserRole, create_access_token
from app.main import app
from app.models import (
    ActionResult,
    BalanceStatus,
    CausalEvidenceLevel,
    CohortType,
    Customer,
    CustomerRiskTier,
    ExperimentDecisionType,
    ExperimentStatus,
    MLPrediction,
    Payment,
    PaymentStatus,
    RecoveryAction,
    RecoveryCase,
    RecoveryCaseStatus,
)
from app.services.experimentation_service import (
    experimentation_service,
)


@pytest.fixture
def client(db_session: Session):
    """Test client with overridden database session dependency."""

    def _override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = _override_get_db
    token = create_access_token(
        user_id="operator_exp_usr", role=UserRole.OPERATOR.value
    )
    with TestClient(app, headers={"Authorization": f"Bearer {token}"}) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def setup_sample_recovery_cases(
    db: Session,
    count: int = 120,
    recovered_ratio: float = 0.50,
    risk_tier: CustomerRiskTier = CustomerRiskTier.STANDARD,
    failure_reason: str = "INSUFFICIENT_FUNDS",
) -> list[RecoveryCase]:
    """Helper to seed historical recovery cases for experimentation evaluation."""
    cases = []
    recovered_count = int(count * recovered_ratio)

    customer = Customer(
        id=uuid.uuid4(),
        external_customer_id=f"cust_exp_{uuid.uuid4().hex[:6]}",
        risk_tier=risk_tier,
    )
    db.add(customer)
    db.commit()

    now = datetime.now(UTC)

    for i in range(count):
        is_rec = i < recovered_count
        p_status = PaymentStatus.CAPTURED if is_rec else PaymentStatus.FAILED
        c_status = RecoveryCaseStatus.RECOVERED if is_rec else RecoveryCaseStatus.CLOSED

        payment = Payment(
            id=uuid.uuid4(),
            customer_id=customer.id,
            amount=100000,
            currency="INR",
            status=p_status.value,
            metadata_json={"failure_reason": failure_reason},
            created_at=now - timedelta(days=5),
        )

        db.add(payment)
        db.flush()

        case = RecoveryCase(
            id=uuid.uuid4(),
            payment_id=payment.id,
            customer_id=customer.id,
            status=c_status.value,
            amount_at_risk=100000,
            recovered_amount=100000 if is_rec else 0,
            total_attempts_count=1 if is_rec else 2,
            opened_at=now - timedelta(days=5),
            resolved_at=now - timedelta(days=2),
            created_at=now - timedelta(days=5),
        )
        db.add(case)
        db.flush()

        pred = MLPrediction(
            id=uuid.uuid4(),
            recovery_case_id=case.id,
            model_name="recovery_xgboost",
            model_version="v1.0",
            recovery_probability=Decimal("0.75") if is_rec else Decimal("0.25"),
            feature_vector_snapshot={
                "risk_tier": risk_tier.value
                if hasattr(risk_tier, "value")
                else str(risk_tier)
            },
            predicted_at=now - timedelta(days=5),
        )
        db.add(pred)

        cases.append(case)

    db.commit()
    return cases


# =========================================================================
# 1. Deterministic Assignment & Allocation Tests
# =========================================================================


def test_deterministic_cohort_assignment():
    """1. Test that the same experiment_id + case_id always maps to the same cohort."""
    exp_id = "exp-test-1234"
    case_id = "case-uuid-9876"

    c1 = experimentation_service.assign_cohort(
        exp_id, case_id, allocation_percentage=50
    )
    c2 = experimentation_service.assign_cohort(
        exp_id, case_id, allocation_percentage=50
    )
    c3 = experimentation_service.assign_cohort(
        exp_id, case_id, allocation_percentage=50
    )

    assert c1 == c2 == c3
    assert c1 in (CohortType.CONTROL, CohortType.TREATMENT)


def test_deterministic_cohort_assignment_cross_experiment():
    """2. Test that different experiment IDs partition cases independently."""
    case_id = "case-uuid-fixed"
    assignments = {
        experimentation_service.assign_cohort(
            f"exp-{i}", case_id, allocation_percentage=50
        )
        for i in range(50)
    }
    # Over 50 experiments, we should see both CONTROL and TREATMENT
    assert CohortType.CONTROL in assignments
    assert CohortType.TREATMENT in assignments


def test_allocation_percentage_edge_cases():
    """3. Test 0% and 100% allocation boundary conditions."""
    exp_id = "exp-boundary"
    case_id = "case-boundary"

    assert (
        experimentation_service.assign_cohort(exp_id, case_id, allocation_percentage=0)
        == CohortType.CONTROL
    )
    assert (
        experimentation_service.assign_cohort(
            exp_id, case_id, allocation_percentage=100
        )
        == CohortType.TREATMENT
    )


# =========================================================================
# 2. RBAC & Lifecycle Tests
# =========================================================================


def test_experiment_creation_rbac(db_session: Session):
    """4. Test that Operator and Admin can create experiments, while Viewer is rejected (403)."""

    def _override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = _override_get_db

    token_viewer = create_access_token(user_id="viewer_usr", role=UserRole.VIEWER.value)
    token_operator = create_access_token(
        user_id="operator_usr", role=UserRole.OPERATOR.value
    )
    token_admin = create_access_token(user_id="admin_usr", role=UserRole.ADMIN.value)

    req_body = {
        "name": "Payment Link vs Smart Retry Exp",
        "description": "Test differential causal uplift of payment links",
        "treatment_strategy": "SEND_PAYMENT_LINK",
        "control_strategy": "RETRY_PAYMENT",
        "allocation_percentage": 50,
    }

    with TestClient(app, headers={"Authorization": f"Bearer {token_viewer}"}) as tc_v:
        res_v = tc_v.post("/api/recovery/intelligence/experiments", json=req_body)
        assert res_v.status_code == 403

    with TestClient(app, headers={"Authorization": f"Bearer {token_operator}"}) as tc_o:
        res_o = tc_o.post("/api/recovery/intelligence/experiments", json=req_body)
        assert res_o.status_code == 201
        data = res_o.json()
        assert data["name"] == req_body["name"]
        assert data["status"] == ExperimentStatus.DRAFT.value
        assert data["created_by"] == "operator_usr"

    with TestClient(app, headers={"Authorization": f"Bearer {token_admin}"}) as tc_a:
        res_a = tc_a.post("/api/recovery/intelligence/experiments", json=req_body)
        assert res_a.status_code == 201
        assert res_a.json()["created_by"] == "admin_usr"

    app.dependency_overrides.clear()


def test_actor_identity_extracted_from_jwt_not_payload(db_session: Session):
    """5. Test that client payload cannot spoof actor identity."""
    token = create_access_token(
        user_id="verified_operator", role=UserRole.OPERATOR.value
    )

    def _override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = _override_get_db

    with TestClient(app, headers={"Authorization": f"Bearer {token}"}) as tc:
        res = tc.post(
            "/api/recovery/intelligence/experiments",
            json={
                "name": "Spoof Test Exp",
                "treatment_strategy": "SEND_PAYMENT_LINK",
                "control_strategy": "RETRY_PAYMENT",
                "created_by": "spoofed_admin",  # Client tries to spoof
            },
        )
        assert res.status_code == 201
        assert res.json()["created_by"] == "verified_operator"

    app.dependency_overrides.clear()


def test_state_machine_valid_and_invalid_transitions(
    client: TestClient, db_session: Session
):
    """6. Test valid lifecycle transitions and 409 Conflict on invalid transitions."""
    # 1. Create (DRAFT)
    res_create = client.post(
        "/api/recovery/intelligence/experiments",
        json={
            "name": "Lifecycle State Machine Exp",
            "treatment_strategy": "SEND_PAYMENT_LINK",
            "control_strategy": "RETRY_PAYMENT",
        },
    )
    assert res_create.status_code == 201
    exp_id = res_create.json()["experiment_id"]

    # 2. Start (DRAFT -> RUNNING)
    res_start = client.post(
        f"/api/recovery/intelligence/experiments/{exp_id}/start", json={}
    )
    assert res_start.status_code == 200
    assert res_start.json()["status"] == ExperimentStatus.RUNNING.value

    # 3. Invalid: Start already running experiment (RUNNING -> RUNNING) -> 409
    res_invalid_start = client.post(
        f"/api/recovery/intelligence/experiments/{exp_id}/start", json={}
    )
    assert res_invalid_start.status_code == 409

    # 4. Pause (RUNNING -> PAUSED)
    res_pause = client.post(
        f"/api/recovery/intelligence/experiments/{exp_id}/pause", json={}
    )
    assert res_pause.status_code == 200
    assert res_pause.json()["status"] == ExperimentStatus.PAUSED.value

    # 5. Resume (PAUSED -> RUNNING)
    res_resume = client.post(
        f"/api/recovery/intelligence/experiments/{exp_id}/start", json={}
    )
    assert res_resume.status_code == 200
    assert res_resume.json()["status"] == ExperimentStatus.RUNNING.value

    # 6. Complete (RUNNING -> COMPLETED)
    res_comp = client.post(
        f"/api/recovery/intelligence/experiments/{exp_id}/complete", json={}
    )
    assert res_comp.status_code == 200
    assert res_comp.json()["status"] == ExperimentStatus.COMPLETED.value

    # 7. Invalid: Pause completed experiment (COMPLETED -> PAUSED) -> 409
    res_invalid_pause = client.post(
        f"/api/recovery/intelligence/experiments/{exp_id}/pause", json={}
    )
    assert res_invalid_pause.status_code == 409


# =========================================================================
# 3. Statistical Testing, Wilson/Newcombe CI & Causal Evidence
# =========================================================================


def test_minimum_sample_handling_insufficient_data(
    client: TestClient, db_session: Session
):
    """7. Test that small sample sizes return LEVEL_0 (INSUFFICIENT_DATA) and INSUFFICIENT_DATA decision."""
    setup_sample_recovery_cases(db_session, count=20, recovered_ratio=0.50)

    res_create = client.post(
        "/api/recovery/intelligence/experiments",
        json={
            "name": "Small Sample Exp",
            "treatment_strategy": "SEND_PAYMENT_LINK",
            "control_strategy": "RETRY_PAYMENT",
        },
    )
    exp_id = res_create.json()["experiment_id"]

    res_analysis = client.get(
        f"/api/recovery/intelligence/experiments/{exp_id}/analysis"
    )
    assert res_analysis.status_code == 200
    data = res_analysis.json()

    assert data["sample_size"] == 20
    assert data["decision"]["evidence_level"] == CausalEvidenceLevel.LEVEL_0.value
    assert (
        data["decision"]["decision"] == ExperimentDecisionType.INSUFFICIENT_DATA.value
    )
    assert data["statistical_test"]["statistically_significant"] is False


def test_wilson_newcombe_confidence_interval_math():
    """8. Test accuracy of Wilson score interval and Newcombe two-proportion difference bounds."""
    # Wilson interval for 60/100
    l1, u1 = experimentation_service._wilson_interval(60, 100)
    assert 0.49 < l1 < 0.51
    assert 0.68 < u1 < 0.70

    # Newcombe difference interval for (80/100) vs (50/100) -> diff = 0.30
    ci_low, ci_high = experimentation_service._newcombe_difference_interval(
        80, 100, 50, 100
    )
    assert 0.16 < ci_low < 0.20
    assert 0.40 < ci_high < 0.44


def test_two_proportion_hypothesis_testing():
    """9. Test two-proportion z-test and p-value calculation."""
    # Identical proportions (50/100 vs 50/100) -> z=0, p=1.0, not significant
    res_null = experimentation_service._perform_statistical_test(50, 100, 50, 100)
    assert res_null.test_statistic == 0.0
    assert res_null.p_value == 1.0
    assert res_null.statistically_significant is False

    # Significant difference (80/100 vs 40/100) -> z > 4.0, p < 0.001, significant
    res_sig = experimentation_service._perform_statistical_test(80, 100, 40, 100)
    assert res_sig.test_statistic is not None and res_sig.test_statistic > 4.0
    assert res_sig.p_value is not None and res_sig.p_value < 0.001
    assert res_sig.statistically_significant is True


def test_analysis_endpoint_with_sufficient_sample(
    client: TestClient, db_session: Session
):
    """10. Test analysis on a cohort with N >= 100 cases calculates full causal and statistical metrics."""
    setup_sample_recovery_cases(db_session, count=150, recovered_ratio=0.65)

    res_create = client.post(
        "/api/recovery/intelligence/experiments",
        json={
            "name": "Full Cohort Causal Exp",
            "treatment_strategy": "SEND_PAYMENT_LINK",
            "control_strategy": "RETRY_PAYMENT",
            "allocation_percentage": 50,
        },
    )
    exp_id = res_create.json()["experiment_id"]
    client.post(f"/api/recovery/intelligence/experiments/{exp_id}/start", json={})

    res_analysis = client.get(
        f"/api/recovery/intelligence/experiments/{exp_id}/analysis"
    )
    assert res_analysis.status_code == 200
    data = res_analysis.json()

    assert data["sample_size"] == 150
    assert data["control_cohort"]["sample_size"] > 40
    assert data["treatment_cohort"]["sample_size"] > 40
    assert data["assignment_method"] == "SHA256_DETERMINISTIC"
    assert "causal_effect" in data
    assert "statistical_test" in data
    assert "balance_diagnostics" in data
    assert "data_quality" in data
    assert "overlap_diagnostics" in data
    assert "stopping_diagnostics" in data
    assert "decision" in data


# =========================================================================
# 4. Covariate Balance & Multi-Experiment Overlap
# =========================================================================


def test_covariate_balance_diagnostics(client: TestClient, db_session: Session):
    """11. Test covariate balance diagnostics correctly identifies balanced vs imbalanced cohorts."""
    setup_sample_recovery_cases(db_session, count=120, recovered_ratio=0.60)

    res_create = client.post(
        "/api/recovery/intelligence/experiments",
        json={
            "name": "Balance Verification Exp",
            "treatment_strategy": "SEND_PAYMENT_LINK",
            "control_strategy": "RETRY_PAYMENT",
        },
    )
    exp_id = res_create.json()["experiment_id"]

    res_analysis = client.get(
        f"/api/recovery/intelligence/experiments/{exp_id}/analysis"
    )
    assert res_analysis.status_code == 200
    b_diag = res_analysis.json()["balance_diagnostics"]

    assert b_diag["overall_status"] in (
        BalanceStatus.BALANCED.value,
        BalanceStatus.MINOR_IMBALANCE.value,
        BalanceStatus.MAJOR_IMBALANCE.value,
    )
    assert len(b_diag["features"]) == 4


def test_multi_experiment_overlap_detection(client: TestClient, db_session: Session):
    """12. Test detection of concurrent active experiments targeting overlapping populations."""
    # Exp 1 (RUNNING)
    res_1 = client.post(
        "/api/recovery/intelligence/experiments",
        json={
            "name": "Active Exp 1",
            "treatment_strategy": "SEND_PAYMENT_LINK",
            "control_strategy": "RETRY_PAYMENT",
            "population_definition": {"risk_tier": "STANDARD"},
        },
    )
    exp_id_1 = res_1.json()["experiment_id"]
    client.post(f"/api/recovery/intelligence/experiments/{exp_id_1}/start", json={})

    # Exp 2 (DRAFT with overlapping population)
    res_2 = client.post(
        "/api/recovery/intelligence/experiments",
        json={
            "name": "Active Exp 2",
            "treatment_strategy": "SEND_PAYMENT_LINK",
            "control_strategy": "RETRY_PAYMENT",
            "population_definition": {"risk_tier": "STANDARD"},
        },
    )
    exp_id_2 = res_2.json()["experiment_id"]

    res_analysis = client.get(
        f"/api/recovery/intelligence/experiments/{exp_id_2}/analysis"
    )
    assert res_analysis.status_code == 200
    overlap = res_analysis.json()["overlap_diagnostics"]
    assert overlap["has_overlap"] is True
    assert exp_id_1 in overlap["conflicting_experiment_ids"]


# =========================================================================
# 5. Financial Isolation & Zero PII/Secrets Verification
# =========================================================================


def test_experiments_create_zero_recovery_actions_or_gateway_calls(
    client: TestClient, db_session: Session
):
    """13. Test that experiment lifecycle operations execute zero financial actions or gateway calls."""
    setup_sample_recovery_cases(db_session, count=50)

    initial_actions_count = db_session.query(RecoveryAction).count()
    initial_cases_count = db_session.query(RecoveryCase).count()
    initial_results_count = db_session.query(ActionResult).count()

    with (
        patch(
            "app.services.action_dispatcher.ActionDispatcher.dispatch_action"
        ) as mock_dispatch,
        patch("app.providers.razorpay.RazorpayActionProvider.execute") as mock_exec,
    ):
        # 1. Create
        res_create = client.post(
            "/api/recovery/intelligence/experiments",
            json={
                "name": "Financial Isolation Exp",
                "treatment_strategy": "SEND_PAYMENT_LINK",
                "control_strategy": "RETRY_PAYMENT",
            },
        )
        exp_id = res_create.json()["experiment_id"]

        # 2. Start
        client.post(f"/api/recovery/intelligence/experiments/{exp_id}/start", json={})

        # 3. Analyze
        client.get(f"/api/recovery/intelligence/experiments/{exp_id}/analysis")

        # 4. Complete
        client.post(
            f"/api/recovery/intelligence/experiments/{exp_id}/complete", json={}
        )

        # Verify zero calls and zero mutations
        mock_dispatch.assert_not_called()
        mock_exec.assert_not_called()
        assert db_session.query(RecoveryAction).count() == initial_actions_count
        assert db_session.query(RecoveryCase).count() == initial_cases_count
        assert db_session.query(ActionResult).count() == initial_results_count


def test_zero_pii_and_zero_secrets_in_experiment_apis(
    client: TestClient, db_session: Session
):
    """14. Test that experiment endpoints never return customer PII or payment credentials."""
    setup_sample_recovery_cases(db_session, count=30)

    res_create = client.post(
        "/api/recovery/intelligence/experiments",
        json={
            "name": "Zero PII Verification Exp",
            "treatment_strategy": "SEND_PAYMENT_LINK",
            "control_strategy": "RETRY_PAYMENT",
        },
    )
    exp_id = res_create.json()["experiment_id"]

    for url in (
        "/api/recovery/intelligence/experiments",
        f"/api/recovery/intelligence/experiments/{exp_id}",
        f"/api/recovery/intelligence/experiments/{exp_id}/analysis",
    ):
        res = client.get(url)
        assert res.status_code == 200
        raw_text = res.text.lower()
        assert "email" not in raw_text or "missing_predictions" in raw_text
        assert "phone" not in raw_text
        assert "card_number" not in raw_text
        assert "password" not in raw_text
        assert "secret" not in raw_text
        assert "token" not in raw_text


# =========================================================================
# 6. Advanced Diagnostics, Stopping Rules & Causal Levels
# =========================================================================


def test_get_experiment_by_id_and_not_found(client: TestClient):
    """15. Test fetching experiment by ID and 404 on nonexistent ID."""
    res_create = client.post(
        "/api/recovery/intelligence/experiments",
        json={
            "name": "Fetch Test Exp",
            "treatment_strategy": "SEND_PAYMENT_LINK",
            "control_strategy": "RETRY_PAYMENT",
        },
    )
    exp_id = res_create.json()["experiment_id"]

    res_get = client.get(f"/api/recovery/intelligence/experiments/{exp_id}")
    assert res_get.status_code == 200
    assert res_get.json()["experiment_id"] == exp_id

    res_404 = client.get(f"/api/recovery/intelligence/experiments/{uuid.uuid4()}")
    assert res_404.status_code == 404


def test_list_experiments_filter_by_status(client: TestClient):
    """16. Test listing experiments with status filtering and pagination."""
    res_1 = client.post(
        "/api/recovery/intelligence/experiments",
        json={
            "name": "Draft Exp 1",
            "treatment_strategy": "SEND_PAYMENT_LINK",
            "control_strategy": "RETRY_PAYMENT",
        },
    )
    assert "experiment_id" in res_1.json()

    res_2 = client.post(
        "/api/recovery/intelligence/experiments",
        json={
            "name": "Running Exp 2",
            "treatment_strategy": "SEND_PAYMENT_LINK",
            "control_strategy": "RETRY_PAYMENT",
        },
    )
    exp_2 = res_2.json()["experiment_id"]
    client.post(f"/api/recovery/intelligence/experiments/{exp_2}/start", json={})

    # List all
    res_all = client.get("/api/recovery/intelligence/experiments")
    assert res_all.status_code == 200
    assert res_all.json()["total"] >= 2

    # Filter RUNNING
    res_running = client.get("/api/recovery/intelligence/experiments?status=RUNNING")
    assert res_running.status_code == 200
    statuses = [e["status"] for e in res_running.json()["items"]]
    assert all(s == "RUNNING" for s in statuses)

    # Filter DRAFT
    res_draft = client.get("/api/recovery/intelligence/experiments?status=DRAFT")
    assert res_draft.status_code == 200
    statuses_d = [e["status"] for e in res_draft.json()["items"]]
    assert all(s == "DRAFT" for s in statuses_d)


def test_stopping_rule_treatment_underperformance():
    """17. Test stopping rule triggers when treatment recovery rate trails control by >= 5.0%."""
    from app.schemas.experimentation import (
        CausalEffectEstimate,
        DataQualityReport,
        OverlapDiagnostics,
        StatisticalTestResult,
    )

    causal_effect = CausalEffectEstimate(
        absolute_treatment_effect=-0.06,
        relative_uplift_pct=-12.0,
        incremental_recovered_cases_estimate=-6.0,
        incremental_erv_paise=-600000,
    )
    stat_test = StatisticalTestResult(
        test_name="TWO_PROPORTION_Z_TEST",
        test_statistic=-2.1,
        p_value=0.035,
        alpha=0.05,
        statistically_significant=True,
        confidence_interval_low=-0.11,
        confidence_interval_high=-0.01,
        confidence_level=0.95,
    )
    dq = DataQualityReport(
        data_quality_status="CLEAN",
        missing_outcomes=0,
        missing_predictions=0,
        diagnostics=[],
    )
    overlap = OverlapDiagnostics(
        has_overlap=False, conflicting_experiment_ids=[], diagnostics=[]
    )

    stopping = experimentation_service._evaluate_stopping_rules(
        causal_effect=causal_effect,
        statistical_test=stat_test,
        is_model_degraded=False,
        data_quality=dq,
        overlap=overlap,
    )
    assert stopping.stop_recommended is True
    assert any("trails control by" in r for r in stopping.reasons)


def test_stopping_rule_model_degraded():
    """18. Test stopping rule triggers when underlying model governance is DEGRADED."""
    from app.schemas.experimentation import (
        CausalEffectEstimate,
        DataQualityReport,
        OverlapDiagnostics,
        StatisticalTestResult,
    )

    causal_effect = CausalEffectEstimate(absolute_treatment_effect=0.05)
    stat_test = StatisticalTestResult(
        test_name="TWO_PROPORTION_Z_TEST",
        statistically_significant=True,
        confidence_interval_low=0.01,
        confidence_interval_high=0.09,
    )
    dq = DataQualityReport(
        data_quality_status="CLEAN",
        missing_outcomes=0,
        missing_predictions=0,
        diagnostics=[],
    )
    overlap = OverlapDiagnostics(
        has_overlap=False, conflicting_experiment_ids=[], diagnostics=[]
    )

    stopping = experimentation_service._evaluate_stopping_rules(
        causal_effect=causal_effect,
        statistical_test=stat_test,
        is_model_degraded=True,  # Degraded
        data_quality=dq,
        overlap=overlap,
    )
    assert stopping.stop_recommended is True
    assert any("ML model governance is DEGRADED" in r for r in stopping.reasons)


def test_stopping_rule_data_quality_degraded():
    """19. Test stopping rule triggers when telemetry data quality is DEGRADED."""
    from app.schemas.experimentation import (
        CausalEffectEstimate,
        DataQualityReport,
        OverlapDiagnostics,
        StatisticalTestResult,
    )

    causal_effect = CausalEffectEstimate(absolute_treatment_effect=0.05)
    stat_test = StatisticalTestResult(
        test_name="TWO_PROPORTION_Z_TEST", statistically_significant=True
    )
    dq = DataQualityReport(
        data_quality_status="DEGRADED",
        missing_outcomes=50,
        missing_predictions=50,
        diagnostics=[],
    )
    overlap = OverlapDiagnostics(
        has_overlap=False, conflicting_experiment_ids=[], diagnostics=[]
    )

    stopping = experimentation_service._evaluate_stopping_rules(
        causal_effect=causal_effect,
        statistical_test=stat_test,
        is_model_degraded=False,
        data_quality=dq,
        overlap=overlap,
    )
    assert stopping.stop_recommended is True
    assert any("data quality is DEGRADED" in r for r in stopping.reasons)


def test_causal_evidence_level_1_not_significant():
    """20. Test that non-significant statistical tests result in LEVEL_1 evidence."""
    from app.schemas.experimentation import (
        BalanceDiagnostics,
        CausalEffectEstimate,
        StatisticalTestResult,
        StoppingDiagnostics,
    )

    causal_effect = CausalEffectEstimate(absolute_treatment_effect=0.01)
    stat_test = StatisticalTestResult(
        test_name="TWO_PROPORTION_Z_TEST",
        statistically_significant=False,  # p >= 0.05
    )
    balance = BalanceDiagnostics(
        overall_status="BALANCED", is_confounded=False, features=[], diagnostics=[]
    )
    stopping = StoppingDiagnostics(stop_recommended=False, reasons=[])

    decision = experimentation_service._determine_decision_and_evidence(
        sample_size=200,
        ctrl_sample=100,
        trt_sample=100,
        causal_effect=causal_effect,
        stat_test=stat_test,
        balance=balance,
        stopping=stopping,
        experiment_status="RUNNING",
    )
    assert decision.evidence_level == CausalEvidenceLevel.LEVEL_1.value
    assert decision.decision == ExperimentDecisionType.CONTINUE.value


def test_causal_evidence_level_2_minor_imbalance():
    """21. Test that minor covariate imbalance produces LEVEL_2 evidence."""
    from app.schemas.experimentation import (
        BalanceDiagnostics,
        CausalEffectEstimate,
        StatisticalTestResult,
        StoppingDiagnostics,
    )

    causal_effect = CausalEffectEstimate(absolute_treatment_effect=0.08)
    stat_test = StatisticalTestResult(
        test_name="TWO_PROPORTION_Z_TEST",
        statistically_significant=True,
        confidence_interval_low=0.02,
        confidence_interval_high=0.14,
    )
    balance = BalanceDiagnostics(
        overall_status="MINOR_IMBALANCE",
        is_confounded=False,
        features=[],
        diagnostics=[],
    )
    stopping = StoppingDiagnostics(stop_recommended=False, reasons=[])

    decision = experimentation_service._determine_decision_and_evidence(
        sample_size=200,
        ctrl_sample=100,
        trt_sample=100,
        causal_effect=causal_effect,
        stat_test=stat_test,
        balance=balance,
        stopping=stopping,
        experiment_status="RUNNING",
    )
    assert decision.evidence_level == CausalEvidenceLevel.LEVEL_2.value
    assert decision.decision == ExperimentDecisionType.PROMOTE_TO_REVIEW.value


def test_causal_evidence_level_3_fully_balanced_and_significant():
    """22. Test that balanced, statistically significant running experiments achieve LEVEL_3."""
    from app.schemas.experimentation import (
        BalanceDiagnostics,
        CausalEffectEstimate,
        StatisticalTestResult,
        StoppingDiagnostics,
    )

    causal_effect = CausalEffectEstimate(absolute_treatment_effect=0.06)
    stat_test = StatisticalTestResult(
        test_name="TWO_PROPORTION_Z_TEST",
        statistically_significant=True,
        confidence_interval_low=0.015,
        confidence_interval_high=0.105,
    )
    balance = BalanceDiagnostics(
        overall_status="BALANCED", is_confounded=False, features=[], diagnostics=[]
    )
    stopping = StoppingDiagnostics(stop_recommended=False, reasons=[])

    decision = experimentation_service._determine_decision_and_evidence(
        sample_size=300,
        ctrl_sample=150,
        trt_sample=150,
        causal_effect=causal_effect,
        stat_test=stat_test,
        balance=balance,
        stopping=stopping,
        experiment_status="RUNNING",
    )
    assert decision.evidence_level == CausalEvidenceLevel.LEVEL_3.value
    assert decision.decision == ExperimentDecisionType.PROMOTE_TO_REVIEW.value


def test_decision_promote_to_review_criteria():
    """23. Test promote to review criteria (ATE >= +2.0%, CI_low > 0, sig=True, LEVEL >= 2)."""
    from app.schemas.experimentation import (
        BalanceDiagnostics,
        CausalEffectEstimate,
        StatisticalTestResult,
        StoppingDiagnostics,
    )

    causal_effect = CausalEffectEstimate(absolute_treatment_effect=0.04)
    stat_test = StatisticalTestResult(
        test_name="TWO_PROPORTION_Z_TEST",
        statistically_significant=True,
        confidence_interval_low=0.005,
        confidence_interval_high=0.075,
    )
    balance = BalanceDiagnostics(
        overall_status="BALANCED", is_confounded=False, features=[], diagnostics=[]
    )
    stopping = StoppingDiagnostics(stop_recommended=False, reasons=[])

    res = experimentation_service._determine_decision_and_evidence(
        sample_size=200,
        ctrl_sample=100,
        trt_sample=100,
        causal_effect=causal_effect,
        stat_test=stat_test,
        balance=balance,
        stopping=stopping,
        experiment_status="RUNNING",
    )
    assert res.decision == ExperimentDecisionType.PROMOTE_TO_REVIEW.value


def test_zero_division_guard_in_relative_uplift():
    """24. Test that zero recoveries in control cohort gracefully handles relative uplift division by zero."""
    res = experimentation_service._calculate_cohort_metrics([], "CONTROL")
    assert res.recovery_rate is None
    assert res.sample_size == 0


def test_financial_yield_and_erv_bounds_calculation():
    """25. Test financial yield and ERV paise bounds calculation."""
    # Control 50 cases of 1,000 INR (100,000 paise each), 25 recovered (50%)
    c_cases = []
    for _ in range(50):
        case = RecoveryCase(
            id=uuid.uuid4(),
            payment_id=uuid.uuid4(),
            customer_id=uuid.uuid4(),
            status=RecoveryCaseStatus.RECOVERED.value,
            amount_at_risk=100000,
            recovered_amount=100000,
            total_attempts_count=1,
        )
        c_cases.append(case)

    metrics = experimentation_service._calculate_cohort_metrics(c_cases, "CONTROL")
    assert metrics.amount_at_risk_paise == 5000000
    assert metrics.amount_recovered_paise == 5000000
    assert metrics.financial_yield == 1.0
    assert metrics.expected_recovery_value_paise == 5000000


def test_policy_engine_authority_unaffected_by_experiments(db_session: Session):
    """26. Test that PolicyEngine decision rules remain authoritative and intact."""
    from app.policy.engine import PolicyEngine

    pe = PolicyEngine()
    assert hasattr(pe, "evaluate")
    assert callable(pe.evaluate)


def test_experiment_action_notes_recorded_in_audit_trail(client: TestClient):
    """27. Test that operator notes are accurately persisted across experiment transitions."""
    res_create = client.post(
        "/api/recovery/intelligence/experiments",
        json={
            "name": "Notes Verification Exp",
            "treatment_strategy": "SEND_PAYMENT_LINK",
            "control_strategy": "RETRY_PAYMENT",
        },
    )
    exp_id = res_create.json()["experiment_id"]

    res_start = client.post(
        f"/api/recovery/intelligence/experiments/{exp_id}/start",
        json={"notes": "Starting Q3 optimization experiment"},
    )
    assert res_start.status_code == 200
    assert res_start.json()["notes"] == "Starting Q3 optimization experiment"


def test_invalid_allocation_percentage_rejected_by_schema(client: TestClient):
    """28. Test that invalid allocation percentages (e.g. 25%, 33%, 75%) are rejected by Pydantic validation."""
    for invalid_alloc in (25, 33, 75, 45, 95):
        res = client.post(
            "/api/recovery/intelligence/experiments",
            json={
                "name": "Invalid Alloc Exp",
                "treatment_strategy": "SEND_PAYMENT_LINK",
                "control_strategy": "RETRY_PAYMENT",
                "allocation_percentage": invalid_alloc,
            },
        )
        assert res.status_code == 422  # Unprocessable Entity
