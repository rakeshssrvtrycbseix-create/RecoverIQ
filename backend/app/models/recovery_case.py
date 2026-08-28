import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Uuid,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import JSON

from app.core.database import Base
from app.models.enums import RecoveryCaseStatus, RecoveryStage

if TYPE_CHECKING:
    from app.models.action_result import ActionResult  # noqa: F401
    from app.models.agent_decision import AgentDecision
    from app.models.audit_log import AuditLog
    from app.models.customer import Customer
    from app.models.ml_prediction import MLPrediction
    from app.models.payment import Payment
    from app.models.policy_decision import PolicyDecision
    from app.models.recovery_action import RecoveryAction

JSON_TYPE = JSONB().with_variant(JSON, "sqlite")


class RecoveryCase(Base):
    """Central operational aggregate tracking payment recovery lifecycle."""

    __tablename__ = "recovery_cases"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    payment_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("payments.id", ondelete="RESTRICT"),
        nullable=False,
    )
    customer_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("customers.id", ondelete="RESTRICT"),
        nullable=False,
    )
    status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default=RecoveryCaseStatus.OPEN.value,
    )
    recovery_stage: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default=RecoveryStage.INITIAL_FAILURE.value,
    )
    amount_at_risk: Mapped[int] = mapped_column(
        BigInteger,
        nullable=False,
    )
    recovered_amount: Mapped[int] = mapped_column(
        BigInteger,
        nullable=False,
        default=0,
    )
    total_attempts_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )
    max_allowed_attempts: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=3,
    )
    latest_failure_reason: Mapped[str | None] = mapped_column(
        String(128),
        nullable=True,
    )
    opened_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    next_action_due_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    resolved_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    closed_reason: Mapped[str | None] = mapped_column(
        String(64),
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
    payment: Mapped["Payment"] = relationship(
        "Payment",
        back_populates="recovery_cases",
    )
    customer: Mapped["Customer"] = relationship(
        "Customer",
        back_populates="recovery_cases",
    )
    predictions: Mapped[list["MLPrediction"]] = relationship(
        "MLPrediction",
        back_populates="recovery_case",
        cascade="all, delete-orphan",
        order_by="MLPrediction.predicted_at",
    )
    agent_decisions: Mapped[list["AgentDecision"]] = relationship(
        "AgentDecision",
        back_populates="recovery_case",
        cascade="all, delete-orphan",
        order_by="AgentDecision.decided_at",
    )
    policy_decisions: Mapped[list["PolicyDecision"]] = relationship(
        "PolicyDecision",
        back_populates="recovery_case",
        cascade="all, delete-orphan",
        order_by="PolicyDecision.decided_at",
    )
    actions: Mapped[list["RecoveryAction"]] = relationship(
        "RecoveryAction",
        back_populates="recovery_case",
        order_by="RecoveryAction.scheduled_for",
    )
    audit_logs: Mapped[list["AuditLog"]] = relationship(
        "AuditLog",
        back_populates="recovery_case",
    )

    __table_args__ = (
        CheckConstraint(
            "amount_at_risk >= 0",
            name="chk_case_amount_at_risk_non_negative",
        ),
        CheckConstraint(
            "recovered_amount >= 0",
            name="chk_case_recovered_amount_non_negative",
        ),
        CheckConstraint(
            "recovered_amount <= amount_at_risk",
            name="chk_case_recovered_not_exceed_risk",
        ),
        Index("idx_recovery_cases_payment_id", "payment_id"),
        Index("idx_recovery_cases_customer_id", "customer_id"),
        Index("idx_recovery_cases_status_next_action", "status", "next_action_due_at"),
        Index("idx_recovery_cases_opened_at", "opened_at"),
    )
