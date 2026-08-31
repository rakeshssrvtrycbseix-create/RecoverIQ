# Governed Model Training, Champion–Challenger Evaluation & Model Lifecycle (Phase 9I)

## 1. Overview & Architectural Workflow

Phase 9I establishes a **governed, offline machine-learning lifecycle** for RecoverIQ. It bridges historical recovery outcomes with candidate model training, deterministic quality gates, and champion–challenger validation while guaranteeing zero unauthorized automatic model deployment.

```
+-----------------------------------------------------------------------------------+
|                        OFFLINE MODEL LIFECYCLE WORKFLOW                            |
+-----------------------------------------------------------------------------------+
 Historical Resolved Cases (RECOVERED vs CLOSED/EXHAUSTED)
                      │
                      ▼
 ┌─────────────────────────────────────────────────────────┐
 │ Training Dataset Builder (Deterministic v1 Features)    │
 │ ├── Strict Pre-Decision Feature Extraction (Zero Leak)  │
 │ ├── Zero PII Guarantee (Masked Identifiers Only)        │
 │ └── Deterministic 70/30 Temporal/Hash Split & SHA-256   │
 └────────────────────────────┬────────────────────────────┘
                              │
                              ▼
 ┌─────────────────────────────────────────────────────────┐
 │ Candidate Model Training (Calibrated Logistic Reg)      │
 │ ├── Deterministic Training on Training Partition        │
 │ └── Immutable Model Artifact Serialization & SHA-256    │
 └────────────────────────────┬────────────────────────────┘
                              │
                              ▼
 ┌─────────────────────────────────────────────────────────┐
 │ Champion vs Challenger Evaluation (Validation Partition)│
 │ ├── Active Champion (v1.0) Baseline Metrics             │
 │ ├── Candidate Challenger Evaluation                     │
 │ └── Directional Delta Calculations (Accuracy, F1, ECE)  │
 └────────────────────────────┬────────────────────────────┘
                              │
                              ▼
 ┌─────────────────────────────────────────────────────────┐
 │ 10 Governed Model Quality Gates                         │
 │ ├── G01: MIN_VALIDATION_SAMPLE (N >= 50)                │
 │ ├── G02: ACCURACY_NON_REGRESSION (Delta >= -0.02)       │
 │ ├── G03: F1_NON_REGRESSION (Delta >= -0.02)             │
 │ ├── G04: BRIER_NON_REGRESSION (Delta <= +0.02)          │
 │ ├── G05: CALIBRATION (ECE <= 0.15, Delta <= +0.03)      │
 │ ├── G06: DATA_QUALITY (Zero NaN, Prob in [0,1])         │
 │ ├── G07: FEATURE_COMPATIBILITY (Schema == 'v1')         │
 │ ├── G08: DRIFT (PSI <= 0.25)                            │
 │ ├── G09: REPRODUCIBILITY (SHA-256 Verified)             │
 │ └── G10: CAUSAL_EVIDENCE (Level >= 2 or Baseline Equiv) │
 └────────────────────────────┬────────────────────────────┘
                              │
                              ▼
 ┌─────────────────────────────────────────────────────────┐
 │ Model Scorecard & Recommendation Engine                 │
 │ ├── Status: REVIEW_REQUIRED                             │
 │ └── Recommendation: PROMOTE_CHALLENGER_REVIEW           │
 └────────────────────────────┬────────────────────────────┘
                              │
                              ▼
 ┌─────────────────────────────────────────────────────────┐
 │ Human Review (Operator / Admin via JWT RBAC)            │
 │ ├── APPROVE: Transitions to PROMOTION_READY (Standby)   │
 │ └── REJECT: Transitions to REJECTED                     │
 └─────────────────────────────────────────────────────────┘
```

---

## 2. Fundamental Architectural Invariants

1. **Offline Computation Only**: Training, feature extraction, and evaluation are computed strictly offline. Phase 9I endpoints create **zero** `RecoveryAction` records, mutate zero payment states, schedule zero retries, and dispatch zero webhook/provider calls.
2. **Approval != Activation**: Human approval transitions a model from `REVIEW_REQUIRED` $\to$ `APPROVED` $\to$ `PROMOTION_READY`. The active production champion remains `v1.0`. The candidate model is **not** activated or used for live recovery scoring until a future explicit deployment phase.
3. **Zero Database Migrations (100% Target Met)**: All model versions, artifact hashes, quality gate evaluations, and state transitions are event-sourced on the existing `AuditLog` table with `entity_type="ml_model"` and deterministic UUIDs (`uuid.uuid5`).
4. **Strict Pre-Decision Feature Boundary (Zero Leakage)**:
   - Features represent only information known at the moment of initial case evaluation.
   - Prohibited fields: `recovered_amount`, `resolved_at`, final case status, `ActionResult` after execution, retry success timestamps, or post-recovery communications.
