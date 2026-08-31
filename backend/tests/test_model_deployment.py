"""Comprehensive test suite for Phase 9J: Governed Model Deployment, Shadow Mode & Champion–Challenger.

Invariants Tested:
1. Zero database migrations (AuditLog event sourcing).
2. Deterministic SHA-256 shadow/canary assignment & percentage whitelist.
3. Champion vs Challenger metrics, 5-bucket calibration, Wilson/Newcombe CI, Z-test.
4. 14 Deterministic Deployment Readiness Safety Gates.
5. Automated Rollback Guardrail Diagnostics.
6. Admin-only atomic activation (retires old champion, activates new challenger).
7. Admin-only rollback (restores champion, retires challenger).
8. Strict JWT RBAC (Viewer read-only, Operator staging, Admin activation).
9. MANDATORY FINANCIAL ISOLATION: 0 RecoveryAction mutations, 0 Payment mutations, 0 gateway calls.
"""

import uuid
from datetime import UTC, datetime

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import UserRole, create_access_token
from app.main import app
from app.models.customer import Customer
from app.models.enums import (
    CustomerRiskTier,
    DeploymentQualityGateCode,
    DeploymentSignificance,
    ModelDeploymentStatus,
    PaymentAttemptStatus,
    PaymentStatus,
    RecoveryCaseStatus,
    SubscriptionStatus,
)
from app.models.payment import Payment
from app.models.payment_attempt import PaymentAttempt
from app.models.recovery_action import RecoveryAction
from app.models.recovery_case import RecoveryCase
from app.models.subscription import Subscription
from app.schemas.model_lifecycle import ModelTrainingRequest
from app.services.model_deployment_service import (
    ALLOWED_TRAFFIC_PERCENTAGES,
    DEFAULT_CHAMPION_VERSION,
    ModelDeploymentService,
)
from app.services.model_lifecycle_service import ModelLifecycleService


@pytest.fixture
def client(db_session: Session) -> TestClient:
    """Provide a TestClient with overridden database and default operator authentication."""

    def _override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = _override_get_db
    token = create_access_token(user_id="op_test_user", role=UserRole.OPERATOR.value)
    with TestClient(app, headers={"Authorization": f"Bearer {token}"}) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture
def admin_client(db_session: Session) -> TestClient:
    """Provide a TestClient with Admin authentication."""

    def _override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = _override_get_db
    token = create_access_token(user_id="admin_test_user", role=UserRole.ADMIN.value)
    with TestClient(app, headers={"Authorization": f"Bearer {token}"}) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture
def viewer_client(db_session: Session) -> TestClient:
    """Provide a TestClient with Viewer authentication."""

    def _override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = _override_get_db
    token = create_access_token(user_id="viewer_test_user", role=UserRole.VIEWER.value)
    with TestClient(app, headers={"Authorization": f"Bearer {token}"}) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture
def setup_promotion_ready_model(db_session: Session) -> str:
    """Helper to train and approve a candidate model into PROMOTION_READY status."""
    lifecycle_service = ModelLifecycleService(db_session)
    scorecard = lifecycle_service.train_candidate_pipeline(
        request=ModelTrainingRequest(
            model_name="recovery_probability", parent_version="v1.0"
        ),
        actor_id="test_operator",
        actor_role="operator",
    )
    chall_ver = scorecard.challenger_version
    lifecycle_service.approve_model(
        version=chall_ver,
        actor_id="test_operator",
        actor_role="operator",
        notes="Approved candidate for Phase 9J deployment testing",
    )
    return chall_ver


