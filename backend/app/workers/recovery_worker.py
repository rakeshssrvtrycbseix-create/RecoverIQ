import logging
import uuid
from datetime import UTC, datetime

from sqlalchemy import update
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.models import (
    ActionResult,
    RecoveryAction,
    RecoveryActionStatus,
)
from app.providers.base import ActionProvider
from app.services.action_dispatcher import (
    ActionDispatchError,
    action_dispatcher,
)
from app.workers.telemetry import worker_telemetry

logger = logging.getLogger(__name__)


class RecoveryWorker:
    """
    Background worker that polls due SCHEDULED RecoveryActions, atomically claims them,
    and executes them through the ActionDispatcher pipeline.

    Guarantees:
    - Mutually exclusive execution: Atomic row-level claim ensures only one worker executes an action.
    - Isolation: An error or crash during one action never prevents other due actions from executing.
    - Zero PII or credential logging.
    - Uses ActionDispatcher without bypassing PolicyEngine or ProviderFactory.
    """

    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()

    def fetch_due_action_ids(
        self,
        db: Session,
        batch_size: int | None = None,
        as_of: datetime | None = None,
    ) -> list[uuid.UUID]:
        """Query primary keys of SCHEDULED actions due for execution."""
        now_utc = as_of or datetime.now(UTC)
        if now_utc.tzinfo is None:
            now_utc = now_utc.replace(tzinfo=UTC)

        limit = batch_size or self.settings.worker_batch_size

        actions = (
            db.query(RecoveryAction.id)
            .filter(
                RecoveryAction.status == RecoveryActionStatus.SCHEDULED.value,
                RecoveryAction.scheduled_for <= now_utc,
            )
            .order_by(RecoveryAction.scheduled_for.asc())
            .limit(limit)
            .all()
        )

        return [row[0] for row in actions]

    def claim_action(
        self,
        db: Session,
        action_id: uuid.UUID,
        as_of: datetime | None = None,
    ) -> bool:
        """
        Atomically claim a SCHEDULED action by transitioning it to EXECUTING.

        Returns True if this worker successfully claimed the action (rowcount == 1).
        Returns False if another worker claimed it or it is no longer SCHEDULED.
        """
        now_utc = as_of or datetime.now(UTC)
        if now_utc.tzinfo is None:
            now_utc = now_utc.replace(tzinfo=UTC)

        try:
            stmt = (
                update(RecoveryAction)
                .where(
                    RecoveryAction.id == action_id,
                    RecoveryAction.status == RecoveryActionStatus.SCHEDULED.value,
                )
                .values(
                    status=RecoveryActionStatus.EXECUTING.value,
                    dispatched_at=now_utc,
                )
            )
            result = db.execute(stmt)
            db.commit()
            return result.rowcount == 1
        except Exception as exc:
            db.rollback()
            logger.error(
                "action_claim_failed_exception",
                extra={"action_id": str(action_id), "error": str(exc)},
            )
            return False

    def process_action(
        self,
        db: Session,
        action_id: uuid.UUID,
        provider: ActionProvider | None = None,
        as_of: datetime | None = None,
    ) -> ActionResult | None:
        """Atomically claim and dispatch a single recovery action."""
        now_utc = as_of or datetime.now(UTC)
        if now_utc.tzinfo is None:
            now_utc = now_utc.replace(tzinfo=UTC)

        # 1. Atomic claim check
        claimed = self.claim_action(db=db, action_id=action_id, as_of=now_utc)
        if not claimed:
            logger.info(
                "action_claim_skipped",
                extra={
                    "action_id": str(action_id),
                    "reason": "already_claimed_or_not_scheduled",
                },
            )
            return None

        worker_telemetry.record_claim(1)

        # 2. Dispatch through authoritative ActionDispatcher
        try:
            result = action_dispatcher.dispatch_action(
                db=db,
                recovery_action_id=action_id,
                provider=provider,
                as_of=now_utc,
                already_claimed=True,
            )

            if result:
                worker_telemetry.record_action_outcome(result.execution_status)

            return result

        except ActionDispatchError as exc:
            logger.warning(
                "action_dispatch_domain_error",
                extra={"action_id": str(action_id), "error": str(exc)},
            )
            worker_telemetry.record_error(str(exc))
            return None
        except Exception as exc:
            logger.error(
                "action_dispatch_unexpected_error",
                extra={"action_id": str(action_id), "error": str(exc)},
            )
            worker_telemetry.record_error(str(exc))
            return None

    def poll_and_dispatch(
        self,
        db: Session,
        batch_size: int | None = None,
        provider: ActionProvider | None = None,
        as_of: datetime | None = None,
    ) -> list[ActionResult]:
        """Perform a single polling cycle over all due scheduled actions."""
        now_utc = as_of or datetime.now(UTC)
        if now_utc.tzinfo is None:
            now_utc = now_utc.replace(tzinfo=UTC)

        due_action_ids = self.fetch_due_action_ids(
            db=db, batch_size=batch_size, as_of=now_utc
        )
        worker_telemetry.record_poll(queue_depth=len(due_action_ids))

        dispatched_results: list[ActionResult] = []

        for action_id in due_action_ids:
            # Execute each action independently with failure isolation
            try:
                res = self.process_action(
                    db=db,
                    action_id=action_id,
                    provider=provider,
                    as_of=now_utc,
                )
                if res:
                    dispatched_results.append(res)
            except Exception as exc:
                db.rollback()
                logger.error(
                    "worker_polling_loop_isolated_item_error",
                    extra={"action_id": str(action_id), "error": str(exc)},
                )
                worker_telemetry.record_error(str(exc))

        return dispatched_results


recovery_worker = RecoveryWorker()
