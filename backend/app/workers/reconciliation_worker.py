import logging
import threading
from datetime import UTC, datetime

from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.models import ActionResult
from app.providers.base import ActionProvider
from app.services.action_reconciliation import action_reconciliation_service
from app.workers.telemetry import worker_telemetry

logger = logging.getLogger(__name__)


class ReconciliationWorker:
    """
    Background worker that periodically triggers ActionReconciliationService
    to resolve stale EXECUTING actions with external gateways.

    Guarantees:
    - Non-overlapping execution: Protects against concurrent/overlapping sweeps.
    - Failure isolation: Telemetry tracks outcomes and errors without crashing runner.
    - Zero PII or credential logging.
    """

    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()
        self._execution_lock = threading.Lock()
        self._is_running = False

    def is_running(self) -> bool:
        """Check whether a reconciliation sweep is currently in-flight."""
        with self._execution_lock:
            return self._is_running

    def run_reconciliation(
        self,
        db: Session,
        threshold_minutes: int | None = None,
        provider: ActionProvider | None = None,
        as_of: datetime | None = None,
    ) -> list[ActionResult]:
        """Execute a single reconciliation sweep over stale EXECUTING actions."""
        # Prevent overlapping execution
        with self._execution_lock:
            if self._is_running:
                logger.info("reconciliation_sweep_skipped_already_running")
                return []
            self._is_running = True

        now_utc = as_of or datetime.now(UTC)
        if now_utc.tzinfo is None:
            now_utc = now_utc.replace(tzinfo=UTC)

        try:
            results = action_reconciliation_service.reconcile_stale_actions(
                db=db,
                threshold_minutes=threshold_minutes,
                provider=provider,
                as_of=now_utc,
            )

            completed = sum(
                1 for r in results if r.execution_status == "SUCCESS"
            )
            failed = sum(
                1 for r in results if r.execution_status == "FAILED"
            )
            deferred = len(results) - (completed + failed)

            worker_telemetry.record_reconciliation(
                completed=completed,
                failed=failed,
                deferred=max(0, deferred),
            )

            return results

        except Exception as exc:
            db.rollback()
            logger.error(
                "reconciliation_worker_sweep_failed",
                extra={"error": str(exc)},
            )
            worker_telemetry.record_error(f"Reconciliation error: {exc}")
            return []

        finally:
            with self._execution_lock:
                self._is_running = False


reconciliation_worker = ReconciliationWorker()
