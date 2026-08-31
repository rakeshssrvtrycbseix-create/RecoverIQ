import json
from unittest.mock import patch

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models import (
    AuditLog,
    Customer,
    Payment,
    PaymentEvent,
    PaymentEventProcessingStatus,
    PaymentEventSource,
    PaymentStatus,
    RecoveryCase,
    RecoveryCaseStatus,
)
from app.services.payment_event_processor import payment_event_processor
from tests.conftest import TEST_WEBHOOK_SECRET
from tests.test_webhooks import compute_signature


def sample_payment_failed_event_payload() -> dict:
    """Return a full Razorpay payment.failed webhook event payload."""
    return {
        "entity": "event",
        "account_id": "acc_test_001",
        "event": "payment.failed",
        "contains": ["payment"],
        "payload": {
            "payment": {
                "entity": {
                    "id": "pay_proc_fail_001",
                    "entity": "payment",
                    "amount": 299900,
                    "currency": "INR",
                    "status": "failed",
                    "order_id": "order_proc_001",
                    "method": "card",
                    "email": "proc_user@example.com",
                    "contact": "+919876543210",
                    "customer_id": "cust_proc_001",
                    "error_code": "BAD_REQUEST_ERROR",
                    "error_reason": "insufficient_funds",
                }
            }
        },
        "created_at": 1724851200,
    }


def sample_payment_captured_event_payload() -> dict:
    """Return a full Razorpay payment.captured webhook event payload."""
    return {
        "entity": "event",
        "account_id": "acc_test_001",
        "event": "payment.captured",
        "contains": ["payment"],
        "payload": {
            "payment": {
                "entity": {
                    "id": "pay_proc_cap_001",
                    "entity": "payment",
                    "amount": 299900,
                    "currency": "INR",
                    "status": "captured",
                    "order_id": "order_proc_001",
                    "method": "card",
                    "customer_id": "cust_proc_001",
                }
            }
        },
        "created_at": 1724851250,
    }


def test_process_payment_failed_event_creates_recovery_case(
    db_session: Session,
):
    """Test processing payment.failed event creates a RecoveryCase."""
    raw_payload = sample_payment_failed_event_payload()
    event = PaymentEvent(
        idempotency_key="evt_proc_fail_001",
        razorpay_event_id="evt_proc_fail_001",
        event_type="payment.failed",
        source=PaymentEventSource.RAZORPAY_WEBHOOK.value,
        payload=raw_payload,
        processing_status=PaymentEventProcessingStatus.RECEIVED.value,
    )
    db_session.add(event)
    db_session.commit()

    result = payment_event_processor.process_payment_event(db_session, event)
    assert result.processing_status == PaymentEventProcessingStatus.PROCESSED.value
    assert result.already_processed is False
    assert result.recovery_case_id is not None

    # Verify event updated in DB
    db_session.refresh(event)
    assert event.processing_status == PaymentEventProcessingStatus.PROCESSED.value
    assert event.processed_at is not None
    assert event.payment_id is not None
    assert event.processing_error is None

    # Verify RecoveryCase in DB
    case = db_session.query(RecoveryCase).filter_by(id=result.recovery_case_id).first()
    assert case is not None
    assert case.status == RecoveryCaseStatus.OPEN.value
    assert case.amount_at_risk == 299900


def test_process_payment_captured_event_resolves_recovery_case(
    db_session: Session,
):
    """Test processing payment.captured resolves an open RecoveryCase."""
    # 1. Process failure first
    fail_payload = sample_payment_failed_event_payload()
    fail_event = PaymentEvent(
        idempotency_key="evt_cap_proc_001",
        razorpay_event_id="evt_cap_proc_001",
        event_type="payment.failed",
        source=PaymentEventSource.RAZORPAY_WEBHOOK.value,
        payload=fail_payload,
        processing_status=PaymentEventProcessingStatus.RECEIVED.value,
    )
    db_session.add(fail_event)
    db_session.commit()
    fail_res = payment_event_processor.process_payment_event(db_session, fail_event)

    # 2. Process capture
    cap_payload = sample_payment_captured_event_payload()
    cap_event = PaymentEvent(
        idempotency_key="evt_cap_proc_002",
        razorpay_event_id="evt_cap_proc_002",
        event_type="payment.captured",
        source=PaymentEventSource.RAZORPAY_WEBHOOK.value,
        payload=cap_payload,
        processing_status=PaymentEventProcessingStatus.RECEIVED.value,
    )
    db_session.add(cap_event)
    db_session.commit()
    cap_res = payment_event_processor.process_payment_event(db_session, cap_event)
    assert cap_res.processing_status == PaymentEventProcessingStatus.PROCESSED.value

    # Verify case resolved
    case = (
        db_session.query(RecoveryCase).filter_by(id=fail_res.recovery_case_id).first()
    )
    assert case.status == RecoveryCaseStatus.RECOVERED.value
    assert case.recovered_amount == 299900


