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
from app.services.intelligence_evaluation_service import (
    intelligence_evaluation_service,
)


@pytest.fixture
def client(db_session: Session):
    """Test client with overridden database session dependency and viewer auth."""

    def _override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = _override_get_db
    token = create_access_token(user_id="viewer_test_eval", role=UserRole.VIEWER.value)
    with TestClient(app, headers={"Authorization": f"Bearer {token}"}) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def make_eval_case(
    db_session: Session,
    status: str = RecoveryCaseStatus.RECOVERED.value,
    amount: int = 100000,
    recovered_amount: int = 100000,
    prob: float = 0.85,
    conf: float = 0.90,
    action_type: str = RecoveryActionType.RETRY_PAYMENT.value,
    policy_result: str = PolicyEvaluationResult.ALLOWED.value,
    risk_tier: str = CustomerRiskTier.STANDARD.value,
    failure_reason: str = "insufficient_funds",
    duration_hours: float | None = 2.5,
) -> RecoveryCase:
    """Helper to provision a complete resolved recovery case with all intelligence linkages."""
    uid = uuid.uuid4().hex[:8]
    now_utc = datetime.now(UTC)
    opened_at = now_utc - timedelta(hours=duration_hours or 2.0)
    resolved_at = (
        now_utc
        if status
        in (
            RecoveryCaseStatus.RECOVERED.value,
            RecoveryCaseStatus.CLOSED.value,
            RecoveryCaseStatus.EXHAUSTED.value,
        )
        else None
    )

    customer = Customer(
        external_customer_id=f"cust_eval_{uid}",
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
        recovered_amount=recovered_amount,
        total_attempts_count=1,
        max_allowed_attempts=3,
        latest_failure_reason=failure_reason,
        opened_at=opened_at,
        resolved_at=resolved_at,
        metadata_json={},
    )
    db_session.add(case)
    db_session.flush()

    prediction = MLPrediction(
        recovery_case_id=case.id,
        model_name="recovery_probability",
        model_version="v1.0",
        recovery_probability=Decimal(str(round(prob, 4))),
        feature_vector_snapshot={"error_reason": failure_reason, "amount": amount},
    )
    db_session.add(prediction)
    db_session.flush()

    agent_dec = AgentDecision(
        recovery_case_id=case.id,
        ml_prediction_id=prediction.id,
        agent_name="RecoveryOrchestrator",
        agent_version="v1.0",
        prompt_template_version="recovery_agent_v1.0",
        proposed_action_type=action_type,
        confidence_score=Decimal(str(round(conf, 4))),
        reasoning_summary=f"Automated evaluation recommendation for {action_type}.",
        suggested_payload={"channel": "GATEWAY_API"},
    )
    db_session.add(agent_dec)
    db_session.flush()

    pol_dec = PolicyDecision(
        recovery_case_id=case.id,
        agent_decision_id=agent_dec.id,
        evaluation_result=policy_result,
        policy_engine_version="policy_v1.0",
        decision_reason=f"Policy evaluation outcome: {policy_result}.",
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
        scheduled_for=now_utc,
    )
    db_session.add(action)
    db_session.commit()

    return case


# =========================================================================
# 1. Classification & Confusion Matrix Tests
# =========================================================================


def test_confusion_matrix_four_quadrants(db_session: Session):
    """
    1-4. Test explicit computation of True Positive, False Positive,
    True Negative, and False Negative quadrants.
    """
    # 1. TP: Prob >= 0.50 and Recovered
    make_eval_case(db_session, status=RecoveryCaseStatus.RECOVERED.value, prob=0.80)
    # 2. FP: Prob >= 0.50 and Failed
    make_eval_case(
        db_session,
        status=RecoveryCaseStatus.CLOSED.value,
        recovered_amount=0,
        prob=0.70,
    )
    # 3. TN: Prob < 0.50 and Failed
    make_eval_case(
        db_session,
        status=RecoveryCaseStatus.CLOSED.value,
        recovered_amount=0,
        prob=0.30,
    )
    # 4. FN: Prob < 0.50 and Recovered
    make_eval_case(db_session, status=RecoveryCaseStatus.RECOVERED.value, prob=0.20)

    report = intelligence_evaluation_service.evaluate(db_session)
    c = report.classification

    assert c.sample_size == 4
    assert c.true_positive == 1
    assert c.false_positive == 1
    assert c.true_negative == 1
    assert c.false_negative == 1
    assert c.accuracy == 0.50
    assert c.precision == 0.50
    assert c.recall == 0.50
    assert c.f1_score == 0.50


