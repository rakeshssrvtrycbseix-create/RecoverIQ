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


class StrategyRecommendationStatus(StrEnum):
    """Lifecycle state of governed strategy recommendations."""

    NO_RECOMMENDATION = "NO_RECOMMENDATION"
    OBSERVATIONAL = "OBSERVATIONAL"
    REVIEW_REQUIRED = "REVIEW_REQUIRED"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    EXPIRED = "EXPIRED"


class RecommendationReliability(StrEnum):
    """Reliability confidence tier of historical recommendation evidence."""

    SUFFICIENT = "SUFFICIENT"
    LIMITED = "LIMITED"
    INSUFFICIENT_DATA = "INSUFFICIENT_DATA"


class RecommendationAuditEventType(StrEnum):
    """Audit log event types for recommendation governance."""

    RECOMMENDATION_CREATED = "RECOMMENDATION_CREATED"
    RECOMMENDATION_APPROVED = "RECOMMENDATION_APPROVED"
    RECOMMENDATION_REJECTED = "RECOMMENDATION_REJECTED"
    RECOMMENDATION_EXPIRED = "RECOMMENDATION_EXPIRED"


class StrategyActivationStatus(StrEnum):
    """Lifecycle state of controlled strategy activations and production promotions."""

    DRAFT = "DRAFT"
    APPROVED = "APPROVED"
    CANARY = "CANARY"
    MONITORING = "MONITORING"
    PROMOTION_READY = "PROMOTION_READY"
    ACTIVE = "ACTIVE"
    PRODUCTION = "PRODUCTION"
    DEGRADED = "DEGRADED"
    PAUSED = "PAUSED"
    ROLLED_BACK = "ROLLED_BACK"
    EXPIRED = "EXPIRED"


class ActivationAuditEventType(StrEnum):
    """Audit log event types for controlled strategy activation and production promotion."""

    ACTIVATION_CREATED = "ACTIVATION_CREATED"
    ACTIVATION_APPROVED = "ACTIVATION_APPROVED"
    CANARY_STARTED = "CANARY_STARTED"
    ACTIVATION_PAUSED = "ACTIVATION_PAUSED"
    ACTIVATION_ROLLED_BACK = "ACTIVATION_ROLLED_BACK"
    ACTIVATION_PROMOTED = "ACTIVATION_PROMOTED"
    ACTIVATION_EXPIRED = "ACTIVATION_EXPIRED"
    PRODUCTION_PROMOTION_EVALUATED = "PRODUCTION_PROMOTION_EVALUATED"
    PRODUCTION_PROMOTION_APPROVED = "PRODUCTION_PROMOTION_APPROVED"
    PRODUCTION_PROMOTED = "PRODUCTION_PROMOTED"
    PRODUCTION_MONITORING_WARNING = "PRODUCTION_MONITORING_WARNING"
    PRODUCTION_ROLLBACK_RECOMMENDED = "PRODUCTION_ROLLBACK_RECOMMENDED"
    PRODUCTION_PAUSED = "PRODUCTION_PAUSED"
    PRODUCTION_ROLLED_BACK = "PRODUCTION_ROLLED_BACK"
    PRODUCTION_EXPIRED = "PRODUCTION_EXPIRED"


class RolloutHealthStatus(StrEnum):
    """Health safety status of an active strategy rollout/canary experiment."""

    SAFE = "SAFE"
    WARNING = "WARNING"
    ROLLBACK_RECOMMENDED = "ROLLBACK_RECOMMENDED"


class PromotionBlockerCode(StrEnum):
    """Deterministic blocker codes preventing production strategy promotion."""

    PROMOTION_BLOCKED_INSUFFICIENT_SAMPLE = "PROMOTION_BLOCKED_INSUFFICIENT_SAMPLE"
    PROMOTION_BLOCKED_NO_UPLIFT = "PROMOTION_BLOCKED_NO_UPLIFT"
    PROMOTION_BLOCKED_LOW_EFFECT = "PROMOTION_BLOCKED_LOW_EFFECT"
    PROMOTION_BLOCKED_NEGATIVE_EFFECT = "PROMOTION_BLOCKED_NEGATIVE_EFFECT"
    PROMOTION_BLOCKED_MODEL_DEGRADED = "PROMOTION_BLOCKED_MODEL_DEGRADED"
    PROMOTION_BLOCKED_GOVERNANCE_DATA = "PROMOTION_BLOCKED_GOVERNANCE_DATA"
    PROMOTION_BLOCKED_DATA_QUALITY = "PROMOTION_BLOCKED_DATA_QUALITY"
    PROMOTION_BLOCKED_ROLLBACK_ACTIVE = "PROMOTION_BLOCKED_ROLLBACK_ACTIVE"
    PROMOTION_BLOCKED_EXPIRED = "PROMOTION_BLOCKED_EXPIRED"
    PROMOTION_BLOCKED_INVALID_STATE = "PROMOTION_BLOCKED_INVALID_STATE"


class ProductionStrategyStatus(StrEnum):
    """Health and operational status of production-promoted strategy."""

    HEALTHY = "HEALTHY"
    WARNING = "WARNING"
    DEGRADED = "DEGRADED"
    ROLLBACK_RECOMMENDED = "ROLLBACK_RECOMMENDED"
    NO_ACTIVE_STRATEGY = "NO_ACTIVE_STRATEGY"


class ExperimentStatus(StrEnum):
    """Lifecycle states of causal experiments."""

    DRAFT = "DRAFT"
    APPROVED = "APPROVED"
    RUNNING = "RUNNING"
    PAUSED = "PAUSED"
    STOPPED = "STOPPED"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"
    ARCHIVED = "ARCHIVED"


class CohortType(StrEnum):
    """Experimental cohort designation."""

    CONTROL = "CONTROL"
    TREATMENT = "TREATMENT"


class BalanceStatus(StrEnum):
    """Randomization balance assessment across covariates."""

    BALANCED = "BALANCED"
    MINOR_IMBALANCE = "MINOR_IMBALANCE"
    MAJOR_IMBALANCE = "MAJOR_IMBALANCE"


class CausalEvidenceLevel(StrEnum):
    """Rigorous classification of causal evidence."""

    LEVEL_0 = "LEVEL_0"  # INSUFFICIENT_DATA
    LEVEL_1 = "LEVEL_1"  # OBSERVATIONAL_DIFFERENCE
    LEVEL_2 = "LEVEL_2"  # STATISTICALLY_SIGNIFICANT_DIFFERENCE
    LEVEL_3 = "LEVEL_3"  # CONTROLLED_EXPERIMENT_EVIDENCE


class ExperimentDecisionType(StrEnum):
    """Deterministic experiment governance recommendation."""

    CONTINUE = "CONTINUE"
    STOP_RECOMMENDED = "STOP_RECOMMENDED"
    PROMOTE_TO_REVIEW = "PROMOTE_TO_REVIEW"
    INSUFFICIENT_DATA = "INSUFFICIENT_DATA"


class ExperimentAuditEventType(StrEnum):
    """Audit log event types for causal experimentation lifecycle."""

    EXPERIMENT_CREATED = "EXPERIMENT_CREATED"
    EXPERIMENT_APPROVED = "EXPERIMENT_APPROVED"
    EXPERIMENT_STARTED = "EXPERIMENT_STARTED"
    EXPERIMENT_PAUSED = "EXPERIMENT_PAUSED"
    EXPERIMENT_STOPPED = "EXPERIMENT_STOPPED"
    EXPERIMENT_COMPLETED = "EXPERIMENT_COMPLETED"
    EXPERIMENT_ANALYSIS_GENERATED = "EXPERIMENT_ANALYSIS_GENERATED"
    EXPERIMENT_STOP_RECOMMENDED = "EXPERIMENT_STOP_RECOMMENDED"
    EXPERIMENT_PROMOTE_TO_REVIEW = "EXPERIMENT_PROMOTE_TO_REVIEW"


# =============================================================================
# Phase 9I: Governed Model Training, Champion–Challenger & Model Lifecycle
# =============================================================================


class ModelLifecycleStatus(StrEnum):
    """Governed lifecycle states for ML models."""

    DRAFT = "DRAFT"
    TRAINING = "TRAINING"
    VALIDATING = "VALIDATING"
    REVIEW_REQUIRED = "REVIEW_REQUIRED"
    APPROVED = "APPROVED"
    PROMOTION_READY = "PROMOTION_READY"
    ACTIVE = "ACTIVE"
    RETIRED = "RETIRED"
    REJECTED = "REJECTED"
    FAILED = "FAILED"


class ModelAuditEventType(StrEnum):
    """Audit trail events for governed ML lifecycle and governance operations."""

    # Phase 9I/9J/9K Lifecycle Events
    MODEL_CREATED = "MODEL_CREATED"
    TRAINING_STARTED = "TRAINING_STARTED"
    TRAINING_COMPLETED = "TRAINING_COMPLETED"
    VALIDATION_STARTED = "VALIDATION_STARTED"
    VALIDATION_COMPLETED = "VALIDATION_COMPLETED"
    REVIEW_REQUIRED = "REVIEW_REQUIRED"
    MODEL_APPROVED = "MODEL_APPROVED"
    MODEL_REJECTED = "MODEL_REJECTED"
    PROMOTION_READY = "PROMOTION_READY"
    MODEL_ACTIVATED = "MODEL_ACTIVATED"
    MODEL_RETIRED = "MODEL_RETIRED"
    TRAINING_FAILED = "TRAINING_FAILED"

    # Phase 10J AI/ML Governance Operations
    MODEL_REGISTERED = "MODEL_REGISTERED"
    VERSION_REGISTERED = "VERSION_REGISTERED"
    MODEL_EVALUATED = "MODEL_EVALUATED"
    DRIFT_DETECTED = "DRIFT_DETECTED"
    BIAS_DETECTED = "BIAS_DETECTED"
    CALIBRATION_FAILED = "CALIBRATION_FAILED"
    EXPLANATION_GENERATED = "EXPLANATION_GENERATED"
    RISK_ASSESSED = "RISK_ASSESSED"
    APPROVAL_REQUESTED = "APPROVAL_REQUESTED"
    ROLLBACK_RECOMMENDED = "ROLLBACK_RECOMMENDED"
    ML_INCIDENT_CREATED = "ML_INCIDENT_CREATED"
    READINESS_EVALUATED = "READINESS_EVALUATED"
    REPORT_GENERATED = "REPORT_GENERATED"
    FAIRNESS_AUDITED = "fairness_audited"
    DRIFT_ANALYZED = "drift_analyzed"
    SHADOW_COMPARED = "shadow_compared"
    PROMOTION_REQUESTED = "promotion_requested"
    KILL_SWITCH_TOGGLED = "kill_switch_toggled"
    COMPLIANCE_CARD_GENERATED = "compliance_card_generated"
    INCIDENT_TRIGGERED = "incident_triggered"
    INCIDENT_ACTIONED = "incident_actioned"


class ModelScorecardRecommendation(StrEnum):
    """Deterministic champion-challenger recommendation."""

    KEEP_CHAMPION = "KEEP_CHAMPION"
    PROMOTE_CHALLENGER_REVIEW = "PROMOTE_CHALLENGER_REVIEW"
    INSUFFICIENT_DATA = "INSUFFICIENT_DATA"
    REJECT_CHALLENGER = "REJECT_CHALLENGER"


