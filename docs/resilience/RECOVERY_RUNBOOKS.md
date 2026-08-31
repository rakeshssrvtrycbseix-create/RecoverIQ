# Governed Recovery Runbooks Specification
**RecoverIQ — Phase 10C Specification**

---

## 1. Runbook Framework & Execution Standards

RecoverIQ defines **9 structured recovery runbooks** covering critical operational failure modes. Each runbook specifies:
- Explicit preconditions before execution
- Step-by-step ordered recovery procedure
- Post-recovery verification criteria
- Deterministic rollback procedure
- Minimum required RBAC role (`OPERATOR` or `ADMIN`)
- Estimated duration and target RTO/RPO

---

## 2. Production Runbooks Catalog

### 1. `RB-DB-OUTAGE`: Relational Database Failover & Recovery
- **Required Role:** `ADMIN` | **Est. Duration:** 5 mins | **Target RTO:** 120s | **Target RPO:** 30s
- **Preconditions:**
  - Primary database unresponsive or returning connection refused errors.
  - Replica database confirmed in sync within 30 seconds of primary.
- **Ordered Steps:**
  1. Isolate failed primary node from database connection pool.
  2. Promote designated read-replica to primary read-write role.
  3. Update SQLAlchemy connection string pool to point to newly promoted primary.
  4. Execute dry-run heartbeat transaction on promoted node.
  5. Unpause application API gateway and worker dispatch pools.
- **Verification Steps:**
  - Query `SELECT 1` returns successful response within 10ms.
  - Test write operation on `AuditLog` completes without errors.
- **Rollback Procedure:**
  - If promotion fails, revert DNS/connection string to standby secondary cluster and retry.

---

### 2. `RB-REDIS-RECOVERY`: Redis Cache & Rate-Limiter Recovery
- **Required Role:** `OPERATOR` | **Est. Duration:** 2 mins | **Target RTO:** 45s | **Target RPO:** 0s
- **Preconditions:**
  - Redis sentinel reporting master node down or connection timeouts.
- **Ordered Steps:**
  1. Enable in-memory fallback rate limiter in FastAPI middleware.
  2. Trigger Redis Sentinel failover to secondary replica.
  3. Validate Redis memory usage and eviction policy settings.
  4. Flush corrupted token revocation cache and reload active tokens from DB.
  5. Re-enable Redis-backed distributed rate limiting.
- **Verification Steps:**
  - `redis-cli ping` returns `PONG`.
  - Rate limiter middleware processes requests with Redis backend.
- **Rollback Procedure:**
  - Retain in-memory fallback rate limiter until Redis cluster stabilizes.

---

### 3. `RB-WORKER-RECOVERY`: Recovery Worker & Task Processor Recovery
- **Required Role:** `OPERATOR` | **Est. Duration:** 3 mins | **Target RTO:** 60s | **Target RPO:** 0s
- **Preconditions:**
  - Worker process heartbeat missing for > 60 seconds.
- **Ordered Steps:**
  1. Terminate orphaned or unresponsive worker processes.
  2. Inspect `RecoveryAction` table for stuck `IN_PROGRESS` actions.
  3. Reset orphaned actions with elapsed timeout back to `PENDING`.
  4. Spawn fresh worker pool with configured concurrency limits.
  5. Monitor action dispatch rates and error rates.
- **Verification Steps:**
  - Worker processes claim and execute `PENDING` actions sequentially.
  - Action latency returns below 500ms.
- **Rollback Procedure:**
  - Reduce worker concurrency to 1 to prevent resource starvation.

---

### 4. `RB-QUEUE-BACKLOG`: Queue Backlog Mitigation & Drain
- **Required Role:** `OPERATOR` | **Est. Duration:** 4 mins | **Target RTO:** 90s | **Target RPO:** 0s
- **Preconditions:**
  - Pending recovery action queue depth > 100 actions.
- **Ordered Steps:**
  1. Prioritize queue items by `amount_at_risk` descending.
  2. Scale worker processes horizontally (2x replica count).
  3. Batch low-priority webhook event processing.
  4. Enable backpressure throttling on incoming case ingestion.
  5. Drain high-priority recovery queues first.
- **Verification Steps:**
  - Pending queue depth decreases below 50 within 5 minutes.
- **Rollback Procedure:**
  - Descale worker replicas after queue depth normalizes.

---

