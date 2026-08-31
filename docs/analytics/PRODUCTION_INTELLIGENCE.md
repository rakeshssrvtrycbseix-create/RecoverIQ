# Production Strategy Promotion, Automated Guardrails & Continuous Intelligence (Phase 9G)

## 1. Overview & Objective

Phase 9G establishes a **governed, continuous production lifecycle** for recovery strategies in RecoverIQ. Building upon Phase 9F (Controlled Canary Rollouts), Phase 9G enforces **8 deterministic promotion safety gates**, continuous telemetry monitoring, multi-factor safety guardrails (`HEALTHY`, `WARNING`, `DEGRADED`, `ROLLBACK_RECOMMENDED`), drift tracking, and integer-paise financial yield telemetry.

```
Controlled Canary Experiment (Phase 9F)
        │
        ▼
Continuous Production Telemetry & Drift Monitoring (Phase 9G)
        │
        ▼  [Evaluate 8 Deterministic Safety Gates]
Promotion Readiness Engine
        ├── ✗ Any Gate Fails ──▶ PROMOTION_BLOCKED (HTTP 409 Conflict)
        │
        └── ✓ All 8 Gates Pass ─▶ PROMOTION_READY
                                       │
                                       ▼  [Admin Role Execution Only]
                                Full 100% Production Promotion
                                       │
                                       ▼
                       Continuous Guardrails & Telemetry
                (Automated ROLLBACK_RECOMMENDED alerts if metrics regress)
```

---

## 2. Fundamental Architectural Invariants

1. **PolicyEngine Remains Authoritative**: No promotion, monitoring, or rollback operation ever bypasses the authoritative `PolicyEngine`. The execution pipeline remains:
   $$\text{PolicyEngine} \longrightarrow \text{RecoveryAction} \longrightarrow \text{Worker} \longrightarrow \text{Dispatcher} \longrightarrow \text{RazorpayProvider}$$
2. **Zero Financial Mutation on Promotion**: Promoting a strategy or evaluating readiness mutates **only** the governance activation state (`StrategyActivationStatus.PRODUCTION` with `rollout_percentage=100`). It creates **zero** `RecoveryAction` records, modifies zero payment statuses, and makes zero gateway API calls.
3. **Zero Database Migrations**: All promotion events (`PRODUCTION_PROMOTION_EVALUATED`, `PRODUCTION_PROMOTION_APPROVED`, `PRODUCTION_PROMOTED`, `PRODUCTION_MONITORING_WARNING`, `PRODUCTION_ROLLBACK_RECOMMENDED`, etc.) are immutably persisted using the existing `AuditLog` entity (`entity_type="strategy_activation"`). All 12 core tables remain untouched.
4. **Integer Paise Financial Representation**: All monetary quantities (`incremental_erv_paise`, `amount_at_risk_paise`, `amount_recovered_paise`, `expected_recovery_value_paise`) are strictly maintained as integer paise.
5. **Zero-PII & Secrets Enforced**: API responses contain zero customer names, email addresses, phone numbers, raw card numbers, webhook secrets, or gateway tokens.
6. **Strict RBAC & Verified Identity**:
   - `Viewer`: Read-only access to `/intelligence/production` and `/activations/{id}/promotion-readiness`.
   - `Operator`: Cannot execute 100% full production promotion (HTTP 403 Forbidden).
   - `Admin`: Required for `/activations/{id}/promote` execution. Actor identity is extracted strictly from verified JWT claims (`current_user.id`, `current_user.role`). Client request payloads cannot spoof the actor.

---

## 3. The 8 Deterministic Promotion Safety Gates

A strategy activation cannot be promoted to 100% production unless all 8 rules pass simultaneously:

