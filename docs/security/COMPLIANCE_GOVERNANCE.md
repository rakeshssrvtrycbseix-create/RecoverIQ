# RecoverIQ — Fintech Compliance, Audit Intelligence & Regulatory Governance (Phase 10B)

## 1. Executive Summary & Legal Disclaimer

> [!IMPORTANT]
> **Engineering Control Evidence Notice:**
> The RecoverIQ Compliance & Governance layer provides automated, deterministic software engineering control evidence and audit trail reconstruction. It evaluates technical control alignment across 5 categories and does **NOT** constitute legal, regulatory, or formal accredited third-party certification (e.g., RBI, PCI DSS, SOC 2, ISO 27001, GDPR).

### Non-Negotiable Invariants
1. **PolicyEngine Supremacy:** The `PolicyEngine` remains the sole authoritative gatekeeper for all financial recovery actions.
2. **Zero Financial Mutations ($\Delta \text{Mutations} = 0$):** Compliance evaluation is strictly observational and reconstructed from immutable event sourcing. Calling compliance endpoints executes zero database inserts/updates to `RecoveryAction`, `Payment`, or `RecoveryCase` financial balances.
3. **Zero Direct Gateway Invocations:** The compliance subsystem never directly interacts with external payment gateways (e.g., Razorpay) or dispatches worker tasks.
4. **Deterministic Evaluation:** Identical database states always yield identical compliance risk scores (0–100) and posture classifications without timestamp drift or random variations.

---

## 2. Engineering Control Matrix (18 Deterministic Controls)

RecoverIQ evaluates 18 continuous engineering controls across 5 weighted governance categories:

| Control ID | Category | Name | Description | Default Status | Severity |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **SEC-AUTH-01** | `SECURITY` | Authoritative Cryptographic JWT Verification | HMAC-SHA256 signature verification with algorithm pinning and expiration enforcement. | `PASS` | `CRITICAL` |
| **SEC-RBAC-01** | `SECURITY` | 3-Tier Centralized RBAC Hierarchy | Role boundary enforcement (`viewer` < `operator` < `admin`) on sensitive mutations. | `PASS` | `HIGH` |
| **SEC-RATE-01** | `SECURITY` | Sliding-Window Distributed Rate Limiting | Rate limiting on read and mutation endpoints preventing DoS and brute-force abuse. | `PASS` | `MEDIUM` |
| **SEC-THREAT-01** | `SECURITY` | Multi-Vector Threat Intelligence Surveillance | Tripwires detecting SQL injection, XSS, rate-limit threshold breaches, and token replay. | `PASS` | `HIGH` |
| **SEC-REVOKE-01** | `SECURITY` | Cryptographic Token Revocation & Blacklisting | Instant in-memory and database revocation tripwire for compromised JWT JTIs. | `PASS` | `HIGH` |
| **SEC-WEBHOOK-01** | `SECURITY` | Constant-Time Webhook Signature Verification | Webhook integrity verification using `hmac.compare_digest` with replay tripwires. | `PASS` | `CRITICAL` |
| **SEC-PII-01** | `SECURITY` | Deep Zero-PII & Raw Secret Redaction | Automatic sanitization preventing plaintext PANs, CVVs, passwords, and API keys. | `PASS` | `CRITICAL` |
| **FIN-POL-01** | `FINANCIAL_CONTROL` | PolicyEngine Supremacy Verification | Invariant that 100% of executed recovery actions originate from an explicit PolicyDecision. | `PASS` | `CRITICAL` |
| **FIN-MUT-01** | `FINANCIAL_CONTROL` | Zero Unauthorized Financial Mutations | Strict verification that observational endpoints create zero financial delta. | `PASS` | `CRITICAL` |
| **FIN-GATE-01** | `FINANCIAL_CONTROL` | Zero Direct Payment Gateway Calls | Observational subsystems isolated from payment providers with zero provider calls. | `PASS` | `CRITICAL` |
| **FIN-AUD-01** | `FINANCIAL_CONTROL` | Complete Financial Lifecycle Provenance | 6-stage lifecycle traceability from case inception to payment reconciliation. | `PASS` | `HIGH` |
| **ML-GATE-01** | `ML_GOVERNANCE` | 14-Gate Continuous Learning Safety Gates | Offline dataset lineage, statistical sanity checks, and drift thresholds before canary. | `PASS` | `HIGH` |
| **ML-DEP-01** | `ML_GOVERNANCE` | Governed Challenger Deployment Gates | Shadow analysis and canary allocation gating before full production champion promotion. | `PASS` | `HIGH` |
| **ML-PROD-01** | `ML_GOVERNANCE` | Production Telemetry & Drift Monitoring | Continuous tracking of recovery rate, MTTR, KS-drift, and PSI distribution shifts. | `PASS` | `MEDIUM` |
| **DAT-SCAN-01** | `DATA_GOVERNANCE` | Continuous PII & Secrets Surveillance | PII scanner surveillance verifying zero unmasked Aadhaar, cards, or raw tokens. | `PASS` | `CRITICAL` |
| **DAT-MASK-01** | `DATA_GOVERNANCE` | Persistent Customer Contact Masking | Verification that database customers store only masked emails and phone numbers. | `PASS` | `HIGH` |
| **HUM-REV-01** | `HUMAN_GOVERNANCE` | Low-Confidence Human Review Routing | PolicyEngine rule enforcing human operator review when AI confidence < floor. | `PASS` | `MEDIUM` |
| **HUM-AUD-01** | `HUMAN_GOVERNANCE` | Immutable Operator Identity Attribution | Verified JWT operator identity recorded in AuditLog for manual actions. | `PASS` | `HIGH` |

