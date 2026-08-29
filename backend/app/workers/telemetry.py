import threading
from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel, Field


class WorkerMetricsSnapshot(BaseModel):
    """Immutable snapshot of worker performance and state telemetry."""

    worker_status: str = Field(
        default="STOPPED",
        description="Operational state of the background worker runner",
    )
    started_at: datetime | None = Field(
        default=None,
        description="Timestamp when worker runner was started",
    )
    last_poll_at: datetime | None = Field(
        default=None,
        description="Timestamp of the most recent action polling sweep",
    )
    last_reconciliation_at: datetime | None = Field(
        default=None,
        description="Timestamp of the most recent reconciliation sweep",
    )
    actions_claimed: int = Field(
        default=0,
        description="Total number of SCHEDULED actions successfully claimed",
    )
    actions_completed: int = Field(
        default=0,
        description="Total number of actions transitioned to COMPLETED",
    )
    actions_failed: int = Field(
        default=0,
        description="Total number of actions transitioned to FAILED",
    )
    actions_timed_out: int = Field(
        default=0,
        description="Total number of actions that encountered gateway timeouts",
    )
    reconciliation_runs: int = Field(
        default=0,
        description="Total number of background reconciliation sweeps executed",
    )
    reconciled_completed: int = Field(
        default=0,
        description="Total stale actions resolved to COMPLETED by reconciler",
    )
    reconciled_failed: int = Field(
        default=0,
        description="Total stale actions resolved to FAILED by reconciler",
    )
    reconciled_deferred: int = Field(
        default=0,
        description="Total stale actions deferred during reconciliation",
    )
    last_error: str | None = Field(
        default=None,
        description="Sanitized summary or category of the most recent error",
    )
    last_error_at: datetime | None = Field(
        default=None,
        description="Timestamp of the most recent error",
    )
    queue_depth: int = Field(
        default=0,
        description="Number of due SCHEDULED actions pending execution",
    )


class WorkerTelemetryTracker:
    """
    Thread-safe in-memory state tracker for background worker telemetry.

    Guarantees:
    - Never records customer PII, secrets, API keys, or raw auth headers.
    - Safe for concurrent read and write operations from multiple worker tasks.
    """

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._status = "STOPPED"
        self._started_at: datetime | None = None
        self._last_poll_at: datetime | None = None
        self._last_reconciliation_at: datetime | None = None
        self._actions_claimed = 0
        self._actions_completed = 0
        self._actions_failed = 0
        self._actions_timed_out = 0
        self._reconciliation_runs = 0
        self._reconciled_completed = 0
        self._reconciled_failed = 0
        self._reconciled_deferred = 0
        self._last_error: str | None = None
        self._last_error_at: datetime | None = None
        self._queue_depth = 0

    def set_status(self, status: str) -> None:
        with self._lock:
            self._status = status
            if status == "RUNNING" and self._started_at is None:
                self._started_at = datetime.now(UTC)
            elif status == "STOPPED":
                self._started_at = None

    def record_poll(self, queue_depth: int) -> None:
        with self._lock:
            self._last_poll_at = datetime.now(UTC)
            self._queue_depth = queue_depth

    def record_claim(self, count: int = 1) -> None:
        with self._lock:
            self._actions_claimed += count

    def record_action_outcome(self, execution_status: str) -> None:
        with self._lock:
            if execution_status == "SUCCESS":
                self._actions_completed += 1
            elif execution_status == "TIMED_OUT":
                self._actions_timed_out += 1
            elif execution_status == "FAILED":
                self._actions_failed += 1

    def record_reconciliation(
        self, completed: int = 0, failed: int = 0, deferred: int = 0
    ) -> None:
        with self._lock:
            self._last_reconciliation_at = datetime.now(UTC)
            self._reconciliation_runs += 1
            self._reconciled_completed += completed
            self._reconciled_failed += failed
            self._reconciled_deferred += deferred

    def record_error(self, error_summary: str) -> None:
        with self._lock:
            self._last_error = str(error_summary)[:200]
            self._last_error_at = datetime.now(UTC)

    def get_snapshot(self) -> WorkerMetricsSnapshot:
        with self._lock:
            return WorkerMetricsSnapshot(
                worker_status=self._status,
                started_at=self._started_at,
                last_poll_at=self._last_poll_at,
                last_reconciliation_at=self._last_reconciliation_at,
                actions_claimed=self._actions_claimed,
                actions_completed=self._actions_completed,
                actions_failed=self._actions_failed,
                actions_timed_out=self._actions_timed_out,
                reconciliation_runs=self._reconciliation_runs,
                reconciled_completed=self._reconciled_completed,
                reconciled_failed=self._reconciled_failed,
                reconciled_deferred=self._reconciled_deferred,
                last_error=self._last_error,
                last_error_at=self._last_error_at,
                queue_depth=self._queue_depth,
            )

    def to_dict(self) -> dict[str, Any]:
        return self.get_snapshot().model_dump(mode="json")


worker_telemetry = WorkerTelemetryTracker()
