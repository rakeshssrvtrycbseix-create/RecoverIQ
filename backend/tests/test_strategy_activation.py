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
    AgentDecision,
    Customer,
    CustomerRiskTier,
    MLPrediction,
    Payment,
    PaymentStatus,
    PolicyDecision,
    PolicyEvaluationResult,
    RecoveryAction,
    RecoveryActionStatus,
    RecoveryActionType,
    RecoveryCase,
    RecoveryCaseStatus,
    RolloutHealthStatus,
    StrategyActivationStatus,
)
from app.services.strategy_activation_service import (
    strategy_activation_service,
)
from app.services.strategy_governance_service import (
    strategy_governance_service,
)


@pytest.fixture
def client(db_session: Session):
    """Test client with overridden database session dependency and viewer auth."""

    def _override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = _override_get_db
    token = create_access_token(user_id="viewer_test_act", role=UserRole.VIEWER.value)
    with TestClient(app, headers={"Authorization": f"Bearer {token}"}) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def make_case(
    db_session: Session,
    status: str = RecoveryCaseStatus.RECOVERED.value,
    amount: int = 100000,
    prob: float = 0.85,
    action_type: str = RecoveryActionType.SEND_PAYMENT_LINK.value,
    delay_hours: int = 4,
) -> RecoveryCase:
    """Helper to provision a resolved recovery case."""
    uid = uuid.uuid4().hex[:8]
    now_utc = datetime.now(UTC)
    resolved_time = now_utc - timedelta(days=1)

    customer = Customer(
        external_customer_id=f"cust_act_{uid}",
        risk_tier=CustomerRiskTier.STANDARD.value,
        total_payments_count=5,
        failed_payments_count=1,
        recovered_payments_count=4,
    )
    db_session.add(customer)
    db_session.flush()

    payment = Payment(
        customer_id=customer.id,
        amount=amount,
        currency="INR",
        status=PaymentStatus.CAPTURED.value
        if status == RecoveryCaseStatus.RECOVERED.value
        else PaymentStatus.FAILED.value,
    )
    db_session.add(payment)
    db_session.flush()

    case = RecoveryCase(
        payment_id=payment.id,
        customer_id=customer.id,
        status=status,
        amount_at_risk=amount,
        recovered_amount=amount if status == RecoveryCaseStatus.RECOVERED.value else 0,
        total_attempts_count=1,
        max_allowed_attempts=3,
        latest_failure_reason="insufficient_funds",
        opened_at=resolved_time - timedelta(hours=delay_hours),
        resolved_at=resolved_time,
        created_at=resolved_time,
        metadata_json={},
    )
    db_session.add(case)
    db_session.flush()

    prediction = MLPrediction(
        recovery_case_id=case.id,
        model_name="recovery_probability",
        model_version="v1.0",
        recovery_probability=Decimal(str(round(prob, 4))),
        predicted_channel=action_type,
        predicted_delay_hours=delay_hours,
        feature_vector_snapshot={
            "error_reason": "insufficient_funds",
            "amount": amount,
        },
        predicted_at=resolved_time,
    )
    db_session.add(prediction)
    db_session.flush()

    agent_dec = AgentDecision(
        recovery_case_id=case.id,
        ml_prediction_id=prediction.id,
        agent_name="RecoveryOrchestrator",
        agent_version="v1.0",
        prompt_template_version="v1.0",
        proposed_action_type=action_type,
        confidence_score=Decimal("0.8500"),
        reasoning_summary="Activation test decision.",
        suggested_payload={"channel": "GATEWAY_API"},
    )
    db_session.add(agent_dec)
    db_session.flush()

    pol_dec = PolicyDecision(
        recovery_case_id=case.id,
        agent_decision_id=agent_dec.id,
        evaluation_result=PolicyEvaluationResult.ALLOWED.value,
        policy_engine_version="v1.0",
        decision_reason="Policy allowed.",
    )
    db_session.add(pol_dec)
    db_session.flush()

    action = RecoveryAction(
        recovery_case_id=case.id,
        policy_decision_id=pol_dec.id,
        action_idempotency_key=f"act_{uid}",
        action_type=action_type,
        status=RecoveryActionStatus.COMPLETED.value
        if status == RecoveryCaseStatus.RECOVERED.value
        else RecoveryActionStatus.FAILED.value,
        scheduled_for=resolved_time,
    )
    db_session.add(action)
    db_session.commit()

    return case


