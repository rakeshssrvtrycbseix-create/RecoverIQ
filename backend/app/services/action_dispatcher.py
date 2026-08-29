import logging
import re
import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy.orm import Session

from app.models import (
    ActionResult,
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
from app.providers.base import ActionProvider, ProviderResult
from app.providers.factory import ProviderFactory

logger = logging.getLogger(__name__)

TERMINAL_CASE_STATUSES = {
    RecoveryCaseStatus.RECOVERED.value,
    RecoveryCaseStatus.CLOSED.value,
}

FORBIDDEN_SENSITIVE_KEYS = {
    "email",
    "phone",
    "contact",
    "card_number",
    "pan",
    "cvv",
    "cvc",
    "pin",
    "password",
    "secret",
    "token",
    "api_key",
    "secret_key",
    "private_key",
    "auth_token",
    "access_token",
    "webhook_secret",
    "razorpay_key",
    "razorpay_secret",
    "bearer",
}

EMAIL_REGEX = re.compile(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+")
CARD_REGEX = re.compile(r"\b(?:\d[ -]*?){13,19}\b")
SECRET_TOKEN_REGEX = re.compile(
    r"(?:sk_live_|sk_test_|rzp_live_|rzp_test_|Bearer\s+|eyJh)[A-Za-z0-9_\-\.]{8,}"
)


class ActionDispatchError(Exception):
    """Base exception for all action dispatcher errors."""


class RecoveryActionNotFoundError(ActionDispatchError):
    """Raised when the specified RecoveryAction does not exist."""


class InvalidActionStateError(ActionDispatchError):
    """Raised when an action is not in a valid state for execution."""


class ActionNotDueError(ActionDispatchError):
    """Raised when an action's scheduled_for time has not yet elapsed."""


class UnauthorizedActionError(ActionDispatchError):
    """Raised when the associated PolicyDecision is not ALLOWED."""


class UnactionableCaseError(ActionDispatchError):
    """Raised when the associated RecoveryCase is in a terminal state."""


class InvalidActionTypeError(ActionDispatchError):
    """Raised when an action type is unsupported or invalid."""


class ConcurrentExecutionError(ActionDispatchError):
    """Raised when an action is already in EXECUTING state by another worker."""


class UnsafeActionPayloadError(ActionDispatchError):
    """Raised when action payload contains sensitive PII or credentials."""


class ActionExecutionPersistenceError(ActionDispatchError):
    """Raised when persisting execution telemetry or state finalization fails."""


def _validate_payload_safety(data: Any, path: str = "payload") -> None:
    """Validate action payload for forbidden sensitive keys, cards, and tokens."""
    if isinstance(data, dict):
        for k, v in data.items():
            k_lower = str(k).lower()
            current_path = f"{path}.{k}"
            if (
                k_lower in FORBIDDEN_SENSITIVE_KEYS
                or "secret" in k_lower
                or k_lower.startswith("card_")
            ):
                raise UnsafeActionPayloadError(
                    f"Unsafe payload: Forbidden key '{k}' at {current_path}"
                )
            _validate_payload_safety(v, current_path)
    elif isinstance(data, list | tuple | set):
        for i, item in enumerate(data):
            _validate_payload_safety(item, f"{path}[{i}]")
    elif isinstance(data, str):
        if EMAIL_REGEX.search(data):
            raise UnsafeActionPayloadError(
                f"Unsafe payload: Email address detected at {path}"
            )
        digits = re.sub(r"\D", "", data)
        if len(digits) >= 13 and CARD_REGEX.search(data):
            raise UnsafeActionPayloadError(
                f"Unsafe payload: Card-like number detected at {path}"
            )
        if SECRET_TOKEN_REGEX.search(data):
            raise UnsafeActionPayloadError(
                f"Unsafe payload: Secret token prefix detected at {path}"
            )


class ActionDispatcher:
    """
    Deterministic Action Dispatcher that orchestrates external provider execution,
    state transitions, idempotency guards, and execution telemetry persistence.

    Guarantees:
    - Never executes unless status is SCHEDULED and scheduled_for <= current UTC time.
    - Zero execution for BLOCKED / HUMAN_REVIEW policy outcomes or terminal cases.
    - Idempotent: Repeated execution returns existing ActionResult with 0 duplicate calls.
    - Concurrency protection: Transitions SCHEDULED -> EXECUTING atomically before dispatch.
    - Non-retrying: FAILED actions remain FAILED (no automatic retry loops).
    """

    def dispatch_action(
        self,
        db: Session,
        recovery_action_id: uuid.UUID,
        provider: ActionProvider | None = None,
        as_of: datetime | None = None,
    ) -> ActionResult | None:
        """Dispatch a single scheduled recovery action deterministically."""
        logger.info(
            "action_dispatch_initiated",
            extra={"recovery_action_id": str(recovery_action_id)},
        )

        # 1. Load RecoveryAction
        action = (
            db.query(RecoveryAction)
            .filter_by(id=recovery_action_id)
            .first()
        )
        if not action:
            raise RecoveryActionNotFoundError(
                f"RecoveryAction '{recovery_action_id}' not found."
            )

        # 2. Idempotency & Terminal State Check
        if action.status in {
            RecoveryActionStatus.COMPLETED.value,
            RecoveryActionStatus.FAILED.value,
        }:
            logger.info(
                "action_already_finalized_idempotent_return",
                extra={"action_id": str(action.id), "status": action.status},
            )
            return (
                db.query(ActionResult)
                .filter_by(recovery_action_id=action.id)
                .order_by(ActionResult.executed_at.desc())
                .first()
            )

        if action.status == RecoveryActionStatus.EXECUTING.value:
            raise ConcurrentExecutionError(
                f"RecoveryAction '{action.id}' is currently EXECUTING."
            )

        if action.status != RecoveryActionStatus.SCHEDULED.value:
            raise InvalidActionStateError(
                f"RecoveryAction '{action.id}' has unexpected status '{action.status}' "
                f"(expected '{RecoveryActionStatus.SCHEDULED.value}')."
            )

        # 3. Due Time Validation
        now_utc = as_of or datetime.now(UTC)
        if now_utc.tzinfo is None:
            now_utc = now_utc.replace(tzinfo=UTC)

        sched_time = action.scheduled_for
        if sched_time.tzinfo is None:
            sched_time = sched_time.replace(tzinfo=UTC)

        if sched_time > now_utc:
            raise ActionNotDueError(
                f"RecoveryAction '{action.id}' is scheduled for '{sched_time.isoformat()}', "
                f"which is in the future relative to '{now_utc.isoformat()}'."
            )

        # 4. Policy Clearance Validation
        policy_decision = (
            db.query(PolicyDecision)
            .filter_by(id=action.policy_decision_id)
            .first()
        )
        if (
            not policy_decision
            or policy_decision.evaluation_result
            != PolicyEvaluationResult.ALLOWED.value
        ):
            res = (
                policy_decision.evaluation_result
                if policy_decision
                else "MISSING"
            )
            raise UnauthorizedActionError(
                f"Cannot dispatch action '{action.id}' with policy evaluation '{res}'."
            )

        # 5. Case Actionability Validation
        case = (
            db.query(RecoveryCase)
            .filter_by(id=action.recovery_case_id)
            .first()
        )
        if not case or case.status in TERMINAL_CASE_STATUSES:
            case_status = case.status if case else "MISSING"
            raise UnactionableCaseError(
                f"Cannot dispatch action for case with terminal status '{case_status}'."
            )

        # 6. Action Type Validation
        if action.action_type not in [a.value for a in RecoveryActionType]:
            raise InvalidActionTypeError(
                f"Unsupported action type '{action.action_type}'."
            )

        # 7. Payload Safety Check
        if action.action_payload:
            _validate_payload_safety(action.action_payload)

        # 8. Step A: Atomic Transition -> EXECUTING
        try:
            action.status = RecoveryActionStatus.EXECUTING.value
            action.dispatched_at = now_utc
            db.commit()
            db.refresh(action)
        except Exception as exc:
            db.rollback()
            raise ActionExecutionPersistenceError(
                f"Failed to transition action to EXECUTING: {exc}"
            ) from exc

        # 9. Step B: Invoke Action Provider (External Boundary)
        active_provider = provider or ProviderFactory.get_provider()
        try:
            provider_result = active_provider.execute(action)
        except Exception as exc:
            logger.error(
                "action_provider_unhandled_exception",
                extra={"action_id": str(action.id), "error": str(exc)},
            )
            provider_result = ProviderResult(
                success=False,
                execution_status="FAILED",
                provider_reference_id=f"err_{action.id}",
                provider_status_code="500",
                failure_reason="PROVIDER_EXCEPTION",
                error_details=str(exc),
                response_payload_summary={"unhandled_exception": True},
                executed_at=now_utc,
            )

        # 10. Step C: State Finalization & Persistence
        try:
            if (
                provider_result.execution_status == "TIMED_OUT"
                or provider_result.failure_reason == "GATEWAY_TIMEOUT"
            ):
                # Gateway timeout: Keep action in EXECUTING for background reconciliation
                action_result = ActionResult(
                    recovery_action_id=action.id,
                    execution_status="TIMED_OUT",
                    provider_reference_id=provider_result.provider_reference_id,
                    provider_status_code=provider_result.provider_status_code or "408",
                    failure_reason="GATEWAY_TIMEOUT",
                    error_details=provider_result.error_details,
                    response_payload_summary=provider_result.response_payload_summary,
                    executed_at=provider_result.executed_at,
                )
                audit = AuditLog(
                    event_type="ACTION_EXECUTION_TIMED_OUT",
                    actor_type=AuditActorType.ACTION_EXECUTOR.value,
                    actor_id="action_dispatcher",
                    recovery_case_id=case.id,
                    entity_type="recovery_actions",
                    entity_id=action.id,
                    action="ACTION_EXECUTION_TIMED_OUT",
                    previous_state={"status": RecoveryActionStatus.EXECUTING.value},
                    new_state={
                        "status": RecoveryActionStatus.EXECUTING.value,
                        "execution_status": "TIMED_OUT",
                        "failure_reason": "GATEWAY_TIMEOUT",
                    },
                    metadata_json={
                        "action_type": action.action_type,
                    },
                )
            elif provider_result.success:
                action.status = RecoveryActionStatus.COMPLETED.value
                action.completed_at = provider_result.executed_at
                action_result = ActionResult(
                    recovery_action_id=action.id,
                    execution_status="SUCCESS",
                    provider_reference_id=provider_result.provider_reference_id,
                    provider_status_code=provider_result.provider_status_code,
                    failure_reason=None,
                    error_details=None,
                    response_payload_summary=provider_result.response_payload_summary,
                    executed_at=provider_result.executed_at,
                )
                audit = AuditLog(
                    event_type="RECOVERY_ACTION_EXECUTED",
                    actor_type=AuditActorType.ACTION_EXECUTOR.value,
                    actor_id="action_dispatcher",
                    recovery_case_id=case.id,
                    entity_type="recovery_actions",
                    entity_id=action.id,
                    action="RECOVERY_ACTION_EXECUTED",
                    previous_state={"status": RecoveryActionStatus.EXECUTING.value},
                    new_state={
                        "status": action.status,
                        "execution_status": "SUCCESS",
                        "provider_reference_id": provider_result.provider_reference_id,
                    },
                    metadata_json={
                        "action_type": action.action_type,
                    },
                )
            else:
                action.status = RecoveryActionStatus.FAILED.value
                action.completed_at = provider_result.executed_at
                action_result = ActionResult(
                    recovery_action_id=action.id,
                    execution_status="FAILED",
                    provider_reference_id=provider_result.provider_reference_id,
                    provider_status_code=provider_result.provider_status_code,
                    failure_reason=provider_result.failure_reason,
                    error_details=provider_result.error_details,
                    response_payload_summary=provider_result.response_payload_summary,
                    executed_at=provider_result.executed_at,
                )
                audit = AuditLog(
                    event_type="RECOVERY_ACTION_FAILED",
                    actor_type=AuditActorType.ACTION_EXECUTOR.value,
                    actor_id="action_dispatcher",
                    recovery_case_id=case.id,
                    entity_type="recovery_actions",
                    entity_id=action.id,
                    action="RECOVERY_ACTION_FAILED",
                    previous_state={"status": RecoveryActionStatus.EXECUTING.value},
                    new_state={
                        "status": action.status,
                        "execution_status": "FAILED",
                        "failure_reason": provider_result.failure_reason,
                    },
                    metadata_json={
                        "action_type": action.action_type,
                    },
                )

            db.add(action_result)
            db.add(audit)
            db.commit()
            db.refresh(action_result)

            logger.info(
                "action_dispatch_completed",
                extra={
                    "action_id": str(action.id),
                    "status": action.status,
                    "provider_ref": provider_result.provider_reference_id,
                },
            )
            return action_result

        except Exception as exc:
            db.rollback()
            logger.error(
                "action_dispatch_persistence_failed",
                extra={"action_id": str(action.id), "error": str(exc)},
            )
            raise ActionExecutionPersistenceError(
                f"Failed to persist action execution result: {exc}"
            ) from exc


action_dispatcher = ActionDispatcher()