class ModelQualityGateCode(StrEnum):
    """Deterministic validation quality gates."""

    MIN_VALIDATION_SAMPLE = "MIN_VALIDATION_SAMPLE"
    ACCURACY_NON_REGRESSION = "ACCURACY_NON_REGRESSION"
    F1_NON_REGRESSION = "F1_NON_REGRESSION"
    BRIER_NON_REGRESSION = "BRIER_NON_REGRESSION"
    CALIBRATION = "CALIBRATION"
    DATA_QUALITY = "DATA_QUALITY"
    FEATURE_COMPATIBILITY = "FEATURE_COMPATIBILITY"
    DRIFT = "DRIFT"
    REPRODUCIBILITY = "REPRODUCIBILITY"
    CAUSAL_EVIDENCE = "CAUSAL_EVIDENCE"


class ComparisonStatus(StrEnum):
    """Relative improvement indicator."""

    IMPROVED = "IMPROVED"
    REGRESSED = "REGRESSED"
    UNCHANGED = "UNCHANGED"


# =============================================================================
# Phase 9J: Governed Model Deployment, Shadow Mode & Champion–Challenger
# =============================================================================


class ModelDeploymentStatus(StrEnum):
    """Governed deployment operational states."""

    # Phase 9J Deployment States
    SHADOW = "SHADOW"
    CANARY = "CANARY"
    ACTIVE = "ACTIVE"
    PAUSED = "PAUSED"
    ROLLBACK_REQUIRED = "ROLLBACK_REQUIRED"
    RETIRED = "RETIRED"

    # Phase 10J Deployment States
    NOT_DEPLOYED = "NOT_DEPLOYED"
    STAGED = "STAGED"
    PRODUCTION = "PRODUCTION"
    ROLLBACK_RECOMMENDED = "ROLLBACK_RECOMMENDED"
    BLOCKED = "BLOCKED"
    STAGING = "STAGING"
    ARCHIVED = "ARCHIVED"
    DISABLED = "DISABLED"


class DeploymentAuditEventType(StrEnum):
    """Audit log event types for model deployment lifecycle."""

    DEPLOYMENT_CREATED = "DEPLOYMENT_CREATED"
    SHADOW_STARTED = "SHADOW_STARTED"
    SHADOW_EVALUATED = "SHADOW_EVALUATED"
    DEPLOYMENT_PAUSED = "DEPLOYMENT_PAUSED"
    CANARY_STARTED = "CANARY_STARTED"
    CANARY_UPDATED = "CANARY_UPDATED"
    DEPLOYMENT_ACTIVATED = "DEPLOYMENT_ACTIVATED"
    DEPLOYMENT_ROLLED_BACK = "DEPLOYMENT_ROLLED_BACK"
    ROLLBACK_RECOMMENDED = "ROLLBACK_RECOMMENDED"


class DeploymentReadinessDecision(StrEnum):
    """Deterministic readiness assessment outcome."""

    HOLD = "HOLD"
    CONTINUE_SHADOW = "CONTINUE_SHADOW"
    PROMOTION_READY = "PROMOTION_READY"
    CANARY_ELIGIBLE = "CANARY_ELIGIBLE"
    ROLLBACK_RECOMMENDED = "ROLLBACK_RECOMMENDED"
    INSUFFICIENT_DATA = "INSUFFICIENT_DATA"


class DeploymentSignificance(StrEnum):
    """Statistical hypothesis test significance classification."""

    STATISTICALLY_SIGNIFICANT = "STATISTICALLY_SIGNIFICANT"
    NOT_STATISTICALLY_SIGNIFICANT = "NOT_STATISTICALLY_SIGNIFICANT"
    INSUFFICIENT_DATA = "INSUFFICIENT_DATA"


class DeploymentQualityGateCode(StrEnum):
    """14 Deterministic Deployment Readiness Safety Gates."""

    PHASE_9I_VALIDATION_PASSED = "PHASE_9I_VALIDATION_PASSED"
    MIN_SHADOW_SAMPLE = "MIN_SHADOW_SAMPLE"
    RECOVERY_RATE_NON_REGRESSION = "RECOVERY_RATE_NON_REGRESSION"
    MIN_PRACTICAL_UPLIFT = "MIN_PRACTICAL_UPLIFT"
    CONFIDENCE_INTERVAL_UPPER = "CONFIDENCE_INTERVAL_UPPER"
    BRIER_NON_REGRESSION = "BRIER_NON_REGRESSION"
    F1_NON_REGRESSION = "F1_NON_REGRESSION"
    CALIBRATION_ACCEPTABLE = "CALIBRATION_ACCEPTABLE"
    DATA_QUALITY_CLEAN = "DATA_QUALITY_CLEAN"
    MODEL_GOVERNANCE_HEALTHY = "MODEL_GOVERNANCE_HEALTHY"
    NO_ROLLBACK_ALERT = "NO_ROLLBACK_ALERT"
    ARTIFACT_HASH_VERIFIED = "ARTIFACT_HASH_VERIFIED"
    FEATURE_SCHEMA_COMPATIBLE = "FEATURE_SCHEMA_COMPATIBLE"
    EXPLICIT_ADMIN_APPROVAL = "EXPLICIT_ADMIN_APPROVAL"


# =============================================================================
# Phase 9K: Continuous Learning, Automated Monitoring & Safe Model Evolution
# =============================================================================


class LearningTriggerType(StrEnum):
    """Categorization of automated continuous learning triggers."""

    NEW_RESOLVED_CASES = "NEW_RESOLVED_CASES"
    MODEL_DRIFT = "MODEL_DRIFT"
    PERFORMANCE_DEGRADATION = "PERFORMANCE_DEGRADATION"
    CALIBRATION_DEGRADATION = "CALIBRATION_DEGRADATION"
    SCHEDULED_INTERVAL = "SCHEDULED_INTERVAL"


class RetrainingEligibilityDecision(StrEnum):
    """Deterministic retraining eligibility evaluation status."""

    ELIGIBLE = "ELIGIBLE"
    WAITING_FOR_DATA = "WAITING_FOR_DATA"
    DRIFT_TRIGGERED = "DRIFT_TRIGGERED"
    PERFORMANCE_TRIGGERED = "PERFORMANCE_TRIGGERED"
    CALIBRATION_TRIGGERED = "CALIBRATION_TRIGGERED"
    BLOCKED_BY_DATA_QUALITY = "BLOCKED_BY_DATA_QUALITY"
    BLOCKED_BY_ACTIVE_TRAINING = "BLOCKED_BY_ACTIVE_TRAINING"


class ModelEvolutionDecision(StrEnum):
    """Deterministic model evolution decision hierarchy."""

    NO_ACTION = "NO_ACTION"
    RETRAIN_RECOMMENDED = "RETRAIN_RECOMMENDED"
    REVIEW_REQUIRED = "REVIEW_REQUIRED"
    CHALLENGER_READY = "CHALLENGER_READY"
    PROMOTION_BLOCKED = "PROMOTION_BLOCKED"
    RETIRE_RECOMMENDED = "RETIRE_RECOMMENDED"


class ContinuousLearningQualityGateCode(StrEnum):
    """14 Deterministic Continuous Learning & Model Evolution Safety Gates."""

    MIN_DATASET_SIZE = "MIN_DATASET_SIZE"
    DATA_QUALITY = "DATA_QUALITY"
    FEATURE_SCHEMA_COMPATIBILITY = "FEATURE_SCHEMA_COMPATIBILITY"
    DATASET_CHECKSUM = "DATASET_CHECKSUM"
    MODEL_ARTIFACT_CHECKSUM = "MODEL_ARTIFACT_CHECKSUM"
    VALIDATION_SAMPLE_SIZE = "VALIDATION_SAMPLE_SIZE"
    ACCURACY_NON_REGRESSION = "ACCURACY_NON_REGRESSION"
    F1_NON_REGRESSION = "F1_NON_REGRESSION"
    BRIER_NON_REGRESSION = "BRIER_NON_REGRESSION"
    CALIBRATION = "CALIBRATION"
    DRIFT = "DRIFT"
    CAUSAL_EVIDENCE = "CAUSAL_EVIDENCE"
    HUMAN_REVIEW_REQUIRED = "HUMAN_REVIEW_REQUIRED"
    DEPLOYMENT_SEPARATION = "DEPLOYMENT_SEPARATION"


class LearningAuditEventType(StrEnum):
    """Audit log event types for continuous learning lifecycle."""

    DATASET_CREATED = "DATASET_CREATED"
    DATASET_VERSIONED = "DATASET_VERSIONED"
    RETRAINING_TRIGGERED = "RETRAINING_TRIGGERED"
    TRAINING_STARTED = "TRAINING_STARTED"
    TRAINING_COMPLETED = "TRAINING_COMPLETED"
    TRAINING_FAILED = "TRAINING_FAILED"
    VALIDATION_STARTED = "VALIDATION_STARTED"
    VALIDATION_COMPLETED = "VALIDATION_COMPLETED"
    GOVERNANCE_EVALUATED = "GOVERNANCE_EVALUATED"
    CANDIDATE_READY = "CANDIDATE_READY"
    PROMOTION_BLOCKED = "PROMOTION_BLOCKED"
    HUMAN_REVIEW_REQUIRED = "HUMAN_REVIEW_REQUIRED"


class TrainingRunStatus(StrEnum):
    """Lifecycle state of an offline training run."""

    QUEUED = "QUEUED"
    TRAINING = "TRAINING"
    VALIDATING = "VALIDATING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


# =============================================================================
# Phase 9L: Intelligence Control Plane & Unified Autonomous Governance
# =============================================================================


class GlobalSystemState(StrEnum):
    """Deterministic global intelligence health and safety states.

    Priority hierarchy (highest to lowest):
    1. EMERGENCY_LOCKDOWN
    2. ROLLBACK_REQUIRED
    3. DEGRADED
    4. HUMAN_REVIEW_REQUIRED
    5. LEARNING_REQUIRED
    6. WARNING
    7. MONITORING
    8. HEALTHY
    """

    EMERGENCY_LOCKDOWN = "EMERGENCY_LOCKDOWN"
    ROLLBACK_REQUIRED = "ROLLBACK_REQUIRED"
    DEGRADED = "DEGRADED"
    HUMAN_REVIEW_REQUIRED = "HUMAN_REVIEW_REQUIRED"
    LEARNING_REQUIRED = "LEARNING_REQUIRED"
    WARNING = "WARNING"
    MONITORING = "MONITORING"
    HEALTHY = "HEALTHY"


class SubsystemHealthStatus(StrEnum):
    """Individual health classification for intelligence subsystems."""

    HEALTHY = "HEALTHY"
    WARNING = "WARNING"
    DEGRADED = "DEGRADED"
    CRITICAL = "CRITICAL"


class ControlPlaneDiagnosticSeverity(StrEnum):
    """Severity classification for control plane diagnostics."""

    INFO = "INFO"
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class IncidentSeverity(StrEnum):
    """Severity classification for automated correlated incidents."""

    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class IncidentState(StrEnum):
    """Lifecycle status of an intelligence incident."""

    ACTIVE = "ACTIVE"
    INVESTIGATING = "INVESTIGATING"
    MITIGATED = "MITIGATED"
    RESOLVED = "RESOLVED"


class LineageStageType(StrEnum):
    """Stages in the unified model + strategy provenance progression."""

    DATASET = "DATASET"
    TRAINING_RUN = "TRAINING_RUN"
    MODEL_ARTIFACT = "MODEL_ARTIFACT"
    VALIDATION = "VALIDATION"
    GOVERNANCE = "GOVERNANCE"
    EXPERIMENT = "EXPERIMENT"
    STRATEGY_RECOMMENDATION = "STRATEGY_RECOMMENDATION"
    CONTROLLED_ROLLOUT = "CONTROLLED_ROLLOUT"
    PRODUCTION_DEPLOYMENT = "PRODUCTION_DEPLOYMENT"
    PRODUCTION_OUTCOME = "PRODUCTION_OUTCOME"


