import uuid
from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING, Any

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Uuid,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import JSON

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.agent_decision import AgentDecision
    from app.models.recovery_case import RecoveryCase

JSON_TYPE = JSONB().with_variant(JSON, "sqlite")


class MLPrediction(Base):
    """Immutable record of ML inference runs and recovery scoring."""

    __tablename__ = "ml_predictions"

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
    model_name: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
    )
    model_version: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
    )
    recovery_probability: Mapped[Decimal] = mapped_column(
        Numeric(5, 4),
        nullable=False,
    )
    predicted_channel: Mapped[str | None] = mapped_column(
        String(32),
        nullable=True,
    )
    predicted_delay_hours: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )
    feature_vector_snapshot: Mapped[dict[str, Any]] = mapped_column(
        JSON_TYPE,
        nullable=False,
    )
    predicted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    # Relationships
    recovery_case: Mapped["RecoveryCase"] = relationship(
        "RecoveryCase",
        back_populates="predictions",
    )
    agent_decisions: Mapped[list["AgentDecision"]] = relationship(
        "AgentDecision",
        back_populates="ml_prediction",
    )

    __table_args__ = (
        CheckConstraint(
            "recovery_probability >= 0.0000 AND recovery_probability <= 1.0000",
            name="chk_ml_recovery_probability_range",
        ),
        Index("idx_ml_predictions_case_id", "recovery_case_id"),
        Index("idx_ml_predictions_model_version", "model_name", "model_version"),
    )
