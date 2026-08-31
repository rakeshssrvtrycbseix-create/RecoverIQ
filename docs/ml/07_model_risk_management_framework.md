# Model Risk Management (MRM) Framework & 10-Factor Scorecard

## 1. Governance Framework Architecture

RecoverIQ implements a regulatory-grade Model Risk Management (MRM) framework aligned with SR 11-7 / OCC 2011-12 standards for model validation, continuous surveillance, and governance scoring.

---

## 2. 10-Factor Weighted Scorecard

The overall model health score is computed deterministically across 10 weighted dimensions:

| # | Dimension Category | Weight (%) | Metric Focus | Target Threshold | Baseline Score | Weighted Points |
| :- | :--- | :-: | :--- | :--- | :-: | :-: |
| 1 | **Data Quality & Integrity** | 10% | Missing values, range violations, schema compliance | 100% schema match | 98.0 | 9.80 |
| 2 | **Model Performance SLA** | 15% | ROC-AUC, Accuracy, F1, PR-AUC | ROC-AUC $\ge 0.85$ | 96.0 | 14.40 |
| 3 | **Drift Surveillance** | 15% | Feature & Prediction PSI with $\epsilon=10^{-6}$ | $\text{PSI} < 0.10$ | 97.0 | 14.55 |
| 4 | **Fairness & Parity** | 10% | Disparate Impact Ratio, Demographic Parity | $\text{DIR} \ge 0.80$ | 99.0 | 9.90 |
| 5 | **Calibration Error** | 10% | Expected Calibration Error, Brier Score | $\text{ECE} \le 0.05$ | 98.0 | 9.80 |
| 6 | **Explainability** | 10% | Linear SHAP attributions, zero PII | 100% sanitized | 97.0 | 9.70 |
| 7 | **Robustness & Adversarial** | 10% | Noise injection resilience, boundary stability | Stability $\ge 95\%$ | 95.0 | 9.50 |
| 8 | **Operational Reliability** | 5% | p99 Latency ($\le 25\text{ms}$), uptime, error rate | Uptime $\ge 99.95\%$ | 98.0 | 4.90 |
| 9 | **Privacy & Sanitization** | 5% | Zero PAN, CVV, Aadhaar, names in payloads | Strict 0 violations | 100.0 | 5.00 |
| 10 | **Financial Isolation** | 10% | Observational purity, $\Delta\text{RecoveryAction}=0$ | 0 financial calls | 100.0 | 10.00 |
| **Total** | | **100%** | | | | **97.55 / 100** |

---

## 3. Model Risk Tier Classification

Models are classified into 4 operational risk tiers:
- **Tier 1 (Critical)**: Models influencing case prioritization or channel strategy (`recovery_probability`).
- **Tier 2 (High)**: Models guiding timing and discount elasticity (`optimal_channel`, `optimal_timing`, `discount_sensitivity`).
- **Tier 3 (Medium)**: Urgent aging heuristic models (`urgency_scorer`).
- **Tier 4 (Low)**: Observational exploration prototypes.
