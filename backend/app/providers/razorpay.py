import json
import logging
from datetime import UTC, datetime
from typing import Any

import httpx

from app.core.config import Settings, get_settings
from app.models.enums import RecoveryActionType
from app.models.recovery_action import RecoveryAction
from app.providers.base import ProviderResult
from app.providers.exceptions import (
    LiveActionsDisabledError,
    ProviderConfigurationError,
)

logger = logging.getLogger(__name__)


def generate_gateway_idempotency_key(action: RecoveryAction) -> str:
    """
    Generate deterministic, unique Razorpay gateway idempotency key.

    Invariant: The same RecoveryAction will ALWAYS produce the exact same key.
    """
    return f"recoveriq_{action.id}"


def _sanitize_response_data(data: Any) -> Any:
    """Recursively scrub sensitive credential tokens and keys from response payloads."""
    if isinstance(data, dict):
        sanitized = {}
        for k, v in data.items():
            k_lower = str(k).lower()
            if any(
                secret in k_lower
                for secret in ["secret", "key", "token", "auth", "password", "cvv", "pin"]
            ):
                sanitized[k] = "[REDACTED]"
            else:
                sanitized[k] = _sanitize_response_data(v)
        return sanitized
    elif isinstance(data, list):
        return [_sanitize_response_data(item) for item in data]
    return data