def test_reprocessing_already_processed_event_is_idempotent_no_op(
    db_session: Session,
):
    """Test that re-processing an already PROCESSED event is a safe no-op."""
    payload = sample_payment_failed_event_payload()
    event = PaymentEvent(
        idempotency_key="evt_idemp_run_001",
        razorpay_event_id="evt_idemp_run_001",
        event_type="payment.failed",
        source=PaymentEventSource.RAZORPAY_WEBHOOK.value,
        payload=payload,
        processing_status=PaymentEventProcessingStatus.RECEIVED.value,
    )
    db_session.add(event)
    db_session.commit()

    # First run
    res_1 = payment_event_processor.process_payment_event(db_session, event)
    assert res_1.already_processed is False

    # Second run (re-processing)
    res_2 = payment_event_processor.process_payment_event(db_session, event)
    assert res_2.already_processed is True
    assert res_2.processing_status == PaymentEventProcessingStatus.PROCESSED.value


def test_process_unknown_non_recovery_event_safely_ignored(
    db_session: Session,
):
    """Test that non-recovery event types (order.paid) are marked PROCESSED."""
    payload = {
        "entity": "event",
        "event": "order.paid",
        "payload": {"order": {"entity": {"id": "order_custom_99"}}},
    }
    event = PaymentEvent(
        idempotency_key="evt_order_paid_001",
        razorpay_event_id="evt_order_paid_001",
        event_type="order.paid",
        source=PaymentEventSource.RAZORPAY_WEBHOOK.value,
        payload=payload,
        processing_status=PaymentEventProcessingStatus.RECEIVED.value,
    )
    db_session.add(event)
    db_session.commit()

    res = payment_event_processor.process_payment_event(db_session, event)
    assert res.processing_status == PaymentEventProcessingStatus.PROCESSED.value
    assert res.recovery_case_id is None

    # Audit log written for non-recovery event
    audit = (
        db_session.query(AuditLog)
        .filter_by(event_type="NON_RECOVERY_EVENT_IGNORED")
        .first()
    )
    assert audit is not None


def test_processor_transactional_rollback_on_failure(db_session: Session):
    """Test that a processing exception sets status to FAILED and rolls back."""
    payload = sample_payment_failed_event_payload()
    event = PaymentEvent(
        idempotency_key="evt_err_roll_001",
        razorpay_event_id="evt_err_roll_001",
        event_type="payment.failed",
        source=PaymentEventSource.RAZORPAY_WEBHOOK.value,
        payload=payload,
        processing_status=PaymentEventProcessingStatus.RECEIVED.value,
    )
    db_session.add(event)
    db_session.commit()

    with patch(
        "app.services.recovery_case_service.recovery_case_service.handle_payment_failure",
        side_effect=RuntimeError("Simulated database constraint failure"),
    ):
        try:
            payment_event_processor.process_payment_event(db_session, event)
        except RuntimeError:
            pass

    # Verify event status marked FAILED in DB and error recorded
    stored_event = db_session.query(PaymentEvent).filter_by(id=event.id).first()
    assert stored_event is not None
    assert stored_event.processing_status == PaymentEventProcessingStatus.FAILED.value
    assert "Simulated database constraint failure" in (
        stored_event.processing_error or ""
    )