| # | Rule Identifier | Validation Condition | Blocker Code (on Failure) |
|---|---|---|---|
| 1 | `MIN_SAMPLE_SIZE` | Evaluated cohort sample size $N \ge 100$ | `PROMOTION_BLOCKED_INSUFFICIENT_SAMPLE` |
| 2 | `POSITIVE_UPLIFT` | Treatment recovery rate > Control recovery rate ($p_t > p_c$) | `PROMOTION_BLOCKED_NO_UPLIFT` |
| 3 | `MIN_PRACTICAL_UPLIFT` | Absolute recovery uplift $\ge +2.0\%$ ($p_t - p_c \ge 0.02$) | `PROMOTION_BLOCKED_LOW_EFFECT` |
| 4 | `CONFIDENCE_INTERVAL` | $95\%$ Confidence interval upper bound $\ge 0$ ($CI_{\text{high}} \ge 0$) | `PROMOTION_BLOCKED_NEGATIVE_EFFECT` |
| 5 | `MODEL_GOVERNANCE` | Model governance status is not `DEGRADED` and has valid data | `PROMOTION_BLOCKED_MODEL_DEGRADED` / `PROMOTION_BLOCKED_GOVERNANCE_DATA` |
| 6 | `DATA_QUALITY` | Zero invalid predictions in prediction store | `PROMOTION_BLOCKED_DATA_QUALITY` |
| 7 | `ROLLBACK_STATUS` | No active `ROLLBACK_RECOMMENDED` health alert | `PROMOTION_BLOCKED_ROLLBACK_ACTIVE` |
| 8 | `RECOMMENDATION_TTL` | Strategy activation TTL is not expired (`now <= expires_at`) | `PROMOTION_BLOCKED_EXPIRED` |

If an Admin attempts to promote an activation with active blockers, the API immediately halts execution with an **HTTP 409 Conflict** error containing the complete list of blocking codes.

---

## 4. Continuous Production Monitoring & Guardrails

The production monitoring service (`GET /api/recovery/intelligence/production`) provides live telemetry across the active production strategy:

### Status Determination State Machine

- **`NO_ACTIVE_STRATEGY`**: Returned during cold-start when no active production strategy is deployed.
- **`HEALTHY`**: Strategy has positive uplift, model governance is healthy, drift level is low, and data quality is clean.
- **`WARNING`**: Uplift is positive but moderate prediction drift ($PSI \ge 0.10$) or model governance warnings are present.
- **`DEGRADED`**: Model governance is degraded ($PSI \ge 0.25$) or data quality issues detected.
- **`ROLLBACK_RECOMMENDED`**: Critical safety alert triggered when treatment recovery rate trails control baseline by $\ge 5.0\%$ ($p_t - p_c \le -0.05$) or model status is critically degraded.

### Key Telemetry Metrics

- **Production Recovery Rate ($p_t$)**: Observed success rate in the treatment cohort.
- **Control Baseline Rate ($p_c$)**: Observed success rate in the control cohort.
- **Differential Uplift**: Absolute and relative percentage uplift.
- **Incremental ERV**: $\text{Incremental ERV (paise)} = \text{ERV}_{\text{treatment}} - \text{ERV}_{\text{control}}$.
- **Financial Yield**: Ratio of total recovered amount to total amount at risk.
- **Mean Time to Recovery (MTTR)**: Average elapsed duration in hours from case creation to resolution.
- **Prediction PSI & Drift Classification**: Population Stability Index comparing production prediction distributions to reference training distribution.

---

## 5. REST API Specifications

