# AI/ML Governance, Model Risk Management & Responsible AI Control Plane Architecture

## 1. Executive Summary & Core Mission

RecoverIQ Phase 10J introduces a comprehensive, production-grade **AI/ML Governance, Model Risk Management (MRM), Explainability, Drift Detection & Responsible AI Control Plane**.

The core mission of Phase 10J is to establish deterministic, mathematically grounded, and cryptographically auditable control over all Machine Learning and Artificial Intelligence models within the RecoverIQ platform, while maintaining **absolute financial isolation and observational purity**.

```
+-----------------------------------------------------------------------------------------+
|                                RECOVERIQ AI/ML CONTROL PLANE                            |
|                                                                                         |
|  +---------------------+   +---------------------+   +-------------------------------+  |
|  | 5 Canonical Models  |   | 22 Readiness Gates  |   | 10-Factor MRM Scorecard       |  |
|  | Registry & Versions |   | GATE-ML-01 to 22    |   | Weighted Composite Health     |  |
|  +---------------------+   +---------------------+   +-------------------------------+  |
|            |                          |                              |                  |
|  +---------------------+   +---------------------+   +-------------------------------+  |
|  | Multi-Dim Drift     |   | Sanitized SHAP      |   | Responsible AI Fairness       |  |
|  | PSI with epsilon    |   | 100% Zero PII       |   | Disparate Impact >= 0.80      |  |
|  +---------------------+   +---------------------+   +-------------------------------+  |
|            |                          |                              |                  |
|  +---------------------+   +---------------------+   +-------------------------------+  |
|  | Calibration ECE     |   | Event-Sourced Inc.  |   | Cryptographic DAG Lineage     |  |
|  | ECE <= 0.05         |   | SEV-1 to SEV-4      |   | HMAC-SHA256 Signed Reports    |  |
|  +---------------------+   +---------------------+   +-------------------------------+  |
+-----------------------------------------------------------------------------------------+
                                            |
                                  OBSERVATIONAL SCORING
                                            v
+-----------------------------------------------------------------------------------------+
|                               POLICYENGINE (SOLE AUTHORITY)                             |
|                                                                                         |
|  - Invariant: Delta RecoveryAction = 0 from ML service                                  |
|  - Invariant: Delta Payment = 0 from ML service                                         |
|  - Invariant: ActionDispatcher calls = 0 from ML service                                |
|  - Invariant: Razorpay Provider calls = 0 from ML service                               |
+-----------------------------------------------------------------------------------------+
```

---

## 2. Non-Negotiable Architectural Invariants

| Invariant | Mathematical / Behavioral Proof | Enforcement Mechanism |
| :--- | :--- | :--- |
| **PolicyEngine Supremacy** | $\Delta \text{RecoveryAction} = 0, \Delta \text{Payment} = 0$ | ML service has zero access to `ActionDispatcher` or `RazorpayPaymentProvider`. |
| **Observational Purity** | Read-only input scoring for downstream rules | Model outputs are strictly advisory probability/ranking vectors. |
| **Zero Database Migrations** | Schema version unchanged | Event-sourcing implemented via existing append-only `AuditLog` table. |
| **Zero Customer PII / Secrets** | 0 customer PAN, CVV, Aadhaar, names, secret keys in payloads | Deterministic input sanitization, tokenization, and regex validation. |
| **Cryptographic Integrity** | 64-character SHA-256 artifact checksums and HMAC-SHA256 signatures | SHA-256 DAG lineage and HMAC-SHA256 signed governance export reports. |
| **Deterministic Readiness** | 22 mandatory gates (`GATE-ML-01` to `GATE-ML-22`) | All gates evaluated deterministically prior to model promotion or sign-off. |

---

## 3. Subsystem Breakdown

1. **Model Catalog & Artifact Provenance**: Manages 5 canonical production models with active version tracking, framework metadata, and cryptographic hashes.
2. **Model Lineage DAG Visualizer**: 8 sequential DAG nodes (Dataset $\to$ Feature Store $\to$ Code Repo $\to$ Hyperparameters $\to$ Artifact $\to$ Evaluation $\to$ Approval $\to$ Deployment) linked by SHA-256 digests.
3. **Multi-Dimensional Drift Surveillance**: Real-time tracking of Data, Feature, Prediction, and Concept Drift using Population Stability Index (PSI with $\epsilon=10^{-6}$ safe denominator protection), Kolmogorov-Smirnov (KS) tests, and Jensen-Shannon (JS) divergence.
4. **Sanitized Explainability Engine**: Linear SHAP feature attribution generation, strictly normalized to 100% relative contribution with zero customer PII leakage.
5. **Responsible AI & Fairness Auditing**: Demographic parity, equal opportunity, predictive equality audits across synthetic non-identifying cohorts (`Disparate Impact Ratio` $\ge 0.80$, `Demographic Disparity` $\le 0.05$).
6. **Probability Calibration & Reliability Curve**: Expected Calibration Error (ECE $\le 0.05$), Brier score ($\le 0.15$), and 5-bin reliability curve generation.
7. **Model Risk Management (MRM) Scorecard**: 10-dimension weighted scoring matrix providing composite health scores (0-100) and risk tier assignments (Tier 1-4).
8. **22 Deterministic ML Readiness Gates**: Strict pre-flight validation gates ensuring compliance across Registry, Performance, Drift, Explainability, Fairness, Calibration, Security, Privacy, Isolation, Lineage, Rollback, and Incidents.
9. **Promotion Advisory & Rollback Drill**: Human-in-the-loop candidate comparison, shadow validation verification, and $\le 30$ second rollback SLA verification.
10. **Event-Sourced ML Incident Lifecycle**: Triage, acknowledgment, and resolution workflows with MTTA/MTTR telemetry.
11. **6-Stage Financial Path Observational Forensics**: Verifies zero financial state mutation across the entire decision boundary (`RecoveryCase` $\to$ `MLPrediction` $\to$ `AgentDecision` $\to$ `PolicyDecision` $\to$ `RecoveryAction` $\to$ `ActionResult`).
12. **Cryptographic Governance Reports**: HMAC-SHA256 signed reports ensuring non-repudiation and regulatory compliance.
