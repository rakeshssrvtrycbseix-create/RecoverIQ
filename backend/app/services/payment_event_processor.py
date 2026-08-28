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
        4. Maintains strict transactional atomicity.
        """
        event_id = payment_event.idempotency_key
        event_type = payment_event.event_type

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
            subscription_data = (
                payload_container["subscription"].get("entity") or {}
            )

        # 3. Route to deterministic handler
        recovery_case: RecoveryCase | None = None
        try:
            if event_type == "payment.failed":
                if payment_data:
                    recovery_case = (
                        recovery_case_service.handle_payment_failure(
                            db, payment_event, payment_data
                        )
                    )
            elif event_type == "payment.captured":
                if payment_data:
                    recovery_case = (
                        recovery_case_service.handle_payment_captured(
                            db, payment_event, payment_data
                        )
                    )
            elif event_type == "subscription.halted":
                recovery_case = (
                    recovery_case_service.handle_subscription_halted(
                        db,
                        payment_event,
                        subscription_data,
                        payment_data or None,
                    )
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

            # 4. Update PaymentEvent status
            payment_event.processing_status = (
                PaymentEventProcessingStatus.PROCESSED.value
            )
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
            db.rollback()
            logger.error(
                "event_processing_failed",
                extra={"event_id": event_id, "error": str(exc)},
            )
            # Update event status to FAILED in isolated commit
            try:
                payment_event.processing_status = (
                    PaymentEventProcessingStatus.FAILED.value
                )
                payment_event.processing_error = str(exc)
                db.commit()
            except Exception:
                db.rollback()

            raise


payment_event_processor = PaymentEventProcessor()
