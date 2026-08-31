import uuid
from datetime import UTC, datetime, timedelta
from decimal import Decimal

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
from app.services.strategy_optimization_service import (
    strategy_optimization_service,
)


@pytest.fixture
def client(db_session: Session):
    """Test client with overridden database session dependency and viewer auth."""

    def _override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = _override_get_db
    token = create_access_token(user_id="viewer_test_opt", role=UserRole.VIEWER.value)
    with TestClient(app, headers={"Authorization": f"Bearer {token}"}) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def make_opt_case(
    db_session: Session,
    status: str = RecoveryCaseStatus.RECOVERED.value,
    amount: int = 100000,
    prob: float = 0.85,
    action_type: str = RecoveryActionType.RETRY_PAYMENT.value,
    delay_hours: int = 4,
    risk_tier: str = CustomerRiskTier.STANDARD.value,
    failure_reason: str = "insufficient_funds",
    attempt_number: int = 1,
) -> RecoveryCase:
    """Helper to provision a complete resolved recovery case with all optimization dimensions."""
    uid = uuid.uuid4().hex[:8]
    now_utc = datetime.now(UTC)
    resolved_time = now_utc - timedelta(days=1)

    customer = Customer(
        external_customer_id=f"cust_opt_{uid}",
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
        confidence_score=Decimal("0.8800"),
        reasoning_summary="Strategy optimization test proposal.",
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
# 1. Expected Recovery Value (ERV) & Monetary Precision Tests
# =========================================================================


def test_expected_recovery_value_calculation_integer_paise(db_session: Session):
    """1. Test ERV formula = Amount at Risk * Recovery Probability in integer paise."""
    # Case 1: ₹10,000 (1,000,000 paise), prob 0.80 -> ERV = 800,000 paise
    make_opt_case(db_session, amount=1000000, prob=0.80)
    # Case 2: ₹5,000 (500,000 paise), prob 0.60 -> combined total risk 1,500,000 paise, avg prob 0.70 -> ERV = 1,050,000 paise
    make_opt_case(db_session, amount=500000, prob=0.60)

    report = strategy_optimization_service.optimize(db_session)
    erv = report.expected_recovery_value_summary

    assert erv.amount_at_risk == 1500000
    assert erv.recovery_probability == pytest.approx(0.70, 0.001)
    assert erv.expected_recovery_value == 1050000
    assert isinstance(erv.expected_recovery_value, int)


# =========================================================================
# 2. Strategy Performance & Action Attribution Tests
# =========================================================================


def test_action_strategy_recovery_rate_and_yield(db_session: Session):
    """2-3. Test strategy recovery rate and financial yield calculation across action types."""
    # 2 retry payments (1 recovered for ₹1,000, 1 failed for ₹1,000) -> 50% recovery rate, 50% amount rate
    make_opt_case(
        db_session,
        status=RecoveryCaseStatus.RECOVERED.value,
        amount=100000,
        action_type=RecoveryActionType.RETRY_PAYMENT.value,
    )
    make_opt_case(
        db_session,
        status=RecoveryCaseStatus.CLOSED.value,
        amount=100000,
        action_type=RecoveryActionType.RETRY_PAYMENT.value,
    )

    # 1 payment link (1 recovered for ₹2,000) -> 100% recovery rate, 100% amount rate
    make_opt_case(
        db_session,
        status=RecoveryCaseStatus.RECOVERED.value,
        amount=200000,
        action_type=RecoveryActionType.SEND_PAYMENT_LINK.value,
    )

    report = strategy_optimization_service.optimize(db_session)
    strat_map = {s.action_type: s for s in report.strategies}

    retry = strat_map[RecoveryActionType.RETRY_PAYMENT.value]
    assert retry.sample_size == 2
    assert retry.recovered_count == 1
    assert retry.failed_count == 1
    assert retry.recovery_rate == 0.50
    assert retry.amount_at_risk == 200000
    assert retry.amount_recovered == 100000
    assert retry.recovery_amount_rate == 0.50

    link = strat_map[RecoveryActionType.SEND_PAYMENT_LINK.value]
    assert link.sample_size == 1
    assert link.recovered_count == 1
    assert link.recovery_rate == 1.0
    assert link.amount_recovered == 200000
    assert link.recovery_amount_rate == 1.0


# =========================================================================
# 3. Champion Strategy Selection & Minimum Sample Size Tests
# =========================================================================


def test_champion_strategy_selection_sufficient_sample(db_session: Session):
    """4-5. Test deterministic champion selection prioritizing statistically SUFFICIENT sample size."""
    # 35 cases of RETRY_PAYMENT with 80% recovery rate (SUFFICIENT reliability)
    for i in range(35):
        status = (
            RecoveryCaseStatus.RECOVERED.value
            if i < 28
            else RecoveryCaseStatus.CLOSED.value
        )
        make_opt_case(
            db_session,
            status=status,
            action_type=RecoveryActionType.RETRY_PAYMENT.value,
        )

    # 2 cases of SEND_PAYMENT_LINK with 100% recovery rate (INSUFFICIENT_DATA reliability)
    for _ in range(2):
        make_opt_case(
            db_session,
            status=RecoveryCaseStatus.RECOVERED.value,
            action_type=RecoveryActionType.SEND_PAYMENT_LINK.value,
        )

    report = strategy_optimization_service.optimize(db_session)
    champion = report.overall_recommendation

    # Champion must be RETRY_PAYMENT because it has SUFFICIENT sample size (35 >= 30) despite link having 100% rate on N=2
    assert champion.action_type == RecoveryActionType.RETRY_PAYMENT.value
    assert champion.confidence_level == "SUFFICIENT"
    assert champion.sample_size == 35
    assert champion.recovery_rate == pytest.approx(0.80, 0.01)


def test_champion_strategy_selection_low_sample_classification(db_session: Session):
    """Test champion selection when all candidate strategies have < 30 observations."""
    for _ in range(5):
        make_opt_case(
            db_session,
            status=RecoveryCaseStatus.RECOVERED.value,
            action_type=RecoveryActionType.SEND_PAYMENT_LINK.value,
        )

    report = strategy_optimization_service.optimize(db_session)
    champion = report.overall_recommendation

    assert champion.action_type == RecoveryActionType.SEND_PAYMENT_LINK.value
    assert champion.confidence_level == "INSUFFICIENT_DATA"
    assert champion.sample_size == 5


# =========================================================================
# 4. Delay Cadence Optimization Tests
# =========================================================================


def test_delay_performance_and_optimal_cadence_selection(db_session: Session):
    """6. Test evaluation across delay cadences (2h, 4h, 12h, 24h)."""
    # 4-hour delay (3 recovered, 1 failed -> 75% rate)
    for i in range(4):
        status = (
            RecoveryCaseStatus.RECOVERED.value
            if i < 3
            else RecoveryCaseStatus.CLOSED.value
        )
        make_opt_case(db_session, status=status, delay_hours=4)

    # 24-hour delay (1 recovered, 3 failed -> 25% rate)
    for i in range(4):
        status = (
            RecoveryCaseStatus.RECOVERED.value
            if i < 1
            else RecoveryCaseStatus.CLOSED.value
        )
        make_opt_case(db_session, status=status, delay_hours=24)

    report = strategy_optimization_service.optimize(db_session)
    delay_map = {d.delay_hours: d for d in report.delay_analysis}

    assert delay_map[4].sample_size == 4
    assert delay_map[4].recovery_rate == 0.75

    assert delay_map[24].sample_size == 4
    assert delay_map[24].recovery_rate == 0.25

    # Overall recommendation recommended delay should be 4
    assert report.overall_recommendation.recommended_delay_hours == 4


# =========================================================================
# 5. Segment Optimization Tests
# =========================================================================


def test_segment_recommendations_risk_tier_and_failure_reason(db_session: Session):
    """7-10. Test segment champion recommendations across risk tier, failure reason, and amount bands."""
    # HIGH risk tier with transient_error (recovers well with PAYMENT_LINK)
    for _ in range(12):
        make_opt_case(
            db_session,
            status=RecoveryCaseStatus.RECOVERED.value,
            amount=200000,
            risk_tier=CustomerRiskTier.HIGH.value,
            failure_reason="transient_network_error",
            action_type=RecoveryActionType.SEND_PAYMENT_LINK.value,
            attempt_number=1,
        )

    # LOW risk tier with insufficient_funds (recovers well with RETRY_PAYMENT)
    for _ in range(15):
        make_opt_case(
            db_session,
            status=RecoveryCaseStatus.RECOVERED.value,
            amount=50000,
            risk_tier=CustomerRiskTier.LOW.value,
            failure_reason="insufficient_funds",
            action_type=RecoveryActionType.RETRY_PAYMENT.value,
            attempt_number=2,
        )

    report = strategy_optimization_service.optimize(db_session)
    seg_recs = report.segment_recommendations

    # High risk segment
    high_risk_seg = next(
        s
        for s in seg_recs
        if s.segment_type == "risk_tier"
        and s.segment_value == CustomerRiskTier.HIGH.value
    )
    assert high_risk_seg.best_action_type == RecoveryActionType.SEND_PAYMENT_LINK.value
    assert high_risk_seg.sample_size == 12
    assert high_risk_seg.recovery_rate == 1.0

    # Low risk segment
    low_risk_seg = next(
        s
        for s in seg_recs
        if s.segment_type == "risk_tier"
        and s.segment_value == CustomerRiskTier.LOW.value
    )
    assert low_risk_seg.best_action_type == RecoveryActionType.RETRY_PAYMENT.value
    assert low_risk_seg.sample_size == 15
    assert low_risk_seg.recovery_rate == 1.0

    # Failure reason segment
    network_seg = next(
        s
        for s in seg_recs
        if s.segment_type == "failure_reason"
        and s.segment_value == "transient_network_error"
    )
    assert network_seg.best_action_type == RecoveryActionType.SEND_PAYMENT_LINK.value

    # Amount band segment (< ₹1,000)
    band_seg = next(
        s
        for s in seg_recs
        if s.segment_type == "amount_band" and s.segment_value == "< ₹1,000"
    )
    assert band_seg.sample_size == 15


# =========================================================================
# 6. Edge Cases & Zero-Division Safety Tests
# =========================================================================


def test_zero_historical_cases_empty_database(db_session: Session):
    """11-12. Test zero historical cases returns 0 sample size, null ratios, and 0 ERV safely."""
    report = strategy_optimization_service.optimize(db_session)

    assert report.sample_size == 0
    assert report.expected_recovery_value_summary.amount_at_risk == 0
    assert report.expected_recovery_value_summary.expected_recovery_value == 0
    assert report.overall_recommendation.action_type is None
    assert report.overall_recommendation.confidence_level == "INSUFFICIENT_DATA"
    assert len(report.segment_recommendations) == 0
    assert any(f.code == "INSUFFICIENT_DATA" for f in report.diagnostic_findings)


def test_single_case_boundary_behavior(db_session: Session):
    """Test optimizer with exactly 1 case behaves defensively."""
    make_opt_case(db_session, status=RecoveryCaseStatus.RECOVERED.value, amount=50000)

    report = strategy_optimization_service.optimize(db_session)
    assert report.sample_size == 1
    assert report.overall_recommendation.confidence_level == "INSUFFICIENT_DATA"
    assert report.expected_recovery_value_summary.amount_at_risk == 50000


# =========================================================================
# 7. Determinism & RBAC Security Tests
# =========================================================================


def test_optimization_is_strictly_deterministic(db_session: Session):
    """13. Test repeated optimization calls against identical DB produce identical recommendations."""
    for i in range(10):
        status = (
            RecoveryCaseStatus.RECOVERED.value
            if i % 2 == 0
            else RecoveryCaseStatus.CLOSED.value
        )
        make_opt_case(db_session, status=status, amount=100000)

    res1 = strategy_optimization_service.optimize(db_session)
    res2 = strategy_optimization_service.optimize(db_session)

    assert (
        res1.overall_recommendation.action_type
        == res2.overall_recommendation.action_type
    )
    assert (
        res1.overall_recommendation.sample_size
        == res2.overall_recommendation.sample_size
    )
    assert (
        res1.expected_recovery_value_summary.expected_recovery_value
        == res2.expected_recovery_value_summary.expected_recovery_value
    )
    assert len(res1.strategies) == len(res2.strategies)
    assert len(res1.segment_recommendations) == len(res2.segment_recommendations)


def test_optimization_api_security_roles(db_session: Session):
    """14. Test unauthenticated request is rejected (401), and Viewer/Operator/Admin allowed (200)."""
    make_opt_case(db_session, status=RecoveryCaseStatus.RECOVERED.value)

    def _override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = _override_get_db

    with TestClient(app) as test_client:
        # Unauthenticated -> 401
        res_unauth = test_client.get("/api/recovery/intelligence/optimization")
        assert res_unauth.status_code == 401

        # Viewer -> 200
        token_v = create_access_token(user_id="viewer_opt", role=UserRole.VIEWER.value)
        res_v = test_client.get(
            "/api/recovery/intelligence/optimization",
            headers={"Authorization": f"Bearer {token_v}"},
        )
        assert res_v.status_code == 200
        data = res_v.json()
        assert "overall_recommendation" in data
        assert "expected_recovery_value_summary" in data

        # Operator -> 200
        token_o = create_access_token(
            user_id="operator_opt", role=UserRole.OPERATOR.value
        )
        res_o = test_client.get(
            "/api/recovery/intelligence/optimization",
            headers={"Authorization": f"Bearer {token_o}"},
        )
        assert res_o.status_code == 200

        # Admin -> 200
        token_a = create_access_token(user_id="admin_opt", role=UserRole.ADMIN.value)
        res_a = test_client.get(
            "/api/recovery/intelligence/optimization",
            headers={"Authorization": f"Bearer {token_a}"},
        )
        assert res_a.status_code == 200

    app.dependency_overrides.clear()


# =========================================================================
# 8. Financial Isolation & Zero-PII Tests
# =========================================================================


def test_optimization_endpoint_strictly_read_only_and_zero_pii(
    client: TestClient, db_session: Session
):
    """15-18. Test zero financial mutations, zero PII, and absolute financial isolation."""
    case = make_opt_case(db_session, status=RecoveryCaseStatus.RECOVERED.value)
    initial_updated_at = case.updated_at
    initial_status = case.status
    initial_actions_count = db_session.query(RecoveryAction).count()
    initial_results_count = db_session.query(ActionResult).count()

    res = client.get("/api/recovery/intelligence/optimization")
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


def test_diagnostic_findings_generation(db_session: Session):
    """19-21. Test generation of STRATEGY_PERFORMING_WELL and DELAY_EFFECT_DETECTED findings."""
    # 35 cases of SEND_PAYMENT_LINK with 4-hour delay, 90% recovery rate
    for i in range(35):
        status = (
            RecoveryCaseStatus.RECOVERED.value
            if i < 31
            else RecoveryCaseStatus.CLOSED.value
        )
        make_opt_case(
            db_session,
            status=status,
            action_type=RecoveryActionType.SEND_PAYMENT_LINK.value,
            delay_hours=4,
        )

    # 15 cases of RETRY_PAYMENT with 24-hour delay, 20% recovery rate
    for i in range(15):
        status = (
            RecoveryCaseStatus.RECOVERED.value
            if i < 3
            else RecoveryCaseStatus.CLOSED.value
        )
        make_opt_case(
            db_session,
            status=status,
            action_type=RecoveryActionType.RETRY_PAYMENT.value,
            delay_hours=24,
        )

    report = strategy_optimization_service.optimize(db_session)
    finding_codes = {f.code for f in report.diagnostic_findings}

    assert "STRATEGY_PERFORMING_WELL" in finding_codes
    assert "DELAY_EFFECT_DETECTED" in finding_codes
