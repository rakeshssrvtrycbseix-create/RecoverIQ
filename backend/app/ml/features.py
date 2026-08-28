from datetime import UTC, datetime

from app.ml.schemas import RecoveryFeatures
from app.models import Customer, Payment, PaymentAttempt, RecoveryCase

FORBIDDEN_PII_KEYWORDS = {
    "email",
    "phone",
    "contact",
    "card_number",
    "cvv",
    "cvc",
    "pin",
    "password",
    "secret",
    "token",
}


def validate_no_pii_in_features(features_dict: dict) -> None:
    """
    Assert that no raw PII or credentials entered the feature dictionary.
    """
    for key, val in features_dict.items():
        key_lower = str(key).lower()
        if any(keyword in key_lower for keyword in FORBIDDEN_PII_KEYWORDS):
            raise ValueError(
                f"PII violation: Forbidden keyword '{key}' in features"
            )
        if isinstance(val, str):
            val_lower = val.lower()
            if "@" in val_lower and ("." in val_lower or "example" in val_lower):
                raise ValueError(
                    f"PII violation: Email-like value detected in '{key}'"
                )


def extract_features(
    recovery_case: RecoveryCase,
    payment: Payment,
    customer: Customer,
    attempts: list[PaymentAttempt] | None = None,
    as_of: datetime | None = None,
) -> RecoveryFeatures:
    """
    Deterministically extract and validate the feature vector for a RecoveryCase.

    Strict Leakage Guard:
    - Uses only telemetry established at or before `as_of`.
    - Explicitly excludes recovery outcomes, resolved_at, and closed_reason.
    """
    eval_time = as_of or datetime.now(UTC)
    if eval_time.tzinfo is None:
        eval_time = eval_time.replace(tzinfo=UTC)

    # 1. Customer history telemetry
    total_payments = max(0, customer.total_payments_count)
    failed_payments = max(0, customer.failed_payments_count)
    successful_payments = max(0, total_payments - failed_payments)

    if total_payments > 0:
        success_rate = round(successful_payments / total_payments, 4)
    else:
        # Default neutral prior for new customer with no prior transaction history
        success_rate = 0.50

    # 2. Latest attempt gateway telemetry
    error_code = "UNKNOWN"
    error_source = "UNKNOWN"
    error_step = "UNKNOWN"
    error_reason = recovery_case.latest_failure_reason or "UNKNOWN"
    attempt_number = max(1, recovery_case.total_attempts_count)

    if attempts:
        # Filter attempts initiated before or at evaluation time
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

        if valid_attempts:
            latest_attempt = max(valid_attempts, key=lambda a: a.attempt_number)
            attempt_number = latest_attempt.attempt_number
            error_code = latest_attempt.error_code or error_code
            error_source = latest_attempt.error_source or error_source
            error_step = latest_attempt.error_step or error_step
            error_reason = latest_attempt.error_reason or error_reason

    # 3. Temporal calculations
    opened_at = recovery_case.opened_at
    if opened_at.tzinfo is None:
        opened_at = opened_at.replace(tzinfo=UTC)

    elapsed_seconds = max(0.0, (eval_time - opened_at).total_seconds())
    hours_since_failure = round(elapsed_seconds / 3600.0, 2)

    # 4. Subscription age
    subscription_age_days = 0
    if payment.subscription and payment.subscription.created_at:
        sub_created = payment.subscription.created_at
        if sub_created.tzinfo is None:
            sub_created = sub_created.replace(tzinfo=UTC)
        subscription_age_days = max(
            0, (eval_time - sub_created).days
        )

    # 5. Build and validate feature object
    features = RecoveryFeatures(
        payment_amount=payment.amount,
        currency=payment.currency,
        attempt_number=attempt_number,
        customer_total_payments=total_payments,
        customer_successful_payments=successful_payments,
        customer_failed_payments=failed_payments,
        customer_success_rate=success_rate,
        error_code=str(error_code).upper(),
        error_source=str(error_source).lower(),
        error_step=str(error_step).lower(),
        error_reason=str(error_reason).lower(),
        hours_since_failure=hours_since_failure,
        subscription_age_days=subscription_age_days,
        total_attempts_count=max(1, recovery_case.total_attempts_count),
    )

    # Validate no PII in final dictionary
    validate_no_pii_in_features(features.model_dump())

    return features
