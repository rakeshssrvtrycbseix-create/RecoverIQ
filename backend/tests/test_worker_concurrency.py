import uuid
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from unittest.mock import MagicMock

import pytest
from sqlalchemy.orm import Session

from app.models import (
    AgentDecision,
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
from app.services.action_dispatcher import (
    ConcurrentExecutionError,
    action_dispatcher,
)
from app.workers.reconciliation_worker import ReconciliationWorker
from app.workers.recovery_worker import RecoveryWorker


def create_concurrency_test_action(
    db_session: Session,
    status: str = RecoveryActionStatus.SCHEDULED.value,
) -> RecoveryAction:
    """Helper to provision test database entities for concurrency tests."""
    customer = Customer(
        external_customer_id=f"cust_cc_{uuid.uuid4().hex[:8]}",
        email_masked="c***c@example.com",
        phone_masked="+91******2222",
        risk_tier=CustomerRiskTier.STANDARD.value,
        total_payments_count=5,
        failed_payments_count=1,
        recovered_payments_count=4,
    )
    db_session.add(customer)
    db_session.flush()

    payment = Payment(
        customer_id=customer.id,
        razorpay_order_id=f"order_cc_{uuid.uuid4().hex[:8]}",
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
        proposed_action_type=RecoveryActionType.RETRY_PAYMENT.value,
        confidence_score=Decimal("0.85"),
        reasoning_summary="Concurrency test.",
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

    sched_time = datetime.now(UTC) - timedelta(hours=1.0)
    action = RecoveryAction(
        recovery_case_id=case.id,
        policy_decision_id=pol_dec.id,
        action_idempotency_key=f"act_cc_{case.id}_{pol_dec.id}_{uuid.uuid4().hex[:6]}",
        action_type=RecoveryActionType.RETRY_PAYMENT.value,
        status=status,
        scheduled_for=sched_time,
        action_payload={"channel": "GATEWAY_API"},
    )
    db_session.add(action)
    db_session.commit()

    db_session.refresh(action)
    return action


def test_two_workers_cannot_claim_same_action(db_session: Session):
    """6. Test that when Worker 1 claims an action, Worker 2's claim fails."""
    action = create_concurrency_test_action(db_session)

    worker1 = RecoveryWorker()
    worker2 = RecoveryWorker()

    # Worker 1 claims action
    claimed_1 = worker1.claim_action(db=db_session, action_id=action.id)
    assert claimed_1 is True

    # Worker 2 attempts to claim the same action
    claimed_2 = worker2.claim_action(db=db_session, action_id=action.id)
    assert claimed_2 is False

    db_session.refresh(action)
    assert action.status == RecoveryActionStatus.EXECUTING.value


def test_only_one_provider_execution_occurs(db_session: Session):
    """7. Test that when two workers process the same action ID, provider is called once."""
    action = create_concurrency_test_action(db_session)

    mock_provider = MagicMock()
    mock_provider.execute.return_value = ProviderResult(
        success=True,
        execution_status="SUCCESS",
        provider_reference_id=f"rec_{action.id}",
        executed_at=datetime.now(UTC),
    )

    worker1 = RecoveryWorker()
    worker2 = RecoveryWorker()

    res1 = worker1.process_action(
        db=db_session, action_id=action.id, provider=mock_provider
    )
    res2 = worker2.process_action(
        db=db_session, action_id=action.id, provider=mock_provider
    )

    # Worker 1 succeeded, Worker 2 returned None (claim failed)
    assert res1 is not None
    assert res1.execution_status == "SUCCESS"
    assert res2 is None

    # Provider was called exactly ONCE
    assert mock_provider.execute.call_count == 1


def test_already_executing_action_is_not_claimed_or_dispatched(db_session: Session):
    """8. Test that an action already in EXECUTING state is ignored by the worker."""
    action = create_concurrency_test_action(
        db_session, status=RecoveryActionStatus.EXECUTING.value
    )

    worker = RecoveryWorker()
    claimed = worker.claim_action(db=db_session, action_id=action.id)
    assert claimed is False


def test_atomic_claim_failure_prevents_provider_execution(db_session: Session):
    """9. Test that if claim fails, process_action returns None without calling provider."""
    action = create_concurrency_test_action(
        db_session, status=RecoveryActionStatus.COMPLETED.value
    )

    mock_provider = MagicMock()
    worker = RecoveryWorker()

    result = worker.process_action(
        db=db_session, action_id=action.id, provider=mock_provider
    )

    assert result is None
    assert mock_provider.execute.call_count == 0


def test_concurrent_claim_collision_handled_safely(db_session: Session):
    """10. Test that multiple workers polling the same queue only dispatch each action once."""
    a1 = create_concurrency_test_action(db_session)
    a2 = create_concurrency_test_action(db_session)

    worker1 = RecoveryWorker()
    worker2 = RecoveryWorker()

    # Both workers see the same due action IDs
    due_ids_1 = worker1.fetch_due_action_ids(db=db_session)
    due_ids_2 = worker2.fetch_due_action_ids(db=db_session)

    assert set(due_ids_1) == {a1.id, a2.id}
    assert set(due_ids_2) == {a1.id, a2.id}

    # Worker 1 processes a1
    r1 = worker1.process_action(db=db_session, action_id=a1.id)
    assert r1 is not None

    # Worker 2 attempts a1 (fails claim), then processes a2 (succeeds)
    r2_a1 = worker2.process_action(db=db_session, action_id=a1.id)
    r2_a2 = worker2.process_action(db=db_session, action_id=a2.id)

    assert r2_a1 is None
    assert r2_a2 is not None

    # Both actions are finalized
    db_session.refresh(a1)
    db_session.refresh(a2)
    assert a1.status == RecoveryActionStatus.COMPLETED.value
    assert a2.status == RecoveryActionStatus.COMPLETED.value


def test_direct_dispatcher_and_worker_concurrency(db_session: Session):
    """Audit: Direct ActionDispatcher and RecoveryWorker racing on same action."""
    action = create_concurrency_test_action(db_session)

    mock_provider = MagicMock()
    mock_provider.execute.return_value = ProviderResult(
        success=True,
        execution_status="SUCCESS",
        provider_reference_id=f"rec_{action.id}",
        executed_at=datetime.now(UTC),
    )

    worker = RecoveryWorker()

    # 1. Worker claims action first
    claimed = worker.claim_action(db=db_session, action_id=action.id)
    assert claimed is True

    # 2. Direct dispatch attempting to dispatch the same action fails with ConcurrentExecutionError
    with pytest.raises(ConcurrentExecutionError, match="currently EXECUTING"):
        action_dispatcher.dispatch_action(
            db=db_session,
            recovery_action_id=action.id,
            provider=mock_provider,
            already_claimed=False,
        )

    # 3. Worker continues and dispatches successfully
    result = action_dispatcher.dispatch_action(
        db=db_session,
        recovery_action_id=action.id,
        provider=mock_provider,
        already_claimed=True,
    )
    assert result is not None
    assert result.execution_status == "SUCCESS"
    assert mock_provider.execute.call_count == 1


def test_worker_restart_ignores_previously_executing_action(db_session: Session):
    """Audit: Worker restart ignores action left in EXECUTING by a crashed process."""
    action = create_concurrency_test_action(
        db_session, status=RecoveryActionStatus.EXECUTING.value
    )

    # New worker instance after restart
    new_worker = RecoveryWorker()
    due_ids = new_worker.fetch_due_action_ids(db=db_session)
    assert action.id not in due_ids

    # Claim fails
    assert new_worker.claim_action(db=db_session, action_id=action.id) is False


def test_provider_success_crash_before_finalization_reconciled(db_session: Session):
    """Audit: Crash before finalization is resolved cleanly by reconciliation."""
    action = create_concurrency_test_action(
        db_session, status=RecoveryActionStatus.EXECUTING.value
    )
    # Simulate action dispatched 20 minutes ago
    action.dispatched_at = datetime.now(UTC) - timedelta(minutes=20)
    db_session.commit()

    class MockReconProvider:
        def reconcile_action(self, act):
            return ProviderResult(
                success=True,
                execution_status="SUCCESS",
                provider_reference_id=f"recoveriq_{act.id}",
                provider_status_code="200",
                executed_at=datetime.now(UTC),
            )

    recon_worker = ReconciliationWorker()
    results = recon_worker.run_reconciliation(
        db=db_session,
        threshold_minutes=15,
        provider=MockReconProvider(),  # type: ignore
    )

    assert len(results) == 1
    assert results[0].execution_status == "SUCCESS"

    db_session.refresh(action)
    assert action.status == RecoveryActionStatus.COMPLETED.value
