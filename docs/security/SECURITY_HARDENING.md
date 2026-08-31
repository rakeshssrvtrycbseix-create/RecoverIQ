# RecoverIQ Security Hardening & Fintech Trust Specification

## 1. Executive Summary & PolicyEngine Supremacy

RecoverIQ **Phase 10A** introduces enterprise-grade fintech defense-in-depth, cryptographic token verification, multi-signal threat detection, rate limiting, and automated PII/secret redaction.

### Absolute Architectural Invariants:
1. **PolicyEngine Supremacy**: `PolicyEngine` remains the sole authoritative financial gatekeeper.
2. **Mandatory Financial Isolation**:
   - The security subsystem is strictly observational, perimeter-defending, and sanitizing.
   - The security subsystem **NEVER** creates `RecoveryAction` records.
   - The security subsystem **NEVER** mutates `Payment` or `RecoveryCase` financial state.
   - The security subsystem **NEVER** calls `ActionDispatcher` or `RazorpayActionProvider`.
3. **0 Database Migrations**:
   - All security threat audits, login anomalies, and token revocations leverage the append-only `AuditLog` table using `entity_type="security_event"` and `entity_type="revoked_token"`.
4. **Authoritative Identity Extraction**:
   - User identity and privileges are derived **strictly** from verified JWT claims (`sub`, `role`). Client-supplied `actor_id` or `operator_id` in request payloads are strictly ignored.

---

## 2. Seven Active Security Controls Matrix

| Control Name | Operational Status | Enforcement Type | Description & Guarantees |
|---|---|---|---|
| **JWT Cryptographic Hardening** | `ACTIVE` | `CRYPTOGRAPHIC` | Algorithm pinning (`HS256`), mandatory claims (`sub`, `exp`, `iat`, `nbf`), unique `jti`, and instantaneous revocation blacklist. |
| **Centralized RBAC Authorization** | `ACTIVE` | `AUTHORIZATION_GATE` | Strict role hierarchy (`VIEWER` < `OPERATOR` < `ADMIN`) with privilege escalation defense. |
| **Multi-Tier Rate Limiting** | `ACTIVE` | `RATE_LIMITER` | Thread-safe sliding-window limiter defending against brute-force, DoS, and credential stuffing. |
| **Webhook Replay & Signature Tripwire** | `ACTIVE` | `HMAC_SHA256_TIMING_SAFE` | Constant-time HMAC verification over exact raw request body bytes with timestamp tolerance window. |
| **Strict Request Validation & Injection Guard** | `ACTIVE` | `DEEP_INSPECTION` | RFC 4122 UUID validation, SQL/NoSQL/Path traversal scanner, and 1MB request body limit. |
| **Zero-PII & Secret Redaction Engine** | `ACTIVE` | `AUTOMATED_SANITIZER` | Luhn credit/debit card PAN detection, Indian Aadhaar (12-digit) masking, CVV/secret redaction. |
| **Financial Execution Isolation Barrier** | `BYPASS_PREVENTED` | `ARCHITECTURAL_INVARIANT` | Architectural guarantee that security endpoints and audits produce $\Delta \text{Financial Mutations} = 0$. |

---

## 3. Rate Limiting Tiers & Headers

The RecoverIQ sliding-window rate limiter partitions counters by Client IP / Forwarded IP and tier key:

| Tier | Rate Limit | Window | Target Endpoints |
|---|---|---|---|
| **Auth Tier** | 15 req/min | 60 seconds | `/api/auth/token` |
| **Webhook Tier** | 120 req/min | 60 seconds | `/webhooks/razorpay` |
| **Mutation Tier** | 60 req/min | 60 seconds | `/api/recovery/security/revoke-token`, Model & Activation mutations |
| **Read Tier** | 240 req/min | 60 seconds | `/api/recovery/security/trust-center`, `/api/recovery/security/events`, telemetry |

When a rate limit is exceeded, the server returns standard **HTTP 429 Too Many Requests** with standard headers:
- `Retry-After: <seconds_until_oldest_timestamp_expires>`
- `X-RateLimit-Limit: <tier_limit>`
- `X-RateLimit-Remaining: 0`
- `X-RateLimit-Reset: <seconds_until_reset>`

---

## 4. Webhook Hardening & Constant-Time Verification

Razorpay webhook ingestion (`/webhooks/razorpay`) implements a strict 8-step lifecycle:
1. **Rate Limit Gate**: Enforces 120 requests/min per IP.
2. **Header Presence**: Validates `X-Razorpay-Signature` and `X-Razorpay-Event-Id`.
3. **Raw Body Extraction**: Extracts exact immutable bytes before JSON parsing.
4. **Constant-Time Verification**: Uses `hmac.compare_digest(computed, signature)` to eliminate timing side-channels.
5. **Replay Protection**: Rejects events whose `created_at` timestamp exceeds `webhook_timestamp_tolerance_seconds` (configurable in production).
6. **Deterministic Sanitization**: Redacts PII, masks card numbers, and redacts secret keys before database storage.
7. **Idempotent Ingestion**: Uses database unique constraints on `event_id` to prevent duplicate processing.
8. **Sub-5-Second Acknowledgment**: Returns HTTP 200 immediately.

