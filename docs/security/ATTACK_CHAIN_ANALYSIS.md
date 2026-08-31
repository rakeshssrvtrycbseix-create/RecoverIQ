# Phase 10H — Automated Attack Chain Correlation & Blast Radius Containment

## Overview

RecoverIQ **Phase 10H Attack Chain Engine** continuously correlates disparate threat indicators into multi-stage attack graphs, performs automated blast-radius containment analysis, and verifies $100\%$ financial isolation across all detected attack paths.

---

## Attack Graph Stages & Correlation Rules

Threat events are linked using temporal and identity correlation heuristics into 5 formal attack chain stages:

```
[ RECONNAISSANCE ] ──► [ INITIAL_ACCESS ] ──► [ LATERAL_MOVEMENT_ATTEMPT ] ──► [ PRIVILEGE_ESCALATION_ATTEMPT ] ──► [ FINANCIAL_MUTATION_ATTEMPT_BLOCKED ]
```

### Stage Definitions

1. `RECONNAISSANCE`: Endpoint scanning, rate-limit probe bursts, abnormal request header parameters.
2. `INITIAL_ACCESS`: Invalid JWT token usage, expired SVID attempts, failed MFA step-up attempts.
3. `LATERAL_MOVEMENT_ATTEMPT`: Unauthorized inter-service call attempts outside defined RBAC authorization matrix.
4. `PRIVILEGE_ESCALATION_ATTEMPT`: Attempting to call Admin scope endpoints with Viewer/Operator tokens.
5. `FINANCIAL_MUTATION_ATTEMPT_BLOCKED`: Attempting to bypass PolicyEngine to invoke ActionDispatcher or Razorpay endpoints directly. **(Always 100% CONTAINED & BLOCKED)**.

---

## Blast Radius Analysis & Financial Containment

For every active attack chain, the system calculates a **Blast Radius Score** $[0.0, 100.0]$ representing potential infrastructure surface area affected:

$$\text{Blast Radius Score} = \frac{|\text{Affected Services}|}{\text{Total Services (11)}} \times 100.0$$

### Financial Isolation Guarantee

> **Strict Isolation Invariant:**
> Regardless of the Blast Radius Score or Attack Chain Stage, financial ledger mutation is **mathematically zero**:
> $$\text{Financial Mutation Count} = 0, \quad \text{Financial Impact INR} = \text{₹0.00}$$
> PolicyEngine remains unaffected as the sole authoritative gatekeeper.

---

## Sample Attack Chain Structure

```json
{
  "chain_id": "CHAIN-98F10A2C",
  "title": "Simulated Multi-Stage Lateral Movement & Financial Mutation Probe",
  "severity": "HIGH",
  "confidence_score": 0.99,
  "first_seen": "2026-08-30T10:15:00Z",
  "last_seen": "2026-08-30T10:18:30Z",
  "stages": [
    {
      "stage": "RECONNAISSANCE",
      "timestamp": "2026-08-30T10:15:00Z",
      "component": "API Gateway",
      "summary": "IP burst scan detected on public endpoints",
      "evidence_hash": "0x7a8b9c..."
    },
    {
      "stage": "LATERAL_MOVEMENT_ATTEMPT",
      "timestamp": "2026-08-30T10:16:30Z",
      "component": "ZeroTrustSecurityService",
      "summary": "Unauthorized inter-service request to PolicyEngine scope",
      "evidence_hash": "0x1c2d3e..."
    },
    {
      "stage": "FINANCIAL_MUTATION_ATTEMPT_BLOCKED",
      "timestamp": "2026-08-30T10:18:30Z",
      "component": "ActionDispatcher",
      "summary": "Direct recovery action trigger attempt blocked with 0 financial impact",
      "evidence_hash": "0x9f8e7d..."
    }
  ],
  "affected_services": ["API Gateway", "PolicyEngine", "ActionDispatcher"],
  "blast_radius_score": 27.27,
  "recommended_action": "ISOLATE_RECOMMENDED",
  "human_review_required": true,
  "financial_isolation_verified": true
}
```
