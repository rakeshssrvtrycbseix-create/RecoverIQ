# RecoverIQ — Governed Strategy Recommendation & Decision Governance (Phase 9E)

## 1. Overview & Primary Objective

Phase 9E represents the pinnacle of RecoverIQ's intelligence architecture. It transforms the observational outputs of:
$$\text{Phase 9A Evaluation} \longrightarrow \text{Phase 9B Model Governance} \longrightarrow \text{Phase 9C Strategy Optimization} \longrightarrow \text{Phase 9D Counterfactual Simulation} \longrightarrow \mathbf{\text{Phase 9E Governed Recommendation}}$$
into an explainable, versioned, evidence-backed strategy proposal subject to deterministic governance gates and strict human operator review.

```
       ┌────────────────────────────────────────────────────────┐
       │   Phase 9A: ML Outcome Evaluation & Performance       │
       └──────────────────────────┬─────────────────────────────┘
                                  ▼
       ┌────────────────────────────────────────────────────────┐
       │   Phase 9B: Model Governance & Drift Monitoring        │
       └──────────────────────────┬─────────────────────────────┘
                                  ▼
       ┌────────────────────────────────────────────────────────┐
       │   Phase 9C: Strategy Optimization & Champion ERV       │
       └──────────────────────────┬─────────────────────────────┘
                                  ▼
       ┌────────────────────────────────────────────────────────┐
       │   Phase 9D: Counterfactual What-If Simulation Uplift   │
       └──────────────────────────┬─────────────────────────────┘
                                  ▼
       ┌────────────────────────────────────────────────────────┐
       │   Phase 9E: Governed Recommendation & Human Review     │
       └──────────────────────────┬─────────────────────────────┘
                                  │
         ┌────────────────────────┴────────────────────────┐
         ▼                                                 ▼
┌──────────────────┐                             ┌───────────────────┐
│ Operator Approve │                             │  Operator Reject  │
│ (Endorsement)    │                             │  (Closed / Logged)│
└──────────────────┘                             └───────────────────┘
```

---

## 2. Absolute Architectural Invariant: Financial Isolation

> **CRITICAL ARCHITECTURAL GUARANTEE:**
> Governed strategy recommendations are **strictly advisory**. Approval of a strategy recommendation represents human operator endorsement and updates the governance state machine to `APPROVED`.
> 
> **Approval MUST NOT and DOES NOT:**
> - Create a `RecoveryAction`
> - Schedule an action in `RecoveryActionScheduler`
> - Invoke the `RecoveryWorker`
> - Invoke the `ActionDispatcher`
> - Invoke `RazorpayActionProvider` or any payment gateway
> - Mutate `Payment.status`
> - Mutate `RecoveryCase.status`
> - Bypass the authoritative `PolicyEngine`

Financial actions are exclusively scheduled through verified recovery lifecycle webhooks evaluated by the authoritative `PolicyEngine`.

---

## 3. Deterministic Governance Safety Gates

Before any active recommendation is synthesized or presented for human review, the engine evaluates strict deterministic rules:

| Gate | Condition | Governance Decision |
| :--- | :--- | :--- |
| **Rule 1: Insufficient Sample** | $N < 10$ historical resolved cases | `NO_RECOMMENDATION` (No active proposal) |
| **Rule 2: Limited Sample** | $10 \le N < 30$ historical cases | `REVIEW_REQUIRED`, `reliability = LIMITED` (Warning in diagnostics) |
| **Rule 3: Sufficient Sample** | $N \ge 30$ historical cases | `REVIEW_REQUIRED`, `reliability = SUFFICIENT` |
| **Rule 4: Degraded Model** | Model health status == `DEGRADED` | `NO_RECOMMENDATION` (Recommendation blocked) |
| **Rule 5: Insufficient Model Telemetry** | Model health == `INSUFFICIENT_DATA` ($N < 10$) | `NO_RECOMMENDATION` |
| **Rule 6: Data Quality Anomalies** | Invalid predictions $> 0$ | `NO_RECOMMENDATION` (Recommendation blocked) |
| **Rule 7: Non-Positive Uplift** | Simulated rate delta $\le 0.0$ | `NO_RECOMMENDATION` (Recommendation blocked) |
| **Rule 8: Negative Incremental ERV** | Estimated incremental ERV $\le 0$ | `NO_RECOMMENDATION` (Recommendation blocked) |

---

## 4. Recommendation Confidence Scoring

Recommendation Confidence is a synthesized metric distinct from individual ML prediction confidence or AI advisory confidence. It measures the aggregate reliability of the evidence trail:

$$\text{Confidence Score} = \text{Sample Reliability} + \text{Model Health} + \text{Data Quality} + \text{Uplift Strength}$$

1. **Sample Reliability (0.0 to 0.40):**
   - $N \ge 30 \implies +0.40$
   - $10 \le N < 30 \implies +0.20$
   - $N < 10 \implies +0.00$
2. **Model Health (0.0 to 0.30):**
   - `HEALTHY` $\implies +0.30$
   - `WARNING` $\implies +0.15$
   - `DEGRADED` / `INSUFFICIENT_DATA` $\implies +0.00$
3. **Data Quality (0.0 to 0.15):**
   - 0 invalid predictions $\implies +0.15$
   - $> 0$ anomalies $\implies +0.00$
4. **Relative Uplift Strength (0.0 to 0.15):**
   - Relative uplift $\ge 10.0\% \implies +0.15$
   - Relative uplift $> 0.0\% \implies +0.08$

**Confidence Levels:**
- $\text{Score} \ge 0.75 \implies \mathbf{HIGH}$
- $\text{Score} \ge 0.45 \implies \mathbf{MEDIUM}$
- $\text{Score} < 0.45 \implies \mathbf{LOW}$

---

## 5. Integer Paise Financial Representation

Expected Recovery Value (ERV) and Estimated Incremental ERV adhere to RecoverIQ's absolute financial standard:
$$\text{ERV}_{\text{paise}} = \text{round}(\text{AmountAtRisk}_{\text{paise}} \times \text{RecoveryProbability})$$
$$\text{Incremental ERV}_{\text{paise}} = \text{Alternative ERV}_{\text{paise}} - \text{Baseline ERV}_{\text{paise}}$$

All currency fields (`baseline_erv_paise`, `alternative_erv_paise`, `incremental_erv_paise`) are strictly 64-bit signed integers. Floating-point currency representation is forbidden.

---

## 6. Audit-Backed Persistence & Lifecycle State Machine

Recommendations maintain full lifecycle state history through immutable `AuditLog` records without requiring database schema alterations (0 migrations):

```
       ┌────────────────────────────────────────────────────────┐
       │                   RECOMMENDATION_CREATED               │
       │                   (status: REVIEW_REQUIRED)            │
       └──────────────────────────┬─────────────────────────────┘
                                  │
         ┌────────────────────────┼────────────────────────┐
         │ (Operator Approve)     │ (Operator Reject)      │ (TTL Expired / Stale)
         ▼                        ▼                        ▼
┌──────────────────┐    ┌──────────────────┐    ┌──────────────────┐
│RECOMMENDATION_   │    │RECOMMENDATION_   │    │RECOMMENDATION_   │
│APPROVED          │    │REJECTED          │    │EXPIRED           │
│(status: APPROVED)│    │(status: REJECTED)│    │(status: EXPIRED) │
└──────────────────┘    └──────────────────┘    └──────────────────┘
```

- `RECOMMENDATION_CREATED`: Recorded upon active proposal generation with complete evidence snapshot.
- `RECOMMENDATION_APPROVED`: Recorded when an authorized operator approves the proposal.
- `RECOMMENDATION_REJECTED`: Recorded when an authorized operator rejects the proposal.
- `RECOMMENDATION_EXPIRED`: Recorded when recommendation expires ($TTL = 7\text{ days}$) or underlying ML model degrades.

---

## 7. Role-Based Access Control (RBAC) & Trust Boundaries

All Phase 9E endpoints are protected by cryptographic JWT validation and RBAC dependencies:

| Endpoint | Method | Required Role | Description |
| :--- | :--- | :--- | :--- |
| `/api/recovery/intelligence/recommendations` | `GET` | `viewer` | List versioned recommendations and active proposal |
| `/api/recovery/intelligence/recommendations/{id}` | `GET` | `viewer` | Get detailed evidence snapshot for a proposal |
| `/api/recovery/intelligence/recommendations/{id}/approve` | `POST` | `operator` | Approve recommendation (Endorsement only) |
| `/api/recovery/intelligence/recommendations/{id}/reject` | `POST` | `operator` | Reject recommendation |

### Actor Identity Verification
Client body payloads containing `operator_id` are strictly ignored. Actor identity is derived solely from verified server-side JWT claims (`current_user.id`, `current_user.role`).

---

## 8. Zero PII & Zero Secrets Guarantee

All API responses strictly project aggregated statistical summaries and anonymized segment attributes. Zero customer identifiers, email addresses, phone numbers, card numbers, or cryptographic tokens are ever exposed.
