# ML Incident Lifecycle, Runbooks & MTTA/MTTR Telemetry

## 1. Incident Severity Classification

| Severity Tier | Trigger Conditions | Automated Impact | Target MTTA | Target MTTR |
| :--- | :--- | :--- | :--- | :--- |
| **SEV-1 (Critical)** | Lineage DAG broken; severe prediction drift ($\text{PSI} \ge 0.35$); calibration collapse ($\text{ECE} \ge 0.10$); financial isolation breach. | Model marked `CRITICAL`; canary traffic diverted to previous stable rollback version; urgent paging. | $\le 5\text{ min}$ | $\le 30\text{ min}$ |
| **SEV-2 (High)** | Feature drift ($\text{PSI} \ge 0.25$); fairness disparity ($\text{DIR} < 0.80$); p99 latency $> 50\text{ms}$. | Model flagged `WARNING`; candidate promotion blocked; operator notification. | $\le 15\text{ min}$ | $\le 2\text{ hours}$ |
| **SEV-3 (Medium)** | Minor feature drift ($0.10 \le \text{PSI} < 0.25$); sample size drop $> 20\%$. | Telemetry warning logged; retraining advisory issued. | $\le 1\text{ hour}$ | $\le 24\text{ hours}$ |
| **SEV-4 (Low)** | Informational telemetry variance; scheduled audit review reminder. | Informational log; no operational disruption. | $\le 24\text{ hours}$ | $\le 72\text{ hours}$ |

---

## 2. Event-Sourced Incident Lifecycle

Every incident progresses through a strict, auditable state machine:

```
[DETECTED] ──(Operator Acknowledgment)──► [ACKNOWLEDGED] ──(Admin Remediation)──► [RESOLVED] ──► [CLOSED]
```

1. **Detection**: Automated surveillance triggers an incident based on gate failures or statistical threshold breaches.
2. **Acknowledgment**: Operators investigate the incident, input triage notes, and record acknowledgment timestamp (recording MTTA).
3. **Resolution**: System administrators apply remediations (e.g. executing rollback drill, tuning hyperparameter bounds) and record resolution details (recording MTTR).

---

## 3. Operational Runbooks

### Runbook 1: Critical Drift Resolution (`SEV-1` / `SEV-2`)
1. Inspect the feature PSI breakdown in Panel 6 of the ML Governance Control Plane.
2. Identify whether drift originates from upstream ETL changes or external macroeconomic debtor behavior shifts.
3. If upstream ETL schema changed, revert data pipeline to last verified schema hash (`GATE-ML-04`).
4. If debtor distribution changed, trigger candidate retraining on fresh 30-day window (`GATE-ML-03`).
5. Execute rollback drill if active production error rate exceeds 2.0%.

### Runbook 2: Instant Model Rollback Execution
1. Open the Model Rollback Panel (Panel 13) in the ML Governance Control Plane.
2. Verify previous stable version artifact checksum (`v0.9.8-stable`).
3. Click "Execute Rollback Switchover".
4. System swaps runtime binary pointer within 12.4 seconds ($\le 30\text{s}$ SLA).
5. Verify `GATE-ML-20` passes and record resolution in AuditLog.
