import logging

from app.core.config import Settings, get_settings
from app.providers.base import ActionProvider
from app.providers.exceptions import (
    LiveActionsDisabledError,
    ProviderConfigurationError,
)
from app.providers.mock import MockActionProvider, mock_action_provider
from app.providers.razorpay import RazorpayActionProvider

logger = logging.getLogger(__name__)


class ProviderFactory:
    """
    Factory for instantiating and configuring ActionProvider implementations.

    Guarantees:
    - Test / default environments automatically resolve to MockActionProvider.
    - Live Razorpay execution requires explicit configuration AND allow_live_financial_actions=True.
    - Fails closed with clean domain exceptions on invalid/unconfigured providers.
    """

    @staticmethod
    def get_provider(
        settings: Settings | None = None,
        custom_mock: MockActionProvider | None = None,
    ) -> ActionProvider:
        """Resolve and instantiate the appropriate ActionProvider based on settings."""
        s = settings or get_settings()
        provider_name = (s.recovery_provider or "mock").lower().strip()

        if provider_name == "mock":
            return custom_mock or mock_action_provider

        elif provider_name == "razorpay":
            # Safety Gate: Live actions must be explicitly enabled
            if not s.allow_live_financial_actions:
                raise LiveActionsDisabledError(
                    "Live financial operations are disabled in application settings. "
                    "Set ALLOW_LIVE_FINANCIAL_ACTIONS=True to enable Razorpay execution."
                )

            # Credential Validation
            if not s.razorpay_key_id or not s.razorpay_key_secret:
                raise ProviderConfigurationError(
                    "Razorpay key_id or key_secret is missing or empty."
                )

            return RazorpayActionProvider(settings=s)

        else:
            raise ProviderConfigurationError(
                f"Unknown or unsupported recovery_provider: '{s.recovery_provider}'. "
                "Must be one of ['mock', 'razorpay']."
            )
