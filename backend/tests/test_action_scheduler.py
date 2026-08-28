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
    RecoveryActionStatus,
    RecoveryActionType,
    RecoveryCase,
    RecoveryCaseStatus,
    RecoveryStage,
)
from app.services.action_scheduler import action_scheduler
from app.services.recovery_action_service import (
    ActionPersistenceError,
    InvalidActionTypeError,
    PolicyDecisionNotFoundError,
    PolicyNotAllowedError,
    RecoveryCaseNotFoundError,
    UnactionableCaseError,
    recovery_action_service,
)


def create_scheduler_fixtures(
    db_session: Session,
    amount: int = 199900,
    case_status: str = RecoveryCaseStatus.OPEN.value,
    action_type: str = RecoveryActionType.RETRY_PAYMENT.value,
    evaluation_result: str = PolicyEvaluationResult.ALLOWED.value,
    recommended_delay_hours: int = 2,
    confidence_score: float = 0.85,
) -> tuple[Customer, Payment, RecoveryCase, AgentDecision, PolicyDecision]:
    """Helper to provision test database entities for Action Scheduler tests."""
    customer = Customer(
        external_customer_id=f"cust_act_{uuid.uuid4().hex[:8]}",
        email_masked="a***t@example.com",
        phone_masked="+91******6666",
        risk_tier=CustomerRiskTier.STANDARD.value,
        total_payments_count=5,
        failed_payments_count=1,
        recovered_payments_count=4,
    )
    db_session.add(customer)
    db_session.flush()

    payment = Payment(
        customer_id=customer.id,
        razorpay_order_id=f"order_act_{uuid.uuid4().hex[:8]}",
        amount=amount,
        currency="INR",
        status=PaymentStatus.FAILED.value,
    )
    db_session.add(payment)
    db_session.flush()

    attempt = PaymentAttempt(
        payment_id=payment.id,
        attempt_number=1,
        amount=amount,
        status=PaymentAttemptStatus.FAILED.value,
        error_code="BAD_REQUEST_ERROR",
        error_source="bank",
        error_step="payment_authorization",
        error_reason="insufficient_funds",
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
        total_attempts_count=1,
        max_allowed_attempts=3,
        latest_failure_reason="insufficient_funds",
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
        reasoning_summary="Automated smart retry authorized.",
        suggested_payload={
            "channel": "GATEWAY_API",
            "recommended_delay_hours": recommended_delay_hours,
        },
    )
    db_session.add(agent_decision)
    db_session.flush()

    policy_decision = PolicyDecision(
        recovery_case_id=case.id,
        agent_decision_id=agent_decision.id,
        evaluation_result=evaluation_result,
        policy_engine_version="policy_v1.0",
        triggered_rule_code=None if evaluation_result == "ALLOWED" else "POL-MOCK",
        rule_name=None if evaluation_result == "ALLOWED" else "Mock Rule",
        evaluation_details={"proposed_action_type": action_type},
        decision_reason="Policy evaluation justification.",
    )
    db_session.add(policy_decision)
    db_session.commit()

    db_session.refresh(case)
    db_session.refresh(payment)
    db_session.refresh(customer)
    db_session.refresh(agent_decision)
    db_session.refresh(policy_decision)

    return customer, payment, case, agent_decision, policy_decision


# =========================================================================
# 1. Action Creation & Policy Outcomes Tests
# =========================================================================


def test_allowed_policy_creates_scheduled_action(db_session: Session):
    """1, 12. Test that an ALLOWED policy outcome creates a SCHEDULED RecoveryAction."""
    _, _, case, agent_dec, policy_dec = create_scheduler_fixtures(
        db_session,
        evaluation_result=PolicyEvaluationResult.ALLOWED.value,
        recommended_delay_hours=4,
    )

    now = datetime(2026, 8, 28, 12, 0, 0, tzinfo=UTC)
    action = action_scheduler.schedule_for_policy_decision(
        db=db_session,
        policy_decision_id=policy_dec.id,
        as_of=now,
    )

    # 1. Assert action attributes
    assert action is not None
    assert action.recovery_case_id == case.id
    assert action.policy_decision_id == policy_dec.id
    assert action.action_type == RecoveryActionType.RETRY_PAYMENT.value
    assert action.status == RecoveryActionStatus.SCHEDULED.value
    expected_time = now + timedelta(hours=4)
    assert action.scheduled_for.replace(tzinfo=UTC) == expected_time
    assert action.action_idempotency_key == (
        f"act_{case.id}_{policy_dec.id}_{action.action_type}"
    )

    # 2. Assert stored in DB
    stored = db_session.query(RecoveryAction).filter_by(id=action.id).first()
    assert stored is not None
    assert stored.status == RecoveryActionStatus.SCHEDULED.value

    # 3. Assert AuditLog created
    audit = (
        db_session.query(AuditLog)
        .filter_by(
            recovery_case_id=case.id,
            entity_id=action.id,
            event_type="RECOVERY_ACTION_SCHEDULED",
        )
        .first()
    )
    assert audit is not None
    assert audit.actor_type == AuditActorType.SYSTEM_EVENT.value
    assert audit.actor_id == "action_scheduler"
    assert audit.action == "RECOVERY_ACTION_SCHEDULED"


