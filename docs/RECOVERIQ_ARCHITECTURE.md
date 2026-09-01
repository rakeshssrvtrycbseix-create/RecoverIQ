# RecoverIQ — Production Architecture Specification

**Status**: ACTIVE & VERIFIED  
**Version**: 1.0.0  
**Stack**: FastAPI (Python 3.12) / SQLAlchemy ORM / Next.js 16.3 (React 19 / TypeScript 5 / Tailwind CSS v4) / SQLite & PostgreSQL  

---

## 1. System Overview & Core Invariants

RecoverIQ is an autonomous revenue-recovery platform for enterprise fintech and SaaS billing workflows. It addresses payment failure recovery through a combination of statistical machine learning, LLM decision orchestration, and strict, non-negotiable deterministic financial policy enforcement.

```
                           [ INCOMING FAILED PAYMENT / WEBHOOK ]
                                            │
                                            ▼
                                 [ RECOVERY CASE ENGINE ]
                                 (OPEN -> ANALYZING)
                                            │
                                            ▼
                              [ ML PREDICTION HEURISTICS ]
                             (Recovery Probability, Risk Score)
                                            │
                                            ▼
                                 [ AI DECISION AGENT ]
                              (Proposed Action & Delay Hours)
                                            │
                                            ▼
                    ┌───────────────────────────────────────────────┐
                    │        POLICYENGINE (SOLE AUTHORITY)          │
                    │                                               │
                    │ - Evaluates Hard Financial/Security Rules    │
                    │ - Zero LLM/Network Dependency                 │
                    │ - Outcomes: ALLOWED | HUMAN_REVIEW | BLOCKED  │
                    │ - Authoritative Financial Isolation Invariant │
                    └───────────────────────┬───────────────────────┘
                                            │
                   ┌────────────────────────┴────────────────────────┐
                   │                                                 │
          (ALLOWED Action)                                  (HUMAN_REVIEW Queued)
                   │                                                 │
                   ▼                                                 ▼
        [ ACTION DISPATCHER ]                             [ HUMAN REVIEW QUEUE ]
                   │                                                 │
                   ▼                                                 ▼ (Operator Approval)
        [ RAZORPAY / PROVIDER ] ───────────┐                         │
                   │                       │                         │
                   ▼                       ▼                         ▼
         [ ACTION RESULT ]       [ APPEND-ONLY AUDITLOG ] ◄──────────┘
                   │                       │
                   ▼                       ▼
         [ RECOVERY CASE ]       [ 22-TAB CONTROL PLANE ]
        (RECOVERED / CLOSED)     (9L, 10A–10J Analytics & Health)
```

---

## 2. The Core Recovery Loop

The complete deterministic lifecycle follows 10 distinct operational phases:

1. **Authentication & RBAC**:
   - Cryptographically signed JWT tokens issued via `/api/auth/token` with HMAC-SHA256 and JTI tracking.
   - 3-tier role hierarchy: `VIEWER` (Read-only analytics) < `OPERATOR` (Case approvals, canary testing) < `ADMIN` (Security policy, promotion, key management).
   - Instant token revocation via in-memory blacklist tripwires.

2. **Dashboard Overview**:
   - Aggregated operational and financial metrics calculated directly from database queries (`/api/recovery/metrics`).
   - Displays real totals: cases count, amount at risk, recovered amount (in paise), clearance rate, action statuses, and worker telemetry.
   - Zero hardcoded or fabricated values.

3. **Payments & Ingestion**:
   - Webhooks ingested via `/webhooks/razorpay` with constant-time HMAC-SHA256 signature verification over raw request body bytes.
   - Replay protection with strict timestamp age tolerance windows.
   - PII sanitization (masking email and phone numbers) before persistence.
   - Idempotent deduplication against `payment_events`.

4. **Recovery Case Engine**:
   - State machine governing case lifecycle:
     $$\text{OPEN} \longrightarrow \text{ANALYZING} \longrightarrow \text{ACTION\_PENDING} \longrightarrow \text{IN\_RECOVERY} \longrightarrow \text{RECOVERED} \mid \text{CLOSED}$$
     $$\text{ANALYZING} \longrightarrow \text{ESCALATED\_HUMAN} \longrightarrow \text{ACTION\_PENDING} \mid \text{CLOSED}$$
   - Prevents invalid or illegal state transitions.

5. **ML Prediction Engine**:
   - Generates structured prediction vectors:
     $$\hat{y} = \langle P(\text{recovery}), \text{RiskTier}, \text{PredictedChannel}, \text{OptimalDelayHours} \rangle$$
   - Persisted immutably in `ml_predictions`.

6. **Authoritative PolicyEngine**:
   - Validates AI proposed actions against 7 deterministic rules in strict precedence order:
     1. `POL-CASE-RESOLVED`: Blocks actions on terminal (RECOVERED/CLOSED) cases.
     2. `POL-RISK-TIER`: Blocks actions on `BLOCKED` risk tier customers.
     3. `POL-MAX-ATTEMPTS`: Blocks retries exceeding 3 attempts or case maximums.
     4. `POL-PERM-FAIL`: Blocks retries on permanent card/account failures (`card_blocked`, `account_closed`, `fraud_suspected`).
     5. `POL-RATE-LIMIT`: Enforces 2-hour minimum cool-down between retries.
     6. `POL-HIGH-VALUE`: Routes retries $\ge ₹50,000$ (5,000,000 paise) to `HUMAN_REVIEW`.
     7. `POL-CONF-FLOOR`: Routes predictions with confidence $< 0.40$ to `HUMAN_REVIEW`.
   - Produces authoritative `PolicyDecision` entity.

