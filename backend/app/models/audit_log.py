import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import (
    BigInteger,
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

if TYPE_CHECKING:
    from app.models.recovery_case import RecoveryCase

JSON_TYPE = JSONB().with_variant(JSON, "sqlite")
BIGINT_TYPE = BigInteger().with_variant(Integer, "sqlite")


class AuditLog(Base):
    """Global, immutable append-only audit trail logging all state changes."""

    __tablename__ = "audit_logs"

    id: Mapped[int] = mapped_column(
        BIGINT_TYPE,
        primary_key=True,
        autoincrement=True,
    )
    event_type: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
    )
    actor_type: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
    )
    actor_id: Mapped[str] = mapped_column(
        String(128),
        nullable=False,
    )
    recovery_case_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("recovery_cases.id", ondelete="SET NULL"),
        nullable=True,
    )
    entity_type: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
    )
    entity_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        nullable=True,
    )
    action: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
    )
    previous_state: Mapped[dict[str, Any] | None] = mapped_column(
        JSON_TYPE,
        nullable=True,
    )
    new_state: Mapped[dict[str, Any] | None] = mapped_column(
        JSON_TYPE,
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

    # Relationships
    recovery_case: Mapped["RecoveryCase | None"] = relationship(
        "RecoveryCase",
        back_populates="audit_logs",
    )

    __table_args__ = (
        Index("idx_audit_logs_case_id", "recovery_case_id"),
        Index("idx_audit_logs_entity", "entity_type", "entity_id"),
        Index("idx_audit_logs_event_type", "event_type"),
        Index("idx_audit_logs_created_at", "created_at"),
    )
