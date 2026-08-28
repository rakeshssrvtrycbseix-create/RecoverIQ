import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import (
    BigInteger,
    Boolean,
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
from app.models.enums import SubscriptionStatus

if TYPE_CHECKING:
    from app.models.customer import Customer
    from app.models.payment import Payment

JSON_TYPE = JSONB().with_variant(JSON, "sqlite")


class Subscription(Base):
    """Tracks recurring subscription contracts, billing plans, and cadence."""

    __tablename__ = "subscriptions"

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
    external_subscription_id: Mapped[str | None] = mapped_column(
        String(128),
        nullable=True,
    )
    razorpay_subscription_id: Mapped[str | None] = mapped_column(
        String(128),
        unique=True,
        nullable=True,
    )
    plan_name: Mapped[str] = mapped_column(
        String(128),
        nullable=False,
    )
    billing_cadence: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
    )
    recurring_amount: Mapped[int] = mapped_column(
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
        default=SubscriptionStatus.ACTIVE.value,
    )
    current_period_start: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    current_period_end: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    cancel_at_period_end: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
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
        back_populates="subscriptions",
    )
    payments: Mapped[list["Payment"]] = relationship(
        "Payment",
        back_populates="subscription",
    )

    __table_args__ = (
        CheckConstraint(
            "recurring_amount >= 0",
            name="chk_subscription_recurring_amount_non_negative",
        ),
        Index("idx_subscriptions_customer_id", "customer_id"),
        Index("idx_subscriptions_status", "status"),
    )
