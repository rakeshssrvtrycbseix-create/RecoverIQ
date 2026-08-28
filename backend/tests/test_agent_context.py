import uuid
from datetime import UTC, datetime
from decimal import Decimal

import pytest
from pydantic import ValidationError
from sqlalchemy.orm import Session

from app.agent.context_builder import (
    build_agent_context,
    validate_zero_pii_and_secrets,
)
from app.agent.schemas import AgentDecisionOutput
from app.models import (
    Customer,
    CustomerRiskTier,
    MLPrediction,
    Payment,
    PaymentAttempt,
    PaymentAttemptStatus,
    PaymentStatus,
    RecoveryActionType,
    RecoveryCase,
    RecoveryCaseStatus,
    RecoveryStage,
    Subscription,
    SubscriptionStatus,
)


def create_agent_fixtures(
    db_session: Session,
    include_subscription: bool = True,
    include_ml_prediction: bool = True,
) -> tuple[Customer, Payment, RecoveryCase, list[PaymentAttempt], MLPrediction | None]:
    """Helper to provision test database entities for context builder."""
    customer = Customer(
        external_customer_id=f"cust_agent_{uuid.uuid4().hex[:8]}",
        email_masked="a***t@example.com",
        phone_masked="+91******9999",
        risk_tier=CustomerRiskTier.STANDARD.value,
        total_payments_count=6,
        failed_payments_count=1,
        recovered_payments_count=5,
    )
    db_session.add(customer)
    db_session.flush()

    subscription = None
    if include_subscription:
        subscription = Subscription(
            customer_id=customer.id,
            razorpay_subscription_id=f"sub_agent_{uuid.uuid4().hex[:8]}",
            plan_name="Pro Monthly Plan",
            recurring_amount=249900,
            billing_cadence="MONTHLY",
            status=SubscriptionStatus.ACTIVE.value,
        )
        db_session.add(subscription)
        db_session.flush()

    payment = Payment(
        customer_id=customer.id,
        subscription_id=subscription.id if subscription else None,
        razorpay_order_id=f"order_agent_{uuid.uuid4().hex[:8]}",
        amount=249900,
        currency="INR",
        status=PaymentStatus.FAILED.value,
    )
    db_session.add(payment)
    db_session.flush()

    attempt = PaymentAttempt(
        payment_id=payment.id,
        attempt_number=1,
        amount=249900,
        status=PaymentAttemptStatus.FAILED.value,
        error_code="BAD_REQUEST_ERROR",
        error_source="bank",
        error_step="payment_authorization",
        error_reason="insufficient_funds",
        error_description="Card balance too low",
    )
    db_session.add(attempt)
    db_session.flush()

    case = RecoveryCase(
        payment_id=payment.id,
        customer_id=customer.id,
        status=RecoveryCaseStatus.OPEN.value,
        recovery_stage=RecoveryStage.INITIAL_FAILURE.value,
        amount_at_risk=249900,
        recovered_amount=0,
        total_attempts_count=1,
        max_allowed_attempts=3,
        latest_failure_reason="insufficient_funds",
    )
    db_session.add(case)
    db_session.flush()

    ml_prediction = None
    if include_ml_prediction:
        ml_prediction = MLPrediction(
            recovery_case_id=case.id,
            model_name="recovery_probability",
            model_version="v1.0",
            recovery_probability=Decimal("0.8500"),
            predicted_channel="SMART_RETRY",
            predicted_delay_hours=2,
            feature_vector_snapshot={
                "risk_score": 0.1500,
                "confidence": 0.90,
                "priority": "HIGH_RECOVERY_POTENTIAL",
            },
        )
        db_session.add(ml_prediction)
        db_session.flush()

    db_session.commit()
    db_session.refresh(case)
    db_session.refresh(payment)
    db_session.refresh(customer)
    if ml_prediction:
        db_session.refresh(ml_prediction)

    return customer, payment, case, [attempt], ml_prediction


# =========================================================================
# Context Construction Tests
# =========================================================================


