from enum import StrEnum


class CustomerRiskTier(StrEnum):
    """Customer risk tiers."""

    LOW = "LOW"
    STANDARD = "STANDARD"
    HIGH = "HIGH"
    BLOCKED = "BLOCKED"


class SubscriptionStatus(StrEnum):
    """Subscription lifecycle states."""

    ACTIVE = "ACTIVE"
    AUTHENTICATED = "AUTHENTICATED"
    PAST_DUE = "PAST_DUE"
    HALTED = "HALTED"
    CANCELLED = "CANCELLED"
    COMPLETED = "COMPLETED"


class BillingCadence(StrEnum):
    """Subscription billing cadences."""

    MONTHLY = "MONTHLY"
    QUARTERLY = "QUARTERLY"
    YEARLY = "YEARLY"


class PaymentStatus(StrEnum):
    """High-level payment transaction states."""

    CREATED = "CREATED"
    AUTHORIZED = "AUTHORIZED"
    CAPTURED = "CAPTURED"
    FAILED = "FAILED"
    REFUNDED = "REFUNDED"
    DISPUTED = "DISPUTED"


class PaymentAttemptStatus(StrEnum):
    """Granular payment attempt transaction states."""

    INITIATED = "INITIATED"
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"
    PENDING = "PENDING"


class PaymentMethod(StrEnum):
    """Supported payment methods."""

    CARD = "CARD"
    UPI = "UPI"
    NETBANKING = "NETBANKING"
    WALLET = "WALLET"
    EMI = "EMI"


class PaymentEventSource(StrEnum):
    """Payment event origin source."""

    RAZORPAY_WEBHOOK = "RAZORPAY_WEBHOOK"
    POLLING_JOB = "POLLING_JOB"
    INTERNAL_AGENT = "INTERNAL_AGENT"


class PaymentEventProcessingStatus(StrEnum):
    """Processing state of ingested payment events."""

    RECEIVED = "RECEIVED"
    PROCESSED = "PROCESSED"
    IGNORED = "IGNORED"
    FAILED = "FAILED"


class RecoveryCaseStatus(StrEnum):
    """Recovery case operational states."""

    OPEN = "OPEN"
    ANALYZING = "ANALYZING"
    ACTION_PENDING = "ACTION_PENDING"
    IN_RECOVERY = "IN_RECOVERY"
    RECOVERED = "RECOVERED"
    EXHAUSTED = "EXHAUSTED"
    ESCALATED_HUMAN = "ESCALATED_HUMAN"
    CLOSED = "CLOSED"


class RecoveryStage(StrEnum):
    """Workflow phase of active recovery."""

    INITIAL_FAILURE = "INITIAL_FAILURE"
    SMART_RETRY = "SMART_RETRY"
    COMMUNICATION = "COMMUNICATION"
    ESCALATION = "ESCALATION"


class RecoveryCaseClosedReason(StrEnum):
    """Reason for closing a recovery case."""

    PAYMENT_RECOVERED = "PAYMENT_RECOVERED"
    MAX_ATTEMPTS_EXCEEDED = "MAX_ATTEMPTS_EXCEEDED"
    MANUALLY_OVERRIDDEN = "MANUALLY_OVERRIDDEN"
    CUSTOMER_CANCELLED = "CUSTOMER_CANCELLED"


class PolicyEvaluationResult(StrEnum):
    """Deterministic policy validation outcomes."""

    ALLOWED = "ALLOWED"
    BLOCKED = "BLOCKED"
    HUMAN_REVIEW = "HUMAN_REVIEW"


class RecoveryActionType(StrEnum):
    """Operational recovery action categories."""

    RETRY_PAYMENT = "RETRY_PAYMENT"
    SEND_PAYMENT_LINK = "SEND_PAYMENT_LINK"
    SEND_NOTIFICATION = "SEND_NOTIFICATION"
    ESCALATE_HUMAN = "ESCALATE_HUMAN"
    HALT_SUBSCRIPTION = "HALT_SUBSCRIPTION"
    CLOSE_CASE = "CLOSE_CASE"


class RecoveryActionStatus(StrEnum):
    """Lifecycle state of an authorized recovery action."""

    PENDING = "PENDING"
    SCHEDULED = "SCHEDULED"
    EXECUTING = "EXECUTING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


class ActionResultExecutionStatus(StrEnum):
    """Provider execution outcome."""

    SUCCESS = "SUCCESS"
    FAILED = "FAILED"
    TIMED_OUT = "TIMED_OUT"
    RATE_LIMITED = "RATE_LIMITED"


class AuditActorType(StrEnum):
    """Actor initiating an audited operation."""

    SYSTEM_EVENT = "SYSTEM_EVENT"
    AI_AGENT = "AI_AGENT"
    POLICY_ENGINE = "POLICY_ENGINE"
    ACTION_EXECUTOR = "ACTION_EXECUTOR"
    HUMAN_ADMIN = "HUMAN_ADMIN"
