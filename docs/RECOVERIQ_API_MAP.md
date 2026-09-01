# RecoverIQ — Production API Contract & Route Map

**Base URL**: `http://localhost:8000`  
**Authentication**: Bearer JWT (`Authorization: Bearer <token>`)  
**Data Format**: JSON (Strict zero-PII and zero-secret response contract)  

---

## 1. Authentication & Identity (`/api/auth`)

| Method | Path | Required Role | Summary | Request Body / Params | Response Schema |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `POST` | `/api/auth/token` | Public | Issue signed JWT token | `LoginRequest` (`user_id`, `role`, `secret`) | `TokenResponse` (`access_token`, `expires_in`, `role`, `jti`) |
| `GET` | `/api/auth/me` | `VIEWER` | Return verified user context | None | `AuthenticatedUser` (`id`, `role`, `jti`) |

---

## 2. Core Recovery Operations (`/api/recovery`)

| Method | Path | Required Role | Summary | Request Body / Params | Response Schema |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `GET` | `/api/recovery/metrics` | `VIEWER` | Top-level KPIs & worker telemetry | None | `RecoveryMetricsResponse` |
| `GET` | `/api/recovery/cases` | `VIEWER` | List paginated recovery cases | `page`, `page_size`, `status`, `recovery_stage`, `search` | `PaginatedRecoveryCasesResponse` |
| `GET` | `/api/recovery/cases/{case_id}` | `VIEWER` | Full recovery case lifecycle timeline | `case_id: UUID` | `RecoveryCaseDetailResponse` |
| `GET` | `/api/recovery/human-review` | `VIEWER` | List cases pending human review | `page`, `page_size` | `PaginatedHumanReviewResponse` |
| `POST` | `/api/recovery/human-review/{case_id}/approve` | `OPERATOR` | Approve case and schedule recovery action | `HumanReviewActionRequest` (`notes`) | `HumanReviewActionResponse` |
| `POST` | `/api/recovery/human-review/{case_id}/dismiss` | `OPERATOR` | Dismiss case with audit trail record | `HumanReviewActionRequest` (`notes`) | `HumanReviewActionResponse` |
| `GET` | `/api/recovery/audit-logs` | `VIEWER` | List immutable append-only audit trail | `page`, `page_size`, `event_type`, `case_id` | `PaginatedAuditLogsResponse` |

---

## 3. Webhooks (`/webhooks`)

| Method | Path | Headers | Summary | Payload |
| :--- | :--- | :--- | :--- | :--- |
| `POST` | `/webhooks/razorpay` | `X-Razorpay-Signature`, `X-Razorpay-Event-Id` | Ingest, verify, and sanitize Razorpay events | Razorpay event JSON payload |

---

## 4. Phase 9 Intelligence & ML Lifecycle (`/api/recovery/intelligence`)

| Method | Path | Required Role | Summary | Response |
| :--- | :--- | :--- | :--- | :--- |
| `GET` | `/api/recovery/intelligence/evaluation` | `VIEWER` | Model evaluation & accuracy metrics | `IntelligenceEvaluationResponse` |
| `GET` | `/api/recovery/intelligence/governance` | `VIEWER` | Model drift (PSI) & health report | `ModelGovernanceResponse` |
| `GET` | `/api/recovery/intelligence/optimization` | `VIEWER` | Strategy optimization & ERV report | `StrategyOptimizationResponse` |
| `POST` | `/api/recovery/intelligence/simulation` | `VIEWER` | Counterfactual scenario simulation | `CounterfactualSimulationResponse` |
| `GET` | `/api/recovery/intelligence/recommendations` | `VIEWER` | List governed strategy recommendations | `PaginatedRecommendationsResponse` |
| `POST` | `/api/recovery/intelligence/recommendations/{id}/approve` | `OPERATOR` | Approve strategy recommendation | `StrategyRecommendationResponse` |
| `POST` | `/api/recovery/intelligence/recommendations/{id}/reject` | `OPERATOR` | Reject strategy recommendation | `StrategyRecommendationResponse` |
| `GET` | `/api/recovery/intelligence/models` | `VIEWER` | List registered models in registry | `PaginatedModelsResponse` |
| `POST` | `/api/recovery/intelligence/models/train` | `OPERATOR` | Train candidate offline model | `ModelSummaryResponse` |
| `GET` | `/api/recovery/intelligence/continuous-learning` | `VIEWER` | Continuous learning telemetry & triggers | `ContinuousLearningSummary` |
| `GET` | `/api/recovery/intelligence/experiments` | `VIEWER` | List A/B causal experiments | `PaginatedExperimentsResponse` |
| `POST` | `/api/recovery/intelligence/experiments` | `OPERATOR` | Create new causal experiment | `ExperimentResponse` |