class SecurityEventType(StrEnum):
    """Event types logged to AuditLog for security and threat auditing."""

    AUTH_SUCCESS = "AUTH_SUCCESS"
    AUTH_FAILURE = "AUTH_FAILURE"
    TOKEN_REVOKED = "TOKEN_REVOKED"
    RBAC_DENIED = "RBAC_DENIED"
    RATE_LIMIT_EXCEEDED = "RATE_LIMIT_EXCEEDED"
    WEBHOOK_SIGNATURE_FAILED = "WEBHOOK_SIGNATURE_FAILED"
    WEBHOOK_REPLAY_DETECTED = "WEBHOOK_REPLAY_DETECTED"
    SUSPICIOUS_PAYLOAD_DETECTED = "SUSPICIOUS_PAYLOAD_DETECTED"
    INJECTION_ATTEMPT_DETECTED = "INJECTION_ATTEMPT_DETECTED"
    PII_LEAK_PREVENTED = "PII_LEAK_PREVENTED"
    SECRET_LEAK_PREVENTED = "SECRET_LEAK_PREVENTED"
    PRIVILEGE_ESCALATION_BLOCKED = "PRIVILEGE_ESCALATION_BLOCKED"
    SECURITY_LOCKDOWN_TRIGGERED = "SECURITY_LOCKDOWN_TRIGGERED"


class SecurityThreatSeverity(StrEnum):
    """Severity levels for detected security and threat anomalies."""

    INFO = "INFO"
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class SecurityControlStatus(StrEnum):
    """Operational status of a security control subsystem."""

    ACTIVE = "ACTIVE"
    DEGRADED = "DEGRADED"
    DISABLED = "DISABLED"
    BYPASS_PREVENTED = "BYPASS_PREVENTED"


# =============================================================================
# Phase 10C: Operational Resilience, Disaster Recovery & Business Continuity
# =============================================================================


class ResilienceState(StrEnum):
    """Deterministic global operational resilience states.

    Priority hierarchy (highest to lowest):
    1. DISASTER_MODE
    2. CRITICAL
    3. SERVICE_IMPACTED
    4. DEGRADED
    5. WARNING
    6. RECOVERY_IN_PROGRESS
    7. RECOVERY_VERIFIED
    8. OPERATIONAL
    """

    DISASTER_MODE = "DISASTER_MODE"
    CRITICAL = "CRITICAL"
    SERVICE_IMPACTED = "SERVICE_IMPACTED"
    DEGRADED = "DEGRADED"
    WARNING = "WARNING"
    RECOVERY_IN_PROGRESS = "RECOVERY_IN_PROGRESS"
    RECOVERY_VERIFIED = "RECOVERY_VERIFIED"
    OPERATIONAL = "OPERATIONAL"


class ResilienceSeverity(StrEnum):
    """Severity classification for resilience findings and incidents."""

    INFO = "INFO"
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class ServiceHealthStatus(StrEnum):
    """Health classification for individual service dependencies."""

    HEALTHY = "HEALTHY"
    DEGRADED = "DEGRADED"
    UNAVAILABLE = "UNAVAILABLE"
    UNKNOWN = "UNKNOWN"


class DependencyStatus(StrEnum):
    """Aggregate dependency health classification with threshold-based levels."""

    HEALTHY = "HEALTHY"
    WARNING = "WARNING"
    DEGRADED = "DEGRADED"
    CRITICAL = "CRITICAL"
    UNAVAILABLE = "UNAVAILABLE"


class RTORPOComplianceStatus(StrEnum):
    """Recovery Time/Point Objective compliance classification."""

    COMPLIANT = "COMPLIANT"
    AT_RISK = "AT_RISK"
    BREACHED = "BREACHED"
    UNKNOWN = "UNKNOWN"


class ReadinessStatus(StrEnum):
    """Disaster recovery readiness gate classification."""

    READY = "READY"
    CONDITIONAL = "CONDITIONAL"
    BLOCKED = "BLOCKED"
    UNKNOWN = "UNKNOWN"


class DisasterScenarioType(StrEnum):
    """Supported observational disaster simulation scenario types."""

    DATABASE_OUTAGE = "DATABASE_OUTAGE"
    REDIS_OUTAGE = "REDIS_OUTAGE"
    WORKER_FAILURE = "WORKER_FAILURE"
    QUEUE_BACKLOG = "QUEUE_BACKLOG"
    WEBHOOK_OUTAGE = "WEBHOOK_OUTAGE"
    ML_SERVICE_DEGRADATION = "ML_SERVICE_DEGRADATION"
    POLICYENGINE_DEGRADATION = "POLICYENGINE_DEGRADATION"
    AUDITLOG_FAILURE = "AUDITLOG_FAILURE"
    PAYMENT_PROVIDER_UNAVAILABLE = "PAYMENT_PROVIDER_UNAVAILABLE"
    REGIONAL_OUTAGE = "REGIONAL_OUTAGE"
    CASCADING_DEPENDENCY_FAILURE = "CASCADING_DEPENDENCY_FAILURE"


class ResilienceIncidentStatus(StrEnum):
    """Lifecycle state of an operational resilience incident."""

    DETECTED = "DETECTED"
    TRIAGED = "TRIAGED"
    HUMAN_REVIEW = "HUMAN_REVIEW"
    MITIGATION_RECOMMENDED = "MITIGATION_RECOMMENDED"
    RECOVERY_IN_PROGRESS = "RECOVERY_IN_PROGRESS"
    RECOVERY_VERIFIED = "RECOVERY_VERIFIED"
    CLOSED = "CLOSED"


class ResilienceIncidentType(StrEnum):
    """Deterministic incident type codes for operational resilience."""

    DB_OUTAGE = "DB_OUTAGE"
    QUEUE_BACKLOG = "QUEUE_BACKLOG"
    WORKER_FAILURE = "WORKER_FAILURE"
    WEBHOOK_DELAY = "WEBHOOK_DELAY"
    CASCADING_FAILURE = "CASCADING_FAILURE"
    RTO_BREACH = "RTO_BREACH"
    RPO_BREACH = "RPO_BREACH"
    BACKUP_STALENESS = "BACKUP_STALENESS"
    RESTORE_UNVERIFIED = "RESTORE_UNVERIFIED"


class ResilienceAuditEventType(StrEnum):
    """Audit log event types for operational resilience lifecycle."""

    RESILIENCE_CHECK_STARTED = "RESILIENCE_CHECK_STARTED"
    RESILIENCE_CHECK_COMPLETED = "RESILIENCE_CHECK_COMPLETED"
    DEPENDENCY_DEGRADED = "DEPENDENCY_DEGRADED"
    DEPENDENCY_RECOVERED = "DEPENDENCY_RECOVERED"
    INCIDENT_DETECTED = "INCIDENT_DETECTED"
    INCIDENT_ACKNOWLEDGED = "INCIDENT_ACKNOWLEDGED"
    INCIDENT_ESCALATED = "INCIDENT_ESCALATED"
    SIMULATION_STARTED = "SIMULATION_STARTED"
    SIMULATION_COMPLETED = "SIMULATION_COMPLETED"
    BACKUP_VERIFIED = "BACKUP_VERIFIED"
    RESTORE_TEST_VERIFIED = "RESTORE_TEST_VERIFIED"
    RTO_BREACH_DETECTED = "RTO_BREACH_DETECTED"
    RPO_BREACH_DETECTED = "RPO_BREACH_DETECTED"
    RECOVERY_STARTED = "RECOVERY_STARTED"
    RECOVERY_VERIFIED = "RECOVERY_VERIFIED"
    RUNBOOK_EXECUTED = "RUNBOOK_EXECUTED"


class BackupIntegrityStatus(StrEnum):
    """Integrity verification status for backup artifacts."""

    VALID = "VALID"
    CORRUPTED = "CORRUPTED"
    UNKNOWN = "UNKNOWN"


class RestoreVerificationStatus(StrEnum):
    """Restore operation test verification status."""

    VERIFIED = "VERIFIED"
    UNVERIFIED = "UNVERIFIED"
    FAILED = "FAILED"


class BackupFreshnessStatus(StrEnum):
    """Freshness/staleness classification for backup age."""

    CURRENT = "CURRENT"
    STALE = "STALE"
    EXPIRED = "EXPIRED"


# =============================================================================
# Phase 10D: Fintech Observability, SRE, Incident Response & Production Operations
# =============================================================================


class OperationalState(StrEnum):
    """Deterministic global operational states.

    Priority hierarchy (highest to lowest):
    1. EMERGENCY_OPERATIONAL_STATE
    2. CRITICAL_INCIDENT
    3. MAJOR_INCIDENT
    4. INCIDENT
    5. DEGRADED
    6. WARNING
    7. MONITORING
    8. RECOVERY
    9. STABILIZED
    10. HEALTHY
    """

    EMERGENCY_OPERATIONAL_STATE = "EMERGENCY_OPERATIONAL_STATE"
    CRITICAL_INCIDENT = "CRITICAL_INCIDENT"
    MAJOR_INCIDENT = "MAJOR_INCIDENT"
    INCIDENT = "INCIDENT"
    DEGRADED = "DEGRADED"
    WARNING = "WARNING"
    MONITORING = "MONITORING"
    RECOVERY = "RECOVERY"
    STABILIZED = "STABILIZED"
    HEALTHY = "HEALTHY"


class ObservabilitySeverity(StrEnum):
    """Severity classification for observability metrics, alerts, and findings."""

    INFO = "INFO"
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class SLIStatus(StrEnum):
    """Operational status of a Service Level Indicator."""

    HEALTHY = "HEALTHY"
    WARNING = "WARNING"
    CRITICAL = "CRITICAL"
    UNKNOWN = "UNKNOWN"


class SLOStatus(StrEnum):
    """Compliance status of a Service Level Objective."""

    COMPLIANT = "COMPLIANT"
    AT_RISK = "AT_RISK"
    BREACHED = "BREACHED"
    UNKNOWN = "UNKNOWN"


class ErrorBudgetStatus(StrEnum):
    """Error budget consumption and burn rate status."""

    HEALTHY = "HEALTHY"
    WARNING = "WARNING"
    FAST_BURN = "FAST_BURN"
    CRITICAL_BURN = "CRITICAL_BURN"
    EXHAUSTED = "EXHAUSTED"


class AlertStatus(StrEnum):
    """Operational status of an observability alert."""

    ACTIVE = "ACTIVE"
    SUPPRESSED = "SUPPRESSED"
    ACKNOWLEDGED = "ACKNOWLEDGED"
    RESOLVED = "RESOLVED"


class SREIncidentSeverity(StrEnum):
    """Standardized SRE incident severity levels."""

    SEV_1 = "SEV_1"
    SEV_2 = "SEV_2"
    SEV_3 = "SEV_3"
    SEV_4 = "SEV_4"


ObservabilityIncidentSeverity = SREIncidentSeverity


class ObservabilityIncidentStatus(StrEnum):
    """Complete lifecycle status of an SRE operational incident."""

    DETECTED = "DETECTED"
    TRIAGED = "TRIAGED"
    ACKNOWLEDGED = "ACKNOWLEDGED"
    INVESTIGATING = "INVESTIGATING"
    MITIGATION_RECOMMENDED = "MITIGATION_RECOMMENDED"
    MONITORING = "MONITORING"
    RESOLVED = "RESOLVED"
    POST_INCIDENT_REVIEW = "POST_INCIDENT_REVIEW"
    CLOSED = "CLOSED"


