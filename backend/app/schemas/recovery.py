import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

# =========================================================================
# Metrics Schemas
# =========================================================================


class CasesMetric(BaseModel):
    """Aggregate counts for recovery cases across statuses."""

    model_config = ConfigDict(frozen=True)

    total: int = Field(ge=0, description="Total lifetime recovery cases")
    active: int = Field(ge=0, description="Currently active (open/in-recovery) cases")
    recovered: int = Field(ge=0, description="Fully resolved/recovered cases")
    closed: int = Field(ge=0, description="Closed without recovery")


class FinancialMetric(BaseModel):
    """Financial totals in integer paise and computed recovery percentage."""

    model_config = ConfigDict(frozen=True)

    amount_at_risk: int = Field(ge=0, description="Total amount at risk in paise")
    amount_recovered: int = Field(ge=0, description="Total amount recovered in paise")
    recovery_rate_pct: float = Field(
        ge=0.0, le=100.0, description="Recovery rate percentage"
    )
    currency: str = Field(default="INR", description="Currency code")


class ActionsMetric(BaseModel):
    """Counts of recovery actions across lifecycle states."""

    model_config = ConfigDict(frozen=True)

    scheduled: int = Field(ge=0, description="Actions scheduled for future execution")
    executing: int = Field(ge=0, description="Actions currently executing")
    completed: int = Field(ge=0, description="Actions successfully completed")
    failed: int = Field(ge=0, description="Actions that failed execution")
    timed_out: int = Field(
        ge=0, description="Actions that timed out and await reconciliation"
    )
    total: int = Field(ge=0, description="Total actions recorded")


class PolicyMetric(BaseModel):
    """Counts of deterministic policy engine outcomes."""

    model_config = ConfigDict(frozen=True)

    allowed: int = Field(ge=0, description="Policy decisions approved for action")
    blocked: int = Field(ge=0, description="Policy decisions blocked by safety rules")
    human_review: int = Field(
        ge=0, description="Policy decisions queued for human review"
    )
    total: int = Field(ge=0, description="Total policy evaluations evaluated")
    clearance_rate_pct: float = Field(
        ge=0.0, le=100.0, description="Percentage of policy evaluations allowed"
    )


class WorkerTelemetrySummary(BaseModel):
    """Sanitized background worker health snapshot."""

    model_config = ConfigDict(frozen=True)

    status: str = Field(description="Operational status of background worker")
    queue_depth: int = Field(ge=0, description="Number of due actions in queue")
    actions_claimed: int = Field(ge=0, description="Total actions claimed by worker")
    actions_completed: int = Field(
        ge=0, description="Total actions completed by worker"
    )
    actions_failed: int = Field(
        ge=0, description="Total actions failed during execution"
    )
    reconciliation_runs: int = Field(
        ge=0, description="Total reconciliation sweeps run"
    )
    last_poll_at: datetime | None = Field(default=None)
    last_reconciliation_at: datetime | None = Field(default=None)


class BreakdownItem(BaseModel):
    """Generic category count item for distribution charts."""

    model_config = ConfigDict(frozen=True)

    category: str
    count: int = Field(ge=0)
    percentage: float = Field(ge=0.0, le=100.0)


class RecentAuditActivityItem(BaseModel):
    """Sanitized audit log item for dashboard activity feed."""

    model_config = ConfigDict(frozen=True)

    id: int
    event_type: str
    actor_type: str
    actor_id: str
    case_id: uuid.UUID | None = None
    action: str
    created_at: datetime


class RecoveryMetricsResponse(BaseModel):
    """Top-level strictly-typed metrics payload for the RecoverIQ Dashboard."""

    model_config = ConfigDict(frozen=True)

    cases: CasesMetric
    financial: FinancialMetric
    actions: ActionsMetric
    policy: PolicyMetric
    worker: WorkerTelemetrySummary
    failure_reasons: list[BreakdownItem] = Field(default_factory=list)
    action_types: list[BreakdownItem] = Field(default_factory=list)
    recent_activity: list[RecentAuditActivityItem] = Field(default_factory=list)


# =========================================================================
# Case & Action Listing Schemas
# =========================================================================


class RecoveryCaseListItem(BaseModel):
    """Sanitized summary row for recovery case tables."""

    model_config = ConfigDict(frozen=True)

    id: uuid.UUID
    payment_id: uuid.UUID
    customer_id: uuid.UUID
    status: str
    recovery_stage: str
    amount_at_risk: int = Field(ge=0)
    recovered_amount: int = Field(ge=0)
    total_attempts_count: int = Field(ge=0)
    max_allowed_attempts: int = Field(ge=1)
    latest_failure_reason: str | None = None
    opened_at: datetime
    next_action_due_at: datetime | None = None
    resolved_at: datetime | None = None
    closed_reason: str | None = None
    ai_proposed_action: str | None = None
    ai_confidence_score: float | None = None
    latest_policy_result: str | None = None
    latest_action_status: str | None = None
    created_at: datetime
    updated_at: datetime


class PaginatedRecoveryCasesResponse(BaseModel):
    """Paginated collection of recovery cases."""

    model_config = ConfigDict(frozen=True)

    items: list[RecoveryCaseListItem]
    total: int = Field(ge=0)
    page: int = Field(ge=1)
    page_size: int = Field(ge=1)
    total_pages: int = Field(ge=0)


# =========================================================================
# Case Detail Schemas
# =========================================================================


class PaymentSummary(BaseModel):
    """Safe payment metadata excluding raw cards or credentials."""

    model_config = ConfigDict(frozen=True)

    id: uuid.UUID
    razorpay_order_id: str | None = None
    razorpay_invoice_id: str | None = None
    amount: int
    currency: str
    status: str
    due_date: datetime | None = None
    captured_at: datetime | None = None
    created_at: datetime


