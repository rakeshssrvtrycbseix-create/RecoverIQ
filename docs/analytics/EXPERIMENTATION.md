# Causal Experimentation, Statistical Significance & Decision Intelligence (Phase 9H)

## 1. Overview & Objective

Phase 9H establishes a **statistically rigorous causal experimentation layer** for RecoverIQ. Building upon the Phase 9A–9G recovery intelligence architecture, Phase 9H evaluates whether observed strategy improvements are likely attributable to the strategy itself rather than random variation, seasonal fluctuation, or population imbalance.

```
Incoming / Historical Recovery Cases
                │
                ▼
Deterministic Partitioning Engine: SHA-256 (experiment_id + case_id) % 10000
        ├── 0 .. (100 - p)*100 - 1 ──────▶ Control Cohort (p_c)
        └── (100 - p)*100 .. 9999 ──────▶ Treatment Cohort (p_t)
                                                  │
                                                  ▼
                         Statistical Hypothesis Testing & Causal Inference
                         ├── Two-Proportion Pooled Z-Test & P-Value (α = 0.05)
                         ├── Wilson Score Intervals & Newcombe Difference 95% CI
                         ├── Covariate Balance Diagnostics (Risk, Failure, Amount, Attempts)
                         ├── Overlap Diagnostics & Telemetry Quality Checks
                         └── Automated Stopping Rules (Underperformance <= -5.0%, Degraded Model)
                                                  │
                                                  ▼
                                Causal Evidence Classification
                         ├── LEVEL_0: Insufficient Sample (N < 100 or Cohort < 50)
                         ├── LEVEL_1: Observational Evidence (Insignificant or Confounded)
                         ├── LEVEL_2: Directional Causal Evidence (Minor Imbalance)
                         └── LEVEL_3: Empirical Controlled Causal Evidence (Balanced & Significant)
                                                  │
                                                  ▼
                               Deterministic Governance Decision
                         ├── CONTINUE: Accumulate more observations
                         ├── INSUFFICIENT_DATA: Sample size threshold not reached
                         ├── STOP_RECOMMENDED: Negative uplift / CI_high < 0 / Model degraded
                         └── PROMOTE_TO_REVIEW: ATE >= +2%, CI_low > 0, Significant, LEVEL >= 2
```

---

## 2. Fundamental Architectural Invariants

1. **PolicyEngine Remains Authoritative**: Experiments are strictly observational from a financial perspective. No experiment operation ever bypasses the authoritative `PolicyEngine`.
2. **Zero Financial Mutation on Evaluation**: Creating, starting, pausing, completing, or analyzing an experiment mutates **only** the experiment audit state. It creates **zero** `RecoveryAction` records, modifies zero payment statuses, and calls zero gateway providers.
3. **Zero Database Migrations**: All experiment lifecycle events (`EXPERIMENT_CREATED`, `EXPERIMENT_STARTED`, `EXPERIMENT_PAUSED`, `EXPERIMENT_STOPPED`, `EXPERIMENT_COMPLETED`, etc.) are immutably persisted using the existing `AuditLog` entity (`entity_type="experiment"`). All 12 core tables remain untouched.
4. **Deterministic SHA-256 Assignment Engine**:
   - `seed = f"{experiment_id}:{case_id}"`
   - `bucket = int(hashlib.sha256(seed.encode("utf-8")).hexdigest(), 16) % 10000`
   - `control_threshold = (100 - allocation_percentage) * 100`
   - `0 <= bucket < control_threshold` $\implies$ `CONTROL`, otherwise `TREATMENT`.
   - Exposes `assignment_method = "SHA256_DETERMINISTIC"`.
5. **Integer Paise Precision**: All monetary values (`amount_at_risk_paise`, `amount_recovered_paise`, `expected_recovery_value_paise`, `incremental_erv_paise`) are represented as integer paise.
6. **Zero-PII & Secrets Enforced**: API responses contain zero customer names, email addresses, phone numbers, raw card numbers, webhook secrets, or gateway tokens.
7. **Strict RBAC & Verified Identity**:
   - `Viewer`: Read-only access to `GET /api/recovery/intelligence/experiments`, `GET /api/recovery/intelligence/experiments/{id}`, and `GET /api/recovery/intelligence/experiments/{id}/analysis`.
   - `Operator` & `Admin`: Can create, start, pause, and complete experiments. Actor identity is extracted strictly from verified JWT claims (`current_user.id`, `current_user.role`). Client request payloads cannot spoof the actor.

---

## 3. Statistical Testing & Confidence Intervals

### 3.1 Two-Proportion Pooled Z-Test
To test the null hypothesis $H_0: p_t = p_c$ against the two-sided alternative $H_1: p_t \neq p_c$:

$$\bar{p} = \frac{x_t + x_c}{n_t + n_c}$$

$$SE = \sqrt{\bar{p}(1 - \bar{p}) \left(\frac{1}{n_t} + \frac{1}{n_c}\right)}$$

$$z = \frac{p_t - p_c}{SE}$$

$$p\text{-value} = \text{erfc}\left(\frac{|z|}{\sqrt{2}}\right)$$

Where $\alpha = 0.05$. An experiment is declared **statistically significant** if $p < 0.05$.

### 3.2 Wilson Score & Newcombe Difference 95% Confidence Interval
For single proportions $p_1 = x_1/n_1$ and $p_2 = x_2/n_2$, exact Wilson score bounds $(l_1, u_1)$ and $(l_2, u_2)$ are computed using $z_{\alpha/2} = 1.95996$.

