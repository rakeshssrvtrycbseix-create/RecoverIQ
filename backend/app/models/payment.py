import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    String,
    Uuid,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import JSON

from app.core.database import Base
from app.models.enums import PaymentStatus

if TYPE_CHECKING:
    from app.models.customer import Customer
    from app.models.payment_attempt import PaymentAttempt
    from app.models.payment_event import PaymentEvent
    from app.models.recovery_case import RecoveryCase
    from app.models.subscription import Subscription

JSON_TYPE = JSONB().with_variant(JSON, "sqlite")


class Payment(Base):
    """Represents a canonical payment transaction/order/invoice intent."""

    __tablename__ = "payments"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    customer_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("customers.id", ondelete="RESTRICT"),
        nullable=False,
    )
    subscription_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("subscriptions.id", ondelete="SET NULL"),
        nullable=True,
    )
    external_order_id: Mapped[str | None] = mapped_column(
        String(128),
        nullable=True,
    )
    razorpay_order_id: Mapped[str | None] = mapped_column(
        String(128),
        unique=True,
        nullable=True,
    )
    razorpay_invoice_id: Mapped[str | None] = mapped_column(
        String(128),
        unique=True,
        nullable=True,
    )
    amount: Mapped[int] = mapped_column(
        BigInteger,
        nullable=False,
    )
    currency: Mapped[str] = mapped_column(
        String(3),
        nullable=False,
        default="INR",
    )
    status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default=PaymentStatus.CREATED.value,
    )
    due_date: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    captured_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    metadata_json: Mapped[dict[str, Any]] = mapped_column(
        "metadata",
        JSON_TYPE,
        nullable=False,
        default=dict,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    # Relationships
    customer: Mapped["Customer"] = relationship(
        "Customer",
        back_populates="payments",
    )
    subscription: Mapped["Subscription | None"] = relationship(
        "Subscription",
        back_populates="payments",
    )
    attempts: Mapped[list["PaymentAttempt"]] = relationship(
        "PaymentAttempt",
        back_populates="payment",
        cascade="all, delete-orphan",
        order_by="PaymentAttempt.attempt_number",
    )
    events: Mapped[list["PaymentEvent"]] = relationship(
        "PaymentEvent",
        back_populates="payment",
    )
    recovery_cases: Mapped[list["RecoveryCase"]] = relationship(
        "RecoveryCase",
        back_populates="payment",
    )

    __table_args__ = (
        CheckConstraint("amount >= 0", name="chk_payment_amount_non_negative"),
        Index("idx_payments_customer_id", "customer_id"),
        Index("idx_payments_subscription_id", "subscription_id"),
        Index("idx_payments_status_created", "status", "created_at"),
    )