7. **Human Review Queue**:
   - Operator review interface for `HUMAN_REVIEW` cases (`/api/recovery/human-review`).
   - Operators can inspect customer risk, failure context, ML reasoning, and policy trigger.
   - Approvals execute `/approve`, updating policy state and scheduling the recovery action.
   - Dismissals execute `/dismiss`, recording operational rejection in the audit trail.

8. **Action Dispatcher**:
   - Controlled execution of authorized actions via `ActionDispatcher`.
   - Atomic state transitions (`SCHEDULED` -> `EXECUTING` -> `COMPLETED` / `FAILED`).
   - Sensitive payload validation prevents credentials or raw PII from reaching provider adapters.

9. **Append-Only Audit Trail**:
   - Every state change, policy evaluation, approval, and execution creates an immutable `AuditLog` entry.
   - Contains actor type, actor ID, entity ID, previous state, new state, and metadata diff.

10. **Analytics & Control Planes**:
    - Purely observational, non-mutating dashboards providing deep insight into ML governance, FinOps, SRE observability, resilience, and security.

---

## 3. Financial Isolation Invariants

To guarantee absolute financial safety, the system enforces mathematical and architectural isolation across all intelligence and control plane layers:

$$\Delta \text{RecoveryAction} = 0$$
$$\Delta \text{Payment} = 0$$
$$\Delta \text{RecoveryCase Financial Balance} = 0$$
$$\text{Calls}(\text{ActionDispatcher}) = 0$$
$$\text{Calls}(\text{RazorpayPaymentProvider}) = 0$$

All intelligence evaluations, counterfactual simulations, drift monitors, FinOps scorecards, and resilience tests execute in read-only / simulation mode.

---

## 4. Control Plane Architecture (9L & 10A–10J)

| Module | Purpose | Key Metrics & Data Sources |
| :--- | :--- | :--- |
| **9L Control Plane** | Unified governance & lineage | Global system health, cross-subsystem dependencies, decision trace graphs. |
| **10A Security & Trust** | Security posture & secrets hygiene | 7 active security controls, PII scanner, token revocation blacklist, threat counts. |
| **10B Compliance** | Regulatory framework alignment | DPDP, RBI, and SOC2 control matrices, audit log coverage, governance risk scores. |
| **10C Resilience** | Disaster recovery & business continuity | Service availability, RTO/RPO compliance, automated DR runbooks, observational blast radius simulations. |
| **10D Observability & SRE** | Production telemetry & SLIs/SLOs | P50/P95/P99 latencies, error budgets, alert deduplication fingerprints, post-incident postmortems. |
| **10E Data Governance** | Privacy engineering & data catalog | Data asset classification, retention schedules, erasure eligibility evaluations, zero-PII validation. |
| **10F Performance** | Capacity planning & load resilience | Throughput (RPM), queue backpressure, database pool utilization, capacity forecasting. |
| **10G Release Governance** | Change safety & architectural gates | Change requests, API backward compatibility checks, database schema drift, canary evaluation. |
| **10H Zero Trust** | Identity & access perimeter | Service identity registry, authorization matrix, threat indicator scoring, attack chain reconstruction. |
| **10I FinOps** | Cloud economics & cost governance | Unit economics (cost per recovery), cost allocation by service, budget variance, waste findings. |
| **10J AI/ML Governance** | Responsible AI & model risk | 5 canonical models, Champion/Challenger registry, PSI drift surveillance, SHAP feature importance, 22 readiness gates. |

---

## 5. Database Schema & Entity Relationships

```
┌───────────────┐        ┌──────────────┐        ┌──────────────────┐
│   Customer    │◄───────┤   Payment    │◄───────┤  PaymentAttempt  │
└───────┬───────┘        └──────┬───────┘        └──────────────────┘
        │                       │
        │                       ▼
        │                ┌──────────────┐        ┌──────────────────┐
        └───────────────►│ RecoveryCase │◄───────┤   PaymentEvent   │
                         └──────┬───────┘        └──────────────────┘
                                │
        ┌───────────────────────┼────────────────────────┐
        ▼                       ▼                        ▼
┌──────────────┐        ┌──────────────┐        ┌──────────────────┐
│ MLPrediction │◄───────┤ AgentDecision│        │    AuditLog      │
└──────────────┘        └───────┬──────┘        └──────────────────┘
                                │
                                ▼
                        ┌──────────────┐
                        │PolicyDecision│
                        └───────┬──────┘
                                │
                                ▼
                        ┌──────────────┐        ┌──────────────────┐
                        │RecoveryAction├───────►│   ActionResult   │
                        └──────────────┘        └──────────────────┘
```

---

## 6. Security, Zero-Trust & Privacy Contract

1. **Zero-PII Storage**: All customer emails and phone numbers in analytics and operational responses are masked at ingestion (e.g. `aa****@example.in`, `+91 98**** 1029`).
2. **Zero-Secret Exposure**: No private keys, JWT signing keys, or provider secrets are exposed via API or logged to standard output.
3. **Strict RBAC Enforcement**: Role checks are enforced at the FastAPI router dependency level via `require_viewer`, `require_operator`, and `require_admin`.
4. **Injection & Payload Hardening**: Request payloads are subject to recursive scanning against SQL injection patterns, path traversal sequences, and unauthorized keys.
