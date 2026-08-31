import os
import tempfile
import uuid
from decimal import Decimal

import pytest
from alembic.config import Config
from sqlalchemy import inspect, text
from sqlalchemy.exc import IntegrityError

from alembic import command
from app.core.database import Base
from app.models import (
    ActionResult,
    ActionResultExecutionStatus,
    AgentDecision,
    AuditActorType,
    AuditLog,
    BillingCadence,
    Customer,
    CustomerRiskTier,
    MLPrediction,
    Payment,
    PaymentAttempt,
    PaymentAttemptStatus,
    PaymentEvent,
    PaymentEventProcessingStatus,
    PaymentEventSource,
    PaymentStatus,
    PolicyDecision,
    PolicyEvaluationResult,
    RecoveryAction,
    RecoveryActionStatus,
    RecoveryActionType,
    RecoveryCase,
    RecoveryCaseStatus,
    RecoveryStage,
    Subscription,
    SubscriptionStatus,
)


def test_database_connection(test_db_engine):
    """1. Test that the database engine connects and executes basic queries."""
    with test_db_engine.connect() as conn:
        result = conn.execute(text("SELECT 1")).scalar()
        assert result == 1


def test_all_models_import_and_metadata():
    """2. Test that all 12 models import and are registered in Base.metadata."""
    expected_tables = {
        "customers",
        "subscriptions",
        "payments",
        "payment_attempts",
        "payment_events",
        "recovery_cases",
        "ml_predictions",
        "agent_decisions",
        "policy_decisions",
        "recovery_actions",
        "action_results",
        "audit_logs",
    }
    registered_tables = set(Base.metadata.tables.keys())
    assert expected_tables.issubset(registered_tables)
    assert len(registered_tables) == 12