The hybrid Newcombe two-proportion difference confidence interval for $p_1 - p_2$ is:

$$\text{Lower} = (p_1 - p_2) - \sqrt{(p_1 - l_1)^2 + (u_2 - p_2)^2}$$

$$\text{Upper} = (p_1 - p_2) + \sqrt{(u_1 - p_1)^2 + (p_2 - l_2)^2}$$

---

## 4. Randomization Balance Diagnostics

The experimentation layer evaluates covariate distribution balance across 4 critical feature dimensions:

1. `risk_tier` (`LOW`, `STANDARD`, `HIGH`, `CRITICAL`)
2. `failure_reason` (`INSUFFICIENT_FUNDS`, `CARD_EXPIRED`, `NETWORK_ERROR`, `AUTHENTICATION_FAILED`, `OTHER`)
3. `amount_band` (`<1k`, `1k-5k`, `5k-20k`, `>20k` INR)
4. `attempt_number` (`attempt_1`, `attempt_2`, `attempt_3`)

For each feature, the maximum absolute distribution difference between treatment and control is calculated:

$$\Delta_{\max} = \max_{k} |D_{\text{treatment}}(k) - D_{\text{control}}(k)|$$

- **`BALANCED`**: $\Delta_{\max} \le 0.10$ ($\le 10\%$) across all features.
- **`MINOR_IMBALANCE`**: $0.10 < \Delta_{\max} \le 0.20$ on one or more features.
- **`MAJOR_IMBALANCE`**: $\Delta_{\max} > 0.20$ ($> 20\%$) on any feature, flagging `is_confounded = True`.

---

## 5. Automated Stopping Guardrails

An experiment triggers an automated `STOP_RECOMMENDED` alert if any of the following deterministic criteria occur:

1. **Severe Treatment Underperformance**: Treatment recovery rate trails control by $\ge 5.0\%$ ($p_t - p_c \le -0.05$).
2. **Strictly Negative Confidence Bound**: $95\%$ Confidence interval upper bound is negative ($CI_{\text{high}} < 0$) with statistical significance ($p < 0.05$).
3. **Model Governance Degraded**: Underlying ML model health transitions to `DEGRADED`.
4. **Data Quality Degraded**: Missing resolution outcomes $> 10\%$ or missing predictions $> 20\%$.
5. **Population Interference**: Overlapping population with another active `RUNNING` experiment.

---

## 6. Causal Evidence Hierarchy & Decision Engine

### Evidence Levels:
- **`LEVEL_0` (Insufficient Sample)**: Total sample $N < 100$ or either cohort sample $< 50$.
- **`LEVEL_1` (Observational Evidence)**: Sufficient sample, but results are not statistically significant ($p \ge 0.05$) or cohort has major confounding imbalance (`is_confounded = True`).
- **`LEVEL_2` (Directional Causal Evidence)**: Statistically significant with minor balance bounds ($0.10 < \Delta_{\max} \le 0.20$).
- **`LEVEL_3` (Empirical Controlled Causal Evidence)**: Statistically significant in a fully balanced randomized cohort ($\Delta_{\max} \le 0.10$).

### Deterministic Decision Outcomes:
- **`INSUFFICIENT_DATA`**: Returned when evidence level is `LEVEL_0`.
- **`STOP_RECOMMENDED`**: Triggered when automated stopping guardrails fail.
- **`PROMOTE_TO_REVIEW`**: Awarded when $ATE \ge +2.0\%$, $CI_{\text{low}} > 0$, statistically significant ($p < 0.05$), and evidence level is `LEVEL_2` or `LEVEL_3`.
- **`CONTINUE`**: Experiment continues normal observation collection.

---

## 7. REST API Reference

| Method | Endpoint | Role | Description |
|---|---|---|---|
| `POST` | `/api/recovery/intelligence/experiments` | Operator, Admin | Create experiment in `DRAFT` status |
| `GET` | `/api/recovery/intelligence/experiments` | Viewer, Operator, Admin | List paginated experiments with status filter |
| `GET` | `/api/recovery/intelligence/experiments/{id}` | Viewer, Operator, Admin | Get experiment metadata |
| `GET` | `/api/recovery/intelligence/experiments/{id}/analysis` | Viewer, Operator, Admin | Comprehensive causal effect & balance analysis |
| `POST` | `/api/recovery/intelligence/experiments/{id}/start` | Operator, Admin | Transition to `RUNNING` status |
| `POST` | `/api/recovery/intelligence/experiments/{id}/pause` | Operator, Admin | Transition to `PAUSED` status |
| `POST` | `/api/recovery/intelligence/experiments/{id}/complete` | Operator, Admin | Transition to `COMPLETED` status |

---

## 8. Verification & Test Suite

The experimentation suite is verified by 28 unit and integration tests in `backend/tests/test_experimentation.py`:

- **RBAC & Security**: Operator/Admin creation vs Viewer rejection (403), JWT actor verification.
- **Assignment**: SHA-256 deterministic reproducibility and cross-experiment independence.
- **Statistical Mathematics**: Wilson score intervals, Newcombe difference bounds, two-proportion pooled z-test and p-values.
- **Balance & Overlap**: Covariate distribution balance checks, multi-experiment population collision detection.
- **Stopping Rules & Evidence**: Underperformance triggers, model degradation detection, evidence hierarchy (`LEVEL_0` to `LEVEL_3`).
- **Financial Isolation**: Verified 0 `RecoveryAction` records created, 0 `Payment` records mutated, 0 gateway API calls executed.
