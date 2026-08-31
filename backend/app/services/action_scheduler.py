import logging
import uuid
from datetime import datetime

from sqlalchemy.orm import Session

from app.models import (
    AgentDecision,
    AuditActorType,
    AuditLog,
    PolicyDecision,
    PolicyEvaluationResult,
    RecoveryAction,
    RecoveryCase,
)
from app.services.recovery_action_service import (
    TERMINAL_CASE_STATUSES,
    ActionPersistenceError,
    PolicyDecisionNotFoundError,
    RecoveryCaseNotFoundError,
    UnactionableCaseError,
    recovery_action_service,
)

logger = logging.getLogger(__name__)


class RecoveryActionScheduler:
    """
    Deterministic orchestration engine that receives evaluated PolicyDecision records
    and safely schedules authorized RecoveryAction jobs.

    Guarantees:
    - Never creates a RecoveryAction for BLOCKED or HUMAN_REVIEW policy outcomes.
    - Strictly validates case actionability before scheduling.
    - Idempotent and deterministic scheduling across runs.
    - Atomic transaction boundary.
    """

    def schedule_for_policy_decision(
        self,
        db: Session,
        policy_decision_id: uuid.UUID,
        as_of: datetime | None = None,
    ) -> RecoveryAction | None:
        """
        Evaluate a PolicyDecision and schedule a RecoveryAction if and only if ALLOWED.
        """
        logger.info(
            "scheduling_orchestration_started",
            extra={"policy_decision_id": str(policy_decision_id)},
        )

        # 1. Load PolicyDecision
        policy_decision = (
            db.query(PolicyDecision).filter_by(id=policy_decision_id).first()
        )
        if not policy_decision:
            raise PolicyDecisionNotFoundError(
                f"PolicyDecision '{policy_decision_id}' not found."
            )

        # 2. Load RecoveryCase
        case = (
            db.query(RecoveryCase)
            .filter_by(id=policy_decision.recovery_case_id)
            .first()
        )
        if not case:
            raise RecoveryCaseNotFoundError(
                f"RecoveryCase '{policy_decision.recovery_case_id}' not found."
            )

        # 3. Check Case Actionability
        if case.status in TERMINAL_CASE_STATUSES:
            raise UnactionableCaseError(
                f"Cannot schedule action for case '{case.id}' "
                f"with status '{case.status}'."
            )

        # 4. Handle BLOCKED Outcome: Exactly ZERO RecoveryActions created
        if policy_decision.evaluation_result == PolicyEvaluationResult.BLOCKED.value:
            logger.info(
                "action_scheduling_blocked_by_policy",
                extra={
                    "case_id": str(case.id),
                    "policy_decision_id": str(policy_decision.id),
                    "triggered_rule": policy_decision.triggered_rule_code,
                },
            )
            try:
                audit = AuditLog(
                    event_type="RECOVERY_ACTION_BLOCKED",
                    actor_type=AuditActorType.SYSTEM_EVENT.value,
                    actor_id="action_scheduler",
                    recovery_case_id=case.id,
                    entity_type="policy_decisions",
                    entity_id=policy_decision.id,
                    action="RECOVERY_ACTION_BLOCKED",
                    previous_state=None,
                    new_state={
                        "evaluation_result": policy_decision.evaluation_result,
                        "triggered_rule_code": policy_decision.triggered_rule_code,
                        "decision_reason": policy_decision.decision_reason,
                    },
                    metadata_json={
                        "policy_decision_id": str(policy_decision.id),
                    },
                )
                db.add(audit)
                db.commit()
            except Exception as exc:
                db.rollback()
                raise ActionPersistenceError(
                    f"Failed to record audit log for blocked action: {exc}"
                ) from exc
            return None

        # 5. Handle HUMAN_REVIEW Outcome: Exactly ZERO RecoveryActions created
        if (
            policy_decision.evaluation_result
            == PolicyEvaluationResult.HUMAN_REVIEW.value
        ):
            logger.info(
                "action_scheduling_queued_for_human_review",
                extra={
                    "case_id": str(case.id),
                    "policy_decision_id": str(policy_decision.id),
                    "triggered_rule": policy_decision.triggered_rule_code,
                },
            )
            try:
                audit = AuditLog(
                    event_type="RECOVERY_ACTION_HUMAN_REVIEW",
                    actor_type=AuditActorType.SYSTEM_EVENT.value,
                    actor_id="action_scheduler",
                    recovery_case_id=case.id,
                    entity_type="policy_decisions",
                    entity_id=policy_decision.id,
                    action="RECOVERY_ACTION_HUMAN_REVIEW",
                    previous_state=None,
                    new_state={
                        "evaluation_result": policy_decision.evaluation_result,
                        "triggered_rule_code": policy_decision.triggered_rule_code,
                        "decision_reason": policy_decision.decision_reason,
                    },
                    metadata_json={
                        "policy_decision_id": str(policy_decision.id),
                    },
                )
                db.add(audit)
                db.commit()
            except Exception as exc:
                db.rollback()
                raise ActionPersistenceError(
                    f"Failed to record audit log for human review: {exc}"
                ) from exc
            return None

        # 6. Handle ALLOWED Outcome: Schedule RecoveryAction
        agent_decision = None
        if policy_decision.agent_decision_id:
            agent_decision = (
                db.query(AgentDecision)
                .filter_by(id=policy_decision.agent_decision_id)
                .first()
            )

        return recovery_action_service.create_recovery_action(
            db=db,
            policy_decision=policy_decision,
            agent_decision=agent_decision,
            as_of=as_of,
        )


action_scheduler = RecoveryActionScheduler()
