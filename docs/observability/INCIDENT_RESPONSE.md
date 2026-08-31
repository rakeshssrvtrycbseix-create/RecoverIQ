# RecoverIQ — Incident Management Lifecycle & SLA Manual

> **Phase 10D: Fintech Observability, Site Reliability Engineering (SRE), Incident Response & Production Operations**
> **Scope:** Severity Classifications (SEV_1–SEV_4), MTTA/MTTR SLAs, Incident State Machines, Escalation Protocols, and Event-Sourced Audit Logging

---

## 1. Incident Severity Classification & SLA Matrix

RecoverIQ enforces strict, deterministic Mean-Time-to-Acknowledge (MTTA) and Mean-Time-to-Resolve (MTTR) SLAs based on incident severity:

| Severity Level | Classification | Impact Scope | MTTA SLA | MTTR Target | Escalation Pathway |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **SEV_1** | Critical Outage | Core payment ingestion halted, database primary down, or critical financial data corruption risk. | $\le 5\text{ minutes}$ | $\le 30\text{ minutes}$ | On-Call Lead $\rightarrow$ VP Engineering $\rightarrow$ Emergency War Room |
| **SEV_2** | Major Degradation | Payment retry workers degraded (>5% error rate), or critical SLO error budget fast burn. | $\le 15\text{ minutes}$ | $\le 2\text{ hours}$ | SRE Team $\rightarrow$ Service Owner $\rightarrow$ Tech Lead |
| **SEV_3** | Minor Impairment | Non-blocking telemetry lag, intermittent ML inference fallback, or single worker node stall. | $\le 60\text{ minutes}$ | $\le 8\text{ hours}$ | Component On-Call Engineer |
| **SEV_4** | Informational / Cosmetic | Minor logging discrepancy, non-critical dashboard rendering delay, or scheduled maintenance alert. | $\le 4\text{ hours}$ | $\le 48\text{ hours}$ | Regular SRE Backlog Triage |

---

## 2. Event-Sourced Incident State Machine

Every incident in RecoverIQ follows an **event-sourced state machine** stored in `AuditLog` records with actor attribution and timestamps:

```
                  ┌──────────────┐
                  │   DETECTED   │
                  └──────┬───────┘
                         │
        handleAcknowledgeObsIncident() [MTTA measured]
                         │
                         ▼
                  ┌──────────────┐
                  │ ACKNOWLEDGED │
                  └──────┬───────┘
                         │
         handleEscalateObsIncident() (If breached)
                         │
                         ▼
                  ┌──────────────┐
                  │  ESCALATED   │
                  └──────┬───────┘
                         │
                  ┌──────▼───────┐
                  │  MITIGATING  │
                  └──────┬───────┘
                         │
          handleResolveObsIncident() [MTTR measured]
                         │
                         ▼
                  ┌──────────────┐
                  │   RESOLVED   │
                  └──────┬───────┘
                         │
         handleCreatePostmortemSubmit() (Within 24h)
                         │
                         ▼
                  ┌──────────────┐
                  │  POSTMORTEM  │
                  └──────────────┘
```

### State Definitions & Transition Rules

1. `DETECTED`: Incident automatically created by rule breach (e.g. `ALT-GW-AVAIL-001`) or manually logged by operator. MTTA timer begins.
2. `ACKNOWLEDGED`: On-call operator confirms receipt via UI or API. MTTA timer concludes.
3. `ESCALATED`: Incident transitioned to Admin review due to SLA breach or cross-subsystem blast radius.
4. `MITIGATING`: Active rollback, failover, or traffic throttling applied to protect error budgets.
5. `RESOLVED`: Service metrics restored to baseline for $>15$ continuous minutes. MTTR timer concludes.
6. `POSTMORTEM`: Structured post-incident review completed and linked in PIR database.

---

## 3. SHA-256 Fingerprint Deduplication Protocol

To eliminate alert storms during cascading failures, RecoverIQ computes a deterministic SHA-256 fingerprint for every alert and incident candidate:

$$\text{Fingerprint} = \text{SHA-256}\left(\text{rule\_code} + \text{service} + \text{severity} + \text{trigger\_entity}\right)$$

* When an alert condition repeats within the rolling 1-hour window, the existing incident record increments `occurrence_count` and updates `last_detected` without spawning duplicate notification tickets.

---

## 4. Incident Escalation & Communication Protocol

### 4.1. SEV_1 War Room Workflow

1. **Phase 1 (Minute 0–5):** Automated alert triggers on-call pager; Incident Commander (IC) claims incident (`POST /incidents/{id}/acknowledge`).
2. **Phase 2 (Minute 5–15):** IC opens Incident War Room; Tech Lead assesses database and gateway health.
3. **Phase 3 (Minute 15–30):** Apply non-mutating mitigation (e.g., enable circuit breakers in PolicyEngine, divert traffic to standby replica).
4. **Phase 4 (Resolution):** Verify zero financial delta in `Payment` and `RecoveryAction` tables.
5. **Phase 5 (Postmortem):** Author PIR report within 24 hours.

---

## 5. Audit Trail & Legal Safety Notice

All incident state transitions emit immutable audit events to the audit ledger:
* `OBSERVABILITY_INCIDENT_DETECTED`
* `OBSERVABILITY_INCIDENT_ACKNOWLEDGED`
* `OBSERVABILITY_INCIDENT_ESCALATED`
* `OBSERVABILITY_INCIDENT_RESOLVED`
* `POST_INCIDENT_REPORT_CREATED`

**Strict Guarantee:** Incident response workflows operate strictly in the telemetry and observability layer. Under no circumstances will incident response actions execute ad-hoc financial mutations or bypass PolicyEngine authorization.
