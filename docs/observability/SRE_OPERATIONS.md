# RecoverIQ — Site Reliability Engineering (SRE) Operations Manual

> **Phase 10D: Fintech Observability, Site Reliability Engineering (SRE), Incident Response & Production Operations**
> **Scope:** SRE Runbooks, SLO Compliance, Multi-Window Error Budget Policies, and Operational Procedures

---

## 1. SRE Core Principles

1. **Service Reliability as a Feature:** Reliability is non-negotiable in financial recovery processing. System instability leads to skipped recovery windows and missed revenue.
2. **Error Budget as the Rate-Limiter of Change:** Feature deployments, model rollouts, and aggressive scheduling are governed by remaining error budgets.
3. **Automated Detection, Governed Remediation:** Alerts and root-cause candidates are detected automatically within 30 seconds; remediation actions are applied via strict change control without autonomous financial mutations.
4. **Blameless Operations:** SRE postmortems emphasize systemic improvements, architectural guardrails, and automated regression testing over human culpability.

---

## 2. Service Level Objectives (SLOs) & Target Standards

RecoverIQ enforces 8 core Engineering SLOs across all environments:

| SLO Code | Metric Name | Target | Measurement Window | Target Service | Failure Impact |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `SLO-API-AVAIL-999` | API Gateway Availability | $\ge 99.90\%$ | 30-day rolling | `api_gateway` | Client recovery request rejections |
| `SLO-API-LATENCY-P95-200` | P95 API Response Latency | $\le 200\text{ ms}$ | 30-day rolling | `api_gateway` | Webhook timeouts & client lag |
| `SLO-POLICY-DECISION-50` | PolicyEngine Decision Latency | $\le 50\text{ ms}$ | 30-day rolling | `policy_engine` | Action dispatch queue delays |
| `SLO-ML-INFERENCE-100` | ML Inference Latency | $\le 100\text{ ms}$ | 30-day rolling | `ml_inference` | Offline recovery estimation backup |
| `SLO-WORKER-SUCCESS-99` | Worker Execution Success Rate | $\ge 99.00\%$ | 30-day rolling | `recovery_worker` | Action claim failures / job stalls |
| `SLO-WEBHOOK-INGESTION-999` | Webhook Ingestion Success Rate | $\ge 99.90\%$ | 30-day rolling | `webhook_ingress` | Dropped failure notifications |
| `SLO-DATABASE-QUERY-P95-10` | Database Query P95 Latency | $\le 10\text{ ms}$ | 30-day rolling | `database_primary` | Connection pool saturation |
| `SLO-AGGREGATE-ERROR-005` | Aggregate Platform Error Rate | $\le 0.50\%$ | 30-day rolling | `platform_global` | Global system instability |

---

## 3. Multi-Window Error Budget Management

Error budgets allow engineering teams to take calculated risks (e.g., canary rollouts, continuous model training) while protecting uptime.

### 3.1. Error Budget Formula

$$\text{Error Budget} = 100.0\% - \text{Target SLO Percentage}$$
$$\text{Consumed Budget} = \frac{\text{Failed Requests}}{\text{Total Requests} \times (1.0 - \text{Target SLO})}$$
$$\text{Remaining Budget \%} = \max\left(0, 100.0\% - \text{Consumed Budget \%}\right)$$

### 3.2. Multi-Window Burn Rate Surveillance

Burn rates indicate how rapidly an error budget is being consumed relative to standard degradation:

$$\text{Burn Rate} = \frac{\text{Observed Error Rate}}{\text{Allowed Error Rate}}$$

* **1-Hour Window (Short-Term Spike):** Burn rate $> 14.4\text{x}$ $\rightarrow$ 2% of budget consumed in 1 hour. Triggers immediate SEV_1 alert.
* **6-Hour Window (Medium-Term Trend):** Burn rate $> 6.0\text{x}$ $\rightarrow$ 5% of budget consumed in 6 hours. Triggers SEV_2 alert and review.
* **24-Hour Window (Long-Term Drift):** Burn rate $> 2.0\text{x}$ $\rightarrow$ 10% of budget consumed in 24 hours. Triggers SEV_3 notification.

```
+---------------------+-------------------+---------------------------------------------------+
| Remaining Budget    | Burn Rate Status  | Operational SRE Action Required                   |
+---------------------+-------------------+---------------------------------------------------+
| 80% to 100%         | Normal (< 1.5x)   | Normal operations; non-blocking canary rollouts.  |
| 50% to 79%          | Elevated (1.5-3x) | Monitor active deployments; review worker load.  |
| 20% to 49%          | High (3.0-6.0x)   | Freeze non-critical rollouts; conduct SRE triage. |
| 1% to 19%           | Critical (> 6.0x) | Full production freeze; escalate to SEV_2.        |
| 0% (Exhausted)      | Exhausted         | Emergency lockdown; rollback pending deployments. |
+---------------------+-------------------+---------------------------------------------------+
```

---

## 4. SRE Standard Operating Procedures (Runbooks)

### 4.1. Runbook SRE-001: Elevated P95 API Latency (>200ms)

1. **Detection:** Alert `ALT-GW-LAT-001` fires or P95 KPI card turns Amber/Red.
2. **Triaging:** Check `/api/recovery/intelligence/observability/traces` to isolate slow downstream dependency (`database_primary`, `policy_engine`, or `razorpay_adapter`).
3. **Mitigation:**
   - If Database query latency elevated: check active connection pool in `/observability/database`.
   - If External Gateway elevated: verify Circuit Breaker status in PolicyEngine.
   - If CPU/Memory bound: scale worker and API replica pools.
4. **Verification:** Confirm P95 latency falls below 100ms for 3 consecutive 1-minute windows.

### 4.2. Runbook SRE-002: Worker Queue Depth Spike (>500 jobs)

1. **Detection:** Alert `ALT-WK-QUEUE-001` triggers.
2. **Triaging:** Inspect `/api/recovery/intelligence/observability/queues` and `/workers` for active concurrency limits.
3. **Mitigation:**
   - Verify DB row-lock contention (`SELECT ... FOR UPDATE SKIP LOCKED`).
   - Re-balance worker threads across partitions.
   - Validate that external payment gateway rate-limiters are not stalling workers.
4. **Verification:** Oldest job age decreases below 60 seconds.

### 4.3. Runbook SRE-003: Webhook Ingestion Failure Spike (>0.10%)

1. **Detection:** Alert `ALT-WH-FAIL-001` triggers.
2. **Triaging:** Query `/api/recovery/intelligence/observability/webhooks` for replay rejection rate vs signature verification failure rate.
3. **Mitigation:**
   - If signature failure: verify webhook secret configuration in secrets manager.
   - If duplicate replay surge: confirm Redis deduplication cache health.
4. **Verification:** Success rate returns to $\ge 99.90\%$.

---

## 5. Operational Governance & Compliance Attestation

This document establishes operational compliance with ISO/IEC 27001 (A.12.1 Operational Procedures) and SOC 2 Type II (CC7.2 Incident Detection and Resolution). All metric evaluations and SRE state changes are recorded immutably in `AuditLog` with actor attribution.