def test_no_partial_business_state_committed_on_failure(db_session: Session):
    """Test that partial payment or case records are not committed after failure."""
    payload = {
        "entity": "event",
        "event": "payment.failed",
        "payload": {
            "payment": {
                "entity": {
                    "id": "pay_partial_rollback_001",
                    "amount": 50000,
                    "currency": "INR",
                    "order_id": "order_rollback_test_99",
                }
            }
        },
    }
    event = PaymentEvent(
        idempotency_key="evt_partial_rb_001",
        razorpay_event_id="evt_partial_rb_001",
        event_type="payment.failed",
        source=PaymentEventSource.RAZORPAY_WEBHOOK.value,
        payload=payload,
        processing_status=PaymentEventProcessingStatus.RECEIVED.value,
    )
    db_session.add(event)
    db_session.commit()

    def partial_failure_mock(db, payment_event, payment_data):
        # Create partial entities in the session without committing
        cust = Customer(external_customer_id="cust_temp_rb_01")
        db.add(cust)
        db.flush()
        payment = Payment(
            customer_id=cust.id,
            razorpay_order_id="order_rollback_test_99",
            amount=50000,
            currency="INR",
            status=PaymentStatus.FAILED.value,
        )
        db.add(payment)
        db.flush()
        # Fail before completing transaction
        raise RuntimeError("Unexpected failure during case processing")

    with patch(
        "app.services.recovery_case_service.recovery_case_service.handle_payment_failure",
        side_effect=partial_failure_mock,
    ):
        try:
            payment_event_processor.process_payment_event(db_session, event)
        except RuntimeError:
            pass

    # Ensure no partial Payment exists in DB (it was rolled back)
    payment = (
        db_session.query(Payment)
        .filter_by(razorpay_order_id="order_rollback_test_99")
        .first()
    )
    assert payment is None

    # Ensure event is marked FAILED in DB
    stored_event = db_session.query(PaymentEvent).filter_by(id=event.id).first()
    assert stored_event.processing_status == PaymentEventProcessingStatus.FAILED.value
    assert "Unexpected failure during case processing" in (
        stored_event.processing_error or ""
    )


def test_failed_event_can_safely_be_retried(db_session: Session):
    """Test that a previously FAILED event can be reprocessed and succeeds."""
    payload = sample_payment_failed_event_payload()
    event = PaymentEvent(
        idempotency_key="evt_retry_success_001",
        razorpay_event_id="evt_retry_success_001",
        event_type="payment.failed",
        source=PaymentEventSource.RAZORPAY_WEBHOOK.value,
        payload=payload,
        processing_status=PaymentEventProcessingStatus.FAILED.value,
        processing_error="Previous network timeout",
    )
    db_session.add(event)
    db_session.commit()

    # Retry processing
    result = payment_event_processor.process_payment_event(db_session, event)
    assert result.processing_status == PaymentEventProcessingStatus.PROCESSED.value
    assert result.already_processed is False
    assert result.recovery_case_id is not None

    # Verify event state in DB
    db_session.refresh(event)
    assert event.processing_status == PaymentEventProcessingStatus.PROCESSED.value
    assert event.processing_error is None  # Error cleared on successful retry


def test_webhook_end_to_end_ingestion_triggers_recovery_case_creation(
    client: TestClient, db_session: Session
):
    """Test end-to-end webhook ingestion creates a RecoveryCase in database."""
    payload_dict = sample_payment_failed_event_payload()
    raw_body = json.dumps(payload_dict).encode("utf-8")
    signature = compute_signature(raw_body, TEST_WEBHOOK_SECRET)
    event_id = "evt_e2e_webhook_001"

    headers = {
        "X-Razorpay-Signature": signature,
        "X-Razorpay-Event-Id": event_id,
        "Content-Type": "application/json",
    }

    response = client.post("/webhooks/razorpay", content=raw_body, headers=headers)
    assert response.status_code == 200

    # Verify event was persisted and processed
    event = db_session.query(PaymentEvent).filter_by(idempotency_key=event_id).first()
    assert event is not None
    assert event.processing_status == PaymentEventProcessingStatus.PROCESSED.value

    # Verify RecoveryCase exists in DB
    payment = (
        db_session.query(Payment).filter_by(razorpay_order_id="order_proc_001").first()
    )
    assert payment is not None
    assert payment.status == PaymentStatus.FAILED.value

    case = db_session.query(RecoveryCase).filter_by(payment_id=payment.id).first()
    assert case is not None
    assert case.status == RecoveryCaseStatus.OPEN.value
    assert case.amount_at_risk == 299900
