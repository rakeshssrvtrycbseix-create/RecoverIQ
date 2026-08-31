from typing import Any

from sqlalchemy.orm import Session

from app.models import (
    AuditLog,
    Customer,
    Payment,
    PaymentAttemptStatus,
    PaymentEvent,
    PaymentEventProcessingStatus,
    PaymentEventSource,
    PaymentStatus,
    RecoveryCase,
    RecoveryCaseClosedReason,
    RecoveryCaseStatus,
    RecoveryStage,
    Subscription,
    SubscriptionStatus,
)
from app.services.recovery_case_service import recovery_case_service


def create_dummy_payment_event(
    event_id: str,
    event_type: str,
    payload: dict[str, Any],
) -> PaymentEvent:
    """Create a dummy PaymentEvent for testing."""
    return PaymentEvent(
        idempotency_key=event_id,
        razorpay_event_id=event_id,
        event_type=event_type,
        source=PaymentEventSource.RAZORPAY_WEBHOOK.value,
        payload=payload,
        processing_status=PaymentEventProcessingStatus.RECEIVED.value,
    )


def test_get_or_create_customer_with_notes_and_razorpay_id(
    db_session: Session,
):
    """Test customer resolution by merchant notes, Razorpay ID, or creation."""
    payload_1 = {
        "customer_id": "cust_rzp_123",
        "email": "jane.doe@example.com",
        "contact": "+919876543210",
        "notes": {"merchant_customer_id": "usr_merchant_99"},
    }
    cust_1 = recovery_case_service.get_or_create_customer(db_session, payload_1)
    assert cust_1.external_customer_id == "usr_merchant_99"
    assert cust_1.razorpay_customer_id == "cust_rzp_123"
    assert cust_1.email_masked == "j***e@example.com"
    assert cust_1.phone_masked == "+91******3210"

    # Resolving again with same merchant_customer_id returns existing customer
    cust_2 = recovery_case_service.get_or_create_customer(db_session, payload_1)
    assert cust_2.id == cust_1.id


def test_get_or_create_payment_with_order_id(db_session: Session):
    """Test payment resolution by order_id or invoice_id."""
    customer = Customer(
        external_customer_id="cust_pay_test_01",
        email_masked="c***1@example.com",
    )
    db_session.add(customer)
    db_session.flush()

    payload_pay = {
        "id": "pay_test_001",
        "order_id": "order_test_99",
        "amount": 499900,
        "currency": "INR",
    }

    payment_1 = recovery_case_service.get_or_create_payment(
        db_session, customer, payload_pay
    )
    assert payment_1.razorpay_order_id == "order_test_99"
    assert payment_1.amount == 499900
    assert payment_1.currency == "INR"
    assert payment_1.status == PaymentStatus.CREATED.value

    # Resolving again returns existing payment
    payment_2 = recovery_case_service.get_or_create_payment(
        db_session, customer, payload_pay
    )
    assert payment_2.id == payment_1.id


def test_record_payment_attempt_increments_attempt_number(db_session: Session):
    """Test recording sequential payment attempts."""
    customer = Customer(external_customer_id="cust_att_test_01")
    db_session.add(customer)
    db_session.flush()

    payment = Payment(
        customer_id=customer.id,
        amount=10000,
        currency="INR",
        status=PaymentStatus.CREATED.value,
    )
    db_session.add(payment)
    db_session.flush()

    attempt_payload_1 = {
        "id": "pay_att_001",
        "amount": 10000,
        "method": "card",
        "error_code": "BAD_REQUEST_ERROR",
        "error_reason": "insufficient_funds",
    }
    att_1 = recovery_case_service.record_payment_attempt(
        db_session, payment, attempt_payload_1, PaymentAttemptStatus.FAILED
    )
    assert att_1.attempt_number == 1
    assert att_1.error_reason == "insufficient_funds"

    attempt_payload_2 = {
        "id": "pay_att_002",
        "amount": 10000,
        "method": "card",
        "error_code": "GATEWAY_ERROR",
        "error_reason": "issuer_down",
    }
    att_2 = recovery_case_service.record_payment_attempt(
        db_session, payment, attempt_payload_2, PaymentAttemptStatus.FAILED
    )
    assert att_2.attempt_number == 2
    assert att_2.error_reason == "issuer_down"


