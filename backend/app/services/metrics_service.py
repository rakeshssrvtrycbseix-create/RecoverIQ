import logging
import math
import uuid
from datetime import UTC, datetime

from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from app.models import (
    ActionResult,
    AgentDecision,
    AuditActorType,
    AuditLog,
    Customer,
    MLPrediction,
    Payment,
    PolicyDecision,
    PolicyEvaluationResult,
    RecoveryAction,
    RecoveryActionStatus,
    RecoveryCase,
    RecoveryCaseStatus,
)
from app.schemas.recovery import (
    ActionResultSummary,
    ActionsMetric,
    AgentDecisionSummary,
    AuditLogSummary,
    BreakdownItem,
    CasesMetric,
    CustomerSummary,
    FinancialMetric,
    HumanReviewActionResponse,
    HumanReviewQueueItem,
    MLPredictionSummary,
    PaginatedAuditLogsResponse,
    PaginatedHumanReviewResponse,
    PaginatedRecoveryCasesResponse,
    PaymentSummary,
    PolicyDecisionSummary,
    PolicyMetric,
    RecentAuditActivityItem,
    RecoveryActionSummary,
    RecoveryCaseDetailResponse,
    RecoveryCaseListItem,
    RecoveryMetricsResponse,
    WorkerTelemetrySummary,
)
from app.services.action_scheduler import action_scheduler
from app.workers.telemetry import worker_telemetry

logger = logging.getLogger(__name__)

ACTIVE_CASE_STATUSES = {
    RecoveryCaseStatus.OPEN.value,
    RecoveryCaseStatus.ANALYZING.value,
    RecoveryCaseStatus.ACTION_PENDING.value,
    RecoveryCaseStatus.IN_RECOVERY.value,
    RecoveryCaseStatus.ESCALATED_HUMAN.value,
}

TERMINAL_CASE_STATUSES = {
    RecoveryCaseStatus.RECOVERED.value,
    RecoveryCaseStatus.CLOSED.value,
}


class MetricsServiceError(Exception):
    """Base exception for metrics and dashboard operations."""


class CaseNotFoundError(MetricsServiceError):
    """Raised when a recovery case is not found."""


class ReviewNotEligibleError(MetricsServiceError):
    """Raised when a case is not eligible for human review actions."""


