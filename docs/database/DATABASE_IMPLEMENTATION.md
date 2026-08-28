# RecoverIQ Database Implementation Documentation

## 1. Overview & Architecture

RecoverIQ implements an autonomous, event-driven payment recovery platform. The database schema serves as the canonical relational persistence layer for ingesting payment events, orchestrating recovery cases, recording machine learning inferences, executing deterministic policy checks, dispatching recovery actions, capturing provider telemetry, and maintaining an immutable audit trail.

The database is built on **SQLAlchemy 2.x** with declarative mapped models and version-controlled using **Alembic** migrations. All monetary values are represented as minor units (`BIGINT` paise/cents), identifiers use UUIDv4 (`Uuid(as_uuid=True)`), and semi-structured metadata uses `JSONB` (with SQLite `JSON` fallback).

---

## 2. Table Inventory & Entity Overview

The schema comprises **12 core relational entities**:

| Entity / Table Name | Primary Key | Description |
| :--- | :--- | :--- |
| `customers` | `UUID` (UUIDv4) | Merchant customers with masked contact info, risk tiers, and recovery counters. |
| `subscriptions` | `UUID` (UUIDv4) | Recurring subscription contracts, plan details, cadence, and recurring amounts. |
| `payments` | `UUID` (UUIDv4) | Payment intents, orders, invoices, captured amounts, and lifecycle status. |
| `payment_attempts` | `UUID` (UUIDv4) | Physical payment attempts with error categorization and retry sequences. |
| `payment_events` | `UUID` (UUIDv4) | Immutable inbound webhook event ledger with strict idempotency deduplication. |
| `recovery_cases` | `UUID` (UUIDv4) | Central aggregate tracking overdue/failed payment recovery lifecycle and stage. |
| `ml_predictions` | `UUID` (UUIDv4) | Machine learning inference scores, predicted channels, and feature snapshots. |
| `agent_decisions` | `UUID` (UUIDv4) | LLM AI reasoning summaries, proposed actions, and confidence scores. |
| `policy_decisions` | `UUID` (UUIDv4) | Deterministic safety rule evaluations (`ALLOWED`, `BLOCKED`, `HUMAN_REVIEW`). |
| `recovery_actions` | `UUID` (UUIDv4) | Approved recovery actions scheduled and dispatched with idempotency safeguards. |
| `action_results` | `UUID` (UUIDv4) | Downstream provider execution telemetry and response payloads. |
| `audit_logs` | `BIGINT` (Autoincrement) | Global immutable append-only audit trail logging state transitions and actor actions. |

---

## 3. Key Constraints & Data Integrity

### Check Constraints
- `chk_subscription_recurring_amount_non_negative`: `subscriptions.recurring_amount >= 0`
- `chk_payment_amount_non_negative`: `payments.amount >= 0`
- `chk_payment_attempt_amount_non_negative`: `payment_attempts.amount >= 0`
- `chk_case_amount_at_risk_non_negative`: `recovery_cases.amount_at_risk >= 0`
- `chk_case_recovered_amount_non_negative`: `recovery_cases.recovered_amount >= 0`
- `chk_case_recovered_not_exceed_risk`: `recovery_cases.recovered_amount <= recovery_cases.amount_at_risk`
- `chk_ml_recovery_probability_range`: `ml_predictions.recovery_probability >= 0.0000 AND ml_predictions.recovery_probability <= 1.0000`
- `chk_agent_confidence_score_range`: `agent_decisions.confidence_score >= 0.0000 AND agent_decisions.confidence_score <= 1.0000`

### Uniqueness & Sequence Constraints
- `uq_customers_external_customer_id`: UNIQUE (`customers.external_customer_id`)
- `uq_customers_razorpay_customer_id`: UNIQUE (`customers.razorpay_customer_id`)
- `uq_subscriptions_razorpay_subscription_id`: UNIQUE (`subscriptions.razorpay_subscription_id`)
- `uq_payments_razorpay_order_id`: UNIQUE (`payments.razorpay_order_id`)
- `uq_payments_razorpay_invoice_id`: UNIQUE (`payments.razorpay_invoice_id`)
- `uq_payment_attempts_razorpay_payment_id`: UNIQUE (`payment_attempts.razorpay_payment_id`)
- `uq_payment_attempt_seq`: UNIQUE (`payment_attempts.payment_id`, `payment_attempts.attempt_number`)
- `uq_payment_events_idempotency_key`: UNIQUE (`payment_events.idempotency_key`)
- `uq_payment_events_razorpay_event_id`: UNIQUE (`payment_events.razorpay_event_id`)
- `uq_recovery_actions_action_idempotency_key`: UNIQUE (`recovery_actions.action_idempotency_key`)

