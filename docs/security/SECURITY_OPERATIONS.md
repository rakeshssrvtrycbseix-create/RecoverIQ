# Phase 10H — SOC Control Plane & Security Incident Operations Specification

## Overview

RecoverIQ **Phase 10H Security Operations Control Plane (SOC)** provides incident lifecycle management, operator triage tools, zero-PII/secret scanner findings, and 3-tier RBAC step-up verification for security operations center engineers.

---

## Security Incident Life Cycle & State Machine

Security incidents follow a deterministic state machine transitions:

```
[ OPEN ] ──────(Acknowledge)──────► [ ACKNOWLEDGED ] ──────(Escalate)──────► [ ESCALATED ] ──────(Resolve)──────► [ RESOLVED ]
```

### Incident State Descriptions

1. **`OPEN`**: Initial security incident created by threat intelligence or readiness gate failure.
2. **`ACKNOWLEDGED`**: Operator has acknowledged the incident and assigned triage ownership.
3. **`ESCALATED`**: Incident escalated to Tier 3 Security Operations / SRE leads for active mitigation.
4. **`RESOLVED`**: Threat mitigated, isolation verified, zero financial impact confirmed.

---

## 3-Tier Human Operator RBAC & Step-Up Authorization

All SOC control plane endpoints require role-based access control (RBAC):

| User Role | Operations Permitted | Action Scope | Step-up MFA Required? |
| :--- | :--- | :--- | :---: |
| **Viewer (`role:viewer`)** | Read-only inspection of security dashboard, threat scores, readiness gates | `READ_ONLY` | No |
| **Operator (`role:operator`)** | Acknowledge incidents, run threat indicator scans, export signed reports | `OPERATOR_TRIAGE` | Yes (MFA Token) |
| **Admin (`role:admin`)** | Escalate/Resolve security incidents, request credential rotation, trigger emergency lockdown recommendation | `ADMIN_CONTROL` | Yes (WebAuthn Step-up) |

---

## Zero-PII & Secret Scanner Operational Rules

Real-time redaction scanners scrub all incoming telemetry, logs, and API payloads prior to persistence:

- **PAN / Credit Cards**: Regex pattern matching 13-19 digit card numbers $\to$ `[REDACTED_PAN]`.
- **CVV**: 3-4 digit verification codes $\to$ `[REDACTED_CVV]`.
- **Aadhaar Numbers**: 12-digit Indian national ID numbers $\to$ `[REDACTED_AADHAAR]`.
- **JWT Secret Keys**: Any `bearer`, `secret`, or `private_key` tokens $\to$ `[REDACTED_JWT_SECRET]`.
- **Razorpay Keys**: `rzp_live_*` or `rzp_test_*` credentials $\to$ `[REDACTED_RAZORPAY_KEY]`.
