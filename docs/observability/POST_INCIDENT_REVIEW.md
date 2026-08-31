# RecoverIQ — Post-Incident Review (PIR) & Root Cause Analysis Guide

> **Phase 10D: Fintech Observability, Site Reliability Engineering (SRE), Incident Response & Production Operations**
> **Scope:** Blameless Postmortem Template, Root Cause Taxonomy, Corrective & Preventive Action Governance

---

## 1. Blameless Postmortem Philosophy

In high-reliability fintech operations, system failures are treated as **learning opportunities**. A Post-Incident Review (PIR) must focus on:
1. **Systemic Deficiencies:** Missing circuit breakers, inadequate connection pools, lack of rate limiting, or brittle timeout configurations.
2. **Detection & Response Gaps:** Why did the alert take $N$ minutes to fire? Why was MTTA longer than the SLA?
3. **Corrective vs. Preventive Measures:** Corrective actions fix the immediate issue; preventive actions ensure an entire class of failure cannot recur.

---

## 2. Root Cause Analysis (RCA) Taxonomy

RecoverIQ classifies incident root causes into 8 standardized categories with confidence ratings (`CONFIRMED`, `PROBABLE`, `HYPOTHESIS`):

```
┌─────────────────────────────────────────────────────────────────────────────────────────────┐
│                             STANDARDIZED ROOT CAUSE TAXONOMY                                │
│                                                                                             │
│  1. DATABASE                 • Connection pool saturation, lock contention, slow query      │
│  2. UPSTREAM_GATEWAY         • Payment gateway HTTP 502/504, API rate limit breach          │
│  3. NETWORK_CONNECTIVITY     • DNS resolution failure, TLS handshake timeout, packet drop   │
│  4. WORKER_CONCURRENCY       • Thread starvation, mutex deadlocks, unacknowledged jobs       │
│  5. MODEL_PERFORMANCE        • Prediction latency spike, model drift, memory leak           │
│  6. POLICY_MISCONFIGURATION  • Faulty rule syntax, unhandled edge-case in PolicyEngine      │
│  7. CONFIGURATION_DRIFT      • Inconsistent environment variables, expired secrets/certs    │
│  8. CODE_REGRESSION          • Unhandled null pointer, schema mismatch, unoptimized loop    │
└─────────────────────────────────────────────────────────────────────────────────────────────┘
```

---

## 3. Standard Post-Incident Review (PIR) Template

```markdown
# Post-Incident Review: [INCIDENT_ID] — [INCIDENT_TITLE]

## 1. Incident Metadata
- **Incident ID:** INC-OBS-YYYY-MMDD-NN
- **Severity:** SEV_1 / SEV_2 / SEV_3 / SEV_4
- **Date & Time (UTC):** YYYY-MM-DD HH:MM:SS
- **Incident Commander:** [NAME / ACTOR_ID]
- **Affected Services:** [LIST_OF_SERVICES]
- **Time to Detect (TTD):** X minutes
- **Mean Time to Acknowledge (MTTA):** Y minutes
- **Mean Time to Resolve (MTTR):** Z minutes

## 2. Executive Summary & Customer Impact
[Brief summary of what happened, customer/merchant impact, and financial isolation verification.]

## 3. Impact on SLOs & Error Budgets
- **Impacted SLOs:** [e.g., SLO-API-AVAIL-999]
- **Observed SLO Percentage:** 99.82% (Target: 99.90%)
- **Error Budget Consumed:** 14.5%

## 4. Chronological Incident Timeline (UTC)
| Timestamp | State Transition | Actor | Action / Event Description |
| :--- | :--- | :--- | :--- |
| HH:MM:SS | DETECTED | System | Alert ALT-GW-LAT-001 fired due to P95 > 200ms |
| HH:MM:SS | ACKNOWLEDGED | Operator-1 | Incident claimed by on-call engineer |
| HH:MM:SS | MITIGATING | SRE Lead | Circuit breaker opened in PolicyEngine |
| HH:MM:SS | RESOLVED | SRE Lead | Connection pool overflow cleared; P95 normalized |

## 5. Root Cause & Contributing Factors
- **Primary Root Cause Category:** DATABASE (Confidence: CONFIRMED)
- **Root Cause Details:** Slow non-indexed query on `recovery_actions` during morning batch processing.
- **Contributing Factors:**
  1. Concurrency spike in renewal volume.
  2. Connection pool max_overflow set to default 10 instead of 20.

## 6. Detection & Response Gaps
- **Detection Gap:** Alert threshold took 3 consecutive 1-minute samples to fire.
- **Response Gap:** MTTA delayed due to misconfigured escalation routing.

## 7. Action Items (Tracked in SRE Backlog)
### Corrective Actions (Immediate Fixes)
- [ ] ACT-001: Add index on `recovery_actions(status, scheduled_at)`.
- [ ] ACT-002: Increase database pool size from 10 to 25 connections.

### Preventive Actions (Long-term Prevention)
- [ ] ACT-003: Deploy query latency circuit breaker in PolicyEngine.
- [ ] ACT-004: Add multi-window burn rate alert for database connection saturation.
```

---

## 4. Postmortem Authoring via RecoverIQ API

Authorized operators can author and register PIR reports directly through the unified API:

```http
POST /api/recovery/intelligence/observability/postmortems
Content-Type: application/json
Authorization: Bearer <JWT_TOKEN>

{
  "incident_id": "INC-OBS-2026-0830-01",
  "title": "Database Connection Pool Saturation During Morning Spikes",
  "impact_summary": "P95 latency elevated to 320ms for 14 minutes. Zero financial mutations.",
  "root_cause_category": "DATABASE",
  "contributing_factors": [
    "Peak renewal traffic surge",
    "Slow query locking connection pool"
  ],
  "corrective_actions": [
    "Increased pool max_overflow to 20",
    "Added index on recovery_cases"
  ],
  "preventive_actions": [
    "Deploy slow-query circuit breaker in PolicyEngine",
    "Add p99 latency SLO alert"
  ]
}
```

---

## 5. Auditing & Safety Invariant

Every Post-Incident Report created in RecoverIQ is signed and written to `AuditLog` (`event_type='POST_INCIDENT_REPORT_CREATED'`). It is purely an operational record and produces **zero financial mutations**.