def test_perfect_classification(db_session: Session):
    """5-8. Test 100% accuracy, precision, recall, and F1 with perfect predictions."""
    make_eval_case(db_session, status=RecoveryCaseStatus.RECOVERED.value, prob=0.90)
    make_eval_case(db_session, status=RecoveryCaseStatus.RECOVERED.value, prob=0.75)
    make_eval_case(
        db_session,
        status=RecoveryCaseStatus.CLOSED.value,
        recovered_amount=0,
        prob=0.10,
    )
    make_eval_case(
        db_session,
        status=RecoveryCaseStatus.CLOSED.value,
        recovered_amount=0,
        prob=0.25,
    )

    report = intelligence_evaluation_service.evaluate(db_session)
    c = report.classification

    assert c.sample_size == 4
    assert c.true_positive == 2
    assert c.true_negative == 2
    assert c.false_positive == 0
    assert c.false_negative == 0
    assert c.accuracy == 1.0
    assert c.precision == 1.0
    assert c.recall == 1.0
    assert c.f1_score == 1.0


# =========================================================================
# 2. Edge Cases & Zero-Division Safety Tests
# =========================================================================


def test_empty_dataset_returns_null_metrics(db_session: Session):
    """9. Test zero eligible cases returns null metrics safely without division error."""
    report = intelligence_evaluation_service.evaluate(db_session)
    c = report.classification

    assert c.sample_size == 0
    assert c.accuracy is None
    assert c.precision is None
    assert c.recall is None
    assert c.f1_score is None
    assert c.brier_score is None
    assert report.confidence_outcomes.sample_size == 0
    assert report.recovery_duration.sample_size == 0


def test_all_positive_cases(db_session: Session):
    """10. Test dataset with only positive cases."""
    make_eval_case(db_session, status=RecoveryCaseStatus.RECOVERED.value, prob=0.85)
    make_eval_case(db_session, status=RecoveryCaseStatus.RECOVERED.value, prob=0.90)

    report = intelligence_evaluation_service.evaluate(db_session)
    c = report.classification

    assert c.sample_size == 2
    assert c.true_positive == 2
    assert c.true_negative == 0
    assert c.false_positive == 0
    assert c.false_negative == 0
    assert c.precision == 1.0
    assert c.recall == 1.0
    assert c.accuracy == 1.0


def test_all_negative_cases(db_session: Session):
    """11. Test dataset with only negative cases."""
    make_eval_case(
        db_session,
        status=RecoveryCaseStatus.CLOSED.value,
        recovered_amount=0,
        prob=0.20,
    )
    make_eval_case(
        db_session,
        status=RecoveryCaseStatus.CLOSED.value,
        recovered_amount=0,
        prob=0.15,
    )

    report = intelligence_evaluation_service.evaluate(db_session)
    c = report.classification

    assert c.sample_size == 2
    assert c.true_positive == 0
    assert c.true_negative == 2
    assert c.accuracy == 1.0
    # No predicted positives -> precision denominator = 0 -> null
    assert c.precision is None
    # No actual positives -> recall denominator = 0 -> null
    assert c.recall is None
    assert c.f1_score is None


def test_zero_denominator_precision_and_recall_handling(db_session: Session):
    """12-14. Test that zero denominator states return None rather than 0 or exception."""
    # Case: Actual is positive, but predicted negative
    make_eval_case(db_session, status=RecoveryCaseStatus.RECOVERED.value, prob=0.10)

    report = intelligence_evaluation_service.evaluate(db_session)
    c = report.classification

    assert c.sample_size == 1
    assert c.true_positive == 0
    assert c.false_negative == 1
    # TP + FP = 0 -> precision denominator is 0
    assert c.precision is None
    # Recall = TP / (TP + FN) = 0 / 1 = 0.0
    assert c.recall == 0.0
    # F1 with precision None -> None
    assert c.f1_score is None


# =========================================================================
# 3. Brier Score & Probability Calibration Tests
# =========================================================================


def test_brier_score_exact_calculation(db_session: Session):
    """15-16. Test exact mean squared error Brier score calculation."""
    # Case 1: prob = 0.80, actual = 1 -> error^2 = (0.8 - 1.0)^2 = 0.04
    make_eval_case(db_session, status=RecoveryCaseStatus.RECOVERED.value, prob=0.80)
    # Case 2: prob = 0.20, actual = 0 -> error^2 = (0.2 - 0.0)^2 = 0.04
    make_eval_case(
        db_session,
        status=RecoveryCaseStatus.CLOSED.value,
        recovered_amount=0,
        prob=0.20,
    )

    report = intelligence_evaluation_service.evaluate(db_session)
    assert report.classification.brier_score == pytest.approx(0.04, 0.001)