def setup_approved_recommendation(db_session: Session) -> str:
    """Provisions dataset and approves a recommendation, returning its recommendation_id."""
    for i in range(20):
        status = (
            RecoveryCaseStatus.RECOVERED.value
            if i < 6
            else RecoveryCaseStatus.CLOSED.value
        )
        make_case(
            db_session,
            status=status,
            prob=0.30,
            action_type=RecoveryActionType.RETRY_PAYMENT.value,
        )

    for i in range(20):
        status = (
            RecoveryCaseStatus.RECOVERED.value
            if i < 17
            else RecoveryCaseStatus.CLOSED.value
        )
        make_case(
            db_session,
            status=status,
            prob=0.85,
            action_type=RecoveryActionType.SEND_PAYMENT_LINK.value,
        )

    rec = strategy_governance_service.evaluate_and_sync_recommendation(db_session)
    assert rec is not None

    op_user = type("AuthUser", (), {"id": "test_op_user", "role": "operator"})()
    appr_rec = strategy_governance_service.approve_recommendation(
        db=db_session,
        recommendation_id=rec.recommendation_id,
        current_user=op_user,  # type: ignore
        notes="Approved for canary testing",
    )
    assert appr_rec.status == "APPROVED"
    return appr_rec.recommendation_id


# =========================================================================
# 1. Deterministic Canary Assignment Tests
# =========================================================================


def test_deterministic_canary_assignment():
    """1. Test that same case_id + activation_id always produces identical canary assignment."""
    case_id = uuid.uuid4()
    act_id = "act_alpha123"

    res1 = strategy_activation_service.is_case_in_canary(case_id, act_id, 10)
    res2 = strategy_activation_service.is_case_in_canary(case_id, act_id, 10)
    assert res1 == res2

    # 0% is strictly False, 100% is strictly True
    assert strategy_activation_service.is_case_in_canary(case_id, act_id, 0) is False
    assert strategy_activation_service.is_case_in_canary(case_id, act_id, 100) is True


def test_canary_assignment_distribution():
    """2. Test canary assignment distribution roughly matches target percentages."""
    act_id = "act_test_dist"
    cases = [uuid.uuid4() for _ in range(200)]

    for pct in [5, 10, 25, 50]:
        assigned = sum(
            1
            for c in cases
            if strategy_activation_service.is_case_in_canary(c, act_id, pct)
        )
        expected = len(cases) * (pct / 100.0)
        # Verify within reasonable standard deviation bound
        assert abs(assigned - expected) < 25


# =========================================================================
# 2. Lifecycle State Machine Tests
# =========================================================================


def test_approved_to_canary_to_active_lifecycle(db_session: Session):
    """3. Test complete forward lifecycle: Create/Approved -> Canary (5%) -> Active (100%)."""
    rec_id = setup_approved_recommendation(db_session)
    op_user = type("AuthUser", (), {"id": "test_op", "role": "operator"})()
    admin_user = type("AuthUser", (), {"id": "test_admin", "role": "admin"})()

    # 1. Create Activation
    act = strategy_activation_service.create_activation(
        db=db_session,
        recommendation_id=rec_id,
        current_user=op_user,  # type: ignore
    )
    assert act.status == StrategyActivationStatus.APPROVED.value
    assert act.rollout_percentage == 0

    # 2. Start Canary (5%)
    act_canary = strategy_activation_service.start_canary(
        db=db_session,
        activation_id=act.activation_id,
        rollout_percentage=5,
        current_user=op_user,  # type: ignore
    )
    assert act_canary.status == StrategyActivationStatus.CANARY.value
    assert act_canary.rollout_percentage == 5

    # 3. Promote to Active (100%)
    act_active = strategy_activation_service.promote_to_active(
        db=db_session,
        activation_id=act.activation_id,
        current_user=admin_user,  # type: ignore
    )
    assert act_active.status == StrategyActivationStatus.ACTIVE.value
    assert act_active.rollout_percentage == 100
    assert act_active.activated_by == "test_admin"


