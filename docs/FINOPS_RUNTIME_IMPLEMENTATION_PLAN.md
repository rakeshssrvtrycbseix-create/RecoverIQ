# RecoverIQ — FinOps Runtime Upgrade Implementation Plan

**Author:** Antigravity AI  
**Date:** 2026-09-04  
**Target:** Phase 10I FinOps Control Plane Local/Development Runtime Upgrade  
**Status:** PROPOSED (Pending Review)

---

## 1. Objective & Scope

Upgrade the RecoverIQ FinOps Control Plane (Phase 10I) from a pure static/demo simulation into a hybrid runtime telemetry engine that:
1. Uses **real database queries and local runtime telemetry** for transactions, recovery cases, recovery actions, amounts, resolution metrics, and audit logs.
2. Explicitly exposes **UNAVAILABLE** or **NOT_CONNECTED** for infrastructure that does not exist locally (Redis, AWS, Aurora, CloudWatch, OpenSearch, S3, Kubernetes HPA, NVIDIA T4 GPU).
3. Clearly flags estimated costs as **ESTIMATED** with `"Cloud billing provider not connected"`.
4. Dynamically evaluates **anomalies**, **forecasts** (`INSUFFICIENT_DATA` when inadequate samples exist), and **the 20 readiness gates** based on concrete database/audit conditions.
5. Preserves 100% **backward compatibility** and **financial isolation** ($\Delta \text{RecoveryAction} = 0$, $\Delta \text{Payment} = 0$, $\Delta \text{RecoveryCase} = 0$).
6. Retains the existing deterministic behavior in `DemoFinOpsDataProvider` selectable via `FINOPS_DATA_MODE=demo` or `?mode=demo`.

---

## 2. Provider Architecture

We introduce a clean provider pattern under `backend/app/services/finops/`:

```
backend/app/services/finops/
├── __init__.py               # Package exports
├── base.py                   # FinOpsDataProvider (Abstract Base Class / Interface)
├── demo_provider.py          # DemoFinOpsDataProvider (Existing deterministic logic)
├── runtime_provider.py       # RuntimeFinOpsDataProvider (Real DB queries & telemetry)
├── cost_estimator.py         # CostEstimator (Separated cost model; marks unmetered as UNAVAILABLE/ESTIMATED)
└── factory.py                # get_finops_provider(db, mode=None) -> FinOpsDataProvider
```

### Delegation in `FinOpsService`
`FinOpsService` in `backend/app/services/finops_service.py` acts as a facade, delegating all calls to `self.provider`:
- If `FINOPS_DATA_MODE=runtime` (or `mode="runtime"`): uses `RuntimeFinOpsDataProvider(db)`
- If `FINOPS_DATA_MODE=demo` (or `mode="demo"`): uses `DemoFinOpsDataProvider(db)`

---

## 3. Database Tables Used

The runtime provider queries actual RecoverIQ relational state:

| Database Table | Model Class | Runtime Metrics Derived |
| :--- | :--- | :--- |
| `payments` | [Payment](file:///d:/RecoverIQ/backend/app/models/payment.py) | Total payment count, captured count, failed count, total volume |
| `payment_attempts` | [PaymentAttempt](file:///d:/RecoverIQ/backend/app/models/payment_attempt.py) | Total physical attempts, method distribution, gateway error codes |
| `payment_events` | [PaymentEvent](file:///d:/RecoverIQ/backend/app/models/payment_event.py) | Total webhooks ingested, event types, deduplication counts |
| `recovery_cases` | [RecoveryCase](file:///d:/RecoverIQ/backend/app/models/recovery_case.py) | Total cases, open/analyzing/action-pending cases, resolved cases, amount at risk, recovered amount, case resolution rate |
| `recovery_actions` | [RecoveryAction](file:///d:/RecoverIQ/backend/app/models/recovery_action.py) | Total scheduled actions, completed actions, failed actions, channel breakdown |
| `action_results` | [ActionResult](file:///d:/RecoverIQ/backend/app/models/action_result.py) | Action execution outcomes, provider latency, retry statistics |
| `ml_predictions` | [MLPrediction](file:///d:/RecoverIQ/backend/app/models/ml_prediction.py) | Total ML predictions generated, average confidence scores |
| `audit_logs` | [AuditLog](file:///d:/RecoverIQ/backend/app/models/audit_log.py) | Application activity, FinOps governance mutations, historical snapshot log |
| `WorkerTelemetry` | [worker_telemetry](file:///d:/RecoverIQ/backend/app/workers/telemetry.py) | In-memory worker status, actions claimed, reconciliation runs |

*Note: All queries are strictly read-only (`SELECT`). FinOps never executes `UPDATE`, `INSERT` (except into `audit_logs`), or `DELETE` on operational financial tables.*

---

## 4. API & Schema Changes (100% Backward Compatible)

### Pydantic Schemas (`backend/app/schemas/finops.py`)
All modifications add fields with **defaults**, guaranteeing that existing callers and tests do not break:
1. `ProvenanceMetadata`:
   ```python
   class ProvenanceMetadata(BaseModel):
       source: str  # "runtime" | "demo" | "derived" | "estimated" | "unavailable"
       provider: str
       timestamp: datetime
       confidence: float
   ```
2. `FinOpsSummary`:
   - `data_mode: str = "runtime"`
   - `provider: str = "RuntimeFinOpsDataProvider"`
   - `provenance: dict[str, str] = Field(default_factory=dict)`
3. `ServiceCostMetric` & `CostCategoryBreakdown`:
   - `source: CostSource` (extended to include `RUNTIME_DATABASE`, `UNAVAILABLE`, `NOT_CONNECTED`)
   - `provider: str = "RuntimeFinOpsDataProvider"`
   - `confidence: float = 1.0`
4. `ResourceUtilization`:
   - `state: ResourceEfficiencyState` (extended with `UNAVAILABLE`, `NOT_CONNECTED`)
   - `source: str = "runtime"`
   - `provider: str = "RuntimeFinOpsDataProvider"`
5. `FinOpsScoreBreakdown`:
   - `component_sources: dict[str, str] = Field(default_factory=dict)`
6. `FinOpsReport`:
   - `data_mode: str = "RUNTIME"`
   - `metric_provenance_summary: dict[str, int] = Field(default_factory=dict)`

### API Endpoints (`backend/app/api/finops.py`)
- Endpoints accept optional query param: `mode: str | None = Query(None, description="'runtime' | 'demo'")`
- If omitted, defaults to `get_settings().finops_data_mode`.

---

## 5. Cost Model & Unavailable Infrastructure Handling

### `CostEstimator`
- For local dev, infrastructure costs for unmetered cloud components return:
  - `status = ResourceEfficiencyState.UNAVAILABLE`
  - `allocated_units = "NOT_CONNECTED"`
  - `utilization_pct = 0.0`
  - `source = CostSource.UNAVAILABLE`
  - `disclaimer = "Cloud billing provider not connected"`
- For Database storage:
  - If SQLite: inspect `os.path.getsize(db_path)` safely.
  - If PostgreSQL: run `SELECT pg_database_size(current_database());`.
- For Memory/CPU:
  - Measure actual Python process RSS / CPU using standard library `psutil` or `resource` if available, otherwise safe local process footprint.

---

## 6. Dynamic Anomalies & Forecasts

### Dynamic Anomalies
- Query `AuditLog` and `PaymentEvent` / `PaymentAttempt` timestamps.
- Compare recent event rates (last 1 hour vs. last 24 hours).
- If failure rate or error code spikes: generate dynamic `CostAnomaly` with real deviation, severity, and runtime SHA-256 evidence hash.
- If no statistical anomaly exists: return empty list `[]` (or low-severity informational baseline), NEVER static fabricated anomalies.

### Dynamic Forecasts
- If fewer than 7 days of audit/payment data exist:
  - Return `forecast_state = ForecastState.INSUFFICIENT_DATA`.
  - Scenario list includes clear explanation: `"Insufficient historical transaction observations to project reliable trend"`.
- In demo mode: returns the deterministic 5-scenario projections.

---

## 7. Dynamic Readiness Gate Evaluation

Each of the 20 gates evaluates real code/database conditions:
- `GATE-FIN-01` (Cost Allocation Coverage): Verify registered microservices in catalog.
- `GATE-FIN-02` (Cost Attribution Integrity): Verify sum of allocations matches total spend.
- `GATE-FIN-03` (Budget Configuration): Query `AuditLog` for `BUDGET_CONFIGURED`. If none, status = `FAIL` or `WARN`.
- `GATE-FIN-04` (Budget Burn Monitoring): Compare actual spend against configured budget.
- `GATE-FIN-05` (Forecast Availability): Check if forecast engine has sufficient data; else `WARN` / `NOT_APPLICABLE`.
- `GATE-FIN-06` (Forecast Confidence): Check forecast confidence $> 0.85$.
- `GATE-FIN-07` (Resource Utilization): Check if host resource monitor is reachable; else `NOT_APPLICABLE`.
- `GATE-FIN-08` (Capacity Efficiency): Evaluate headroom on real database storage.
- `GATE-FIN-09` (Waste Detection): Check for orphaned/stale scheduled actions in `RecoveryAction`.
- `GATE-FIN-10` (Unit Economics): Check if `Payment` and `RecoveryCase` records exist to compute unit metrics.
- `GATE-FIN-11` (Service Cost Visibility): Check service mapping.
- `GATE-FIN-12` (Database Cost Visibility): Check if database size is measurable.
- `GATE-FIN-13` (ML Cost Visibility): Check if `MLPrediction` table exists and is accessible.
- `GATE-FIN-14` (Webhook Cost Visibility): Check if `PaymentEvent` table exists and is accessible.
- `GATE-FIN-15` (Cost Anomaly Detection): Check active unmitigated anomalies count.
- `GATE-FIN-16` (PII/Secret Sanitization): Verify no customer PII exists in FinOps audit events.
- `GATE-FIN-17` (Financial Isolation): Verify PolicyEngine supremacy invariant ($\Delta \text{Actions} = 0$).
- `GATE-FIN-18` (RBAC Enforcement): Verify JWT security handlers are registered on FinOps router.
- `GATE-FIN-19` (Optimization Governance): Verify optimization recommendations require human approval.
- `GATE-FIN-20` (Report Integrity): Verify HMAC-SHA256 signature generation and verification.

---

## 8. Files to Create and Modify

### Files to Create:
1. `docs/FINOPS_RUNTIME_IMPLEMENTATION_PLAN.md` (this plan)
2. `backend/app/services/finops/__init__.py`
3. `backend/app/services/finops/base.py`
4. `backend/app/services/finops/demo_provider.py`
5. `backend/app/services/finops/runtime_provider.py`
6. `backend/app/services/finops/cost_estimator.py`
7. `backend/app/services/finops/factory.py`
8. `backend/tests/test_finops_runtime_provider.py`

### Files to Modify:
1. `backend/app/core/config.py`: Add `finops_data_mode: str = "runtime"`
2. `backend/app/models/enums.py`: Add `UNAVAILABLE`, `NOT_CONNECTED` to `CostSource` and `ResourceEfficiencyState`; add `INSUFFICIENT_DATA` to `ForecastState`; add `NOT_APPLICABLE` to `FinOpsGateStatus`.
3. `backend/app/schemas/finops.py`: Add provenance, data mode, and compatibility fields.
4. `backend/app/services/finops_service.py`: Refactor to delegate to `FinOpsDataProvider`.
5. `backend/app/api/finops.py`: Add optional `mode` query parameter.
6. `backend/tests/conftest.py`: Configure test settings to default `finops_data_mode="demo"` for existing deterministic test suite.

---

## 9. Test Strategy

1. **Unit Tests for Providers:**
   - Test `DemoFinOpsDataProvider` returns the exact deterministic values expected by existing suite.
   - Test `RuntimeFinOpsDataProvider` correctly queries `Payment`, `RecoveryCase`, `RecoveryAction`, `PaymentAttempt`, `AuditLog`.
2. **Provider Selection Tests:**
   - Test switching via `FINOPS_DATA_MODE=demo` vs `FINOPS_DATA_MODE=runtime`.
   - Test query param override `?mode=demo`.
3. **Unavailable Infrastructure Handling:**
   - Verify Redis, AWS, Aurora, CloudWatch, OpenSearch, S3, HPA, GPU return `UNAVAILABLE` / `NOT_CONNECTED` in runtime mode.
4. **Dynamic Gate Evaluation:**
   - Verify gates dynamically reflect database state instead of a hardcoded 20/20 PASS.
5. **Dynamic Anomaly & Forecast:**
   - Verify `INSUFFICIENT_DATA` when inadequate samples exist.
6. **Financial Isolation:**
   - Run `test_finops_financial_isolation.py` and verify 0 mutations on financial tables.
7. **Full Suite Regression:**
   - Run `pytest -v` across all 680+ tests.
   - Run frontend checks: `npm run lint`, `npx tsc --noEmit`, `npm run build`.