def test_handle_payment_failure_creates_new_recovery_case(db_session: Session):
    """Test that payment.failed creates a RecoveryCase and AuditLog."""
    payload_payment = {
        "id": "pay_fail_001",
        "order_id": "order_fail_001",
        "amount": 150000,
        "currency": "INR",
        "error_code": "BAD_REQUEST_ERROR",
        "error_reason": "insufficient_funds",
        "notes": {"merchant_customer_id": "cust_fail_001"},
    }
    event = create_dummy_payment_event(
        "evt_fail_001", "payment.failed", {"payment": payload_payment}
    )

    case = recovery_case_service.handle_payment_failure(
        db_session, event, payload_payment
    )
    assert case is not None
    assert case.status == RecoveryCaseStatus.OPEN.value
    assert case.recovery_stage == RecoveryStage.INITIAL_FAILURE.value
    assert case.amount_at_risk == 150000
    assert case.recovered_amount == 0
    assert case.total_attempts_count == 1
    assert case.latest_failure_reason == "insufficient_funds"
    assert case.next_action_due_at is not None

    # Check payment state
    payment = db_session.query(Payment).filter_by(id=case.payment_id).first()
    assert payment.status == PaymentStatus.FAILED.value

    # Check audit log
    audit = db_session.query(AuditLog).filter_by(recovery_case_id=case.id).first()
    assert audit is not None
    assert audit.event_type == "RECOVERY_CASE_OPENED"
    assert audit.action == "RECOVERY_CASE_OPENED"


def test_multiple_payment_failures_update_existing_active_case(
    db_session: Session,
):
    """Test multiple failures for same payment update existing active case."""
    payload_payment_1 = {
        "id": "pay_multi_001",
        "order_id": "order_multi_001",
        "amount": 250000,
        "currency": "INR",
        "error_reason": "insufficient_funds",
        "notes": {"merchant_customer_id": "cust_multi_001"},
    }
    event_1 = create_dummy_payment_event(
        "evt_m_001", "payment.failed", {"payment": payload_payment_1}
    )
    case_1 = recovery_case_service.handle_payment_failure(
        db_session, event_1, payload_payment_1
    )
    assert case_1.total_attempts_count == 1

    payload_payment_2 = {
        "id": "pay_multi_002",
        "order_id": "order_multi_001",
        "amount": 250000,
        "currency": "INR",
        "error_reason": "card_inactive",
        "notes": {"merchant_customer_id": "cust_multi_001"},
    }
    event_2 = create_dummy_payment_event(
        "evt_m_002", "payment.failed", {"payment": payload_payment_2}
    )
    case_2 = recovery_case_service.handle_payment_failure(
        db_session, event_2, payload_payment_2
    )

    # Must be the exact same case updated
    assert case_2.id == case_1.id
    assert case_2.total_attempts_count == 2
    assert case_2.latest_failure_reason == "card_inactive"

    # Verify no duplicate active cases exist for this payment
    cases_count = (
        db_session.query(RecoveryCase).filter_by(payment_id=case_1.payment_id).count()
    )
    assert cases_count == 1


def test_handle_payment_captured_resolves_active_recovery_case(
    db_session: Session,
):
    """Test payment.captured resolves active RecoveryCase & sets recovered_amount."""
    # 1. First trigger failure to create open case
    payload_fail = {
        "id": "pay_cap_test_001",
        "order_id": "order_cap_test_001",
        "amount": 350000,
        "currency": "INR",
        "error_reason": "insufficient_funds",
        "notes": {"merchant_customer_id": "cust_cap_test_001"},
    }
    event_fail = create_dummy_payment_event(
        "evt_fail_cap_001", "payment.failed", {"payment": payload_fail}
    )
    case = recovery_case_service.handle_payment_failure(
        db_session, event_fail, payload_fail
    )
    assert case.status == RecoveryCaseStatus.OPEN.value
    assert case.recovered_amount == 0

    # 2. Trigger capture
    payload_cap = {
        "id": "pay_cap_test_002",
        "order_id": "order_cap_test_001",
        "amount": 350000,
        "currency": "INR",
        "notes": {"merchant_customer_id": "cust_cap_test_001"},
    }
    event_cap = create_dummy_payment_event(
        "evt_cap_001", "payment.captured", {"payment": payload_cap}
    )
    resolved_case = recovery_case_service.handle_payment_captured(
        db_session, event_cap, payload_cap
    )
    assert resolved_case is not None
    assert resolved_case.id == case.id
    assert resolved_case.status == RecoveryCaseStatus.RECOVERED.value
    assert resolved_case.recovered_amount == 350000
    assert (
        resolved_case.closed_reason == RecoveryCaseClosedReason.PAYMENT_RECOVERED.value
    )
    assert resolved_case.resolved_at is not None

    # Check payment status
    payment = db_session.query(Payment).filter_by(id=resolved_case.payment_id).first()
    assert payment.status == PaymentStatus.CAPTURED.value