def test_canary_pause_and_rollback(db_session: Session):
    """4. Test pausing and rolling back a canary."""
    rec_id = setup_approved_recommendation(db_session)
    op_user = type("AuthUser", (), {"id": "test_op", "role": "operator"})()

    act = strategy_activation_service.create_activation(
        db=db_session,
        recommendation_id=rec_id,
        current_user=op_user,  # type: ignore
    )
    strategy_activation_service.start_canary(
        db=db_session,
        activation_id=act.activation_id,
        rollout_percentage=10,
        current_user=op_user,  # type: ignore
    )

    # Pause
    act_paused = strategy_activation_service.pause_activation(
        db=db_session,
        activation_id=act.activation_id,
        current_user=op_user,
        notes="Pausing for metric check",  # type: ignore
    )
    assert act_paused.status == StrategyActivationStatus.PAUSED.value
    assert act_paused.rollout_percentage == 0

    # Rollback
    act_rb = strategy_activation_service.rollback_activation(
        db=db_session,
        activation_id=act.activation_id,
        current_user=op_user,
        notes="Rollback executed",  # type: ignore
    )
    assert act_rb.status == StrategyActivationStatus.ROLLED_BACK.value
    assert act_rb.rolled_back_by == "test_op"


def test_invalid_transitions_rejected(db_session: Session):
    """5. Test that invalid state transitions raise error."""
    rec_id = setup_approved_recommendation(db_session)
    op_user = type("AuthUser", (), {"id": "test_op", "role": "operator"})()
    admin_user = type("AuthUser", (), {"id": "test_admin", "role": "admin"})()

    act = strategy_activation_service.create_activation(
        db=db_session,
        recommendation_id=rec_id,
        current_user=op_user,  # type: ignore
    )

    # Cannot promote directly to ACTIVE from APPROVED without entering CANARY
    with pytest.raises(Exception):
        strategy_activation_service.promote_to_active(
            db=db_session,
            activation_id=act.activation_id,
            current_user=admin_user,  # type: ignore
        )

    # Rollback
    strategy_activation_service.rollback_activation(
        db=db_session,
        activation_id=act.activation_id,
        current_user=op_user,  # type: ignore
    )

    # Cannot start canary from ROLLED_BACK
    with pytest.raises(Exception):
        strategy_activation_service.start_canary(
            db=db_session,
            activation_id=act.activation_id,
            rollout_percentage=5,
            current_user=op_user,  # type: ignore
        )


# =========================================================================
# 3. Rollout Percentage Validation Tests
# =========================================================================


def test_rollout_percentage_validation(db_session: Session):
    """6. Test unsupported rollout percentages are rejected."""
    rec_id = setup_approved_recommendation(db_session)
    op_user = type("AuthUser", (), {"id": "test_op", "role": "operator"})()

    act = strategy_activation_service.create_activation(
        db=db_session,
        recommendation_id=rec_id,
        current_user=op_user,  # type: ignore
    )

    for invalid_pct in [1, 7, 33, 75, 101, -5]:
        with pytest.raises(Exception):
            strategy_activation_service.start_canary(
                db=db_session,
                activation_id=act.activation_id,
                rollout_percentage=invalid_pct,
                current_user=op_user,  # type: ignore
            )


# =========================================================================
# 4. Statistical Metrics & Integer Financial Tests
# =========================================================================


