# FinOps Operational Runbooks & Incident Response

## Runbook Overview

This document provides step-by-step Standard Operating Procedures (SOPs) for responding to FinOps incidents, budget overruns, cost anomalies, and optimization workflows within RecoverIQ.

---

## SOP-FIN-01: Critical Cost Anomaly Triaging

### Trigger Condition
Alert received from `Cost Anomaly Radar` with severity `CRITICAL` or `HIGH` (e.g., microservice hourly spend $> +100\%$ baseline).

### Action Steps
1. Navigate to `/intelligence` -> Tab 21: **FinOps & Cost Intelligence**.
2. Locate the flagged anomaly in the **Cost Anomaly Surveillance** panel.
3. Review the `evidence_hash`, `affected_service`, and `deviation_pct`.
4. Check whether the cost increase correlates with a proportional surge in processed transaction volume via the **Unit Economics Radar**.
   - If transaction volume surged proportionally: Mark as legitimate business scale. Acknowledge the incident.
   - If transaction volume remained flat (CTDR $> 2.5$): Identify potential runaway loop or un-cached downstream query pattern.
5. Escalate to the service owner via `/api/recovery/intelligence/finops/incidents/{id}/escalate`.
6. Apply advisory optimization or rollout hotfix if verified.

---

## SOP-FIN-02: Monthly Budget Exhaustion Response

### Trigger Condition
Budget burn rate crosses 95% threshold with $> 5$ days remaining in the billing period.

### Action Steps
1. Review the **Budget Surveillance & Governance** panel to identify primary over-spending categories (e.g., `ML_INFERENCE` vs `DATABASE`).
2. Evaluate pending **Advisory Optimization Recommendations**.
3. Identify candidate idle resources in the **Resource Waste & Optimization Opportunities** panel.
4. Obtain Administrator cryptographic approval for non-breaking rightsizing or cache-warming optimizations.
5. If necessary, submit a governed budget revision via `/api/recovery/intelligence/finops/budgets/configure` with VP Engineering approval.

---

## SOP-FIN-03: Signed FinOps Report Verification

### Verification Steps
1. Request signed report via `/api/recovery/intelligence/finops/report`.
2. Extract the `verification_signature` HMAC digest from the response payload.
3. Validate signature locally using the FinOps HMAC-SHA256 verification key.
4. Confirm `financial_isolation_verified == True` and zero modifications to `RecoveryAction` or `Payment` records.