---

## 5. Phase 10 Control Planes

### 10A — Security & Trust (`/api/recovery/security`)
- `GET /api/recovery/security/trust-center` — Executive trust posture and control health.
- `GET /api/recovery/security/events` — Chronological security audit and threat events.
- `POST /api/recovery/security/revoke-token` — Emergency JTI token revocation tripwire (`ADMIN`).
- `POST /api/recovery/security/scan-pii` — On-demand PII and secret discovery scan (`OPERATOR`).

### 10B — Compliance & Governance (`/api/recovery/intelligence/compliance`)
- `GET /api/recovery/intelligence/compliance` — Compliance summary and risk score.
- `GET /api/recovery/intelligence/compliance/controls` — DPDP, RBI, and SOC2 control matrix.
- `GET /api/recovery/intelligence/compliance/incidents` — Detected compliance incidents.
- `GET /api/recovery/intelligence/compliance/audit-coverage` — Event-sourced audit trail coverage.
- `GET /api/recovery/intelligence/compliance/report` — Exportable regulatory compliance report.

### 10C — Operational Resilience (`/api/recovery/intelligence/resilience`)
- `GET /api/recovery/intelligence/resilience` — Executive resilience overview and RTO/RPO score.
- `GET /api/recovery/intelligence/resilience/services` — Individual dependency health and latencies.
- `GET /api/recovery/intelligence/resilience/runbooks` — Automated disaster recovery runbooks.
- `POST /api/recovery/intelligence/resilience/simulate` — Safe observational blast radius simulation (`OPERATOR`).
- `POST /api/recovery/intelligence/resilience/verify-recovery` — Automated multi-service recovery verification (`OPERATOR`).

### 10D — Observability & SRE (`/api/recovery/intelligence/observability`)
- `GET /api/recovery/intelligence/observability` — SRE health summary and operational state.
- `GET /api/recovery/intelligence/observability/slis` — Service Level Indicators (P50/P95/P99, error rate).
- `GET /api/recovery/intelligence/observability/slos` — Service Level Objectives compliance.
- `GET /api/recovery/intelligence/observability/error-budget` — Error budget burn rates.
- `GET /api/recovery/intelligence/observability/alerts` — Deduplicated active alerts.
- `GET /api/recovery/intelligence/observability/incidents` — SRE incidents command view.
- `GET /api/recovery/intelligence/observability/traces` — End-to-end distributed traces.
- `GET /api/recovery/intelligence/observability/financial-path` — Financial pipeline stage latencies.
- `POST /api/recovery/intelligence/observability/postmortems` — Create post-incident review report (`OPERATOR`).