def test_experiment_metrics_and_erv_precision(db_session: Session):
    """7. Test experiment metrics, integer paise ERV, and confidence intervals."""
    cases: list[RecoveryCase] = []
    for i in range(15):
        cases.append(
            make_case(
                db_session, status=RecoveryCaseStatus.RECOVERED.value, amount=100000
            )
        )
    for i in range(5):
        cases.append(
            make_case(db_session, status=RecoveryCaseStatus.CLOSED.value, amount=100000)
        )

    metrics = strategy_activation_service.calculate_experiment_metrics(cases)
    assert metrics.sample_size == 20
    assert metrics.recovered_count == 15
    assert metrics.failed_count == 5
    assert metrics.recovery_rate == 0.75
    assert isinstance(metrics.amount_at_risk_paise, int)
    assert isinstance(metrics.amount_recovered_paise, int)
    assert isinstance(metrics.expected_recovery_value_paise, int)
    assert metrics.expected_recovery_value_paise == int(
        round(metrics.amount_at_risk_paise * 0.75)
    )


def test_uplift_zero_denominator_handling():
    """8. Test uplift calculation handles zero control rate safely without ZeroDivisionError."""
    control = strategy_activation_service.calculate_experiment_metrics([])
    treatment = strategy_activation_service.calculate_experiment_metrics([])

    uplift = strategy_activation_service.calculate_uplift(control, treatment)
    assert uplift.absolute_uplift is None
    assert uplift.relative_uplift_pct is None


def test_reliability_classification():
    """9. Test reliability tiers match N = 0, 9, 10, 29, 30."""
    assert strategy_activation_service.determine_reliability(0) == "INSUFFICIENT_DATA"
    assert strategy_activation_service.determine_reliability(9) == "INSUFFICIENT_DATA"
    assert strategy_activation_service.determine_reliability(10) == "LIMITED"
    assert strategy_activation_service.determine_reliability(29) == "LIMITED"
    assert strategy_activation_service.determine_reliability(30) == "SUFFICIENT"


# =========================================================================
# 5. Rollback Safety Diagnostics Tests
# =========================================================================


def test_negative_treatment_uplift_triggers_rollback_recommended(db_session: Session):
    """10. Test that treatment underperforming control by >= 5% triggers ROLLBACK_RECOMMENDED."""
    control_cases = [
        make_case(db_session, status=RecoveryCaseStatus.RECOVERED.value)
        for _ in range(30)
    ]
    treatment_cases = [
        make_case(db_session, status=RecoveryCaseStatus.CLOSED.value) for _ in range(30)
    ]

    control_m = strategy_activation_service.calculate_experiment_metrics(control_cases)
    treatment_m = strategy_activation_service.calculate_experiment_metrics(
        treatment_cases
    )

    health = strategy_activation_service.evaluate_rollout_health(
        control_m, treatment_m, "HEALTHY"
    )
    assert health.status == RolloutHealthStatus.ROLLBACK_RECOMMENDED.value
    assert any("underperformed" in d for d in health.diagnostics)


def test_positive_uplift_evaluates_safe(db_session: Session):
    """11. Test that positive treatment uplift evaluates as SAFE."""
    control_cases = [
        make_case(
            db_session,
            status=RecoveryCaseStatus.RECOVERED.value
            if i < 15
            else RecoveryCaseStatus.CLOSED.value,
        )
        for i in range(30)
    ]
    treatment_cases = [
        make_case(
            db_session,
            status=RecoveryCaseStatus.RECOVERED.value
            if i < 25
            else RecoveryCaseStatus.CLOSED.value,
        )
        for i in range(30)
    ]

    control_m = strategy_activation_service.calculate_experiment_metrics(control_cases)
    treatment_m = strategy_activation_service.calculate_experiment_metrics(
        treatment_cases
    )

    health = strategy_activation_service.evaluate_rollout_health(
        control_m, treatment_m, "HEALTHY"
    )
    assert health.status == RolloutHealthStatus.SAFE.value


