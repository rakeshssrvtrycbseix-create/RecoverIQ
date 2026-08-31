# Phase 10H — Advanced Threat Intelligence & Anomaly Scoring Specification

## Overview

RecoverIQ **Phase 10H Threat Intelligence Engine** provides continuous, real-time security signal ingestion, statistical behavioral anomaly radar scoring, automated indicator categorization, and multi-vector risk correlation across all platform components.

---

## Behavioral Threat Radar & Statistical Anomaly Math

The platform evaluates a statistical threat score normalized to $[0.0, 100.0]$:

$$\text{Threat Score} = \min\left(100.0, \, \frac{w_1 A_{\text{auth}} + w_2 A_{\text{freq}} + w_3 A_{\text{priv}} + w_4 A_{\text{svc}} + w_5 A_{\text{cfg}} + w_6 A_{\text{runt}}}{1.0}\right)$$

Where:
- $A_{\text{auth}}$ = Authentication anomaly rate (failed login spikes, IP geolocation anomalies)
- $A_{\text{freq}}$ = Request frequency anomaly rate (burst rate breaches, Token Bucket exhaustion)
- $A_{\text{priv}}$ = Privilege escalation anomaly rate (unauthorized scope requests)
- $A_{\text{svc}}$ = Inter-service call anomaly rate (communication outside Least-Privilege matrix)
- $A_{\text{cfg}}$ = Configuration change anomaly rate (unregistered environment variable mutations)
- $A_{\text{runt}}$ = Container runtime anomaly rate (unauthorized process execution attempts)

### Threat Score Classification Bands

| Score Range | Classification | Action Recommendation | Financial Impact |
| :--- | :--- | :--- | :---: |
| $[0.0, 10.0)$ | `NOMINAL` | `MONITOR` (Standard telemetry logging) | ₹0.00 |
| $[10.0, 25.0)$ | `LOW` | `INVESTIGATE` (Informational alert log entry) | ₹0.00 |
| $[25.0, 50.0)$ | `ELEVATED` | `ESCALATE` (Operator review flag) | ₹0.00 |
| $[50.0, 75.0)$ | `HIGH` | `ISOLATE_RECOMMENDED` (Recommend microservice sandbox isolation) | ₹0.00 |
| $[75.0, 100.0]$ | `CRITICAL` | `CREDENTIAL_ROTATION_RECOMMENDED` / `HUMAN_REVIEW_REQUIRED` | ₹0.00 |

---

## Threat Indicator Categories & Schema

All threat indicators ingested into the system are assigned an immutable fingerprint and cataloged under standard security taxonomy:

1. **`AUTHENTICATION`**: IP bursts, credential stuffing, brute-force patterns, invalid JWT signatures.
2. **`AUTHORIZATION`**: Cross-service RBAC matrix bypass attempts, unauthorized scope requests.
3. **`RUNTIME_ANOMALY`**: Ephemeral container rootfs write attempts, unexpected process forks.
4. **`NETWORK_ANOMALY`**: eBPF microsegmentation policy breaches, unexpected outbound connections.
5. **`FINANCIAL_MUTATION_ATTEMPT`**: Unauthorized direct calls targeting ActionDispatcher or Razorpay endpoints. **(Always 100% blocked)**.
6. **`SECRET_EXPOSURE`**: Unmasked PAN, CVV, Aadhaar, JWT secrets, or API keys in request payloads.

---

## Threat Indicator Life Cycle & Audit Provenance

Every threat indicator event is persisted into `AuditLog` under `entity_type="threat_indicator"`:

```json
{
  "entity_id": "IND-8F9A2B3C",
  "entity_type": "threat_indicator",
  "action": "THREAT_INDICATOR_DETECTED",
  "actor_id": "system:zero_trust_scanner",
  "payload": {
    "indicator_id": "IND-8F9A2B3C",
    "fingerprint": "a1b2c3d4e5f6...",
    "category": "FINANCIAL_MUTATION_ATTEMPT",
    "severity": "HIGH",
    "confidence_score": 0.99,
    "target_endpoint": "/api/recovery/intelligence/zero-trust",
    "financial_impact_inr": 0.00
  }
}
```