def test_build_agent_context_valid_full_aggregate(db_session: Session):
    """Test standard context construction with full subscription and ML data."""
    customer, payment, case, attempts, ml_pred = create_agent_fixtures(
        db_session, include_subscription=True, include_ml_prediction=True
    )

    payload = build_agent_context(
        recovery_case=case,
        payment=payment,
        customer=customer,
        attempts=attempts,
        ml_prediction=ml_pred,
    )

    # 1. RecoveryCase context checks
    assert payload.recovery_case.case_id == str(case.id)
    assert payload.recovery_case.status == RecoveryCaseStatus.OPEN.value
    assert payload.recovery_case.amount_at_risk == 249900
    assert payload.recovery_case.currency == "INR"
    assert payload.recovery_case.total_attempts_count == 1
    assert payload.recovery_case.max_allowed_attempts == 3
    assert payload.recovery_case.latest_failure_reason == "insufficient_funds"

    # 2. Payment context checks
    assert payload.payment.payment_id == str(payment.id)
    assert payload.payment.amount == 249900
    assert payload.payment.currency == "INR"
    assert payload.payment.is_subscription is True
    assert payload.payment.billing_cadence == "MONTHLY"

    # 3. Customer profile checks
    assert payload.customer_profile.customer_id == str(customer.id)
    assert payload.customer_profile.risk_tier == CustomerRiskTier.STANDARD.value
    assert payload.customer_profile.total_payments_count == 6
    assert payload.customer_profile.successful_payments_count == 5
    assert payload.customer_profile.failed_payments_count == 1
    assert payload.customer_profile.historical_success_rate == round(5 / 6, 4)

    # 4. ML prediction checks
    assert payload.ml_prediction is not None
    assert payload.ml_prediction.recovery_probability == 0.85
    assert payload.ml_prediction.risk_score == 0.15
    assert payload.ml_prediction.confidence == 0.90
    assert payload.ml_prediction.priority == "HIGH_RECOVERY_POTENTIAL"
    assert payload.ml_prediction.predicted_channel == "SMART_RETRY"
    assert payload.ml_prediction.predicted_delay_hours == 2

    # 5. Attempts history checks
    assert len(payload.attempt_history) == 1
    assert payload.attempt_history[0].attempt_number == 1
    assert payload.attempt_history[0].error_reason == "insufficient_funds"


def test_build_agent_context_missing_optional_subscription(db_session: Session):
    """Test context construction when payment is a one-off order (no subscription)."""
    customer, payment, case, attempts, ml_pred = create_agent_fixtures(
        db_session, include_subscription=False, include_ml_prediction=True
    )

    payload = build_agent_context(
        recovery_case=case,
        payment=payment,
        customer=customer,
        attempts=attempts,
        ml_prediction=ml_pred,
    )

    assert payload.payment.is_subscription is False
    assert payload.payment.billing_cadence is None
    assert payload.subscription_age_days == 0


def test_build_agent_context_missing_ml_prediction(db_session: Session):
    """Test context construction when ML prediction is not yet computed."""
    customer, payment, case, attempts, _ = create_agent_fixtures(
        db_session, include_subscription=True, include_ml_prediction=False
    )

    payload = build_agent_context(
        recovery_case=case,
        payment=payment,
        customer=customer,
        attempts=attempts,
        ml_prediction=None,
    )

    assert payload.ml_prediction is None
    assert payload.recovery_case.case_id == str(case.id)


def test_build_agent_context_is_strictly_deterministic(db_session: Session):
    """Test that identical input parameters produce identical context dicts."""
    customer, payment, case, attempts, ml_pred = create_agent_fixtures(
        db_session, include_subscription=True, include_ml_prediction=True
    )

    fixed_time = datetime(2026, 8, 28, 12, 0, 0, tzinfo=UTC)

    ctx1 = build_agent_context(
        case, payment, customer, attempts, ml_pred, as_of=fixed_time
    )
    ctx2 = build_agent_context(
        case, payment, customer, attempts, ml_pred, as_of=fixed_time
    )

    assert ctx1.model_dump() == ctx2.model_dump()


def test_build_agent_context_handles_incomplete_or_new_customer(
    db_session: Session,
):
    """Test handling of customer with 0 payments and empty attempts."""
    customer = Customer(
        external_customer_id="cust_zero_001",
        total_payments_count=0,
        failed_payments_count=0,
    )
    db_session.add(customer)
    db_session.flush()

    payment = Payment(
        customer_id=customer.id,
        amount=100000,
        currency="INR",
        status=PaymentStatus.FAILED.value,
    )
    db_session.add(payment)
    db_session.flush()

    case = RecoveryCase(
        payment_id=payment.id,
        customer_id=customer.id,
        amount_at_risk=100000,
        total_attempts_count=0,
    )
    db_session.add(case)
    db_session.commit()

    payload = build_agent_context(case, payment, customer, attempts=[])

    assert payload.customer_profile.total_payments_count == 0
    assert payload.customer_profile.historical_success_rate == 0.50
    assert payload.attempt_history == []


