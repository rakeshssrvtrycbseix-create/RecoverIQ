import uuid
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from unittest.mock import patch

import pytest
from sqlalchemy.orm import Session

from app.models import (
    AgentDecision,
    AuditActorType,
    AuditLog,
    Customer,
    CustomerRiskTier,
    Payment,
    PaymentAttempt,
    PaymentAttemptStatus,
    PaymentStatus,
    PolicyDecision,
    PolicyEvaluationResult,
    RecoveryAction,
    RecoveryActionType,
    RecoveryCase,
    RecoveryCaseStatus,
    RecoveryStage,
)
from app.policy.engine import policy_engine
from app.policy.exceptions import (
    AgentDecisionNotFoundError,
    PolicyPersistenceError,
)
from app.policy.rules import evaluate_rules


def create_policy_fixtures(
    db_session: Session,
    amount: int = 199900,
    attempts_count: int = 1,
    failure_reason: str = "insufficient_funds",
    case_status: str = RecoveryCaseStatus.OPEN.value,
    risk_tier: str = CustomerRiskTier.STANDARD.value,
    confidence_score: float = 0.85,
    action_type: str = RecoveryActionType.RETRY_PAYMENT.value,
    last_attempt_hours_ago: float = 3.0,
) -> tuple[Customer, Payment, RecoveryCase, AgentDecision, list[PaymentAttempt]]:
    """Helper to provision test database entities for Policy Engine tests."""
    customer = Customer(
        external_customer_id=f"cust_pol_{uuid.uuid4().hex[:8]}",
        email_masked="p***y@example.com",
        phone_masked="+91******7777",
        risk_tier=risk_tier,
        total_payments_count=5,
        failed_payments_count=1,
        recovered_payments_count=4,
    )
    db_session.add(customer)
    db_session.flush()

    payment = Payment(
        customer_id=customer.id,
        razorpay_order_id=f"order_pol_{uuid.uuid4().hex[:8]}",
        amount=amount,
        currency="INR",
        status=PaymentStatus.FAILED.value,
    )
    db_session.add(payment)
    db_session.flush()

    attempt_time = datetime.now(UTC) - timedelta(hours=last_attempt_hours_ago)
    attempt = PaymentAttempt(
        payment_id=payment.id,
        attempt_number=attempts_count,
        amount=amount,
        status=PaymentAttemptStatus.FAILED.value,
        error_code="BAD_REQUEST_ERROR",
        error_source="bank",
        error_step="payment_authorization",
        error_reason=failure_reason,
        initiated_at=attempt_time,
    )
    db_session.add(attempt)
    db_session.flush()

    case = RecoveryCase(
        payment_id=payment.id,
        customer_id=customer.id,
        status=case_status,
        recovery_stage=RecoveryStage.INITIAL_FAILURE.value,
        amount_at_risk=amount,
        recovered_amount=0,
        total_attempts_count=attempts_count,
        max_allowed_attempts=3,
        latest_failure_reason=failure_reason,
    )
    db_session.add(case)
    db_session.flush()

    agent_decision = AgentDecision(
        recovery_case_id=case.id,
        agent_name="RecoveryOrchestrator",
        agent_version="v1.0",
        prompt_template_version="recovery_agent_v1.0",
        proposed_action_type=action_type,
        confidence_score=Decimal(str(confidence_score)),
        reasoning_summary="Standard retry recommended for soft transient failure.",
        suggested_payload={"channel": "GATEWAY_API", "recommended_delay_hours": 2},
    )
    db_session.add(agent_decision)
    db_session.commit()
    db_session.refresh(case)
    db_session.refresh(payment)
    db_session.refresh(customer)
    db_session.refresh(agent_decision)

    return customer, payment, case, agent_decision, [attempt]


# =========================================================================
# 1. Core Rule & Evaluation Tests
# =========================================================================


def test_valid_allowed_decision(db_session: Session):
    """1, 4, 7, 13, 19. Test valid compliant retry action is ALLOWED."""
    customer, payment, case, agent_dec, attempts = create_policy_fixtures(
        db_session,
        amount=199900,
        attempts_count=1,
        failure_reason="insufficient_funds",
        confidence_score=0.85,
        last_attempt_hours_ago=3.0,
    )

    outcome = evaluate_rules(
        case, payment, customer, agent_dec, attempts
    )

    assert outcome.evaluation_result == PolicyEvaluationResult.ALLOWED
    assert outcome.triggered_rule_code is None
    assert "complies with all" in outcome.decision_reason


