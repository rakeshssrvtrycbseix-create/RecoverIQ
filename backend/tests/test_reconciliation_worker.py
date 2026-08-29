import uuid
from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest
from sqlalchemy.orm import Session

from app.models import (
    AgentDecision,
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
from app.workers.reconciliation_worker import ReconciliationWorker


def create_recon_worker_action(
    db_session: Session,
    dispatched_minutes_ago: float = 30.0,
    status: str = RecoveryActionStatus.EXECUTING.value,
) -> RecoveryAction:
    """Helper to provision test database entities for reconciliation worker tests."""
    customer = Customer(
        external_customer_id=f"cust_rw_{uuid.uuid4().hex[:8]}",
        email_masked="rw***@example.com",
        phone_masked="+91******8888",
        risk_tier=CustomerRiskTier.STANDARD.value,
        total_payments_count=5,
        failed_payments_count=1,
        recovered_payments_count=4,
    )
    db_session.add(customer)
    db_session.flush()

    payment = Payment(
        customer_id=customer.id,
        razorpay_order_id=f"order_rw_{uuid.uuid4().hex[:8]}",
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

    pol_dec = PolicyDecision(
        recovery_case_id=case.id,
        evaluation_result=PolicyEvaluationResult.ALLOWED.value,
        policy_engine_version="policy_v1.0",
        decision_reason="Policy allowed.",
    )
    db_session.add(pol_dec)
    db_session.flush()

    now_utc = datetime.now(UTC)
    dispatched_time = now_utc - timedelta(minutes=dispatched_minutes_ago)
    action = RecoveryAction(
        recovery_case_id=case.id,
        policy_decision_id=pol_dec.id,
        action_idempotency_key=f"act_rw_{case.id}_{uuid.uuid4().hex[:6]}",
        action_type=RecoveryActionType.RETRY_PAYMENT.value,
        status=status,
        scheduled_for=dispatched_time - timedelta(minutes=5),
        dispatched_at=dispatched_time,
        action_payload={"channel": "GATEWAY_API"},
    )
    db_session.add(action)
    db_session.commit()

    db_session.refresh(action)
    return action


class MockProviderForReconWorker:
    def __init__(self, outcome: str = "SUCCESS"):
        self.outcome = outcome

    def reconcile_action(self, action):
        now_utc = datetime.now(UTC)
        if self.outcome == "SUCCESS":
            return ProviderResult(
                success=True,
                execution_status="SUCCESS",
                provider_reference_id=f"rec_{action.id}",
                provider_status_code="200",
                executed_at=now_utc,
            )
        elif self.outcome == "FAILED":
            return ProviderResult(
                success=False,
                execution_status="FAILED",
                provider_reference_id=f"rec_{action.id}",
                provider_status_code="200",
                failure_reason="EXPIRED",
                executed_at=now_utc,
            )
        else:
            return ProviderResult(
                success=False,
                execution_status="UNKNOWN",
                provider_reference_id=f"rec_{action.id}",
                failure_reason="INCONCLUSIVE",
                executed_at=now_utc,
            )


def test_stale_executing_action_is_reconciled(db_session: Session):
    """16, 18. Test stale EXECUTING action is reconciled to COMPLETED."""
    action = create_recon_worker_action(db_session, dispatched_minutes_ago=25.0)

    worker = ReconciliationWorker()
    provider = MockProviderForReconWorker(outcome="SUCCESS")
    results = worker.run_reconciliation(
        db=db_session, threshold_minutes=15, provider=provider  # type: ignore
    )

    assert len(results) == 1
    assert results[0].execution_status == "SUCCESS"

    db_session.refresh(action)
    assert action.status == RecoveryActionStatus.COMPLETED.value


def test_fresh_executing_action_is_not_reconciled(db_session: Session):
    """17. Test fresh action (< 15 mins old) is not reconciled."""
    action = create_recon_worker_action(db_session, dispatched_minutes_ago=5.0)

    worker = ReconciliationWorker()
    provider = MockProviderForReconWorker(outcome="SUCCESS")
    results = worker.run_reconciliation(
        db=db_session, threshold_minutes=15, provider=provider  # type: ignore
    )

    assert len(results) == 0
    db_session.refresh(action)
    assert action.status == RecoveryActionStatus.EXECUTING.value


def test_reconciliation_marks_failed_reconciliation(db_session: Session):
    """19. Test failed reconciliation updates status to FAILED."""
    action = create_recon_worker_action(db_session, dispatched_minutes_ago=25.0)

    worker = ReconciliationWorker()
    provider = MockProviderForReconWorker(outcome="FAILED")
    results = worker.run_reconciliation(
        db=db_session, threshold_minutes=15, provider=provider  # type: ignore
    )

    assert len(results) == 1
    assert results[0].execution_status == "FAILED"

    db_session.refresh(action)
    assert action.status == RecoveryActionStatus.FAILED.value


def test_inconclusive_reconciliation_keeps_executing(db_session: Session):
    """20. Test inconclusive reconciliation keeps action in EXECUTING."""
    action = create_recon_worker_action(db_session, dispatched_minutes_ago=25.0)

    worker = ReconciliationWorker()
    provider = MockProviderForReconWorker(outcome="UNKNOWN")
    results = worker.run_reconciliation(
        db=db_session, threshold_minutes=15, provider=provider  # type: ignore
    )

    assert len(results) == 0
    db_session.refresh(action)
    assert action.status == RecoveryActionStatus.EXECUTING.value


def test_reconciliation_does_not_overlap_with_itself(db_session: Session):
    """24. Test that a concurrent reconciliation call returns immediately if one is in-flight."""
    worker = ReconciliationWorker()

    # Manually set running state
    worker._is_running = True

    results = worker.run_reconciliation(db=db_session)
    assert results == []

    # Reset
    worker._is_running = False
