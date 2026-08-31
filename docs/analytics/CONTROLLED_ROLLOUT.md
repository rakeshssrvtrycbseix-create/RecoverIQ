# Controlled Strategy Activation & Canary Rollout (Phase 9F)

## 1. Overview & Objective

Phase 9F introduces a **controlled, deterministic canary experimentation layer** to RecoverIQ. This layer enables human operators to transition an approved strategy recommendation (from Phase 9E) into a phased empirical rollout (`0%` $\to$ `5%` $\to$ `10%` $\to$ `25%` $\to$ `50%` $\to$ `100%`) to measure live differential recovery uplift before committing to full production activation.

```
AI / Intelligence Analysis (Phases 9A–9D)
        │
        ▼
Governed Recommendation (Phase 9E)
        │
        ▼  [Human Operator Approval]
Strategy Activation (Draft / Approved)
        │
        ▼  [Operator Configures Canary % (5, 10, 25, 50)]
Deterministic Canary Partitioning (SHA-256 Bucketing)
        │
        ├──▶ Control Cohort (0% Traffic Allocation)
        │
        └──▶ Treatment Cohort (Canary Traffic Allocation)
                 │
                 ▼
     RecoveryDecisionEngine
                 │
                 ▼
     Authoritative PolicyEngine (Guardrail Validation)
                 │
                 ▼
     RecoveryActionScheduler & RecoveryWorker
                 │
                 ▼
     ActionDispatcher & Gateway Provider
                 │
                 ▼
     Empirical Experiment Telemetry & Automated Rollback Diagnostics
                 │
                 ▼  [Admin Approval Only]
Full Production Activation (100% Rollout)
```

---

## 2. Fundamental Architectural Invariants & Trust Boundary

1. **Zero Direct Financial Execution**: Activating a strategy or adjusting canary percentage **NEVER** creates `RecoveryAction` records, modifies `Payment.status` or `RecoveryCase.status`, or calls `ActionDispatcher` / `RazorpayActionProvider`.
2. **Authoritative Policy Engine**: The Policy Engine remains 100% authoritative over all actions. No canary configuration can bypass financial limits, cooldowns, or fraud blocks.
3. **Deterministic Traffic Assignment**: Canary cohort membership is computed strictly via deterministic hashing (`hash(case_id + activation_id) % 100`). `random.random()` is prohibited.
4. **Whitelisted Rollout Stages**: Traffic percentages are constrained to `{0, 5, 10, 25, 50, 100}`. Arbitrary percentages (e.g. 1%, 7%, 33%, 75%) are rejected.
5. **Integer Paise Financial Storage**: All monetary figures (`amount_at_risk_paise`, `amount_recovered_paise`, `expected_recovery_value_paise`, `incremental_expected_recovery_value_paise`) are strictly maintained as integer paise.
6. **Immutable Audit Persistence**: All lifecycle transitions (`ACTIVATION_CREATED`, `ACTIVATION_APPROVED`, `CANARY_STARTED`, `ACTIVATION_PAUSED`, `ACTIVATION_ROLLED_BACK`, `ACTIVATION_PROMOTED`, `ACTIVATION_EXPIRED`) are immutably persisted in `AuditLog` with zero DB schema changes.
7. **Strict RBAC & Verified Actor Identity**:
   - `Viewer`: Read-only access to activations and experiment metrics.
   - `Operator`: Create activation, adjust canary percentage (5%, 10%, 25%, 50%), pause, and rollback.
   - `Admin`: Full promotion to active production (100%).

---

## 3. Deterministic Canary Assignment Algorithm

To guarantee test reproducibility, cross-process consistency, and zero runtime randomness:

```python
import hashlib

def is_case_in_canary(case_id: str, activation_id: str, rollout_percentage: int) -> bool:
    if rollout_percentage <= 0:
        return False
    if rollout_percentage >= 100:
        return True

    seed = f"{case_id}:{activation_id}"
    digest = hashlib.sha256(seed.encode("utf-8")).hexdigest()
    bucket = int(digest, 16) % 100
    return bucket < rollout_percentage
```

- **0% Rollout**: Strictly assigns 0 cases to treatment.
- **100% Rollout**: Strictly assigns 100% of cases to treatment.
- **5%, 10%, 25%, 50%**: Uniformly and deterministically partitions cases based on the SHA-256 hash space.

---

## 4. Experiment Metrics & Statistical Evaluation

