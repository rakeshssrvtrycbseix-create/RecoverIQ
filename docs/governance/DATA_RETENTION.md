# RecoverIQ — Data Retention & Advisory Deletion Framework (Phase 10E)

## 1. Statutory Retention Overview

The **RecoverIQ Retention Engine** enforces statutory, regulatory, and business data aging schedules across all data assets without mutating or deleting active financial records.

---

## 2. Retention Schedules by Domain

| Domain | Retention Schedule | Statutory / Business Justification | Legal Hold Status | Deletion Eligibility |
| :--- | :--- | :--- | :--- | :--- |
| **Payment (`Payment`)** | 2,555 days (7 Years) | RBI Master Directions & Indian Income Tax Act Sec 44AA | Statutory Hold | Blocked |
| **Recovery (`RecoveryCase`)** | 1,825 days (5 Years) | Recovery business lifecycle analysis & contract limitation | Active Case Hold | Blocked |
| **ML (`MLPrediction`)** | 1,095 days (3 Years) | Model governance, fairness audits, drift retraining | Model Retraining | Eligible after 3Y |
| **Audit (`AuditLog`)** | 2,555 days (7 Years) | Immutable forensic audit trails & regulatory inquiries | **PERMANENT LEGAL HOLD** | **STRICTLY PROHIBITED** |
| **Observability (`Telemetry`)** | 90 days | SRE latency analysis & incident diagnostics | Rolling Window | Eligible after 90D |

---

## 3. Advisory Subject Erasure Eligibility Evaluator

When a customer submits a "Right to Erasure" request under the DPDP Act or GDPR:

1. **Non-Mutating Evaluation:** The system computes whether any statutory obligations require retaining the customer's records.
2. **Blocker Analysis:**
   - If the subject has associated `Payment` records within the 7-year statutory window, erasure is **BLOCKED**.
   - If the subject is referenced in immutable `AuditLog` events, the audit log entries remain **FROZEN under Legal Hold**.
3. **Advisory Compliance Output:** The evaluator returns a structured JSON evaluation describing exact statutory blockers:
   ```json
   {
     "subject_pseudonym": "sub_pseudo_a1b2c3d4e5f6",
     "eligible_for_erasure": false,
     "legal_hold_active": true,
     "financial_record_retention_required": true,
     "audit_retention_required": true,
     "blocker_reasons": [
       "Subject has active financial transaction records subject to RBI 7-year statutory retention (RBI Master Direction on Payment Aggregators).",
       "AuditLog entries associated with subject are protected by immutable legal hold policy."
     ],
     "advisory_notice": "Advisory evaluation only. No database records were modified or deleted."
   }
   ```
4. **Zero Financial Mutation:** The evaluation never drops tables, deletes rows, or cancels transactions.