class CustomerSummary(BaseModel):
    """Zero-PII customer metrics and risk tier."""

    model_config = ConfigDict(frozen=True)

    id: uuid.UUID
    external_customer_id: str
    risk_tier: str
    total_payments_count: int
    failed_payments_count: int
    recovered_payments_count: int


class MLPredictionSummary(BaseModel):
    """Summary of ML recovery prediction."""

    model_config = ConfigDict(frozen=True)

    id: uuid.UUID
    model_name: str
    model_version: str
    recovery_probability: float
    risk_score: float
    confidence: float
    priority: str
    predicted_channel: str | None = None
    predicted_delay_hours: int | None = None
    predicted_at: datetime


class AgentDecisionSummary(BaseModel):
    """Summary of AI recovery recommendation."""

    model_config = ConfigDict(frozen=True)

    id: uuid.UUID
    proposed_action_type: str
    confidence_score: float
    reasoning_summary: str
    recommended_delay_hours: int
    agent_name: str
    agent_version: str
    decided_at: datetime


class PolicyDecisionSummary(BaseModel):
    """Summary of deterministic policy evaluation."""

    model_config = ConfigDict(frozen=True)

    id: uuid.UUID
    agent_decision_id: uuid.UUID | None = None
    evaluation_result: str
    policy_engine_version: str
    triggered_rule_code: str | None = None
    rule_name: str | None = None
    decision_reason: str
    decided_at: datetime


class ActionResultSummary(BaseModel):
    """Summary of action execution provider result."""

    model_config = ConfigDict(frozen=True)

    id: uuid.UUID
    execution_status: str
    provider_reference_id: str | None = None
    provider_status_code: str | None = None
    failure_reason: str | None = None
    executed_at: datetime


class RecoveryActionSummary(BaseModel):
    """Summary of scheduled / executed recovery action."""

    model_config = ConfigDict(frozen=True)

    id: uuid.UUID
    policy_decision_id: uuid.UUID
    action_type: str
    status: str
    scheduled_for: datetime
    dispatched_at: datetime | None = None
    completed_at: datetime | None = None
    created_at: datetime
    results: list[ActionResultSummary] = Field(default_factory=list)


class AuditLogSummary(BaseModel):
    """Sanitized audit log entry."""

    model_config = ConfigDict(frozen=True)

    id: int
    event_type: str
    actor_type: str
    actor_id: str
    entity_type: str
    entity_id: uuid.UUID | None = None
    action: str
    previous_state: dict[str, Any] | None = None
    new_state: dict[str, Any] | None = None
    metadata_json: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime


class RecoveryCaseDetailResponse(BaseModel):
    """Full detail view of a single recovery case and its complete lifecycle trail."""

    model_config = ConfigDict(frozen=True)

    case: RecoveryCaseListItem
    payment: PaymentSummary
    customer: CustomerSummary
    predictions: list[MLPredictionSummary] = Field(default_factory=list)
    agent_decisions: list[AgentDecisionSummary] = Field(default_factory=list)
    policy_decisions: list[PolicyDecisionSummary] = Field(default_factory=list)
    actions: list[RecoveryActionSummary] = Field(default_factory=list)
    audit_logs: list[AuditLogSummary] = Field(default_factory=list)


# =========================================================================
# Human Review Schemas
# =========================================================================


class HumanReviewQueueItem(BaseModel):
    """Queue item requiring operator approval or dismissal."""

    model_config = ConfigDict(frozen=True)

    case_id: uuid.UUID
    payment_id: uuid.UUID
    customer_id: uuid.UUID
    customer_risk_tier: str
    amount_at_risk: int
    currency: str
    case_status: str
    recovery_stage: str
    latest_failure_reason: str | None = None
    previous_attempts_count: int
    policy_decision_id: uuid.UUID
    triggered_rule_code: str | None = None
    rule_name: str | None = None
    policy_decision_reason: str
    agent_decision_id: uuid.UUID | None = None
    proposed_action_type: str | None = None
    ai_confidence_score: float | None = None
    ai_reasoning_summary: str | None = None
    opened_at: datetime
    decided_at: datetime


class PaginatedHumanReviewResponse(BaseModel):
    """Paginated collection of cases pending human review."""

    model_config = ConfigDict(frozen=True)

    items: list[HumanReviewQueueItem]
    total: int = Field(ge=0)
    page: int = Field(ge=1)
    page_size: int = Field(ge=1)
    total_pages: int = Field(ge=0)


class HumanReviewActionRequest(BaseModel):
    """Operator approval or dismissal payload. Operator identity is derived authoritatively from auth token."""

    model_config = ConfigDict(frozen=True)

    operator_id: str | None = Field(
        default=None,
        max_length=64,
        description="Non-authoritative client hint. Overridden by authenticated token identity.",
    )
    notes: str | None = Field(
        default=None,
        max_length=1000,
        description="Justification notes for the review decision.",
    )


class HumanReviewActionResponse(BaseModel):
    """Outcome of human approval or dismissal."""

    model_config = ConfigDict(frozen=True)

    success: bool
    case_id: uuid.UUID
    action: str = Field(description="APPROVED or DISMISSED")
    scheduled_action_id: uuid.UUID | None = None
    message: str
    timestamp: datetime


# =========================================================================
# Audit Log Listing Schemas
# =========================================================================


class PaginatedAuditLogsResponse(BaseModel):
    """Paginated collection of audit log entries."""

    model_config = ConfigDict(frozen=True)

    items: list[AuditLogSummary]
    total: int = Field(ge=0)
    page: int = Field(ge=1)
    page_size: int = Field(ge=1)
    total_pages: int = Field(ge=0)
