import uuid
from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING, Any

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Numeric,
    String,
    Text,
    Uuid,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import JSON

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.ml_prediction import MLPrediction
    from app.models.policy_decision import PolicyDecision
    from app.models.recovery_case import RecoveryCase

JSON_TYPE = JSONB().with_variant(JSON, "sqlite")


class AgentDecision(Base):
    """Immutable record of LLM AI recovery agent reasoning and recommendations."""

    __tablename__ = "agent_decisions"

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
    ml_prediction_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("ml_predictions.id", ondelete="SET NULL"),
        nullable=True,
    )
    agent_name: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        default="RecoveryOrchestrator",
    )
    agent_version: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
    )
    prompt_template_version: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
    )
    proposed_action_type: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
    )
    confidence_score: Mapped[Decimal] = mapped_column(
        Numeric(5, 4),
        nullable=False,
    )
    reasoning_summary: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )
    suggested_payload: Mapped[dict[str, Any]] = mapped_column(
        JSON_TYPE,
        nullable=False,
        default=dict,
    )
    token_usage: Mapped[dict[str, Any] | None] = mapped_column(
        JSON_TYPE,
        nullable=True,
    )
    decided_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    # Relationships
    recovery_case: Mapped["RecoveryCase"] = relationship(
        "RecoveryCase",
        back_populates="agent_decisions",
    )
    ml_prediction: Mapped["MLPrediction | None"] = relationship(
        "MLPrediction",
        back_populates="agent_decisions",
    )
    policy_decisions: Mapped[list["PolicyDecision"]] = relationship(
        "PolicyDecision",
        back_populates="agent_decision",
    )

    __table_args__ = (
        CheckConstraint(
            "confidence_score >= 0.0000 AND confidence_score <= 1.0000",
            name="chk_agent_confidence_score_range",
        ),
        Index("idx_agent_decisions_case_id", "recovery_case_id"),
        Index("idx_agent_decisions_ml_prediction_id", "ml_prediction_id"),
        Index("idx_agent_decisions_action_type", "proposed_action_type"),
        Index("idx_agent_decisions_decided_at", "decided_at"),
    )
