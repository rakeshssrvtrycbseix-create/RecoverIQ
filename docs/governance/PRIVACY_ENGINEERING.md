# RecoverIQ — Privacy Engineering & Pseudonymization Framework (Phase 10E)

## 1. Overview & Objectives

The **Privacy Engineering Framework** guarantees zero-leakage, zero-plain-text storage of Personally Identifiable Information (PII) and payment cardholder data across all system surfaces in RecoverIQ.

---

## 2. Core Privacy Engineering Capabilities

### 2.1 Deterministic HMAC-SHA256 Pseudonymization
To allow correlation of recovery events and ML features across services without exposing actual customer identifiers, the system uses a secret-salted, HMAC-SHA256 deterministic tokenization algorithm:

$$\text{Pseudonym} = \text{"sub\_pseudo\_"} + \text{HMAC-SHA256}(\text{Key}, \text{SubjectID})[0:12]$$

- **Properties:**
  - One-way cryptographic transformation.
  - Deterministic: The same subject yields the same pseudonym across datasets without exposing the raw identifier.
  - Salted: Secret key rotates safely with cryptographic environment boundaries.

### 2.2 Dynamic Masking & Sanitization
All logs, traces, exception dumps, and API responses pass through dynamic masking sanitizers:
- **Email:** `j***e@domain.com` (first and last char before `@` preserved).
- **Phone:** `+91 ••••• ••123` (country prefix and last 3 digits).
- **Card:** `•••• •••• •••• 4242` (only last 4 digits visible).
- **Aadhaar:** `•••• •••• 9876` (last 4 digits).
- **PAN:** `ABC•• •••1D` (first 3 letters and last letter).
- **Secrets & API Keys:** Completely suppressed (`[REDACTED_SECRET]`).

### 2.3 Interactive & Automated PII Discovery Scanner
The platform includes an automated PII discovery scanner checking arbitrary data payloads against 8 hardened regular expressions:
1. `EMAIL`: RFC 5322 compliant regex with bounded length.
2. `PHONE_E164`: Standard E.164 and 10-digit Indian mobile patterns.
3. `INDIAN_PAN`: Indian Income Tax Permanent Account Number (`[A-Z]{5}[0-9]{4}[A-Z]`).
4. `INDIAN_AADHAAR`: 12-digit UIDAI format with Verhoeff structure checks.
5. `CREDIT_CARD`: Major card prefixes (Visa 4, Mastercard 5, Amex 37) with Luhn validation.
6. `JWT_TOKEN`: Base64URL header/payload/signature format (`ey[A-Za-z0-9-_=]+\.ey...`).
7. `RAZORPAY_KEY`: Razorpay Key ID (`rzp_test_...` / `rzp_live_...`).
8. `GENERIC_SECRET`: Generic high-entropy secret patterns (`sk_live_...`, `sec_...`).

---

## 3. Subject Rights & Privacy Request Workflow

Under DPDP Act 2023 and GDPR/CCPA parity, subjects can submit rights requests:

```
┌──────────────┐     POST /requests      ┌──────────────┐
│  Subject /   │ ──────────────────────► │   RECEIVED   │
│  Client App  │                         │ (Pseudonym)  │
└──────────────┘                         └──────┬───────┘
                                                │
                                                ▼ POST /requests/{id}/review
                                         ┌──────────────┐
                                         │ UNDER_REVIEW │
                                         │ (Operator)   │
                                         └──────┬───────┘
                                                │
                        ┌───────────────────────┴───────────────────────┐
                        ▼ Decision: APPROVE                             ▼ Decision: REJECT
                 ┌──────────────┐                                ┌──────────────┐
                 │   APPROVED   │                                │   REJECTED   │
                 └──────┬───────┘                                └──────────────┘
                        │
                        ▼ POST /requests/{id}/complete
                 ┌──────────────┐
                 │  COMPLETED   │
                 │ (Audit Log)  │
                 └──────────────┘
```

- **Request Types:**
  - `ACCESS`: Retrieve recovery history and processing metadata.
  - `EXPORT`: Generate portable JSON export package.
  - `RECTIFICATION`: Correct outdated or erroneous customer metadata.
  - `ERASURE`: Non-mutating statutory erasure evaluation.
  - `RESTRICTION`: Restrict specific recovery channels (e.g., disable WhatsApp, allow SMS).
  - `PROCESSING_PURPOSE`: Provide purpose justification for data retention.

---

## 4. Zero Financial Impact Guarantee

Subject privacy requests are purely administrative and observational. They do not alter transaction ledgers, settle payments, cancel pending bank debits, or delete statutory financial audits.