IncidentLifecycleStatus = ObservabilityIncidentStatus


class ObservabilityIncidentType(StrEnum):
    """Deterministic incident categories for production operations."""

    PERFORMANCE = "PERFORMANCE"
    AVAILABILITY = "AVAILABILITY"
    CAPACITY = "CAPACITY"
    DEPENDENCY = "DEPENDENCY"
    DATABASE = "DATABASE"
    QUEUE = "QUEUE"
    WORKER = "WORKER"
    WEBHOOK = "WEBHOOK"
    ML = "ML"
    POLICYENGINE = "POLICYENGINE"
    SECURITY = "SECURITY"
    DATA_QUALITY = "DATA_QUALITY"
    DEPLOYMENT = "DEPLOYMENT"
    CONFIGURATION = "CONFIGURATION"
    CASCADING_FAILURE = "CASCADING_FAILURE"
    UNKNOWN = "UNKNOWN"


class TraceStatus(StrEnum):
    """Status of a distributed trace or span."""

    OK = "OK"
    ERROR = "ERROR"
    DEGRADED = "DEGRADED"


class DeploymentImpactStatus(StrEnum):
    """Change-impact classification for production deployments."""

    NO_DETECTED_IMPACT = "NO_DETECTED_IMPACT"
    POSSIBLE_IMPACT = "POSSIBLE_IMPACT"
    LIKELY_IMPACT = "LIKELY_IMPACT"
    HIGH_CONFIDENCE_IMPACT = "HIGH_CONFIDENCE_IMPACT"


class TrafficAnomalyType(StrEnum):
    """Traffic and throughput anomaly classification."""

    NORMAL_TRAFFIC = "NORMAL_TRAFFIC"
    TRAFFIC_SPIKE = "TRAFFIC_SPIKE"
    TRAFFIC_DROP = "TRAFFIC_DROP"
    UNKNOWN_TRAFFIC = "UNKNOWN_TRAFFIC"


class QueueHealthStatus(StrEnum):
    """Queue processing and backlog health status."""

    QUEUE_HEALTHY = "QUEUE_HEALTHY"
    QUEUE_WARNING = "QUEUE_WARNING"
    QUEUE_BACKLOG = "QUEUE_BACKLOG"
    QUEUE_CRITICAL = "QUEUE_CRITICAL"


class WorkerHealthStatus(StrEnum):
    """Worker node and execution pool status."""

    HEALTHY = "HEALTHY"
    DEGRADED = "DEGRADED"
    UNAVAILABLE = "UNAVAILABLE"
    RECOVERING = "RECOVERING"


class WebhookHealthStatus(StrEnum):
    """Webhook ingestion and signature processing status."""

    HEALTHY = "HEALTHY"
    DEGRADED = "DEGRADED"
    UNAVAILABLE = "UNAVAILABLE"
    BACKLOGGED = "BACKLOGGED"


class MLObservabilityStatus(StrEnum):
    """ML model inference and prediction telemetry status."""

    MODEL_HEALTHY = "MODEL_HEALTHY"
    MODEL_LATENCY_DEGRADED = "MODEL_LATENCY_DEGRADED"
    MODEL_ERROR_SPIKE = "MODEL_ERROR_SPIKE"
    MODEL_DRIFT_WARNING = "MODEL_DRIFT_WARNING"
    MODEL_CALIBRATION_WARNING = "MODEL_CALIBRATION_WARNING"
    MODEL_VERSION_ANOMALY = "MODEL_VERSION_ANOMALY"


class PolicyEngineObservabilityStatus(StrEnum):
    """PolicyEngine gatekeeper telemetry status."""

    POLICY_HEALTHY = "POLICY_HEALTHY"
    POLICY_LATENCY_DEGRADED = "POLICY_LATENCY_DEGRADED"
    POLICY_ERROR_SPIKE = "POLICY_ERROR_SPIKE"
    POLICY_TIMEOUT_WARNING = "POLICY_TIMEOUT_WARNING"


class OperationalReadinessStatus(StrEnum):
    """Readiness status for production operations gates."""

    READY = "READY"
    CONDITIONAL = "CONDITIONAL"
    BLOCKED = "BLOCKED"
    UNKNOWN = "UNKNOWN"


class RootCauseConfidence(StrEnum):
    """Confidence level for post-incident root cause classification."""

    CONFIRMED = "CONFIRMED"
    LIKELY = "LIKELY"
    POSSIBLE = "POSSIBLE"
    UNKNOWN = "UNKNOWN"


class ObservabilityAuditEventType(StrEnum):
    """AuditLog event types for observability, alerting, and incident operations."""

    OBSERVABILITY_CHECK_STARTED = "OBSERVABILITY_CHECK_STARTED"
    OBSERVABILITY_CHECK_COMPLETED = "OBSERVABILITY_CHECK_COMPLETED"
    ALERT_DETECTED = "ALERT_DETECTED"
    ALERT_DEDUPLICATED = "ALERT_DEDUPLICATED"
    INCIDENT_CREATED = "INCIDENT_CREATED"
    INCIDENT_TRIAGED = "INCIDENT_TRIAGED"
    INCIDENT_ACKNOWLEDGED = "INCIDENT_ACKNOWLEDGED"
    INCIDENT_ESCALATED = "INCIDENT_ESCALATED"
    INCIDENT_RESOLVED = "INCIDENT_RESOLVED"
    INCIDENT_CLOSED = "INCIDENT_CLOSED"
    SLO_BREACH_DETECTED = "SLO_BREACH_DETECTED"
    ERROR_BUDGET_BREACH = "ERROR_BUDGET_BREACH"
    DEPLOYMENT_IMPACT_DETECTED = "DEPLOYMENT_IMPACT_DETECTED"
    POSTMORTEM_CREATED = "POSTMORTEM_CREATED"
    POSTMORTEM_APPROVED = "POSTMORTEM_APPROVED"
    ROOT_CAUSE_UPDATED = "ROOT_CAUSE_UPDATED"
    READINESS_EVALUATED = "READINESS_EVALUATED"


# =============================================================================
# Phase 10E: Data Governance, Privacy Engineering, Data Lineage & Regulatory-Grade Data Controls
# =============================================================================


class DataClassification(StrEnum):
    """Data classification tiers for RecoverIQ data assets and fields."""

    PUBLIC = "PUBLIC"
    INTERNAL = "INTERNAL"
    CONFIDENTIAL = "CONFIDENTIAL"
    SENSITIVE = "SENSITIVE"
    RESTRICTED = "RESTRICTED"
    FINANCIAL_RESTRICTED = "FINANCIAL_RESTRICTED"


class DataDomain(StrEnum):
    """Business and architectural data domains."""

    PAYMENT = "PAYMENT"
    RECOVERY = "RECOVERY"
    CUSTOMER = "CUSTOMER"
    ML = "ML"
    AUDIT = "AUDIT"
    SECURITY = "SECURITY"
    OBSERVABILITY = "OBSERVABILITY"
    COMPLIANCE = "COMPLIANCE"
    EXPERIMENTATION = "EXPERIMENTATION"
    DEPLOYMENT = "DEPLOYMENT"
    RESILIENCE = "RESILIENCE"


class DataOwnerRole(StrEnum):
    """Data ownership and stewardship roles."""

    DATA_OWNER = "DATA_OWNER"
    DATA_STEWARD = "DATA_STEWARD"
    SECURITY_ADMIN = "SECURITY_ADMIN"
    COMPLIANCE_OPERATOR = "COMPLIANCE_OPERATOR"
    SYSTEM_ADMIN = "SYSTEM_ADMIN"


class ProcessingPurpose(StrEnum):
    """Lawful and regulatory processing purposes."""

    PAYMENT_PROCESSING = "PAYMENT_PROCESSING"
    RECOVERY_ANALYTICS = "RECOVERY_ANALYTICS"
    MODEL_TRAINING = "MODEL_TRAINING"
    MODEL_EVALUATION = "MODEL_EVALUATION"
    SECURITY_MONITORING = "SECURITY_MONITORING"
    AUDIT = "AUDIT"
    COMPLIANCE = "COMPLIANCE"
    OBSERVABILITY = "OBSERVABILITY"
    DISASTER_RECOVERY = "DISASTER_RECOVERY"


class PrivacyControlStatus(StrEnum):
    """Status for automated privacy and data governance controls."""

    PASS = "PASS"
    WARNING = "WARNING"
    FAIL = "FAIL"
    NOT_APPLICABLE = "NOT_APPLICABLE"


class RetentionStatus(StrEnum):
    """Lifecycle retention status for data assets and tables."""

    WITHIN_POLICY = "WITHIN_POLICY"
    EXPIRING_SOON = "EXPIRING_SOON"
    OVERDUE = "OVERDUE"
    LEGAL_HOLD = "LEGAL_HOLD"
    EXEMPT = "EXEMPT"


class LineageNodeType(StrEnum):
    """Node types in the end-to-end data and transformation lineage graph."""

    SOURCE = "SOURCE"
    INGESTION = "INGESTION"
    TRANSFORMATION = "TRANSFORMATION"
    DATASET = "DATASET"
    MODEL = "MODEL"
    PREDICTION = "PREDICTION"
    DECISION = "DECISION"
    OUTPUT = "OUTPUT"
    AUDIT = "AUDIT"


class PrivacyIncidentSeverity(StrEnum):
    """Severity levels for privacy, data leak, and lineage incidents."""

    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class PrivacyRequestType(StrEnum):
    """Subject rights and data governance request types."""

    ACCESS = "ACCESS"
    EXPORT = "EXPORT"
    RECTIFICATION = "RECTIFICATION"
    ERASURE = "ERASURE"
    RESTRICTION = "RESTRICTION"
    PROCESSING_PURPOSE = "PROCESSING_PURPOSE"


class PrivacyRequestStatus(StrEnum):
    """Lifecycle state machine for privacy and data governance requests."""

    RECEIVED = "RECEIVED"
    UNDER_REVIEW = "UNDER_REVIEW"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    COMPLETED = "COMPLETED"
    BLOCKED = "BLOCKED"


class DataQualityStatus(StrEnum):
    """Data quality and hygiene health assessment."""

    HEALTHY = "HEALTHY"
    DEGRADED = "DEGRADED"
    CRITICAL = "CRITICAL"


class GovernanceScoreClassification(StrEnum):
    """Categorical classification for the overall 0-100 data governance score."""

    EXCELLENT = "EXCELLENT"
    GOOD = "GOOD"
    WARNING = "WARNING"
    HIGH_RISK = "HIGH_RISK"
    CRITICAL = "CRITICAL"


