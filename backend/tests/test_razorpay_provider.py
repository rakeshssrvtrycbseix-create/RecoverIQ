import uuid

import httpx
import pytest

from app.core.config import Settings
from app.models import (
    RecoveryAction,
    RecoveryActionStatus,
    RecoveryActionType,
)
from app.providers.exceptions import (
    LiveActionsDisabledError,
    ProviderConfigurationError,
)
from app.providers.razorpay import (
    RazorpayActionProvider,
    generate_gateway_idempotency_key,
)


def create_test_action(
    action_type: str = RecoveryActionType.RETRY_PAYMENT.value,
    payload: dict | None = None,
) -> RecoveryAction:
    """Helper to provision a mock RecoveryAction in memory for provider testing."""
    case_id = uuid.uuid4()
    pol_id = uuid.uuid4()
    return RecoveryAction(
        id=uuid.uuid4(),
        recovery_case_id=case_id,
        policy_decision_id=pol_id,
        action_idempotency_key=f"act_{case_id}_{pol_id}_{action_type}",
        action_type=action_type,
        status=RecoveryActionStatus.SCHEDULED.value,
        action_payload=payload
        or {"subscription_id": "sub_test_12345", "amount": 199900},
    )


def test_deterministic_gateway_idempotency_key():
    """Test deterministic gateway idempotency key generation."""
    action1 = create_test_action()
    key1 = generate_gateway_idempotency_key(action1)
    key2 = generate_gateway_idempotency_key(action1)

    assert key1 == f"recoveriq_{action1.id}"
    assert key1 == key2

    action2 = create_test_action()
    key_other = generate_gateway_idempotency_key(action2)
    assert key1 != key_other


def test_missing_credentials_raises_configuration_error():
    """Test missing key_id or key_secret raises ProviderConfigurationError."""
    settings = Settings(
        database_url="sqlite:///:memory:",
        razorpay_key_id="",
        razorpay_key_secret="",
        allow_live_financial_actions=True,
    )
    with pytest.raises(ProviderConfigurationError, match="unconfigured or empty"):
        RazorpayActionProvider(settings=settings)


def test_live_execution_disabled_by_default_raises_error():
    """Test executing when allow_live_financial_actions is False raises error."""
    settings = Settings(
        database_url="sqlite:///:memory:",
        razorpay_key_id="rzp_test_key123",
        razorpay_key_secret="rzp_test_secret456",
        allow_live_financial_actions=False,  # Disabled
    )
    provider = RazorpayActionProvider(settings=settings)
    action = create_test_action()

    with pytest.raises(
        LiveActionsDisabledError, match="Live financial operations are disabled"
    ):
        provider.execute(action)


def test_successful_payment_retry_execution():
    """Test successful payment retry API response."""
    action = create_test_action(action_type=RecoveryActionType.RETRY_PAYMENT.value)

    def mock_handler(request: httpx.Request) -> httpx.Response:
        assert request.method == "POST"
        assert "/subscriptions/sub_test_12345/charge" in str(request.url)
        assert request.headers.get("X-Razorpay-Idempotency") == f"recoveriq_{action.id}"
        return httpx.Response(
            200, json={"id": "pay_test_success_123", "status": "captured"}
        )

    transport = httpx.MockTransport(mock_handler)
    client = httpx.Client(transport=transport, base_url="https://api.razorpay.com/v1")

    settings = Settings(
        database_url="sqlite:///:memory:",
        razorpay_key_id="rzp_test_key123",
        razorpay_key_secret="rzp_test_secret456",
        allow_live_financial_actions=True,
    )
    provider = RazorpayActionProvider(settings=settings, client=client)

    result = provider.execute(action)
    assert result.success is True
    assert result.execution_status == "SUCCESS"
    assert result.provider_reference_id == "pay_test_success_123"
    assert result.provider_status_code == "200"


def test_successful_payment_link_execution():
    """Test successful payment link creation API response."""
    action = create_test_action(action_type=RecoveryActionType.SEND_PAYMENT_LINK.value)

    def mock_handler(request: httpx.Request) -> httpx.Response:
        assert request.method == "POST"
        assert "/payment_links" in str(request.url)
        return httpx.Response(
            200, json={"id": "plink_test_123", "short_url": "https://rzp.io/i/123"}
        )

    transport = httpx.MockTransport(mock_handler)
    client = httpx.Client(transport=transport, base_url="https://api.razorpay.com/v1")

    settings = Settings(
        database_url="sqlite:///:memory:",
        razorpay_key_id="rzp_test_key123",
        razorpay_key_secret="rzp_test_secret456",
        allow_live_financial_actions=True,
    )
    provider = RazorpayActionProvider(settings=settings, client=client)

    result = provider.execute(action)
    assert result.success is True
    assert result.execution_status == "SUCCESS"
    assert result.provider_reference_id == "plink_test_123"


def test_successful_halt_subscription_execution():
    """Test successful subscription cancellation API response."""
    action = create_test_action(action_type=RecoveryActionType.HALT_SUBSCRIPTION.value)

    def mock_handler(request: httpx.Request) -> httpx.Response:
        assert request.method == "POST"
        assert "/subscriptions/sub_test_12345/cancel" in str(request.url)
        return httpx.Response(200, json={"id": "sub_test_12345", "status": "cancelled"})

    transport = httpx.MockTransport(mock_handler)
    client = httpx.Client(transport=transport, base_url="https://api.razorpay.com/v1")

    settings = Settings(
        database_url="sqlite:///:memory:",
        razorpay_key_id="rzp_test_key123",
        razorpay_key_secret="rzp_test_secret456",
        allow_live_financial_actions=True,
    )
    provider = RazorpayActionProvider(settings=settings, client=client)

    result = provider.execute(action)
    assert result.success is True
    assert result.execution_status == "SUCCESS"


