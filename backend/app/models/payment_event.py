import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import DateTime, ForeignKey, Index, String, Text, Uuid, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import JSON

from app.core.database import Base
from app.models.enums import PaymentEventProcessingStatus, PaymentEventSource

if TYPE_CHECKING:
    from app.models.payment import Payment

JSON_TYPE = JSONB().with_variant(JSON, "sqlite")


class PaymentEvent(Base):
    """Immutable ledger of inbound webhooks and gateway events."""

    __tablename__ = "payment_events"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    idempotency_key: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        nullable=False,
    )
    payment_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("payments.id", ondelete="SET NULL"),
        nullable=True,
    )
    source: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default=PaymentEventSource.RAZORPAY_WEBHOOK.value,
    )
    event_type: Mapped[str] = mapped_column(
        String(128),
        nullable=False,
    )
    razorpay_event_id: Mapped[str | None] = mapped_column(
        String(128),
        unique=True,
        nullable=True,
    )
    payload: Mapped[dict[str, Any]] = mapped_column(
        JSON_TYPE,
        nullable=False,
    )
    processing_status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default=PaymentEventProcessingStatus.RECEIVED.value,
    )
    processing_error: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )
    received_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    processed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    # Relationships
    payment: Mapped["Payment | None"] = relationship(
        "Payment",
        back_populates="events",
    )

    __table_args__ = (
        Index("idx_payment_events_type_status", "event_type", "processing_status"),
        Index("idx_payment_events_payment_id", "payment_id"),
    )