# =========================================================================
# 6. Expiration & Model Governance Tests
# =========================================================================


def test_expired_recommendation_cannot_be_activated(db_session: Session):
    """12. Test that expired recommendation cannot be activated."""
    rec_id = setup_approved_recommendation(db_session)
    op_user = type("AuthUser", (), {"id": "test_op", "role": "operator"})()

    # Expired time in the future
    future_time = datetime.now(UTC) + timedelta(days=10)
    with pytest.raises(Exception):
        strategy_activation_service.create_activation(
            db=db_session,
            recommendation_id=rec_id,
            current_user=op_user,
            as_of=future_time,  # type: ignore
        )


# =========================================================================
# 7. RBAC & HTTP Authorization Tests
# =========================================================================


def test_unauthenticated_rejected(db_session: Session):
    """13. Test unauthenticated requests return 401."""

    def _override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = _override_get_db

    with TestClient(app) as test_client:
        assert (
            test_client.get("/api/recovery/intelligence/activations").status_code == 401
        )
        assert (
            test_client.get(
                "/api/recovery/intelligence/activations/act_123"
            ).status_code
            == 401
        )
        assert (
            test_client.post(
                "/api/recovery/intelligence/activations/create",
                json={"recommendation_id": "rec_1"},
            ).status_code
            == 401
        )
        assert (
            test_client.post(
                "/api/recovery/intelligence/activations/act_123/start-canary",
                json={"rollout_percentage": 5},
            ).status_code
            == 401
        )
        assert (
            test_client.post(
                "/api/recovery/intelligence/activations/act_123/activate", json={}
            ).status_code
            == 401
        )

    app.dependency_overrides.clear()


def test_viewer_can_read_cannot_modify(db_session: Session):
    """14. Test viewer role can read (200) but cannot modify activations (403)."""
    rec_id = setup_approved_recommendation(db_session)
    op_user = type("AuthUser", (), {"id": "test_op", "role": "operator"})()
    act = strategy_activation_service.create_activation(
        db=db_session,
        recommendation_id=rec_id,
        current_user=op_user,  # type: ignore
    )

    def _override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = _override_get_db
    token_v = create_access_token(user_id="viewer_usr", role=UserRole.VIEWER.value)

    with TestClient(app, headers={"Authorization": f"Bearer {token_v}"}) as test_client:
        # Read -> 200
        assert (
            test_client.get("/api/recovery/intelligence/activations").status_code == 200
        )
        assert (
            test_client.get(
                f"/api/recovery/intelligence/activations/{act.activation_id}"
            ).status_code
            == 200
        )

        # Mutations -> 403 Forbidden
        assert (
            test_client.post(
                "/api/recovery/intelligence/activations/create",
                json={"recommendation_id": rec_id},
            ).status_code
            == 403
        )
        assert (
            test_client.post(
                f"/api/recovery/intelligence/activations/{act.activation_id}/start-canary",
                json={"rollout_percentage": 5},
            ).status_code
            == 403
        )
        assert (
            test_client.post(
                f"/api/recovery/intelligence/activations/{act.activation_id}/pause",
                json={},
            ).status_code
            == 403
        )
        assert (
            test_client.post(
                f"/api/recovery/intelligence/activations/{act.activation_id}/rollback",
                json={},
            ).status_code
            == 403
        )
        assert (
            test_client.post(
                f"/api/recovery/intelligence/activations/{act.activation_id}/activate",
                json={},
            ).status_code
            == 403
        )

    app.dependency_overrides.clear()


