# RecoverIQ — Phase 9L: Intelligence Control Plane & Unified Autonomous Governance

## 1. Executive Overview & Absolute Architectural Invariant

**RecoverIQ Phase 9L** provides the **Intelligence Control Plane**, an autonomous, unified surveillance and governance layer that observes and coordinates the complete intelligence lifecycle (Phases 9A through 9K).

### Absolute Architectural Invariant
The authoritative financial execution pipeline remains strictly immutable:

```
Payment
  │
  ▼
RecoveryCase
  │
  ▼
ML Prediction (Phase 9A / 9I / 9J)
  │
  ▼
AgentDecision (Phase 9B / 9C)
  │
  ▼
PolicyDecision (Deterministic PolicyEngine Safety Gate)
  │
  ▼
RecoveryAction
  │
  ▼
RecoveryWorker
  │
  ▼
ActionDispatcher
  │
  ▼
RazorpayActionProvider
  │
  ▼
ActionResult
  │
  ▼
Outcome / Financial Reconciliation
```

### Critical Governance Mandates:
1. **The Intelligence Control Plane MUST NOT replace or bypass `PolicyEngine`.**
2. **The Intelligence Control Plane MUST NOT directly**:
   - Create `RecoveryAction`
   - Modify `Payment` financial state
   - Modify `RecoveryCase` financial state
   - Execute payment retries
   - Send payment links
   - Call Razorpay APIs
   - Call `ActionDispatcher`
   - Alter financial authorization thresholds
3. **The Intelligence Control Plane is strictly an observational, correlation, and human governance layer.**
4. **Target: 0 Database Migrations.** All control plane telemetry, incident states, and audit tracking leverage the immutable `AuditLog` infrastructure.

---

## 2. Deterministic Global System State Priority

The Control Plane synthesizes telemetry across all 8 intelligence subsystems to evaluate the **Global System State** using an absolute deterministic priority hierarchy:

```
EMERGENCY_LOCKDOWN
       │
       ▼
ROLLBACK_REQUIRED
       │
       ▼
   DEGRADED
       │
       ▼
HUMAN_REVIEW_REQUIRED
       │
       ▼
LEARNING_REQUIRED
       │
       ▼
   WARNING
       │
       ▼
  MONITORING
       │
       ▼
   HEALTHY
```

### Deterministic State Transition Matrix:

| State | Trigger Conditions | Recommended Autonomous / Operator Action |
| :--- | :--- | :--- |
| **`EMERGENCY_LOCKDOWN`** | Data Quality `CRITICAL` (missing critical features > 10%) or Model Performance `CRITICAL` (Accuracy < 0.60 or F1 < 0.55). | Model inference automatically disabled; fallback to deterministic rule engine; immediate alert dispatch. |
| **`ROLLBACK_REQUIRED`** | Active model or strategy deployment breaches safety guardrails (negative recovery uplift or severe calibration drift). | Emergency rollback armed in Governance Center to restore prior Champion model/strategy. |
| **`DEGRADED`** | Population drift `CRITICAL` (PSI ≥ 0.25) or Calibration `CRITICAL` (ECE ≥ 0.20) without hard stop. | Operator review required; retrain candidate offline; restrict canary rollout percentage. |
| **`HUMAN_REVIEW_REQUIRED`** | Pending strategy recommendations or model scorecards awaiting operator/admin signoff. | Operator signoff in Human Governance Center. |
| **`LEARNING_REQUIRED`** | Continuous learning surveillance signals retraining eligibility (`ELIGIBLE`, `DRIFT_TRIGGERED`). | Operator triggers offline training run from Continuous Learning tab. |
| **`WARNING`** | Any subsystem evaluates to `WARNING` (e.g. moderate drift 0.10 ≤ PSI < 0.25 or ECE ≥ 0.10). | Increased surveillance cadence; monitor canary cohort metrics. |
| **`MONITORING`** | Sample size < 50 cases (insufficient statistical power). | Accumulate resolved recovery cases. |
| **`HEALTHY`** | All 8 subsystems operating within nominal safety thresholds. | Standard autonomous operation. |

---

## 3. Intelligence Health Score Formula

The Control Plane calculates a deterministic, bounded 0.0–100.0 **Unified Intelligence Health Score** via a weighted sum across 8 operational dimensions:

$$\text{Health Score} = \sum_{i=1}^{8} w_i \times S_i$$

### Dimension Weights and Metrics:

| Dimension | Subsystem | Weight ($w_i$) | Core Telemetry Metrics Monitored |
| :--- | :--- | :---: | :--- |
| **Model Performance** | Phase 9A / 9H | **15%** | Accuracy ( $\ge 0.70$ ), F1-Score ( $\ge 0.65$ ), AUC-ROC |
| **Calibration Reliability** | Phase 9A / 9H | **10%** | Expected Calibration Error ( $\text{ECE} \le 0.10$ ) |
| **Population Drift** | Phase 9B / 9H | **15%** | Population Stability Index ( $\text{PSI} < 0.10$ ), Feature-level KS test |
| **Data Quality Integrity** | Phase 9B / 9H | **10%** | Missing feature rate ( $< 1.0\%$ ), schema adherence |
| **Strategy Optimization** | Phase 9C / 9D | **15%** | Expected Recovery Value (ERV), Champion recovery rate |
| **Causal Experimentation** | Phase 9G | **10%** | Active randomized trials, sample size balance, uplift significance |
| **Model Deployment Safety** | Phase 9J | **15%** | Active canary traffic, shadow convergence, rollback alerts count |
| **Continuous Learning Readiness** | Phase 9K | **10%** | Dataset version, resolved cases delta, retraining eligibility status |
| **Total** | | **100%** | |

---

## 4. Multi-Signal Autonomous Incident Correlation Engine

The Control Plane correlates anomalies across multiple lifecycle phases into unified, actionable incidents with deterministic IDs.

### Correlation Rules:

1. **`INC-CRIT-DATA-LEAK` (Critical Data Ingestion Corruption)**
   - *Signals*: Data Quality `CRITICAL` + Model Degradation.
   - *Source Phases*: Phase 9B (Drift & Data Quality) + Phase 9A (Model Inference).
   - *Impact*: Corrupted feature vectors reaching inference layer.
   - *Recommended Action*: Trigger emergency fallback; verify upstream payment event parser.

2. **`INC-ROLLBACK-UPLIFT` (Deployment Guardrail Breach)**
   - *Signals*: Deployment status `ROLLBACK_REQUIRED` + Causal Experiment negative uplift.
   - *Source Phases*: Phase 9J (Deployment) + Phase 9G (Experimentation).
   - *Impact*: Challenger model performing worse than Champion baseline in live canary.
   - *Recommended Action*: Execute emergency rollback via Governance Center to restore Champion version.

3. **`INC-DRIFT-RETRAIN` (Population Distribution Shift)**
   - *Signals*: Population Drift `CRITICAL` (PSI $\ge 0.25$) + Continuous Learning `ELIGIBLE`.
   - *Source Phases*: Phase 9B (Drift) + Phase 9K (Continuous Learning).
   - *Impact*: Live customer distribution diverged from offline training dataset.
   - *Recommended Action*: Ingest latest resolved cases dataset and trigger candidate retraining run.

4. **`INC-CALIB-DEGRADED` (Model Confidence Miscalibration)**
   - *Signals*: Calibration Error `CRITICAL` (ECE $\ge 0.20$).
   - *Source Phases*: Phase 9A (Evaluation) + Phase 9H (Production Monitoring).
   - *Impact*: Overconfident or underconfident probabilities affecting strategy selection.
   - *Recommended Action*: Recalibrate model via Platt scaling / Isotonic regression on recent validation split.

---

## 5. Unified Provenance & Lineage DAG (10 Stages)

The Control Plane constructs an end-to-end directed acyclic graph (DAG) tracing provenance from offline data extraction to production recovery outcomes:

```
[1. DATASET] (Immutable hash, sample count, feature schema v1.0)
     │
     ▼
[2. TRAINING_RUN] (Learning rate, epochs, gradient convergence, actor ID)
     │
     ▼
[3. MODEL_ARTIFACT] (Sha256 hash, hyperparameter snapshot, artifact URI)
     │
     ▼
[4. VALIDATION] (Offline 10-gate quality check: AUC, ECE, Brier, Causal level)
     │
     ▼
[5. GOVERNANCE] (Model lifecycle status: APPROVED, signed by operator)
     │
     ▼
[6. EXPERIMENT] (A/B randomized trial, synthetic control, cohort split)
     │
     ▼
[7. STRATEGY_RECOMMENDATION] (Governed recommendation, ERV integer paise)
     │
     ▼
[8. CONTROLLED_ROLLOUT] (Deterministic canary hash modulo 100 allocation)
     │
     ▼
[9. PRODUCTION_DEPLOYMENT] (Active Champion / Challenger deployment)
     │
     ▼
[10. PRODUCTION_OUTCOME] (Reconciled payment recovery, actual uplift, audit log)
```

