import pytest

from app.core.config import Settings
from app.providers.exceptions import (
    LiveActionsDisabledError,
    ProviderConfigurationError,
)
from app.providers.factory import ProviderFactory
from app.providers.mock import MockActionProvider
from app.providers.razorpay import RazorpayActionProvider


def test_default_settings_returns_mock_provider():
    """Test default settings resolve to MockActionProvider."""
    settings = Settings(
        database_url="sqlite:///:memory:",
        recovery_provider="mock",
    )
    provider = ProviderFactory.get_provider(settings=settings)
    assert isinstance(provider, MockActionProvider)


def test_razorpay_provider_resolution_when_enabled():
    """Test Razorpay provider resolves when configured and live actions enabled."""
    settings = Settings(
        database_url="sqlite:///:memory:",
        recovery_provider="razorpay",
        razorpay_key_id="rzp_test_123",
        razorpay_key_secret="rzp_sec_456",
        allow_live_financial_actions=True,
    )
    provider = ProviderFactory.get_provider(settings=settings)
    assert isinstance(provider, RazorpayActionProvider)


def test_razorpay_without_live_flag_raises_error():
    """Test Razorpay provider raises LiveActionsDisabledError if flag is False."""
    settings = Settings(
        database_url="sqlite:///:memory:",
        recovery_provider="razorpay",
        razorpay_key_id="rzp_test_123",
        razorpay_key_secret="rzp_sec_456",
        allow_live_financial_actions=False,  # Disabled
    )
    with pytest.raises(
        LiveActionsDisabledError, match="Live financial operations are disabled"
    ):
        ProviderFactory.get_provider(settings=settings)


def test_razorpay_missing_credentials_raises_error():
    """Test Razorpay provider raises ProviderConfigurationError if keys are missing."""
    settings = Settings(
        database_url="sqlite:///:memory:",
        recovery_provider="razorpay",
        razorpay_key_id="",
        razorpay_key_secret="",
        allow_live_financial_actions=True,
    )
    with pytest.raises(ProviderConfigurationError, match="missing or empty"):
        ProviderFactory.get_provider(settings=settings)


def test_unknown_provider_raises_error():
    """Test unsupported provider names fail closed."""
    settings = Settings(
        database_url="sqlite:///:memory:",
        recovery_provider="stripe_unsupported",
    )
    with pytest.raises(ProviderConfigurationError, match="Unknown or unsupported"):
        ProviderFactory.get_provider(settings=settings)


def test_custom_mock_override():
    """Test providing a custom mock instance is preserved."""
    custom_mock = MockActionProvider(force_failure=True)
    settings = Settings(database_url="sqlite:///:memory:", recovery_provider="mock")

    provider = ProviderFactory.get_provider(settings=settings, custom_mock=custom_mock)
    assert provider is custom_mock
    assert provider.force_failure is True
