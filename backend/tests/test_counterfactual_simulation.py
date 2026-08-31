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
)
from app.schemas.simulation import SimulationRequest
from app.services.counterfactual_simulation_service import (
    counterfactual_simulation_service,
)


@pytest.fixture
def client(db_session: Session):
    """Test client with overridden database session dependency and viewer auth."""

    def _override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = _override_get_db
    token = create_access_token(user_id="viewer_test_sim", role=UserRole.VIEWER.value)
    with TestClient(app, headers={"Authorization": f"Bearer {token}"}) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def make_sim_case(
    db_session: Session,
    status: str = RecoveryCaseStatus.RECOVERED.value,
    amount: int = 100000,
    prob: float = 0.85,
    action_type: str = RecoveryActionType.RETRY_PAYMENT.value,
    delay_hours: int = 12,
    risk_tier: str = CustomerRiskTier.STANDARD.value,
    failure_reason: str = "insufficient_funds",
    attempt_number: int = 1,
) -> RecoveryCase:
    """Helper to provision a complete resolved recovery case with all counterfactual simulation dimensions."""
    uid = uuid.uuid4().hex[:8]
    now_utc = datetime.now(UTC)
    resolved_time = now_utc - timedelta(days=1)

    customer = Customer(
        external_customer_id=f"cust_sim_{uid}",
        risk_tier=risk_tier,
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
        total_attempts_count=attempt_number,
        max_allowed_attempts=3,
        latest_failure_reason=failure_reason,
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
        feature_vector_snapshot={"error_reason": failure_reason, "amount": amount},
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
        reasoning_summary="Counterfactual simulation record.",
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


# =========================================================================
# 1. Mathematical Correctness & Uplift Tests
# =========================================================================


def test_simulation_mathematical_uplift_and_erv(db_session: Session):
    """1-3. Test ERV, ERV uplift, recovery rate, and relative percentage uplift."""
    # Current: RETRY_PAYMENT (10 cases, 4 recovered -> 40% rate, avg prob 0.40)
    for i in range(10):
        status = (
            RecoveryCaseStatus.RECOVERED.value
            if i < 4
            else RecoveryCaseStatus.CLOSED.value
        )
        make_sim_case(
            db_session,
            status=status,
            amount=100000,
            prob=0.40,
            action_type=RecoveryActionType.RETRY_PAYMENT.value,
            delay_hours=12,
        )

    # Alternative: SEND_PAYMENT_LINK (10 cases, 8 recovered -> 80% rate, avg prob 0.80)
    for i in range(10):
        status = (
            RecoveryCaseStatus.RECOVERED.value
            if i < 8
            else RecoveryCaseStatus.CLOSED.value
        )
        make_sim_case(
            db_session,
            status=status,
            amount=100000,
            prob=0.80,
            action_type=RecoveryActionType.SEND_PAYMENT_LINK.value,
            delay_hours=4,
        )

    req = SimulationRequest(
        current_action_type=RecoveryActionType.RETRY_PAYMENT.value,
        current_delay_hours=12,
        alternative_action_type=RecoveryActionType.SEND_PAYMENT_LINK.value,
        alternative_delay_hours=4,
        amount_at_risk_paise=1000000,  # ₹10,000 principal
    )

    res = counterfactual_simulation_service.simulate(db_session, req)

    # Current Strategy
    assert res.current_strategy.sample_size == 10
    assert res.current_strategy.recovery_rate == 0.40
    assert res.current_strategy.expected_recovery_value_paise == 400000  # ₹4,000

    # Alternative Strategy
    assert res.alternative_strategy.sample_size == 10
    assert res.alternative_strategy.recovery_rate == 0.80
    assert res.alternative_strategy.expected_recovery_value_paise == 800000  # ₹8,000

    # Uplift
    assert res.estimated_uplift.recovery_rate_delta == 0.40  # +40.0%
    assert res.estimated_uplift.relative_uplift_pct == 100.0  # +100% relative increase
    assert (
        res.estimated_uplift.estimated_incremental_erv_paise == 400000
    )  # +₹4,000 incremental value
    assert res.estimated_uplift.confidence_assessment == "STRONG_POSITIVE_EVIDENCE"


def test_simulation_relative_uplift_zero_denominator_safe(db_session: Session):
    """4. Test that when current recovery rate is 0.0, relative uplift is safely null (no division by zero)."""
    # Current has 0% recovery rate
    for _ in range(5):
        make_sim_case(
            db_session,
            status=RecoveryCaseStatus.CLOSED.value,
            action_type=RecoveryActionType.RETRY_PAYMENT.value,
        )

    # Alternative has 50% recovery rate
    for i in range(4):
        status = (
            RecoveryCaseStatus.RECOVERED.value
            if i < 2
            else RecoveryCaseStatus.CLOSED.value
        )
        make_sim_case(
            db_session,
            status=status,
            action_type=RecoveryActionType.SEND_PAYMENT_LINK.value,
        )

    req = SimulationRequest(
        current_action_type=RecoveryActionType.RETRY_PAYMENT.value,
        alternative_action_type=RecoveryActionType.SEND_PAYMENT_LINK.value,
    )

    res = counterfactual_simulation_service.simulate(db_session, req)
    assert res.current_strategy.recovery_rate == 0.0
    assert res.estimated_uplift.recovery_rate_delta == 0.50
    assert (
        res.estimated_uplift.relative_uplift_pct is None
    )  # Handled safely without exception


# =========================================================================
# 2. Reliability Boundaries (N=0, 9, 10, 29, 30) Tests
# =========================================================================


@pytest.mark.parametrize(
    ("count", "expected_rel"),
    [
        (0, "INSUFFICIENT_DATA"),
        (9, "INSUFFICIENT_DATA"),
        (10, "LIMITED"),
        (29, "LIMITED"),
        (30, "SUFFICIENT"),
    ],
)
def test_reliability_exact_sample_size_boundaries(
    db_session: Session, count: int, expected_rel: str
):
    """5-9. Test strict enforcement of sample size reliability thresholds."""
    for _ in range(count):
        make_sim_case(
            db_session,
            status=RecoveryCaseStatus.RECOVERED.value,
            action_type=RecoveryActionType.SEND_PAYMENT_LINK.value,
        )

    req = SimulationRequest(
        current_action_type=RecoveryActionType.RETRY_PAYMENT.value,
        alternative_action_type=RecoveryActionType.SEND_PAYMENT_LINK.value,
    )

    res = counterfactual_simulation_service.simulate(db_session, req)
    assert res.alternative_strategy.sample_size == count
    assert res.alternative_strategy.reliability == expected_rel


# =========================================================================
# 3. Segmentation & Progressive Fallback Tests
# =========================================================================


def test_segmentation_exact_match(db_session: Session):
    """10. Test simulation with exact multi-dimensional segment matching."""
    # 12 matching cases (Risk: HIGH, Reason: card_inactive)
    for _ in range(12):
        make_sim_case(
            db_session,
            status=RecoveryCaseStatus.RECOVERED.value,
            risk_tier=CustomerRiskTier.HIGH.value,
            failure_reason="card_inactive",
            action_type=RecoveryActionType.SEND_PAYMENT_LINK.value,
        )

    # 10 other cases (Risk: LOW, Reason: other)
    for _ in range(10):
        make_sim_case(
            db_session,
            status=RecoveryCaseStatus.RECOVERED.value,
            risk_tier=CustomerRiskTier.LOW.value,
            failure_reason="insufficient_funds",
            action_type=RecoveryActionType.SEND_PAYMENT_LINK.value,
        )

    req = SimulationRequest(
        current_action_type=RecoveryActionType.RETRY_PAYMENT.value,
        alternative_action_type=RecoveryActionType.SEND_PAYMENT_LINK.value,
        risk_tier=CustomerRiskTier.HIGH.value,
        failure_reason="card_inactive",
    )

    res = counterfactual_simulation_service.simulate(db_session, req)
    assert res.population.segmentation_level_used == "EXACT_MATCH"
    assert res.population.total_cases_analyzed == 12
    assert res.alternative_strategy.sample_size == 12


def test_segmentation_progressive_fallback_to_global(db_session: Session):
    """11. Test progressive fallback to global baseline when exact segment has insufficient data."""
    # 2 cases in specific rare segment
    make_sim_case(
        db_session,
        risk_tier=CustomerRiskTier.HIGH.value,
        failure_reason="rare_custom_failure_code",
    )

    # 20 cases in general database
    for _ in range(20):
        make_sim_case(
            db_session,
            risk_tier=CustomerRiskTier.STANDARD.value,
            failure_reason="insufficient_funds",
        )

    req = SimulationRequest(
        current_action_type=RecoveryActionType.RETRY_PAYMENT.value,
        alternative_action_type=RecoveryActionType.SEND_PAYMENT_LINK.value,
        risk_tier=CustomerRiskTier.HIGH.value,
        failure_reason="rare_custom_failure_code",
    )

    res = counterfactual_simulation_service.simulate(db_session, req)
    assert res.population.segmentation_level_used in (
        "RELAXED_MATCH",
        "GLOBAL_BASELINE",
    )
    assert any(
        d.code in ("FALLBACK_SEGMENTATION", "GLOBAL_BASELINE_FALLBACK")
        for d in res.diagnostics
    )


# =========================================================================
# 4. Edge Cases & Defensive Handling Tests
# =========================================================================


def test_zero_historical_cases_in_database(db_session: Session):
    """12. Test simulation against empty database behaves defensively."""
    req = SimulationRequest(
        current_action_type=RecoveryActionType.RETRY_PAYMENT.value,
        alternative_action_type=RecoveryActionType.SEND_PAYMENT_LINK.value,
    )

    res = counterfactual_simulation_service.simulate(db_session, req)
    assert res.population.total_cases_analyzed == 0
    assert res.current_strategy.sample_size == 0
    assert res.alternative_strategy.sample_size == 0
    assert res.current_strategy.recovery_rate is None
    assert res.estimated_uplift.recovery_rate_delta is None
    assert res.estimated_uplift.confidence_assessment == "INSUFFICIENT_DATA"


def test_missing_alternative_strategy_in_population(db_session: Session):
    """13. Test when population contains current strategy but 0 cases for alternative strategy."""
    for _ in range(10):
        make_sim_case(
            db_session,
            status=RecoveryCaseStatus.RECOVERED.value,
            action_type=RecoveryActionType.RETRY_PAYMENT.value,
        )

    req = SimulationRequest(
        current_action_type=RecoveryActionType.RETRY_PAYMENT.value,
        alternative_action_type=RecoveryActionType.HALT_SUBSCRIPTION.value,
    )

    res = counterfactual_simulation_service.simulate(db_session, req)
    assert res.current_strategy.sample_size == 10
    assert res.alternative_strategy.sample_size == 0
    assert res.alternative_strategy.reliability == "INSUFFICIENT_DATA"
    assert any(d.code == "ALTERNATIVE_STRATEGY_LOW_SAMPLE" for d in res.diagnostics)


# =========================================================================
# 5. Determinism & RBAC Security Tests
# =========================================================================


def test_simulation_is_strictly_deterministic(db_session: Session):
    """14. Test repeated simulation requests against same DB state produce identical output."""
    for i in range(15):
        status = (
            RecoveryCaseStatus.RECOVERED.value
            if i % 2 == 0
            else RecoveryCaseStatus.CLOSED.value
        )
        make_sim_case(db_session, status=status, amount=100000)

    req = SimulationRequest(
        current_action_type=RecoveryActionType.RETRY_PAYMENT.value,
        alternative_action_type=RecoveryActionType.SEND_PAYMENT_LINK.value,
    )

    res1 = counterfactual_simulation_service.simulate(db_session, req)
    res2 = counterfactual_simulation_service.simulate(db_session, req)

    assert res1.current_strategy.sample_size == res2.current_strategy.sample_size
    assert (
        res1.alternative_strategy.sample_size == res2.alternative_strategy.sample_size
    )
    assert (
        res1.estimated_uplift.recovery_rate_delta
        == res2.estimated_uplift.recovery_rate_delta
    )
    assert res1.population.total_cases_analyzed == res2.population.total_cases_analyzed


def test_simulation_api_security_roles(db_session: Session):
    """15. Test unauthenticated rejection (401) and viewer/operator/admin authorization (200)."""
    make_sim_case(db_session, status=RecoveryCaseStatus.RECOVERED.value)

    def _override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = _override_get_db

    payload = {
        "current_action_type": "RETRY_PAYMENT",
        "current_delay_hours": 12,
        "alternative_action_type": "SEND_PAYMENT_LINK",
        "alternative_delay_hours": 4,
    }

    with TestClient(app) as test_client:
        # Unauthenticated -> 401
        res_unauth = test_client.post(
            "/api/recovery/intelligence/simulation", json=payload
        )
        assert res_unauth.status_code == 401

        # Viewer -> 200
        token_v = create_access_token(user_id="viewer_sim", role=UserRole.VIEWER.value)
        res_v = test_client.post(
            "/api/recovery/intelligence/simulation",
            json=payload,
            headers={"Authorization": f"Bearer {token_v}"},
        )
        assert res_v.status_code == 200
        data = res_v.json()
        assert "population" in data
        assert "current_strategy" in data
        assert "alternative_strategy" in data
        assert "observational_disclaimer" in data

        # Operator -> 200
        token_o = create_access_token(
            user_id="operator_sim", role=UserRole.OPERATOR.value
        )
        res_o = test_client.post(
            "/api/recovery/intelligence/simulation",
            json=payload,
            headers={"Authorization": f"Bearer {token_o}"},
        )
        assert res_o.status_code == 200

        # Admin -> 200
        token_a = create_access_token(user_id="admin_sim", role=UserRole.ADMIN.value)
        res_a = test_client.post(
            "/api/recovery/intelligence/simulation",
            json=payload,
            headers={"Authorization": f"Bearer {token_a}"},
        )
        assert res_a.status_code == 200

    app.dependency_overrides.clear()


# =========================================================================
# 6. Financial Isolation & Zero PII/Secrets Verification Tests
# =========================================================================


def test_simulation_endpoint_strictly_read_only_and_zero_pii(
    client: TestClient, db_session: Session
):
    """16-18. Test zero financial mutations, zero PII, and absolute financial isolation."""
    case = make_sim_case(db_session, status=RecoveryCaseStatus.RECOVERED.value)
    initial_updated_at = case.updated_at
    initial_status = case.status
    initial_actions_count = db_session.query(RecoveryAction).count()
    initial_results_count = db_session.query(ActionResult).count()

    payload = {
        "current_action_type": "RETRY_PAYMENT",
        "alternative_action_type": "SEND_PAYMENT_LINK",
    }

    res = client.post("/api/recovery/intelligence/simulation", json=payload)
    assert res.status_code == 200
    text = res.text.lower()

    # Zero PII & Secrets check
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

    # DB Immutability check
    db_session.refresh(case)
    assert case.updated_at == initial_updated_at
    assert case.status == initial_status
    assert db_session.query(RecoveryAction).count() == initial_actions_count
    assert db_session.query(ActionResult).count() == initial_results_count


def test_simulation_never_calls_financial_execution_providers(db_session: Session):
    """19-20. Assert that simulation never calls ActionDispatcher or RazorpayActionProvider."""
    make_sim_case(db_session, status=RecoveryCaseStatus.RECOVERED.value)

    req = SimulationRequest(
        current_action_type=RecoveryActionType.RETRY_PAYMENT.value,
        alternative_action_type=RecoveryActionType.SEND_PAYMENT_LINK.value,
    )

    with (
        patch(
            "app.services.action_dispatcher.ActionDispatcher.dispatch_action"
        ) as mock_dispatch,
        patch("app.providers.razorpay.RazorpayActionProvider.execute") as mock_exec,
    ):
        counterfactual_simulation_service.simulate(db_session, req)
        mock_dispatch.assert_not_called()
        mock_exec.assert_not_called()
