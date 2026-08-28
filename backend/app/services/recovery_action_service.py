import logging
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy.orm import Session

from app.models import (
    AgentDecision,
    AuditActorType,
    AuditLog,
    PolicyDecision,
    PolicyEvaluationResult,
    RecoveryAction,
    RecoveryActionStatus,
    RecoveryActionType,
    RecoveryCase,
    RecoveryCaseStatus,
)

logger = logging.getLogger(__name__)

TERMINAL_CASE_STATUSES = {
    RecoveryCaseStatus.RECOVERED.value,
    RecoveryCaseStatus.CLOSED.value,
}


class ActionSchedulerError(Exception):
    """Base exception for recovery action scheduling errors."""


class PolicyNotAllowedError(ActionSchedulerError):
    """Raised when scheduling an action for a non-ALLOWED policy decision."""


class UnactionableCaseError(ActionSchedulerError):
    """Raised when the RecoveryCase is in a terminal (resolved/closed) state."""


class InvalidActionTypeError(ActionSchedulerError):
    """Raised when the proposed action type is not a valid RecoveryActionType."""


class PolicyDecisionNotFoundError(ActionSchedulerError):
    """Raised when the specified PolicyDecision is not found."""


class RecoveryCaseNotFoundError(ActionSchedulerError):
    """Raised when the associated RecoveryCase is not found."""


class RecoveryActionNotFoundError(ActionSchedulerError):
    """Raised when the specified RecoveryAction is not found."""


class ActionPersistenceError(ActionSchedulerError):
    """Raised when persisting the RecoveryAction or AuditLog fails."""


class RecoveryActionService:
    """Service for deterministic creation and persistence of RecoveryAction records."""

    def create_recovery_action(
        self,
        db: Session,
        policy_decision: PolicyDecision,
        agent_decision: AgentDecision | None = None,
        as_of: datetime | None = None,
    ) -> RecoveryAction:
        """
        Create a SCHEDULED RecoveryAction for an ALLOWED PolicyDecision.

        Guarantees:
        - Never schedules an action unless policy evaluation is ALLOWED.
        - Rejects terminal RecoveryCases (RECOVERED / CLOSED).
        - Generates a deterministic action_idempotency_key.
        - Respects recommended_delay_hours for scheduled_for computation.
        - Commits RecoveryAction and AuditLog atomically.
        """
        # 1. Authoritative Policy Check
        if policy_decision.evaluation_result != PolicyEvaluationResult.ALLOWED.value:
            raise PolicyNotAllowedError(
                f"Cannot schedule action for PolicyDecision '{policy_decision.id}' "
                f"with evaluation_result '{policy_decision.evaluation_result}'. "
                "Only ALLOWED policy decisions may be scheduled."
            )

        # 2. Case Actionability Check
        case = (
            db.query(RecoveryCase)
            .filter_by(id=policy_decision.recovery_case_id)
            .first()
        )
        if not case:
            raise RecoveryCaseNotFoundError(
                f"RecoveryCase '{policy_decision.recovery_case_id}' not found"
            )

        if case.status in TERMINAL_CASE_STATUSES:
            raise UnactionableCaseError(
                f"Cannot schedule action for RecoveryCase '{case.id}' "
                f"with terminal status '{case.status}'."
            )

        # 3. Action Type Resolution & Validation
        action_type: str | None = None
        if agent_decision:
            action_type = str(agent_decision.proposed_action_type)
        elif (
            isinstance(policy_decision.evaluation_details, dict)
            and "proposed_action_type" in policy_decision.evaluation_details
        ):
            action_type = str(
                policy_decision.evaluation_details["proposed_action_type"]
            )

        if not action_type or action_type not in [a.value for a in RecoveryActionType]:
            raise InvalidActionTypeError(
                f"Invalid or missing action_type '{action_type}'. "
                f"Must be one of {[a.value for a in RecoveryActionType]}."
            )

        # 4. Deterministic Idempotency Key
        idempotency_key = f"act_{case.id}_{policy_decision.id}_{action_type}"

        # 5. Idempotent Check: Return existing if already scheduled
        existing_action = (
            db.query(RecoveryAction)
            .filter_by(action_idempotency_key=idempotency_key)
            .first()
        )
        if existing_action:
            logger.info(
                "recovery_action_already_scheduled",
                extra={
                    "action_id": str(existing_action.id),
                    "idempotency_key": idempotency_key,
                },
            )
            return existing_action

        # 6. Scheduled Time Calculation
        now_utc = as_of or datetime.now(UTC)
        if now_utc.tzinfo is None:
            now_utc = now_utc.replace(tzinfo=UTC)

        delay_hours = 0
        payload: dict[str, Any] = {}
        if agent_decision and isinstance(agent_decision.suggested_payload, dict):
            payload = dict(agent_decision.suggested_payload)
            delay_raw = payload.get("recommended_delay_hours", 0)
            try:
                delay_hours = max(0, min(168, int(delay_raw)))
            except (ValueError, TypeError):
                delay_hours = 0

        scheduled_for = now_utc + timedelta(hours=delay_hours)

        # 7. Construct RecoveryAction Entity
        action = RecoveryAction(
            recovery_case_id=case.id,
            policy_decision_id=policy_decision.id,
            action_idempotency_key=idempotency_key,
            action_type=action_type,
            status=RecoveryActionStatus.SCHEDULED.value,
            scheduled_for=scheduled_for,
            action_payload=payload,
        )

        # 8. Atomic Persistence and Audit Logging
        try:
            db.add(action)
            db.flush()

            audit = AuditLog(
                event_type="RECOVERY_ACTION_SCHEDULED",
                actor_type=AuditActorType.SYSTEM_EVENT.value,
                actor_id="action_scheduler",
                recovery_case_id=case.id,
                entity_type="recovery_actions",
                entity_id=action.id,
                action="RECOVERY_ACTION_SCHEDULED",
                previous_state=None,
                new_state={
                    "action_type": action.action_type,
                    "status": action.status,
                    "scheduled_for": action.scheduled_for.isoformat(),
                    "action_idempotency_key": action.action_idempotency_key,
                },
                metadata_json={
                    "policy_decision_id": str(policy_decision.id),
                    "agent_decision_id": (
                        str(agent_decision.id) if agent_decision else None
                    ),
                    "recommended_delay_hours": delay_hours,
                },
            )
            db.add(audit)
            db.commit()
            db.refresh(action)

            logger.info(
                "recovery_action_scheduled",
                extra={
                    "action_id": str(action.id),
                    "case_id": str(case.id),
                    "action_type": action_type,
                    "scheduled_for": action.scheduled_for.isoformat(),
                },
            )
            return action

        except Exception as exc:
            db.rollback()
            logger.error(
                "recovery_action_persistence_failed",
                extra={"case_id": str(case.id), "error": str(exc)},
            )
            raise ActionPersistenceError(
                f"Failed to persist RecoveryAction: {exc}"
            ) from exc


recovery_action_service = RecoveryActionService()