class RecoveryMetricsService:
    """Service providing aggregate analytics, case visibility, and human review operations."""

    def get_dashboard_metrics(self, db: Session) -> RecoveryMetricsResponse:
        """Compute aggregated operational, financial, and worker metrics."""
        # 1. Cases Metrics
        total_cases = db.query(func.count(RecoveryCase.id)).scalar() or 0
        active_cases = (
            db.query(func.count(RecoveryCase.id))
            .filter(RecoveryCase.status.in_(ACTIVE_CASE_STATUSES))
            .scalar()
            or 0
        )
        recovered_cases = (
            db.query(func.count(RecoveryCase.id))
            .filter(RecoveryCase.status == RecoveryCaseStatus.RECOVERED.value)
            .scalar()
            or 0
        )
        closed_cases = (
            db.query(func.count(RecoveryCase.id))
            .filter(RecoveryCase.status == RecoveryCaseStatus.CLOSED.value)
            .scalar()
            or 0
        )

        # 2. Financial Metrics (integer paise)
        amount_at_risk = db.query(func.sum(RecoveryCase.amount_at_risk)).scalar() or 0
        amount_recovered = (
            db.query(func.sum(RecoveryCase.recovered_amount)).scalar() or 0
        )
        recovery_rate = (
            round((amount_recovered / amount_at_risk) * 100.0, 2)
            if amount_at_risk > 0
            else 0.0
        )

        # 3. Actions Metrics
        scheduled_actions = (
            db.query(func.count(RecoveryAction.id))
            .filter(RecoveryAction.status == RecoveryActionStatus.SCHEDULED.value)
            .scalar()
            or 0
        )
        executing_actions = (
            db.query(func.count(RecoveryAction.id))
            .filter(RecoveryAction.status == RecoveryActionStatus.EXECUTING.value)
            .scalar()
            or 0
        )
        completed_actions = (
            db.query(func.count(RecoveryAction.id))
            .filter(RecoveryAction.status == RecoveryActionStatus.COMPLETED.value)
            .scalar()
            or 0
        )
        failed_actions = (
            db.query(func.count(RecoveryAction.id))
            .filter(RecoveryAction.status == RecoveryActionStatus.FAILED.value)
            .scalar()
            or 0
        )
        timed_out_actions = (
            db.query(func.count(ActionResult.id))
            .filter(ActionResult.execution_status == "TIMED_OUT")
            .scalar()
            or 0
        )
        total_actions = db.query(func.count(RecoveryAction.id)).scalar() or 0

        # 4. Policy Metrics
        allowed_decisions = (
            db.query(func.count(PolicyDecision.id))
            .filter(
                PolicyDecision.evaluation_result == PolicyEvaluationResult.ALLOWED.value
            )
            .scalar()
            or 0
        )
        blocked_decisions = (
            db.query(func.count(PolicyDecision.id))
            .filter(
                PolicyDecision.evaluation_result == PolicyEvaluationResult.BLOCKED.value
            )
            .scalar()
            or 0
        )
        human_review_decisions = (
            db.query(func.count(PolicyDecision.id))
            .filter(
                PolicyDecision.evaluation_result
                == PolicyEvaluationResult.HUMAN_REVIEW.value
            )
            .scalar()
            or 0
        )
        total_policy = db.query(func.count(PolicyDecision.id)).scalar() or 0
        clearance_rate = (
            round((allowed_decisions / total_policy) * 100.0, 2)
            if total_policy > 0
            else 0.0
        )

        # 5. Worker Telemetry
        telemetry_snap = worker_telemetry.get_snapshot()
        worker_summary = WorkerTelemetrySummary(
            status=telemetry_snap.worker_status,
            queue_depth=telemetry_snap.queue_depth,
            actions_claimed=telemetry_snap.actions_claimed,
            actions_completed=telemetry_snap.actions_completed,
            actions_failed=telemetry_snap.actions_failed,
            reconciliation_runs=telemetry_snap.reconciliation_runs,
            last_poll_at=telemetry_snap.last_poll_at,
            last_reconciliation_at=telemetry_snap.last_reconciliation_at,
        )

        # 6. Failure Reasons Distribution
        raw_failure_reasons = (
            db.query(
                RecoveryCase.latest_failure_reason,
                func.count(RecoveryCase.id).label("count"),
            )
            .group_by(RecoveryCase.latest_failure_reason)
            .all()
        )
        failure_reasons: list[BreakdownItem] = []
        for reason, count in raw_failure_reasons:
            cat = reason or "unknown"
            pct = round((count / total_cases) * 100.0, 2) if total_cases > 0 else 0.0
            failure_reasons.append(
                BreakdownItem(category=cat, count=count, percentage=pct)
            )

        # 7. Action Types Distribution
        raw_action_types = (
            db.query(
                RecoveryAction.action_type,
                func.count(RecoveryAction.id).label("count"),
            )
            .group_by(RecoveryAction.action_type)
            .all()
        )
        action_types: list[BreakdownItem] = []
        for act_type, count in raw_action_types:
            pct = (
                round((count / total_actions) * 100.0, 2) if total_actions > 0 else 0.0
            )
            action_types.append(
                BreakdownItem(category=act_type, count=count, percentage=pct)
            )

        # 8. Recent Audit Activity
        recent_audits = (
            db.query(AuditLog).order_by(AuditLog.created_at.desc()).limit(10).all()
        )
        recent_activity = [
            RecentAuditActivityItem(
                id=a.id,
                event_type=a.event_type,
                actor_type=a.actor_type,
                actor_id=a.actor_id,
                case_id=a.recovery_case_id,
                action=a.action,
                created_at=a.created_at,
            )
            for a in recent_audits
        ]

        return RecoveryMetricsResponse(
            cases=CasesMetric(
                total=total_cases,
                active=active_cases,
                recovered=recovered_cases,
                closed=closed_cases,
            ),
            financial=FinancialMetric(
                amount_at_risk=amount_at_risk,
                amount_recovered=amount_recovered,
                recovery_rate_pct=recovery_rate,
                currency="INR",
            ),
            actions=ActionsMetric(
                scheduled=scheduled_actions,
                executing=executing_actions,
                completed=completed_actions,
                failed=failed_actions,
                timed_out=timed_out_actions,
                total=total_actions,
            ),
            policy=PolicyMetric(
                allowed=allowed_decisions,
                blocked=blocked_decisions,
                human_review=human_review_decisions,
                total=total_policy,
                clearance_rate_pct=clearance_rate,
            ),
            worker=worker_summary,
            failure_reasons=failure_reasons,
            action_types=action_types,
            recent_activity=recent_activity,
        )

    def list_cases(
        self,
        db: Session,
        page: int = 1,
        page_size: int = 20,
        status: str | None = None,
        recovery_stage: str | None = None,
        search: str | None = None,
    ) -> PaginatedRecoveryCasesResponse:
        """Query paginated recovery cases with safe operational projection."""
        page = max(1, page)
        page_size = max(1, min(100, page_size))

        query = db.query(RecoveryCase)

        if status:
            query = query.filter(RecoveryCase.status == status)
        if recovery_stage:
            query = query.filter(RecoveryCase.recovery_stage == recovery_stage)
        if search:
            search_pattern = f"%{search}%"
            query = query.join(Customer).filter(
                or_(
                    RecoveryCase.latest_failure_reason.ilike(search_pattern),
                    Customer.external_customer_id.ilike(search_pattern),
                )
            )

        total = query.count()
        total_pages = math.ceil(total / page_size) if total > 0 else 0

        cases = (
            query.order_by(RecoveryCase.opened_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
            .all()
        )

        items: list[RecoveryCaseListItem] = []
        for c in cases:
            latest_agent_dec = (
                db.query(AgentDecision)
                .filter_by(recovery_case_id=c.id)
                .order_by(AgentDecision.decided_at.desc())
                .first()
            )
            latest_pol_dec = (
                db.query(PolicyDecision)
                .filter_by(recovery_case_id=c.id)
                .order_by(PolicyDecision.decided_at.desc())
                .first()
            )
            latest_action = (
                db.query(RecoveryAction)
                .filter_by(recovery_case_id=c.id)
                .order_by(RecoveryAction.scheduled_for.desc())
                .first()
            )

            items.append(
                RecoveryCaseListItem(
                    id=c.id,
                    payment_id=c.payment_id,
                    customer_id=c.customer_id,
                    status=c.status,
                    recovery_stage=c.recovery_stage,
                    amount_at_risk=c.amount_at_risk,
                    recovered_amount=c.recovered_amount,
                    total_attempts_count=c.total_attempts_count,
                    max_allowed_attempts=c.max_allowed_attempts,
                    latest_failure_reason=c.latest_failure_reason,
                    opened_at=c.opened_at,
                    next_action_due_at=c.next_action_due_at,
                    resolved_at=c.resolved_at,
                    closed_reason=c.closed_reason,
                    ai_proposed_action=(
                        latest_agent_dec.proposed_action_type
                        if latest_agent_dec
                        else None
                    ),
                    ai_confidence_score=(
                        float(latest_agent_dec.confidence_score)
                        if latest_agent_dec
                        else None
                    ),
                    latest_policy_result=(
                        latest_pol_dec.evaluation_result if latest_pol_dec else None
                    ),
                    latest_action_status=(
                        latest_action.status if latest_action else None
                    ),
                    created_at=c.created_at,
                    updated_at=c.updated_at,
                )
            )

        return PaginatedRecoveryCasesResponse(
            items=items,
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
        )

    def get_case_detail(
        self, db: Session, case_id: uuid.UUID
    ) -> RecoveryCaseDetailResponse | None:
        """Fetch complete, zero-PII lifecycle trail for a specific recovery case."""
        case = db.query(RecoveryCase).filter_by(id=case_id).first()
        if not case:
            return None

        payment = db.query(Payment).filter_by(id=case.payment_id).first()
        customer = db.query(Customer).filter_by(id=case.customer_id).first()

        latest_agent_dec = (
            db.query(AgentDecision)
            .filter_by(recovery_case_id=case.id)
            .order_by(AgentDecision.decided_at.desc())
            .first()
        )
        latest_pol_dec = (
            db.query(PolicyDecision)
            .filter_by(recovery_case_id=case.id)
            .order_by(PolicyDecision.decided_at.desc())
            .first()
        )
        latest_action = (
            db.query(RecoveryAction)
            .filter_by(recovery_case_id=case.id)
            .order_by(RecoveryAction.scheduled_for.desc())
            .first()
        )

        case_item = RecoveryCaseListItem(
            id=case.id,
            payment_id=case.payment_id,
            customer_id=case.customer_id,
            status=case.status,
            recovery_stage=case.recovery_stage,
            amount_at_risk=case.amount_at_risk,
            recovered_amount=case.recovered_amount,
            total_attempts_count=case.total_attempts_count,
            max_allowed_attempts=case.max_allowed_attempts,
            latest_failure_reason=case.latest_failure_reason,
            opened_at=case.opened_at,
            next_action_due_at=case.next_action_due_at,
            resolved_at=case.resolved_at,
            closed_reason=case.closed_reason,
            ai_proposed_action=(
                latest_agent_dec.proposed_action_type if latest_agent_dec else None
            ),
            ai_confidence_score=(
                float(latest_agent_dec.confidence_score) if latest_agent_dec else None
            ),
            latest_policy_result=(
                latest_pol_dec.evaluation_result if latest_pol_dec else None
            ),
            latest_action_status=(latest_action.status if latest_action else None),
            created_at=case.created_at,
            updated_at=case.updated_at,
        )

        payment_summary = PaymentSummary(
            id=payment.id if payment else case.payment_id,
            razorpay_order_id=payment.razorpay_order_id if payment else None,
            razorpay_invoice_id=payment.razorpay_invoice_id if payment else None,
            amount=payment.amount if payment else case.amount_at_risk,
            currency=payment.currency if payment else "INR",
            status=payment.status if payment else "FAILED",
            due_date=payment.due_date if payment else None,
            captured_at=payment.captured_at if payment else None,
            created_at=payment.created_at if payment else case.created_at,
        )

        customer_summary = CustomerSummary(
            id=customer.id if customer else case.customer_id,
            external_customer_id=(
                customer.external_customer_id if customer else "unknown"
            ),
            risk_tier=customer.risk_tier if customer else "STANDARD",
            total_payments_count=(customer.total_payments_count if customer else 0),
            failed_payments_count=(customer.failed_payments_count if customer else 0),
            recovered_payments_count=(
                customer.recovered_payments_count if customer else 0
            ),
        )

        predictions = (
            db.query(MLPrediction)
            .filter_by(recovery_case_id=case.id)
            .order_by(MLPrediction.predicted_at.asc())
            .all()
        )
        pred_summaries = []
        for p in predictions:
            snap = (
                p.feature_vector_snapshot
                if isinstance(p.feature_vector_snapshot, dict)
                else {}
            )
            prob = (
                float(p.recovery_probability)
                if p.recovery_probability is not None
                else 0.0
            )

            # Safe risk_score resolution
            risk_val = getattr(p, "risk_score", None)
            if risk_val is None:
                risk_val = snap.get("risk_score")
            if risk_val is None:
                risk_val = round(max(0.0, min(1.0, 1.0 - prob)), 4)
            else:
                try:
                    risk_val = float(risk_val)
                except (ValueError, TypeError):
                    risk_val = round(max(0.0, min(1.0, 1.0 - prob)), 4)

            # Safe confidence resolution
            conf_val = getattr(p, "confidence", None)
            if conf_val is None:
                conf_val = snap.get("confidence")
            if conf_val is None:
                conf_val = 0.85
            else:
                try:
                    conf_val = float(conf_val)
                except (ValueError, TypeError):
                    conf_val = 0.85

            # Safe priority resolution
            prio_val = getattr(p, "priority", None)
            if not prio_val:
                prio_val = snap.get("priority")
            if not prio_val:
                prio_val = (
                    "HIGH_RECOVERY_POTENTIAL"
                    if prob >= 0.75
                    else "MEDIUM_RECOVERY_POTENTIAL"
                    if prob >= 0.40
                    else "LOW_RECOVERY_POTENTIAL"
                )

            pred_summaries.append(
                MLPredictionSummary(
                    id=p.id,
                    model_name=p.model_name,
                    model_version=p.model_version,
                    recovery_probability=prob,
                    risk_score=risk_val,
                    confidence=conf_val,
                    priority=str(prio_val),
                    predicted_channel=p.predicted_channel,
                    predicted_delay_hours=p.predicted_delay_hours,
                    predicted_at=p.predicted_at,
                )
            )

        agent_decs = (
            db.query(AgentDecision)
            .filter_by(recovery_case_id=case.id)
            .order_by(AgentDecision.decided_at.asc())
            .all()
        )
        agent_summaries = []
        for d in agent_decs:
            payload = (
                d.suggested_payload if isinstance(d.suggested_payload, dict) else {}
            )
            delay_hrs = (
                int(payload.get("recommended_delay_hours", 0))
                if isinstance(payload.get("recommended_delay_hours"), int | float)
                else 0
            )
            agent_summaries.append(
                AgentDecisionSummary(
                    id=d.id,
                    proposed_action_type=d.proposed_action_type,
                    confidence_score=float(d.confidence_score),
                    reasoning_summary=d.reasoning_summary,
                    recommended_delay_hours=delay_hrs,
                    agent_name=d.agent_name,
                    agent_version=d.agent_version,
                    decided_at=d.decided_at,
                )
            )

        policy_decs = (
            db.query(PolicyDecision)
            .filter_by(recovery_case_id=case.id)
            .order_by(PolicyDecision.decided_at.asc())
            .all()
        )
        policy_summaries = [
            PolicyDecisionSummary(
                id=pd.id,
                agent_decision_id=pd.agent_decision_id,
                evaluation_result=pd.evaluation_result,
                policy_engine_version=pd.policy_engine_version,
                triggered_rule_code=pd.triggered_rule_code,
                rule_name=pd.rule_name,
                decision_reason=pd.decision_reason,
                decided_at=pd.decided_at,
            )
            for pd in policy_decs
        ]

        actions = (
            db.query(RecoveryAction)
            .filter_by(recovery_case_id=case.id)
            .order_by(RecoveryAction.scheduled_for.asc())
            .all()
        )
        action_summaries = []
        for act in actions:
            act_results = (
                db.query(ActionResult)
                .filter_by(recovery_action_id=act.id)
                .order_by(ActionResult.executed_at.asc())
                .all()
            )
            res_summaries = [
                ActionResultSummary(
                    id=r.id,
                    execution_status=r.execution_status,
                    provider_reference_id=r.provider_reference_id,
                    provider_status_code=r.provider_status_code,
                    failure_reason=r.failure_reason,
                    executed_at=r.executed_at,
                )
                for r in act_results
            ]
            action_summaries.append(
                RecoveryActionSummary(
                    id=act.id,
                    policy_decision_id=act.policy_decision_id,
                    action_type=act.action_type,
                    status=act.status,
                    scheduled_for=act.scheduled_for,
                    dispatched_at=act.dispatched_at,
                    completed_at=act.completed_at,
                    created_at=act.created_at,
                    results=res_summaries,
                )
            )

        audits = (
            db.query(AuditLog)
            .filter_by(recovery_case_id=case.id)
            .order_by(AuditLog.created_at.asc())
            .all()
        )
        audit_summaries = [
            AuditLogSummary(
                id=a.id,
                event_type=a.event_type,
                actor_type=a.actor_type,
                actor_id=a.actor_id,
                entity_type=a.entity_type,
                entity_id=a.entity_id,
                action=a.action,
                previous_state=a.previous_state,
                new_state=a.new_state,
                metadata_json=a.metadata_json or {},
                created_at=a.created_at,
            )
            for a in audits
        ]

        return RecoveryCaseDetailResponse(
            case=case_item,
            payment=payment_summary,
            customer=customer_summary,
            predictions=pred_summaries,
            agent_decisions=agent_summaries,
            policy_decisions=policy_summaries,
            actions=action_summaries,
            audit_logs=audit_summaries,
        )

    def get_human_review_queue(
        self, db: Session, page: int = 1, page_size: int = 20
    ) -> PaginatedHumanReviewResponse:
        """Query active cases with latest policy decision in HUMAN_REVIEW."""
        page = max(1, page)
        page_size = max(1, min(100, page_size))

        # Query cases where status is active
        active_cases = (
            db.query(RecoveryCase)
            .filter(RecoveryCase.status.in_(ACTIVE_CASE_STATUSES))
            .order_by(RecoveryCase.opened_at.desc())
            .all()
        )

        review_items: list[HumanReviewQueueItem] = []
        for case in active_cases:
            latest_pol = (
                db.query(PolicyDecision)
                .filter_by(recovery_case_id=case.id)
                .order_by(PolicyDecision.decided_at.desc())
                .first()
            )
            if (
                not latest_pol
                or latest_pol.evaluation_result
                != PolicyEvaluationResult.HUMAN_REVIEW.value
            ):
                continue

            # Ensure no active SCHEDULED or EXECUTING action already exists
            active_action = (
                db.query(RecoveryAction)
                .filter(
                    RecoveryAction.recovery_case_id == case.id,
                    RecoveryAction.status.in_(
                        [
                            RecoveryActionStatus.SCHEDULED.value,
                            RecoveryActionStatus.EXECUTING.value,
                        ]
                    ),
                )
                .first()
            )
            if active_action:
                continue

            customer = db.query(Customer).filter_by(id=case.customer_id).first()
            agent_dec = (
                db.query(AgentDecision)
                .filter_by(id=latest_pol.agent_decision_id)
                .first()
                if latest_pol.agent_decision_id
                else None
            )

            review_items.append(
                HumanReviewQueueItem(
                    case_id=case.id,
                    payment_id=case.payment_id,
                    customer_id=case.customer_id,
                    customer_risk_tier=customer.risk_tier if customer else "STANDARD",
                    amount_at_risk=case.amount_at_risk,
                    currency="INR",
                    case_status=case.status,
                    recovery_stage=case.recovery_stage,
                    latest_failure_reason=case.latest_failure_reason,
                    previous_attempts_count=case.total_attempts_count,
                    policy_decision_id=latest_pol.id,
                    triggered_rule_code=latest_pol.triggered_rule_code,
                    rule_name=latest_pol.rule_name,
                    policy_decision_reason=latest_pol.decision_reason,
                    agent_decision_id=agent_dec.id if agent_dec else None,
                    proposed_action_type=agent_dec.proposed_action_type
                    if agent_dec
                    else None,
                    ai_confidence_score=float(agent_dec.confidence_score)
                    if agent_dec
                    else None,
                    ai_reasoning_summary=agent_dec.reasoning_summary
                    if agent_dec
                    else None,
                    opened_at=case.opened_at,
                    decided_at=latest_pol.decided_at,
                )
            )

        total = len(review_items)
        total_pages = math.ceil(total / page_size) if total > 0 else 0
        paginated_items = review_items[(page - 1) * page_size : page * page_size]

        return PaginatedHumanReviewResponse(
            items=paginated_items,
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
        )

    def approve_human_review(
        self,
        db: Session,
        case_id: uuid.UUID,
        operator_id: str,
        notes: str | None = None,
        as_of: datetime | None = None,
    ) -> HumanReviewActionResponse:
        """
        Approve a case in human review by authoritatively creating an ALLOWED PolicyDecision
        and delegating to RecoveryActionScheduler.
        """
        now_utc = as_of or datetime.now(UTC)
        if now_utc.tzinfo is None:
            now_utc = now_utc.replace(tzinfo=UTC)

        case = db.query(RecoveryCase).filter_by(id=case_id).first()
        if not case:
            raise CaseNotFoundError(f"RecoveryCase '{case_id}' not found.")

        if case.status in TERMINAL_CASE_STATUSES:
            raise ReviewNotEligibleError(
                f"Case '{case_id}' is in terminal status '{case.status}'."
            )

        latest_pol = (
            db.query(PolicyDecision)
            .filter_by(recovery_case_id=case.id)
            .order_by(PolicyDecision.decided_at.desc())
            .first()
        )
        if (
            not latest_pol
            or latest_pol.evaluation_result != PolicyEvaluationResult.HUMAN_REVIEW.value
        ):
            raise ReviewNotEligibleError(
                f"Case '{case_id}' does not have an active HUMAN_REVIEW policy outcome."
            )

        # Check for active action collision
        active_action = (
            db.query(RecoveryAction)
            .filter(
                RecoveryAction.recovery_case_id == case.id,
                RecoveryAction.status.in_(
                    [
                        RecoveryActionStatus.SCHEDULED.value,
                        RecoveryActionStatus.EXECUTING.value,
                    ]
                ),
            )
            .first()
        )
        if active_action:
            raise ReviewNotEligibleError(
                f"Case '{case_id}' already has an active action ({active_action.status})."
            )

        try:
            # 1. Create approved PolicyDecision
            approved_pol = PolicyDecision(
                recovery_case_id=case.id,
                agent_decision_id=latest_pol.agent_decision_id,
                evaluation_result=PolicyEvaluationResult.ALLOWED.value,
                policy_engine_version=latest_pol.policy_engine_version,
                triggered_rule_code="HUMAN_OVERRIDE_APPROVED",
                rule_name="Human Review Operator Approval",
                decision_reason=(
                    f"Approved by operator '{operator_id}': {notes or 'No notes provided'}"
                ),
                evaluation_details={
                    "original_policy_decision_id": str(latest_pol.id),
                    "operator_id": operator_id,
                    "notes": notes,
                },
                decided_at=now_utc,
            )
            db.add(approved_pol)
            db.flush()

            # 2. Delegate to authoritative RecoveryActionScheduler
            action = action_scheduler.schedule_for_policy_decision(
                db=db,
                policy_decision_id=approved_pol.id,
                as_of=now_utc,
            )

            # 3. Create immutable AuditLog
            audit = AuditLog(
                event_type="HUMAN_REVIEW_APPROVED",
                actor_type=AuditActorType.HUMAN_ADMIN.value,
                actor_id=operator_id,
                recovery_case_id=case.id,
                entity_type="recovery_cases",
                entity_id=case.id,
                action="HUMAN_REVIEW_APPROVED",
                previous_state={"evaluation_result": latest_pol.evaluation_result},
                new_state={
                    "evaluation_result": PolicyEvaluationResult.ALLOWED.value,
                    "policy_decision_id": str(approved_pol.id),
                    "scheduled_action_id": str(action.id) if action else None,
                },
                metadata_json={
                    "operator_id": operator_id,
                    "notes": notes,
                    "original_policy_decision_id": str(latest_pol.id),
                },
                created_at=now_utc,
            )
            db.add(audit)
            db.commit()

            logger.info(
                "human_review_approved",
                extra={
                    "case_id": str(case.id),
                    "operator_id": operator_id,
                    "action_id": str(action.id) if action else None,
                },
            )

            return HumanReviewActionResponse(
                success=True,
                case_id=case.id,
                action="APPROVED",
                scheduled_action_id=action.id if action else None,
                message="Case approved and recovery action scheduled successfully.",
                timestamp=now_utc,
            )

        except Exception as exc:
            db.rollback()
            logger.error(
                "human_review_approval_failed",
                extra={"case_id": str(case.id), "error": str(exc)},
            )
            raise MetricsServiceError(f"Failed to approve review: {exc}") from exc

    def dismiss_human_review(
        self,
        db: Session,
        case_id: uuid.UUID,
        operator_id: str,
        notes: str | None = None,
        as_of: datetime | None = None,
    ) -> HumanReviewActionResponse:
        """
        Dismiss a case in human review with an immutable AuditLog entry.
        """
        now_utc = as_of or datetime.now(UTC)
        if now_utc.tzinfo is None:
            now_utc = now_utc.replace(tzinfo=UTC)

        case = db.query(RecoveryCase).filter_by(id=case_id).first()
        if not case:
            raise CaseNotFoundError(f"RecoveryCase '{case_id}' not found.")

        if case.status in TERMINAL_CASE_STATUSES:
            raise ReviewNotEligibleError(
                f"Case '{case_id}' is in terminal status '{case.status}'."
            )

        latest_pol = (
            db.query(PolicyDecision)
            .filter_by(recovery_case_id=case.id)
            .order_by(PolicyDecision.decided_at.desc())
            .first()
        )
        if (
            not latest_pol
            or latest_pol.evaluation_result != PolicyEvaluationResult.HUMAN_REVIEW.value
        ):
            raise ReviewNotEligibleError(
                f"Case '{case_id}' does not have an active HUMAN_REVIEW policy outcome."
            )

        try:
            # 1. Create blocked dismissal PolicyDecision
            dismissed_pol = PolicyDecision(
                recovery_case_id=case.id,
                agent_decision_id=latest_pol.agent_decision_id,
                evaluation_result=PolicyEvaluationResult.BLOCKED.value,
                policy_engine_version=latest_pol.policy_engine_version,
                triggered_rule_code="HUMAN_OVERRIDE_DISMISSED",
                rule_name="Human Review Operator Dismissal",
                decision_reason=(
                    f"Dismissed by operator '{operator_id}': {notes or 'No notes provided'}"
                ),
                evaluation_details={
                    "original_policy_decision_id": str(latest_pol.id),
                    "operator_id": operator_id,
                    "notes": notes,
                },
                decided_at=now_utc,
            )
            db.add(dismissed_pol)

            # 2. Create AuditLog
            audit = AuditLog(
                event_type="HUMAN_REVIEW_DISMISSED",
                actor_type=AuditActorType.HUMAN_ADMIN.value,
                actor_id=operator_id,
                recovery_case_id=case.id,
                entity_type="recovery_cases",
                entity_id=case.id,
                action="HUMAN_REVIEW_DISMISSED",
                previous_state={"evaluation_result": latest_pol.evaluation_result},
                new_state={
                    "evaluation_result": PolicyEvaluationResult.BLOCKED.value,
                    "policy_decision_id": str(dismissed_pol.id),
                },
                metadata_json={
                    "operator_id": operator_id,
                    "notes": notes,
                    "original_policy_decision_id": str(latest_pol.id),
                },
                created_at=now_utc,
            )
            db.add(audit)
            db.commit()

            logger.info(
                "human_review_dismissed",
                extra={"case_id": str(case.id), "operator_id": operator_id},
            )

            return HumanReviewActionResponse(
                success=True,
                case_id=case.id,
                action="DISMISSED",
                scheduled_action_id=None,
                message="Case dismissed successfully with audit log recording.",
                timestamp=now_utc,
            )

        except Exception as exc:
            db.rollback()
            logger.error(
                "human_review_dismissal_failed",
                extra={"case_id": str(case.id), "error": str(exc)},
            )
            raise MetricsServiceError(f"Failed to dismiss review: {exc}") from exc

    def list_audit_logs(
        self,
        db: Session,
        page: int = 1,
        page_size: int = 20,
        event_type: str | None = None,
        case_id: uuid.UUID | None = None,
    ) -> PaginatedAuditLogsResponse:
        """Query paginated audit log entries with optional filters."""
        page = max(1, page)
        page_size = max(1, min(100, page_size))

        query = db.query(AuditLog)
        if event_type:
            query = query.filter(AuditLog.event_type == event_type)
        if case_id:
            query = query.filter(AuditLog.recovery_case_id == case_id)

        total = query.count()
        total_pages = math.ceil(total / page_size) if total > 0 else 0

        logs = (
            query.order_by(AuditLog.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
            .all()
        )

        items = [
            AuditLogSummary(
                id=a.id,
                event_type=a.event_type,
                actor_type=a.actor_type,
                actor_id=a.actor_id,
                entity_type=a.entity_type,
                entity_id=a.entity_id,
                action=a.action,
                previous_state=a.previous_state,
                new_state=a.new_state,
                metadata_json=a.metadata_json or {},
                created_at=a.created_at,
            )
            for a in logs
        ]

        return PaginatedAuditLogsResponse(
            items=items,
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
        )


recovery_metrics_service = RecoveryMetricsService()
