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
        auto_process: bool = True,
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
            self.dispatch_event(
                payment_event=new_event,
                db=db if auto_process else None,
            )
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

    def dispatch_event(
        self,
        payment_event: PaymentEvent,
        db: Session | None = None,
    ) -> None:
        """
        Dispatch abstraction exposing the future async worker boundary.

        Logs dispatch request. In local/synchronous mode, triggers the
        deterministic payment event processor.
        """
        logger.info(
            "processing_dispatch_requested",
            extra={
                "event_id": payment_event.idempotency_key,
                "event_type": payment_event.event_type,
                "payment_event_id": str(payment_event.id),
            },
        )
        if db is not None:
            from app.services.payment_event_processor import (
                payment_event_processor,
            )

            payment_event_processor.process_payment_event(
                db=db,
                payment_event=payment_event,
            )


payment_event_service = PaymentEventService()