def test_calibration_buckets_and_boundaries(db_session: Session):
    """17-20. Test discrete probability calibration buckets [0.0-0.2, ..., 0.8-1.0]."""
    # Bucket 0.0-0.2
    make_eval_case(
        db_session,
        status=RecoveryCaseStatus.CLOSED.value,
        recovered_amount=0,
        prob=0.10,
    )
    # Bucket 0.2-0.4 (Boundary 0.2 belongs to [0.2, 0.4))
    make_eval_case(
        db_session,
        status=RecoveryCaseStatus.CLOSED.value,
        recovered_amount=0,
        prob=0.20,
    )
    # Bucket 0.4-0.6
    make_eval_case(db_session, status=RecoveryCaseStatus.RECOVERED.value, prob=0.50)
    # Bucket 0.6-0.8
    make_eval_case(db_session, status=RecoveryCaseStatus.RECOVERED.value, prob=0.70)
    # Bucket 0.8-1.0 (Boundary 1.0 included)
    make_eval_case(db_session, status=RecoveryCaseStatus.RECOVERED.value, prob=0.90)

    report = intelligence_evaluation_service.evaluate(db_session)
    cal = report.calibration

    assert len(cal) == 5

    b1 = cal[0]  # 0.0 - 0.2
    assert b1.sample_size == 1
    assert b1.predicted_probability_avg == 0.10
    assert b1.actual_recovery_rate == 0.0
    assert b1.calibration_error == 0.10

    b5 = cal[4]  # 0.8 - 1.0
    assert b5.sample_size == 1
    assert b5.predicted_probability_avg == 0.90
    assert b5.actual_recovery_rate == 1.0
    assert b5.calibration_error == 0.10


# =========================================================================
# 4. Action Attribution & Confidence Outcomes Tests
# =========================================================================


def test_action_attribution_grouping(db_session: Session):
    """21-22. Test recovery rate and average confidence segmented by action type."""
    # 2 retry payments (1 recovered, 1 failed) -> 50% recovery rate
    make_eval_case(
        db_session,
        status=RecoveryCaseStatus.RECOVERED.value,
        action_type=RecoveryActionType.RETRY_PAYMENT.value,
        conf=0.90,
    )
    make_eval_case(
        db_session,
        status=RecoveryCaseStatus.CLOSED.value,
        recovered_amount=0,
        action_type=RecoveryActionType.RETRY_PAYMENT.value,
        conf=0.80,
    )
    # 1 payment link (1 recovered) -> 100% recovery rate
    make_eval_case(
        db_session,
        status=RecoveryCaseStatus.RECOVERED.value,
        action_type=RecoveryActionType.SEND_PAYMENT_LINK.value,
        conf=0.75,
    )

    report = intelligence_evaluation_service.evaluate(db_session)
    attr_map = {item.action_type: item for item in report.action_attribution}

    retry_item = attr_map[RecoveryActionType.RETRY_PAYMENT.value]
    assert retry_item.sample_size == 2
    assert retry_item.recovered_count == 1
    assert retry_item.failed_count == 1
    assert retry_item.recovery_rate == 0.50
    assert retry_item.average_confidence == 0.85

    link_item = attr_map[RecoveryActionType.SEND_PAYMENT_LINK.value]
    assert link_item.sample_size == 1
    assert link_item.recovered_count == 1
    assert link_item.recovery_rate == 1.0


def test_confidence_vs_outcome_correlation(db_session: Session):
    """Test confidence difference and correlation between recovered and failed cases."""
    make_eval_case(db_session, status=RecoveryCaseStatus.RECOVERED.value, conf=0.95)
    make_eval_case(db_session, status=RecoveryCaseStatus.RECOVERED.value, conf=0.85)
    make_eval_case(
        db_session,
        status=RecoveryCaseStatus.CLOSED.value,
        recovered_amount=0,
        conf=0.40,
    )
    make_eval_case(
        db_session,
        status=RecoveryCaseStatus.CLOSED.value,
        recovered_amount=0,
        conf=0.50,
    )

    report = intelligence_evaluation_service.evaluate(db_session)
    c_out = report.confidence_outcomes

    assert c_out.sample_size == 4
    assert c_out.average_confidence_recovered == 0.90
    assert c_out.average_confidence_failed == 0.45
    assert c_out.confidence_difference == 0.45
    assert c_out.correlation is not None
    assert c_out.correlation > 0.80  # Strong positive correlation


# =========================================================================
# 5. Policy & Segmentation Tests
# =========================================================================


def test_policy_outcome_alignment(db_session: Session):
    """23-25. Test grouping outcomes by PolicyDecision (ALLOWED, BLOCKED, HUMAN_REVIEW)."""
    make_eval_case(
        db_session,
        status=RecoveryCaseStatus.RECOVERED.value,
        policy_result=PolicyEvaluationResult.ALLOWED.value,
    )
    make_eval_case(
        db_session,
        status=RecoveryCaseStatus.CLOSED.value,
        recovered_amount=0,
        policy_result=PolicyEvaluationResult.BLOCKED.value,
    )

    report = intelligence_evaluation_service.evaluate(db_session)
    pol_map = {item.policy_outcome: item for item in report.policy_alignment}

    assert pol_map[PolicyEvaluationResult.ALLOWED.value].recovered_count == 1
    assert pol_map[PolicyEvaluationResult.ALLOWED.value].recovery_rate == 1.0
    assert pol_map[PolicyEvaluationResult.BLOCKED.value].failed_count == 1
    assert pol_map[PolicyEvaluationResult.BLOCKED.value].recovery_rate == 0.0


