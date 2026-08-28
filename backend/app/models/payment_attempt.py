import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    Uuid,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.payment import Payment


class PaymentAttempt(Base):
    """Records an individual physical payment attempt and gateway response."""

    __tablename__ = "payment_attempts"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    payment_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("payments.id", ondelete="CASCADE"),
        nullable=False,
    )
    attempt_number: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )
    razorpay_payment_id: Mapped[str | None] = mapped_column(
        String(128),
        unique=True,
        nullable=True,
    )
    payment_method: Mapped[str | None] = mapped_column(
        String(32),
        nullable=True,
    )
    payment_method_sub_type: Mapped[str | None] = mapped_column(
        String(64),
        nullable=True,
    )
    amount: Mapped[int] = mapped_column(
        BigInteger,
        nullable=False,
    )
    status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
    )
    error_code: Mapped[str | None] = mapped_column(
        String(64),
        nullable=True,
    )
    error_source: Mapped[str | None] = mapped_column(
        String(64),
        nullable=True,
    )
    error_step: Mapped[str | None] = mapped_column(
        String(64),
        nullable=True,
    )
    error_reason: Mapped[str | None] = mapped_column(
        String(128),
        nullable=True,
    )
    error_description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )
    initiated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    # Relationships
    payment: Mapped["Payment"] = relationship(
        "Payment",
        back_populates="attempts",
    )

    __table_args__ = (
        CheckConstraint("amount >= 0", name="chk_payment_attempt_amount_non_negative"),
        UniqueConstraint("payment_id", "attempt_number", name="uq_payment_attempt_seq"),
        Index("idx_payment_attempts_payment_id", "payment_id"),
        Index("idx_payment_attempts_error_reason", "error_reason"),
    )