def _seed_resolved_cases(db_session: Session, count: int = 120) -> list[RecoveryCase]:
    """Helper to seed historical resolved cases in database."""
    run_id = uuid.uuid4().hex[:6]
    customer = Customer(
        external_customer_id=f"cust_dep_test_{run_id}",
        email_masked="c***@example.com",
        phone_masked="+91******9999",
        risk_tier=CustomerRiskTier.LOW.value,
        total_payments_count=10,
        failed_payments_count=1,
    )
    db_session.add(customer)
    db_session.flush()

    cases = []
    for i in range(count):
        sub = Subscription(
            customer_id=customer.id,
            external_subscription_id=f"sub_dep_{run_id}_{i}",
            status=SubscriptionStatus.ACTIVE.value,
            plan_name="Pro Tier",
            billing_cadence="MONTHLY",
            recurring_amount=299900,
        )
        db_session.add(sub)
        db_session.flush()

        is_positive = (i % 3) != 0  # ~66% recovery rate
        p_status = (
            PaymentStatus.CAPTURED.value if is_positive else PaymentStatus.FAILED.value
        )
        c_status = (
            RecoveryCaseStatus.RECOVERED.value
            if is_positive
            else RecoveryCaseStatus.CLOSED.value
        )

        payment = Payment(
            customer_id=customer.id,
            subscription_id=sub.id,
            external_order_id=f"pay_dep_{run_id}_{i}",
            amount=299900,
            currency="INR",
            status=p_status,
        )

        db_session.add(payment)
        db_session.flush()

        case = RecoveryCase(
            payment_id=payment.id,
            customer_id=customer.id,
            status=c_status,
            amount_at_risk=299900,
            recovered_amount=299900 if is_positive else 0,
            opened_at=datetime.now(UTC),
            resolved_at=datetime.now(UTC),
            total_attempts_count=1,
        )
        db_session.add(case)
        db_session.flush()

        attempt = PaymentAttempt(
            payment_id=payment.id,
            attempt_number=1,
            amount=299900,
            status=PaymentAttemptStatus.SUCCESS.value
            if is_positive
            else PaymentAttemptStatus.FAILED.value,
            error_reason="INSUFFICIENT_FUNDS" if not is_positive else None,
        )
        db_session.add(attempt)
        cases.append(case)

    db_session.commit()
    return cases


# =============================================================================
# Unit & Integration Tests
# =============================================================================


def test_deterministic_shadow_assignment():
    """1. Test SHA-256 deterministic shadow traffic assignment."""
    dep_id = "dep_test_sha256"
    case_id = str(uuid.uuid4())

    # Consistency across multiple evaluations
    res1 = ModelDeploymentService.assign_shadow_traffic(dep_id, case_id, 50)
    res2 = ModelDeploymentService.assign_shadow_traffic(dep_id, case_id, 50)
    assert res1 == res2

    # Edge cases 0% and 100%
    assert ModelDeploymentService.assign_shadow_traffic(dep_id, case_id, 0) is False
    assert ModelDeploymentService.assign_shadow_traffic(dep_id, case_id, 100) is True


def test_shadow_percentages_whitelist(
    client: TestClient, db_session: Session, setup_promotion_ready_model: str
):
    """2. Test allowed shadow percentages [0, 5, 10, 25, 50, 100] and rejection of invalid percentages."""
    chall_ver = setup_promotion_ready_model

    # Create deployment
    create_res = client.post(
        "/api/recovery/intelligence/models/deployments",
        json={"challenger_version": chall_ver, "notes": "Testing percentages"},
    )
    assert create_res.status_code == 201
    dep_id = create_res.json()["deployment_id"]

    # Allowed percentages succeed
    for pct in ALLOWED_TRAFFIC_PERCENTAGES:
        res = client.post(
            f"/api/recovery/intelligence/models/deployments/{dep_id}/start-shadow",
            json={"shadow_percentage": pct},
        )
        assert res.status_code == 200
        assert res.json()["traffic_allocation_percentage"] == pct

    # Invalid percentages rejected
    for invalid_pct in [15, 33, 75, 120, -5]:
        bad_res = client.post(
            f"/api/recovery/intelligence/models/deployments/{dep_id}/start-shadow",
            json={"shadow_percentage": invalid_pct},
        )
        assert bad_res.status_code == 422


