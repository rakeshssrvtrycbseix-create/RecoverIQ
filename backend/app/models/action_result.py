import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import DateTime, ForeignKey, Index, String, Text, Uuid, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import JSON

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.recovery_action import RecoveryAction

JSON_TYPE = JSONB().with_variant(JSON, "sqlite")


class ActionResult(Base):
    """Execution telemetry and outcome returned by external providers."""

    __tablename__ = "action_results"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    recovery_action_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("recovery_actions.id", ondelete="CASCADE"),
        nullable=False,
    )
    execution_status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
    )
    provider_reference_id: Mapped[str | None] = mapped_column(
        String(128),
        nullable=True,
    )
    provider_status_code: Mapped[str | None] = mapped_column(
        String(64),
        nullable=True,
    )
    failure_reason: Mapped[str | None] = mapped_column(
        String(128),
        nullable=True,
    )
    error_details: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )
    response_payload_summary: Mapped[dict[str, Any] | None] = mapped_column(
        JSON_TYPE,
        nullable=True,
    )
    executed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    # Relationships
    recovery_action: Mapped["RecoveryAction"] = relationship(
        "RecoveryAction",
        back_populates="results",
    )

    __table_args__ = (
        Index("idx_action_results_action_id", "recovery_action_id"),
        Index("idx_action_results_provider_ref", "provider_reference_id"),
        Index("idx_action_results_status", "execution_status"),
    )