def test_unsupported_action_type_returns_safe_failure():
    """Test non-gateway action types return structured failure result."""
    action = create_test_action(action_type=RecoveryActionType.SEND_NOTIFICATION.value)

    settings = Settings(
        database_url="sqlite:///:memory:",
        razorpay_key_id="rzp_test_key123",
        razorpay_key_secret="rzp_test_secret456",
        allow_live_financial_actions=True,
    )
    provider = RazorpayActionProvider(settings=settings)

    result = provider.execute(action)
    assert result.success is False
    assert result.execution_status == "FAILED"
    assert result.failure_reason == "UNSUPPORTED_GATEWAY_ACTION"


def test_gateway_timeout_handling():
    """Test request timeout is converted to structured failed ProviderResult."""
    action = create_test_action()

    def mock_handler(request: httpx.Request) -> httpx.Response:
        raise httpx.TimeoutException("Connection timed out after 10.0s")

    transport = httpx.MockTransport(mock_handler)
    client = httpx.Client(transport=transport, base_url="https://api.razorpay.com/v1")

    settings = Settings(
        database_url="sqlite:///:memory:",
        razorpay_key_id="rzp_test_key123",
        razorpay_key_secret="rzp_test_secret456",
        allow_live_financial_actions=True,
    )
    provider = RazorpayActionProvider(settings=settings, client=client)

    result = provider.execute(action)
    assert result.success is False
    assert result.execution_status == "TIMED_OUT"
    assert result.failure_reason == "GATEWAY_TIMEOUT"
    assert result.provider_status_code == "408"


def test_gateway_connection_failure_handling():
    """Test connection error is converted to structured failed ProviderResult."""
    action = create_test_action()

    def mock_handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("Connection refused")

    transport = httpx.MockTransport(mock_handler)
    client = httpx.Client(transport=transport, base_url="https://api.razorpay.com/v1")

    settings = Settings(
        database_url="sqlite:///:memory:",
        razorpay_key_id="rzp_test_key123",
        razorpay_key_secret="rzp_test_secret456",
        allow_live_financial_actions=True,
    )
    provider = RazorpayActionProvider(settings=settings, client=client)

    result = provider.execute(action)
    assert result.success is False
    assert result.execution_status == "FAILED"
    assert result.failure_reason == "GATEWAY_NETWORK_ERROR"
    assert result.provider_status_code == "503"


def test_gateway_http_4xx_client_error_handling():
    """Test HTTP 400 Bad Request is captured in ProviderResult."""
    action = create_test_action()

    def mock_handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            400,
            json={
                "error": {
                    "code": "BAD_REQUEST_ERROR",
                    "description": "Card has expired",
                }
            },
        )

    transport = httpx.MockTransport(mock_handler)
    client = httpx.Client(transport=transport, base_url="https://api.razorpay.com/v1")

    settings = Settings(
        database_url="sqlite:///:memory:",
        razorpay_key_id="rzp_test_key123",
        razorpay_key_secret="rzp_test_secret456",
        allow_live_financial_actions=True,
    )
    provider = RazorpayActionProvider(settings=settings, client=client)

    result = provider.execute(action)
    assert result.success is False
    assert result.execution_status == "FAILED"
    assert result.failure_reason == "BAD_REQUEST_ERROR"
    assert "Card has expired" in (result.error_details or "")


def test_gateway_http_5xx_server_error_handling():
    """Test HTTP 500 Internal Error is captured in ProviderResult."""
    action = create_test_action()

    def mock_handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            500,
            json={
                "error": {
                    "code": "GATEWAY_ERROR",
                    "description": "Downstream bank gateway unavailable",
                }
            },
        )

    transport = httpx.MockTransport(mock_handler)
    client = httpx.Client(transport=transport, base_url="https://api.razorpay.com/v1")

    settings = Settings(
        database_url="sqlite:///:memory:",
        razorpay_key_id="rzp_test_key123",
        razorpay_key_secret="rzp_test_secret456",
        allow_live_financial_actions=True,
    )
    provider = RazorpayActionProvider(settings=settings, client=client)

    result = provider.execute(action)
    assert result.success is False
    assert result.execution_status == "FAILED"
    assert result.provider_status_code == "500"


def test_credentials_never_appear_in_provider_result():
    """Security test: Secrets and API keys in response are redacted from telemetry."""
    action = create_test_action()

    def mock_handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "id": "pay_test_123",
                "api_key": "rzp_live_secretkey999",
                "auth_token": "secret_token_abc",
                "status": "authorized",
            },
        )

    transport = httpx.MockTransport(mock_handler)
    client = httpx.Client(transport=transport, base_url="https://api.razorpay.com/v1")

    settings = Settings(
        database_url="sqlite:///:memory:",
        razorpay_key_id="rzp_test_key123",
        razorpay_key_secret="rzp_test_secret456",
        allow_live_financial_actions=True,
    )
    provider = RazorpayActionProvider(settings=settings, client=client)

    result = provider.execute(action)
    assert result.success is True
    # Verify redacted
    summary = result.response_payload_summary
    assert summary.get("api_key") == "[REDACTED]"
    assert summary.get("auth_token") == "[REDACTED]"
