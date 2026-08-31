# Phase 10F: Performance Engineering & Incident Remediation Runbooks

## 1. High Latency & Tail Degradation Runbook (P95 > 100ms / P99 > 250ms)

### Detection
- `GATE-PERF-01` or `GATE-PERF-02` transitions to `WARN` or `FAIL`.
- Performance Health Score drops below 80.0.

### Triage & Diagnostics
1. Check **11-Service Matrix** in Intelligence Control Plane (Tab 18) to isolate affected component.
2. If `PostgreSQL Primary` P95 > 50ms:
   - Check active connection pool utilization.
   - Inspect lock wait times and long-running transactions.
3. If `ML Inference Engine` P95 > 100ms:
   - Inspect ML inference queue depth and model warm-up status.
4. If `API Gateway` latency is elevated but backend services are fast:
   - Check Redis command latency and network transport metrics.

### Mitigation Actions
- Enable Redis query caching for high-read models.
- If database pool utilization > 75%, scale connection pool or deploy read replica routing.
- If ML queue is saturated, increase tensor worker pool concurrency.

---

## 2. Queue Backpressure & Buffer Saturation Runbook

### Detection
- Webhook queue depth > 500 or drain time > 5.0s.
- `GATE-PERF-11` or `GATE-PERF-13` triggers `WARN`.

### Remediation
1. Verify Redis memory consumption and worker heartbeat.
2. Scale `RecoveryWorker` concurrency from baseline 10 to 25 workers.
3. Verify webhook deduplication rate to prevent replay attacks from swamping queues.

---

## 3. Database Connection Contention Runbook

### Detection
- Active database connections > 75 / 100.
- `GATE-PERF-05` triggers `WARN`.

### Remediation
1. Inspect connection leaks in FastAPI dependency injection lifecycle.
2. Verify all SQLAlchemy sessions are explicitly closed or returned to the pool.
3. Enable PgBouncer connection pooling in transaction mode.
