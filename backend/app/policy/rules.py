from datetime import UTC, datetime
from typing import Any

from app.models import (
    AgentDecision,
    Customer,
    CustomerRiskTier,
    Payment,
    PaymentAttempt,
    RecoveryActionType,
    RecoveryCase,
    RecoveryCaseStatus,
)
from app.models.enums import PolicyEvaluationResult
from app.policy.schemas import PolicyEvaluationOutcome

POLICY_ENGINE_VERSION = "policy_v1.0"
HIGH_VALUE_THRESHOLD_PAISE = 5000000  # ₹50,000
CONFIDENCE_FLOOR = 0.4000
COOLDOWN_SECONDS = 7200  # 2 hours

PERMANENT_ERROR_REASONS = {
    "card_blocked",
    "card_inactive",
    "account_closed",
    "fraud_suspected",
    "invalid_card_details",
}


def evaluate_rules(
    case: RecoveryCase,
    payment: Payment,
    customer: Customer,
    agent_decision: AgentDecision,
    attempts: list[PaymentAttempt] | None = None,
    as_of: datetime | None = None,
) -> PolicyEvaluationOutcome:
    """
    Evaluate deterministic safety rules in strict precedence order.

    Rule Precedence Order:
    1. POL-CASE-RESOLVED (Terminal Case Guard) -> BLOCKED
    2. POL-RISK-TIER (Blocked Customer Gate) -> BLOCKED
    3. POL-MAX-ATTEMPTS (Maximum Attempts Ceiling) -> BLOCKED
    4. POL-PERM-FAIL (Permanent Failure Guard) -> BLOCKED
    5. POL-RATE-LIMIT (Cool-Down Rate Limit Guard) -> BLOCKED
    6. POL-HIGH-VALUE (High-Value Transaction Gate) -> HUMAN_REVIEW
    7. POL-CONF-FLOOR (Low AI Confidence Gate) -> HUMAN_REVIEW
    Default: ALLOWED
    """
    eval_time = as_of or datetime.now(UTC)
    if eval_time.tzinfo is None:
        eval_time = eval_time.replace(tzinfo=UTC)

    action_type = str(agent_decision.proposed_action_type)
    conf_score = float(agent_decision.confidence_score)
    failure_reason = (case.latest_failure_reason or "").lower().strip()

    details: dict[str, Any] = {
        "case_id": str(case.id),
        "case_status": str(case.status),
        "customer_risk_tier": str(customer.risk_tier),
        "proposed_action_type": action_type,
        "confidence_score": conf_score,
        "total_attempts_count": case.total_attempts_count,
        "max_allowed_attempts": case.max_allowed_attempts,
        "payment_amount": payment.amount,
        "latest_failure_reason": failure_reason,
    }

    # -------------------------------------------------------------------------
    # RULE 1: POL-CASE-RESOLVED (Precedence 1)
    # -------------------------------------------------------------------------
    if case.status in {
        RecoveryCaseStatus.RECOVERED.value,
        RecoveryCaseStatus.CLOSED.value,
    }:
        return PolicyEvaluationOutcome(
            evaluation_result=PolicyEvaluationResult.BLOCKED,
            policy_engine_version=POLICY_ENGINE_VERSION,
            triggered_rule_code="POL-CASE-RESOLVED",
            rule_name="Terminal Case Guard",
            decision_reason=(
                f"RecoveryCase status is '{case.status}'; "
                "no further recovery actions are permitted."
            ),
            evaluation_details=details,
        )

    # -------------------------------------------------------------------------
    # RULE 2: POL-RISK-TIER (Precedence 2)
    # -------------------------------------------------------------------------
    if customer.risk_tier == CustomerRiskTier.BLOCKED.value:
        return PolicyEvaluationOutcome(
            evaluation_result=PolicyEvaluationResult.BLOCKED,
            policy_engine_version=POLICY_ENGINE_VERSION,
            triggered_rule_code="POL-RISK-TIER",
            rule_name="Blocked Customer Gate",
            decision_reason=(
                "Customer is marked as BLOCKED risk tier; "
                "all recovery actions are prohibited."
            ),
            evaluation_details=details,
        )

    # -------------------------------------------------------------------------
    # RULE 3: POL-MAX-ATTEMPTS (Precedence 3)
    # Applies to retry-based payment attempts
    # -------------------------------------------------------------------------
    if (
        case.total_attempts_count >= case.max_allowed_attempts
        or case.total_attempts_count >= 3
    ) and action_type in {
        RecoveryActionType.RETRY_PAYMENT.value,
        RecoveryActionType.RETRY_PAYMENT,
    }:
        return PolicyEvaluationOutcome(
            evaluation_result=PolicyEvaluationResult.BLOCKED,
            policy_engine_version=POLICY_ENGINE_VERSION,
            triggered_rule_code="POL-MAX-ATTEMPTS",
            rule_name="Maximum Attempts Ceiling",
            decision_reason=(
                f"Maximum payment retry attempts reached "
                f"({case.total_attempts_count}/{case.max_allowed_attempts}); "
                "automated payment retry is blocked."
            ),
            evaluation_details=details,
        )

    # -------------------------------------------------------------------------
    # RULE 4: POL-PERM-FAIL (Precedence 4)
    # Applies to retry actions for permanent card/account failures
    # -------------------------------------------------------------------------
    if (
        failure_reason in PERMANENT_ERROR_REASONS
        and action_type in {
            RecoveryActionType.RETRY_PAYMENT.value,
            RecoveryActionType.RETRY_PAYMENT,
        }
    ):
        return PolicyEvaluationOutcome(
            evaluation_result=PolicyEvaluationResult.BLOCKED,
            policy_engine_version=POLICY_ENGINE_VERSION,
            triggered_rule_code="POL-PERM-FAIL",
            rule_name="Permanent Failure Guard",
            decision_reason=(
                f"Permanent gateway error detected ('{failure_reason}'); "
                "direct payment retry is blocked."
            ),
            evaluation_details=details,
        )

    # -------------------------------------------------------------------------
    # RULE 5: POL-RATE-LIMIT (Precedence 5)
    # Minimum 2-hour cooldown between payment retry attempts
    # -------------------------------------------------------------------------
    if action_type in {
        RecoveryActionType.RETRY_PAYMENT.value,
        RecoveryActionType.RETRY_PAYMENT,
    } and attempts:
        valid_attempts = [
            a for a in attempts
            if a.initiated_at is not None
        ]
        if valid_attempts:
            latest_attempt = max(
                valid_attempts,
                key=lambda a: a.initiated_at or datetime.min.replace(tzinfo=UTC),
            )
            if latest_attempt.initiated_at:
                init_at = latest_attempt.initiated_at
                if init_at.tzinfo is None:
                    init_at = init_at.replace(tzinfo=UTC)
                elapsed_sec = (eval_time - init_at).total_seconds()
                if elapsed_sec < COOLDOWN_SECONDS:
                    elapsed_min = round(elapsed_sec / 60.0, 1)
                    details["elapsed_cooldown_seconds"] = elapsed_sec
                    return PolicyEvaluationOutcome(
                        evaluation_result=PolicyEvaluationResult.BLOCKED,
                        policy_engine_version=POLICY_ENGINE_VERSION,
                        triggered_rule_code="POL-RATE-LIMIT",
                        rule_name="Cool-Down Rate Limit Guard",
                        decision_reason=(
                            f"Retry rate limit active. Only {elapsed_min} minutes "
                            f"elapsed since previous attempt; 120.0 minutes required."
                        ),
                        evaluation_details=details,
                    )

    # -------------------------------------------------------------------------
    # RULE 6: POL-HIGH-VALUE (Precedence 6)
    # Amounts >= ₹50,000 require human operator review for automated retries
    # -------------------------------------------------------------------------
    if (
        payment.amount >= HIGH_VALUE_THRESHOLD_PAISE
        and action_type in {
            RecoveryActionType.RETRY_PAYMENT.value,
            RecoveryActionType.RETRY_PAYMENT,
        }
    ):
        return PolicyEvaluationOutcome(
            evaluation_result=PolicyEvaluationResult.HUMAN_REVIEW,
            policy_engine_version=POLICY_ENGINE_VERSION,
            triggered_rule_code="POL-HIGH-VALUE",
            rule_name="High-Value Transaction Gate",
            decision_reason=(
                f"Transaction amount ₹{payment.amount / 100:.2f} exceeds "
                f"automated retry threshold (₹{HIGH_VALUE_THRESHOLD_PAISE / 100:.2f}); "
                "human operator review required."
            ),
            evaluation_details=details,
        )

    # -------------------------------------------------------------------------
    # RULE 7: POL-CONF-FLOOR (Precedence 7)
    # AI confidence < 0.40 forces human review
    # -------------------------------------------------------------------------
    if conf_score < CONFIDENCE_FLOOR:
        return PolicyEvaluationOutcome(
            evaluation_result=PolicyEvaluationResult.HUMAN_REVIEW,
            policy_engine_version=POLICY_ENGINE_VERSION,
            triggered_rule_code="POL-CONF-FLOOR",
            rule_name="Low AI Confidence Gate",
            decision_reason=(
                f"AI Agent confidence score ({conf_score:.4f}) is below "
                f"safety floor ({CONFIDENCE_FLOOR:.4f}); human review required."
            ),
            evaluation_details=details,
        )

    # -------------------------------------------------------------------------
    # DEFAULT OUTCOME: ALLOWED
    # -------------------------------------------------------------------------
    return PolicyEvaluationOutcome(
        evaluation_result=PolicyEvaluationResult.ALLOWED,
        policy_engine_version=POLICY_ENGINE_VERSION,
        triggered_rule_code=None,
        rule_name=None,
        decision_reason=(
            "Proposed recovery action complies with all deterministic "
            "safety policies and is authorized."
        ),
        evaluation_details=details,
    )
