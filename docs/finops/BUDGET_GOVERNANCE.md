# FinOps Budget Surveillance & Multi-Tier Governance

## Overview

RecoverIQ implements deterministic **Budget Governance** to surveil daily, monthly, and quarterly cloud expenditure. Budgets are parameterized with multi-stage alert thresholds and automated notifications that escalate across administrative channels without interrupting production processing.

---

## Budget State Machine

Budgets transition through a deterministic finite state machine based on actual burn rate and projected end-of-period overrun:

```
       ┌───────────┐
       │  NORMAL   │  (Burn Rate < 80%)
       └─────┬─────┘
             │ Actual spend crosses 80%
             ▼
       ┌───────────┐
       │  WARNING  │  (80% <= Burn Rate < 95%)
       └─────┬─────┘
             │ Actual spend crosses 95%
             ▼
       ┌───────────┐
       │ CRITICAL  │  (95% <= Burn Rate < 100%)
       └─────┬─────┘
             │ Actual spend exceeds 100%
             ▼
       ┌───────────┐
       │ EXHAUSTED │  (Burn Rate >= 100%)
       └───────────┘
```

---

## Multi-Tier Alert Thresholds

Each budget defines default notification thresholds:

1. **50% Threshold (Pace Notification)**: Sent to Engineering Leads to confirm steady linear burn.
2. **80% Threshold (Warning Notification)**: FinOps Slack webhook triggered; review optimization recommendations.
3. **95% Threshold (Critical Alert)**: PagerDuty alert to Platform SRE; freeze non-essential load test / shadow runs.
4. **100% Threshold (Exhaustion Notice)**: Executive escalation to VP Engineering & Head of Finance.

---

## Budget Configuration API & Auditing

All budget modifications are strictly audited in the `audit_logs` table under entity type `budget_event`.

### Audit Invariant
- Every modification records `previous_state`, `new_state`, `actor_id`, and `created_at`.
- Unallocated funds or overruns are calculated in real-time on every telemetry sync.
