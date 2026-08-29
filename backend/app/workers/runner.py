import asyncio
import logging
from datetime import UTC, datetime
from typing import Any, Callable

from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.models import ActionResult
from app.providers.base import ActionProvider
from app.workers.reconciliation_worker import (
    ReconciliationWorker,
    reconciliation_worker,
)
from app.workers.recovery_worker import RecoveryWorker, recovery_worker
from app.workers.telemetry import worker_telemetry

logger = logging.getLogger(__name__)


class WorkerRunner:
    """
    Orchestration runner that manages background polling, periodic reconciliation,
    and lifecycle health for the RecoverIQ recovery system.

    Guarantees:
    - Clean startup and graceful shutdown.
    - Configurable polling and reconciliation intervals.
    - Exception isolation: Errors in one loop or action never crash the runner.
    """

    def __init__(
        self,
        settings: Settings | None = None,
        rec_worker: RecoveryWorker | None = None,
        recon_worker: ReconciliationWorker | None = None,
    ) -> None:
        self.settings = settings or get_settings()
        self.recovery_worker = rec_worker or recovery_worker
        self.reconciliation_worker = recon_worker or reconciliation_worker
        self._running = False
        self._tasks: list[asyncio.Task] = []

    @property
    def is_running(self) -> bool:
        """Check whether the worker runner is actively running."""
        return self._running

    def poll_once(
        self,
        db: Session,
        batch_size: int | None = None,
        provider: ActionProvider | None = None,
        as_of: datetime | None = None,
    ) -> list[ActionResult]:
        """Execute a single synchronous polling sweep over due actions."""
        return self.recovery_worker.poll_and_dispatch(
            db=db,
            batch_size=batch_size,
            provider=provider,
            as_of=as_of,
        )

    def reconcile_once(
        self,
        db: Session,
        threshold_minutes: int | None = None,
        provider: ActionProvider | None = None,
        as_of: datetime | None = None,
    ) -> list[ActionResult]:
        """Execute a single synchronous reconciliation sweep."""
        return self.reconciliation_worker.run_reconciliation(
            db=db,
            threshold_minutes=threshold_minutes,
            provider=provider,
            as_of=as_of,
        )

    def start(self) -> None:
        """Mark runner as active."""
        self._running = True
        worker_telemetry.set_status("RUNNING")
        logger.info("worker_runner_started")

    def stop(self) -> None:
        """Signal all worker loops to stop gracefully."""
        self._running = False
        for task in self._tasks:
            if not task.done():
                task.cancel()
        self._tasks.clear()
        worker_telemetry.set_status("STOPPED")
        logger.info("worker_runner_stopped")

    async def run_polling_loop(
        self,
        session_factory: Callable[[], Session],
        poll_interval: float | None = None,
    ) -> None:
        """Continuous async polling loop for due scheduled actions."""
        interval = poll_interval or self.settings.action_poll_interval_seconds
        logger.info(
            "worker_polling_loop_started",
            extra={"interval_seconds": interval},
        )

        while self._running:
            db = session_factory()
            try:
                self.poll_once(db=db)
            except Exception as exc:
                db.rollback()
                logger.error(
                    "worker_polling_loop_cycle_error",
                    extra={"error": str(exc)},
                )
                worker_telemetry.record_error(f"Polling loop error: {exc}")
            finally:
                db.close()

            try:
                await asyncio.sleep(interval)
            except asyncio.CancelledError:
                break

    async def run_reconciliation_loop(
        self,
        session_factory: Callable[[], Session],
        reconciliation_interval: float | None = None,
    ) -> None:
        """Continuous async reconciliation loop for stale executing actions."""
        interval = (
            reconciliation_interval
            or self.settings.reconciliation_interval_seconds
        )
        logger.info(
            "worker_reconciliation_loop_started",
            extra={"interval_seconds": interval},
        )

        while self._running:
            db = session_factory()
            try:
                self.reconcile_once(db=db)
            except Exception as exc:
                db.rollback()
                logger.error(
                    "worker_reconciliation_loop_cycle_error",
                    extra={"error": str(exc)},
                )
                worker_telemetry.record_error(f"Reconciliation loop error: {exc}")
            finally:
                db.close()

            try:
                await asyncio.sleep(interval)
            except asyncio.CancelledError:
                break

    def get_health(self) -> dict[str, Any]:
        """Return sanitized worker status and performance metrics."""
        return worker_telemetry.to_dict()


worker_runner = WorkerRunner()
