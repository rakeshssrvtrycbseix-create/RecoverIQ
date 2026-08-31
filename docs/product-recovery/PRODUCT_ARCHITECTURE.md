# RecoverIQ — Product Architecture

## 1. High-Level System Architecture

RecoverIQ is an enterprise-grade Autonomous AI Revenue Recovery platform designed to detect, diagnose, predict, and recover failed payments with strict, non-negotiable financial safety controls and observational isolation.

```
Incoming Failed Payment Event (Razorpay Webhook / Polling)
                    │
                    ▼
          [ Event Ingestion Engine ]
                    │
                    ▼
       [ Observational AI & ML Intelligence ]
       (XGBoost Recovery Prediction, Context Builder,
        Sanitized SHAP, Feature Drift Surveillance)
                    │
                    ▼ (Advisory Prediction Vector)
       ┌────────────────────────────────────┐
       │   POLICY ENGINE (SOLE AUTHORITY)   │
       │                                    │
       │   - Invariant: Δ RecoveryAction=0  │
       │   - Invariant: Δ Payment=0         │
       │   - Deterministic Rule Validation  │
       └─────────────────┬──────────────────┘
                         │
     ┌───────────────────┴───────────────────┐
     │ (ALLOWED)                             │ (HUMAN_REVIEW / BLOCKED)
     ▼                                       ▼
[ Action Scheduler ]                   [ Human Review Queue ]
     │                                       │
     ▼                                       ▼ (Operator/Admin Approval)
[ Action Dispatcher ]                  [ PolicyEngine Signoff ]
     │                                       │
     ▼                                       ▼
[ Razorpay Test API ]                  [ Append-Only Audit Trail ]
```

---

## 2. Core Architectural Pillars

### A. Authoritative Policy Engine Boundary
- **Principle**: The AI Agent and ML models are strictly advisory. They generate proposed recovery actions, confidence scores, and reasoning summaries.
- **Enforcement**: Only `PolicyEngine` can authorize action creation (`ALLOWED`), route high-risk/high-value cases to the `Human Review Queue` (`HUMAN_REVIEW`), or block unsafe actions (`BLOCKED`).
- **Mathematical Invariant**:
  $$\Delta \text{RecoveryAction} = 0 \quad \text{for all observational / control-plane queries}$$
  $$\text{Calls}(\text{ActionDispatcher}) = 0 \quad \text{outside authorized worker execution}$$

### B. Zero-Trust & Privacy Contract
- **No PII Persistence**: Customer names, emails, phone numbers, and payment instruments are masked at ingestion (`aarav.m****@example.in`, `+91 98**** 1029`).
- **Secrets Sanitization**: API tokens, JWT keys, and provider secrets are strictly excluded from telemetry, logs, and frontend payloads.

### C. Unified Control Plane
- **Executive Overview**: Real-time recovered revenue, amount at risk, recovery clearance rate, and worker telemetry.
- **Recovery Cases & Human Review**: Granular operational aggregate tracking with interactive approval workflows and state preservation.
- **Intelligence & Governance**: Model risk management, counterfactual simulations, FinOps cost governance, fintech observability (SLIs/SLOs), and release safety gates.