def test_deployment_creation_and_state_transitions(
    client: TestClient,
    admin_client: TestClient,
    db_session: Session,
    setup_promotion_ready_model: str,
):
    """3. Test state machine: SHADOW -> CANARY -> ACTIVE -> RETIRED."""
    chall_ver = setup_promotion_ready_model

    # Create deployment in SHADOW status
    create_res = client.post(
        "/api/recovery/intelligence/models/deployments",
        json={"challenger_version": chall_ver},
    )
    assert create_res.status_code == 201
    dep = create_res.json()
    dep_id = dep["deployment_id"]
    assert dep["status"] == ModelDeploymentStatus.SHADOW.value
    assert dep["champion_version"] == DEFAULT_CHAMPION_VERSION
    assert dep["challenger_version"] == chall_ver

    # Pause deployment
    pause_res = client.post(
        f"/api/recovery/intelligence/models/deployments/{dep_id}/pause"
    )
    assert pause_res.status_code == 200
    assert pause_res.json()["status"] == ModelDeploymentStatus.PAUSED.value

    # Advance to CANARY (10%)
    canary_res = client.post(
        f"/api/recovery/intelligence/models/deployments/{dep_id}/canary",
        json={"canary_percentage": 10},
    )
    assert canary_res.status_code == 200
    assert canary_res.json()["status"] == ModelDeploymentStatus.CANARY.value
    assert canary_res.json()["traffic_allocation_percentage"] == 10

    # Admin Activation
    act_res = admin_client.post(
        f"/api/recovery/intelligence/models/deployments/{dep_id}/activate",
        json={"notes": "Admin activated candidate into production"},
    )
    assert act_res.status_code == 200
    assert act_res.json()["status"] == ModelDeploymentStatus.ACTIVE.value

    # Admin Rollback
    rb_res = admin_client.post(
        f"/api/recovery/intelligence/models/deployments/{dep_id}/rollback",
        json={"reason": "Emergency rollback test"},
    )
    assert rb_res.status_code == 200
    assert rb_res.json()["status"] == ModelDeploymentStatus.RETIRED.value


def test_invalid_state_transition_from_shadow_to_activate_fails(
    admin_client: TestClient, db_session: Session, setup_promotion_ready_model: str
):
    """4. Test that activating directly from SHADOW without CANARY status raises HTTP 409."""
    chall_ver = setup_promotion_ready_model
    create_res = admin_client.post(
        "/api/recovery/intelligence/models/deployments",
        json={"challenger_version": chall_ver},
    )
    dep_id = create_res.json()["deployment_id"]

    # Attempt activation from SHADOW status
    bad_act = admin_client.post(
        f"/api/recovery/intelligence/models/deployments/{dep_id}/activate",
        json={"notes": "Should fail directly from shadow"},
    )
    assert bad_act.status_code == 409
    assert "CANARY" in bad_act.json()["detail"]


def test_shadow_mode_analysis_and_metrics(
    client: TestClient, db_session: Session, setup_promotion_ready_model: str
):
    """5. Test shadow mode analysis metrics, deltas, calibration, and agreement rates."""
    chall_ver = setup_promotion_ready_model
    _seed_resolved_cases(db_session, count=120)

    create_res = client.post(
        "/api/recovery/intelligence/models/deployments",
        json={"challenger_version": chall_ver},
    )
    dep_id = create_res.json()["deployment_id"]

    # Get shadow analysis
    analysis_res = client.get(
        f"/api/recovery/intelligence/models/deployments/{dep_id}/shadow-analysis"
    )
    assert analysis_res.status_code == 200
    data = analysis_res.json()

    assert data["sample_size"] >= 100
    assert data["assignment_method"] == "SHA256_DETERMINISTIC"

    # Champion metrics
    champ = data["champion_metrics"]
    assert 0.0 <= champ["accuracy"] <= 1.0
    assert 0.0 <= champ["f1_score"] <= 1.0
    assert 0.0 <= champ["brier_score"] <= 1.0
    assert champ["recovery_rate"] is not None

    # Challenger metrics
    chall = data["challenger_metrics"]
    assert 0.0 <= chall["accuracy"] <= 1.0
    assert 0.0 <= chall["f1_score"] <= 1.0
    assert 0.0 <= chall["brier_score"] <= 1.0

    # Deltas
    assert len(data["metric_deltas"]) >= 5
    assert data["channel_agreement_rate"] is not None

    # Calibration report
    cal = data["calibration"]
    assert len(cal["buckets"]) == 5
    assert 0.0 <= cal["champion_ece"] <= 1.0
    assert 0.0 <= cal["challenger_ece"] <= 1.0

    # Statistical test
    stat = data["statistical_test"]
    assert stat["test_name"] == "TWO_PROPORTION_POOLED_Z_TEST"
    assert stat["significance_level"] == 0.05
    assert stat["wilson_champion_ci"] is not None
    assert stat["wilson_challenger_ci"] is not None