class RazorpayActionProvider:
    """
    Production-grade Razorpay Action Provider implementing payment retries,
    payment links, and subscription operations via official Razorpay APIs.

    Guarantees:
    - Never logs credentials, secrets, or authorization headers.
    - Uses deterministic gateway idempotency keys for every request.
    - Requires explicit live action enablement (ALLOW_LIVE_FINANCIAL_ACTIONS=True).
    - Fails safely on timeouts, HTTP errors, and network disconnects.
    """

    def __init__(
        self,
        settings: Settings | None = None,
        client: httpx.Client | None = None,
    ) -> None:
        self.settings = settings or get_settings()
        self._custom_client = client

        # Validate Credentials
        if not self.settings.razorpay_key_id or not self.settings.razorpay_key_secret:
            raise ProviderConfigurationError(
                "Razorpay key_id or key_secret is unconfigured or empty."
            )

    def _get_client(self) -> httpx.Client:
        """Create or return HTTP client configured with timeouts and base URL."""
        if self._custom_client:
            return self._custom_client
        return httpx.Client(
            base_url=self.settings.razorpay_base_url,
            timeout=self.settings.razorpay_timeout_seconds,
            auth=(self.settings.razorpay_key_id, self.settings.razorpay_key_secret),
        )

    def execute(
        self,
        action: RecoveryAction,
        context: dict[str, Any] | None = None,
    ) -> ProviderResult:
        """Execute a scheduled recovery action against Razorpay APIs."""
        # Governance Guard: Prevent accidental live transactions
        if not self.settings.allow_live_financial_actions:
            raise LiveActionsDisabledError(
                "Live financial operations are disabled in application settings. "
                "Set ALLOW_LIVE_FINANCIAL_ACTIONS=True to permit execution."
            )

        action_type = str(action.action_type)
        now_utc = datetime.now(UTC)
        idempotency_key = generate_gateway_idempotency_key(action)

        # Route to appropriate gateway operation
        if action_type == RecoveryActionType.RETRY_PAYMENT.value:
            return self._execute_payment_retry(action, idempotency_key, now_utc)
        elif action_type == RecoveryActionType.SEND_PAYMENT_LINK.value:
            return self._execute_payment_link(action, idempotency_key, now_utc)
        elif action_type == RecoveryActionType.HALT_SUBSCRIPTION.value:
            return self._execute_halt_subscription(action, idempotency_key, now_utc)
        else:
            logger.warning(
                "unsupported_razorpay_action_type",
                extra={"action_type": action_type, "action_id": str(action.id)},
            )
            return ProviderResult(
                success=False,
                execution_status="FAILED",
                provider_reference_id=idempotency_key,
                provider_status_code="400",
                failure_reason="UNSUPPORTED_GATEWAY_ACTION",
                error_details=(
                    f"Action type '{action_type}' cannot be executed directly "
                    "via the Razorpay payment gateway."
                ),
                response_payload_summary={"action_type": action_type},
                executed_at=now_utc,
            )

    def _execute_payment_retry(
        self,
        action: RecoveryAction,
        idempotency_key: str,
        now_utc: datetime,
    ) -> ProviderResult:
        """Execute a payment retry or invoice charge via Razorpay API."""
        payload = action.action_payload or {}
        sub_id = payload.get("subscription_id") or payload.get("razorpay_subscription_id")

        endpoint = (
            f"/subscriptions/{sub_id}/charge"
            if sub_id
            else "/orders"
        )
        body = {
            "amount": payload.get("amount", 100),
            "currency": payload.get("currency", "INR"),
            "notes": {
                "recoveriq_action_id": str(action.id),
                "recoveriq_case_id": str(action.recovery_case_id),
            },
        }
        headers = {"X-Razorpay-Idempotency": idempotency_key}

        return self._send_request("POST", endpoint, body, headers, idempotency_key, now_utc)

    def _execute_payment_link(
        self,
        action: RecoveryAction,
        idempotency_key: str,
        now_utc: datetime,
    ) -> ProviderResult:
        """Create a payment link for customer payment method update."""
        payload = action.action_payload or {}
        body = {
            "amount": payload.get("amount", 100),
            "currency": payload.get("currency", "INR"),
            "reference_id": idempotency_key,
            "description": "Subscription payment recovery link",
            "notes": {
                "recoveriq_action_id": str(action.id),
            },
        }
        headers = {"X-Razorpay-Idempotency": idempotency_key}
        return self._send_request(
            "POST", "/payment_links", body, headers, idempotency_key, now_utc
        )

    def _execute_halt_subscription(
        self,
        action: RecoveryAction,
        idempotency_key: str,
        now_utc: datetime,
    ) -> ProviderResult:
        """Cancel/halt a subscription in Razorpay."""
        payload = action.action_payload or {}
        sub_id = payload.get("subscription_id") or payload.get("razorpay_subscription_id")
        endpoint = f"/subscriptions/{sub_id}/cancel" if sub_id else "/subscriptions/halt"
        body = {"cancel_at_cycle_end": False}
        headers = {"X-Razorpay-Idempotency": idempotency_key}
        return self._send_request(
            "POST", endpoint, body, headers, idempotency_key, now_utc
        )

    def _send_request(
        self,
        method: str,
        endpoint: str,
        json_body: dict[str, Any],
        headers: dict[str, str],
        idempotency_key: str,
        now_utc: datetime,
    ) -> ProviderResult:
        """Send HTTP request with comprehensive timeout and error handling."""
        try:
            with self._get_client() as client:
                resp = client.request(
                    method=method,
                    url=endpoint,
                    json=json_body,
                    headers=headers,
                )

            # Try parsing response JSON safely
            try:
                resp_json = resp.json()
            except Exception:
                resp_json = {"raw_text": resp.text[:200]}

            sanitized_resp = _sanitize_response_data(resp_json)

            if 200 <= resp.status_code < 300:
                ref_id = resp_json.get("id") or idempotency_key
                return ProviderResult(
                    success=True,
                    execution_status="SUCCESS",
                    provider_reference_id=str(ref_id),
                    provider_status_code=str(resp.status_code),
                    failure_reason=None,
                    error_details=None,
                    response_payload_summary=sanitized_resp,
                    executed_at=now_utc,
                )
            else:
                err_dict = resp_json.get("error", {}) if isinstance(resp_json, dict) else {}
                err_reason = err_dict.get("code") or f"HTTP_{resp.status_code}"
                err_desc = err_dict.get("description") or resp.text[:250]

                return ProviderResult(
                    success=False,
                    execution_status="FAILED",
                    provider_reference_id=idempotency_key,
                    provider_status_code=str(resp.status_code),
                    failure_reason=str(err_reason),
                    error_details=str(err_desc),
                    response_payload_summary=sanitized_resp,
                    executed_at=now_utc,
                )

        except httpx.TimeoutException:
            logger.error("razorpay_request_timeout", extra={"idempotency_key": idempotency_key})
            return ProviderResult(
                success=False,
                execution_status="FAILED",
                provider_reference_id=idempotency_key,
                provider_status_code="408",
                failure_reason="GATEWAY_TIMEOUT",
                error_details="Request to Razorpay API timed out after configured duration.",
                response_payload_summary={"timeout": True},
                executed_at=now_utc,
            )

        except (httpx.ConnectError, httpx.NetworkError) as exc:
            logger.error("razorpay_network_error", extra={"idempotency_key": idempotency_key})
            return ProviderResult(
                success=False,
                execution_status="FAILED",
                provider_reference_id=idempotency_key,
                provider_status_code="503",
                failure_reason="GATEWAY_NETWORK_ERROR",
                error_details=f"Failed to establish connection to Razorpay: {exc}",
                response_payload_summary={"network_error": True},
                executed_at=now_utc,
            )

        except Exception as exc:
            logger.error(
                "razorpay_unexpected_provider_error",
                extra={"idempotency_key": idempotency_key, "error": str(exc)},
            )
            return ProviderResult(
                success=False,
                execution_status="FAILED",
                provider_reference_id=idempotency_key,
                provider_status_code="500",
                failure_reason="GATEWAY_INTERNAL_ERROR",
                error_details=f"Unexpected error during Razorpay execution: {exc}",
                response_payload_summary={"unexpected_error": True},
                executed_at=now_utc,
            )

    def reconcile_action(self, action: RecoveryAction) -> ProviderResult:
        """
        Query external gateway status for an ambiguous or stale action.
        """
        now_utc = datetime.now(UTC)
        idempotency_key = generate_gateway_idempotency_key(action)

        try:
            with self._get_client() as client:
                # Query payment links or payments endpoint
                resp = client.get(
                    f"/payment_links?reference_id={idempotency_key}"
                )

            if resp.status_code == 200:
                data = resp.json()
                items = data.get("payment_links", []) if isinstance(data, dict) else []
                if items:
                    latest = items[0]
                    status = str(latest.get("status", "")).lower()
                    if status in {"paid", "captured"}:
                        return ProviderResult(
                            success=True,
                            execution_status="SUCCESS",
                            provider_reference_id=latest.get("id", idempotency_key),
                            provider_status_code="200",
                            response_payload_summary=_sanitize_response_data(latest),
                            executed_at=now_utc,
                        )
                    elif status in {"cancelled", "expired"}:
                        return ProviderResult(
                            success=False,
                            execution_status="FAILED",
                            provider_reference_id=latest.get("id", idempotency_key),
                            provider_status_code="200",
                            failure_reason=f"GATEWAY_STATUS_{status.upper()}",
                            response_payload_summary=_sanitize_response_data(latest),
                            executed_at=now_utc,
                        )

            return ProviderResult(
                success=False,
                execution_status="UNKNOWN",
                provider_reference_id=idempotency_key,
                provider_status_code=str(resp.status_code),
                failure_reason="RECONCILIATION_INCONCLUSIVE",
                error_details="External gateway query returned no conclusive status.",
                response_payload_summary={},
                executed_at=now_utc,
            )

        except Exception as exc:
            return ProviderResult(
                success=False,
                execution_status="UNKNOWN",
                provider_reference_id=idempotency_key,
                provider_status_code="500",
                failure_reason="RECONCILIATION_ERROR",
                error_details=str(exc),
                response_payload_summary={},
                executed_at=now_utc,
            )