def test_max_attempts_blocked(db_session: Session):
    """2, 3. Test POL-MAX-ATTEMPTS blocks retry when attempts >= 3."""
    customer, payment, case, agent_dec, attempts = create_policy_fixtures(
        db_session, attempts_count=3, action_type=RecoveryActionType.RETRY_PAYMENT.value
    )

    outcome = evaluate_rules(
        case, payment, customer, agent_dec, attempts
    )

    assert outcome.evaluation_result == PolicyEvaluationResult.BLOCKED
    assert outcome.triggered_rule_code == "POL-MAX-ATTEMPTS"
    assert outcome.rule_name == "Maximum Attempts Ceiling"


def test_retry_rate_limit_blocked(db_session: Session):
    """5. Test POL-RATE-LIMIT blocks retry if < 2 hours since last attempt."""
    customer, payment, case, agent_dec, attempts = create_policy_fixtures(
        db_session,
        attempts_count=1,
        last_attempt_hours_ago=1.0,  # 1 hour ago < 2 hours
        action_type=RecoveryActionType.RETRY_PAYMENT.value,
    )

    outcome = evaluate_rules(
        case, payment, customer, agent_dec, attempts
    )

    assert outcome.evaluation_result == PolicyEvaluationResult.BLOCKED
    assert outcome.triggered_rule_code == "POL-RATE-LIMIT"
    assert outcome.rule_name == "Cool-Down Rate Limit Guard"


def test_retry_rate_limit_boundary_at_two_hours(db_session: Session):
    """6. Test retry exactly at / after 2 hours is ALLOWED."""
    customer, payment, case, agent_dec, attempts = create_policy_fixtures(
        db_session,
        attempts_count=1,
        last_attempt_hours_ago=2.001,  # >= 2.0 hours
        action_type=RecoveryActionType.RETRY_PAYMENT.value,
    )

    outcome = evaluate_rules(
        case, payment, customer, agent_dec, attempts
    )

    assert outcome.evaluation_result == PolicyEvaluationResult.ALLOWED


def test_permanent_card_blocked_error(db_session: Session):
    """8, 9, 10. Test POL-PERM-FAIL blocks retry on permanent failure reasons."""
    reasons = ["card_blocked", "account_closed", "fraud_suspected", "card_inactive"]

    for r in reasons:
        customer, payment, case, agent_dec, attempts = create_policy_fixtures(
            db_session,
            failure_reason=r,
            action_type=RecoveryActionType.RETRY_PAYMENT.value,
            last_attempt_hours_ago=5.0,
        )

        outcome = evaluate_rules(
            case, payment, customer, agent_dec, attempts
        )

        assert outcome.evaluation_result == PolicyEvaluationResult.BLOCKED
        assert outcome.triggered_rule_code == "POL-PERM-FAIL"
        assert outcome.rule_name == "Permanent Failure Guard"


def test_high_value_payment_human_review(db_session: Session):
    """11, 12. Test POL-HIGH-VALUE triggers HUMAN_REVIEW for amount >= ₹50,000."""
    customer, payment, case, agent_dec, attempts = create_policy_fixtures(
        db_session,
        amount=5000000,  # Exactly ₹50,000
        action_type=RecoveryActionType.RETRY_PAYMENT.value,
        last_attempt_hours_ago=5.0,
    )

    outcome = evaluate_rules(
        case, payment, customer, agent_dec, attempts
    )

    assert outcome.evaluation_result == PolicyEvaluationResult.HUMAN_REVIEW
    assert outcome.triggered_rule_code == "POL-HIGH-VALUE"
    assert outcome.rule_name == "High-Value Transaction Gate"


def test_below_high_value_allowed(db_session: Session):
    """13. Test transaction below ₹50,000 (e.g. ₹49,999) is ALLOWED."""
    customer, payment, case, agent_dec, attempts = create_policy_fixtures(
        db_session,
        amount=4999900,  # ₹49,999
        action_type=RecoveryActionType.RETRY_PAYMENT.value,
        last_attempt_hours_ago=5.0,
    )

    outcome = evaluate_rules(
        case, payment, customer, agent_dec, attempts
    )

    assert outcome.evaluation_result == PolicyEvaluationResult.ALLOWED


def test_blocked_customer_risk_tier(db_session: Session):
    """14. Test POL-RISK-TIER blocks any action on BLOCKED customers."""
    customer, payment, case, agent_dec, attempts = create_policy_fixtures(
        db_session,
        risk_tier=CustomerRiskTier.BLOCKED.value,
        action_type=RecoveryActionType.SEND_NOTIFICATION.value,
    )

    outcome = evaluate_rules(
        case, payment, customer, agent_dec, attempts
    )

    assert outcome.evaluation_result == PolicyEvaluationResult.BLOCKED
    assert outcome.triggered_rule_code == "POL-RISK-TIER"
    assert outcome.rule_name == "Blocked Customer Gate"