def test_blocked_policy_creates_zero_actions(db_session: Session):
    """2. Test that a BLOCKED policy outcome creates ZERO RecoveryAction records."""
    _, _, case, _, policy_dec = create_scheduler_fixtures(
        db_session,
        evaluation_result=PolicyEvaluationResult.BLOCKED.value,
    )

    action = action_scheduler.schedule_for_policy_decision(
        db=db_session,
        policy_decision_id=policy_dec.id,
    )

    # Assert None returned and 0 actions created
    assert action is None
    actions_count = (
        db_session.query(RecoveryAction)
        .filter_by(recovery_case_id=case.id)
        .count()
    )
    assert actions_count == 0

    # Verify AuditLog created for blocked action
    audit = (
        db_session.query(AuditLog)
        .filter_by(
            recovery_case_id=case.id,
            entity_id=policy_dec.id,
            event_type="RECOVERY_ACTION_BLOCKED",
        )
        .first()
    )
    assert audit is not None
    assert audit.action == "RECOVERY_ACTION_BLOCKED"


def test_human_review_policy_creates_zero_actions(db_session: Session):
    """3. Test that HUMAN_REVIEW policy outcome creates ZERO RecoveryAction records."""
    _, _, case, _, policy_dec = create_scheduler_fixtures(
        db_session,
        evaluation_result=PolicyEvaluationResult.HUMAN_REVIEW.value,
    )

    action = action_scheduler.schedule_for_policy_decision(
        db=db_session,
        policy_decision_id=policy_dec.id,
    )

    # Assert None returned and 0 actions created
    assert action is None
    actions_count = (
        db_session.query(RecoveryAction)
        .filter_by(recovery_case_id=case.id)
        .count()
    )
    assert actions_count == 0

    # Verify AuditLog created for human review
    audit = (
        db_session.query(AuditLog)
        .filter_by(
            recovery_case_id=case.id,
            entity_id=policy_dec.id,
            event_type="RECOVERY_ACTION_HUMAN_REVIEW",
        )
        .first()
    )
    assert audit is not None
    assert audit.action == "RECOVERY_ACTION_HUMAN_REVIEW"


# =========================================================================
# 2. Case Actionability & Rejection Tests
# =========================================================================


def test_resolved_case_cannot_create_action(db_session: Session):
    """4. Test that scheduling for RECOVERED case raises UnactionableCaseError."""
    _, _, case, _, policy_dec = create_scheduler_fixtures(
        db_session,
        case_status=RecoveryCaseStatus.RECOVERED.value,
        evaluation_result=PolicyEvaluationResult.ALLOWED.value,
    )

    with pytest.raises(UnactionableCaseError, match="status 'RECOVERED'"):
        action_scheduler.schedule_for_policy_decision(
            db=db_session,
            policy_decision_id=policy_dec.id,
        )


def test_closed_case_cannot_create_action(db_session: Session):
    """5. Test that scheduling for CLOSED case raises UnactionableCaseError."""
    _, _, case, _, policy_dec = create_scheduler_fixtures(
        db_session,
        case_status=RecoveryCaseStatus.CLOSED.value,
        evaluation_result=PolicyEvaluationResult.ALLOWED.value,
    )

    with pytest.raises(UnactionableCaseError, match="status 'CLOSED'"):
        action_scheduler.schedule_for_policy_decision(
            db=db_session,
            policy_decision_id=policy_dec.id,
        )


def test_invalid_action_type_rejected(db_session: Session):
    """6. Test invalid action type raises InvalidActionTypeError."""
    _, _, case, agent_dec, policy_dec = create_scheduler_fixtures(
        db_session,
        evaluation_result=PolicyEvaluationResult.ALLOWED.value,
    )
    agent_dec.proposed_action_type = "INVALID_TYPE"
    policy_dec.evaluation_details = {"proposed_action_type": "INVALID_TYPE"}
    db_session.commit()

    with pytest.raises(InvalidActionTypeError, match="Invalid or missing action_type"):
        recovery_action_service.create_recovery_action(
            db=db_session,
            policy_decision=policy_dec,
            agent_decision=agent_dec,
        )


def test_direct_service_call_on_blocked_policy_rejected(db_session: Session):
    """Test calling service with BLOCKED policy raises PolicyNotAllowedError."""
    _, _, _, agent_dec, policy_dec = create_scheduler_fixtures(
        db_session,
        evaluation_result=PolicyEvaluationResult.BLOCKED.value,
    )

    with pytest.raises(PolicyNotAllowedError, match="Only ALLOWED policy decisions"):
        recovery_action_service.create_recovery_action(
            db=db_session,
            policy_decision=policy_dec,
            agent_decision=agent_dec,
        )


