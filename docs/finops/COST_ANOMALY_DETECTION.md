# FinOps Cost Anomaly Detection Engine

## Overview

RecoverIQ incorporates a real-time **Cost Anomaly Detection Engine** that scans hourly and daily cost telemetry for unexpected cost spikes, traffic-cost divergence, runaway microservice loops, and unoptimized resource provisioning.

---

## Statistical Detection Methods

Cost anomalies are identified using dual-band statistical surveillance:

1. **Z-Score Deviation Engine**:
   $$Z_t = \frac{C_t - \mu_{C, 14\text{d}}}{\sigma_{C, 14\text{d}}}$$
   - $|Z_t| \ge 3.0$: Critical Anomaly Flagged.
   - $2.0 \le |Z_t| < 3.0$: Warning Anomaly Flagged.

2. **Cost-to-Traffic Divergence Ratio (CTDR)**:
   $$\text{CTDR} = \frac{\Delta \text{Cost}_{\text{hourly}} (\% + 100)}{\Delta \text{Transactions}_{\text{hourly}} (\% + 100)}$$
   - $\text{CTDR} > 2.5$: Cost grew $2.5\times$ faster than business transaction volume — indicates runaway worker, infinite loop, or missing cache.

---

## Anomaly Severity Levels

- **`CRITICAL`**: Hourly cost $> +100\%$ over baseline or unbudgeted run rate $> ₹10,000/\text{day}$.
- **`HIGH`**: Hourly cost $> +50\%$ over baseline or continuous unbudgeted spend $> ₹3,000/\text{day}$.
- **`MEDIUM`**: Deviation between $25\%$ and $50\%$ over expected baseline.
- **`LOW`**: Minor statistical outlier ($15\%$ to $25\%$), self-resolving.

---

## Automated Alerting & Evidence Hashing

Every anomaly generates an immutable `CostAnomaly` record with an HMAC-SHA256 evidence fingerprint guaranteeing the raw telemetry cannot be tampered with.
