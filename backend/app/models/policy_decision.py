import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import DateTime, ForeignKey, Index, String, Text, Uuid, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import JSON

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.agent_decision import AgentDecision
    from app.models.recovery_action import RecoveryAction
    from app.models.recovery_case import RecoveryCase

JSON_TYPE = JSONB().with_variant(JSON, "sqlite")


class PolicyDecision(Base):
    """Immutable record of deterministic safety validation for proposed actions."""

    __tablename__ = "policy_decisions"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    recovery_case_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("recovery_cases.id", ondelete="CASCADE"),
        nullable=False,
    )
    agent_decision_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("agent_decisions.id", ondelete="SET NULL"),
        nullable=True,
    )
    evaluation_result: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
    )
    policy_engine_version: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
    )
    triggered_rule_code: Mapped[str | None] = mapped_column(
        String(64),
        nullable=True,
    )
    rule_name: Mapped[str | None] = mapped_column(
        String(128),
        nullable=True,
    )
    evaluation_details: Mapped[dict[str, Any]] = mapped_column(
        JSON_TYPE,
        nullable=False,
        default=dict,
    )
    decision_reason: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )
    decided_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    # Relationships
    recovery_case: Mapped["RecoveryCase"] = relationship(
        "RecoveryCase",
        back_populates="policy_decisions",
    )
    agent_decision: Mapped["AgentDecision | None"] = relationship(
        "AgentDecision",
        back_populates="policy_decisions",
    )
    recovery_actions: Mapped[list["RecoveryAction"]] = relationship(
        "RecoveryAction",
        back_populates="policy_decision",
    )

    __table_args__ = (
        Index("idx_policy_decisions_case_id", "recovery_case_id"),
        Index("idx_policy_decisions_agent_decision_id", "agent_decision_id"),
        Index("idx_policy_decisions_result", "evaluation_result"),
        Index("idx_policy_decisions_rule_code", "triggered_rule_code"),
    )
