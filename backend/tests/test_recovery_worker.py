import uuid
from datetime import UTC, datetime, timedelta
from decimal import Decimal

from sqlalchemy.orm import Session

from app.models import (
    AgentDecision,
    AuditLog,
    Customer,
    CustomerRiskTier,
    Payment,
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
from app.workers.recovery_worker import RecoveryWorker
from app.workers.runner import WorkerRunner
from app.workers.telemetry import worker_telemetry


def create_worker_test_action(
    db_session: Session,
    status: str = RecoveryActionStatus.SCHEDULED.value,
    hours_offset: float = -1.0,
    action_type: str = RecoveryActionType.RETRY_PAYMENT.value,
) -> tuple[RecoveryCase, RecoveryAction]:
    """Helper to provision test database entities for worker tests."""
    customer = Customer(
        external_customer_id=f"cust_w_{uuid.uuid4().hex[:8]}",
        email_masked="w***r@example.com",
        phone_masked="+91******1111",
        risk_tier=CustomerRiskTier.STANDARD.value,
        total_payments_count=5,
        failed_payments_count=1,
        recovered_payments_count=4,
    )
    db_session.add(customer)
    db_session.flush()

    payment = Payment(
        customer_id=customer.id,
        razorpay_order_id=f"order_w_{uuid.uuid4().hex[:8]}",
        amount=199900,
        currency="INR",
        status=PaymentStatus.FAILED.value,
    )
    db_session.add(payment)
    db_session.flush()

    case = RecoveryCase(
        payment_id=payment.id,
        customer_id=customer.id,
        status=RecoveryCaseStatus.OPEN.value,
        recovery_stage=RecoveryStage.INITIAL_FAILURE.value,
        amount_at_risk=199900,
        recovered_amount=0,
        total_attempts_count=1,
        max_allowed_attempts=3,
        latest_failure_reason="insufficient_funds",
    )
    db_session.add(case)
    db_session.flush()

    agent_dec = AgentDecision(
        recovery_case_id=case.id,
        agent_name="RecoveryOrchestrator",
        agent_version="v1.0",
        prompt_template_version="recovery_agent_v1.0",
        proposed_action_type=action_type,
        confidence_score=Decimal("0.85"),
        reasoning_summary="Smart retry approved.",
    )
    db_session.add(agent_dec)
    db_session.flush()

    pol_dec = PolicyDecision(
        recovery_case_id=case.id,
        agent_decision_id=agent_dec.id,
        evaluation_result=PolicyEvaluationResult.ALLOWED.value,
        policy_engine_version="policy_v1.0",
        decision_reason="Policy allowed.",
    )
    db_session.add(pol_dec)
    db_session.flush()

    sched_time = datetime.now(UTC) + timedelta(hours=hours_offset)
    action = RecoveryAction(
        recovery_case_id=case.id,
        policy_decision_id=pol_dec.id,
        action_idempotency_key=f"act_w_{case.id}_{pol_dec.id}_{action_type}_{uuid.uuid4().hex[:6]}",
        action_type=action_type,
        status=status,
        scheduled_for=sched_time,
        action_payload={"channel": "GATEWAY_API"},
    )
    db_session.add(action)
    db_session.commit()

    db_session.refresh(case)
    db_session.refresh(action)
    return case, action


# =========================================================================
# Scheduling & Polling Tests
# =========================================================================


def test_due_scheduled_action_is_claimed_and_dispatched(db_session: Session):
    """1. Test due SCHEDULED action (scheduled in past) is claimed and reaches COMPLETED."""
    _, action = create_worker_test_action(
        db_session, status=RecoveryActionStatus.SCHEDULED.value, hours_offset=-1.0
    )

    worker = RecoveryWorker()
    results = worker.poll_and_dispatch(db=db_session)

    assert len(results) == 1
    assert results[0].execution_status == "SUCCESS"

    db_session.refresh(action)
    assert action.status == RecoveryActionStatus.COMPLETED.value


def test_future_action_is_ignored_by_worker(db_session: Session):
    """2. Test action scheduled in the future is ignored by worker polling."""
    _, action = create_worker_test_action(
        db_session, status=RecoveryActionStatus.SCHEDULED.value, hours_offset=2.0
    )

    worker = RecoveryWorker()
    results = worker.poll_and_dispatch(db=db_session)

    assert len(results) == 0
    db_session.refresh(action)
    assert action.status == RecoveryActionStatus.SCHEDULED.value


def test_non_scheduled_action_is_ignored_by_worker(db_session: Session):
    """3. Test non-SCHEDULED actions (PENDING, CANCELLED) are ignored."""
    _, action = create_worker_test_action(
        db_session, status=RecoveryActionStatus.PENDING.value, hours_offset=-1.0
    )

    worker = RecoveryWorker()
    results = worker.poll_and_dispatch(db=db_session)

    assert len(results) == 0
    db_session.refresh(action)
    assert action.status == RecoveryActionStatus.PENDING.value


def test_multiple_due_actions_are_processed_in_batch(db_session: Session):
    """4. Test multiple due actions are claimed and dispatched in batch."""
    _, a1 = create_worker_test_action(db_session, hours_offset=-2.0)
    _, a2 = create_worker_test_action(db_session, hours_offset=-1.0)

    worker = RecoveryWorker()
    results = worker.poll_and_dispatch(db=db_session)

    assert len(results) == 2
    db_session.refresh(a1)
    db_session.refresh(a2)
    assert a1.status == RecoveryActionStatus.COMPLETED.value
    assert a2.status == RecoveryActionStatus.COMPLETED.value


def test_empty_queue_is_handled_safely(db_session: Session):
    """5. Test polling with empty queue returns empty list with 0 errors."""
    worker = RecoveryWorker()
    results = worker.poll_and_dispatch(db=db_session)
    assert results == []


# =========================================================================
# Dispatcher Integration & Outcomes Tests
# =========================================================================


def test_worker_calls_action_dispatcher_pipeline(db_session: Session):
    """11, 12. Test worker dispatches through ActionDispatcher and writes audit log."""
    case, action = create_worker_test_action(db_session, hours_offset=-1.0)

    worker = RecoveryWorker()
    results = worker.poll_and_dispatch(db=db_session)

    assert len(results) == 1
    assert results[0].recovery_action_id == action.id

    # Verify audit log created
    audit = (
        db_session.query(AuditLog)
        .filter_by(recovery_case_id=case.id, entity_id=action.id)
        .first()
    )
    assert audit is not None
    assert audit.action == "RECOVERY_ACTION_EXECUTED"


def test_failed_provider_action_reaches_failed(db_session: Session):
    """13. Test provider failure marks action FAILED."""
    _, action = create_worker_test_action(db_session, hours_offset=-1.0)

    class FailingProvider:
        def execute(self, act, context=None):
            return ProviderResult(
                success=False,
                execution_status="FAILED",
                provider_reference_id=f"rec_{act.id}",
                provider_status_code="500",
                failure_reason="CARD_DECLINED",
                error_details="Insufficient balance",
                executed_at=datetime.now(UTC),
            )

    worker = RecoveryWorker()
    results = worker.poll_and_dispatch(db=db_session, provider=FailingProvider())  # type: ignore

    assert len(results) == 1
    assert results[0].execution_status == "FAILED"

    db_session.refresh(action)
    assert action.status == RecoveryActionStatus.FAILED.value


def test_timeout_action_remains_executing(db_session: Session):
    """14. Test timeout keeps action in EXECUTING for reconciliation."""
    _, action = create_worker_test_action(db_session, hours_offset=-1.0)

    class TimeoutProvider:
        def execute(self, act, context=None):
            return ProviderResult(
                success=False,
                execution_status="TIMED_OUT",
                provider_reference_id=f"rec_{act.id}",
                provider_status_code="408",
                failure_reason="GATEWAY_TIMEOUT",
                error_details="Timeout",
                executed_at=datetime.now(UTC),
            )

    worker = RecoveryWorker()
    results = worker.poll_and_dispatch(db=db_session, provider=TimeoutProvider())  # type: ignore

    assert len(results) == 1
    assert results[0].execution_status == "TIMED_OUT"

    db_session.refresh(action)
    assert action.status == RecoveryActionStatus.EXECUTING.value


def test_one_failed_action_does_not_stop_processing_of_other_actions(
    db_session: Session,
):
    """15. Test that failure on action A does not prevent action B from executing."""
    _, a1 = create_worker_test_action(db_session, hours_offset=-2.0)
    _, a2 = create_worker_test_action(db_session, hours_offset=-1.0)

    class SelectiveFailingProvider:
        def execute(self, act, context=None):
            if act.id == a1.id:
                raise RuntimeError("Exploding provider on action 1")
            return ProviderResult(
                success=True,
                execution_status="SUCCESS",
                provider_reference_id=f"rec_{act.id}",
                executed_at=datetime.now(UTC),
            )

    worker = RecoveryWorker()
    results = worker.poll_and_dispatch(
        db=db_session,
        provider=SelectiveFailingProvider(),  # type: ignore
    )

    # Action 1 resulted in FAILED, but Action 2 completed successfully
    assert len(results) == 2
    r1 = next(r for r in results if r.recovery_action_id == a1.id)
    r2 = next(r for r in results if r.recovery_action_id == a2.id)
    assert r1.execution_status == "FAILED"
    assert r2.execution_status == "SUCCESS"

    db_session.refresh(a1)
    db_session.refresh(a2)
    assert a1.status == RecoveryActionStatus.FAILED.value
    assert a2.status == RecoveryActionStatus.COMPLETED.value


# =========================================================================
# Reliability & Runner Tests
# =========================================================================


def test_runner_lifecycle_and_shutdown():
    """23. Test runner startup, status check, and graceful shutdown."""
    runner = WorkerRunner()
    assert not runner.is_running

    runner.start()
    assert runner.is_running
    health = runner.get_health()
    assert health["worker_status"] == "RUNNING"

    runner.stop()
    assert not runner.is_running
    health = runner.get_health()
    assert health["worker_status"] == "STOPPED"


def test_worker_telemetry_contains_no_secrets_or_pii():
    """25. Test that worker telemetry dictionary contains zero sensitive fields."""
    telemetry = worker_telemetry.to_dict()

    for key, value in telemetry.items():
        key_lower = str(key).lower()
        assert "secret" not in key_lower
        assert "key" not in key_lower or key_lower in {"queue_depth"}
        assert "password" not in key_lower
        assert "auth" not in key_lower
        assert "email" not in key_lower
        assert "phone" not in key_lower
