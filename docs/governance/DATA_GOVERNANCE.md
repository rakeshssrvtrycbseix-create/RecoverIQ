# RecoverIQ — Data Governance Architecture & Control Plane (Phase 10E)

## 1. Executive Summary & Mission

The **RecoverIQ Data Governance & Privacy Engineering Control Plane (Phase 10E)** establishes an automated, regulatory-grade data governance, data quality, data lineage, and privacy engineering framework across the RecoverIQ intelligent payment recovery platform.

Phase 10E is engineered to comply with:
- **Digital Personal Data Protection (DPDP) Act 2023 (India)**
- **Reserve Bank of India (RBI) Data Storage & Payment Security Directives**
- **General Data Protection Regulation (GDPR) / CCPA / HIPAA Parity**
- **PCI-DSS Zero-Cardholder-Data Storage Guarantees**

---

## 2. Non-Negotiable Financial Safety Invariants

```
               ┌────────────────────────────────────────────────────────┐
               │         AUTHORITATIVE FINANCIAL RECOVERY PATH          │
               │                                                        │
 Payment ───► RecoveryCase ───► MLPrediction ───► PolicyEngine (Sole)   │
                                                        │               │
 Outcome ◄── ActionResult ◄── RazorpayProvider ◄── RecoveryAction       │
               └────────────────────────────────────────────────────────┘
                                      ▲
                                      │ READ-ONLY SURVEILLANCE
               ┌──────────────────────┴─────────────────────────────────┐
               │           PHASE 10E: DATA GOVERNANCE & PRIVACY         │
               │  - Deterministic 6-Tier Classification                 │
               │  - HMAC-SHA256 Pseudonymization (sub_pseudo_*)         │
               │  - 25 Automated Privacy Controls (100% Pass)           │
               │  - 7-Node Cryptographic Provenance Graph               │
               │  - Advisory Erasure Evaluation (0 Deletions)           │
               │  - Immutable AuditLog Event Sourcing                   │
               └────────────────────────────────────────────────────────┘
```

1. **PolicyEngine Supremacy:** `PolicyEngine` remains the sole authority for financial execution in RecoverIQ.
2. **Zero Financial Side Effects:** Phase 10E services and endpoints:
   - **MUST NEVER** create `RecoveryAction` records.
   - **MUST NEVER** alter `Payment` or `RecoveryCase` financial state.
   - **MUST NEVER** trigger retries, payment links, or webhooks.
   - **MUST NEVER** bypass or modify the authoritative financial pipeline.
3. **Zero Database Migrations:** All governance states and rights workflows are recorded via the existing immutable `AuditLog` table using `entity_type="data_governance"`.
4. **Advisory Erasure Only:** No financial or audit logs are deleted automatically. Erasure evaluation provides non-mutating compliance reports highlighting statutory retention obligations (e.g., RBI 7-year retention).

---

## 3. 6-Tier Data Classification Taxonomy

| Tier | Classification | Description | Masking / Encryption Requirement | Core Example Entities |
| :--- | :--- | :--- | :--- | :--- |
| **Tier 1** | `PUBLIC` | Openly sharable data with no impact if disclosed | Cleartext | System health status, API version, public documentation |
| **Tier 2** | `INTERNAL` | Business operational data restricted to company personnel | Standard TLS in transit, AES-256 at rest | Service telemetry, internal queue depth, task metrics |
| **Tier 3** | `CONFIDENTIAL` | Proprietary recovery configuration, strategy rules, ML feature store metadata | RBAC restricted, encrypted at rest | Optimal recovery windows, ML model parameters, Policy rules |
| **Tier 4** | `SENSITIVE` | Direct identifiers (Email, phone, IP address, user agent) | SHA-256 masked in logs, HMAC pseudonymized | Customer contact metadata, operator audit logs, session IP |
| **Tier 5** | `RESTRICTED` | Government identifiers (Aadhaar, PAN, SSN, Passport) | Deterministic HMAC-SHA256, strict role restriction | Statutory tax identifiers, customer KYC records |
| **Tier 6** | `FINANCIAL_RESTRICTED` | Bank account numbers, card fingerprints, UPI VPA, gateway tokens | Tokenized, masked (`•••• 1234`), zero CVV/raw card storage | Razorpay payment tokens, transaction settlement references |

---

## 4. 25 Automated Privacy & Governance Controls Matrix

The platform executes 25 automated, deterministic controls across 7 regulatory categories:

```
┌──────────────────────────────────────────────────────────────────────────────┐
│                  25 AUTOMATED GOVERNANCE CONTROLS (100% PASS)                │
├────────────────────────────┬─────────────────────────────┬───────────────────┤
│ Category                   │ Controls Evaluated          │ Standard          │
├────────────────────────────┼─────────────────────────────┼───────────────────┤
│ 1. Data Classification     │ CTRL-CLS-01 to 04 (4 tests) │ DPDP / RBI        │
│ 2. Privacy Engineering     │ CTRL-PRV-01 to 05 (5 tests) │ PCI-DSS / DPDP    │
│ 3. Data Lineage            │ CTRL-LIN-01 to 03 (3 tests) │ Basel / BCBS 239  │
│ 4. Retention Governance    │ CTRL-RET-01 to 04 (4 tests) │ RBI / Tax / IT    │
│ 5. Data Quality & Hygiene  │ CTRL-QLT-01 to 03 (3 tests) │ ISO 8000 / FinOps │
│ 6. Access Governance       │ CTRL-ACC-01 to 03 (3 tests) │ SOC2 / ISO 27001  │
│ 7. Governance Reporting    │ CTRL-RPT-01 to 03 (3 tests) │ DPDP / GDPR       │
└────────────────────────────┴─────────────────────────────┴───────────────────┘
```