class DataGovernanceAuditEventType(StrEnum):
    """AuditLog event types for Phase 10E Data Governance and Privacy operations."""

    DATA_ASSET_REGISTERED = "DATA_ASSET_REGISTERED"
    CLASSIFICATION_UPDATED = "CLASSIFICATION_UPDATED"
    LINEAGE_REGISTERED = "LINEAGE_REGISTERED"
    RETENTION_EVALUATED = "RETENTION_EVALUATED"
    PRIVACY_SCAN_COMPLETED = "PRIVACY_SCAN_COMPLETED"
    ACCESS_REVIEW_COMPLETED = "ACCESS_REVIEW_COMPLETED"
    PRIVACY_INCIDENT_DETECTED = "PRIVACY_INCIDENT_DETECTED"
    PRIVACY_REQUEST_CREATED = "PRIVACY_REQUEST_CREATED"
    PRIVACY_REQUEST_REVIEWED = "PRIVACY_REQUEST_REVIEWED"
    PRIVACY_REQUEST_APPROVED = "PRIVACY_REQUEST_APPROVED"
    PRIVACY_REQUEST_REJECTED = "PRIVACY_REQUEST_REJECTED"
    PRIVACY_REQUEST_COMPLETED = "PRIVACY_REQUEST_COMPLETED"
    DATA_GOVERNANCE_POLICY_EVALUATED = "DATA_GOVERNANCE_POLICY_EVALUATED"


# =========================================================================
# Phase 10F: Fintech Performance Engineering, Scalability, Capacity Planning & High-Load Resilience
# =========================================================================


class PerformanceHealth(StrEnum):
    """Categorical classification for the overall 0-100 performance score."""

    EXCELLENT = "EXCELLENT"
    GOOD = "GOOD"
    WARNING = "WARNING"
    DEGRADED = "DEGRADED"
    CRITICAL = "CRITICAL"


class PerformanceGlobalState(StrEnum):
    """Global performance and capacity state in priority order."""

    EMERGENCY_CAPACITY_FAILURE = "EMERGENCY_CAPACITY_FAILURE"
    PERFORMANCE_CRITICAL = "PERFORMANCE_CRITICAL"
    CAPACITY_EXHAUSTION = "CAPACITY_EXHAUSTION"
    SEVERE_DEGRADATION = "SEVERE_DEGRADATION"
    PERFORMANCE_DEGRADED = "PERFORMANCE_DEGRADED"
    HIGH_UTILIZATION = "HIGH_UTILIZATION"
    SCALING_RECOMMENDED = "SCALING_RECOMMENDED"
    PERFORMANCE_WARNING = "PERFORMANCE_WARNING"
    MONITORING = "MONITORING"
    HEALTHY = "HEALTHY"


class PerformanceSeverity(StrEnum):
    """Severity levels for performance degradation, bottlenecks, and incidents."""

    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class CapacityState(StrEnum):
    """System and service level capacity headroom state."""

    SAFE = "SAFE"
    ADEQUATE = "ADEQUATE"
    CONSTRAINED = "CONSTRAINED"
    EXHAUSTED = "EXHAUSTED"
    CRITICAL = "CRITICAL"


class QueueState(StrEnum):
    """Background queue and worker backpressure state."""

    QUEUE_HEALTHY = "QUEUE_HEALTHY"
    QUEUE_GROWING = "QUEUE_GROWING"
    QUEUE_SATURATED = "QUEUE_SATURATED"
    QUEUE_CRITICAL = "QUEUE_CRITICAL"


class DatabasePerformanceState(StrEnum):
    """Relational database risk and performance state."""

    DB_HEALTHY = "DB_HEALTHY"
    DB_WARNING = "DB_WARNING"
    DB_DEGRADED = "DB_DEGRADED"
    DB_SATURATED = "DB_SATURATED"
    DB_CRITICAL = "DB_CRITICAL"


class CachePerformanceState(StrEnum):
    """Redis / memory cache health and pressure state."""

    CACHE_HEALTHY = "CACHE_HEALTHY"
    CACHE_WARNING = "CACHE_WARNING"
    CACHE_DEGRADED = "CACHE_DEGRADED"
    CACHE_PRESSURED = "CACHE_PRESSURED"
    CACHE_CRITICAL = "CACHE_CRITICAL"


class BottleneckType(StrEnum):
    """Subsystem identified as primary or secondary performance bottleneck."""

    API = "API"
    DATABASE = "DATABASE"
    REDIS = "REDIS"
    QUEUE = "QUEUE"
    WORKER = "WORKER"
    ML = "ML"
    WEBHOOK = "WEBHOOK"
    CPU = "CPU"
    MEMORY = "MEMORY"
    NETWORK = "NETWORK"
    EXTERNAL_PROVIDER = "EXTERNAL_PROVIDER"
    NONE = "NONE"


class ScalingRecommendation(StrEnum):
    """Governed advisory scaling action recommendation."""

    NO_SCALING_REQUIRED = "NO_SCALING_REQUIRED"
    MONITOR = "MONITOR"
    SCALE_SOON = "SCALE_SOON"
    SCALE_NOW = "SCALE_NOW"
    EMERGENCY_SCALE = "EMERGENCY_SCALE"


class LoadTestScenario(StrEnum):
    """Synthetic benchmark and load testing scenarios."""

    API_NORMAL = "API_NORMAL"
    API_2X = "API_2X"
    API_5X = "API_5X"
    API_10X = "API_10X"
    API_20X = "API_20X"
    WEBHOOK_NORMAL = "WEBHOOK_NORMAL"
    WEBHOOK_5X = "WEBHOOK_5X"
    WEBHOOK_10X = "WEBHOOK_10X"
    WEBHOOK_20X = "WEBHOOK_20X"
    RECOVERY_NORMAL = "RECOVERY_NORMAL"
    RECOVERY_5X = "RECOVERY_5X"
    RECOVERY_10X = "RECOVERY_10X"
    ML_NORMAL = "ML_NORMAL"
    ML_5X = "ML_5X"
    ML_10X = "ML_10X"
    DATABASE_PRESSURE = "DATABASE_PRESSURE"
    CACHE_PRESSURE = "CACHE_PRESSURE"
    QUEUE_PRESSURE = "QUEUE_PRESSURE"


class LoadTestStatus(StrEnum):
    """Lifecycle state of synthetic benchmark runs."""

    INITIALIZED = "INITIALIZED"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    ABORTED = "ABORTED"


class PerformanceIncidentType(StrEnum):
    """Categorization of performance incidents."""

    PERF_LATENCY_CRITICAL = "PERF_LATENCY_CRITICAL"
    PERF_THROUGHPUT_COLLAPSE = "PERF_THROUGHPUT_COLLAPSE"
    PERF_DB_SATURATION = "PERF_DB_SATURATION"
    PERF_QUEUE_EXPLOSION = "PERF_QUEUE_EXPLOSION"
    PERF_ML_BACKLOG = "PERF_ML_BACKLOG"
    PERF_CACHE_PRESSURE = "PERF_CACHE_PRESSURE"
    PERF_WORKER_SATURATION = "PERF_WORKER_SATURATION"
    PERF_CAPACITY_EXHAUSTION = "PERF_CAPACITY_EXHAUSTION"


class PerformanceIncidentStatus(StrEnum):
    """Lifecycle status of performance incident records."""

    DETECTED = "DETECTED"
    INVESTIGATING = "INVESTIGATING"
    MITIGATING = "MITIGATING"
    RESOLVED = "RESOLVED"
    AUTO_REMEDIATED = "AUTO_REMEDIATED"


class PerformanceAuditEventType(StrEnum):
    """AuditLog event types for Phase 10F Performance and Capacity operations."""

    PERFORMANCE_BENCHMARK_EXECUTED = "PERFORMANCE_BENCHMARK_EXECUTED"
    CAPACITY_ASSESSMENT_COMPLETED = "CAPACITY_ASSESSMENT_COMPLETED"
    LOAD_TEST_INITIATED = "LOAD_TEST_INITIATED"
    LOAD_TEST_COMPLETED = "LOAD_TEST_COMPLETED"
    LOAD_TEST_APPROVED = "LOAD_TEST_APPROVED"
    SCALING_RECOMMENDATION_ISSUED = "SCALING_RECOMMENDATION_ISSUED"
    PERFORMANCE_INCIDENT_DETECTED = "PERFORMANCE_INCIDENT_DETECTED"
    PERFORMANCE_INCIDENT_UPDATED = "PERFORMANCE_INCIDENT_UPDATED"
    BOTTLENECK_IDENTIFIED = "BOTTLENECK_IDENTIFIED"
    CACHE_ANALYSIS_EXECUTED = "CACHE_ANALYSIS_EXECUTED"
    DB_PERFORMANCE_AUDITED = "DB_PERFORMANCE_AUDITED"


# =============================================================================
# Phase 10G: Fintech Architecture Governance, Change Management & Release Safety
# =============================================================================


class ChangeType(StrEnum):
    """Categorization of proposed system changes."""

    FEATURE = "FEATURE"
    BUGFIX = "BUGFIX"
    SECURITY = "SECURITY"
    DATABASE = "DATABASE"
    API = "API"
    CONFIGURATION = "CONFIGURATION"
    DEPENDENCY = "DEPENDENCY"
    ML_MODEL = "ML_MODEL"
    INFRASTRUCTURE = "INFRASTRUCTURE"
    HOTFIX = "HOTFIX"


class ChangeRiskLevel(StrEnum):
    """Risk severity classification for change requests."""

    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class ChangeStatus(StrEnum):
    """Lifecycle status of a change request."""

    PROPOSED = "PROPOSED"
    IN_REVIEW = "IN_REVIEW"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    DEPLOYED = "DEPLOYED"
    CANCELLED = "CANCELLED"


class ChangeApprovalStatus(StrEnum):
    """Human approval state for change governance."""

    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    CHANGES_REQUESTED = "CHANGES_REQUESTED"


class ReleaseStage(StrEnum):
    """Progressive release deployment stages."""

    DRAFT = "DRAFT"
    TESTING = "TESTING"
    STAGING = "STAGING"
    CANARY = "CANARY"
    PRODUCTION = "PRODUCTION"
    ROLLED_BACK = "ROLLED_BACK"


class ReleaseStatus(StrEnum):
    """Lifecycle status of a release candidate."""

    PREPARING = "PREPARING"
    READY_FOR_REVIEW = "READY_FOR_REVIEW"
    APPROVED = "APPROVED"
    IN_PROGRESS = "IN_PROGRESS"
    SUCCESSFUL = "SUCCESSFUL"
    FAILED = "FAILED"
    ABORTED = "ABORTED"


class ReleaseHealth(StrEnum):
    """Deterministic release safety score classification."""

    EXCELLENT = "EXCELLENT"
    HEALTHY = "HEALTHY"
    WARNING = "WARNING"
    DEGRADED = "DEGRADED"
    CRITICAL = "CRITICAL"


class ReleaseDecision(StrEnum):
    """Advisory release governance decision."""

    GO = "GO"
    NO_GO = "NO_GO"
    CONDITIONAL_GO = "CONDITIONAL_GO"
    PENDING_REVIEW = "PENDING_REVIEW"


class DeploymentStrategy(StrEnum):
    """Target deployment strategy for a release candidate."""

    BLUE_GREEN = "BLUE_GREEN"
    CANARY = "CANARY"
    ROLLING = "ROLLING"
    SHADOW = "SHADOW"
    ROLLBACK = "ROLLBACK"


class ArchitectureRisk(StrEnum):
    """Architecture structural impact risk level."""

    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class DependencyRisk(StrEnum):
    """Dependency coupling and blast-radius risk level."""

    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class CompatibilityStatus(StrEnum):
    """API and Database contract compatibility status."""

    BACKWARD_COMPATIBLE = "BACKWARD_COMPATIBLE"
    NON_BREAKING = "NON_BREAKING"
    BREAKING = "BREAKING"
    UNKNOWN = "UNKNOWN"


class ArchitectureLayer(StrEnum):
    """Categorization of architectural layers."""

    GATEWAY = "GATEWAY"
    CORE_ENGINE = "CORE_ENGINE"
    DATA_TIER = "DATA_TIER"
    INTEGRATION = "INTEGRATION"
    OBSERVABILITY = "OBSERVABILITY"
    GOVERNANCE = "GOVERNANCE"