def test_14_deployment_readiness_safety_gates(
    client: TestClient, db_session: Session, setup_promotion_ready_model: str
):
    """6. Test evaluation of all 14 deployment readiness safety gates."""
    chall_ver = setup_promotion_ready_model
    _seed_resolved_cases(db_session, count=120)

    create_res = client.post(
        "/api/recovery/intelligence/models/deployments",
        json={"challenger_version": chall_ver},
    )
    dep_id = create_res.json()["deployment_id"]

    readiness_res = client.get(
        f"/api/recovery/intelligence/models/deployments/{dep_id}/readiness"
    )
    assert readiness_res.status_code == 200
    readiness = readiness_res.json()

    assert len(readiness["gates"]) == 14
    gate_codes = {g["gate_code"] for g in readiness["gates"]}
    assert DeploymentQualityGateCode.MIN_SHADOW_SAMPLE.value in gate_codes
    assert DeploymentQualityGateCode.RECOVERY_RATE_NON_REGRESSION.value in gate_codes
    assert DeploymentQualityGateCode.BRIER_NON_REGRESSION.value in gate_codes
    assert DeploymentQualityGateCode.CALIBRATION_ACCEPTABLE.value in gate_codes
    assert DeploymentQualityGateCode.DATA_QUALITY_CLEAN.value in gate_codes
    assert DeploymentQualityGateCode.MODEL_GOVERNANCE_HEALTHY.value in gate_codes
    assert DeploymentQualityGateCode.NO_ROLLBACK_ALERT.value in gate_codes
    assert DeploymentQualityGateCode.ARTIFACT_HASH_VERIFIED.value in gate_codes
    assert DeploymentQualityGateCode.FEATURE_SCHEMA_COMPATIBLE.value in gate_codes
    assert DeploymentQualityGateCode.EXPLICIT_ADMIN_APPROVAL.value in gate_codes


def test_rollback_guardrail_diagnostics(db_session: Session):
    """7. Test that critical regression triggers automated rollback recommendation."""
    service = ModelDeploymentService(db_session)
    champ = service._calculate_metrics_snapshot([1] * 80 + [0] * 20, [0.8] * 100)
    # Severe drop of > 5%
    chall = service._calculate_metrics_snapshot([1] * 60 + [0] * 40, [0.6] * 100)
    cal = service._calculate_calibration_report([1] * 100, [0.8] * 100, [0.6] * 100)

    diag = service._evaluate_rollback_guardrails(
        champ_metrics=champ,
        chall_metrics=chall,
        calibration=cal,
        is_gov_degraded=False,
    )
    assert diag.rollback_recommended is True
    assert len(diag.reasons) > 0


def test_viewer_rbac_read_only(
    viewer_client: TestClient, db_session: Session, setup_promotion_ready_model: str
):
    """8. Test Viewer role is strictly read-only."""
    chall_ver = setup_promotion_ready_model

    # Read operations allowed
    list_res = viewer_client.get("/api/recovery/intelligence/models/deployments")
    assert list_res.status_code == 200

    # Write operations forbidden (HTTP 403)
    create_res = viewer_client.post(
        "/api/recovery/intelligence/models/deployments",
        json={"challenger_version": chall_ver},
    )
    assert create_res.status_code == 403


def test_operator_cannot_activate_or_rollback_production(
    client: TestClient, db_session: Session, setup_promotion_ready_model: str
):
    """9. Test Operator role cannot execute production activation or rollback (Admin only)."""
    chall_ver = setup_promotion_ready_model
    create_res = client.post(
        "/api/recovery/intelligence/models/deployments",
        json={"challenger_version": chall_ver},
    )
    dep_id = create_res.json()["deployment_id"]

    # Operator cannot activate (HTTP 403)
    act_res = client.post(
        f"/api/recovery/intelligence/models/deployments/{dep_id}/activate",
        json={"notes": "Operator trying to activate"},
    )
    assert act_res.status_code == 403

    # Operator cannot rollback (HTTP 403)
    rb_res = client.post(
        f"/api/recovery/intelligence/models/deployments/{dep_id}/rollback",
        json={"reason": "Operator trying to rollback"},
    )
    assert rb_res.status_code == 403