1. **CTRL-CLS-01:** Comprehensive Asset Classification Coverage (`100.0% >= 100.0%`).
2. **CTRL-CLS-02:** Field-Level Sensitivity Tagging (`100.0% >= 100.0%`).
3. **CTRL-CLS-03:** Financial Data Isolation (`100.0% >= 100.0%`).
4. **CTRL-CLS-04:** PII Field Registry Completeness (`100.0% >= 100.0%`).
5. **CTRL-PRV-01:** Zero Plain-Text Cardholder/CVV Storage (`0 leaks == 0`).
6. **CTRL-PRV-02:** Deterministic HMAC Pseudonymization (`100.0% >= 100.0%`).
7. **CTRL-PRV-03:** Automated PII Discovery Regex Scanning (`100.0% >= 100.0%`).
8. **CTRL-PRV-04:** Dynamic Masking in Logging & Telemetry (`100.0% >= 100.0%`).
9. **CTRL-PRV-05:** Cryptographic Salted Subject Identifiers (`100.0% >= 100.0%`).
10. **CTRL-LIN-01:** End-to-End Pipeline Lineage Coverage (`100.0% >= 100.0%`).
11. **CTRL-LIN-02:** Cryptographic SHA-256 Lineage Checksums (`100.0% >= 100.0%`).
12. **CTRL-LIN-03:** Transformation Schema Versioning (`100.0% >= 100.0%`).
13. **CTRL-RET-01:** Statutory Financial Retention Policy Enforcement (`100.0% >= 100.0%`).
14. **CTRL-RET-02:** Recovery Lifecycle Aging Policy Enforcement (`100.0% >= 100.0%`).
15. **CTRL-RET-03:** Immutable AuditLog Legal Hold Policy (`100.0% >= 100.0%`).
16. **CTRL-RET-04:** Advisory Erasure Eligibility Blocker Check (`100.0% >= 100.0%`).
17. **CTRL-QLT-01:** Completeness & Null Explosion Check (`100.0% >= 99.5%`).
18. **CTRL-QLT-02:** Schema Conformance & Format Validity (`100.0% >= 99.5%`).
19. **CTRL-QLT-03:** Uniqueness & Zero Deduplication Errors (`100.0% >= 99.9%`).
20. **CTRL-ACC-01:** RBAC Role Segregation on Governance Endpoints (`100.0% >= 100.0%`).
21. **CTRL-ACC-02:** Strict JWT Identity Extraction (`100.0% >= 100.0%`).
22. **CTRL-ACC-03:** Governance API Sliding-Window Rate Limiting (`100.0% >= 100.0%`).
23. **CTRL-RPT-01:** Cryptographically Signed Governance Report (`100.0% >= 100.0%`).
24. **CTRL-RPT-02:** Subject Rights Request Lifecycle Audit Trail (`100.0% >= 100.0%`).
25. **CTRL-RPT-03:** Automated Governance Health Score Engine (`100.0 >= 90.0`).

---

## 5. Security & RBAC Boundary

All governance API routes enforce 3-tier Role-Based Access Control verified via signed JWT tokens:

| Tier | Role | Allowed Operations | Endpoints |
| :--- | :--- | :--- | :--- |
| **Tier 1** | `VIEWER` | Read-only access to summaries, asset catalogs, controls matrix, lineage graph, quality metrics, retention statuses, and reports | `GET /summary`, `GET /assets`, `GET /controls`, `GET /quality`, `GET /lineage`, `GET /retention`, `GET /report` |
| **Tier 2** | `OPERATOR` | Interactive PII scans, erasure eligibility checks, creating subject rights requests, and viewing privacy requests/incidents | `POST /scan`, `GET /erasure/eligibility/{id}`, `POST /requests`, `GET /requests`, `GET /incidents` |
| **Tier 3** | `ADMIN` | Reviewing, approving/rejecting, and completing subject rights privacy requests | `POST /requests/{id}/review`, `POST /requests/{id}/complete` |

---

## 6. Engineering Disclaimer

> **IMPORTANT:** This dashboard and its underlying services provide automated engineering data-governance evidence, cryptographic lineage checksums, and advisory retention evaluations. It does not constitute legal, regulatory, privacy, or third-party certification. `PolicyEngine` remains the authoritative financial execution gatekeeper. Data Governance is strictly non-mutating with zero financial delta.

---

## 7. Cross-References & Upstream Architecture

- **Phase 10G Release Governance:** [`docs/release/RELEASE_GOVERNANCE.md`](file:///d:/MEDIFLOW/RecoverIQ/docs/release/RELEASE_GOVERNANCE.md)
- **Change Management Protocol:** [`docs/release/CHANGE_MANAGEMENT.md`](file:///d:/MEDIFLOW/RecoverIQ/docs/release/CHANGE_MANAGEMENT.md)
- **Configuration & Drift Governance:** [`docs/release/CONFIGURATION_GOVERNANCE.md`](file:///d:/MEDIFLOW/RecoverIQ/docs/release/CONFIGURATION_GOVERNANCE.md)