# =========================================================================
# Zero-PII & Secret Rejection Guard Tests
# =========================================================================


def test_validate_zero_pii_rejects_email_and_contact():
    """Test that validate_zero_pii_and_secrets rejects emails and phone keywords."""
    with pytest.raises(
        ValueError, match="Zero-PII / Secret violation: Forbidden key 'email'"
    ):
        validate_zero_pii_and_secrets({"email": "user@example.com"})

    with pytest.raises(
        ValueError, match="Zero-PII / Secret violation: Forbidden key 'phone'"
    ):
        validate_zero_pii_and_secrets({"phone": "+919876543210"})

    with pytest.raises(
        ValueError, match="Zero-PII violation: Email-like value detected"
    ):
        validate_zero_pii_and_secrets(
            {"notes": "contact customer at support@example.com"}
        )


def test_validate_zero_pii_rejects_secrets_and_cards():
    """Test that validate_zero_pii_and_secrets rejects API keys and card numbers."""
    with pytest.raises(
        ValueError, match="Zero-PII / Secret violation: Forbidden key 'cvv'"
    ):
        validate_zero_pii_and_secrets({"cvv": "123"})

    with pytest.raises(
        ValueError,
        match="Zero-PII / Secret violation: Forbidden key 'webhook_secret'",
    ):
        validate_zero_pii_and_secrets({"webhook_secret": "whsec_test12345"})

    with pytest.raises(
        ValueError, match="Zero-PII violation: Secret/token prefix detected"
    ):
        validate_zero_pii_and_secrets(
            {"auth_header": "Bearer rzp_live_abcdef123456"}
        )

    with pytest.raises(
        ValueError, match="Zero-PII violation: Card-like number detected"
    ):
        validate_zero_pii_and_secrets(
            {"custom_note": "4111 1111 1111 1111"}
        )


def test_validate_zero_pii_rejects_nested_structures():
    """Test that deeply nested forbidden keys or values are detected and rejected."""
    nested_data = {
        "metadata": {
            "level1": {
                "level2": [{"item_tag": "safe"}, {"api_key": "secret_val"}]
            }
        }
    }
    with pytest.raises(
        ValueError, match="Zero-PII / Secret violation: Forbidden key 'api_key'"
    ):
        validate_zero_pii_and_secrets(nested_data)


# =========================================================================
# Agent Decision Output Schema Tests
# =========================================================================


def test_agent_decision_output_schema_validation():
    """Test AgentDecisionOutput validates allowed fields and rejects out-of-bounds."""
    valid_output = AgentDecisionOutput(
        proposed_action_type=RecoveryActionType.RETRY_PAYMENT,
        confidence_score=0.85,
        reasoning_summary="Soft failure due to insufficient funds; high history.",
        suggested_payload={"channel": "GATEWAY_API", "target": "GATEWAY"},
        recommended_delay_hours=2,
    )
    assert (
        valid_output.proposed_action_type == RecoveryActionType.RETRY_PAYMENT
    )
    assert valid_output.confidence_score == 0.85
    assert valid_output.agent_name == "RecoveryOrchestrator"

    # Confidence score > 1.0 rejected
    with pytest.raises(ValidationError):
        AgentDecisionOutput(
            proposed_action_type=RecoveryActionType.RETRY_PAYMENT,
            confidence_score=1.5,
            reasoning_summary="Invalid confidence",
        )

    # Negative delay rejected
    with pytest.raises(ValidationError):
        AgentDecisionOutput(
            proposed_action_type=RecoveryActionType.RETRY_PAYMENT,
            confidence_score=0.8,
            reasoning_summary="Invalid delay",
            recommended_delay_hours=-1,
        )

    # Delay > 168 (1 week) rejected
    with pytest.raises(ValidationError):
        AgentDecisionOutput(
            proposed_action_type=RecoveryActionType.RETRY_PAYMENT,
            confidence_score=0.8,
            reasoning_summary="Excessive delay",
            recommended_delay_hours=200,
        )

    # Unknown action type rejected
    with pytest.raises(ValidationError):
        AgentDecisionOutput(
            proposed_action_type="UNAUTHORIZED_ACTION",  # type: ignore
            confidence_score=0.8,
            reasoning_summary="Illegal action",
        )