def test_resolved_or_closed_case_blocked(db_session: Session):
    """15, 16. Test POL-CASE-RESOLVED blocks actions on RECOVERED or CLOSED cases."""
    for st in [RecoveryCaseStatus.RECOVERED.value, RecoveryCaseStatus.CLOSED.value]:
        customer, payment, case, agent_dec, attempts = create_policy_fixtures(
            db_session,
            case_status=st,
            action_type=RecoveryActionType.RETRY_PAYMENT.value,
        )

        outcome = evaluate_rules(
            case, payment, customer, agent_dec, attempts
        )

        assert outcome.evaluation_result == PolicyEvaluationResult.BLOCKED
        assert outcome.triggered_rule_code == "POL-CASE-RESOLVED"
        assert outcome.rule_name == "Terminal Case Guard"


def test_low_ai_confidence_human_review(db_session: Session):
    """17, 18. Test POL-CONF-FLOOR forces HUMAN_REVIEW when confidence < 0.40."""
    customer, payment, case, agent_dec, attempts = create_policy_fixtures(
        db_session,
        confidence_score=0.35,
        action_type=RecoveryActionType.SEND_PAYMENT_LINK.value,
    )

    outcome = evaluate_rules(
        case, payment, customer, agent_dec, attempts
    )

    assert outcome.evaluation_result == PolicyEvaluationResult.HUMAN_REVIEW
    assert outcome.triggered_rule_code == "POL-CONF-FLOOR"
    assert outcome.rule_name == "Low AI Confidence Gate"


def test_confidence_at_or_above_floor_allowed(db_session: Session):
    """18, 19. Test confidence exactly 0.40 or above is ALLOWED."""
    customer, payment, case, agent_dec, attempts = create_policy_fixtures(
        db_session,
        confidence_score=0.40,
        action_type=RecoveryActionType.SEND_PAYMENT_LINK.value,
    )

    outcome = evaluate_rules(
        case, payment, customer, agent_dec, attempts
    )

    assert outcome.evaluation_result == PolicyEvaluationResult.ALLOWED


# =========================================================================
# 2. Action-Specific Applicability & Precedence Tests
# =========================================================================


def test_action_specific_applicability(db_session: Session):
    """20. Test rules only apply to relevant action types."""
    # Permanent error blocks RETRY_PAYMENT but allows SEND_PAYMENT_LINK
    customer, payment, case, agent_dec, attempts = create_policy_fixtures(
        db_session,
        failure_reason="card_blocked",
        action_type=RecoveryActionType.SEND_PAYMENT_LINK.value,
        last_attempt_hours_ago=5.0,
    )
    outcome = evaluate_rules(case, payment, customer, agent_dec, attempts)
    assert outcome.evaluation_result == PolicyEvaluationResult.ALLOWED

    # Rate limit blocks RETRY_PAYMENT but does not block ESCALATE_HUMAN
    customer2, payment2, case2, agent_dec2, attempts2 = create_policy_fixtures(
        db_session,
        action_type=RecoveryActionType.ESCALATE_HUMAN.value,
        last_attempt_hours_ago=0.5,  # 30 mins ago
    )
    outcome2 = evaluate_rules(case2, payment2, customer2, agent_dec2, attempts2)
    assert outcome2.evaluation_result == PolicyEvaluationResult.ALLOWED