### Referential Integrity & Deletion Rules
- `subscriptions.customer_id` &rarr; `customers.id` (`ON DELETE RESTRICT`)
- `payments.customer_id` &rarr; `customers.id` (`ON DELETE RESTRICT`)
- `payments.subscription_id` &rarr; `subscriptions.id` (`ON DELETE SET NULL`)
- `payment_attempts.payment_id` &rarr; `payments.id` (`ON DELETE CASCADE`)
- `payment_events.payment_id` &rarr; `payments.id` (`ON DELETE SET NULL`)
- `recovery_cases.payment_id` &rarr; `payments.id` (`ON DELETE RESTRICT`)
- `recovery_cases.customer_id` &rarr; `customers.id` (`ON DELETE RESTRICT`)
- `ml_predictions.recovery_case_id` &rarr; `recovery_cases.id` (`ON DELETE CASCADE`)
- `agent_decisions.recovery_case_id` &rarr; `recovery_cases.id` (`ON DELETE CASCADE`)
- `agent_decisions.ml_prediction_id` &rarr; `ml_predictions.id` (`ON DELETE SET NULL`)
- `policy_decisions.recovery_case_id` &rarr; `recovery_cases.id` (`ON DELETE CASCADE`)
- `policy_decisions.agent_decision_id` &rarr; `agent_decisions.id` (`ON DELETE SET NULL`)
- `recovery_actions.recovery_case_id` &rarr; `recovery_cases.id` (`ON DELETE RESTRICT`)
- `recovery_actions.policy_decision_id` &rarr; `policy_decisions.id` (`ON DELETE RESTRICT`)
- `action_results.recovery_action_id` &rarr; `recovery_actions.id` (`ON DELETE CASCADE`)
- `audit_logs.recovery_case_id` &rarr; `recovery_cases.id` (`ON DELETE SET NULL`)

---

## 4. Performance Indexing Matrix

