class PolicyEngineError(Exception):
    """Base exception for all Policy Engine validation errors."""


class AgentDecisionNotFoundError(PolicyEngineError):
    """Raised when the specified AgentDecision is not found."""


class RecoveryCaseNotFoundError(PolicyEngineError):
    """Raised when the associated RecoveryCase or required aggregate is missing."""


class PolicyPersistenceError(PolicyEngineError):
    """Raised when saving PolicyDecision or AuditLog to database fails."""
