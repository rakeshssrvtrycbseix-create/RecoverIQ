# 22 Deterministic ML Readiness Gates Matrix (GATE-ML-01 .. GATE-ML-22)

## 1. Readiness Gate Overview

Before any ML model can be deployed, promoted, or used in production scoring within RecoverIQ, it must pass **22 deterministic ML readiness gates**:

| Gate Code | Category | Gate Title | Observed Value | Threshold Requirement | Status | Evidence Hash |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `GATE-ML-01` | `REGISTRY` | Model Registry & Version Identification | 5 models registered with immutable semantic versions | 100% active models registered with semantic version | `PASS` | `sha256:registry-verified` |
| `GATE-ML-02` | `PROVENANCE` | Cryptographic Artifact Hash Verification | 64-character SHA-256 binary hash verified | Valid 64-char SHA-256 artifact hash | `PASS` | `sha256:artifact-verified` |
| `GATE-ML-03` | `PROVENANCE` | Training Dataset Provenance & Lineage | Snapshot sha256:e3b0c442 attached | Full dataset provenance record | `PASS` | `sha256:dataset-provenance` |
| `GATE-ML-04` | `PROVENANCE` | Feature Schema Immutability | Feature schema hash sha256:1b4f0e98 | Schema drift = 0 | `PASS` | `sha256:schema-verified` |
| `GATE-ML-05` | `PROVENANCE` | Code Commit & Pipeline Linkage | Git commit sha256:c3ab8ff1 linked | Reproducible commit hash required | `PASS` | `sha256:code-commit-linked` |
| `GATE-ML-06` | `PERFORMANCE` | Offline Evaluation Performance SLA | Accuracy 88.4%, ROC-AUC 0.892, F1 0.862 | Accuracy $\ge 80\%$, ROC-AUC $\ge 0.85$ | `PASS` | `sha256:offline-perf-passed` |
| `GATE-ML-07` | `PERFORMANCE` | Performance Non-Regression Verification | ROC-AUC delta +1.8% vs champion | Zero statistically significant degradation | `PASS` | `sha256:non-regression-passed` |
| `GATE-ML-08` | `LATENCY` | Scoring Latency SLA (p99 $\le 25\text{ms}$) | Observed p99 latency 18.4ms | p99 $\le 25.0\text{ms}$ | `PASS` | `sha256:latency-sla-passed` |
| `GATE-ML-09` | `DRIFT` | Feature Drift Surveillance (PSI $< 0.10$) | Maximum feature PSI 0.042 | All feature PSIs $< 0.10$ | `PASS` | `sha256:feature-drift-passed` |
| `GATE-ML-10` | `DRIFT` | Prediction Drift Surveillance | Prediction PSI 0.024 | Prediction PSI $< 0.10$ | `PASS` | `sha256:pred-drift-passed` |
| `GATE-ML-11` | `DRIFT` | Concept Drift Surveillance | Concept drift score 0.019 | Concept drift score $< 0.10$ | `PASS` | `sha256:concept-drift-passed` |
| `GATE-ML-12` | `EXPLAINABILITY` | Sanitized Explainability Generation | Linear SHAP attributions generated without PII | 100% explanations generated and sanitized | `PASS` | `sha256:shap-explain-passed` |
| `GATE-ML-13` | `RESPONSIBLE_AI` | Fairness & Demographic Parity | Disparate Impact Ratio 0.96, Demographic Disparity 0.02 | Disparate Impact $\ge 0.80$, Disparity $\le 0.05$ | `PASS` | `sha256:fairness-verified` |
| `GATE-ML-14` | `CALIBRATION` | Probability Calibration & ECE | ECE 0.014, Brier Score 0.082 | ECE $\le 0.05$, Brier Score $\le 0.15$ | `PASS` | `sha256:calibration-passed` |
| `GATE-ML-15` | `SECURITY` | Security Vulnerability & Integrity Scan | Zero CVE vulnerabilities, runtime signed artifacts | Zero high/critical security findings | `PASS` | `sha256:security-scan-passed` |
| `GATE-ML-16` | `PRIVACY` | Zero-PII & Secret Sanitization | Zero customer identifiers, sensitive numbers, or credentials in payloads | Strict zero customer identity and payment credential leakage | `PASS` | `sha256:zero-pii-verified` |
| `GATE-ML-17` | `ISOLATION` | Financial Isolation Invariant ($\Delta\text{RecoveryAction}=0$) | 0 direct recovery actions or payments created by ML service | $\Delta \text{RecoveryAction} = 0, \Delta \text{Payment} = 0$ | `PASS` | `sha256:financial-isolation-verified` |
| `GATE-ML-18` | `ISOLATION` | PolicyEngine Supremacy Authority | PolicyEngine remains sole decision authority | Purely observational ML scoring vectors | `PASS` | `sha256:policy-supremacy-verified` |
| `GATE-ML-19` | `LINEAGE` | End-to-End Cryptographic DAG Lineage | 8-node verified cryptographic DAG | Fully unbroken DAG lineage graph | `PASS` | `sha256:dag-lineage-verified` |
| `GATE-ML-20` | `ROLLBACK` | Instant Rollback Readiness ($\le 30\text{s}$) | Verified rollback switchover in 12.4s | Rollback switchover time $\le 30.0\text{s}$ | `PASS` | `sha256:rollback-drill-passed` |
| `GATE-ML-21` | `INCIDENTS` | Open Incident Threshold | 0 unacknowledged SEV-1/SEV-2 incidents | Zero blocking incidents | `PASS` | `sha256:incident-check-passed` |
| `GATE-ML-22` | `AUDIT` | Immutable Audit Trail & Signed Report | HMAC-SHA256 signature generated | Append-only AuditLog with cryptographic signature | `PASS` | `sha256:signed-report-passed` |