class ConfigurationDriftStatus(StrEnum):
    """Configuration synchronization status."""

    IN_SYNC = "IN_SYNC"
    DRIFT_DETECTED = "DRIFT_DETECTED"
    CRITICAL_DRIFT = "CRITICAL_DRIFT"
    OVERRIDDEN = "OVERRIDDEN"


class FeatureFlagStatus(StrEnum):
    """Lifecycle state of a governed feature flag."""

    CREATED = "CREATED"
    ACTIVE = "ACTIVE"
    ROLLOUT = "ROLLOUT"
    PAUSED = "PAUSED"
    ROLLED_BACK = "ROLLED_BACK"
    RETIRED = "RETIRED"


class GovernanceDecision(StrEnum):
    """Human review decision for release and change governance."""

    APPROVE = "APPROVE"
    REJECT = "REJECT"
    REQUEST_CHANGES = "REQUEST_CHANGES"
    HOLD = "HOLD"


class ReleaseAuditEventType(StrEnum):
    """AuditLog event types for Phase 10G Release Governance operations."""

    CHANGE_REQUEST_CREATED = "CHANGE_REQUEST_CREATED"
    CHANGE_REQUEST_APPROVED = "CHANGE_REQUEST_APPROVED"
    CHANGE_REQUEST_REJECTED = "CHANGE_REQUEST_REJECTED"
    RELEASE_CANDIDATE_CREATED = "RELEASE_CANDIDATE_CREATED"
    RELEASE_APPROVED = "RELEASE_APPROVED"
    RELEASE_REJECTED = "RELEASE_REJECTED"
    CONFIG_DRIFT_DETECTED = "CONFIG_DRIFT_DETECTED"
    FEATURE_FLAG_CREATED = "FEATURE_FLAG_CREATED"
    FEATURE_FLAG_UPDATED = "FEATURE_FLAG_UPDATED"
    ROLLBACK_TRIGGERED = "ROLLBACK_TRIGGERED"
    CANARY_EVALUATED = "CANARY_EVALUATED"
    READINESS_GATES_EVALUATED = "READINESS_GATES_EVALUATED"
    ARCHITECTURE_FINDING_RECORDED = "ARCHITECTURE_FINDING_RECORDED"


class ZeroTrustScoreClassification(StrEnum):
    """Zero-Trust posture classification."""

    TRUSTED = "TRUSTED"
    ACCEPTABLE = "ACCEPTABLE"
    DEGRADED = "DEGRADED"
    HIGH_RISK = "HIGH_RISK"
    CRITICAL = "CRITICAL"


class GlobalSecurityState(StrEnum):
    """Global Security State Priority Hierarchy."""

    EMERGENCY_SECURITY_LOCKDOWN = "EMERGENCY_SECURITY_LOCKDOWN"
    CRITICAL_SECURITY_BREACH = "CRITICAL_SECURITY_BREACH"
    ACTIVE_ATTACK = "ACTIVE_ATTACK"
    TRUST_BOUNDARY_VIOLATION = "TRUST_BOUNDARY_VIOLATION"
    HIGH_SECURITY_RISK = "HIGH_SECURITY_RISK"
    THREAT_DETECTED = "THREAT_DETECTED"
    SECURITY_DEGRADED = "SECURITY_DEGRADED"
    INVESTIGATION_REQUIRED = "INVESTIGATION_REQUIRED"
    MONITORING = "MONITORING"
    SECURE = "SECURE"


class ServiceIdentityStatus(StrEnum):
    """Service identity authentication and trust status."""

    AUTHENTICATED = "AUTHENTICATED"
    VALIDATED = "VALIDATED"
    DEGRADED = "DEGRADED"
    STALE_CREDENTIAL = "STALE_CREDENTIAL"
    REVOKED = "REVOKED"
    UNTRUSTED = "UNTRUSTED"


class AuthMatrixStatus(StrEnum):
    """Service-to-service authorization matrix status."""

    ALLOWED = "ALLOWED"
    DENIED = "DENIED"
    CONDITIONAL = "CONDITIONAL"
    REVIEW_REQUIRED = "REVIEW_REQUIRED"


class ThreatSeverity(StrEnum):
    """Threat indicator and attack-chain severity classification."""

    INFORMATIONAL = "INFORMATIONAL"
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class ThreatScoreClassification(StrEnum):
    """Behavioral threat score classification."""

    INFORMATIONAL = "INFORMATIONAL"
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class SecurityIncidentStatus(StrEnum):
    """Security incident lifecycle state."""

    DETECTED = "DETECTED"
    TRIAGED = "TRIAGED"
    ACKNOWLEDGED = "ACKNOWLEDGED"
    INVESTIGATING = "INVESTIGATING"
    CONTAINMENT_RECOMMENDED = "CONTAINMENT_RECOMMENDED"
    ESCALATED = "ESCALATED"
    RESOLVED = "RESOLVED"
    POST_INCIDENT_REVIEW = "POST_INCIDENT_REVIEW"


class ZeroTrustGateStatus(StrEnum):
    """Zero-Trust readiness gate status."""

    PASS = "PASS"
    WARN = "WARN"
    FAIL = "FAIL"
    BLOCKED = "BLOCKED"


class ZeroTrustGateId(StrEnum):
    """Identifiers for the 22 Zero-Trust Security Readiness Gates."""

    GATE_ZT_01 = "GATE-ZT-01"
    GATE_ZT_02 = "GATE-ZT-02"
    GATE_ZT_03 = "GATE-ZT-03"
    GATE_ZT_04 = "GATE-ZT-04"
    GATE_ZT_05 = "GATE-ZT-05"
    GATE_ZT_06 = "GATE-ZT-06"
    GATE_ZT_07 = "GATE-ZT-07"
    GATE_ZT_08 = "GATE-ZT-08"
    GATE_ZT_09 = "GATE-ZT-09"
    GATE_ZT_10 = "GATE-ZT-10"
    GATE_ZT_11 = "GATE-ZT-11"
    GATE_ZT_12 = "GATE-ZT-12"
    GATE_ZT_13 = "GATE-ZT-13"
    GATE_ZT_14 = "GATE-ZT-14"
    GATE_ZT_15 = "GATE-ZT-15"
    GATE_ZT_16 = "GATE-ZT-16"
    GATE_ZT_17 = "GATE-ZT-17"
    GATE_ZT_18 = "GATE-ZT-18"
    GATE_ZT_19 = "GATE-ZT-19"
    GATE_ZT_20 = "GATE-ZT-20"
    GATE_ZT_21 = "GATE-ZT-21"
    GATE_ZT_22 = "GATE-ZT-22"


class AttackChainStage(StrEnum):
    """Sequential stages of a reconstructed attack chain."""

    INITIAL_SIGNAL = "INITIAL_SIGNAL"
    AUTHENTICATION_ANOMALY = "AUTHENTICATION_ANOMALY"
    API_ANOMALY = "API_ANOMALY"
    PRIVILEGE_ESCALATION = "PRIVILEGE_ESCALATION"
    SERVICE_BOUNDARY_VIOLATION = "SERVICE_BOUNDARY_VIOLATION"
    RUNTIME_ANOMALY = "RUNTIME_ANOMALY"
    POTENTIAL_DATA_ACCESS = "POTENTIAL_DATA_ACCESS"
    THREAT_INCIDENT = "THREAT_INCIDENT"
    HUMAN_ESCALATION = "HUMAN_ESCALATION"


class SecurityResponseType(StrEnum):
    """Advisory response recommendations (strictly zero-automatic-financial-mutation)."""

    MONITOR = "MONITOR"
    INVESTIGATE = "INVESTIGATE"
    ESCALATE = "ESCALATE"
    ISOLATE_RECOMMENDED = "ISOLATE_RECOMMENDED"
    CREDENTIAL_ROTATION_RECOMMENDED = "CREDENTIAL_ROTATION_RECOMMENDED"
    ROLLBACK_RECOMMENDED = "ROLLBACK_RECOMMENDED"
    HUMAN_REVIEW_REQUIRED = "HUMAN_REVIEW_REQUIRED"


class ZeroTrustAuditEventType(StrEnum):
    """AuditLog event types for Phase 10H Zero-Trust operations."""

    ZERO_TRUST_EVENT = "ZERO_TRUST_EVENT"
    SERVICE_IDENTITY_VERIFIED = "SERVICE_IDENTITY_VERIFIED"
    SERVICE_AUTH_EVALUATED = "SERVICE_AUTH_EVALUATED"
    THREAT_INDICATOR_DETECTED = "THREAT_INDICATOR_DETECTED"
    ATTACK_CHAIN_CORRELATED = "ATTACK_CHAIN_CORRELATED"
    RUNTIME_POSTURE_EVALUATED = "RUNTIME_POSTURE_EVALUATED"
    SECRET_EXPOSURE_DETECTED = "SECRET_EXPOSURE_DETECTED"
    SECURITY_INCIDENT_CREATED = "SECURITY_INCIDENT_CREATED"
    SECURITY_INCIDENT_UPDATED = "SECURITY_INCIDENT_UPDATED"
    SECURITY_READINESS_EVALUATED = "SECURITY_READINESS_EVALUATED"
    SECURITY_REPORT_SIGNED = "SECURITY_REPORT_SIGNED"


# =============================================================================
# Phase 10I: FinOps, Cost Intelligence, Resource Governance, Unit Economics & Financial Efficiency Enums
# =============================================================================


class FinOpsHealth(StrEnum):
    """FinOps health score classification."""

    EXCELLENT = "EXCELLENT"
    GOOD = "GOOD"
    WARNING = "WARNING"
    DEGRADED = "DEGRADED"
    HIGH_RISK = "HIGH_RISK"
    CRITICAL = "CRITICAL"


class FinOpsGlobalState(StrEnum):
    """Global FinOps control plane state priority hierarchy."""

    EMERGENCY_COST_BREACH = "EMERGENCY_COST_BREACH"
    CRITICAL_FINOPS_FAILURE = "CRITICAL_FINOPS_FAILURE"
    BUDGET_EXHAUSTION = "BUDGET_EXHAUSTION"
    SEVERE_COST_ANOMALY = "SEVERE_COST_ANOMALY"
    FINOPS_DEGRADED = "FINOPS_DEGRADED"
    HIGH_COST_UTILIZATION = "HIGH_COST_UTILIZATION"
    OPTIMIZATION_REQUIRED = "OPTIMIZATION_REQUIRED"
    COST_WARNING = "COST_WARNING"
    MONITORING = "MONITORING"
    HEALTHY = "HEALTHY"


class FinOpsSeverity(StrEnum):
    """FinOps diagnostic and incident severity tiers."""

    INFO = "INFO"
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class CostCategory(StrEnum):
    """Infrastructure cost categories."""

    COMPUTE = "COMPUTE"
    DATABASE = "DATABASE"
    CACHE = "CACHE"
    STORAGE = "STORAGE"
    NETWORK = "NETWORK"
    WEBHOOK_PROCESSING = "WEBHOOK_PROCESSING"
    ML_INFERENCE = "ML_INFERENCE"
    QUEUE_PROCESSING = "QUEUE_PROCESSING"
    MONITORING = "MONITORING"
    EXTERNAL_APIS = "EXTERNAL_APIS"


