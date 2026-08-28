import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import DateTime, Integer, String, Uuid, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import JSON

from app.core.database import Base
from app.models.enums import CustomerRiskTier

if TYPE_CHECKING:
    from app.models.payment import Payment
    from app.models.recovery_case import RecoveryCase
    from app.models.subscription import Subscription

JSON_TYPE = JSONB().with_variant(JSON, "sqlite")


class Customer(Base):
    """Represents a merchant customer associated with payments and subscriptions."""

    __tablename__ = "customers"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    external_customer_id: Mapped[str] = mapped_column(
        String(128),
        unique=True,
        nullable=False,
    )
    razorpay_customer_id: Mapped[str | None] = mapped_column(
        String(128),
        unique=True,
        nullable=True,
    )
    email_masked: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )
    phone_masked: Mapped[str | None] = mapped_column(
        String(64),
        nullable=True,
    )
    risk_tier: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default=CustomerRiskTier.STANDARD.value,
    )
    total_payments_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )
    failed_payments_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )
    recovered_payments_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
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
    subscriptions: Mapped[list["Subscription"]] = relationship(
        "Subscription",
        back_populates="customer",
        cascade="all, delete-orphan",
    )
    payments: Mapped[list["Payment"]] = relationship(
        "Payment",
        back_populates="customer",
    )
    recovery_cases: Mapped[list["RecoveryCase"]] = relationship(
        "RecoveryCase",
        back_populates="customer",
    )
