# Multi-Dimensional Drift Surveillance & Population Stability Index (PSI)

## 1. Multi-Dimensional Drift Taxonomy

RecoverIQ Phase 10J monitors 4 dimensions of statistical drift:

1. **Data Drift**: Shifts in raw input distributions prior to feature engineering.
2. **Feature Drift**: Shifts in normalized, scaled feature vectors fed into models.
3. **Prediction Drift**: Shifts in model output probabilities or classification distributions.
4. **Concept Drift**: Degradation of the statistical relationship between features and true recovery outcomes over time ($P(Y|X)$).

---

## 2. Mathematical Formulations

### Population Stability Index (PSI)
For baseline distribution $B = [b_1, b_2, \dots, b_k]$ and current distribution $A = [a_1, a_2, \dots, a_k]$, the PSI is defined as:

$$\text{PSI} = \sum_{i=1}^{k} (A_i - B_i) \times \ln\left(\frac{A_i + \epsilon}{B_i + \epsilon}\right)$$

Where $\epsilon = 10^{-6}$ provides numerical stability and prevents division-by-zero or $\ln(0)$ undefined errors.

### Two-Sample Kolmogorov-Smirnov (KS) Statistic
Measures the maximum vertical distance between empirical cumulative distribution functions $F_A(x)$ and $F_B(x)$:

$$D = \sup_x |F_A(x) - F_B(x)|$$

### Jensen-Shannon (JS) Divergence
A symmetric and bounded statistical distance metric:

$$\text{JS}(A \parallel B) = \frac{1}{2} D_{\text{KL}}(A \parallel M) + \frac{1}{2} D_{\text{KL}}(B \parallel M)$$

where $M = \frac{1}{2}(A + B)$ and $D_{\text{KL}}$ is the Kullback-Leibler divergence.

---

## 3. Drift Thresholds & Automated Alerting

| Metric | Range | Status Classification | Automated Action |
| :--- | :--- | :--- | :--- |
| **PSI** | $\text{PSI} < 0.10$ | `STABLE` | Normal operations; continuous logging. |
| **PSI** | $0.10 \le \text{PSI} < 0.25$ | `MINOR_DRIFT` / `MODERATE_DRIFT` | `WARN` alert logged; notification sent to ML Ops. |
| **PSI** | $\text{PSI} \ge 0.25$ | `SEVERE_DRIFT` / `CRITICAL_DRIFT` | `SEV-2` incident generated; promotion blocked. |
| **KS Stat** | $D \ge 0.15$ | `WARNING` | Feature distribution shift flagged. |
| **JS Div** | $\text{JS} \ge 0.10$ | `WARNING` | Divergence alert logged in audit trail. |