def test_alembic_migration_from_empty_database_and_upgrade():
    """3 & 4. Test that Alembic migration runs from empty database and succeeds."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, "alembic_test.db")
        db_url = f"sqlite:///{db_path}"

        backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        ini_path = os.path.join(backend_dir, "alembic.ini")
        alembic_cfg = Config(ini_path)
        alembic_cfg.set_main_option(
            "script_location", os.path.join(backend_dir, "alembic")
        )
        alembic_cfg.set_main_option("sqlalchemy.url", db_url)

        # Run upgrade
        command.upgrade(alembic_cfg, "head")

        # Verify tables exist via reflection
        from sqlalchemy import create_engine

        engine = create_engine(db_url)
        inspector = inspect(engine)
        tables = set(inspector.get_table_names())
        assert "customers" in tables
        assert "recovery_cases" in tables
        assert "audit_logs" in tables
        assert "payment_events" in tables

        # Run downgrade
        command.downgrade(alembic_cfg, "base")
        inspector_post_down = inspect(engine)
        assert "customers" not in inspector_post_down.get_table_names()

        # Re-upgrade
        command.upgrade(alembic_cfg, "head")
        inspector_post_up = inspect(engine)
        assert "customers" in inspector_post_up.get_table_names()
        engine.dispose()


def test_tables_exist_after_creation(test_db_engine):
    """5. Test that all 12 tables exist in the schema."""
    inspector = inspect(test_db_engine)
    tables = inspector.get_table_names()
    for table_name in [
        "customers",
        "subscriptions",
        "payments",
        "payment_attempts",
        "payment_events",
        "recovery_cases",
        "ml_predictions",
        "agent_decisions",
        "policy_decisions",
        "recovery_actions",
        "action_results",
        "audit_logs",
    ]:
        assert table_name in tables


def test_foreign_key_relationships(db_session):
    """6. Test foreign key constraints and referential integrity."""
    # Attempting to insert a subscription with a non-existent customer should fail
    sub = Subscription(
        id=uuid.uuid4(),
        customer_id=uuid.uuid4(),  # Non-existent customer
        plan_name="Pro Plan",
        billing_cadence=BillingCadence.MONTHLY.value,
        recurring_amount=99900,
        currency="INR",
        status=SubscriptionStatus.ACTIVE.value,
    )
    db_session.add(sub)
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()


def test_unique_provider_identifiers(db_session):
    """7. Test unique constraints on provider reference identifiers."""
    c1 = Customer(
        external_customer_id="cust_ext_001",
        razorpay_customer_id="cust_rzp_001",
        risk_tier=CustomerRiskTier.STANDARD.value,
    )
    c2 = Customer(
        external_customer_id="cust_ext_002",
        razorpay_customer_id="cust_rzp_001",  # Duplicate razorpay_customer_id
        risk_tier=CustomerRiskTier.STANDARD.value,
    )
    db_session.add(c1)
    db_session.commit()

    db_session.add(c2)
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()


def test_duplicate_payment_event_idempotency_rejected(db_session):
    """8. Test that duplicate payment event idempotency_key is rejected."""
    evt1 = PaymentEvent(
        idempotency_key="event_idemp_key_123",
        source=PaymentEventSource.RAZORPAY_WEBHOOK.value,
        event_type="payment.failed",
        razorpay_event_id="event_rzp_123",
        payload={"event": "payment.failed"},
        processing_status=PaymentEventProcessingStatus.RECEIVED.value,
    )
    evt2 = PaymentEvent(
        idempotency_key="event_idemp_key_123",  # Duplicate idempotency_key
        source=PaymentEventSource.RAZORPAY_WEBHOOK.value,
        event_type="payment.failed",
        razorpay_event_id="event_rzp_456",
        payload={"event": "payment.failed"},
        processing_status=PaymentEventProcessingStatus.RECEIVED.value,
    )
    db_session.add(evt1)
    db_session.commit()

    db_session.add(evt2)
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()


def test_duplicate_action_idempotency_key_rejected(db_session):
    """9. Test that duplicate action_idempotency_key is rejected."""
    # Create customer, payment, case, agent_decision, policy_decision
    cust = Customer(external_customer_id="cust_action_1")
    db_session.add(cust)
    db_session.flush()

    payment = Payment(
        customer_id=cust.id,
        amount=50000,
        currency="INR",
        status=PaymentStatus.FAILED.value,
    )
    db_session.add(payment)
    db_session.flush()

    case = RecoveryCase(
        payment_id=payment.id,
        customer_id=cust.id,
        status=RecoveryCaseStatus.OPEN.value,
        recovery_stage=RecoveryStage.INITIAL_FAILURE.value,
        amount_at_risk=50000,
    )
    db_session.add(case)
    db_session.flush()

    agent_dec = AgentDecision(
        recovery_case_id=case.id,
        agent_name="RecoveryOrchestrator",
        agent_version="v1.0.0",
        prompt_template_version="pt_v1",
        proposed_action_type=RecoveryActionType.SEND_PAYMENT_LINK.value,
        confidence_score=Decimal("0.8500"),
        reasoning_summary="Soft decline; high recovery likelihood",
    )
    db_session.add(agent_dec)
    db_session.flush()

    pol_dec = PolicyDecision(
        recovery_case_id=case.id,
        agent_decision_id=agent_dec.id,
        evaluation_result=PolicyEvaluationResult.ALLOWED.value,
        policy_engine_version="v1.0.0",
        decision_reason="All frequency and risk checks passed",
    )
    db_session.add(pol_dec)
    db_session.flush()

    act1 = RecoveryAction(
        recovery_case_id=case.id,
        policy_decision_id=pol_dec.id,
        action_idempotency_key="act_case1_retry_1",
        action_type=RecoveryActionType.SEND_PAYMENT_LINK.value,
        status=RecoveryActionStatus.PENDING.value,
    )
    act2 = RecoveryAction(
        recovery_case_id=case.id,
        policy_decision_id=pol_dec.id,
        action_idempotency_key="act_case1_retry_1",  # Duplicate action_idempotency_key
        action_type=RecoveryActionType.SEND_PAYMENT_LINK.value,
        status=RecoveryActionStatus.PENDING.value,
    )
    db_session.add(act1)
    db_session.commit()

    db_session.add(act2)
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()


def test_audit_log_recovery_case_id_can_be_null(db_session):
    """10 & 11. Test that recovery_case_id on audit_logs is nullable."""
    audit_entry = AuditLog(
        event_type="SYSTEM_STARTUP",
        actor_type=AuditActorType.SYSTEM_EVENT.value,
        actor_id="system_daemon",
        recovery_case_id=None,  # Nullable
        entity_type="system",
        entity_id=None,
        action="DAEMON_INITIALIZED",
        metadata_json={"cluster": "us-east-1"},
    )
    db_session.add(audit_entry)
    db_session.commit()

    retrieved = (
        db_session.query(AuditLog).filter_by(event_type="SYSTEM_STARTUP").first()
    )
    assert retrieved is not None
    assert retrieved.recovery_case_id is None
    assert retrieved.action == "DAEMON_INITIALIZED"


def test_monetary_constraints(db_session):
    """12. Test monetary amount check constraints (non-negative, recovered <= risk)."""
    cust = Customer(external_customer_id="cust_money_test")
    db_session.add(cust)
    db_session.flush()

    # Negative payment amount should fail
    bad_payment = Payment(
        customer_id=cust.id,
        amount=-100,  # Negative
        currency="INR",
    )
    db_session.add(bad_payment)
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()

    # Recovered amount exceeding amount_at_risk should fail
    cust = Customer(external_customer_id="cust_money_test_2")
    db_session.add(cust)
    db_session.flush()

    good_payment = Payment(
        customer_id=cust.id,
        amount=10000,
        currency="INR",
    )
    db_session.add(good_payment)
    db_session.flush()

    bad_case = RecoveryCase(
        payment_id=good_payment.id,
        customer_id=cust.id,
        amount_at_risk=10000,
        recovered_amount=15000,  # Exceeds amount_at_risk
    )
    db_session.add(bad_case)
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()


def test_basic_relationship_creation_and_traversal(db_session):
    """13. Test full lifecycle relationship creation from Customer to ActionResult."""
    # 1. Customer
    cust = Customer(
        external_customer_id="cust_rel_001",
        email_masked="u***@example.com",
    )
    db_session.add(cust)
    db_session.flush()

    # 2. Subscription
    sub = Subscription(
        customer_id=cust.id,
        plan_name="Enterprise Plan",
        billing_cadence=BillingCadence.MONTHLY.value,
        recurring_amount=499900,
        currency="INR",
        status=SubscriptionStatus.ACTIVE.value,
    )
    db_session.add(sub)
    db_session.flush()

    # 3. Payment
    payment = Payment(
        customer_id=cust.id,
        subscription_id=sub.id,
        amount=499900,
        currency="INR",
        status=PaymentStatus.FAILED.value,
        razorpay_order_id="order_rel_001",
    )
    db_session.add(payment)
    db_session.flush()

    # 4. PaymentAttempt
    attempt = PaymentAttempt(
        payment_id=payment.id,
        attempt_number=1,
        amount=499900,
        status=PaymentAttemptStatus.FAILED.value,
        error_code="BAD_REQUEST_ERROR",
        error_reason="insufficient_funds",
        razorpay_payment_id="pay_rel_attempt_001",
    )
    db_session.add(attempt)
    db_session.flush()

    # 5. PaymentEvent
    event_entry = PaymentEvent(
        idempotency_key="evt_idemp_rel_001",
        payment_id=payment.id,
        source=PaymentEventSource.RAZORPAY_WEBHOOK.value,
        event_type="payment.failed",
        razorpay_event_id="event_rel_001",
        payload={
            "id": "pay_rel_attempt_001",
            "error": {"reason": "insufficient_funds"},
        },
        processing_status=PaymentEventProcessingStatus.PROCESSED.value,
    )
    db_session.add(event_entry)
    db_session.flush()

    # 6. RecoveryCase
    case = RecoveryCase(
        payment_id=payment.id,
        customer_id=cust.id,
        status=RecoveryCaseStatus.OPEN.value,
        recovery_stage=RecoveryStage.INITIAL_FAILURE.value,
        amount_at_risk=499900,
        recovered_amount=0,
    )
    db_session.add(case)
    db_session.flush()

    # 7. MLPrediction
    prediction = MLPrediction(
        recovery_case_id=case.id,
        model_name="recoveriq-xgb-classifier",
        model_version="v1.2.0",
        recovery_probability=Decimal("0.7850"),
        predicted_channel="PAYMENT_LINK",
        predicted_delay_hours=12,
        feature_vector_snapshot={"history_score": 0.8, "card_type": "debit"},
    )
    db_session.add(prediction)
    db_session.flush()

    # 8. AgentDecision
    decision = AgentDecision(
        recovery_case_id=case.id,
        ml_prediction_id=prediction.id,
        agent_name="RecoveryOrchestrator",
        agent_version="v1.0.0",
        prompt_template_version="pt_v2",
        proposed_action_type=RecoveryActionType.SEND_PAYMENT_LINK.value,
        confidence_score=Decimal("0.8900"),
        reasoning_summary="Payment failed due to insufficient funds; send link.",
        suggested_payload={"channel": "WHATSAPP", "link_expiry_hours": 48},
    )
    db_session.add(decision)
    db_session.flush()

    # 9. PolicyDecision
    policy_dec = PolicyDecision(
        recovery_case_id=case.id,
        agent_decision_id=decision.id,
        evaluation_result=PolicyEvaluationResult.ALLOWED.value,
        policy_engine_version="v1.1.0",
        triggered_rule_code=None,
        rule_name="StandardSafetyCheck",
        evaluation_details={"attempt_count": 0, "max_allowed": 3},
        decision_reason="All frequency and amount safety rules satisfied.",
    )
    db_session.add(policy_dec)
    db_session.flush()

    # 10. RecoveryAction
    action = RecoveryAction(
        recovery_case_id=case.id,
        policy_decision_id=policy_dec.id,
        action_idempotency_key="act_rel_case_001_1",
        action_type=RecoveryActionType.SEND_PAYMENT_LINK.value,
        status=RecoveryActionStatus.COMPLETED.value,
    )
    db_session.add(action)
    db_session.flush()

    # 11. ActionResult
    result = ActionResult(
        recovery_action_id=action.id,
        execution_status=ActionResultExecutionStatus.SUCCESS.value,
        provider_reference_id="plink_rel_001",
        provider_status_code="200",
        response_payload_summary={
            "link_id": "plink_rel_001",
            "short_url": "https://rzp.io/l/rel001",
        },
    )
    db_session.add(result)
    db_session.flush()

    # 12. AuditLog (case-bound)
    audit = AuditLog(
        event_type="RECOVERY_ACTION_EXECUTED",
        actor_type=AuditActorType.ACTION_EXECUTOR.value,
        actor_id="executor_service",
        recovery_case_id=case.id,
        entity_type="recovery_actions",
        entity_id=action.id,
        action="PAYMENT_LINK_DISPATCHED",
        metadata_json={"plink_id": "plink_rel_001"},
    )
    db_session.add(audit)
    db_session.commit()

    # Verify bidirectional relationship navigations
    fetched_case = db_session.query(RecoveryCase).filter_by(id=case.id).first()
    assert fetched_case is not None
    assert fetched_case.payment.amount == 499900
    assert fetched_case.customer.external_customer_id == "cust_rel_001"
    assert len(fetched_case.predictions) == 1
    assert fetched_case.predictions[0].recovery_probability == Decimal("0.7850")
    assert len(fetched_case.agent_decisions) == 1
    assert (
        fetched_case.agent_decisions[0].proposed_action_type
        == RecoveryActionType.SEND_PAYMENT_LINK.value
    )
    assert len(fetched_case.actions) == 1
    assert len(fetched_case.actions[0].results) == 1
    assert fetched_case.actions[0].results[0].provider_reference_id == "plink_rel_001"
    assert len(fetched_case.audit_logs) == 1
    assert fetched_case.audit_logs[0].action == "PAYMENT_LINK_DISPATCHED"
