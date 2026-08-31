# Probability Calibration, Expected Calibration Error (ECE) & Reliability Curves

## 1. The Critical Role of Probability Calibration

In financial decision systems, a model score of `0.70` must mean that out of 100 cases scored with `0.70`, approximately 70 will successfully result in debt recovery.

Uncalibrated models (e.g. overconfident neural networks or unscaled tree ensembles) distort PolicyEngine discount allocations and retry scheduling. RecoverIQ mandates strict probability calibration across all scoring pipelines.

---

## 2. Calibration Metrics

### Expected Calibration Error (ECE)
The sample-weighted average difference between predicted confidence and observed empirical accuracy across $M$ probability bins:

$$\text{ECE} = \sum_{m=1}^M \frac{|B_m|}{N} \left| \text{acc}(B_m) - \text{conf}(B_m) \right|$$

- **Threshold**: $\text{ECE} \le 0.05$ (Observed: 0.014)
- **Gate**: `GATE-ML-14` (PASS)

### Maximum Calibration Error (MCE)
The worst-case calibration error across all bins:

$$\text{MCE} = \max_{m \in \{1, \dots, M\}} \left| \text{acc}(B_m) - \text{conf}(B_m) \right|$$

- **Threshold**: $\text{MCE} \le 0.10$ (Observed: 0.028)

### Brier Score
Mean squared error of probabilistic predictions:

$$\text{BS} = \frac{1}{N} \sum_{i=1}^N (f_t - o_t)^2$$

- **Threshold**: $\text{BS} \le 0.15$ (Observed: 0.082)

---

## 3. Reliability Curve (5-Bin Breakdown)

| Probability Bin | Mean Predicted Probability | Observed Fraction Recovered | Bin Sample Count | Calibration Status |
| :--- | :--- | :--- | :--- | :--- |
| **0.00 – 0.20** | 0.100 | 0.095 | 30,000 | `CALIBRATED` |
| **0.20 – 0.40** | 0.300 | 0.305 | 30,000 | `CALIBRATED` |
| **0.40 – 0.60** | 0.500 | 0.490 | 30,000 | `CALIBRATED` |
| **0.60 – 0.80** | 0.700 | 0.710 | 30,000 | `CALIBRATED` |
| **0.80 – 1.00** | 0.900 | 0.895 | 30,000 | `CALIBRATED` |