def test_risk_tier_and_failure_reason_segmentation(db_session: Session):
    """26-27. Test segmentation by CustomerRiskTier and initial failure reason."""
    make_eval_case(
        db_session,
        status=RecoveryCaseStatus.RECOVERED.value,
        risk_tier=CustomerRiskTier.LOW.value,
        failure_reason="network_timeout",
    )
    make_eval_case(
        db_session,
        status=RecoveryCaseStatus.CLOSED.value,
        recovered_amount=0,
        risk_tier=CustomerRiskTier.HIGH.value,
        failure_reason="card_blocked",
    )

    report = intelligence_evaluation_service.evaluate(db_session)

    risk_map = {item.risk_tier: item for item in report.risk_segments}
    assert risk_map[CustomerRiskTier.LOW.value].recovery_rate == 1.0
    assert risk_map[CustomerRiskTier.HIGH.value].recovery_rate == 0.0

    reason_map = {item.failure_reason: item for item in report.failure_reason_segments}
    assert reason_map["network_timeout"].recovery_rate == 1.0
    assert reason_map["card_blocked"].recovery_rate == 0.0


# =========================================================================
# 6. Recovery Duration (MTTR) Tests
# =========================================================================


def test_recovery_duration_calculation(db_session: Session):
    """28-30. Test mean and median time to recovery (hours) on successfully recovered cases."""
    # Case 1: Duration 2.0 hours
    make_eval_case(
        db_session,
        status=RecoveryCaseStatus.RECOVERED.value,
        action_type=RecoveryActionType.RETRY_PAYMENT.value,
        duration_hours=2.0,
    )
    # Case 2: Duration 4.0 hours
    make_eval_case(
        db_session,
        status=RecoveryCaseStatus.RECOVERED.value,
        action_type=RecoveryActionType.RETRY_PAYMENT.value,
        duration_hours=4.0,
    )
    # Case 3: Failed case with 10.0 hours -> must NOT be included in recovered MTTR
    make_eval_case(
        db_session,
        status=RecoveryCaseStatus.CLOSED.value,
        recovered_amount=0,
        duration_hours=10.0,
    )

    report = intelligence_evaluation_service.evaluate(db_session)
    dur = report.recovery_duration

    assert dur.sample_size == 2
    assert dur.overall_average_hours == 3.0
    assert dur.overall_median_hours == 3.0


# =========================================================================
# 7. API Security, Observability & Immutability Tests
# =========================================================================


def test_unauthenticated_evaluation_request_rejected(db_session: Session):
    """31. Test unauthenticated request to /api/recovery/intelligence/evaluation returns 401."""

    def _override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = _override_get_db
    with TestClient(app) as unauth_client:
        res = unauth_client.get("/api/recovery/intelligence/evaluation")
        assert res.status_code == 401
    app.dependency_overrides.clear()


def test_viewer_can_read_evaluation(client: TestClient, db_session: Session):
    """32. Test authenticated viewer role can successfully fetch evaluation report."""
    make_eval_case(db_session, status=RecoveryCaseStatus.RECOVERED.value)
    res = client.get("/api/recovery/intelligence/evaluation")
    assert res.status_code == 200
    data = res.json()
    assert "classification" in data
    assert "calibration" in data
    assert "action_attribution" in data
    assert data["model"]["model_name"] == "recovery_probability"


def test_evaluation_is_strictly_read_only(client: TestClient, db_session: Session):
    """33. Test evaluation endpoint performs zero database mutations."""
    case = make_eval_case(db_session, status=RecoveryCaseStatus.RECOVERED.value)
    initial_updated_at = case.updated_at

    res = client.get("/api/recovery/intelligence/evaluation")
    assert res.status_code == 200

    # Ensure case state and timestamps remain unchanged
    db_session.refresh(case)
    assert case.updated_at == initial_updated_at
    assert case.status == RecoveryCaseStatus.RECOVERED.value


def test_data_integrity_zero_pii_and_secrets(client: TestClient, db_session: Session):
    """34-36. Test evaluation responses strictly contain zero PII and zero secrets."""
    make_eval_case(db_session, status=RecoveryCaseStatus.RECOVERED.value)
    res = client.get("/api/recovery/intelligence/evaluation")
    assert res.status_code == 200
    text = res.text.lower()

    assert "password" not in text
    assert "secret" not in text
    assert "bearer" not in text
    assert "@" not in text
    assert "email" not in text
    assert "phone" not in text
