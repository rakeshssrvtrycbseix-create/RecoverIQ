# Advisory Resource Optimization Governance

## Non-Negotiable Human-in-the-Loop Invariant

> **Strict Governance Mandate:**
> All FinOps resource optimization recommendations are **strictly advisory**. The FinOps subsystem is cryptographically and architecturally prevented from automatically mutating infrastructure, resizing databases, shutting down nodes, or altering financial ledger states.
>
> Every optimization requires explicit review and cryptographic authorization by an **authenticated Administrator** via the `/api/recovery/intelligence/finops/optimizations/{id}/approve` endpoint.

---

## Optimization Taxonomy

| Optimization Type | Description | Target Resource | Estimated Monthly Savings | Implementation Risk |
| :--- | :--- | :--- | :---: | :---: |
| `RIGHTSIZING_ADVISORY` | Downscale over-provisioned worker pods | API Gateway Pods | ₹4,500 – ₹12,000 | `LOW` |
| `IDLE_SHUTDOWN_ADVISORY` | Terminate unutilized dev/staging databases | Staging Aurora DB | ₹8,000 – ₹18,000 | `LOW` |
| `STORAGE_TIERING_ADVISORY` | Migrate $>90\text{d}$ AuditLogs to S3 Glacier Deep Archive | AuditLog S3 Bucket | ₹3,200 – ₹7,500 | `LOW` |
| `RESERVED_INSTANCE_ADVISORY` | Purchase 1-year Savings Plans for baseline compute | Core Worker Pool | ₹15,000 – ₹35,000 | `MEDIUM` |
| `ML_MODEL_QUANTIZATION_ADVISORY` | Quantize XGBoost inference trees to FP16/INT8 | ML Inference Pods | ₹6,000 – ₹14,000 | `MEDIUM` |

---

## Mandatory Rollback Runbook Invariant

Every optimization recommendation must include:
1. **Target Resource Identifier**: Exact ARN / container deployment name.
2. **Impact Assessment**: Explicit verification of zero degradation to SLA, recovery rate, or security posture.
3. **Deterministic Rollback Plan**: Step-by-step Terraform / Kubernetes rollback command sequence executable within 60 seconds if regressions occur.
