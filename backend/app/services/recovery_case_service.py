import logging
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy.orm import Session

from app.models import (
    AuditActorType,
    AuditLog,
    Customer,
    CustomerRiskTier,
    Payment,
    PaymentAttempt,
    PaymentAttemptStatus,
    PaymentEvent,
    PaymentStatus,
    RecoveryCase,
    RecoveryCaseClosedReason,
    RecoveryCaseStatus,
    RecoveryStage,
    Subscription,
    SubscriptionStatus,
)
from app.webhooks.sanitizer import mask_email, mask_phone

logger = logging.getLogger(__name__)

# Active recovery statuses where a case is open and active
ACTIVE_RECOVERY_STATUSES = {
    RecoveryCaseStatus.OPEN.value,
    RecoveryCaseStatus.ANALYZING.value,
    RecoveryCaseStatus.ACTION_PENDING.value,
    RecoveryCaseStatus.IN_RECOVERY.value,
    RecoveryCaseStatus.ESCALATED_HUMAN.value,
}


class RecoveryCaseService:
    """Deterministic business service for payment recovery case lifecycle management."""

    def get_or_create_customer(
        self,
        db: Session,
        payload_payment: dict[str, Any],
    ) -> Customer:
        """
        Deterministically resolve or create a customer profile from metadata.

        Resolution Hierarchy:
        1. notes.merchant_customer_id -> Customer.external_customer_id
        2. customer_id -> Customer.razorpay_customer_id
        3. Provisional Customer creation if neither exists
        """
        notes = payload_payment.get("notes") or {}
        merchant_cust_id = (
            notes.get("merchant_customer_id")
            or notes.get("customer_id")
            or notes.get("user_id")
        )
        rzp_cust_id = payload_payment.get("customer_id")

        customer = None
        if merchant_cust_id:
            customer = (
                db.query(Customer)
                .filter_by(external_customer_id=str(merchant_cust_id))
                .first()
            )

        if not customer and rzp_cust_id:
            customer = (
                db.query(Customer)
                .filter_by(razorpay_customer_id=str(rzp_cust_id))
                .first()
            )

        if not customer:
            if merchant_cust_id:
                ext_id = str(merchant_cust_id)
            elif rzp_cust_id:
                ext_id = str(rzp_cust_id)
            else:
                ext_id = f"cust_prov_{uuid.uuid4().hex[:12]}"

            customer = Customer(
                external_customer_id=ext_id,
                razorpay_customer_id=str(rzp_cust_id) if rzp_cust_id else None,
                email_masked=mask_email(payload_payment.get("email")),
                phone_masked=mask_phone(payload_payment.get("contact")),
                risk_tier=CustomerRiskTier.STANDARD.value,
                total_payments_count=0,
                failed_payments_count=0,
                recovered_payments_count=0,
                metadata_json={},
            )
            db.add(customer)
            db.flush()

        return customer

    def get_or_create_payment(
        self,
        db: Session,
        customer: Customer,
        payload_payment: dict[str, Any],
    ) -> Payment:
        """
        Deterministically resolve or create a canonical Payment entity.

        Resolution Hierarchy:
        1. razorpay_order_id -> Payment.razorpay_order_id
        2. razorpay_invoice_id -> Payment.razorpay_invoice_id
        3. Create Payment entity if not previously registered
        """
        order_id = payload_payment.get("order_id")
        invoice_id = payload_payment.get("invoice_id")
        amount = max(0, int(payload_payment.get("amount", 0)))
        currency = payload_payment.get("currency", "INR")

        payment = None
        if order_id:
            payment = (
                db.query(Payment)
                .filter_by(razorpay_order_id=str(order_id))
                .first()
            )

        if not payment and invoice_id:
            payment = (
                db.query(Payment)
                .filter_by(razorpay_invoice_id=str(invoice_id))
                .first()
            )

        if not payment:
            payment = Payment(
                customer_id=customer.id,
                subscription_id=None,
                razorpay_order_id=str(order_id) if order_id else None,
                razorpay_invoice_id=str(invoice_id) if invoice_id else None,
                amount=amount,
                currency=currency,
                status=PaymentStatus.CREATED.value,
                metadata_json={},
            )
            db.add(payment)
            db.flush()
            customer.total_payments_count += 1

        return payment

    def record_payment_attempt(
        self,
        db: Session,
        payment: Payment,
        payload_payment: dict[str, Any],
        status: PaymentAttemptStatus,
    ) -> PaymentAttempt:
        """Record an individual physical payment attempt and gateway telemetry."""
        rzp_payment_id = payload_payment.get("id")

        # Check if attempt was already recorded
        if rzp_payment_id:
            existing = (
                db.query(PaymentAttempt)
                .filter_by(razorpay_payment_id=str(rzp_payment_id))
                .first()
            )
            if existing:
                return existing

        count = (
            db.query(PaymentAttempt)
            .filter_by(payment_id=payment.id)
            .count()
        )
        attempt_number = count + 1

        card_info = payload_payment.get("card")
        sub_type = None
        if isinstance(card_info, dict):
            sub_type = card_info.get("type")

        attempt = PaymentAttempt(
            payment_id=payment.id,
            attempt_number=attempt_number,
            razorpay_payment_id=str(rzp_payment_id) if rzp_payment_id else None,
            payment_method=payload_payment.get("method"),
            payment_method_sub_type=sub_type,
            amount=max(0, int(payload_payment.get("amount", payment.amount))),
            status=status.value,
            error_code=payload_payment.get("error_code"),
            error_source=payload_payment.get("error_source"),
            error_step=payload_payment.get("error_step"),
            error_reason=payload_payment.get("error_reason"),
            error_description=payload_payment.get("error_description"),
        )
        db.add(attempt)
        db.flush()
        return attempt

    def handle_payment_failure(
        self,
        db: Session,
        payment_event: PaymentEvent,
        payload_payment: dict[str, Any],
    ) -> RecoveryCase | None:
        """
        Process a payment.failed event deterministically.

        1. Locate or create Customer and Payment entities.
        2. Record the failed PaymentAttempt.
        3. Check for state ordering: If payment is already CAPTURED, ignore failure.
        4. Locate active RecoveryCase; update if exists, or create a new one.
        5. Write structured AuditLog.
        """
        logger.info(
            "payment_failure_detected",
            extra={
                "event_id": payment_event.idempotency_key,
                "payment_id": payload_payment.get("id"),
            },
        )

        customer = self.get_or_create_customer(db, payload_payment)
        payment = self.get_or_create_payment(db, customer, payload_payment)
        self.record_payment_attempt(
            db, payment, payload_payment, PaymentAttemptStatus.FAILED
        )

        # Event Ordering Protection: Do NOT regress a captured payment to failed
        if payment.status == PaymentStatus.CAPTURED.value:
            logger.info(
                "stale_event_ignored",
                extra={
                    "event_id": payment_event.idempotency_key,
                    "payment_id": str(payment.id),
                    "reason": "payment_already_captured",
                },
            )
            audit = AuditLog(
                event_type="STALE_PAYMENT_FAILURE_IGNORED",
                actor_type=AuditActorType.SYSTEM_EVENT.value,
                actor_id="event_processor",
                recovery_case_id=None,
                entity_type="payments",
                entity_id=payment.id,
                action="STALE_EVENT_IGNORED",
                previous_state={"status": payment.status},
                new_state={"status": payment.status},
                metadata_json={
                    "event_id": payment_event.idempotency_key,
                    "reason": "payment_already_captured",
                },
            )
            db.add(audit)
            db.flush()
            return None

        # Update payment state
        payment.status = PaymentStatus.FAILED.value
        customer.failed_payments_count += 1

        # Check for existing active recovery case for this payment
        case = (
            db.query(RecoveryCase)
            .filter(
                RecoveryCase.payment_id == payment.id,
                RecoveryCase.status.in_(ACTIVE_RECOVERY_STATUSES),
            )
            .first()
        )

        now_utc = datetime.now(UTC)
        error_reason = payload_payment.get("error_reason")

        if case:
            # Update existing active case
            prev_state = {
                "status": case.status,
                "attempts_count": case.total_attempts_count,
                "latest_failure_reason": case.latest_failure_reason,
            }
            case.total_attempts_count += 1
            if error_reason:
                case.latest_failure_reason = error_reason
            case.next_action_due_at = now_utc + timedelta(hours=2)

            if case.total_attempts_count >= case.max_allowed_attempts:
                case.recovery_stage = RecoveryStage.ESCALATION.value

            audit = AuditLog(
                event_type="RECOVERY_CASE_UPDATED",
                actor_type=AuditActorType.SYSTEM_EVENT.value,
                actor_id="event_processor",
                recovery_case_id=case.id,
                entity_type="recovery_cases",
                entity_id=case.id,
                action="PAYMENT_FAILURE_UPDATED_CASE",
                previous_state=prev_state,
                new_state={
                    "status": case.status,
                    "attempts_count": case.total_attempts_count,
                    "latest_failure_reason": case.latest_failure_reason,
                },
                metadata_json={
                    "payment_id": str(payment.id),
                    "event_id": payment_event.idempotency_key,
                },
            )
            db.add(audit)
            db.flush()
            logger.info(
                "recovery_case_updated",
                extra={"case_id": str(case.id), "payment_id": str(payment.id)},
            )
            return case

        # Create new RecoveryCase
        amount_at_risk = max(0, payment.amount)
        case = RecoveryCase(
            payment_id=payment.id,
            customer_id=customer.id,
            status=RecoveryCaseStatus.OPEN.value,
            recovery_stage=RecoveryStage.INITIAL_FAILURE.value,
            amount_at_risk=amount_at_risk,
            recovered_amount=0,
            total_attempts_count=1,
            max_allowed_attempts=3,
            latest_failure_reason=error_reason,
            opened_at=now_utc,
            next_action_due_at=now_utc + timedelta(hours=2),
            metadata_json={},
        )
        db.add(case)
        db.flush()

        audit = AuditLog(
            event_type="RECOVERY_CASE_OPENED",
            actor_type=AuditActorType.SYSTEM_EVENT.value,
            actor_id="event_processor",
            recovery_case_id=case.id,
            entity_type="recovery_cases",
            entity_id=case.id,
            action="RECOVERY_CASE_OPENED",
            previous_state=None,
            new_state={
                "status": case.status,
                "amount_at_risk": case.amount_at_risk,
                "recovery_stage": case.recovery_stage,
            },
            metadata_json={
                "payment_id": str(payment.id),
                "event_id": payment_event.idempotency_key,
            },
        )
        db.add(audit)
        db.flush()
        logger.info(
            "recovery_case_created",
            extra={"case_id": str(case.id), "payment_id": str(payment.id)},
        )
        return case

    def handle_payment_captured(
        self,
        db: Session,
        payment_event: PaymentEvent,
        payload_payment: dict[str, Any],
    ) -> RecoveryCase | None:
        """
        Process a payment.captured event deterministically.

        1. Locate or create Customer and Payment entities.
        2. Record successful PaymentAttempt.
        3. Update Payment state to CAPTURED.
        4. Resolve active RecoveryCase (recovered_amount = min(payment.amount, risk)).
        5. Write structured AuditLog.
        """
        logger.info(
            "payment_captured",
            extra={
                "event_id": payment_event.idempotency_key,
                "payment_id": payload_payment.get("id"),
            },
        )

        customer = self.get_or_create_customer(db, payload_payment)
        payment = self.get_or_create_payment(db, customer, payload_payment)
        self.record_payment_attempt(
            db, payment, payload_payment, PaymentAttemptStatus.SUCCESS
        )

        now_utc = datetime.now(UTC)
        payment.status = PaymentStatus.CAPTURED.value
        payment.captured_at = now_utc

        # Locate active recovery case for this payment
        case = (
            db.query(RecoveryCase)
            .filter(
                RecoveryCase.payment_id == payment.id,
                RecoveryCase.status.in_(ACTIVE_RECOVERY_STATUSES),
            )
            .first()
        )

        if case:
            prev_state = {
                "status": case.status,
                "recovered_amount": case.recovered_amount,
            }
            # Defensive calculation: recovered_amount must not exceed amount_at_risk
            recovered_amt = min(payment.amount, case.amount_at_risk)
            case.status = RecoveryCaseStatus.RECOVERED.value
            case.recovered_amount = max(0, recovered_amt)
            case.resolved_at = now_utc
            case.closed_reason = RecoveryCaseClosedReason.PAYMENT_RECOVERED.value
            customer.recovered_payments_count += 1

            audit = AuditLog(
                event_type="RECOVERY_CASE_RECOVERED",
                actor_type=AuditActorType.SYSTEM_EVENT.value,
                actor_id="event_processor",
                recovery_case_id=case.id,
                entity_type="recovery_cases",
                entity_id=case.id,
                action="PAYMENT_CAPTURED_CASE_RESOLVED",
                previous_state=prev_state,
                new_state={
                    "status": case.status,
                    "recovered_amount": case.recovered_amount,
                    "closed_reason": case.closed_reason,
                },
                metadata_json={
                    "payment_id": str(payment.id),
                    "captured_amount": payment.amount,
                    "event_id": payment_event.idempotency_key,
                },
            )
            db.add(audit)
            db.flush()
            logger.info(
                "recovery_case_resolved",
                extra={"case_id": str(case.id), "payment_id": str(payment.id)},
            )
            return case

        # No active recovery case (clean direct capture)
        audit = AuditLog(
            event_type="PAYMENT_CAPTURED",
            actor_type=AuditActorType.SYSTEM_EVENT.value,
            actor_id="event_processor",
            recovery_case_id=None,
            entity_type="payments",
            entity_id=payment.id,
            action="PAYMENT_DIRECT_CAPTURED",
            previous_state=None,
            new_state={"status": payment.status, "amount": payment.amount},
            metadata_json={
                "payment_id": str(payment.id),
                "event_id": payment_event.idempotency_key,
            },
        )
        db.add(audit)
        db.flush()
        return None

    def handle_subscription_halted(
        self,
        db: Session,
        payment_event: PaymentEvent,
        payload_subscription: dict[str, Any],
        payload_payment: dict[str, Any] | None,
    ) -> RecoveryCase | None:
        """
        Process a subscription.halted event deterministically.

        1. Locate or update Subscription state to HALTED.
        2. If payment payload is present, trigger payment failure handling.
        3. If a recovery case exists, escalate stage to ESCALATION.
        4. Write structured AuditLog.
        """
        sub_id = payload_subscription.get("id")
        plan_id = payload_subscription.get("plan_id")

        subscription = None
        if sub_id:
            subscription = (
                db.query(Subscription)
                .filter_by(razorpay_subscription_id=str(sub_id))
                .first()
            )

        customer = None
        if payload_payment:
            customer = self.get_or_create_customer(db, payload_payment)

        if not subscription and sub_id and customer:
            subscription = Subscription(
                customer_id=customer.id,
                razorpay_subscription_id=str(sub_id),
                plan_name=str(plan_id or "Subscription"),
                billing_cadence="MONTHLY",
                recurring_amount=max(0, int(payload_subscription.get("amount", 0))),
                currency="INR",
                status=SubscriptionStatus.HALTED.value,
                metadata_json={},
            )
            db.add(subscription)
            db.flush()
        elif subscription:
            subscription.status = SubscriptionStatus.HALTED.value

        case = None
        if payload_payment:
            case = self.handle_payment_failure(db, payment_event, payload_payment)
            if case:
                case.recovery_stage = RecoveryStage.ESCALATION.value

        audit = AuditLog(
            event_type="SUBSCRIPTION_HALTED",
            actor_type=AuditActorType.SYSTEM_EVENT.value,
            actor_id="event_processor",
            recovery_case_id=case.id if case else None,
            entity_type="subscriptions",
            entity_id=subscription.id if subscription else None,
            action="SUBSCRIPTION_HALTED_ESCALATION",
            previous_state=None,
            new_state={"status": SubscriptionStatus.HALTED.value},
            metadata_json={
                "subscription_id": str(sub_id),
                "event_id": payment_event.idempotency_key,
            },
        )
        db.add(audit)
        db.flush()
        return case


recovery_case_service = RecoveryCaseService()
