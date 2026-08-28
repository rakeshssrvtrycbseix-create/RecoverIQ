import re
from datetime import UTC, datetime
from typing import Any

from app.models.enums import RecoveryActionType
from app.models.recovery_action import RecoveryAction
from app.providers.base import ProviderResult

FORBIDDEN_SENSITIVE_KEYS = {
    "email",
    "phone",
    "contact",
    "card_number",
    "pan",
    "cvv",
    "cvc",
    "pin",
    "password",
    "secret",
    "token",
    "api_key",
    "secret_key",
    "private_key",
    "auth_token",
    "access_token",
    "webhook_secret",
    "razorpay_key",
    "razorpay_secret",
    "bearer",
}

EMAIL_REGEX = re.compile(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+")
CARD_REGEX = re.compile(r"\b(?:\d[ -]*?){13,19}\b")
SECRET_TOKEN_REGEX = re.compile(
    r"(?:sk_live_|sk_test_|rzp_live_|rzp_test_|Bearer\s+|eyJh)[A-Za-z0-9_\-\.]{8,}"
)


class MockProviderSecurityError(Exception):
    """Raised when mock provider detects sensitive or secret payload data."""


def _validate_mock_payload_safety(data: Any) -> None:
    """Recursively check payload for sensitive data or forbidden keys."""
    if isinstance(data, dict):
        for k, v in data.items():
            k_lower = str(k).lower()
            if k_lower in FORBIDDEN_SENSITIVE_KEYS or "secret" in k_lower:
                raise MockProviderSecurityError(
                    f"Mock provider rejected sensitive payload key: '{k}'"
                )
            _validate_mock_payload_safety(v)
    elif isinstance(data, list | tuple | set):
        for item in data:
            _validate_mock_payload_safety(item)
    elif isinstance(data, str):
        if EMAIL_REGEX.search(data):
            raise MockProviderSecurityError(
                "Mock provider rejected payload containing email address"
            )
        digits = re.sub(r"\D", "", data)
        if len(digits) >= 13 and CARD_REGEX.search(data):
            raise MockProviderSecurityError(
                "Mock provider rejected payload containing card number"
            )
        if SECRET_TOKEN_REGEX.search(data):
            raise MockProviderSecurityError(
                "Mock provider rejected payload containing secret token"
            )


class MockActionProvider:
    """
    Deterministic mock action provider for development, testing, and CI/CD.

    Guarantees:
    - Zero network calls or external APIs.
    - Strictly deterministic outputs with no randomness.
    - Configurable failure hooks for regression testing.
    """

    def __init__(
        self,
        force_failure: bool = False,
        force_exception: bool = False,
        failure_reason: str = "SIMULATED_PROVIDER_FAILURE",
        error_details: str = "Simulated provider error for testing",
    ) -> None:
        self.force_failure = force_failure
        self.force_exception = force_exception
        self.failure_reason = failure_reason
        self.error_details = error_details

    def execute(
        self,
        action: RecoveryAction,
        context: dict[str, Any] | None = None,
    ) -> ProviderResult:
        """Execute simulated recovery action with full safety verification."""
        if self.force_exception:
            raise RuntimeError(
                "Simulated unhandled provider network/system crash"
            )

        # Safety validation: Reject sensitive payload data
        if action.action_payload:
            _validate_mock_payload_safety(action.action_payload)

        now_utc = datetime.now(UTC)
        ref_id = f"mock_{action.id}"

        # Configurable failure simulation
        if self.force_failure:
            return ProviderResult(
                success=False,
                execution_status="FAILED",
                provider_reference_id=ref_id,
                provider_status_code="500",
                failure_reason=self.failure_reason,
                error_details=self.error_details,
                response_payload_summary={
                    "mock_executed": True,
                    "simulated_error": True,
                    "action_type": action.action_type,
                },
                executed_at=now_utc,
            )

        # Standard deterministic success simulation
        action_type = str(action.action_type)
        channel = (
            action.action_payload.get("channel", "SIMULATED_CHANNEL")
            if isinstance(action.action_payload, dict)
            else "SIMULATED_CHANNEL"
        )

        response_summary: dict[str, Any] = {
            "mock_executed": True,
            "channel": channel,
            "action_type": action_type,
        }

        if action_type == RecoveryActionType.RETRY_PAYMENT.value:
            response_summary["simulated_gateway_response"] = "PAYMENT_INITIATED"
        elif action_type == RecoveryActionType.SEND_PAYMENT_LINK.value:
            response_summary["simulated_link_id"] = f"plink_mock_{action.id.hex[:8]}"
        elif action_type == RecoveryActionType.SEND_NOTIFICATION.value:
            response_summary["simulated_message_id"] = f"msg_mock_{action.id.hex[:8]}"
        elif action_type == RecoveryActionType.ESCALATE_HUMAN.value:
            response_summary["simulated_ticket_id"] = f"tkt_mock_{action.id.hex[:8]}"
        elif action_type == RecoveryActionType.HALT_SUBSCRIPTION.value:
            response_summary["simulated_sub_status"] = "HALTED"

        return ProviderResult(
            success=True,
            execution_status="SUCCESS",
            provider_reference_id=ref_id,
            provider_status_code="200",
            failure_reason=None,
            error_details=None,
            response_payload_summary=response_summary,
            executed_at=now_utc,
        )


mock_action_provider = MockActionProvider()
