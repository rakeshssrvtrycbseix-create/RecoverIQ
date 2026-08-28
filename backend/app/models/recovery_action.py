import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import (
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
from app.models.enums import RecoveryActionStatus

if TYPE_CHECKING:
    from app.models.action_result import ActionResult
    from app.models.policy_decision import PolicyDecision
    from app.models.recovery_case import RecoveryCase

JSON_TYPE = JSONB().with_variant(JSON, "sqlite")


class RecoveryAction(Base):
    """Represents an authorized recovery action scheduled/executed by the system."""

    __tablename__ = "recovery_actions"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    recovery_case_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("recovery_cases.id", ondelete="RESTRICT"),
        nullable=False,
    )
    policy_decision_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("policy_decisions.id", ondelete="RESTRICT"),
        nullable=False,
    )
    action_idempotency_key: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        nullable=False,
    )
    action_type: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
    )
    status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default=RecoveryActionStatus.PENDING.value,
    )
    scheduled_for: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    dispatched_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    action_payload: Mapped[dict[str, Any]] = mapped_column(
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
    recovery_case: Mapped["RecoveryCase"] = relationship(
        "RecoveryCase",
        back_populates="actions",
    )
    policy_decision: Mapped["PolicyDecision"] = relationship(
        "PolicyDecision",
        back_populates="recovery_actions",
    )
    results: Mapped[list["ActionResult"]] = relationship(
        "ActionResult",
        back_populates="recovery_action",
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        Index("idx_recovery_actions_case_id", "recovery_case_id"),
        Index("idx_recovery_actions_policy_decision_id", "policy_decision_id"),
        Index("idx_recovery_actions_status_scheduled", "status", "scheduled_for"),
    )
