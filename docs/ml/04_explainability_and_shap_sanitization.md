# Sanitized Explainability & Linear SHAP Attribution

## 1. Objectives & Safety Guarantees

In financial debt recovery, model explainability must satisfy two competing requirements:
1. **Granular Transparency**: Operators and auditors must understand exactly why a specific propensity or urgency score was generated.
2. **Strict Zero-PII Sanitization**: Explainability records must never leak personally identifiable information (PII), bank account details, PAN/Aadhaar numbers, or internal secret keys.

---

## 2. Linear SHAP Formulation

For model prediction $f(x)$ given input feature vector $x = (x_1, \dots, x_M)$, the Shapley additive explanation satisfies:

$$g(z') = \phi_0 + \sum_{j=1}^M \phi_j z_j'$$

Where $\phi_0$ is the base expected value and $\phi_j$ is the feature attribution weight for feature $j$.

### Relative Percentage Contribution
To present normalized attributions to operators, the system computes:

$$\text{Pct}_j = \frac{|\phi_j|}{\sum_{k=1}^M |\phi_k|} \times 100\%$$

Ensuring $\sum_{j=1}^M \text{Pct}_j = 100\%$.

---

## 3. PII Sanitization & Zero-Leakage Pipeline

The explainability engine applies strict deterministic sanitization:

```
[Raw Case Telemetry]
       │
       ▼ (Sanitization & Normalization)
[Sanitized Feature Names] (e.g. dpd_bucket_normalized, historical_payment_rate)
       │
       ▼ (SHAP Linear Decomposition)
[Feature Contributions & Weights] (Zero customer names, zero card numbers)
       │
       ▼ (Automated PII Regex Scan)
[Clean Explainability Record] (Signed with SHA-256 evidence hash)
```

### Mandatory Observational Disclaimer
Every explainability record includes the non-negotiable legal disclaimer:
> *"ML predictions and feature attributions are purely observational inputs to PolicyEngine. No autonomous financial execution, payment creation, or recovery case state mutation occurs within the ML service."*
