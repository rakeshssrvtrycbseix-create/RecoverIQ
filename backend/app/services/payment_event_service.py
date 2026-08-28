import logging
from dataclasses import dataclass
from typing import Any

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models import PaymentEvent, PaymentEventProcessingStatus, PaymentEventSource

logger = logging.getLogger(__name__)


@dataclass
class IngestionResult:
    """Represents the outcome of a webhook event ingestion."""

    event_id: str
    event_type: str
    is_duplicate: bool
    payment_event: PaymentEvent


class PaymentEventService:
    """Service handling payment event persistence, deduplication, and async dispatch."""

    def ingest_event(
        self,
        db: Session,
        event_id: str,
        event_type: str,
        payload: dict[str, Any],
        source: str = PaymentEventSource.RAZORPAY_WEBHOOK.value,
    ) -> IngestionResult:
        """
        Persist an inbound payment event with database-backed idempotency.

        Guarantees:
        1. Duplicate events return is_duplicate=True without dispatch.
        2. Database errors rollback cleanly and raise exceptions.
        3. Fresh events are persisted and dispatched to async worker boundary.
        """
        # 1. Optimistic fast-path check for existing event
        existing_event = (
            db.query(PaymentEvent).filter_by(idempotency_key=event_id).first()
        )
        if existing_event:
            logger.info(
                "duplicate_event",
                extra={
                    "event_id": event_id,
                    "event_type": existing_event.event_type,
                    "status": existing_event.processing_status,
                },
            )
            return IngestionResult(
                event_id=event_id,
                event_type=existing_event.event_type,
                is_duplicate=True,
                payment_event=existing_event,
            )

        # 2. Prepare new PaymentEvent entity with sanitized payload
        new_event = PaymentEvent(
            idempotency_key=event_id,
            razorpay_event_id=event_id,
            event_type=event_type,
            source=source,
            payload=payload,
            processing_status=PaymentEventProcessingStatus.RECEIVED.value,
        )

        # 3. Attempt database insertion (authoritative unique constraint check)
        try:
            db.add(new_event)
            db.commit()
            db.refresh(new_event)
            logger.info(
                "event_persisted",
                extra={
                    "event_id": event_id,
                    "event_type": event_type,
                    "payment_event_id": str(new_event.id),
                },
            )
        except IntegrityError:
            # Concurrent race condition: another transaction committed with same key
            db.rollback()
            existing = (
                db.query(PaymentEvent).filter_by(idempotency_key=event_id).first()
            )
            if existing:
                logger.info(
                    "duplicate_event",
                    extra={
                        "event_id": event_id,
                        "event_type": event_type,
                        "reason": "concurrent_insert_conflict",
                    },
                )
                return IngestionResult(
                    event_id=event_id,
                    event_type=event_type,
                    is_duplicate=True,
                    payment_event=existing,
                )
            # Re-raise if IntegrityError was not a duplicate key conflict
            raise
        except Exception as exc:
            db.rollback()
            logger.error(
                "database_persistence_failure",
                extra={"event_id": event_id, "error": str(exc)},
            )
            raise

        # 4. Dispatch to downstream processing boundary
        try:
            self.dispatch_event(new_event)
        except Exception as exc:
            logger.error(
                "dispatch_error",
                extra={
                    "event_id": event_id,
                    "payment_event_id": str(new_event.id),
                    "error": str(exc),
                },
            )

        return IngestionResult(
            event_id=event_id,
            event_type=event_type,
            is_duplicate=False,
            payment_event=new_event,
        )

    def dispatch_event(self, payment_event: PaymentEvent) -> None:
        """
        Minimal dispatch abstraction exposing the future async worker boundary.

        Logs dispatch request without executing heavy synchronous business logic.
        """
        logger.info(
            "processing_dispatch_requested",
            extra={
                "event_id": payment_event.idempotency_key,
                "event_type": payment_event.event_type,
                "payment_event_id": str(payment_event.id),
            },
        )


payment_event_service = PaymentEventService()
