class ProviderError(Exception):
    """Base exception for all external provider errors."""


class ProviderConfigurationError(ProviderError):
    """Raised when provider configuration or credentials are missing/invalid."""


class LiveActionsDisabledError(ProviderError):
    """Raised when attempting live execution while live actions are disabled."""


class ProviderNetworkError(ProviderError):
    """Raised when a network transport failure occurs communicating with provider."""


class ProviderTimeoutError(ProviderError):
    """Raised when an external provider request times out."""


class ProviderAPIError(ProviderError):
    """Raised when the external provider returns an error HTTP status code."""


class ProviderAuthenticationError(ProviderError):
    """Raised when provider rejects authentication credentials."""


class UnsupportedActionTypeError(ProviderError):
    """Raised when an action type is not supported by the designated provider."""