---

## 3. Compliance Risk Scoring (0–100) & Posture Mapping

### Category Weighting
$$\text{Overall Score} = \sum_{c \in \text{Categories}} \left( \text{Category Score}_c \times \frac{\text{Weight}_c}{100} \right)$$

* **Security Controls (`SECURITY`):** 30% Weight
* **Financial Controls (`FINANCIAL_CONTROL`):** 30% Weight
* **ML & Strategy Governance (`ML_GOVERNANCE`):** 15% Weight
* **Data Protection & Privacy (`DATA_GOVERNANCE`):** 15% Weight
* **Human-in-the-Loop Governance (`HUMAN_GOVERNANCE`):** 10% Weight

### Posture Thresholds
* **`EXCELLENT`:** $\text{Score} \ge 90.0$
* **`GOOD`:** $75.0 \le \text{Score} < 90.0$
* **`WARNING`:** $60.0 \le \text{Score} < 75.0$
* **`HIGH_RISK`:** $40.0 \le \text{Score} < 60.0$
* **`CRITICAL`:** $\text{Score} < 40.0$

---

## 4. Immutable AuditLog Completeness Engine

RecoverIQ monitors 10 mandatory lifecycle event categories across the immutable `AuditLog` event-store:
1. `AUTHENTICATION`
2. `AUTHORIZATION`
3. `PAYMENT_INGESTION`
4. `RECOVERY_LIFECYCLE`
5. `POLICY_GOVERNANCE`
6. `ACTION_EXECUTION`
7. `ACTION_RESULT`
8. `MODEL_LIFECYCLE`
9. `STRATEGY_GOVERNANCE`
10. `SECURITY_THREAT`

### Decision Trace Compliance (6-Stage Provenance)
$$\text{RecoveryCase} \longrightarrow \text{MLPrediction} \longrightarrow \text{AgentDecision} \longrightarrow \text{PolicyDecision} \longrightarrow \text{RecoveryAction} \longrightarrow \text{ActionResult}$$

All traces sample resolved cases and ensure zero orphaned records, unlinked actions, or PII exposures.

---

## 5. REST API Endpoint Reference

All endpoints are mounted under `/api/recovery/intelligence/compliance` and require `require_viewer` (Viewer, Operator, Admin):

1. `GET /api/recovery/intelligence/compliance`
   - Returns high-level compliance summary, category scores, posture, and subsystem audits.
2. `GET /api/recovery/intelligence/compliance/controls`
   - Returns the full 18-control matrix with optional filtering by `category`, `status`, and `severity`.
3. `GET /api/recovery/intelligence/compliance/incidents`
   - Returns compliance findings and security incidents with optional filtering by `severity`, `category`, and `status`.
4. `GET /api/recovery/intelligence/compliance/audit-coverage`
   - Returns AuditLog completeness metrics, observed event categories, and missing categories.
5. `GET /api/recovery/intelligence/compliance/report`
   - Generates an exportable JSON compliance snapshot with executive summary and structured remediation roadmap.

---

## 6. Verification & Automated Test Suite

The compliance layer is validated by 14 dedicated automated tests in `backend/tests/test_compliance_governance.py`:
- Deterministic compliance score and posture calculation
- 18 engineering controls evaluation and category/status filtering
- AuditLog 10-category lifecycle completeness and gap detection
- 6-stage lifecycle decision trace validation
- PolicyEngine supremacy and financial governance integrity
- RBAC escalation detection and authoritative identity validation
- ML model lineage and safety gate governance
- Deep PII and credential leakage scanner validation
- Deterministic incident generation and severity classification
- RBAC endpoint protection across unauthenticated and authorized roles
- **Mandatory Financial Isolation Guarantee** ($\Delta \text{RecoveryAction} = 0, \Delta \text{Payment} = 0, \Delta \text{RecoveryCase} = 0, \text{Dispatcher Calls} = 0, \text{Gateway Calls} = 0$).
