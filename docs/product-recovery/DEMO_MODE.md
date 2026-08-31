# RecoverIQ — Development Demo Mode & Seeder

## 1. Overview

RecoverIQ includes a deterministic, safe, synthetic data seeder designed for local evaluation, demos, and end-to-end integration testing.

- **Location**: `backend/scripts/seed_demo_data.py`
- **Safety Policy**: Strictly synthetic data. Uses masked zero-PII representations (`aarav.m****@example.in`), simulated Razorpay test identifiers, and isolated SQLite/PostgreSQL development environments.

---

## 2. Seed Generation Details

The seeder generates:
- **20 Synthetic Customers**: Distributed across Low, Standard, High, and Critical risk tiers.
- **32 Comprehensive Recovery Cases**:
  - **10 Recovered Cases**: Successfully processed through the autonomous smart retry pipeline.
  - **8 In Recovery / Action Pending**: Currently scheduled or executing actions.
  - **6 Escalated to Human Review**: Blocked by high-value threshold (`PR-003_HIGH_VALUE_THRESHOLD`) or risk tier rules (`PR-005_RISK_TIER_OVERRIDE`), waiting in the `/review` queue.
  - **4 Open / Analyzing**: In initial diagnosis phase.
  - **4 Closed Cases**: Exhausted maximum allowed retry attempts (`PR-002_MAX_ATTEMPTS_EXCEEDED`).
- **22 Recovery Actions & Results**: Demonstrating WhatsApp payment links, smart retries, and SMS prompts.
- **140+ Immutable Audit Logs**: Capturing chronological state transitions, ML predictions, AI agent decisions, policy evaluations, and worker dispatches.

---

## 3. Running the Seeder

To seed or reset the database at any time:
```bash
cd backend
python scripts/seed_demo_data.py --reset
```
