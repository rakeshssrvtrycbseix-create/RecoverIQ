class AgentDecisionError(Exception):
    """Base exception for all AI Recovery Decision Engine errors."""


class RecoveryCaseNotFoundError(AgentDecisionError):
    """Raised when the specified RecoveryCase is not found."""


class InvalidAIOutputError(AgentDecisionError):
    """Raised when the AI output is malformed or violates schema constraints."""


class UnsafeAIOutputError(AgentDecisionError):
    """
    Raised when the AI output contains forbidden PII, secrets, or
    illegal operations.
    """


class AIProviderError(AgentDecisionError):
    """Raised when the underlying AI provider fails to generate a response."""


class DecisionPersistenceError(AgentDecisionError):
    """Raised when persisting the AgentDecision or AuditLog to database fails."""