### Cohort Metrics (Control vs. Treatment)
- **Sample Size ($N$)**: Total resolved cases in the cohort.
- **Recovery Rate ($p$)**: $\frac{\text{Recovered Cases}}{N}$
- **Financial Yield**: $\frac{\text{Amount Recovered (paise)}}{\text{Amount at Risk (paise)}}$
- **Expected Recovery Value (ERV)**: $\text{round}(\text{Amount at Risk (paise)} \times p)$
- **Mean & Median Time to Recovery (MTTR)**: Elapsed duration in hours between `opened_at` and `resolved_at`.

### Comparative Uplift Statistics
- **Absolute Uplift**: $p_{\text{treatment}} - p_{\text{control}}$
- **Relative Uplift (%)**: $\frac{p_{\text{treatment}} - p_{\text{control}}}{p_{\text{control}}} \times 100$ (Safe against zero denominators)
- **Incremental ERV**: $\text{ERV}_{\text{treatment}} - \text{ERV}_{\text{control}}$

### 95% Confidence Interval & Statistical Significance
$$\text{Standard Error } (SE) = \sqrt{\frac{p_t(1 - p_t)}{n_t} + \frac{p_c(1 - p_c)}{n_c}}$$
$$\text{Confidence Interval } = (p_t - p_c) \pm 1.96 \times SE$$

A canary experiment is marked **Statistically Significant ($p < 0.05$)** when the 95% confidence interval strictly excludes zero.

### Sample Reliability Tiers
- $N < 10 \implies \mathbf{INSUFFICIENT\_DATA}$
- $10 \le N < 30 \implies \mathbf{LIMITED}$
- $N \ge 30 \implies \mathbf{SUFFICIENT}$

---

## 5. Rollback Safety Diagnostics Engine

The safety engine automatically evaluates experiment health on every telemetry read:

| Health State | Trigger Conditions | Recommended Action |
| :--- | :--- | :--- |
| $\mathbf{SAFE}$ | Treatment rate $\ge$ Control rate; Model health $\mathbf{HEALTHY}$. | Continue staged rollout. |
| $\mathbf{WARNING}$ | Treatment trailing control by $2.0\% - 4.9\%$, or Model health $\mathbf{WARNING}$. | Monitor telemetry closely. |
| $\mathbf{ROLLBACK\_RECOMMENDED}$ | Treatment underperforming control by $\ge 5.0\%$ ($N \ge 30$), or Model $\mathbf{DEGRADED}$. | Operator rollback recommended. |

---

## 6. Activation Lifecycle State Machine

```
   [Approved Recommendation]
               │
               ▼
           [APPROVED] ──(Start Canary 5%, 10%, 25%, 50%)──▶ [CANARY]
               │                                               │
               │                                               ├──(Pause)──▶ [PAUSED] ──(Resume)──┐
               │                                               │                                  │
               │                                               ├──(Promote 100% - Admin Only)──▶ [ACTIVE]
               │                                               │                                  │
               │                                               ├──(TTL Elapsed / Drift)──▶ [EXPIRED]
               ▼                                               ▼                                  │
          [ROLLED_BACK] ◀───────────────────────────── [ROLLED_BACK] ◀────────────────────────────┘
```

- Invalid transitions (e.g. `ROLLED_BACK` $\to$ `ACTIVE`, `EXPIRED` $\to$ `CANARY`, `APPROVED` $\to$ `ACTIVE` without canary) return HTTP 400 Bad Request.

---

## 7. API Reference

| Method | Path | Required Role | Description |
| :--- | :--- | :--- | :--- |
| `GET` | `/api/recovery/intelligence/activations` | `viewer` | List all strategy activations and active canary rollout. |
| `GET` | `/api/recovery/intelligence/activations/{id}` | `viewer` | Fetch detailed metrics, cohort comparison, and health. |
| `POST` | `/api/recovery/intelligence/activations/create` | `operator` | Create an activation from an approved recommendation. |
| `POST` | `/api/recovery/intelligence/activations/{id}/start-canary` | `operator` | Start or adjust canary rollout percentage (`5, 10, 25, 50`). |
| `POST` | `/api/recovery/intelligence/activations/{id}/pause` | `operator` | Pause rollout (`0%` traffic allocation). |
| `POST` | `/api/recovery/intelligence/activations/{id}/rollback` | `operator` | Terminate and rollback activation. |
| `GET` | `/api/recovery/intelligence/activations/{id}/promotion-readiness` | `viewer` | Evaluate 8 deterministic production promotion safety gates (Phase 9G). |
| `POST` | `/api/recovery/intelligence/activations/{id}/promote` | `admin` | Promote canary to 100% full production rollout upon passing all 8 gates (Phase 9G). |
| `GET` | `/api/recovery/intelligence/production` | `viewer` | Live continuous production strategy monitoring & guardrails (Phase 9G). |