5. **Zero-PII Compliance**: No customer names, unmasked emails, unmasked phone numbers, or card PANs are used in feature vectors or returned in API responses.
6. **Deterministic Reproducibility**: Dataset content and serialized model artifacts are cryptographically hashed using SHA-256 to ensure byte-for-byte reproducibility.
7. **Strict JWT RBAC**:
   - `Viewer`: Read-only access to model registry, details, and scorecards.
   - `Operator` / `Admin`: Can trigger offline training, approve models into `PROMOTION_READY`, or reject candidates. Actor identity is extracted exclusively from verified JWT tokens.

---

## 3. Training Dataset Builder

The `TrainingDatasetBuilder` extracts historical resolved recovery cases from the PostgreSQL database:

### Outcome Labeling
- **Positive Label ($y = 1$)**: Cases where `RecoveryCase.status == RECOVERED` and `Payment.status == CAPTURED`.
- **Negative Label ($y = 0$)**: Cases where `RecoveryCase.status in [CLOSED, EXHAUSTED]` and `Payment.status == FAILED`.
- **Unresolved Cases Excluded**: Cases in `OPEN`, `IN_RECOVERY`, `ACTION_REQUIRED`, `PENDING_CUSTOMER`, or `DISPUTED` are strictly excluded to eliminate survival bias and outcome contamination.

### Feature Schema `v1` Vector (10 Dimensions)
1. `amount_log`: $\ln(\text{amount\_paise} / 100 + 1)$
2. `attempt_count_norm`: $\min(\text{attempt\_count} / 10.0, 1.0)$
3. `is_card_expired`: Boolean indicator ($0.0$ or $1.0$)
4. `is_insufficient_funds`: Boolean indicator ($0.0$ or $1.0$)
5. `is_auth_failed`: Boolean indicator ($0.0$ or $1.0$)
6. `risk_score_norm`: Customer risk tier normalized ($0.2$ to $0.9$)
7. `customer_success_rate`: Ratio of successful to total historical payments $[0.0, 1.0]$
8. `case_age_hours_norm`: $\min(\text{case\_age\_hours} / 168.0, 1.0)$
9. `has_subscription`: Boolean indicator ($0.0$ or $1.0$)
10. `hour_of_day_norm`: $\text{hour} / 24.0$

### Temporal / Deterministic Partitioning
Cases are split chronologically or via deterministic hash into **70% Training** and **30% Validation** partitions. Both dataset partitions receive individual SHA-256 checksums.

---

## 4. 10 Governed Model Quality Gates

Before any candidate model can be recommended for human review, it is evaluated across 10 deterministic gates:

| Gate Code | Metric / Property | Threshold | Direction / Condition |
|:---|:---|:---|:---|
| `MIN_VALIDATION_SAMPLE` | Sample Size ($N_{\text{val}}$) | $\ge 50$ | Minimum statistical power |
| `ACCURACY_NON_REGRESSION` | $\Delta \text{ Accuracy}$ | $\ge -0.02$ | Maximum allowable accuracy drop is 2% |
| `F1_NON_REGRESSION` | $\Delta \text{ F1 Score}$ | $\ge -0.02$ | Maximum allowable F1 drop is 2% |
| `BRIER_NON_REGRESSION` | $\Delta \text{ Brier Score}$ | $\le +0.02$ | Lower is better; candidate MSE must not worsen |
| `CALIBRATION` | ECE & $\Delta \text{ ECE}$ | $\text{ECE} \le 0.15$, $\Delta \le +0.03$ | Expected calibration error must remain tight |
| `DATA_QUALITY` | Probability Integrity | Zero NaNs, $p_i \in [0, 1]$ | Valid mathematical output bounds |
| `FEATURE_COMPATIBILITY`| Schema Version | Exactly `"v1"` | 10-feature dimensional alignment |
| `DRIFT` | Covariate Shift | $\text{PSI} \le 0.25$ | No severe population distribution shift |
| `REPRODUCIBILITY` | Artifact Checksum | SHA-256 Match | Deterministic serialization verified |
| `CAUSAL_EVIDENCE` | Experimental Rigor | Level $\ge 2$ or baseline equiv | Statistically sound evidence basis |

---

## 5. Model Lifecycle State Machine

