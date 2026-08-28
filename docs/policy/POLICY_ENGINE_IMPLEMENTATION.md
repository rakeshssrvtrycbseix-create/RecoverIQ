# Phase 6C — Deterministic Policy Engine Implementation

## 1. Executive Summary & Objective

The **Deterministic Policy Engine** is the authoritative safety and compliance gatekeeper of RecoverIQ. Positioned between the advisory AI Recovery Decision Engine (Phase 6B) and the operational Recovery Action Scheduler (Phase 7), the Policy Engine enforces hard mathematical, financial, and regulatory guardrails on every proposed recovery strategy.

### Core Architectural Mandate
- **The Policy Engine is Authoritative**: AI Agent recommendations are purely advisory. No recovery action can ever be executed or scheduled without explicit authorization from the Policy Engine.
- **100% Deterministic & Non-LLM**: Rules are evaluated via pure procedural logic with zero LLM inference, zero randomness, and zero network calls.
- **Untrusted Input Model**: The AI Agent's `suggested_payload` and `reasoning_summary` are treated as untrusted data.
- **Zero Financial Execution**: The Policy Engine does not create `RecoveryAction` records, execute payments, or interact with Razorpay APIs.

---

## 2. Architecture & Data Flow

```mermaid
flowchart TD
    AD[AgentDecision Record] --> PE[PolicyEngine Service]
    
    subgraph Data [Aggregate Context]
        RC[RecoveryCase]
        PAY[Payment]
        CUST[Customer Profile]
        ATT[Payment Attempts History]
    end
    
    Data --> PE
    
    subgraph Rules [Precedence-Ordered Rules (policy_v1.0)]
        R1[1. POL-CASE-RESOLVED] --> R2[2. POL-RISK-TIER]
        R2 --> R3[3. POL-MAX-ATTEMPTS]
        R3 --> R4[4. POL-PERM-FAIL]
        R4 --> R5[5. POL-RATE-LIMIT]
        R5 --> R6[6. POL-HIGH-VALUE]
        R6 --> R7[7. POL-CONF-FLOOR]
    end
    
    PE --> Rules
    
    subgraph Outcomes [Authoritative Policy Outcomes]
        Allowed[ALLOWED -> Authorized for Phase 7 Scheduling]
        Blocked[BLOCKED -> Action Forbidden / Discarded]
        Review[HUMAN_REVIEW -> Flagged for Operator Queue]
    end
    
    Rules --> Outcomes
    
    Outcomes --> PD[(policy_decisions Table)]
    Outcomes --> AL[(audit_logs Table)]
```

---

## 3. Deterministic Safety Rules Matrix

| Rule Code | Rule Name | Trigger Condition | Applicable Actions | Authoritative Result |
| :--- | :--- | :--- | :--- | :--- |
| `POL-CASE-RESOLVED` | Terminal Case Guard | `RecoveryCase.status` in `[RECOVERED, CLOSED]` | All Actions | `BLOCKED` |
| `POL-RISK-TIER` | Blocked Customer Gate | `Customer.risk_tier == 'BLOCKED'` | All Actions | `BLOCKED` |
| `POL-MAX-ATTEMPTS` | Maximum Attempts Ceiling | `case.total_attempts_count >= 3` | `RETRY_PAYMENT` | `BLOCKED` |
| `POL-PERM-FAIL` | Permanent Failure Guard | `latest_failure_reason` in permanent card/bank failure set | `RETRY_PAYMENT` | `BLOCKED` |
| `POL-RATE-LIMIT` | Cool-Down Rate Limit Guard | Elapsed time since latest attempt $< 2$ hours ($7200$s) | `RETRY_PAYMENT` | `BLOCKED` |
| `POL-HIGH-VALUE` | High-Value Transaction Gate | `Payment.amount >= 5000000` (₹50,000) | `RETRY_PAYMENT` | `HUMAN_REVIEW` |
| `POL-CONF-FLOOR` | Low AI Confidence Gate | `AgentDecision.confidence_score < 0.40` | All Actions | `HUMAN_REVIEW` |
| *Default* | Standard Clearance | All safety rules passed | All Actions | `ALLOWED` |

---

## 4. Rule Precedence & Action Applicability

### 4.1 Strict Precedence Order
When multiple conditions match, the Policy Engine resolves the single highest-precedence rule:
1. **`POL-CASE-RESOLVED`**: If a debt is already paid or closed, all further money movement is immediately blocked.
2. **`POL-RISK-TIER`**: Fraudulent or blocked customers cannot receive retries, links, or notifications.
3. **`POL-MAX-ATTEMPTS`**: Hard cap on payment attempts to prevent card network penalties.
4. **`POL-PERM-FAIL`**: Unusable payment credentials (`card_blocked`, `account_closed`) cannot be retried.
5. **`POL-RATE-LIMIT`**: Enforces a minimum 2-hour cooldown period between gateway payment calls.
6. **`POL-HIGH-VALUE`**: High-exposure transactions ($\ge ₹50,000$) require human operator sign-off.
7. **`POL-CONF-FLOOR`**: Low-confidence AI suggestions are escalated for operator inspection.

### 4.2 Action-Aware Applicability
Rules only apply to actions where the risk is relevant:
- `POL-PERM-FAIL` blocks direct `RETRY_PAYMENT`, but permits `SEND_PAYMENT_LINK` (enabling the customer to enter a new card).
- `POL-RATE-LIMIT` blocks automated `RETRY_PAYMENT`, but permits non-charging communications (`SEND_NOTIFICATION`, `ESCALATE_HUMAN`).

---

## 5. Persistence, Immutability & Audit Trail

### 5.1 `policy_decisions`
Every policy evaluation writes an immutable relational record:
- `recovery_case_id`: UUID of active recovery case.
- `agent_decision_id`: UUID of evaluated `AgentDecision`.
- `evaluation_result`: String (`ALLOWED`, `BLOCKED`, `HUMAN_REVIEW`).
- `policy_engine_version`: `"policy_v1.0"`.
- `triggered_rule_code`: E.g. `"POL-RATE-LIMIT"` (or `None` if allowed).
- `rule_name`: Human-readable name (or `None`).
- `evaluation_details`: JSON snapshot of evaluated thresholds and metrics.
- `decision_reason`: Authoritative textual justification.
- `decided_at`: UTC timestamp.

### 5.2 `audit_logs`
An audit record is created in the same database transaction:
- `event_type`: `"POLICY_DECISION_EVALUATED"`
- `actor_type`: `AuditActorType.POLICY_ENGINE.value` (`"POLICY_ENGINE"`)
- `actor_id`: `"policy_engine_v1"`
- `recovery_case_id`: Case UUID
- `entity_type`: `"policy_decisions"`
- `entity_id`: Created `PolicyDecision` UUID
- `action`: `"EVALUATE_POLICY"`
- `new_state`: Evaluation outcome, triggered rule code, and version.

---

## 6. Phase 7 Operational Boundary

The Policy Engine terminates the decision lifecycle (Phase 6):
1. Phase 6A: Assembles Zero-PII Context.
2. Phase 6B: Generates Advisory AI Recommendation (`AgentDecision`).
3. Phase 6C: Evaluates Deterministic Policy Guardrails (`PolicyDecision`).
4. **Phase 7 (Future)**: Will read `PolicyDecision` rows with `evaluation_result == 'ALLOWED'` and schedule authorized `RecoveryAction` tasks in background workers.