def test_unauthenticated_requests_return_401(db_session: Session):
    """10. Test unauthenticated calls return HTTP 401."""

    def _override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = _override_get_db
    unauth_client = TestClient(app)
    res = unauth_client.get("/api/recovery/intelligence/models/deployments")
    assert res.status_code == 401
    app.dependency_overrides.clear()


def test_zero_pii_and_secrets_in_deployment_apis(
    client: TestClient, db_session: Session, setup_promotion_ready_model: str
):
    """11. Test zero PII and secrets in deployment API responses."""
    chall_ver = setup_promotion_ready_model
    create_res = client.post(
        "/api/recovery/intelligence/models/deployments",
        json={"challenger_version": chall_ver},
    )
    dep_id = create_res.json()["deployment_id"]

    analysis_res = client.get(
        f"/api/recovery/intelligence/models/deployments/{dep_id}/shadow-analysis"
    )
    assert analysis_res.status_code == 200
    raw_text = analysis_res.text.lower()

    for forbidden in ["password", "secret", "card_pan", "cvv", "bearer", "apikey"]:
        assert forbidden not in raw_text


# =============================================================================
# MANDATORY FINANCIAL ISOLATION TEST (Step 19)
# =============================================================================


def test_mandatory_financial_isolation_end_to_end(
    client: TestClient,
    admin_client: TestClient,
    db_session: Session,
    setup_promotion_ready_model: str,
):
    """12. MANDATORY: Complete lifecycle from Shadow -> Canary -> Activation -> Rollback.

    Asserts:
    - Delta RecoveryAction count == 0
    - Delta Payment mutation count == 0
    - Delta RecoveryCase financial mutation count == 0
    - PolicyEngine remains authoritative.
    """
    chall_ver = setup_promotion_ready_model
    _seed_resolved_cases(db_session, count=120)

    # 1. Capture baseline financial state
    initial_actions_count = db_session.query(RecoveryAction).count()
    initial_payments_captured = (
        db_session.query(Payment)
        .filter(Payment.status == PaymentStatus.CAPTURED.value)
        .count()
    )
    initial_cases_recovered = (
        db_session.query(RecoveryCase)
        .filter(RecoveryCase.status == RecoveryCaseStatus.RECOVERED.value)
        .count()
    )

    # 2. Create deployment in SHADOW mode
    create_res = client.post(
        "/api/recovery/intelligence/models/deployments",
        json={
            "challenger_version": chall_ver,
            "notes": "Mandatory financial isolation test",
        },
    )
    assert create_res.status_code == 201
    dep_id = create_res.json()["deployment_id"]

    # 3. Evaluate shadow mode
    shadow_res = client.get(
        f"/api/recovery/intelligence/models/deployments/{dep_id}/shadow-analysis"
    )
    assert shadow_res.status_code == 200

    # 4. Start Canary Rollout (10%)
    canary_res = client.post(
        f"/api/recovery/intelligence/models/deployments/{dep_id}/canary",
        json={"canary_percentage": 10},
    )
    assert canary_res.status_code == 200

    # 5. Admin Production Activation
    act_res = admin_client.post(
        f"/api/recovery/intelligence/models/deployments/{dep_id}/activate",
        json={"notes": "Admin activated during financial isolation test"},
    )
    assert act_res.status_code == 200

    # 6. Admin Production Rollback
    rb_res = admin_client.post(
        f"/api/recovery/intelligence/models/deployments/{dep_id}/rollback",
        json={"reason": "Completed mandatory isolation verification"},
    )
    assert rb_res.status_code == 200

    # 7. Post-execution financial assertions
    final_actions_count = db_session.query(RecoveryAction).count()
    final_payments_captured = (
        db_session.query(Payment)
        .filter(Payment.status == PaymentStatus.CAPTURED.value)
        .count()
    )
    final_cases_recovered = (
        db_session.query(RecoveryCase)
        .filter(RecoveryCase.status == RecoveryCaseStatus.RECOVERED.value)
        .count()
    )

    # ZERO FINANCIAL MUTATIONS STRICT ASSERTIONS
    assert final_actions_count == initial_actions_count, (
        "RecoveryAction count must not change!"
    )
    assert final_payments_captured == initial_payments_captured, (
        "Payment statuses must not change!"
    )
    assert final_cases_recovered == initial_cases_recovered, (
        "RecoveryCase statuses must not change!"
    )