```
                   ┌──────────┐
                   │  DRAFT   │
                   └────┬─────┘
                        │ Start Training
                        ▼
                   ┌──────────┐
                   │ TRAINING │
                   └────┬─────┘
                        │ Complete Training
                        ▼
                  ┌────────────┐
                  │ VALIDATING │
                  └─────┬──────┘
                        │ Quality Gates & Scorecard
                        ▼
               ┌─────────────────┐
               │ REVIEW_REQUIRED │
               └────┬───────┬────┘
      Approve Model │       │ Reject Model
                    ▼       ▼
          ┌──────────┐    ┌──────────┐
          │ APPROVED │    │ REJECTED │
          └─────┬────┘    └──────────┘
                │ Ready for Release
                ▼
       ┌─────────────────┐
       │ PROMOTION_READY │
       └────────┬────────┘
                │ Future Controlled Rollout
                ▼
           ┌──────────┐
           │  ACTIVE  │ (Champion)
           └────┬─────┘
                │ Superceded
                ▼
           ┌──────────┐
           │ RETIRED  │
           └──────────┘
```

---

## 6. REST API Reference

All endpoints require standard `Bearer <JWT_TOKEN>` authentication.

### `GET /api/recovery/intelligence/models`
- **Role**: `Viewer`, `Operator`, `Admin`
- **Query Params**: `status` (optional filter, e.g. `ACTIVE`, `REVIEW_REQUIRED`, `PROMOTION_READY`)
- **Returns**: `PaginatedModelsResponse` listing registered models and active champion.

### `GET /api/recovery/intelligence/models/{version}`
- **Role**: `Viewer`, `Operator`, `Admin`
- **Returns**: `ModelSummaryResponse` with lifecycle status, sample sizes, and artifact hashes.

### `GET /api/recovery/intelligence/models/{version}/scorecard`
- **Role**: `Viewer`, `Operator`, `Admin`
- **Returns**: `ModelScorecardResponse` with side-by-side champion/challenger comparison, 10 quality gates, and governance recommendation.

### `POST /api/recovery/intelligence/models/train`
- **Role**: `Operator`, `Admin`
- **Body**: `{ "model_name": "recovery_probability", "parent_version": "v1.0", "learning_rate": 0.05, "epochs": 50, "notes": "..." }`
- **Returns**: `ModelScorecardResponse` with evaluated candidate in `REVIEW_REQUIRED` status.

### `POST /api/recovery/intelligence/models/{version}/approve`
- **Role**: `Operator`, `Admin`
- **Body**: `{ "notes": "Approved for promotion readiness" }`
- **Returns**: `ModelSummaryResponse` with updated status `PROMOTION_READY`.

### `POST /api/recovery/intelligence/models/{version}/reject`
- **Role**: `Operator`, `Admin`
- **Body**: `{ "reason": "F1 score regression on validation split" }`
- **Returns**: `ModelSummaryResponse` with updated status `REJECTED`.

---

## 7. Next Stage: Governed Model Deployment (Phase 9J)

Models reaching `PROMOTION_READY` status are eligible for governed multi-stage deployment via **Phase 9J (Governed Model Deployment, Shadow Mode & Champion–Challenger Production Validation)**. See [MODEL_DEPLOYMENT.md](file:///d:/MEDIFLOW/RecoverIQ/docs/analytics/MODEL_DEPLOYMENT.md) for details on:
- Passive shadow mode execution with deterministic SHA-256 case partitioning.
- 14 deterministic deployment readiness safety gates.
- Controlled canary staging ($5\%$, $10\%$, $25\%$, $50\%$, $100\%$).
- Atomic Admin promotion to `ACTIVE` Champion with automated rollback guardrails.

---

## 8. Continuous Retraining Surveillance (Phase 9K)

Phase 9I model training is continuously orchestrated via **Phase 9K (Governed Continuous Learning & Automated Retraining Monitoring)**. See [CONTINUOUS_LEARNING.md](file:///d:/MEDIFLOW/RecoverIQ/docs/analytics/CONTINUOUS_LEARNING.md) for details on:
- Multi-signal retraining triggers ($\Delta N \ge 100$, $\text{PSI} \ge 0.20$, $\Delta \text{Acc} \le -0.05$, $\Delta \text{ECE} \ge 0.05$).
- Point-in-time immutable dataset version registry (`dataset-vX.Y`) with SHA-256 integrity verification.
- Complete provenance tracking in the Model Lineage DAG.
- 14 deterministic Continuous Learning safety gates.

---

## 9. Data Lineage & Model Retention Governance (Phase 10E)

Model training datasets, feature representations, and inference outputs participate in the **Phase 10E Data Lineage & Retention Governance framework**:
- **Lineage Node 4 (Model)**: Maps feature store transformations with immutable SHA-256 schema digests.
- **3-Year Statutory Retention**: Model artifacts and training splits are governed under a 3-year statutory ML lifecycle.
- **HMAC Pseudonymization**: Training samples never contain plain-text customer identifiers.

For full specifications, see [DATA_LINEAGE.md](file:///d:/MEDIFLOW/RecoverIQ/docs/governance/DATA_LINEAGE.md) and [DATA_RETENTION.md](file:///d:/MEDIFLOW/RecoverIQ/docs/governance/DATA_RETENTION.md).