---

## 5. PII & Secret Redaction Engine

The automated scanner deep-scans all incoming/outgoing payloads and logs:
- **Card PANs**: Validates 13–19 digit sequences with the **Luhn Checksum Algorithm** and masks to `XX******XXXX`.
- **Aadhaar Numbers**: Detects 12-digit Indian national identity numbers and masks to `XXXX-XXXX-XXXX`.
- **CVV/CVC & UPI PINs**: Replaces with `[REDACTED_SECRET]`.
- **API Keys & JWT Tokens**: Detects `rzp_live_*`, `rzp_test_*`, and private key headers.
- **Emails & Phones**: Recursively masks user identifiers (`a***e@domain.com`, `+91******3210`).

---

## 6. HTTP Security Headers

`SecurityHeadersMiddleware` injects strict enterprise security headers on all responses:
- `X-Content-Type-Options: nosniff`
- `X-Frame-Options: DENY`
- `X-XSS-Protection: 1; mode=block`
- `Strict-Transport-Security: max-age=31536000; includeSubDomains`
- `Content-Security-Policy: default-src 'self'; frame-ancestors 'none'; object-src 'none'; base-uri 'self';`
- `Referrer-Policy: strict-origin-when-cross-origin`
- `Permissions-Policy: geolocation=(), camera=(), microphone=(), payment=()`

---

## 7. REST API Endpoints

| Endpoint | Method | Required Role | Description |
|---|---|---|---|
| `/api/recovery/security/trust-center` | `GET` | `VIEWER` | Returns Fintech Trust Score (0-100), active control statuses, and threat telemetry. |
| `/api/recovery/security/events` | `GET` | `OPERATOR` | Paginated chronological security audit events filtered by severity/event type. |
| `/api/recovery/security/revoke-token` | `POST` | `ADMIN` | Emergency JTI blacklist tripwire. |
| `/api/recovery/security/scan` | `POST` | `OPERATOR` | On-demand test payload scanner for PII and secret redaction. |

---

## 8. Integration with Phase 10B Compliance & Governance

The Security Hardening and Trust Layer serves as the foundational substrate for **Phase 10B Compliance & Audit Intelligence**. All security controls (`SEC-AUTH-01`, `SEC-RBAC-01`, `SEC-RATE-01`, `SEC-THREAT-01`, `SEC-REVOKE-01`, `SEC-WEBHOOK-01`, `SEC-PII-01`) feed directly into the **18-Control Compliance Matrix** and weighted scoring engine.

For complete compliance control mappings and audit provenance, see [COMPLIANCE_GOVERNANCE.md](file:///d:/MEDIFLOW/RecoverIQ/docs/security/COMPLIANCE_GOVERNANCE.md).

---

## 9. Integration with Phase 10E Data Governance & Privacy Engineering

The Security Hardening and Trust Layer integrates directly with **Phase 10E Data Governance, Privacy Engineering, Data Lineage & Regulatory-Grade Data Controls**:
- **Deterministic HMAC Pseudonymization**: Sanitizes customer identifiers (`sub_pseudo_*`) across all intelligence queries.
- **25 Privacy Controls Matrix**: Enforces field-level sensitivity classification, statutory aging schedules, and zero-PII storage.
- **7-Node Lineage Graph**: Cryptographically traces security events and recovery cases with SHA-256 digests.

For full architectural details, see [DATA_GOVERNANCE.md](file:///d:/MEDIFLOW/RecoverIQ/docs/governance/DATA_GOVERNANCE.md) and [PRIVACY_ENGINEERING.md](file:///d:/MEDIFLOW/RecoverIQ/docs/governance/PRIVACY_ENGINEERING.md).

---

## 10. Integration with Phase 10G Release Governance & Deployment Assurance

The Security Hardening Layer provides cryptographic verification and security gates for **Phase 10G Release Governance**:
- **`GATE-REL-04` Vulnerability Gate:** Enforces 0 Critical/High CVEs and strict token validation before candidate promotion.
- **`GATE-REL-06` Zero-PII Assurance:** Validates zero raw customer identifiers or secret leakage in release metadata.
- **Human Governance Verification:** Enforces authenticated, role-based digital sign-offs for release approvals.

For full architectural details, see [RELEASE_GOVERNANCE.md](file:///d:/MEDIFLOW/RecoverIQ/docs/release/RELEASE_GOVERNANCE.md) and [CHANGE_MANAGEMENT.md](file:///d:/MEDIFLOW/RecoverIQ/docs/release/CHANGE_MANAGEMENT.md).


