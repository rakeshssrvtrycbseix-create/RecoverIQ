import uuid
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from unittest.mock import MagicMock, patch

import pytest
from sqlalchemy.orm import Session

from app.models import (
    ActionResult,
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
from app.providers.base import ProviderResult
from app.providers.mock import MockActionProvider
from app.services.action_dispatcher import (
    ActionExecutionPersistenceError,
    ActionNotDueError,
    ConcurrentExecutionError,
    InvalidActionStateError,
    InvalidActionTypeError,
    RecoveryActionNotFoundError,
    UnactionableCaseError,
    UnauthorizedActionError,
    UnsafeActionPayloadError,
    action_dispatcher,
)


def create_dispatcher_fixtures(
    db_session: Session,
    amount: int = 199900,
    case_status: str = RecoveryCaseStatus.OPEN.value,
    action_type: str = RecoveryActionType.RETRY_PAYMENT.value,
    action_status: str = RecoveryActionStatus.SCHEDULED.value,
    evaluation_result: str = PolicyEvaluationResult.ALLOWED.value,
    scheduled_hours_offset: float = -1.0,  # 1 hour in the past (due for execution)
    payload: dict | None = None,
) -> tuple[Customer, Payment, RecoveryCase, PolicyDecision, RecoveryAction]:
    """Helper to provision test database entities for Action Dispatcher tests."""
    customer = Customer(
        external_customer_id=f"cust_disp_{uuid.uuid4().hex[:8]}",
        email_masked="d***p@example.com",
        phone_masked="+91******5555",
        risk_tier=CustomerRiskTier.STANDARD.value,
        total_payments_count=5,
        failed_payments_count=1,
        recovered_payments_count=4,
    )
    db_session.add(customer)
    db_session.flush()

    payment = Payment(
        customer_id=customer.id,
        razorpay_order_id=f"order_disp_{uuid.uuid4().hex[:8]}",
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
        confidence_score=Decimal("0.88"),
        reasoning_summary="Smart retry approved.",
        suggested_payload={"channel": "GATEWAY_API"},
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
        decision_reason="Policy evaluation allowed.",
    )
    db_session.add(policy_decision)
    db_session.flush()

    scheduled_time = datetime.now(UTC) + timedelta(hours=scheduled_hours_offset)
    action = RecoveryAction(
        recovery_case_id=case.id,
        policy_decision_id=policy_decision.id,
        action_idempotency_key=f"act_{case.id}_{policy_decision.id}_{action_type}_{uuid.uuid4().hex[:6]}",
        action_type=action_type,
        status=action_status,
        scheduled_for=scheduled_time,
        action_payload=payload if payload is not None else {"channel": "GATEWAY_API"},
    )
    db_session.add(action)
    db_session.commit()

    db_session.refresh(case)
    db_session.refresh(payment)
    db_session.refresh(customer)
    db_session.refresh(policy_decision)
    db_session.refresh(action)

    return customer, payment, case, policy_decision, action


# =========================================================================
# 1. Successful Dispatch & Action Results Tests
# =========================================================================


def test_scheduled_action_executes_successfully(db_session: Session):
    """1, 13, 14. Test scheduled action transitions to COMPLETED, creates result & audit."""
    _, _, case, _, action = create_dispatcher_fixtures(db_session)

    result = action_dispatcher.dispatch_action(
        db=db_session,
        recovery_action_id=action.id,
    )

    # 1. Assert result fields
    assert result is not None
    assert result.recovery_action_id == action.id
    assert result.execution_status == "SUCCESS"
    assert result.provider_reference_id == f"mock_{action.id}"
    assert result.provider_status_code == "200"

    # 2. Assert action status
    db_session.refresh(action)
    assert action.status == RecoveryActionStatus.COMPLETED.value
    assert action.dispatched_at is not None
    assert action.completed_at is not None

    # 3. Assert AuditLog created
    audit = (
        db_session.query(AuditLog)
        .filter_by(
            recovery_case_id=case.id,
            entity_id=action.id,
            event_type="RECOVERY_ACTION_EXECUTED",
        )
        .first()
    )
    assert audit is not None
    assert audit.actor_type == AuditActorType.ACTION_EXECUTOR.value
    assert audit.actor_id == "action_dispatcher"
    assert audit.action == "RECOVERY_ACTION_EXECUTED"


def test_all_supported_action_types_mock_execution(db_session: Session):
    """8, 9, 10, 11, 12. Test execution of all 5 supported RecoveryActionType values."""
    actions = [
        (RecoveryActionType.RETRY_PAYMENT.value, "simulated_gateway_response"),
        (RecoveryActionType.SEND_PAYMENT_LINK.value, "simulated_link_id"),
        (RecoveryActionType.SEND_NOTIFICATION.value, "simulated_message_id"),
        (RecoveryActionType.ESCALATE_HUMAN.value, "simulated_ticket_id"),
        (RecoveryActionType.HALT_SUBSCRIPTION.value, "simulated_sub_status"),
    ]

    for action_type, expected_key in actions:
        _, _, _, _, action = create_dispatcher_fixtures(
            db_session, action_type=action_type
        )
        result = action_dispatcher.dispatch_action(
            db=db_session, recovery_action_id=action.id
        )

        assert result is not None
        assert result.execution_status == "SUCCESS"
        assert expected_key in result.response_payload_summary


# =========================================================================
# 2. Timing, Policy & Case Actionability Guards
# =========================================================================


def test_future_scheduled_action_not_executed(db_session: Session):
    """2. Test action scheduled in the future raises ActionNotDueError."""
    _, _, _, _, action = create_dispatcher_fixtures(
        db_session,
        scheduled_hours_offset=2.0,  # 2 hours in the future
    )

    with pytest.raises(ActionNotDueError, match="in the future"):
        action_dispatcher.dispatch_action(
            db=db_session,
            recovery_action_id=action.id,
        )


def test_non_scheduled_action_not_executed(db_session: Session):
    """3. Test action not in SCHEDULED status raises InvalidActionStateError."""
    _, _, _, _, action = create_dispatcher_fixtures(
        db_session,
        action_status=RecoveryActionStatus.PENDING.value,
    )

    with pytest.raises(InvalidActionStateError, match="unexpected status 'PENDING'"):
        action_dispatcher.dispatch_action(
            db=db_session,
            recovery_action_id=action.id,
        )


def test_blocked_policy_action_not_executed(db_session: Session):
    """4. Test action with BLOCKED policy outcome raises UnauthorizedActionError."""
    _, _, _, _, action = create_dispatcher_fixtures(
        db_session,
        evaluation_result=PolicyEvaluationResult.BLOCKED.value,
    )

    with pytest.raises(UnauthorizedActionError, match="policy evaluation 'BLOCKED'"):
        action_dispatcher.dispatch_action(
            db=db_session,
            recovery_action_id=action.id,
        )


def test_human_review_action_not_executed(db_session: Session):
    """5. Test action with HUMAN_REVIEW policy outcome raises UnauthorizedActionError."""
    _, _, _, _, action = create_dispatcher_fixtures(
        db_session,
        evaluation_result=PolicyEvaluationResult.HUMAN_REVIEW.value,
    )

    with pytest.raises(
        UnauthorizedActionError, match="policy evaluation 'HUMAN_REVIEW'"
    ):
        action_dispatcher.dispatch_action(
            db=db_session,
            recovery_action_id=action.id,
        )


def test_recovered_case_action_not_executed(db_session: Session):
    """6. Test action on RECOVERED case raises UnactionableCaseError."""
    _, _, _, _, action = create_dispatcher_fixtures(
        db_session,
        case_status=RecoveryCaseStatus.RECOVERED.value,
    )

    with pytest.raises(UnactionableCaseError, match="status 'RECOVERED'"):
        action_dispatcher.dispatch_action(
            db=db_session,
            recovery_action_id=action.id,
        )


def test_closed_case_action_not_executed(db_session: Session):
    """7. Test action on CLOSED case raises UnactionableCaseError."""
    _, _, _, _, action = create_dispatcher_fixtures(
        db_session,
        case_status=RecoveryCaseStatus.CLOSED.value,
    )

    with pytest.raises(UnactionableCaseError, match="status 'CLOSED'"):
        action_dispatcher.dispatch_action(
            db=db_session,
            recovery_action_id=action.id,
        )


def test_invalid_action_type_rejected(db_session: Session):
    """22. Test invalid action type is rejected."""
    _, _, _, _, action = create_dispatcher_fixtures(db_session)
    action.action_type = "UNKNOWN_ACTION_TYPE"
    db_session.commit()

    with pytest.raises(InvalidActionTypeError, match="Unsupported action type"):
        action_dispatcher.dispatch_action(
            db=db_session,
            recovery_action_id=action.id,
        )


# =========================================================================
# 3. Provider Failures & Exceptions Tests
# =========================================================================


def test_provider_failure_marks_action_failed(db_session: Session):
    """15, 16, 17. Test provider failure marks action FAILED and creates audit log."""
    _, _, case, _, action = create_dispatcher_fixtures(db_session)

    failing_provider = MockActionProvider(
        force_failure=True,
        failure_reason="CARD_AUTH_FAILED",
        error_details="Customer card issuer rejected authorization request",
    )

    result = action_dispatcher.dispatch_action(
        db=db_session,
        recovery_action_id=action.id,
        provider=failing_provider,
    )

    # 1. Assert result fields
    assert result is not None
    assert result.execution_status == "FAILED"
    assert result.failure_reason == "CARD_AUTH_FAILED"
    assert "rejected authorization" in (result.error_details or "")

    # 2. Assert action status FAILED
    db_session.refresh(action)
    assert action.status == RecoveryActionStatus.FAILED.value

    # 3. Assert AuditLog created
    audit = (
        db_session.query(AuditLog)
        .filter_by(
            recovery_case_id=case.id,
            entity_id=action.id,
            event_type="RECOVERY_ACTION_FAILED",
        )
        .first()
    )
    assert audit is not None
    assert audit.action == "RECOVERY_ACTION_FAILED"


def test_provider_exception_is_handled(db_session: Session):
    """23. Test unhandled provider exception is safely converted into a failed result."""
    _, _, _, _, action = create_dispatcher_fixtures(db_session)

    exploding_provider = MockActionProvider(force_exception=True)

    result = action_dispatcher.dispatch_action(
        db=db_session,
        recovery_action_id=action.id,
        provider=exploding_provider,
    )

    assert result is not None
    assert result.execution_status == "FAILED"
    assert result.failure_reason == "PROVIDER_EXCEPTION"

    db_session.refresh(action)
    assert action.status == RecoveryActionStatus.FAILED.value


def test_gateway_timeout_keeps_action_executing(db_session: Session):
    """Test gateway timeout keeps RecoveryAction in EXECUTING state for reconciliation."""
    _, _, _, _, action = create_dispatcher_fixtures(db_session)

    class TimeoutProvider:
        def execute(self, action, context=None):
            return ProviderResult(
                success=False,
                execution_status="TIMED_OUT",
                provider_reference_id=f"rec_{action.id}",
                provider_status_code="408",
                failure_reason="GATEWAY_TIMEOUT",
                error_details="Connection to gateway timed out",
                response_payload_summary={"timeout": True},
                executed_at=datetime.now(UTC),
            )

    result = action_dispatcher.dispatch_action(
        db=db_session,
        recovery_action_id=action.id,
        provider=TimeoutProvider(),  # type: ignore
    )

    # 1. Assert result execution_status is TIMED_OUT
    assert result is not None
    assert result.execution_status == "TIMED_OUT"
    assert result.failure_reason == "GATEWAY_TIMEOUT"
    assert result.provider_status_code == "408"

    # 2. Assert RecoveryAction remains EXECUTING (not FAILED)
    db_session.refresh(action)
    assert action.status == RecoveryActionStatus.EXECUTING.value
    assert action.dispatched_at is not None
    assert action.completed_at is None


def test_gateway_timeout_creates_timeout_action_result_and_audit_log(
    db_session: Session,
):
    """Test gateway timeout persists ActionResult(TIMED_OUT) and AuditLog(ACTION_EXECUTION_TIMED_OUT)."""
    _, _, case, _, action = create_dispatcher_fixtures(db_session)

    class TimeoutProvider:
        def execute(self, action, context=None):
            return ProviderResult(
                success=False,
                execution_status="TIMED_OUT",
                provider_reference_id=f"rec_{action.id}",
                provider_status_code="408",
                failure_reason="GATEWAY_TIMEOUT",
                error_details="Connection to gateway timed out",
                response_payload_summary={"timeout": True},
                executed_at=datetime.now(UTC),
            )

    action_dispatcher.dispatch_action(
        db=db_session,
        recovery_action_id=action.id,
        provider=TimeoutProvider(),  # type: ignore
    )

    # 1. Assert ActionResult row in database
    db_result = (
        db_session.query(ActionResult).filter_by(recovery_action_id=action.id).first()
    )
    assert db_result is not None
    assert db_result.execution_status == "TIMED_OUT"
    assert db_result.failure_reason == "GATEWAY_TIMEOUT"

    # 2. Assert AuditLog row in database
    audit = (
        db_session.query(AuditLog)
        .filter_by(
            recovery_case_id=case.id,
            entity_id=action.id,
            event_type="ACTION_EXECUTION_TIMED_OUT",
        )
        .first()
    )
    assert audit is not None
    assert audit.action == "ACTION_EXECUTION_TIMED_OUT"
    assert audit.actor_id == "action_dispatcher"


# =========================================================================
# 4. Idempotency, Concurrency & Retry Behavior Tests
# =========================================================================


def test_already_completed_action_is_idempotent(db_session: Session):
    """18, 19. Test repeated dispatch of COMPLETED action returns result with 0 calls."""
    _, _, _, _, action = create_dispatcher_fixtures(db_session)

    mock_provider = MockActionProvider()
    mock_provider.execute = MagicMock(wraps=mock_provider.execute)  # type: ignore

    res1 = action_dispatcher.dispatch_action(
        db=db_session, recovery_action_id=action.id, provider=mock_provider
    )
    assert mock_provider.execute.call_count == 1

    res2 = action_dispatcher.dispatch_action(
        db=db_session, recovery_action_id=action.id, provider=mock_provider
    )
    # Second call should NOT execute the provider again
    assert mock_provider.execute.call_count == 1
    assert res1 is not None and res2 is not None
    assert res1.id == res2.id


def test_failed_action_is_not_automatically_retried(db_session: Session):
    """27. Test that FAILED actions are not retried in Phase 7B."""
    _, _, _, _, action = create_dispatcher_fixtures(db_session)

    failing_provider = MockActionProvider(force_failure=True)
    res1 = action_dispatcher.dispatch_action(
        db=db_session, recovery_action_id=action.id, provider=failing_provider
    )
    assert res1.execution_status == "FAILED"

    # Second call returns existing failed result without retrying
    res2 = action_dispatcher.dispatch_action(
        db=db_session, recovery_action_id=action.id, provider=failing_provider
    )
    assert res2.id == res1.id


def test_concurrent_dispatch_does_not_execute_twice(db_session: Session):
    """20. Test that an action currently EXECUTING raises ConcurrentExecutionError."""
    _, _, _, _, action = create_dispatcher_fixtures(
        db_session,
        action_status=RecoveryActionStatus.EXECUTING.value,
    )

    with pytest.raises(ConcurrentExecutionError, match="currently EXECUTING"):
        action_dispatcher.dispatch_action(
            db=db_session,
            recovery_action_id=action.id,
        )


# =========================================================================
# 5. Security, State Invariance & Rollback Tests
# =========================================================================


def test_sensitive_payload_rejected(db_session: Session):
    """24. Test that sensitive credentials and PII in action_payload are rejected."""
    sensitive_payloads = [
        {"api_key": "sec_12345"},
        {"note": "Card number 4111 1111 1111 1111"},
        {"contact_email": "user@domain.com"},
        {"auth": "Bearer rzp_live_998877665544"},
        {"webhook_secret": "whsec_live_999"},
    ]

    for p in sensitive_payloads:
        _, _, _, _, action = create_dispatcher_fixtures(
            db_session,
            payload=p,
        )
        with pytest.raises(UnsafeActionPayloadError):
            action_dispatcher.dispatch_action(
                db=db_session,
                recovery_action_id=action.id,
            )


def test_payment_and_case_status_not_modified(db_session: Session):
    """25, 26. Test dispatcher NEVER mutates Payment.status or RecoveryCase.status."""
    customer, payment, case, _, action = create_dispatcher_fixtures(db_session)

    init_pay_status = payment.status
    init_case_status = case.status

    action_dispatcher.dispatch_action(
        db=db_session,
        recovery_action_id=action.id,
    )

    db_session.refresh(payment)
    db_session.refresh(case)
    assert payment.status == init_pay_status
    assert case.status == init_case_status


def test_database_failure_rolls_back_execution(db_session: Session):
    """21. Test database failure during final commit rolls back cleanly."""
    _, _, _, _, action = create_dispatcher_fixtures(db_session)

    # Patch commit during final step
    orig_commit = db_session.commit
    call_count = 0

    def fail_on_second_commit():
        nonlocal call_count
        call_count += 1
        if call_count > 1:
            raise RuntimeError("Database disk failure during result commit")
        orig_commit()

    with patch.object(db_session, "commit", side_effect=fail_on_second_commit):
        with pytest.raises(ActionExecutionPersistenceError):
            action_dispatcher.dispatch_action(
                db=db_session,
                recovery_action_id=action.id,
            )


def test_action_not_found_raises_domain_exception(db_session: Session):
    """Test non-existent recovery action raises RecoveryActionNotFoundError."""
    fake_id = uuid.uuid4()
    with pytest.raises(RecoveryActionNotFoundError):
        action_dispatcher.dispatch_action(
            db=db_session,
            recovery_action_id=fake_id,
        )