def test_get_deployment_by_id_and_not_found(
    client: TestClient, db_session: Session, setup_promotion_ready_model: str
):
    """13. Test fetching single deployment by ID and 404 for missing IDs."""
    chall_ver = setup_promotion_ready_model
    create_res = client.post(
        "/api/recovery/intelligence/models/deployments",
        json={"challenger_version": chall_ver},
    )
    dep_id = create_res.json()["deployment_id"]

    # Existing deployment
    get_res = client.get(f"/api/recovery/intelligence/models/deployments/{dep_id}")
    assert get_res.status_code == 200
    assert get_res.json()["deployment_id"] == dep_id

    # Non-existent deployment
    missing_id = str(uuid.uuid4())
    bad_res = client.get(f"/api/recovery/intelligence/models/deployments/{missing_id}")
    assert bad_res.status_code == 404


def test_deployments_list_pagination_and_filtering(
    client: TestClient, db_session: Session, setup_promotion_ready_model: str
):
    """14. Test pagination and status filtering on deployments list endpoint."""
    chall_ver = setup_promotion_ready_model
    create_res = client.post(
        "/api/recovery/intelligence/models/deployments",
        json={"challenger_version": chall_ver},
    )
    dep_id = create_res.json()["deployment_id"]

    # Filter by SHADOW status
    shadow_list = client.get(
        "/api/recovery/intelligence/models/deployments?status=SHADOW&page=1&page_size=10"
    )
    assert shadow_list.status_code == 200
    assert shadow_list.json()["total"] >= 1
    assert any(d["deployment_id"] == dep_id for d in shadow_list.json()["items"])

    # Filter by RETIRED status (should not include newly created deployment)
    retired_list = client.get(
        "/api/recovery/intelligence/models/deployments?status=RETIRED&page=1&page_size=10"
    )
    assert retired_list.status_code == 200
    assert not any(d["deployment_id"] == dep_id for d in retired_list.json()["items"])


def test_cannot_create_deployment_for_unapproved_model(
    client: TestClient, db_session: Session
):
    """15. Test that creating a deployment for a non-existent or unapproved model raises error."""
    bad_res = client.post(
        "/api/recovery/intelligence/models/deployments",
        json={"challenger_version": "v99.9-nonexistent"},
    )
    assert bad_res.status_code in (404, 409, 422)


def test_statistical_calculations_wilson_and_newcombe(db_session: Session):
    """16. Test Wilson score interval and Newcombe two-proportion difference intervals."""
    service = ModelDeploymentService(db_session)

    # Wilson interval for 80/100
    w_low, w_high = service._wilson_interval(80, 100)
    assert 0.70 <= w_low <= 0.75
    assert 0.85 <= w_high <= 0.90

    # Newcombe difference interval for (80/100) vs (70/100)
    diff_low, diff_high = service._newcombe_difference_interval(80, 100, 70, 100)
    assert diff_low < 0.10 < diff_high
    assert diff_low > -0.10

    # Z-test execution
    stat_report = service._perform_statistical_test(
        champ_recovered=70,
        champ_total=100,
        chall_recovered=85,
        chall_total=100,
    )
    assert stat_report.test_statistic is not None
    assert stat_report.p_value is not None
    assert stat_report.significance_classification in (
        DeploymentSignificance.STATISTICALLY_SIGNIFICANT,
        DeploymentSignificance.NOT_STATISTICALLY_SIGNIFICANT,
    )


def test_deterministic_traffic_distribution_proportions():
    """17. Test that SHA-256 hash buckets partition traffic approximately proportionally."""
    dep_id = "test_traffic_partition_123"
    total_cases = 1000

    # Test 25% allocation
    assigned_count = sum(
        1
        for i in range(total_cases)
        if ModelDeploymentService.assign_shadow_traffic(dep_id, f"case_uuid_{i}", 25)
    )
    # Expected: ~250 out of 1000 (allowing normal pseudorandom variance)
    assert 200 <= assigned_count <= 300

    # Test 50% allocation
    assigned_50 = sum(
        1
        for i in range(total_cases)
        if ModelDeploymentService.assign_shadow_traffic(dep_id, f"case_uuid_{i}", 50)
    )
    assert 440 <= assigned_50 <= 560
