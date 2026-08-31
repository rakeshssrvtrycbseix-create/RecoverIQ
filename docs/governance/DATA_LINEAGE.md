# RecoverIQ — Data Lineage & Cryptographic Provenance Architecture (Phase 10E)

## 1. Lineage Architecture Overview

The **RecoverIQ Data Lineage Engine** maps and cryptographically verifies every stage of the payment recovery lifecycle—from webhook ingestion to ML inference, PolicyEngine evaluation, action dispatch, and audit logging.

---

## 2. End-to-End Pipeline Lineage Graph

```
┌────────────────────────────────┐
│   Node 1: Payment Webhook      │  Type: SOURCE (External Gateway)
│   (Razorpay payment.failed)    │  Schema: v1.0 • SHA-256 Checksum
└───────────────┬────────────────┘
                │ Edge 1: HMAC Verification & Field Sanitization
                ▼
┌────────────────────────────────┐
│   Node 2: Raw Ingestion Event  │  Type: INGESTION (Ingestion Queue)
│   (PaymentIngestEvent)         │  Schema: v2.1 • SHA-256 Checksum
└───────────────┬────────────────┘
                │ Edge 2: Recovery Case Initialization & State Machine
                ▼
┌────────────────────────────────┐
│   Node 3: Case Lifecycle       │  Type: TRANSFORMATION (Core Engine)
│   (RecoveryCase entity)        │  Schema: v3.0 • SHA-256 Checksum
└───────────────┬────────────────┘
                │ Edge 3: Feature Engineering & Context Assembly
                ▼
┌────────────────────────────────┐
│   Node 4: ML Inference Engine  │  Type: MODEL (Feature Store)
│   (MLPrediction / Score)       │  Schema: v1.4 • SHA-256 Checksum
└───────────────┬────────────────┘
                │ Edge 4: Authoritative Policy Guardrails Evaluation
                ▼
┌────────────────────────────────┐
│   Node 5: PolicyEngine Gate    │  Type: DECISION (Sole Financial Authority)
│   (PolicyDecision record)      │  Schema: v2.0 • SHA-256 Checksum
└───────────────┬────────────────┘
                │ Edge 5: Worker Task Queue Routing
                ▼
┌────────────────────────────────┐
│   Node 6: Action Dispatcher    │  Type: OUTPUT (Provider Execution)
│   (RecoveryAction queue)       │  Schema: v2.0 • SHA-256 Checksum
└───────────────┬────────────────┘
                │ Edge 6: Immutable Event Sourcing Append
                ▼
┌────────────────────────────────┐
│   Node 7: AuditLog Ledger      │  Type: AUDIT (Immutable Compliance Store)
│   (AuditLog entity)            │  Schema: v1.0 • SHA-256 Checksum
└────────────────────────────────┘
```

---

## 3. Cryptographic Checksum Engine

Each node in the lineage graph computes a canonical SHA-256 digest of its state and schema:

$$\text{Checksum} = \text{SHA-256}(\text{NodeID} + \text{Domain} + \text{SchemaVersion} + \text{Timestamp} + \text{Salt})$$

- **100% Lineage Coverage:** All 7 pipeline stages are mapped with 6 verified transformation edges.
- **Tamper Evidence:** Any unauthorized schema drift or mutation breaks the forward hash chain.
- **Traceability:** Operators can inspect the full provenance path for any recovery decision in the dashboard.
