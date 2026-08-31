# FinOps Cost Allocation & Attribution Model

## Overview

The RecoverIQ **Cost Allocation Engine** provides granular attribution of cloud infrastructure expenditure across all **11 Core Microservices** and **9 Cost Categories**. It enables precise visibility into where capital is deployed and supports multi-dimensional attribution across compute, memory, database, cache, network, and machine learning infrastructure.

---

## The 11 Core Microservices

Infrastructure costs are mapped 100% deterministically to the following services:

1. **API Gateway**: Edge routing, TLS termination, API rate limiting, and request validation.
2. **PolicyEngine**: Authoritative financial recovery rule evaluation and ML scoring integration.
3. **Intelligence Control Plane**: Real-time analytics, shadow deployments, ML lifecycle, and continuous learning.
4. **ActionDispatcher**: Recovery action dispatching, scheduling, and state machine transitions.
5. **Razorpay Action Provider**: Payment gateway integration, webhook signature verification, and reconciliation.
6. **ZeroTrustSecurityService**: mTLS management, SPIFFE validation, eBPF network filtering, and PII/secret scrubbing.
7. **Observability Engine**: Prometheus metric ingestion, distributed tracing, OpenTelemetry collectors, and error budget tracking.
8. **Performance Service**: Load test harness, bottleneck analyzers, capacity forecasting, and regression detectors.
9. **Data Governance Engine**: Lineage tracking, GDPR/DPDP privacy requests, retention lifecycle, and PII audit scanning.
10. **Release Safety Service**: Change risk scoring, API compatibility verification, feature flags, and canary rollouts.
11. **AuditLog Ledger Service**: Append-only cryptographic audit logging, HMAC validation, and compliance evidence trails.

---

## The 9 Cost Categories

| Cost Category | Description | Primary Drivers | Cost Metric |
| :--- | :--- | :--- | :--- |
| `COMPUTE` | Worker nodes, API pods, background tasks | CPU cores, memory limits, container replicas | ₹ / Core-Hour |
| `DATABASE` | PostgreSQL Aurora instances, read replicas | Provisioned IOPS, storage GB, query throughput | ₹ / GB-Month, ₹ / 100k IOPS |
| `CACHE` | Redis Cluster nodes, cache persistence | Memory allocation, ops/sec throughput | ₹ / GB-Month, ₹ / 1M Ops |
| `NETWORK` | Ingress/egress bandwidth, cross-AZ traffic | Data transfer GB, NAT gateway processing | ₹ / GB Egress |
| `STORAGE` | S3 cold storage, backup snapshots, EBS volumes | Capacity GB, retention lifecycle tier | ₹ / GB-Month |
| `ML_INFERENCE` | XGBoost & LightGBM model scoring servers | GPU/CPU compute, inference batching | ₹ / 1k Inferences |
| `OBSERVABILITY` | OTel collectors, Loki logs, Prometheus metrics | Active time-series, log ingestion GB | ₹ / GB Ingested |
| `SECURITY` | Vault instances, KMS key calls, WAF inspection | API request volume, cryptographic keys | ₹ / 10k KMS Calls |
| `THIRD_PARTY` | Razorpay gateway fees, SMS/Email notification providers | External API call volume, delivery status | ₹ / API Call |

---

## Cost Attribution Formula

For each service $s \in \text{Services}$:

$$\text{Monthly Cost}(s) = \sum_{c \in \text{Categories}} \text{Allocated Cost}(s, c)$$

$$\text{Cost Share}(s) = \frac{\text{Monthly Cost}(s)}{\sum_{i} \text{Monthly Cost}(i)} \times 100\%$$

$$\text{Cost per 1k Requests}(s) = \frac{\text{Monthly Cost}(s)}{\text{Monthly Request Volume}(s) / 1000}$$
