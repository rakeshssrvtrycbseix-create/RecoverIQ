# Responsible AI, Fairness Audits & Synthetic Cohort Disparity

## 1. Responsible AI Principles in Debt Recovery

Fintech debt recovery requires stringent protections against algorithmic bias, ensuring that debtor scoring is based purely on objective financial propensity and interaction history, free from protected demographic bias.

RecoverIQ enforces fairness without storing or processing sensitive demographic attributes by utilizing **synthetic non-identifying proxy cohorts** (`SYNTH_COHORT_A`, `SYNTH_COHORT_B`, etc.).

---

## 2. Quantitative Fairness Metrics

### Disparate Impact Ratio (80% Rule)
The ratio of the favorable outcome rate in an unprivileged synthetic cohort to that in a privileged baseline cohort:

$$\text{DIR} = \frac{P(\hat{Y} = 1 \mid \text{Cohort}_{\text{Unprivileged}})}{P(\hat{Y} = 1 \mid \text{Cohort}_{\text{Privileged}})}$$

- **Threshold**: $\text{DIR} \ge 0.80$ (Observed: 0.96)
- **Gate**: `GATE-ML-13` (PASS)

### Demographic Parity Disparity
The absolute difference in positive prediction rates across synthetic cohorts:

$$\text{DPD} = |P(\hat{Y} = 1 \mid \text{Cohort}_A) - P(\hat{Y} = 1 \mid \text{Cohort}_B)|$$

- **Threshold**: $\text{DPD} \le 0.05$ (Observed: 0.02)
- **Gate**: `GATE-ML-13` (PASS)

### Equal Opportunity Difference
The difference in true positive rates (recall) across cohorts:

$$\text{EOD} = |\text{TPR}_A - \text{TPR}_B|$$

- **Threshold**: $\text{EOD} \le 0.05$ (Observed: 0.01)

---

## 3. Auditing & Governance Protocol

1. **Continuous Evaluation**: Every candidate model undergoing promotion review is audited against the synthetic cohort suite.
2. **Deterministic Blocking**: Any candidate model failing the $\text{DIR} \ge 0.80$ or $\text{DPD} \le 0.05$ threshold is immediately assigned a `PROMOTION_REJECTED` status.
3. **Audit Trail**: Fairness metrics are signed and preserved in immutable `AuditLog` records with cryptographic evidence hashes.
