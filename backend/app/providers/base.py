from datetime import UTC, datetime
from typing import Any, Protocol

from pydantic import BaseModel, ConfigDict, Field

from app.models.recovery_action import RecoveryAction


class ProviderResult(BaseModel):
    """Normalized outcome returned from action providers."""

    model_config = ConfigDict(frozen=True)

    success: bool = Field(
        description="Whether the provider operation succeeded",
    )
    execution_status: str = Field(
        description="Execution status string (SUCCESS or FAILED)",
    )
    provider_reference_id: str | None = Field(
        default=None,
        description="External reference identifier returned by provider",
    )
    provider_status_code: str | None = Field(
        default=None,
        description="Raw or normalized HTTP/API status code from provider",
    )
    failure_reason: str | None = Field(
        default=None,
        description="Standardized error category if execution failed",
    )
    error_details: str | None = Field(
        default=None,
        description="Detailed diagnostic or error trace information",
    )
    response_payload_summary: dict[str, Any] = Field(
        default_factory=dict,
        description="Redacted, safe response telemetry payload",
    )
    executed_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="UTC timestamp when provider execution took place",
    )


class ActionProvider(Protocol):
    """Protocol interface for external communication and payment execution providers."""

    def execute(
        self,
        action: RecoveryAction,
        context: dict[str, Any] | None = None,
    ) -> ProviderResult:
        """Execute the given recovery action deterministically."""
        ...