---

## 6. Zero-PII Case Decision Trace Architecture

Every recovery case in RecoverIQ can be forensically audited through the **Case Decision Trace** endpoint:

### 6 Chronological Stages Reconstructed per Case:
1. **`PAYMENT_FAILURE_INGESTION`**: Failure timestamp, payment attempt number, error code, sanitized error reason.
2. **`ML_PROBABILITY_INFERENCE`**: Active model version, calculated recovery probability (e.g. 0.7850), predicted channel.
3. **`AGENT_REASONING_AND_STRATEGY`**: Orchestrator agent name, proposed action, confidence score, reasoning summary.
4. **`POLICY_ENGINE_SAFETY_GATE`**: Evaluation result (`ALLOWED`), triggered rule name, deterministic validation status.
5. **`RECOVERY_ACTION_DISPATCH`**: Action type, idempotency key, dispatcher status, provider execution result.
6. **`RECOVERY_CASE_OUTCOME`**: Final recovery state (`RECOVERED` / `UNRECOVERED`), recovered amount in paise, resolution timestamp.

### Zero-PII & Zero-Secrets Guarantee:
- **Never includes**: Customer name, unmasked email, unmasked phone, card PAN, CVV, bank account numbers, Razorpay API keys, JWT secrets, webhook signing keys.
- **Includes only**: Mathematical inference feature vectors (counts, ratios, attempt numbers, amounts in integer paise, sanitized error codes).

---

## 7. Human Governance Center

The Governance Center centralizes all pending human reviews across intelligence domains into a single unified queue:

1. **Pending Strategy Recommendations**: Reviews required for recommendations generated with medium confidence or limited sample sizes before canary activation.
2. **Pending Model Scorecards**: Candidate models evaluated offline awaiting human approval/rejection.
3. **Pending Deployment Canary Reviews**: Active canary rollouts undergoing statistical recovery rate surveillance.
4. **Rollback Guardrails & Tripwires**: Emergency tripwires armed against negative recovery uplift or critical drift.
5. **Continuous Learning Alerts**: Notifications of accumulated datasets and retraining readiness.
6. **Required Operator Actions Checklist**: Prioritized list of required human decisions.

---

## 8. API Specification & Role-Based Access Control (RBAC)

All endpoints enforce verified JWT authentication via `app.core.security`. Client-supplied operator identity is strictly ignored in favor of verified JWT claims.

| Method | Endpoint | Allowed Roles | Description |
| :--- | :--- | :--- | :--- |
| `GET` | `/api/recovery/intelligence/control-plane` | `VIEWER`, `OPERATOR`, `ADMIN` | High-level Control Plane summary, global state, health scores, top diagnostics. |
| `GET` | `/api/recovery/intelligence/control-plane/health` | `VIEWER`, `OPERATOR`, `ADMIN` | Detailed unified health breakdown across all 8 subsystems with diagnostic findings. |
| `GET` | `/api/recovery/intelligence/control-plane/incidents` | `VIEWER`, `OPERATOR`, `ADMIN` | Active correlated multi-signal incidents stream. |
| `GET` | `/api/recovery/intelligence/control-plane/lineage` | `VIEWER`, `OPERATOR`, `ADMIN` | End-to-end 10-stage model & strategy provenance DAG. |
| `GET` | `/api/recovery/intelligence/governance-center` | `VIEWER`, `OPERATOR`, `ADMIN` | Centralized human governance action items, pending reviews, and rollback alerts. |
| `GET` | `/api/recovery/intelligence/decision-trace/{case_id}` | `VIEWER`, `OPERATOR`, `ADMIN` | Zero-PII 6-stage chronological forensic trace for a specific recovery case. |

---

## 9. Financial Isolation Verification & Automated Test Suite

Automated test suite located in `backend/tests/test_intelligence_control_plane.py` guarantees:

1. **Financial Isolation Guarantee**: Calling control plane endpoints results in:
   - $\Delta \text{ RecoveryAction Count} = 0$
   - $\Delta \text{ Payment Mutation Count} = 0$
   - $\Delta \text{ RecoveryCase Financial State} = 0$
   - $\Delta \text{ ActionDispatcher Calls} = 0$
   - $\Delta \text{ Razorpay Provider Calls} = 0$
