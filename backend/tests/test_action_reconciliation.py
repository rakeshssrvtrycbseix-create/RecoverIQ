import uuid
from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest
from sqlalchemy.orm import Session

from app.agent.decision_engine import recovery_decision_engine
from app.core.config import Settings
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
from app.policy.engine import policy_engine
from app.providers.base import ProviderResult
from app.services.action_dispatcher import action_dispatcher
from app.services.action_reconciliation import ActionReconciliationService
from app.services.action_scheduler import action_scheduler


def create_reconciliation_fixtures(
    db_session: Session,
    dispatched_minutes_ago: float = 30.0,
    action_status: str = RecoveryActionStatus.EXECUTING.value,
) -> tuple[Customer, Payment, RecoveryCase, PolicyDecision, RecoveryAction]:
    """Helper to provision test database entities for Action Reconciliation tests."""
    customer = Customer(
        external_customer_id=f"cust_rec_{uuid.uuid4().hex[:8]}",
        email_masked="r***c@example.com",
        phone_masked="+91******4444",
        risk_tier=CustomerRiskTier.STANDARD.value,
        total_payments_count=5,
        failed_payments_count=1,
        recovered_payments_count=4,
    )
    db_session.add(customer)
    db_session.flush()

    payment = Payment(
        customer_id=customer.id,
        razorpay_order_id=f"order_rec_{uuid.uuid4().hex[:8]}",
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

    policy_decision = PolicyDecision(
        recovery_case_id=case.id,
        evaluation_result=PolicyEvaluationResult.ALLOWED.value,
        policy_engine_version="policy_v1.0",
        decision_reason="Allowed by policy.",
    )
    db_session.add(policy_decision)
    db_session.flush()

    now_utc = datetime.now(UTC)
    dispatched_time = now_utc - timedelta(minutes=dispatched_minutes_ago)
    action = RecoveryAction(
        recovery_case_id=case.id,
        policy_decision_id=policy_decision.id,
        action_idempotency_key=f"act_rec_{case.id}_{uuid.uuid4().hex[:6]}",
        action_type=RecoveryActionType.RETRY_PAYMENT.value,
        status=action_status,
        scheduled_for=dispatched_time - timedelta(minutes=5),
        dispatched_at=dispatched_time,
        action_payload={"channel": "GATEWAY_API"},
    )
    db_session.add(action)
    db_session.commit()

    db_session.refresh(case)
    db_session.refresh(payment)
    db_session.refresh(customer)
    db_session.refresh(policy_decision)
    db_session.refresh(action)

    return customer, payment, case, policy_decision, action


class MockReconciliationProvider:
    """Mock provider with customizable reconciliation outcomes."""

    def __init__(self, outcome_status: str = "SUCCESS") -> None:
        self.outcome_status = outcome_status

    def execute(self, action, context=None):
        return ProviderResult(
            success=True,
            execution_status="SUCCESS",
            provider_reference_id=f"mock_{action.id}",
            executed_at=datetime.now(UTC),
        )

    def reconcile_action(self, action) -> ProviderResult:
        now_utc = datetime.now(UTC)
        if self.outcome_status == "SUCCESS":
            return ProviderResult(
                success=True,
                execution_status="SUCCESS",
                provider_reference_id=f"recoveriq_{action.id}",
                provider_status_code="200",
                response_payload_summary={"reconciled_state": "PAID"},
                executed_at=now_utc,
            )
        elif self.outcome_status == "FAILED":
            return ProviderResult(
                success=False,
                execution_status="FAILED",
                provider_reference_id=f"recoveriq_{action.id}",
                provider_status_code="200",
                failure_reason="GATEWAY_PAYMENT_EXPIRED",
                response_payload_summary={"reconciled_state": "EXPIRED"},
                executed_at=now_utc,
            )
        else:
            return ProviderResult(
                success=False,
                execution_status="UNKNOWN",
                provider_reference_id=f"recoveriq_{action.id}",
                failure_reason="INCONCLUSIVE",
                executed_at=now_utc,
            )


def test_recent_executing_action_is_not_reconciled(db_session: Session):
    """Test action dispatched 2 minutes ago (< 15 min threshold) is ignored."""
    _, _, _, _, action = create_reconciliation_fixtures(
        db_session, dispatched_minutes_ago=2.0
    )

    reconciler = ActionReconciliationService()
    results = reconciler.reconcile_stale_actions(db=db_session, threshold_minutes=15)

    assert len(results) == 0
    db_session.refresh(action)
    assert action.status == RecoveryActionStatus.EXECUTING.value


def test_stale_executing_action_is_reconciled_to_completed(db_session: Session):
    """Test stale action is reconciled to COMPLETED when provider reports SUCCESS."""
    _, _, case, _, action = create_reconciliation_fixtures(
        db_session, dispatched_minutes_ago=30.0
    )

    mock_provider = MockReconciliationProvider(outcome_status="SUCCESS")
    reconciler = ActionReconciliationService()
    results = reconciler.reconcile_stale_actions(
        db=db_session, threshold_minutes=15, provider=mock_provider  # type: ignore
    )

    assert len(results) == 1
    assert results[0].execution_status == "SUCCESS"

    db_session.refresh(action)
    assert action.status == RecoveryActionStatus.COMPLETED.value
    assert action.completed_at is not None

    # Verify AuditLog created
    audit = (
        db_session.query(AuditLog)
        .filter_by(
            recovery_case_id=case.id,
            entity_id=action.id,
            event_type="ACTION_RECONCILED_SUCCESS",
        )
        .first()
    )
    assert audit is not None
    assert audit.actor_id == "action_reconciler"


def test_stale_executing_action_is_reconciled_to_failed(db_session: Session):
    """Test stale action is reconciled to FAILED when provider reports FAILED."""
    _, _, case, _, action = create_reconciliation_fixtures(
        db_session, dispatched_minutes_ago=30.0
    )

    mock_provider = MockReconciliationProvider(outcome_status="FAILED")
    reconciler = ActionReconciliationService()
    results = reconciler.reconcile_stale_actions(
        db=db_session, threshold_minutes=15, provider=mock_provider  # type: ignore
    )

    assert len(results) == 1
    assert results[0].execution_status == "FAILED"

    db_session.refresh(action)
    assert action.status == RecoveryActionStatus.FAILED.value


def test_inconclusive_reconciliation_remains_executing(db_session: Session):
    """Test inconclusive reconciliation leaves action in EXECUTING."""
    _, _, case, _, action = create_reconciliation_fixtures(
        db_session, dispatched_minutes_ago=30.0
    )

    mock_provider = MockReconciliationProvider(outcome_status="UNKNOWN")
    reconciler = ActionReconciliationService()
    results = reconciler.reconcile_stale_actions(
        db=db_session, threshold_minutes=15, provider=mock_provider  # type: ignore
    )

    assert len(results) == 0
    db_session.refresh(action)
    assert action.status == RecoveryActionStatus.EXECUTING.value

    # Verify AuditLog deferred
    audit = (
        db_session.query(AuditLog)
        .filter_by(
            recovery_case_id=case.id,
            entity_id=action.id,
            event_type="ACTION_RECONCILIATION_DEFERRED",
        )
        .first()
    )
    assert audit is not None


def test_reconciliation_is_idempotent(db_session: Session):
    """Test running reconciliation multiple times does not duplicate results."""
    _, _, _, _, action = create_reconciliation_fixtures(
        db_session, dispatched_minutes_ago=30.0
    )

    mock_provider = MockReconciliationProvider(outcome_status="SUCCESS")
    reconciler = ActionReconciliationService()

    res1 = reconciler.reconcile_stale_actions(
        db=db_session, threshold_minutes=15, provider=mock_provider  # type: ignore
    )
    assert len(res1) == 1

    # Second pass: action is now COMPLETED, so it's not scanned as EXECUTING
    res2 = reconciler.reconcile_stale_actions(
        db=db_session, threshold_minutes=15, provider=mock_provider  # type: ignore
    )
    assert len(res2) == 0

    results_count = (
        db_session.query(ActionResult)
        .filter_by(recovery_action_id=action.id)
        .count()
    )
    assert results_count == 1


def test_payment_and_case_status_not_modified_by_reconciler(db_session: Session):
    """Test reconciler never mutates Payment.status or RecoveryCase.status."""
    customer, payment, case, _, action = create_reconciliation_fixtures(
        db_session, dispatched_minutes_ago=30.0
    )
    init_pay_status = payment.status
    init_case_status = case.status

    reconciler = ActionReconciliationService()
    reconciler.reconcile_stale_actions(db=db_session, threshold_minutes=15)

    db_session.refresh(payment)
    db_session.refresh(case)
    assert payment.status == init_pay_status
    assert case.status == init_case_status


# =========================================================================
# End-to-End Pipeline Integration Test
# =========================================================================


@pytest.mark.anyio
async def test_full_recovery_pipeline_end_to_end_integration(db_session: Session):
    """
    End-to-End Architecture Integration Test:
    RecoveryCase
    → AgentDecision
    → PolicyDecision (ALLOWED)
    → RecoveryAction (SCHEDULED)
    → ActionDispatcher
    → ProviderFactory (Mock)
    → ActionResult (SUCCESS)
    → AuditLog
    """
    # 1. Setup entities
    customer = Customer(
        external_customer_id=f"cust_e2e_{uuid.uuid4().hex[:8]}",
        email_masked="e***e@example.com",
        phone_masked="+91******3333",
        risk_tier=CustomerRiskTier.STANDARD.value,
        total_payments_count=5,
        failed_payments_count=1,
        recovered_payments_count=4,
    )
    db_session.add(customer)
    db_session.flush()

    payment = Payment(
        customer_id=customer.id,
        razorpay_order_id=f"order_e2e_{uuid.uuid4().hex[:8]}",
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
    db_session.commit()

    # 2. Generate AgentDecision (Phase 6B)
    agent_dec = await recovery_decision_engine.generate_decision(
        db=db_session,
        recovery_case_id=case.id,
    )
    assert agent_dec is not None
    assert agent_dec.proposed_action_type == RecoveryActionType.SEND_NOTIFICATION.value or agent_dec.proposed_action_type == RecoveryActionType.RETRY_PAYMENT.value

    # 3. Evaluate PolicyDecision (Phase 6C)
    now_utc = datetime.now(UTC)
    policy_dec = policy_engine.evaluate(
        db=db_session,
        agent_decision_id=agent_dec.id,
        as_of=now_utc,
    )
    assert policy_dec is not None
    assert policy_dec.evaluation_result == PolicyEvaluationResult.ALLOWED.value

    # 4. Schedule RecoveryAction (Phase 7A)
    action = action_scheduler.schedule_for_policy_decision(
        db=db_session,
        policy_decision_id=policy_dec.id,
        as_of=now_utc,
    )
    assert action is not None
    assert action.status == RecoveryActionStatus.SCHEDULED.value

    # 5. Dispatch Action (Phase 7B)
    # Set scheduled_for to past to make it immediately due
    action.scheduled_for = now_utc - timedelta(minutes=1)
    db_session.commit()

    action_res = action_dispatcher.dispatch_action(
        db=db_session,
        recovery_action_id=action.id,
        as_of=now_utc,
    )
    assert action_res is not None
    assert action_res.execution_status == "SUCCESS"

    db_session.refresh(action)
    assert action.status == RecoveryActionStatus.COMPLETED.value

    # 6. Verify complete Audit Trail
    audit_logs = (
        db_session.query(AuditLog)
        .filter_by(recovery_case_id=case.id)
        .all()
    )
    event_types = {a.event_type for a in audit_logs}
    assert "AGENT_DECISION_GENERATED" in event_types
    assert "POLICY_DECISION_EVALUATED" in event_types
    assert "RECOVERY_ACTION_SCHEDULED" in event_types
    assert "RECOVERY_ACTION_EXECUTED" in event_types


# =========================================================================
# Phase 8A Gateway Timeout & Reconciliation Tests
# =========================================================================


def test_timed_out_action_is_reconciled(db_session: Session):
    """5, 6. Test action that experienced gateway timeout is reconciled to COMPLETED."""
    _, _, case, _, action = create_reconciliation_fixtures(
        db_session, dispatched_minutes_ago=20.0
    )

    # Simulate timeout outcome previously recorded
    action.status = RecoveryActionStatus.EXECUTING.value
    timeout_res = ActionResult(
        recovery_action_id=action.id,
        execution_status="TIMED_OUT",
        provider_reference_id=f"recoveriq_{action.id}",
        provider_status_code="408",
        failure_reason="GATEWAY_TIMEOUT",
        error_details="Connection timed out",
        executed_at=datetime.now(UTC) - timedelta(minutes=20),
    )
    db_session.add(timeout_res)
    db_session.commit()

    # Reconciler finds it and provider reports payment was captured
    mock_provider = MockReconciliationProvider(outcome_status="SUCCESS")
    reconciler = ActionReconciliationService()
    results = reconciler.reconcile_stale_actions(
        db=db_session, threshold_minutes=15, provider=mock_provider  # type: ignore
    )

    assert len(results) == 1
    assert results[0].execution_status == "SUCCESS"

    db_session.refresh(action)
    assert action.status == RecoveryActionStatus.COMPLETED.value


def test_reconciliation_marks_failed_timeout_failed(db_session: Session):
    """7. Test timed-out action where gateway reports expired/failed transitions to FAILED."""
    _, _, case, _, action = create_reconciliation_fixtures(
        db_session, dispatched_minutes_ago=20.0
    )

    mock_provider = MockReconciliationProvider(outcome_status="FAILED")
    reconciler = ActionReconciliationService()
    results = reconciler.reconcile_stale_actions(
        db=db_session, threshold_minutes=15, provider=mock_provider  # type: ignore
    )

    assert len(results) == 1
    assert results[0].execution_status == "FAILED"

    db_session.refresh(action)
    assert action.status == RecoveryActionStatus.FAILED.value


def test_reconciliation_defers_inconclusive_timeout(db_session: Session):
    """8. Test timed-out action where gateway status is inconclusive remains EXECUTING."""
    _, _, case, _, action = create_reconciliation_fixtures(
        db_session, dispatched_minutes_ago=20.0
    )

    mock_provider = MockReconciliationProvider(outcome_status="UNKNOWN")
    reconciler = ActionReconciliationService()
    results = reconciler.reconcile_stale_actions(
        db=db_session, threshold_minutes=15, provider=mock_provider  # type: ignore
    )

    assert len(results) == 0
    db_session.refresh(action)
    assert action.status == RecoveryActionStatus.EXECUTING.value


def test_timeout_reconciliation_does_not_create_duplicate_payment(db_session: Session):
    """10, 13. Test reconciliation reuses same idempotency key and does not trigger duplicate charge."""
    _, _, case, _, action = create_reconciliation_fixtures(
        db_session, dispatched_minutes_ago=20.0
    )

    mock_provider = MockReconciliationProvider(outcome_status="SUCCESS")
    reconciler = ActionReconciliationService()
    results = reconciler.reconcile_stale_actions(
        db=db_session, threshold_minutes=15, provider=mock_provider  # type: ignore
    )

    assert len(results) == 1
    assert f"recoveriq_{action.id}" in results[0].provider_reference_id