def test_operator_and_admin_permissions(db_session: Session):
    """15. Test operator can start-canary/pause/rollback, but only admin can activate (100%)."""
    rec_id = setup_approved_recommendation(db_session)
    op_user = type("AuthUser", (), {"id": "test_op", "role": "operator"})()
    act = strategy_activation_service.create_activation(
        db=db_session,
        recommendation_id=rec_id,
        current_user=op_user,  # type: ignore
    )

    def _override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = _override_get_db
    token_op = create_access_token(user_id="operator_usr", role=UserRole.OPERATOR.value)
    token_admin = create_access_token(user_id="admin_usr", role=UserRole.ADMIN.value)

    # Operator starts canary -> 200
    with TestClient(
        app, headers={"Authorization": f"Bearer {token_op}"}
    ) as test_client:
        res_canary = test_client.post(
            f"/api/recovery/intelligence/activations/{act.activation_id}/start-canary",
            json={"rollout_percentage": 5},
        )
        assert res_canary.status_code == 200
        assert res_canary.json()["status"] == "CANARY"
        assert res_canary.json()["rollout_percentage"] == 5

        # Operator tries to promote to ACTIVE -> 403 Forbidden
        res_act = test_client.post(
            f"/api/recovery/intelligence/activations/{act.activation_id}/activate",
            json={},
        )
        assert res_act.status_code == 403

    # Admin promotes to ACTIVE -> 200
    with TestClient(
        app, headers={"Authorization": f"Bearer {token_admin}"}
    ) as test_client:
        res_act = test_client.post(
            f"/api/recovery/intelligence/activations/{act.activation_id}/activate",
            json={},
        )
        assert res_act.status_code == 200
        assert res_act.json()["status"] == "ACTIVE"
        assert res_act.json()["rollout_percentage"] == 100

    app.dependency_overrides.clear()


# =========================================================================
# 8. Financial Isolation & Zero PII/Secrets Verification
# =========================================================================


def test_activation_never_creates_recovery_action_or_calls_provider(
    db_session: Session,
):
    """16. Test that activating canary never creates RecoveryAction or calls gateway provider."""
    rec_id = setup_approved_recommendation(db_session)
    op_user = type("AuthUser", (), {"id": "test_op", "role": "operator"})()
    act = strategy_activation_service.create_activation(
        db=db_session,
        recommendation_id=rec_id,
        current_user=op_user,  # type: ignore
    )

    initial_actions_count = db_session.query(RecoveryAction).count()
    initial_cases_count = db_session.query(RecoveryCase).count()
    initial_results_count = db_session.query(ActionResult).count()

    def _override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = _override_get_db
    token_op = create_access_token(user_id="operator_usr", role=UserRole.OPERATOR.value)

    with (
        patch(
            "app.services.action_dispatcher.ActionDispatcher.dispatch_action"
        ) as mock_dispatch,
        patch("app.providers.razorpay.RazorpayActionProvider.execute") as mock_exec,
        TestClient(app, headers={"Authorization": f"Bearer {token_op}"}) as test_client,
    ):
        res = test_client.post(
            f"/api/recovery/intelligence/activations/{act.activation_id}/start-canary",
            json={"rollout_percentage": 10},
        )
        assert res.status_code == 200
        mock_dispatch.assert_not_called()
        mock_exec.assert_not_called()

    app.dependency_overrides.clear()

    # Zero DB changes in operational entities
    assert db_session.query(RecoveryAction).count() == initial_actions_count
    assert db_session.query(RecoveryCase).count() == initial_cases_count
    assert db_session.query(ActionResult).count() == initial_results_count


def test_zero_pii_and_zero_secrets_in_activation_responses(
    client: TestClient, db_session: Session
):
    """17. Test that activation responses contain no PII and no secrets."""
    rec_id = setup_approved_recommendation(db_session)
    op_user = type("AuthUser", (), {"id": "test_op", "role": "operator"})()
    strategy_activation_service.create_activation(
        db=db_session,
        recommendation_id=rec_id,
        current_user=op_user,  # type: ignore
    )

    res = client.get("/api/recovery/intelligence/activations")
    assert res.status_code == 200
    text = res.text.lower()

    for forbidden in [
        "password",
        "secret",
        "bearer",
        "@",
        "email",
        "phone",
        "card_number",
        "pan",
        "cvv",
        "api_key",
    ]:
        assert forbidden not in text