def test_rule_precedence_combinations(db_session: Session):
    """21, 31. Test explicit precedence order when multiple rules match."""
    # Combination 1: Resolved Case + Blocked Customer -> POL-CASE-RESOLVED wins
    c1, p1, cs1, ad1, at1 = create_policy_fixtures(
        db_session,
        case_status=RecoveryCaseStatus.RECOVERED.value,
        risk_tier=CustomerRiskTier.BLOCKED.value,
    )
    out1 = evaluate_rules(cs1, p1, c1, ad1, at1)
    assert out1.triggered_rule_code == "POL-CASE-RESOLVED"

    # Combination 2: Blocked Customer + Max Attempts -> POL-RISK-TIER wins
    c2, p2, cs2, ad2, at2 = create_policy_fixtures(
        db_session,
        risk_tier=CustomerRiskTier.BLOCKED.value,
        attempts_count=3,
    )
    out2 = evaluate_rules(cs2, p2, c2, ad2, at2)
    assert out2.triggered_rule_code == "POL-RISK-TIER"

    # Combination 3: Max Attempts + Permanent Error -> POL-MAX-ATTEMPTS wins
    c3, p3, cs3, ad3, at3 = create_policy_fixtures(
        db_session,
        attempts_count=3,
        failure_reason="card_blocked",
    )
    out3 = evaluate_rules(cs3, p3, c3, ad3, at3)
    assert out3.triggered_rule_code == "POL-MAX-ATTEMPTS"

    # Combination 4: High Value + Low Confidence -> POL-HIGH-VALUE wins
    c4, p4, cs4, ad4, at4 = create_policy_fixtures(
        db_session,
        amount=6000000,
        confidence_score=0.30,
        action_type=RecoveryActionType.RETRY_PAYMENT.value,
        last_attempt_hours_ago=5.0,
    )
    out4 = evaluate_rules(cs4, p4, c4, ad4, at4)
    assert out4.triggered_rule_code == "POL-HIGH-VALUE"


# =========================================================================
# 3. Persistence, Immutability & Audit Log Tests
# =========================================================================


def test_policy_engine_persistence_and_audit(db_session: Session):
    """23, 24, 30. Test policy_engine.evaluate persists PolicyDecision and AuditLog."""
    _, _, case, agent_dec, _ = create_policy_fixtures(
        db_session,
        amount=199900,
        attempts_count=1,
        failure_reason="insufficient_funds",
        last_attempt_hours_ago=3.0,
    )

    policy_dec = policy_engine.evaluate(
        db=db_session,
        agent_decision_id=agent_dec.id,
    )

    # 1. Assert PolicyDecision
    assert policy_dec is not None
    assert policy_dec.recovery_case_id == case.id
    assert policy_dec.agent_decision_id == agent_dec.id
    assert policy_dec.evaluation_result == PolicyEvaluationResult.ALLOWED.value
    assert policy_dec.policy_engine_version == "policy_v1.0"
    assert "proposed_action_type" in policy_dec.evaluation_details

    # 2. Verify AuditLog
    audit = (
        db_session.query(AuditLog)
        .filter_by(
            recovery_case_id=case.id,
            entity_id=policy_dec.id,
            event_type="POLICY_DECISION_EVALUATED",
        )
        .first()
    )
    assert audit is not None
    assert audit.actor_type == AuditActorType.POLICY_ENGINE.value
    assert audit.actor_id == "policy_engine_v1"
    assert audit.action == "EVALUATE_POLICY"


def test_repeated_evaluation_creates_immutable_history(db_session: Session):
    """22, 26, 27. Test repeated evaluations create append-only rows."""
    _, _, case, agent_dec, _ = create_policy_fixtures(db_session)

    p1 = policy_engine.evaluate(db=db_session, agent_decision_id=agent_dec.id)
    p2 = policy_engine.evaluate(db=db_session, agent_decision_id=agent_dec.id)

    assert p1.id != p2.id

    count = (
        db_session.query(PolicyDecision)
        .filter_by(recovery_case_id=case.id)
        .count()
    )
    assert count == 2


def test_no_recovery_action_or_gateway_call_created(db_session: Session):
    """28, 29. Test PolicyEngine does NOT create RecoveryAction or gateway calls."""
    _, _, _, agent_dec, _ = create_policy_fixtures(db_session)

    init_actions = db_session.query(RecoveryAction).count()

    policy_engine.evaluate(db=db_session, agent_decision_id=agent_dec.id)

    final_actions = db_session.query(RecoveryAction).count()
    assert final_actions == init_actions == 0


def test_transaction_rollback_on_persistence_failure(db_session: Session):
    """25. Test atomic rollback if database commit crashes."""
    _, _, case, agent_dec, _ = create_policy_fixtures(db_session)

    with patch.object(
        db_session, "commit", side_effect=RuntimeError("Disk failure")
    ):
        with pytest.raises(PolicyPersistenceError):
            policy_engine.evaluate(
                db=db_session, agent_decision_id=agent_dec.id
            )

    # 0 PolicyDecisions committed
    count = (
        db_session.query(PolicyDecision)
        .filter_by(recovery_case_id=case.id)
        .count()
    )
    assert count == 0


def test_non_existent_agent_decision_raises_error(db_session: Session):
    """Test non-existent agent decision raises error."""
    fake_id = uuid.uuid4()
    with pytest.raises(AgentDecisionNotFoundError):
        policy_engine.evaluate(db=db_session, agent_decision_id=fake_id)