| Table | Index Name | Columns Indexed | Purpose |
| :--- | :--- | :--- | :--- |
| `subscriptions` | `idx_subscriptions_customer_id` | `customer_id` | Foreign key lookup |
| `subscriptions` | `idx_subscriptions_status` | `status` | Active subscription filtering |
| `payments` | `idx_payments_customer_id` | `customer_id` | Foreign key lookup |
| `payments` | `idx_payments_subscription_id` | `subscription_id` | Subscription payments lookup |
| `payments` | `idx_payments_status_created` | `(status, created_at)` | Composite index for status queries |
| `payment_attempts` | `idx_payment_attempts_payment_id` | `payment_id` | Attempt history lookup |
| `payment_attempts` | `idx_payment_attempts_error_reason` | `error_reason` | Error pattern analytics |
| `payment_events` | `idx_payment_events_type_status` | `(event_type, processing_status)` | Webhook ingestion queue processing |
| `payment_events` | `idx_payment_events_payment_id` | `payment_id` | Event reconciliation by payment |
| `recovery_cases` | `idx_recovery_cases_payment_id` | `payment_id` | Payment case lookup |
| `recovery_cases` | `idx_recovery_cases_customer_id` | `customer_id` | Customer case history |
| `recovery_cases` | `idx_recovery_cases_status_next_action`| `(status, next_action_due_at)` | Worker cron polling for scheduled cases |
| `recovery_cases` | `idx_recovery_cases_opened_at` | `opened_at` | Aging case queries and SLA monitoring |
| `ml_predictions` | `idx_ml_predictions_case_id` | `recovery_case_id` | Case predictions retrieval |
| `ml_predictions` | `idx_ml_predictions_model_version` | `(model_name, model_version)` | Model telemetry and A/B tracking |
| `agent_decisions` | `idx_agent_decisions_case_id` | `recovery_case_id` | Decision history retrieval |
| `agent_decisions` | `idx_agent_decisions_action_type` | `proposed_action_type` | Action distribution analytics |
| `agent_decisions` | `idx_agent_decisions_decided_at` | `decided_at` | Time-series decision querying |
| `agent_decisions` | `idx_agent_decisions_ml_prediction_id`| `ml_prediction_id` | Lineage linking to ML score |
| `policy_decisions` | `idx_policy_decisions_case_id` | `recovery_case_id` | Policy history retrieval |
| `policy_decisions` | `idx_policy_decisions_agent_decision_id`| `agent_decision_id` | Lineage linking to Agent proposal |
| `policy_decisions` | `idx_policy_decisions_result` | `evaluation_result` | Blocked/Allowed rate reporting |
| `policy_decisions` | `idx_policy_decisions_rule_code` | `triggered_rule_code` | Guardrail trigger analytics |
| `recovery_actions` | `idx_recovery_actions_case_id` | `recovery_case_id` | Action history retrieval |
| `recovery_actions` | `idx_recovery_actions_policy_decision_id`| `policy_decision_id` | Lineage linking to policy approval |
| `recovery_actions` | `idx_recovery_actions_status_scheduled`| `(status, scheduled_for)` | Action scheduler dispatcher queue |
| `action_results` | `idx_action_results_action_id` | `recovery_action_id` | Telemetry lookup per action |
| `action_results` | `idx_action_results_provider_ref`| `provider_reference_id` | External provider webhook reconciliation |
| `action_results` | `idx_action_results_status` | `execution_status` | Execution success/failure monitoring |
| `audit_logs` | `idx_audit_logs_case_id` | `recovery_case_id` | Case audit trail |
| `audit_logs` | `idx_audit_logs_entity` | `(entity_type, entity_id)` | Entity-level audit timeline |
| `audit_logs` | `idx_audit_logs_event_type` | `event_type` | Event category reporting |
| `audit_logs` | `idx_audit_logs_created_at` | `created_at` | Chronological audit queries |

---

## 5. Key Design Decisions

1. **Deterministic Separation of Roles**:
   - `ml_predictions` records purely statistical recovery predictions.
   - `agent_decisions` records autonomous LLM cognitive reasoning and proposals.
   - `policy_decisions` strictly validates proposed actions against deterministic guardrails.
   - `recovery_actions` represents concrete authorized dispatch events with unique `action_idempotency_key`.
   - `action_results` stores telemetry returned by downstream providers.

2. **Idempotency Architecture**:
   - `payment_events.idempotency_key`: Deduplicates inbound webhook requests at the gateway boundary.
   - `recovery_actions.action_idempotency_key`: Authoritative application-level idempotency preventing duplicate recovery execution. Where downstream Razorpay APIs support idempotency headers, it acts as an additional defense-in-depth safeguard.

3. **Audit Log Decoupling**:
   - `audit_logs.recovery_case_id` is explicitly nullable with `ON DELETE SET NULL`, allowing the audit ledger to record system initialization, webhook ingestion, customer syncing, or admin changes occurring before or outside a recovery case context.

4. **Monetary Precision & Type Dialects**:
   - All amounts are integers in minor currency units (paise/cents), avoiding float rounding errors.
   - Dialect variants (`JSONB().with_variant(JSON, "sqlite")` and `BigInteger().with_variant(Integer, "sqlite")`) ensure full production compatibility with PostgreSQL 16 Alpine while supporting in-memory SQLite for test suites.

---

## 6. Migration & Database Setup Instructions

### Environment Configuration
Ensure `.env` contains:
```env
POSTGRES_DB=recoveriq
POSTGRES_USER=recoveriq
POSTGRES_PASSWORD=change-me
DATABASE_URL=postgresql://recoveriq:change-me@localhost:5432/recoveriq
```

### Running Migrations
To apply the initial schema migration:
```powershell
cd backend
alembic upgrade head
```

To roll back the migration:
```powershell
alembic downgrade base
```

To run the database test suite:
```powershell
pytest tests/test_database.py -v
```
