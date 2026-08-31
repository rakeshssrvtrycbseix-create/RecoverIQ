# Phase 10H — SPIFFE/SPIRE Microservice Identity & mTLS 1.3 Architecture

## Overview

RecoverIQ **Phase 10H Service Identity & Mutual TLS (mTLS)** establishes cryptographically verifiable microservice identity for 100% of inter-service traffic. Every microservice within the RecoverIQ cluster is assigned a unique **SPIFFE ID** and issued short-lived SVID certificates via TLS 1.3.

---

## Microservice SPIFFE ID Registry

The following 11 microservices have registered SPIFFE identities:

| Service Name | SPIFFE ID Format | Allowed TLS Protocol | Certificate Issuer |
| :--- | :--- | :---: | :--- |
| **API Gateway** | `spiffe://recoveriq.internal/ns/prod/sa/api-gateway` | TLSv1.3 | Vault SPIFFE CA |
| **PolicyEngine** | `spiffe://recoveriq.internal/ns/prod/sa/policy-engine` | TLSv1.3 | Vault SPIFFE CA |
| **Intelligence Control Plane** | `spiffe://recoveriq.internal/ns/prod/sa/intelligence-control-plane` | TLSv1.3 | Vault SPIFFE CA |
| **ActionDispatcher** | `spiffe://recoveriq.internal/ns/prod/sa/action-dispatcher` | TLSv1.3 | Vault SPIFFE CA |
| **Razorpay Action Provider** | `spiffe://recoveriq.internal/ns/prod/sa/razorpay-provider` | TLSv1.3 | Vault SPIFFE CA |
| **ZeroTrustSecurityService** | `spiffe://recoveriq.internal/ns/prod/sa/zero-trust-security` | TLSv1.3 | Vault SPIFFE CA |
| **Observability Engine** | `spiffe://recoveriq.internal/ns/prod/sa/observability-engine` | TLSv1.3 | Vault SPIFFE CA |
| **Performance Service** | `spiffe://recoveriq.internal/ns/prod/sa/performance-service` | TLSv1.3 | Vault SPIFFE CA |
| **Data Governance Engine** | `spiffe://recoveriq.internal/ns/prod/sa/data-governance` | TLSv1.3 | Vault SPIFFE CA |
| **Release Safety Service** | `spiffe://recoveriq.internal/ns/prod/sa/release-safety` | TLSv1.3 | Vault SPIFFE CA |
| **AuditLog Ledger Service** | `spiffe://recoveriq.internal/ns/prod/sa/audit-ledger` | TLSv1.3 | Vault SPIFFE CA |

---

## Least-Privilege Inter-Service Authorization Matrix

Cross-service communication follows strict deny-all defaults. Only explicit caller-callee permissions are authorized:

```
[API Gateway] ───────(EVALUATE_POLICY)───────► [PolicyEngine]
[API Gateway] ───(READ_SECURITY_POSTURE)───► [ZeroTrustSecurityService]
[Intelligence] ──────(EVALUATE_POLICY)───────► [PolicyEngine]
[PolicyEngine] ──────(DISPATCH_ACTION)──────► [ActionDispatcher]
[ZeroTrust] ───X─(DISMISS_FINANCIAL_ACTION)─X► [PolicyEngine]   (DENIED)
[ZeroTrust] ───X─────(EXECUTE_RECOVERY)─────X► [ActionDispatcher](DENIED)
```

### Authorization Rules Table

| Caller Microservice | Target Microservice | Scope / Action Permission | Decision | Financial Path |
| :--- | :--- | :--- | :---: | :---: |
| `API Gateway` | `PolicyEngine` | `EVALUATE_POLICY` | **`PERMIT`** | Yes (Read-Only) |
| `Intelligence Control Plane` | `PolicyEngine` | `EVALUATE_POLICY` | **`PERMIT`** | Yes (Read-Only) |
| `PolicyEngine` | `ActionDispatcher` | `DISPATCH_ACTION` | **`PERMIT`** | Yes (Authoritative) |
| `ZeroTrustSecurityService` | `PolicyEngine` | `READ_POLICY_CONFIG` | **`PERMIT`** | No |
| `ZeroTrustSecurityService` | `PolicyEngine` | `DISMISS_FINANCIAL_ACTION` | **`DENY`** | **Blocked** |
| `ZeroTrustSecurityService` | `ActionDispatcher` | `EXECUTE_RECOVERY` | **`DENY`** | **Blocked** |
| `ZeroTrustSecurityService` | `Razorpay Provider` | `MUTATE_PAYMENT` | **`DENY`** | **Blocked** |