2. **Zero-PII Assurance**: Output verified free of unmasked emails, phone numbers, customer names, or credentials.
3. **Deterministic State Priority Verification**: Rigorous matrix tests verifying `EMERGENCY_LOCKDOWN` overrules `ROLLBACK_REQUIRED`, `DEGRADED`, etc.
4. **Health Score Math Bounds**: Strict validation that all dimension scores and weighted totals are bounded within $[0.0, 100.0]$.
5. **RBAC Validation**: Unauthenticated requests return `401 Unauthorized`; allowed roles (`VIEWER`, `OPERATOR`, `ADMIN`) successfully retrieve governed telemetry.

---

## 10. Integration with Phase 10B Compliance & Governance Layer

The Intelligence Control Plane coordinates directly with **Phase 10B Compliance & Audit Intelligence** (Tab 14):
- **AuditLog Completeness**: Analyzes 10-category lifecycle event streams to ensure zero untracked records.
- **Decision Trace Provenance**: Validates 6-stage lifecycle chains from case creation to payment reconciliation.
- **18 Engineering Controls**: Feeds ML, financial, security, and human governance metrics into the deterministic compliance score (0–100) and regulatory export snapshot generator.

For full details, see [COMPLIANCE_GOVERNANCE.md](file:///d:/MEDIFLOW/RecoverIQ/docs/security/COMPLIANCE_GOVERNANCE.md).

---

## 11. Integration with Phase 10E Data Governance & Lineage Control Plane

The Intelligence Control Plane links directly to **Phase 10E Data Governance, Privacy Engineering, Data Lineage & Regulatory Controls** (Tab 17):
- **7-Node Cryptographic Provenance Graph**: Connects Control Plane decision traces directly to underlying data assets and SHA-256 digests.
- **HMAC Pseudonymization**: Sanitizes subject customer identifiers across case decision traces and multi-signal alerts.
- **25 Automated Privacy Controls**: Validates zero-PII data pipelines and statutory retention compliance.

For architectural specifications, see [DATA_GOVERNANCE.md](file:///d:/MEDIFLOW/RecoverIQ/docs/governance/DATA_GOVERNANCE.md) and [DATA_LINEAGE.md](file:///d:/MEDIFLOW/RecoverIQ/docs/governance/DATA_LINEAGE.md).

---

## 12. Integration with Phase 10F Fintech Performance Engineering & Capacity Planning

The Intelligence Control Plane incorporates **Phase 10F Fintech Performance Engineering, Scalability, Capacity Planning & High-Load Resilience** (Tab 18):
- **10-Factor Performance Health Score**: Continuously evaluates system efficiency, database latency, queue backpressure, and capacity utilization.
- **Safe Headroom & Scaling Advisory**: Provides deterministic headroom calculations (5,000 RPM safe limit, 71.0% headroom) and traffic forecasting (1x to 20x).
- **18 Performance Readiness Gates & Load Testing**: Enforces latency SLAs and financial isolation during synthetic load simulations.

For complete performance specifications, see [PERFORMANCE_ENGINEERING.md](file:///d:/MEDIFLOW/RecoverIQ/docs/performance/PERFORMANCE_ENGINEERING.md) and [CAPACITY_PLANNING.md](file:///d:/MEDIFLOW/RecoverIQ/docs/performance/CAPACITY_PLANNING.md).

---

## 13. Integration with Phase 10G Release Governance & Deployment Assurance

The Intelligence Control Plane incorporates **Phase 10G Fintech Architecture Governance, Change Management, Release Safety & Deployment Assurance** (Tab 19):
- **10-Factor Release Health Score**: Evaluates change risk, dependency DAG blast radius, contract compatibility, and canary performance.
- **18 Deterministic Readiness Gates**: Validates test coverage, financial isolation, security CVEs, API compatibility, and configuration drift before promotion.
- **Cryptographic Lineage DAG & Signed Audit Reports**: Connects commits, candidates, and approvals to SHA-256 evidence digests.
- **Human Governance Sign-off**: Enforces non-automated production deployment recommendations requiring human sign-off.

For complete release governance specifications, see [RELEASE_GOVERNANCE.md](file:///d:/MEDIFLOW/RecoverIQ/docs/release/RELEASE_GOVERNANCE.md) and [CHANGE_MANAGEMENT.md](file:///d:/MEDIFLOW/RecoverIQ/docs/release/CHANGE_MANAGEMENT.md).