### 5. `RB-WEBHOOK-RECOVERY`: Webhook Ingestion Buffer & Replay
- **Required Role:** `OPERATOR` | **Est. Duration:** 2 mins | **Target RTO:** 30s | **Target RPO:** 10s
- **Preconditions:**
  - Ingestion failure rate > 5% or missed payment webhook events reported.
- **Ordered Steps:**
  1. Inspect webhook dead-letter queue (DLQ) for dropped payloads.
  2. Verify HMAC-SHA256 signature secret configuration.
  3. Replay unhandled webhook events through sanitization pipeline.
  4. Reconcile payment statuses against Razorpay API.
  5. Resume standard real-time webhook ingestion stream.
- **Verification Steps:**
  - Webhook processing latency < 50ms with 0 dropped events.
- **Rollback Procedure:**
  - Route malformed payloads to quarantine table for manual operator review.

---

### 6. `RB-ML-SERVICE`: ML Inference Degradation & Rule Fallback
- **Required Role:** `OPERATOR` | **Est. Duration:** 1 min | **Target RTO:** 15s | **Target RPO:** 0s
- **Preconditions:**
  - ML inference latency > 200ms or model prediction errors detected.
- **Ordered Steps:**
  1. Enable deterministic champion heuristic policy fallback.
  2. Route all recovery case scoring through baseline rule engine.
  3. Isolate degraded ML model artifact from prediction path.
  4. Log fallback telemetry event in `AuditLog`.
  5. Notify ML operations team for offline model recalibration.
- **Verification Steps:**
  - Recovery decision latency drops below 20ms.
  - Policy decisions continue with confidence = 1.0 heuristic score.
- **Rollback Procedure:**
  - Re-enable ML inference after model passes canary validation.

---

### 7. `RB-AUDITLOG-RECOVERY`: AuditLog Stream Continuity Recovery
- **Required Role:** `ADMIN` | **Est. Duration:** 3 mins | **Target RTO:** 45s | **Target RPO:** 15s
- **Preconditions:**
  - AuditLog write errors or event sequence gap detected.
- **Ordered Steps:**
  1. Redirect active audit writes to emergency in-memory circular buffer.
  2. Verify database disk space and table lock status for `audit_logs`.
  3. Clear stuck locks and restore database write pipeline.
  4. Flush emergency buffer to `audit_logs` table preserving event timestamps.
  5. Verify audit event sequence integrity and hash chains.
- **Verification Steps:**
  - AuditLog writes succeed with zero buffer drop count.
- **Rollback Procedure:**
  - Persist unwritten audit buffer to encrypted disk file if database remains locked.

---

### 8. `RB-PAYMENT-PROVIDER`: Payment Gateway Provider Outage
- **Required Role:** `ADMIN` | **Est. Duration:** 4 mins | **Target RTO:** 60s | **Target RPO:** 0s
- **Preconditions:**
  - Razorpay gateway returning 5xx status or elevated error rate > 20%.
- **Ordered Steps:**
  1. Pause automated payment retry action dispatching in PolicyEngine.
  2. Queue recovery actions with exponential backoff (1h, 4h, 24h).
  3. Notify merchant operations dashboard with gateway advisory notice.
  4. Monitor Razorpay status page and automated observational health probes.
  5. Resume controlled canary dispatch when provider error rate drops below 1%.
- **Verification Steps:**
  - Provider probe returns successful observational health check.
- **Rollback Procedure:**
  - Keep dispatch paused until gateway status is confirmed OPERATIONAL.

---

### 9. `RB-REGIONAL-DISASTER`: Regional Outage & Complete Disaster Failover
- **Required Role:** `ADMIN` | **Est. Duration:** 10 mins | **Target RTO:** 300s | **Target RPO:** 60s
- **Preconditions:**
  - Primary cloud region completely offline or network partition detected.
- **Ordered Steps:**
  1. Declare disaster mode and activate secondary disaster recovery region.
  2. Update global DNS / Cloudflare routing to secondary regional endpoint.
  3. Restore latest database snapshot and apply WAL transaction logs.
  4. Initialize API gateway, PolicyEngine, and worker pools in secondary region.
  5. Execute end-to-end recovery verification test across all 11 services.
  6. Broadcast operational status update to merchant dashboard.
- **Verification Steps:**
  - All 11 services report HEALTHY status in secondary region.
  - Recovery readiness score reaches $\ge 90\%$.
- **Rollback Procedure:**
  - Plan graceful failback to primary region during scheduled maintenance window.