### 10E — Data Governance & Privacy (`/api/recovery/intelligence/data-governance`)
- `GET /api/recovery/intelligence/data-governance` — Executive privacy engineering summary.
- `GET /api/recovery/intelligence/data-governance/assets` — Data asset catalog and field classifications.
- `GET /api/recovery/intelligence/data-governance/controls` — 25 privacy controls and evaluation states.
- `GET /api/recovery/intelligence/data-governance/lineage` — End-to-end data lineage graph.
- `GET /api/recovery/intelligence/data-governance/retention` — Data retention and disposal schedules.
- `GET /api/recovery/intelligence/data-governance/erasure-eligibility` — Advisory subject erasure check.
- `POST /api/recovery/intelligence/data-governance/privacy-requests` — Create DPDP privacy request (`VIEWER`).
- `POST /api/recovery/intelligence/data-governance/privacy-requests/{id}/review` — Review privacy request (`ADMIN`).

### 10F — Performance & Capacity (`/api/recovery/intelligence/performance`)
- `GET /api/recovery/intelligence/performance` — Global performance score and throughput.
- `GET /api/recovery/intelligence/performance/capacity` — Safe operating headroom and scaling advisory.
- `GET /api/recovery/intelligence/performance/database` — Connection pool utilization and query latencies.
- `GET /api/recovery/intelligence/performance/load-tests` — Historical load test execution reports.
- `POST /api/recovery/intelligence/performance/load-tests` — Execute deterministic load test scenario (`OPERATOR`).

### 10G — Release Governance (`/api/recovery/intelligence/release-governance`)
- `GET /api/recovery/intelligence/release-governance/summary` — Release safety score and readiness.
- `GET /api/recovery/intelligence/release-governance/changes` — Change requests and risk classifications.
- `GET /api/recovery/intelligence/release-governance/api-compatibility` — OpenAPI backward compatibility report.
- `GET /api/recovery/intelligence/release-governance/database-compatibility` — Database migration drift check.
- `GET /api/recovery/intelligence/release-governance/feature-flags` — Dynamic feature flags and rollouts.
- `POST /api/recovery/intelligence/release-governance/release-candidates/{id}/approve` — Release sign-off (`ADMIN`).

### 10H — Zero Trust Security (`/api/recovery/intelligence/zero-trust`)
- `GET /api/recovery/intelligence/zero-trust/summary` — Zero-trust security score and posture.
- `GET /api/recovery/intelligence/zero-trust/identities` — Service identity registry and cryptographic keys.
- `GET /api/recovery/intelligence/zero-trust/auth-matrix` — Inter-service authorization matrix and violations.
- `GET /api/recovery/intelligence/zero-trust/threats` — Behavioral threat indicators and anomaly scores.
- `GET /api/recovery/intelligence/zero-trust/attack-chains` — Reconstructed multi-stage attack chains.
- `GET /api/recovery/intelligence/zero-trust/secrets` — Codebase and runtime secret exposure findings.

### 10I — FinOps & Cost Intelligence (`/api/recovery/intelligence/finops`)
- `GET /api/recovery/intelligence/finops/summary` — FinOps score and cost allocation summary.
- `GET /api/recovery/intelligence/finops/unit-economics` — Unit economics (cost per recovery, cost per attempt).
- `GET /api/recovery/intelligence/finops/budgets` — Service-level budget tracking and variance.
- `GET /api/recovery/intelligence/finops/optimizations` — Cost optimization recommendations.
- `POST /api/recovery/intelligence/finops/optimizations/{id}/approve` — Approve cost reduction action (`ADMIN`).

### 10J — AI/ML Governance (`/api/recovery/intelligence/ml-governance`)
- `GET /api/recovery/intelligence/ml-governance/summary` — ML governance score and model inventory.
- `GET /api/recovery/intelligence/ml-governance/models/{id}/drift` — Feature, prediction, and outcome drift (PSI).
- `GET /api/recovery/intelligence/ml-governance/models/{id}/fairness` — Demographic parity and equalized odds.
- `GET /api/recovery/intelligence/ml-governance/models/{id}/explainability` — SHAP feature attribution.
- `GET /api/recovery/intelligence/ml-governance/kill-switches` — Model emergency shutdown controls.
- `POST /api/recovery/intelligence/ml-governance/kill-switches/{id}/toggle` — Toggle model kill-switch (`ADMIN`).
