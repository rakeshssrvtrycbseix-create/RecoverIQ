import logging
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from sqlalchemy.orm import Session

from app.models import (
    AuditActorType,
    AuditLog,
    PaymentEvent,
    PaymentEventProcessingStatus,
    RecoveryCase,
)
from app.services.recovery_case_service import recovery_case_service

logger = logging.getLogger(__name__)


@dataclass
class ProcessedEventResult:
    """Represents the outcome of processing a payment event."""

    event_id: str
    event_type: str
    processing_status: str
    already_processed: bool
    recovery_case_id: uuid.UUID | None
    error: str | None = None


class PaymentEventProcessor:
    """Deterministic event consumer processing persisted PaymentEvent records."""

    def _record_failure_status(
        self,
        db: Session,
        payment_event_id: uuid.UUID,
        error_message: str,
    ) -> None:
        """
        Record processing failure status in an isolated transaction after rollback.

        Guarantees that all uncommitted business state is discarded while
        persisting processing_status=FAILED and processing_error to payment_events.
        """
        try:
            db.rollback()
            event = db.query(PaymentEvent).filter_by(id=payment_event_id).first()
            if event:
                event.processing_status = PaymentEventProcessingStatus.FAILED.value
                event.processing_error = error_message
                db.commit()
                db.refresh(event)
        except Exception as err:
            db.rollback()
            logger.error(
                "failed_to_record_event_failure_status",
                extra={
                    "payment_event_id": str(payment_event_id),
                    "error": str(err),
                },
            )

    def process_payment_event(
        self,
        db: Session,
        payment_event: PaymentEvent,
    ) -> ProcessedEventResult:
        """
        Process a persisted PaymentEvent deterministically.

        Guarantees:
        1. Processing is idempotent (re-running a PROCESSED event is a no-op).
        2. Routes payment.failed, payment.captured, subscription.halted.
        3. Safely ignores unhandled events without failing.
        4. Atomic transaction boundary for business state mutations.
        5. On exception, rolls back business state and records FAILED status.
        6. Allows retrying previously FAILED events.
        """
        event_id = payment_event.idempotency_key
        event_type = payment_event.event_type
        payment_event_id = payment_event.id

        # 1. Idempotency Check: Don't re-process already processed events
        if (
            payment_event.processing_status
            == PaymentEventProcessingStatus.PROCESSED.value
        ):
            logger.info(
                "event_already_processed",
                extra={"event_id": event_id, "event_type": event_type},
            )
            return ProcessedEventResult(
                event_id=event_id,
                event_type=event_type,
                processing_status=payment_event.processing_status,
                already_processed=True,
                recovery_case_id=None,
            )

        logger.info(
            "event_processing_started",
            extra={"event_id": event_id, "event_type": event_type},
        )

        # 2. Extract nested entities from sanitized payload
        payload = payment_event.payload or {}
        payload_container: dict[str, Any] = (
            payload.get("payload")
            if isinstance(payload.get("payload"), dict)
            else payload
        )

        payment_data = {}
        if isinstance(payload_container.get("payment"), dict):
            payment_data = payload_container["payment"].get("entity") or {}

        subscription_data = {}
        if isinstance(payload_container.get("subscription"), dict):
            subscription_data = payload_container["subscription"].get("entity") or {}

        # 3. Route to deterministic handler
        recovery_case: RecoveryCase | None = None
        try:
            if event_type == "payment.failed":
                if payment_data:
                    recovery_case = recovery_case_service.handle_payment_failure(
                        db, payment_event, payment_data
                    )
            elif event_type == "payment.captured":
                if payment_data:
                    recovery_case = recovery_case_service.handle_payment_captured(
                        db, payment_event, payment_data
                    )
            elif event_type == "subscription.halted":
                recovery_case = recovery_case_service.handle_subscription_halted(
                    db,
                    payment_event,
                    subscription_data,
                    payment_data or None,
                )
            else:
                # Ignore non-recovery events (e.g. payment.authorized)
                logger.info(
                    "non_recovery_event_ignored",
                    extra={"event_id": event_id, "event_type": event_type},
                )
                audit = AuditLog(
                    event_type="NON_RECOVERY_EVENT_IGNORED",
                    actor_type=AuditActorType.SYSTEM_EVENT.value,
                    actor_id="event_processor",
                    recovery_case_id=None,
                    entity_type="payment_events",
                    entity_id=payment_event.id,
                    action="EVENT_IGNORED_NON_RECOVERY",
                    metadata_json={
                        "event_type": event_type,
                        "event_id": event_id,
                    },
                )
                db.add(audit)
                db.flush()

            # 4. Update PaymentEvent status to PROCESSED and clear prior errors
            payment_event.processing_status = (
                PaymentEventProcessingStatus.PROCESSED.value
            )
            payment_event.processing_error = None
            payment_event.processed_at = datetime.now(UTC)
            if recovery_case:
                payment_event.payment_id = recovery_case.payment_id

            # 5. Commit state changes atomically
            db.commit()
            db.refresh(payment_event)

            logger.info(
                "event_processing_completed",
                extra={
                    "event_id": event_id,
                    "event_type": event_type,
                    "case_id": str(recovery_case.id) if recovery_case else None,
                },
            )

            return ProcessedEventResult(
                event_id=event_id,
                event_type=event_type,
                processing_status=payment_event.processing_status,
                already_processed=False,
                recovery_case_id=recovery_case.id if recovery_case else None,
            )

        except Exception as exc:
            logger.error(
                "event_processing_failed",
                extra={"event_id": event_id, "error": str(exc)},
            )
            # Record failure in isolated transaction after full rollback
            self._record_failure_status(
                db=db,
                payment_event_id=payment_event_id,
                error_message=str(exc),
            )
            raise


payment_event_processor = PaymentEventProcessor()