class CostSource(StrEnum):
    """Origin of infrastructure cost telemetry."""

    AWS_ESTIMATED = "AWS_ESTIMATED"
    GCP_ESTIMATED = "GCP_ESTIMATED"
    OBSERVED_TELEMETRY = "OBSERVED_TELEMETRY"
    DERIVED_METRIC = "DERIVED_METRIC"
    SYNTHETIC_BENCHMARK = "SYNTHETIC_BENCHMARK"


class CostAllocationMethod(StrEnum):
    """Cost allocation methodology."""

    DIRECT_ATTRIBUTION = "DIRECT_ATTRIBUTION"
    PROPORTIONAL_USAGE = "PROPORTIONAL_USAGE"
    TAG_BASED = "TAG_BASED"
    HYBRID_EQUATION = "HYBRID_EQUATION"


class ResourceType(StrEnum):
    """Infrastructure resource types tracked by FinOps."""

    CPU = "CPU"
    MEMORY = "MEMORY"
    DATABASE_IOPS = "DATABASE_IOPS"
    DATABASE_STORAGE = "DATABASE_STORAGE"
    REDIS_MEMORY = "REDIS_MEMORY"
    QUEUE_CAPACITY = "QUEUE_CAPACITY"
    DISK_STORAGE = "DISK_STORAGE"
    EGRESS_BANDWIDTH = "EGRESS_BANDWIDTH"
    ML_GPU_COMPUTE = "ML_GPU_COMPUTE"
    WEBHOOK_WORKER_PODS = "WEBHOOK_WORKER_PODS"


class ResourceEfficiencyState(StrEnum):
    """Resource utilization and efficiency state."""

    OPTIMAL = "OPTIMAL"
    ACCEPTABLE = "ACCEPTABLE"
    UNDERUTILIZED = "UNDERUTILIZED"
    OVERPROVISIONED = "OVERPROVISIONED"
    SATURATED = "SATURATED"


class BudgetState(StrEnum):
    """Governance state of an active budget."""

    HEALTHY = "HEALTHY"
    WARNING = "WARNING"
    AT_RISK = "AT_RISK"
    BREACHED = "BREACHED"


class ForecastState(StrEnum):
    """Trajectory state of a cost forecast."""

    ON_TRACK = "ON_TRACK"
    SLIGHT_DEVIATION = "SLIGHT_DEVIATION"
    ELEVATED_GROWTH = "ELEVATED_GROWTH"
    CRITICAL_OVERRUN = "CRITICAL_OVERRUN"


class CostAnomalyType(StrEnum):
    """Types of detected cost anomalies."""

    SUDDEN_COST_SPIKE = "SUDDEN_COST_SPIKE"
    UNEXPECTED_SERVICE_GROWTH = "UNEXPECTED_SERVICE_GROWTH"
    DATABASE_COST_SPIKE = "DATABASE_COST_SPIKE"
    CACHE_COST_SPIKE = "CACHE_COST_SPIKE"
    ML_COST_SPIKE = "ML_COST_SPIKE"
    WEBHOOK_COST_SPIKE = "WEBHOOK_COST_SPIKE"
    NETWORK_COST_SPIKE = "NETWORK_COST_SPIKE"
    IDLE_RESOURCE_WASTE = "IDLE_RESOURCE_WASTE"
    UNDERUTILIZED_RESOURCE = "UNDERUTILIZED_RESOURCE"
    BUDGET_BURN_ACCELERATION = "BUDGET_BURN_ACCELERATION"
    FORECAST_DEVIATION = "FORECAST_DEVIATION"
    UNIT_COST_REGRESSION = "UNIT_COST_REGRESSION"


class CostAnomalySeverity(StrEnum):
    """Cost anomaly severity classifications."""

    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class OptimizationType(StrEnum):
    """Advisory resource optimization types."""

    RIGHTSIZE_COMPUTE = "RIGHTSIZE_COMPUTE"
    RIGHTSIZE_DATABASE = "RIGHTSIZE_DATABASE"
    RIGHTSIZE_CACHE = "RIGHTSIZE_CACHE"
    ADJUST_QUEUE_CAPACITY = "ADJUST_QUEUE_CAPACITY"
    OPTIMIZE_STORAGE = "OPTIMIZE_STORAGE"
    REDUCE_LOG_RETENTION = "REDUCE_LOG_RETENTION"
    OPTIMIZE_ML_INFERENCE = "OPTIMIZE_ML_INFERENCE"
    OPTIMIZE_WEBHOOK_WORKERS = "OPTIMIZE_WEBHOOK_WORKERS"
    OPTIMIZE_NETWORK_USAGE = "OPTIMIZE_NETWORK_USAGE"
    ADJUST_AUTOSCALING = "ADJUST_AUTOSCALING"


class OptimizationRisk(StrEnum):
    """Risk tier of executing an optimization."""

    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class OptimizationStatus(StrEnum):
    """Governance lifecycle status of an optimization recommendation."""

    IDENTIFIED = "IDENTIFIED"
    RECOMMENDED = "RECOMMENDED"
    UNDER_REVIEW = "UNDER_REVIEW"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    IMPLEMENTED_EXTERNALLY = "IMPLEMENTED_EXTERNALLY"


class UnitEconomicsMetric(StrEnum):
    """Unit economics financial efficiency metrics."""

    COST_PER_TRANSACTION = "COST_PER_TRANSACTION"
    COST_PER_RECOVERY_CASE = "COST_PER_RECOVERY_CASE"
    COST_PER_ML_PREDICTION = "COST_PER_ML_PREDICTION"
    COST_PER_WEBHOOK = "COST_PER_WEBHOOK"
    COST_PER_1K_REQUESTS = "COST_PER_1K_REQUESTS"
    RECOVERY_INTELLIGENCE_VALUE_EFFICIENCY = "RECOVERY_INTELLIGENCE_VALUE_EFFICIENCY"


class FinOpsIncidentType(StrEnum):
    """FinOps incident classifications."""

    BUDGET_BREACH = "BUDGET_BREACH"
    COST_ANOMALY = "COST_ANOMALY"
    UNIT_COST_REGRESSION = "UNIT_COST_REGRESSION"
    RESOURCE_WASTE = "RESOURCE_WASTE"
    FORECAST_OVERRUN = "FORECAST_OVERRUN"
    ML_COST_SPIKE = "ML_COST_SPIKE"
    DATABASE_COST_SPIKE = "DATABASE_COST_SPIKE"
    CAPACITY_COST_MISMATCH = "CAPACITY_COST_MISMATCH"


class FinOpsIncidentStatus(StrEnum):
    """FinOps incident operational status."""

    DETECTED = "DETECTED"
    ACKNOWLEDGED = "ACKNOWLEDGED"
    ESCALATED = "ESCALATED"
    MITIGATING = "MITIGATING"
    RESOLVED = "RESOLVED"


class FinOpsAuditEventType(StrEnum):
    """AuditLog event types for Phase 10I FinOps operations."""

    FINOPS_SNAPSHOT = "FINOPS_SNAPSHOT"
    COST_ANOMALY_DETECTED = "COST_ANOMALY_DETECTED"
    BUDGET_THRESHOLD_BREACHED = "BUDGET_THRESHOLD_BREACHED"
    OPTIMIZATION_RECOMMENDED = "OPTIMIZATION_RECOMMENDED"
    OPTIMIZATION_APPROVED = "OPTIMIZATION_APPROVED"
    OPTIMIZATION_REJECTED = "OPTIMIZATION_REJECTED"
    FINOPS_INCIDENT_CREATED = "FINOPS_INCIDENT_CREATED"
    FINOPS_INCIDENT_UPDATED = "FINOPS_INCIDENT_UPDATED"
    FINOPS_READINESS_EVALUATED = "FINOPS_READINESS_EVALUATED"
    FINOPS_REPORT_GENERATED = "FINOPS_REPORT_GENERATED"


class FinOpsGateId(StrEnum):
    """Identifiers for the 20 FinOps Readiness Gates."""

    GATE_FIN_01 = "GATE-FIN-01"
    GATE_FIN_02 = "GATE-FIN-02"
    GATE_FIN_03 = "GATE-FIN-03"
    GATE_FIN_04 = "GATE-FIN-04"
    GATE_FIN_05 = "GATE-FIN-05"
    GATE_FIN_06 = "GATE-FIN-06"
    GATE_FIN_07 = "GATE-FIN-07"
    GATE_FIN_08 = "GATE-FIN-08"
    GATE_FIN_09 = "GATE-FIN-09"
    GATE_FIN_10 = "GATE-FIN-10"
    GATE_FIN_11 = "GATE-FIN-11"
    GATE_FIN_12 = "GATE-FIN-12"
    GATE_FIN_13 = "GATE-FIN-13"
    GATE_FIN_14 = "GATE-FIN-14"
    GATE_FIN_15 = "GATE-FIN-15"
    GATE_FIN_16 = "GATE-FIN-16"
    GATE_FIN_17 = "GATE-FIN-17"
    GATE_FIN_18 = "GATE-FIN-18"
    GATE_FIN_19 = "GATE-FIN-19"
    GATE_FIN_20 = "GATE-FIN-20"


class FinOpsGateStatus(StrEnum):
    """FinOps readiness gate status."""

    PASS = "PASS"
    WARN = "WARN"
    FAIL = "FAIL"
    BLOCKED = "BLOCKED"


# ============================================================================
# Phase 10J: AI/ML Governance, Model Risk Management, Explainability,
# Drift Detection & Responsible AI Control Plane Enums
# ============================================================================


class MLGovernanceHealth(StrEnum):
    """Health classification for ML governance score."""

    EXCELLENT = "EXCELLENT"
    GOOD = "GOOD"
    WARNING = "WARNING"
    DEGRADED = "DEGRADED"
    HIGH_RISK = "HIGH_RISK"
    CRITICAL = "CRITICAL"


class MLGlobalState(StrEnum):
    """Deterministic global ML state hierarchy."""

    EMERGENCY_MODEL_RISK = "EMERGENCY_MODEL_RISK"
    MODEL_GOVERNANCE_CRITICAL = "MODEL_GOVERNANCE_CRITICAL"
    SEVERE_MODEL_DRIFT = "SEVERE_MODEL_DRIFT"
    MODEL_PERFORMANCE_FAILURE = "MODEL_PERFORMANCE_FAILURE"
    HIGH_MODEL_RISK = "HIGH_MODEL_RISK"
    BIAS_WARNING = "BIAS_WARNING"
    CALIBRATION_WARNING = "CALIBRATION_WARNING"
    DRIFT_WARNING = "DRIFT_WARNING"
    MONITORING = "MONITORING"
    HEALTHY = "HEALTHY"
    # Backward compatible aliases
    EMERGENCY_MODEL_SHUTDOWN = "EMERGENCY_MODEL_SHUTDOWN"
    CRITICAL_ML_FAILURE = "CRITICAL_ML_FAILURE"
    KILL_SWITCH_ACTIVE = "KILL_SWITCH_ACTIVE"
    PROMOTION_BLOCKED = "PROMOTION_BLOCKED"
    EVALUATION_FAILED = "EVALUATION_FAILED"
    FAIRNESS_ALERT = "FAIRNESS_ALERT"
    DRIFT_DETECTED = "DRIFT_DETECTED"
    RETRAINING_RECOMMENDED = "RETRAINING_RECOMMENDED"


class ModelLifecycleState(StrEnum):
    """Model version lifecycle states."""

    REGISTERED = "REGISTERED"
    VALIDATING = "VALIDATING"
    APPROVED = "APPROVED"
    PRODUCTION = "PRODUCTION"
    DEPRECATED = "DEPRECATED"
    RETIRED = "RETIRED"
    BLOCKED = "BLOCKED"
    DEVELOPMENT = "DEVELOPMENT"
    VALIDATION = "VALIDATION"
    STAGING = "STAGING"
    SHADOW = "SHADOW"