### 1. `GET /api/recovery/intelligence/production`
- **RBAC**: `Viewer`, `Operator`, `Admin`
- **Response**: `ProductionMonitoringResponse`
```json
{
  "status": "HEALTHY",
  "strategy_id": "SEND_PAYMENT_LINK",
  "strategy_name": "SEND_PAYMENT_LINK",
  "strategy_version": "strategy-v1.0",
  "model_version": "v1.0",
  "activation_id": "c1f72922-...",
  "recommendation_id": "d2a84910-...",
  "rollout_percentage": 100,
  "sample_size": 150,
  "treatment_sample_size": 75,
  "control_sample_size": 75,
  "recovery_rate": 0.8000,
  "control_recovery_rate": 0.4667,
  "absolute_uplift": 0.3333,
  "relative_uplift_pct": 71.42,
  "incremental_erv_paise": 2500000,
  "financial_yield": 0.8000,
  "mttr_hours": 3.5,
  "model_health": "HEALTHY",
  "prediction_psi": 0.045,
  "drift_status": "LOW",
  "rollback_recommended": false,
  "diagnostics": [
    "Production strategy performance is healthy. Treatment recovery rate exceeds control by +33.3%."
  ],
  "promoted_at": "2026-08-29T10:00:00Z",
  "promoted_by": "admin_usr",
  "last_evaluated": "2026-08-29T11:00:00Z",
  "disclaimer": "Observational continuous production intelligence. PolicyEngine remains authoritative."
}
```

### 2. `GET /api/recovery/intelligence/activations/{id}/promotion-readiness`
- **RBAC**: `Viewer`, `Operator`, `Admin`
- **Response**: `PromotionReadinessResponse`

### 3. `POST /api/recovery/intelligence/activations/{id}/promote`
- **RBAC**: `Admin` only (HTTP 403 for Operators/Viewers)
- **Request Body**: `{"reason": "Empirical canary verified with statistically significant uplift"}`
- **Success (200)**: `StrategyActivationResponse` with `rollout_percentage=100` and `status="PRODUCTION"`
- **Blocked (409 Conflict)**: `{"detail": "Promotion blocked by 2 safety rules: ['PROMOTION_BLOCKED_INSUFFICIENT_SAMPLE', 'PROMOTION_BLOCKED_NO_UPLIFT']"}`

---

## 5. Next Steps: Phase 9H & Phase 9I Intelligence Lifecycle

Phase 9G production promotion telemetry feeds directly into:
- **Phase 9H (Causal Experimentation & Statistical Decision Intelligence)**:
  - Deterministic SHA-256 multi-strategy cohort partitioning
  - Wilson / Newcombe 95% confidence intervals and Two-Proportion Pooled Z-Tests
  - Multidimensional covariate balance diagnostics across risk tiers, failure reasons, amounts, and attempts
  - Causal evidence level classification (`LEVEL_0` to `LEVEL_3`)
  - See [EXPERIMENTATION.md](file:///d:/MEDIFLOW/RecoverIQ/docs/analytics/EXPERIMENTATION.md) for full details.
- **Phase 9I (Governed Model Training, Champion–Challenger Evaluation & Model Lifecycle)**:
  - Historical resolved case extraction with strict pre-decision feature bounds
  - Offline candidate model training and deterministic SHA-256 artifact hashing
  - 10 Governed Model Quality Gates and Champion vs Challenger scorecards
  - Human review operations (`REVIEW_REQUIRED` $\to$ `PROMOTION_READY`) with zero unauthorized automatic activation
  - See [MODEL_LIFECYCLE.md](file:///d:/MEDIFLOW/RecoverIQ/docs/analytics/MODEL_LIFECYCLE.md) for full details.

- **Fintech Performance Engineering, Capacity Planning & High-Load Resilience (Phase 10F)**:
  - 10-factor deterministic performance health score and safe headroom engine (71.0% safe headroom)
  - 11-service performance & saturation matrix and 5-scenario traffic multiplier projections (1x to 20x)
  - 18 deterministic performance readiness safety gates and zero-mutation synthetic load testing
  - See [PERFORMANCE_ENGINEERING.md](file:///d:/MEDIFLOW/RecoverIQ/docs/performance/PERFORMANCE_ENGINEERING.md) and [CAPACITY_PLANNING.md](file:///d:/MEDIFLOW/RecoverIQ/docs/performance/CAPACITY_PLANNING.md) for full details.



