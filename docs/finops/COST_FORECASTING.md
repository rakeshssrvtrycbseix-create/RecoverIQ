# FinOps Cost Forecasting & Scenario Modeling

## Overview

The RecoverIQ **Cost Forecasting Engine** generates predictive statistical trajectories for infrastructure expenditure over 7-day, 30-day, and 90-day planning horizons. Using autoregressive Holt-Winters exponential smoothing and traffic-weighted linear regression, the model provides deterministic forecast scenarios with explicit confidence intervals.

---

## Forecast Scenarios

The engine generates three standard scenarios:

1. **Baseline Scenario**: Assumes current traffic growth trend (+5% MoM), standard ML training cadence, and baseline batch indexing.
2. **Aggressive Growth Scenario**: Models +25% MoM transaction acceleration, 3x shadow model deployments, and multi-region read replicas.
3. **Optimized Scenario**: Models immediate adoption of all approved rightsizing, idle resource shutdowns, and ML model quantization recommendations.

---

## Statistical Formulation

The baseline forecast $\hat{C}_{t+h}$ for horizon $h$ days is calculated as:

$$\hat{C}_{t+h} = \left(\mu_C + \beta_T \cdot h\right) \cdot \gamma_{\text{dow}(t+h)} \cdot M_{\text{traffic}}$$

Where:
- $\mu_C$: Rolling 30-day baseline daily expenditure.
- $\beta_T$: Linear drift coefficient.
- $\gamma_{\text{dow}}$: Day-of-week seasonality multiplier ($\gamma_{\text{weekday}} \approx 1.08, \gamma_{\text{weekend}} \approx 0.82$).
- $M_{\text{traffic}}$: Transaction volume scaling factor.

---

## Forecast States

- **`ON_TRACK`**: Variance between forecast and allocated budget is within $\pm 5\%$.
- **`OVER_BUDGET_PROJECTED`**: 30-day forecast exceeds allocated budget by $> 5\%$.
- **`UNDER_BUDGET_PROJECTED`**: 30-day forecast is below allocated budget by $> 15\%$ (indicating over-provisioning or idle capacity).
- **`VOLATILE`**: Forecast confidence interval exceeds $\pm 20\%$ due to erratic traffic spikes.
