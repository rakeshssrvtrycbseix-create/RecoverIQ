# Model Registry, Provenance & Cryptographic Lineage (DAG)

## 1. Canonical Model Catalog

RecoverIQ Phase 10J governs 5 canonical ML models:

| Model ID | Model Name | Architecture / Framework | Tier | Active Version | Primary Purpose |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `recovery_probability` | Recovery Propensity Scorer | XGBoost (Gradient Boosted Trees) | Tier-1 | `v1.0.0` | Predicts debtor repayment likelihood based on DPD and payment history. |
| `optimal_channel` | Contact Channel Optimizer | LightGBM Classifier | Tier-2 | `v1.0.0` | Selects optimal communication channel (WhatsApp, SMS, Email, Voice). |
| `optimal_timing` | Engagement Timing Scorer | CatBoost Regressor | Tier-2 | `v1.0.0` | Determines hour-of-day and day-of-week for highest conversion. |
| `discount_sensitivity` | Settlement Discount Elasticity | Random Forest Regressor | Tier-2 | `v1.0.0` | Estimates marginal payment uplift per percentage point of settlement discount. |
| `urgency_scorer` | Case Escalation Urgency Scorer | Multi-Layer Perceptron (MLP) | Tier-3 | `v1.0.0` | Assesses risk of account aging into severe default cohorts. |

---

## 2. Model Version & Artifact Provenance

Every model version registered in the system must supply complete cryptographic provenance:

- **Artifact SHA-256 Checksum**: 64-character hexadecimal digest of the serialized model weights binary.
- **Training Dataset Hash**: Cryptographic digest of the training data snapshot.
- **Feature Schema Hash**: Digest representing the exact feature ordering, data types, and scaling parameters.
- **Code Commit SHA**: Git commit hash representing the exact training pipeline source code.
- **Hyperparameters Hash**: Deterministic JSON hash of all training hyperparameters.
- **Timestamps**: ISO-8601 UTC timestamps for training completion and offline evaluation sign-off.

---

## 3. Cryptographic Lineage DAG

The lineage of every governed model is represented as an acyclic directed graph (DAG) composed of 8 sequential nodes:

```
[1. Dataset v2.4] (sha256:e3b0c442)
       │
       ▼
[2. Feature Schema] (sha256:1b4f0e98)
       │
       ▼
[3. Git Repo SHA] (sha256:c3ab8ff1)
       │
       ▼
[4. Tuned Hyperparameters] (sha256:8f434346)
       │
       ▼
[5. Model Binary Artifact] (sha256:7f83b165)
       │
       ▼
[6. Offline Benchmarks] (sha256:6b86b273)
       │
       ▼
[7. Governance Sign-Off] (sha256:d4735e3a)
       │
       ▼
[8. Sandbox Runtime Deployment] (sha256:4e074085)
```

### Root Composite Hash
A single composite SHA-256 root digest binds the entire DAG graph:
$$\text{RootHash} = \text{SHA256}(\text{Node}_1 \| \text{Node}_2 \| \dots \| \text{Node}_8)$$
Any alteration to upstream data, code, or weights invalidates the composite root hash, triggering an automated `SEV-1` governance violation.
