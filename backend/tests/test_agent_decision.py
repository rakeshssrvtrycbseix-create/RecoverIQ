import uuid
from decimal import Decimal
from unittest.mock import patch

import pytest
from sqlalchemy.orm import Session

from app.agent.decision_engine import recovery_decision_engine
from app.agent.exceptions import (
    AIProviderError,
    DecisionPersistenceError,
    InvalidAIOutputError,
    RecoveryCaseNotFoundError,
    UnsafeAIOutputError,
)
from app.agent.prompts import PROMPT_VERSION_V1_0
from app.agent.provider import MockAIProvider
from app.agent.schemas import AgentContextPayload, AgentDecisionOutput
from app.agent.validators import validate_agent_decision_output
from app.models import (
    AgentDecision,
    AuditActorType,
    AuditLog,
    Customer,
    CustomerRiskTier,
    MLPrediction,
    Payment,
    PaymentAttempt,
    PaymentAttemptStatus,
    PaymentStatus,
    RecoveryAction,
    RecoveryActionType,
    RecoveryCase,
    RecoveryCaseStatus,
    RecoveryStage,
    Subscription,
    SubscriptionStatus,
)


def create_decision_fixtures(
    db_session: Session,
    amount: int = 199900,
    attempts_count: int = 1,
    failure_reason: str = "insufficient_funds",
    include_ml: bool = True,
    include_sub: bool = True,
) -> tuple[Customer, Payment, RecoveryCase, MLPrediction | None]:
    """Helper to provision test database entities for decision engine tests."""
    customer = Customer(
        external_customer_id=f"cust_dec_{uuid.uuid4().hex[:8]}",
        email_masked="d***n@example.com",
        phone_masked="+91******8888",
        risk_tier=CustomerRiskTier.STANDARD.value,
        total_payments_count=5,
        failed_payments_count=1,
        recovered_payments_count=4,
    )
    db_session.add(customer)
    db_session.flush()

    sub = None
    if include_sub:
        sub = Subscription(
            customer_id=customer.id,
            razorpay_subscription_id=f"sub_dec_{uuid.uuid4().hex[:8]}",
            plan_name="Enterprise Plan",
            recurring_amount=amount,
            billing_cadence="MONTHLY",
            status=SubscriptionStatus.ACTIVE.value,
        )
        db_session.add(sub)
        db_session.flush()

    payment = Payment(
        customer_id=customer.id,
        subscription_id=sub.id if sub else None,
        razorpay_order_id=f"order_dec_{uuid.uuid4().hex[:8]}",
        amount=amount,
        currency="INR",
        status=PaymentStatus.FAILED.value,
    )
    db_session.add(payment)
    db_session.flush()

    attempt = PaymentAttempt(
        payment_id=payment.id,
        attempt_number=attempts_count,
        amount=amount,
        status=PaymentAttemptStatus.FAILED.value,
        error_code="BAD_REQUEST_ERROR",
        error_source="bank",
        error_step="payment_authorization",
        error_reason=failure_reason,
    )
    db_session.add(attempt)
    db_session.flush()

    case = RecoveryCase(
        payment_id=payment.id,
        customer_id=customer.id,
        status=RecoveryCaseStatus.OPEN.value,
        recovery_stage=RecoveryStage.INITIAL_FAILURE.value,
        amount_at_risk=amount,
        recovered_amount=0,
        total_attempts_count=attempts_count,
        max_allowed_attempts=3,
        latest_failure_reason=failure_reason,
    )
    db_session.add(case)
    db_session.flush()

    ml_prediction = None
    if include_ml:
        ml_prediction = MLPrediction(
            recovery_case_id=case.id,
            model_name="recovery_probability",
            model_version="v1.0",
            recovery_probability=Decimal("0.8200"),
            predicted_channel="SMART_RETRY",
            predicted_delay_hours=2,
            feature_vector_snapshot={
                "risk_score": 0.1800,
                "confidence": 0.88,
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

    return customer, payment, case, ml_prediction


# =========================================================================
# 1. Decision Generation & Persistence Tests
# =========================================================================


@pytest.mark.anyio
async def test_valid_ai_decision_generation_and_persistence(
    db_session: Session,
):
    """1, 3, 4, 5, 6, 22. Test valid AI decision generation, persistence, and audit."""
    _, _, case, ml = create_decision_fixtures(db_session)

    decision = await recovery_decision_engine.generate_decision(
        db=db_session,
        recovery_case_id=case.id,
    )

    # 1. Assert AgentDecision attributes
    assert decision is not None
    assert decision.recovery_case_id == case.id
    assert decision.ml_prediction_id == ml.id
    assert decision.prompt_template_version == PROMPT_VERSION_V1_0
    assert decision.proposed_action_type == RecoveryActionType.RETRY_PAYMENT.value
    assert float(decision.confidence_score) == 0.88
    assert "recommended_delay_hours" in decision.suggested_payload
    assert decision.suggested_payload["recommended_delay_hours"] == 2

    # 2. Verify in DB
    stored = db_session.query(AgentDecision).filter_by(id=decision.id).first()
    assert stored is not None
    assert stored.proposed_action_type == RecoveryActionType.RETRY_PAYMENT.value

    # 3. Verify AuditLog created
    audit = (
        db_session.query(AuditLog)
        .filter_by(
            recovery_case_id=case.id,
            entity_id=decision.id,
            event_type="AGENT_DECISION_GENERATED",
        )
        .first()
    )
    assert audit is not None
    assert audit.actor_type == AuditActorType.AI_AGENT.value
    assert audit.actor_id == "RecoverIQ-Agent-v1"
    assert audit.action == "PROPOSE_ACTION"


@pytest.mark.anyio
async def test_deterministic_mock_ai_provider():
    """2. Test MockAIProvider generates strictly deterministic decisions."""
    provider = MockAIProvider()

    # Case 1: Max attempts reached -> HALT_SUBSCRIPTION
    ctx1 = AgentContextPayload(
        recovery_case={
            "case_id": "c1",
            "status": "OPEN",
            "recovery_stage": "INITIAL_FAILURE",
            "amount_at_risk": 1000,
            "currency": "INR",
            "total_attempts_count": 3,
            "max_allowed_attempts": 3,
            "opened_at": "2026-08-28T12:00:00Z",
            "hours_since_failure": 2.0,
        },
        payment={
            "payment_id": "p1",
            "amount": 1000,
            "currency": "INR",
            "is_subscription": True,
        },
        customer_profile={
            "customer_id": "cust1",
            "risk_tier": "STANDARD",
            "total_payments_count": 5,
            "successful_payments_count": 4,
            "failed_payments_count": 1,
            "historical_success_rate": 0.8,
        },
    )
    res1 = await provider.generate_decision(ctx1)
    assert res1.proposed_action_type == RecoveryActionType.HALT_SUBSCRIPTION

    # Case 2: High value -> ESCALATE_HUMAN
    ctx2 = AgentContextPayload(
        recovery_case={
            "case_id": "c2",
            "status": "OPEN",
            "recovery_stage": "INITIAL_FAILURE",
            "amount_at_risk": 6000000,
            "currency": "INR",
            "total_attempts_count": 1,
            "max_allowed_attempts": 3,
            "opened_at": "2026-08-28T12:00:00Z",
            "hours_since_failure": 1.0,
        },
        payment={
            "payment_id": "p2",
            "amount": 6000000,
            "currency": "INR",
            "is_subscription": True,
        },
        customer_profile={
            "customer_id": "cust2",
            "risk_tier": "STANDARD",
            "total_payments_count": 5,
            "successful_payments_count": 4,
            "failed_payments_count": 1,
            "historical_success_rate": 0.8,
        },
    )
    res2 = await provider.generate_decision(ctx2)
    assert res2.proposed_action_type == RecoveryActionType.ESCALATE_HUMAN


@pytest.mark.anyio
async def test_missing_ml_prediction_handling(db_session: Session):
    """7. Test decision engine handles cases with no ML prediction gracefully."""
    _, _, case, _ = create_decision_fixtures(
        db_session, include_ml=False, failure_reason="unknown"
    )

    decision = await recovery_decision_engine.generate_decision(
        db=db_session,
        recovery_case_id=case.id,
    )

    assert decision is not None
    assert decision.ml_prediction_id is None
    assert (
        decision.proposed_action_type
        == RecoveryActionType.SEND_NOTIFICATION.value
    )


@pytest.mark.anyio
async def test_missing_subscription_handling(db_session: Session):
    """8. Test decision engine handles one-off orders without subscriptions."""
    _, _, case, ml = create_decision_fixtures(
        db_session, include_sub=False, include_ml=True
    )

    decision = await recovery_decision_engine.generate_decision(
        db=db_session,
        recovery_case_id=case.id,
    )

    assert decision is not None
    assert decision.recovery_case_id == case.id
    assert decision.ml_prediction_id == ml.id


@pytest.mark.anyio
async def test_repeated_inference_creates_immutable_history(
    db_session: Session,
):
    """19. Test multiple inferences create multiple immutable rows."""
    _, _, case, _ = create_decision_fixtures(db_session)

    d1 = await recovery_decision_engine.generate_decision(
        db=db_session, recovery_case_id=case.id
    )
    d2 = await recovery_decision_engine.generate_decision(
        db=db_session, recovery_case_id=case.id
    )

    assert d1.id != d2.id

    decisions_count = (
        db_session.query(AgentDecision)
        .filter_by(recovery_case_id=case.id)
        .count()
    )
    assert decisions_count == 2


@pytest.mark.anyio
async def test_no_recovery_action_or_gateway_call_created(db_session: Session):
    """20, 21. Test that the AI decision engine NEVER creates RecoveryAction rows."""
    _, _, case, _ = create_decision_fixtures(db_session)

    initial_actions_count = db_session.query(RecoveryAction).count()

    await recovery_decision_engine.generate_decision(
        db=db_session,
        recovery_case_id=case.id,
    )

    final_actions_count = db_session.query(RecoveryAction).count()
    assert final_actions_count == initial_actions_count == 0


@pytest.mark.anyio
async def test_non_existent_case_raises_error(db_session: Session):
    """Test recovery case not found error."""
    fake_id = uuid.uuid4()
    with pytest.raises(RecoveryCaseNotFoundError):
        await recovery_decision_engine.generate_decision(
            db=db_session,
            recovery_case_id=fake_id,
        )


# =========================================================================
# 2. Output Validation & Security Safety Tests
# =========================================================================


def test_invalid_action_type_rejection():
    """9, 10. Test validation rejects unknown/malformed action types."""
    with pytest.raises(InvalidAIOutputError, match="Invalid proposed_action_type"):
        output = AgentDecisionOutput.model_construct(
            proposed_action_type="ILLEGAL_ACTION",  # type: ignore
            confidence_score=0.8,
            reasoning_summary="Valid reasoning text long enough",
            suggested_payload={},
            recommended_delay_hours=0,
        )
        validate_agent_decision_output(output)


def test_confidence_and_delay_bounds_rejection():
    """11, 12. Test validation rejects out-of-bound confidence and delay hours."""
    with pytest.raises(InvalidAIOutputError, match="Confidence score"):
        output = AgentDecisionOutput.model_construct(
            proposed_action_type=RecoveryActionType.RETRY_PAYMENT,
            confidence_score=1.5,
            reasoning_summary="Valid reasoning text long enough",
            suggested_payload={},
            recommended_delay_hours=0,
        )
        validate_agent_decision_output(output)

    with pytest.raises(InvalidAIOutputError, match="Recommended delay"):
        output2 = AgentDecisionOutput.model_construct(
            proposed_action_type=RecoveryActionType.RETRY_PAYMENT,
            confidence_score=0.8,
            reasoning_summary="Valid reasoning text long enough",
            suggested_payload={},
            recommended_delay_hours=200,
        )
        validate_agent_decision_output(output2)


def test_pii_in_reasoning_summary_rejected():
    """13. Test that email or phone in reasoning_summary raises UnsafeAIOutputError."""
    with pytest.raises(UnsafeAIOutputError, match="Email address detected"):
        output = AgentDecisionOutput(
            proposed_action_type=RecoveryActionType.RETRY_PAYMENT,
            confidence_score=0.8,
            reasoning_summary="Customer contacted at user@example.com for payment.",
            suggested_payload={},
            recommended_delay_hours=0,
        )
        validate_agent_decision_output(output)


def test_pii_and_secrets_in_suggested_payload_rejected():
    """14, 15. Test that secrets, cards, and keys in payload are rejected."""
    # 1. API key in payload key
    with pytest.raises(UnsafeAIOutputError, match="Forbidden key 'api_key'"):
        output1 = AgentDecisionOutput(
            proposed_action_type=RecoveryActionType.RETRY_PAYMENT,
            confidence_score=0.8,
            reasoning_summary="Valid reasoning text long enough",
            suggested_payload={"api_key": "sec_12345"},
            recommended_delay_hours=0,
        )
        validate_agent_decision_output(output1)

    # 2. Secret token in payload value
    with pytest.raises(UnsafeAIOutputError, match="Secret token prefix detected"):
        output2 = AgentDecisionOutput(
            proposed_action_type=RecoveryActionType.RETRY_PAYMENT,
            confidence_score=0.8,
            reasoning_summary="Valid reasoning text long enough",
            suggested_payload={"auth": "Bearer rzp_live_998877665544"},
            recommended_delay_hours=0,
        )
        validate_agent_decision_output(output2)

    # 3. Card number in payload value
    with pytest.raises(UnsafeAIOutputError, match="Card-like number detected"):
        output3 = AgentDecisionOutput(
            proposed_action_type=RecoveryActionType.RETRY_PAYMENT,
            confidence_score=0.8,
            reasoning_summary="Valid reasoning text long enough",
            suggested_payload={"note": "Retry card 4111 1111 1111 1111"},
            recommended_delay_hours=0,
        )
        validate_agent_decision_output(output3)


def test_forbidden_credentials_security_sweep():
    """Security test: Explicitly verify all forbidden credential strings are blocked."""
    forbidden_tokens = [
        "user@domain.com",
        "4111111111111111",
        "rzp_live_testsecret123",
        "Bearer eyJhbGciOiJIUzI1NiJ9",
        "webhook_secret",
        "razorpay_key",
        "razorpay_secret",
        "private_key",
    ]

    for token in forbidden_tokens:
        with pytest.raises(UnsafeAIOutputError):
            output = AgentDecisionOutput(
                proposed_action_type=RecoveryActionType.RETRY_PAYMENT,
                confidence_score=0.8,
                reasoning_summary=f"Safe text containing {token}",
                suggested_payload={},
                recommended_delay_hours=0,
            )
            validate_agent_decision_output(output)


# =========================================================================
# 3. Transaction Rollback Tests
# =========================================================================


class FailingProvider:
    """Mock provider that simulates an inference failure."""

    async def generate_decision(
        self, context: AgentContextPayload, prompt_version: str = ""
    ) -> AgentDecisionOutput:
        raise RuntimeError("Provider service timeout")


class UnsafeOutputProvider:
    """Mock provider that returns unsafe PII output."""

    async def generate_decision(
        self, context: AgentContextPayload, prompt_version: str = ""
    ) -> AgentDecisionOutput:
        return AgentDecisionOutput(
            proposed_action_type=RecoveryActionType.RETRY_PAYMENT,
            confidence_score=0.8,
            reasoning_summary="Contact victim at leak@example.com",
            suggested_payload={},
            recommended_delay_hours=0,
        )


@pytest.mark.anyio
async def test_provider_failure_rollback(db_session: Session):
    """16. Test that provider failure rolls back cleanly without persisting rows."""
    _, _, case, _ = create_decision_fixtures(db_session)

    with pytest.raises(AIProviderError):
        await recovery_decision_engine.generate_decision(
            db=db_session,
            recovery_case_id=case.id,
            ai_provider=FailingProvider(),  # type: ignore
        )

    # Assert 0 AgentDecisions exist
    stored_count = (
        db_session.query(AgentDecision)
        .filter_by(recovery_case_id=case.id)
        .count()
    )
    assert stored_count == 0


@pytest.mark.anyio
async def test_validation_failure_rollback(db_session: Session):
    """17. Test that output validation failure rolls back cleanly."""
    _, _, case, _ = create_decision_fixtures(db_session)

    with pytest.raises(UnsafeAIOutputError):
        await recovery_decision_engine.generate_decision(
            db=db_session,
            recovery_case_id=case.id,
            ai_provider=UnsafeOutputProvider(),  # type: ignore
        )

    # Assert 0 AgentDecisions exist
    stored_count = (
        db_session.query(AgentDecision)
        .filter_by(recovery_case_id=case.id)
        .count()
    )
    assert stored_count == 0


@pytest.mark.anyio
async def test_database_failure_rollback(db_session: Session):
    """18. Test that database persistence crash rolls back cleanly."""
    _, _, case, _ = create_decision_fixtures(db_session)

    with patch.object(
        db_session, "commit", side_effect=RuntimeError("Disk crash")
    ):
        with pytest.raises(DecisionPersistenceError):
            await recovery_decision_engine.generate_decision(
                db=db_session,
                recovery_case_id=case.id,
            )