class ModelRiskLevel(StrEnum):
    """Risk severity classifications."""

    LOW = "LOW"
    MODERATE = "MODERATE"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class ModelHealth(StrEnum):
    """Operational and evaluation model health."""

    EXCELLENT = "EXCELLENT"
    GOOD = "GOOD"
    FAIR = "FAIR"
    WARNING = "WARNING"
    DEGRADED = "DEGRADED"
    CRITICAL = "CRITICAL"


class DriftStatus(StrEnum):
    """Classification of drift severity."""

    STABLE = "STABLE"
    WARNING = "WARNING"
    DETECTED = "DETECTED"
    SEVERE = "SEVERE"
    UNKNOWN = "UNKNOWN"
    NO_DRIFT = "no_drift"
    NEGLIGIBLE_DRIFT = "negligible_drift"
    MODERATE_DRIFT = "moderate_drift"
    SEVERE_DRIFT = "severe_drift"


class DriftType(StrEnum):
    """Category of statistical drift."""

    DATA_DRIFT = "DATA_DRIFT"
    CONCEPT_DRIFT = "CONCEPT_DRIFT"
    PREDICTION_DRIFT = "PREDICTION_DRIFT"
    FEATURE_DRIFT = "FEATURE_DRIFT"
    LABEL_DRIFT = "LABEL_DRIFT"
    COVARIATE_SHIFT = "COVARIATE_SHIFT"


class ExplainabilityStatus(StrEnum):
    """Explainability generation status."""

    COMPLETE = "COMPLETE"
    PARTIAL = "PARTIAL"
    FAILED = "FAILED"
    UNAVAILABLE = "UNAVAILABLE"
    EXPLAINED = "EXPLAINED"
    UNEXPLAINED = "UNEXPLAINED"


class BiasStatus(StrEnum):
    """Fairness and bias assessment status."""

    FAIR = "FAIR"
    WARNING = "WARNING"
    BIASED = "BIASED"
    UNKNOWN = "UNKNOWN"
    UNBIASED = "UNBIASED"
    LOW_BIAS = "LOW_BIAS"
    MODERATE_BIAS = "MODERATE_BIAS"
    HIGH_BIAS = "HIGH_BIAS"
    CRITICAL_BIAS = "CRITICAL_BIAS"


class CalibrationStatus(StrEnum):
    """Model probability calibration health status."""

    CALIBRATED = "CALIBRATED"
    WARNING = "WARNING"
    MIS_CALIBRATED = "MIS_CALIBRATED"
    UNKNOWN = "UNKNOWN"
    WELL_CALIBRATED = "WELL_CALIBRATED"
    MODERATE_MISCALIBRATION = "MODERATE_MISCALIBRATION"
    SEVERE_MISCALIBRATION = "SEVERE_MISCALIBRATION"


class ModelApprovalStatus(StrEnum):
    """Status for model version approval workflow."""

    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    EXPIRED = "EXPIRED"
    REVOKED = "REVOKED"
    PENDING_APPROVAL = "PENDING_APPROVAL"
    CONDITIONALLY_APPROVED = "CONDITIONALLY_APPROVED"


class MLIncidentSeverity(StrEnum):
    """Severity classification for ML incidents."""

    SEV_1 = "SEV_1"
    SEV_2 = "SEV_2"
    SEV_3 = "SEV_3"
    SEV_4 = "SEV_4"
    P1_CRITICAL = "P1_CRITICAL"
    P2_HIGH = "P2_HIGH"
    P3_MEDIUM = "P3_MEDIUM"
    P4_LOW = "P4_LOW"


class MLIncidentStatus(StrEnum):
    """Lifecycle status of ML governance incident."""

    DETECTED = "DETECTED"
    ACKNOWLEDGED = "ACKNOWLEDGED"
    INVESTIGATING = "INVESTIGATING"
    MITIGATING = "MITIGATING"
    RESOLVED = "RESOLVED"
    CLOSED = "CLOSED"
    TRIGGERED = "TRIGGERED"
    MITIGATED = "MITIGATED"
    SUPPRESSED = "SUPPRESSED"


class ModelEvaluationType(StrEnum):
    """Evaluation methodology types."""

    OFFLINE = "OFFLINE"
    ONLINE = "ONLINE"
    SHADOW = "SHADOW"
    CANARY = "CANARY"
    REGRESSION = "REGRESSION"
    DRIFT = "DRIFT"
    FAIRNESS = "FAIRNESS"
    CALIBRATION = "CALIBRATION"
    BENCHMARK = "BENCHMARK"


class ModelRiskCategory(StrEnum):
    """Risk domain categories for MRM."""

    PERFORMANCE = "PERFORMANCE"
    DATA = "DATA"
    DRIFT = "DRIFT"
    FAIRNESS = "FAIRNESS"
    EXPLAINABILITY = "EXPLAINABILITY"
    SECURITY = "SECURITY"
    GOVERNANCE = "GOVERNANCE"
    FINANCIAL = "FINANCIAL"
    OPERATIONAL = "OPERATIONAL"
    HUMAN = "HUMAN"
    FINANCIAL_INTEGRITY = "FINANCIAL_INTEGRITY"
    FAIRNESS_AND_BIAS = "FAIRNESS_AND_BIAS"
    DRIFT_AND_DEGRADATION = "DRIFT_AND_DEGRADATION"
    SECURITY_AND_EXPLOIT = "SECURITY_AND_EXPLOIT"
    COMPLIANCE_AND_LEGAL = "COMPLIANCE_AND_LEGAL"


MLAuditEventType = ModelAuditEventType


class MLGateId(StrEnum):
    """Identifiers for 22 Deterministic ML Readiness Gates."""

    GATE_ML_01 = "GATE-ML-01"
    GATE_ML_02 = "GATE-ML-02"
    GATE_ML_03 = "GATE-ML-03"
    GATE_ML_04 = "GATE-ML-04"
    GATE_ML_05 = "GATE-ML-05"
    GATE_ML_06 = "GATE-ML-06"
    GATE_ML_07 = "GATE-ML-07"
    GATE_ML_08 = "GATE-ML-08"
    GATE_ML_09 = "GATE-ML-09"
    GATE_ML_10 = "GATE-ML-10"
    GATE_ML_11 = "GATE-ML-11"
    GATE_ML_12 = "GATE-ML-12"
    GATE_ML_13 = "GATE-ML-13"
    GATE_ML_14 = "GATE-ML-14"
    GATE_ML_15 = "GATE-ML-15"
    GATE_ML_16 = "GATE-ML-16"
    GATE_ML_17 = "GATE-ML-17"
    GATE_ML_18 = "GATE-ML-18"
    GATE_ML_19 = "GATE-ML-19"
    GATE_ML_20 = "GATE-ML-20"
    GATE_ML_21 = "GATE-ML-21"
    GATE_ML_22 = "GATE-ML-22"


class MLGateStatus(StrEnum):
    """ML readiness gate status."""

    PASS = "PASS"
    WARN = "WARN"
    FAIL = "FAIL"
    BLOCKED = "BLOCKED"


class PromotionRecommendation(StrEnum):
    """Advisory promotion recommendations."""

    PROMOTE_RECOMMENDED = "PROMOTE_RECOMMENDED"
    CONDITIONAL = "CONDITIONAL"
    HOLD = "HOLD"
    BLOCKED = "BLOCKED"
    RECOMMENDED = "RECOMMENDED"
    NOT_RECOMMENDED = "NOT_RECOMMENDED"
    REQUIRES_ADDITIONAL_EVALUATION = "REQUIRES_ADDITIONAL_EVALUATION"


class RollbackReadinessStatus(StrEnum):
    """Status of rollback readiness mechanism."""

    READY = "READY"
    CONDITIONAL = "CONDITIONAL"
    NOT_READY = "NOT_READY"
    DEGRADED = "DEGRADED"
    BLOCKED = "BLOCKED"


# Legacy / Support Enums
class ModelTier(StrEnum):
    """Criticality tier of ML models."""

    TIER_1_MISSION_CRITICAL = "tier_1_mission_critical"
    TIER_2_HIGH_IMPACT = "tier_2_high_impact"
    TIER_3_OPERATIONAL = "tier_3_operational"
    TIER_4_EXPERIMENTAL = "tier_4_experimental"


class OperationalStatus(StrEnum):
    """Operational status of ML model."""

    ACTIVE = "active"
    SHADOW = "shadow"
    CANARY = "canary"
    STANDBY = "standby"
    DISABLED = "disabled"
    DEPRECATED = "deprecated"


class GovernanceStage(StrEnum):
    """Governance lifecycle stage."""

    DEVELOPMENT = "development"
    STAGING = "staging"
    SHADOW = "shadow"
    PRODUCTION = "production"
    ARCHIVED = "archived"


class ArtifactStorageType(StrEnum):
    """Storage backing for model artifacts."""

    LOCAL_STORE = "local_store"
    S3_COMPLIANT = "s3_compliant"
    GCS_COMPLIANT = "gcs_compliant"
    REGISTRY = "registry"


class EvaluationType(StrEnum):
    """Type of model evaluation."""

    OFFLINE_VALIDATION = "offline_validation"
    ONLINE_METRICS = "online_metrics"
    SHADOW_COMPARISON = "shadow_comparison"
    CROSS_VALIDATION = "cross_validation"
    STRESS_TEST = "stress_test"


class FairnessMetricType(StrEnum):
    """Fairness and bias metric dimensions."""

    DISPARATE_IMPACT = "disparate_impact"
    DEMOGRAPHIC_PARITY = "demographic_parity"
    EQUAL_OPPORTUNITY = "equal_opportunity"
    FALSE_POSITIVE_PARITY = "false_positive_parity"
    PREDICTIVE_PARITY = "predictive_parity"


class DriftMetricType(StrEnum):
    """Statistical metric used for drift calculation."""

    PSI = "psi"
    KS_TEST = "ks_test"
    WASSERSTEIN_DISTANCE = "wasserstein_distance"
    JENSEN_SHANNON = "jensen_shannon"
    CRAMER_V = "cramer_v"


class PromotionStatus(StrEnum):
    """Status of model promotion request."""

    PENDING_REVIEW = "pending_review"
    APPROVED = "approved"
    REJECTED = "rejected"
    SUPERSEDED = "superseded"
    ROLLED_BACK = "rolled_back"


class PromotionRisk(StrEnum):
    """Assessed risk of model promotion."""

    MINIMAL = "minimal"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class KillSwitchState(StrEnum):
    """State of model kill switch."""

    ACTIVE = "active"
    INACTIVE = "inactive"
    ARMED = "armed"
    DISABLED = "disabled"


class ComplianceFramework(StrEnum):
    """AI regulatory compliance framework."""

    EU_AI_ACT = "eu_ai_act"
    NIST_AI_RMF = "nist_ai_rmf"
    RBI_FAIR_LENDING = "rbi_fair_lending"
    ISO_42001 = "iso_42001"
    SOC2_TYPE_II = "soc2_type_ii"


class MLIncidentAction(StrEnum):
    """Actions applicable to ML incidents."""

    ACKNOWLEDGE = "acknowledge"
    INVESTIGATE = "investigate"
    MITIGATE = "mitigate"
    RESOLVE = "resolve"
    SUPPRESS = "suppress"