def test_payment_captured_recovered_amount_cannot_exceed_risk(
    db_session: Session,
):
    """Test that recovered_amount is bounded by amount_at_risk."""
    payload_fail = {
        "id": "pay_bound_001",
        "order_id": "order_bound_001",
        "amount": 100000,
        "currency": "INR",
        "error_reason": "insufficient_funds",
    }
    event_fail = create_dummy_payment_event(
        "evt_bound_001", "payment.failed", {"payment": payload_fail}
    )
    case = recovery_case_service.handle_payment_failure(
        db_session, event_fail, payload_fail
    )
    assert case.amount_at_risk == 100000

    # Attempt capture with higher amount
    payload_cap = {
        "id": "pay_bound_002",
        "order_id": "order_bound_001",
        "amount": 150000,  # Higher than amount_at_risk
        "currency": "INR",
    }
    event_cap = create_dummy_payment_event(
        "evt_bound_002", "payment.captured", {"payment": payload_cap}
    )
    resolved_case = recovery_case_service.handle_payment_captured(
        db_session, event_cap, payload_cap
    )
    # Recovered amount must be capped at amount_at_risk
    assert resolved_case.recovered_amount == 100000
    assert resolved_case.recovered_amount <= resolved_case.amount_at_risk


def test_late_payment_failed_does_not_reopen_captured_payment_case(
    db_session: Session,
):
    """Test ordering protection: late failure after capture does not reopen case."""
    # 1. Initial capture
    payload_cap = {
        "id": "pay_order_prot_001",
        "order_id": "order_prot_001",
        "amount": 50000,
        "currency": "INR",
    }
    event_cap = create_dummy_payment_event(
        "evt_cap_first", "payment.captured", {"payment": payload_cap}
    )
    recovery_case_service.handle_payment_captured(db_session, event_cap, payload_cap)

    # Verify payment is CAPTURED
    payment = (
        db_session.query(Payment).filter_by(razorpay_order_id="order_prot_001").first()
    )
    assert payment.status == PaymentStatus.CAPTURED.value

    # 2. Late failure arrives
    payload_late_fail = {
        "id": "pay_order_prot_002",
        "order_id": "order_prot_001",
        "amount": 50000,
        "currency": "INR",
        "error_reason": "stale_network_timeout",
    }
    event_late_fail = create_dummy_payment_event(
        "evt_late_fail", "payment.failed", {"payment": payload_late_fail}
    )
    result = recovery_case_service.handle_payment_failure(
        db_session, event_late_fail, payload_late_fail
    )
    assert result is None  # Ignored

    # Payment must remain CAPTURED
    db_session.refresh(payment)
    assert payment.status == PaymentStatus.CAPTURED.value

    # Stale event audit log written
    stale_audit = (
        db_session.query(AuditLog)
        .filter_by(event_type="STALE_PAYMENT_FAILURE_IGNORED")
        .first()
    )
    assert stale_audit is not None
    assert stale_audit.action == "STALE_EVENT_IGNORED"


def test_handle_subscription_halted_escalates_recovery_stage(
    db_session: Session,
):
    """Test subscription.halted updates status & escalates recovery stage."""
    payload_sub = {
        "id": "sub_halt_test_001",
        "plan_id": "plan_enterprise",
        "amount": 499900,
    }
    payload_pay = {
        "id": "pay_sub_halt_001",
        "amount": 499900,
        "currency": "INR",
        "error_reason": "card_inactive",
        "customer_id": "cust_sub_halt_001",
    }
    event = create_dummy_payment_event(
        "evt_sub_halt_001",
        "subscription.halted",
        {"subscription": payload_sub, "payment": payload_pay},
    )

    case = recovery_case_service.handle_subscription_halted(
        db_session, event, payload_sub, payload_pay
    )
    assert case is not None
    assert case.recovery_stage == RecoveryStage.ESCALATION.value

    sub = (
        db_session.query(Subscription)
        .filter_by(razorpay_subscription_id="sub_halt_test_001")
        .first()
    )
    assert sub is not None
    assert sub.status == SubscriptionStatus.HALTED.value
