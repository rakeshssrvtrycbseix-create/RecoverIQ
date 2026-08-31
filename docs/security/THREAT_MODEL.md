# RecoverIQ Threat Model & Risk Analysis (STRIDE)

## 1. Scope & System Boundaries

RecoverIQ processes sensitive recurring subscription failure events, calculates ML-guided recovery scores, and automates recovery attempts. This threat model analyzes potential threats against RecoverIQ's control plane, webhooks, authentication, and execution layers using the **STRIDE** methodology.

```
                      +-----------------------------+
                      |   Razorpay Webhook Sender   |
                      +--------------+--------------+
                                     |
                                     | [HTTPS + HMAC-SHA256 Signature]
                                     v
+------------------+  [JWT / RBAC]  +--------------------------------+
| Operator / Admin | -------------> |       RecoverIQ FastAPI        |
+------------------+                | - SecurityHeadersMiddleware    |
                                    | - SlidingWindowRateLimiter     |
                                    | - Constant-Time HMAC Verifier  |
                                    | - Injection Guard & PII Engine |
                                    +---------------+----------------+
                                                    |
                                                    | [Strict Isolation Barrier]
                                                    v
                                    +--------------------------------+
                                    |          PolicyEngine          |
                                    | (Sole Financial Gatekeeper)    |
                                    +---------------+----------------+
                                                    |
                                                    v
                                    +--------------------------------+
                                    |  PostgreSQL / AuditLog Events  |
                                    +--------------------------------+
```

---

## 2. STRIDE Threat Analysis Matrix

| Threat Category | Potential Vector | Mitigation & Controls in RecoverIQ | Residual Risk |
|---|---|---|---|
| **Spoofing** | Forged JWT access token or attacker impersonating Razorpay webhook sender. | • Strict HS256 algorithm pinning & signature validation.<br>• Constant-time raw body HMAC-SHA256 signature check.<br>• Instant JTI token revocation blacklist. | Minimal |
| **Tampering** | Modifying webhook payload parameters (e.g. payment amount, customer ID) in transit. | • HMAC signature computed over exact raw request bytes prior to JSON parsing.<br>• Tampered signatures immediately rejected (HTTP 401) and logged. | Minimal |
| **Repudiation** | Operator performing unauthorized rollback or action and denying involvement. | • Immutable append-only `AuditLog` captures all state changes, caller identity, and UTC timestamps.<br>• Identity derived authoritatively from verified JWT claims only. | Minimal |
| **Information Disclosure** | Leakage of customer credit card PANs, Aadhaar numbers, CVVs, or API secrets in logs/responses. | • Automated recursive PII/Secret scanner.<br>• Luhn algorithm validation masks card numbers.<br>• Aadhaar 12-digit masking, CVV redaction, private key scrubbing. | Minimal |
| **Denial of Service (DoS)** | Credential brute-forcing, webhook flood attacks, or memory exhaustion from large payloads. | • Thread-safe sliding-window rate limiting per IP (15 auth/m, 120 webhooks/m, 60 mutations/m, 240 reads/m).<br>• 1MB maximum request payload size limit. | Low |
| **Elevation of Privilege** | Viewer role caller attempting to approve models, trigger training runs, or revoke tokens. | • Strict 3-tier RBAC (`VIEWER` < `OPERATOR` < `ADMIN`).<br>• Centralized `require_role` dependency checks on all endpoints.<br>• Client payload `operator_id` is strictly ignored. | Minimal |

---

## 3. Financial Execution Threat Mitigations

### Threat: Malicious or Compromised Security Service Triggering Financial Retries
- **Vulnerability**: An attacker or rogue script abusing security endpoints to trigger unauthorized payment retries.
- **Architectural Defense**:
  - `PolicyEngine` is the **sole** authoritative gatekeeper.
  - Security endpoints are strictly decoupled from `RecoveryActionService`, `ActionDispatcher`, and `RazorpayActionProvider`.
  - Security endpoints never create `RecoveryAction` records or alter `Payment`/`RecoveryCase` financial balances.
  - Verified by automated unit test: `test_mandatory_financial_isolation_guarantee`.

---

## 4. Cryptographic Standards & Key Management

- **JWT Signing**: HMAC-SHA256 (`HS256`) with secret keys loaded strictly from environment variables.
- **Webhook Ingestion**: HMAC-SHA256 computed on raw byte streams using constant-time string comparison (`hmac.compare_digest`).
- **Signature Algorithm Pinning**: Any JWT with algorithm `none`, `RS256`, or mismatched cryptographic primitives is rejected immediately.
- **Token Expiration**: Enforces mandatory `exp`, `iat`, and `nbf` claims with defense against clock skew.