# =========================================================================
# 3. Idempotency & Delay Tests
# =========================================================================


def test_idempotency_prevents_duplicate_action(db_session: Session):
    """7, 8, 16, 17. Test idempotency key prevents duplicate actions."""
    _, _, case, _, policy_dec = create_scheduler_fixtures(
        db_session,
        evaluation_result=PolicyEvaluationResult.ALLOWED.value,
    )

    a1 = action_scheduler.schedule_for_policy_decision(
        db=db_session,
        policy_decision_id=policy_dec.id,
    )
    a2 = action_scheduler.schedule_for_policy_decision(
        db=db_session,
        policy_decision_id=policy_dec.id,
    )

    # Both return the exact same action entity without duplicating
    assert a1 is not None
    assert a2 is not None
    assert a1.id == a2.id

    actions_count = (
        db_session.query(RecoveryAction)
        .filter_by(recovery_case_id=case.id)
        .count()
    )
    assert actions_count == 1


def test_zero_delay_schedules_immediately(db_session: Session):
    """9, 10. Test that 0 recommended_delay_hours schedules at current timestamp."""
    _, _, _, _, policy_dec = create_scheduler_fixtures(
        db_session,
        evaluation_result=PolicyEvaluationResult.ALLOWED.value,
        recommended_delay_hours=0,
    )

    now = datetime(2026, 8, 28, 15, 30, 0, tzinfo=UTC)
    action = action_scheduler.schedule_for_policy_decision(
        db=db_session,
        policy_decision_id=policy_dec.id,
        as_of=now,
    )

    assert action is not None
    assert action.scheduled_for.replace(tzinfo=UTC) == now


def test_future_delay_schedules_correctly(db_session: Session):
    """11. Test positive recommended_delay_hours schedules at exact future time."""
    _, _, _, _, policy_dec = create_scheduler_fixtures(
        db_session,
        evaluation_result=PolicyEvaluationResult.ALLOWED.value,
        recommended_delay_hours=12,
    )

    now = datetime(2026, 8, 28, 10, 0, 0, tzinfo=UTC)
    action = action_scheduler.schedule_for_policy_decision(
        db=db_session,
        policy_decision_id=policy_dec.id,
        as_of=now,
    )

    assert action is not None
    assert action.scheduled_for.replace(tzinfo=UTC) == now + timedelta(hours=12)


# =========================================================================
# 4. Error Handling & Rollback Tests
# =========================================================================


def test_policy_decision_not_found_raises_domain_error(db_session: Session):
    """14. Test non-existent PolicyDecision raises PolicyDecisionNotFoundError."""
    fake_id = uuid.uuid4()
    with pytest.raises(PolicyDecisionNotFoundError):
        action_scheduler.schedule_for_policy_decision(
            db=db_session,
            policy_decision_id=fake_id,
        )


def test_recovery_case_not_found_raises_domain_error(db_session: Session):
    """15. Test missing RecoveryCase raises RecoveryCaseNotFoundError."""
    _, _, _, _, policy_dec = create_scheduler_fixtures(db_session)

    orig_query = db_session.query

    class MockResult:
        def first(self):
            return None

    class MockQuery:
        def filter_by(self, **kwargs):
            return MockResult()

    with patch.object(
        db_session,
        "query",
        side_effect=lambda model: (
            MockQuery() if model == RecoveryCase else orig_query(model)
        ),
    ):
        with pytest.raises(RecoveryCaseNotFoundError):
            action_scheduler.schedule_for_policy_decision(
                db=db_session,
                policy_decision_id=policy_dec.id,
            )


def test_database_failure_rolls_back_action_and_audit(db_session: Session):
    """13. Test database commit failure rolls back cleanly."""
    _, _, case, _, policy_dec = create_scheduler_fixtures(db_session)

    with patch.object(
        db_session, "commit", side_effect=RuntimeError("Disk failure")
    ):
        with pytest.raises(ActionPersistenceError):
            action_scheduler.schedule_for_policy_decision(
                db=db_session,
                policy_decision_id=policy_dec.id,
            )

    # 0 RecoveryActions committed
    count = (
        db_session.query(RecoveryAction)
        .filter_by(recovery_case_id=case.id)
        .count()
    )
    assert count == 0


def test_no_gateway_or_state_mutation(db_session: Session):
    """18, 19, 20. Test scheduler never modifies Payment/Case status."""
    customer, payment, case, _, policy_dec = create_scheduler_fixtures(db_session)

    init_pay_status = payment.status
    init_case_status = case.status

    action = action_scheduler.schedule_for_policy_decision(
        db=db_session,
        policy_decision_id=policy_dec.id,
    )

    assert action is not None
    assert payment.status == init_pay_status
    assert case.status == init_case_status
