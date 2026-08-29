import re
from datetime import UTC, datetime
from typing import Any

from app.agent.schemas import (
    AgentContextPayload,
    CustomerProfileContext,
    MLPredictionContext,
    PaymentAttemptContext,
    PaymentContext,
    RecoveryCaseContext,
)
from app.models import (
    Customer,
    MLPrediction,
    Payment,
    PaymentAttempt,
    RecoveryCase,
)

# Forbidden sensitive keywords in context keys or data
FORBIDDEN_PII_AND_SECRET_KEYS = {
    "email",
    "phone",
    "contact",
    "card_number",
    "pan",
    "cvv",
    "cvc",
    "pin",
    "password",
    "secret",
    "token",
    "api_key",
    "secret_key",
    "private_key",
    "auth_token",
    "access_token",
    "webhook_secret",
    "authorization",
    "cookie",
    "signature",
}

FORBIDDEN_KEY_SUBSTRINGS = {
    "password",
    "secret",
    "cvv",
    "cvc",
    "api_key",
    "auth_token",
    "access_token",
    "private_key",
}

# Regex patterns for accidental PII or credential leaks in values
EMAIL_PATTERN = re.compile(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+")
CARD_PATTERN = re.compile(r"\b(?:\d[ -]*?){13,19}\b")
UUID_PATTERN = re.compile(
    r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$"
)
SECRET_TOKEN_PATTERN = re.compile(
    r"(?:sk_live_|sk_test_|rzp_live_|rzp_test_|Bearer\s+|eyJh)[A-Za-z0-9_\-\.]{8,}"
)


def validate_zero_pii_and_secrets(data: Any, path: str = "root") -> None:
    """
    Recursively traverse data structures to assert zero PII or credentials exist.
    Fails closed by raising ValueError if any forbidden keyword or pattern is found.
    """
    if isinstance(data, dict):
        for k, v in data.items():
            key_str = str(k).lower()
            current_path = f"{path}.{k}"
            is_forbidden = (
                key_str in FORBIDDEN_PII_AND_SECRET_KEYS
                or any(sub in key_str for sub in FORBIDDEN_KEY_SUBSTRINGS)
                or key_str.startswith("card_")
            )
            if is_forbidden:
                raise ValueError(
                    f"Zero-PII / Secret violation: Forbidden key '{k}' "
                    f"at {current_path}"
                )
            validate_zero_pii_and_secrets(v, current_path)
    elif isinstance(data, list | tuple | set):
        for i, item in enumerate(data):
            validate_zero_pii_and_secrets(item, f"{path}[{i}]")
    elif isinstance(data, str):
        # Value content inspections
        if EMAIL_PATTERN.search(data):
            raise ValueError(
                f"Zero-PII violation: Email-like value detected at {path}"
            )
        # Avoid false positives on standard UUIDs/timestamps by checking UUID pattern first
        if not UUID_PATTERN.match(data):
            digits_only = re.sub(r"\D", "", data)
            if len(digits_only) >= 13 and CARD_PATTERN.search(data):
                raise ValueError(
                    f"Zero-PII violation: Card-like number detected at {path}"
                )
        if SECRET_TOKEN_PATTERN.search(data):
            raise ValueError(
                f"Zero-PII violation: Secret/token prefix detected at {path}"
            )


def build_agent_context(
    recovery_case: RecoveryCase,
    payment: Payment,
    customer: Customer,
    attempts: list[PaymentAttempt] | None = None,
    ml_prediction: MLPrediction | None = None,
    as_of: datetime | None = None,
) -> AgentContextPayload:
    """
    Deterministically construct the zero-PII input context for the AI Recovery Agent.

    Guarantees:
    - Pure functional transformation without side effects or ORM mutation.
    - Zero PII (emails, phones, customer names, cards, tokens) included.
    - Deterministic ordering of historical attempts.
    - Timezone-safe calculations in UTC.
    """
    eval_time = as_of or datetime.now(UTC)
    if eval_time.tzinfo is None:
        eval_time = eval_time.replace(tzinfo=UTC)

    # 1. Temporal calculations
    opened_at = recovery_case.opened_at
    if opened_at.tzinfo is None:
        opened_at = opened_at.replace(tzinfo=UTC)

    elapsed_seconds = max(0.0, (eval_time - opened_at).total_seconds())
    hours_since_failure = round(elapsed_seconds / 3600.0, 2)

    # 2. RecoveryCase Context
    currency_val = (
        recovery_case.payment.currency
        if recovery_case.payment
        else payment.currency
    )
    case_ctx = RecoveryCaseContext(
        case_id=str(recovery_case.id),
        status=str(recovery_case.status),
        recovery_stage=str(recovery_case.recovery_stage),
        amount_at_risk=recovery_case.amount_at_risk,
        currency=currency_val,
        total_attempts_count=max(0, recovery_case.total_attempts_count),
        max_allowed_attempts=max(1, recovery_case.max_allowed_attempts),
        opened_at=opened_at.isoformat(),
        latest_failure_reason=recovery_case.latest_failure_reason,
        hours_since_failure=hours_since_failure,
    )

    # 3. Payment & Subscription Context
    is_sub = bool(payment.subscription_id or payment.subscription)
    billing_cadence = None
    sub_age_days = 0

    if payment.subscription:
        if payment.subscription.billing_cadence:
            billing_cadence = str(payment.subscription.billing_cadence)
        if payment.subscription.created_at:
            sub_created = payment.subscription.created_at
            if sub_created.tzinfo is None:
                sub_created = sub_created.replace(tzinfo=UTC)
            sub_age_days = max(0, (eval_time - sub_created).days)

    payment_ctx = PaymentContext(
        payment_id=str(payment.id),
        amount=payment.amount,
        currency=payment.currency,
        is_subscription=is_sub,
        billing_cadence=billing_cadence,
    )

    # 4. Customer Profile Context (Aggregated statistics only)
    total_cust_payments = max(0, customer.total_payments_count)
    failed_cust_payments = max(0, customer.failed_payments_count)
    successful_cust_payments = max(0, total_cust_payments - failed_cust_payments)

    if total_cust_payments > 0:
        success_rate = round(successful_cust_payments / total_cust_payments, 4)
    else:
        success_rate = 0.50

    customer_ctx = CustomerProfileContext(
        customer_id=str(customer.id),
        risk_tier=str(customer.risk_tier),
        total_payments_count=total_cust_payments,
        successful_payments_count=successful_cust_payments,
        failed_payments_count=failed_cust_payments,
        historical_success_rate=success_rate,
    )

    # 5. ML Prediction Context (if available)
    ml_ctx = None
    if ml_prediction is not None:
        snapshot = ml_prediction.feature_vector_snapshot or {}
        risk_score = snapshot.get(
            "risk_score",
            round(1.0 - float(ml_prediction.recovery_probability), 4),
        )
        confidence = snapshot.get("confidence", 0.50)
        priority = snapshot.get("priority", "UNKNOWN")

        ml_ctx = MLPredictionContext(
            prediction_id=str(ml_prediction.id),
            model_name=ml_prediction.model_name,
            model_version=ml_prediction.model_version,
            recovery_probability=float(ml_prediction.recovery_probability),
            risk_score=float(risk_score),
            confidence=float(confidence),
            priority=str(priority),
            predicted_channel=ml_prediction.predicted_channel,
            predicted_delay_hours=ml_prediction.predicted_delay_hours,
        )

    # 6. Payment Attempts History Context (Filtered <= eval_time and sorted)
    attempt_contexts: list[PaymentAttemptContext] = []
    if attempts:
        valid_attempts = []
        for a in attempts:
            init_at = a.initiated_at
            if init_at is None:
                valid_attempts.append(a)
            else:
                if init_at.tzinfo is None:
                    init_at = init_at.replace(tzinfo=UTC)
                if init_at <= eval_time:
                    valid_attempts.append(a)

        # Sort ascending by attempt number
        valid_attempts.sort(key=lambda a: a.attempt_number)

        for a in valid_attempts:
            init_str = None
            if a.initiated_at:
                init_dt = a.initiated_at
                if init_dt.tzinfo is None:
                    init_dt = init_dt.replace(tzinfo=UTC)
                init_str = init_dt.isoformat()

            attempt_contexts.append(
                PaymentAttemptContext(
                    attempt_number=a.attempt_number,
                    amount=a.amount,
                    status=str(a.status),
                    error_code=a.error_code,
                    error_source=a.error_source,
                    error_step=a.error_step,
                    error_reason=a.error_reason,
                    error_description=a.error_description,
                    initiated_at=init_str,
                )
            )

    # 7. Build complete aggregated payload
    payload = AgentContextPayload(
        recovery_case=case_ctx,
        payment=payment_ctx,
        customer_profile=customer_ctx,
        ml_prediction=ml_ctx,
        attempt_history=attempt_contexts,
        subscription_age_days=sub_age_days,
    )

    # 8. Assert zero PII / secrets in final payload dict
    validate_zero_pii_and_secrets(payload.model_dump())

    return payload
