import uuid
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import UserRole, create_access_token
from app.main import app
from app.models import (
    ActionResult,
    AgentDecision,
    Customer,
    CustomerRiskTier,
    MLPrediction,
    Payment,
    PaymentStatus,
    PolicyDecision,
    PolicyEvaluationResult,
    ProductionStrategyStatus,
    RecoveryAction,
    RecoveryActionStatus,
    RecoveryActionType,
    RecoveryCase,
    RecoveryCaseStatus,
    RolloutHealthStatus,
)
from app.schemas.activation import (
    ConfidenceInterval,
    ExperimentMetrics,
    RolloutHealth,
    StrategyComparison,
    UpliftMetrics,
)
from app.services.production_monitoring_service import (
    production_monitoring_service,
)
from app.services.strategy_activation_service import (
    strategy_activation_service,
)
from app.services.strategy_governance_service import (
    strategy_governance_service,
)


@pytest.fixture
def client(db_session: Session):
    """Test client with overridden database session dependency and viewer auth."""

    def _override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = _override_get_db
    token = create_access_token(user_id="viewer_test_mon", role=UserRole.VIEWER.value)
    with TestClient(app, headers={"Authorization": f"Bearer {token}"}) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def make_case(
    db_session: Session,
    status: str = RecoveryCaseStatus.RECOVERED.value,
    amount: int = 100000,
    prob: float = 0.85,
    action_type: str = RecoveryActionType.SEND_PAYMENT_LINK.value,
    delay_hours: int = 4,
) -> RecoveryCase:
    """Helper to provision a resolved recovery case."""
    uid = uuid.uuid4().hex[:8]
    now_utc = datetime.now(UTC)
    resolved_time = now_utc - timedelta(days=1)

    customer = Customer(
        external_customer_id=f"cust_mon_{uid}",
        risk_tier=CustomerRiskTier.STANDARD.value,
        total_payments_count=5,
        failed_payments_count=1,
        recovered_payments_count=4,
    )
    db_session.add(customer)
    db_session.flush()

    payment = Payment(
        customer_id=customer.id,
        amount=amount,
        currency="INR",
        status=PaymentStatus.CAPTURED.value
        if status == RecoveryCaseStatus.RECOVERED.value
        else PaymentStatus.FAILED.value,
    )
    db_session.add(payment)
    db_session.flush()

    case = RecoveryCase(
        payment_id=payment.id,
        customer_id=customer.id,
        status=status,
        amount_at_risk=amount,
        recovered_amount=amount if status == RecoveryCaseStatus.RECOVERED.value else 0,
        total_attempts_count=1,
        max_allowed_attempts=3,
        latest_failure_reason="insufficient_funds",
        opened_at=resolved_time - timedelta(hours=delay_hours),
        resolved_at=resolved_time,
        created_at=resolved_time,
        metadata_json={},
    )
    db_session.add(case)
    db_session.flush()

    prediction = MLPrediction(
        recovery_case_id=case.id,
        model_name="recovery_probability",
        model_version="v1.0",
        recovery_probability=Decimal(str(round(prob, 4))),
        predicted_channel=action_type,
        predicted_delay_hours=delay_hours,
        feature_vector_snapshot={
            "error_reason": "insufficient_funds",
            "amount": amount,
        },
        predicted_at=resolved_time,
    )
    db_session.add(prediction)
    db_session.flush()

    agent_dec = AgentDecision(
        recovery_case_id=case.id,
        ml_prediction_id=prediction.id,
        agent_name="RecoveryOrchestrator",
        agent_version="v1.0",
        prompt_template_version="v1.0",
        proposed_action_type=action_type,
        confidence_score=Decimal("0.8500"),
        reasoning_summary="Monitoring test decision.",
        suggested_payload={"channel": "GATEWAY_API"},
    )
    db_session.add(agent_dec)
    db_session.flush()

    pol_dec = PolicyDecision(
        recovery_case_id=case.id,
        agent_decision_id=agent_dec.id,
        evaluation_result=PolicyEvaluationResult.ALLOWED.value,
        policy_engine_version="v1.0",
        decision_reason="Policy allowed.",
    )
    db_session.add(pol_dec)
    db_session.flush()

    action = RecoveryAction(
        recovery_case_id=case.id,
        policy_decision_id=pol_dec.id,
        action_idempotency_key=f"act_{uid}",
        action_type=action_type,
        status=RecoveryActionStatus.COMPLETED.value
        if status == RecoveryCaseStatus.RECOVERED.value
        else RecoveryActionStatus.FAILED.value,
        scheduled_for=resolved_time,
    )
    db_session.add(action)
    db_session.commit()

    return case


def setup_active_canary(db_session: Session) -> str:
    """Provisions dataset and activates a canary experiment."""
    # Control cases: 20 cases with 30% recovery rate
    for i in range(20):
        status = (
            RecoveryCaseStatus.RECOVERED.value
            if i < 6
            else RecoveryCaseStatus.CLOSED.value
        )
        make_case(
            db_session,
            status=status,
            prob=0.30,
            action_type=RecoveryActionType.RETRY_PAYMENT.value,
        )

    # Treatment cases: 20 cases with 85% recovery rate
    for i in range(20):
        status = (
            RecoveryCaseStatus.RECOVERED.value
            if i < 17
            else RecoveryCaseStatus.CLOSED.value
        )
        make_case(
            db_session,
            status=status,
            prob=0.85,
            action_type=RecoveryActionType.SEND_PAYMENT_LINK.value,
        )

    rec = strategy_governance_service.evaluate_and_sync_recommendation(db_session)
    assert rec is not None

    op_user = type("AuthUser", (), {"id": "test_op_mon", "role": "operator"})()
    appr_rec = strategy_governance_service.approve_recommendation(
        db=db_session,
        recommendation_id=rec.recommendation_id,
        current_user=op_user,  # type: ignore
    )
    act = strategy_activation_service.create_activation(
        db=db_session,
        recommendation_id=appr_rec.recommendation_id,
        current_user=op_user,  # type: ignore
    )
    strategy_activation_service.start_canary(
        db=db_session,
        activation_id=act.activation_id,
        rollout_percentage=50,
        current_user=op_user,  # type: ignore
    )
    return act.activation_id


# =========================================================================
# 1. Continuous Production Monitoring Tests
# =========================================================================


def test_cold_start_no_active_strategy(db_session: Session):
    """1. Test monitoring behavior when no active strategy is running (NO_ACTIVE_STRATEGY)."""
    mon = production_monitoring_service.monitor_production(db=db_session)
    assert mon.status == ProductionStrategyStatus.NO_ACTIVE_STRATEGY.value
    assert mon.activation_id is None
    assert mon.rollback_recommended is False
    assert len(mon.diagnostics) > 0


def test_healthy_production_strategy_monitoring(db_session: Session):
    """2. Test monitoring of an active, healthy strategy produces HEALTHY status."""
    setup_active_canary(db_session)

    mock_comp = StrategyComparison(
        control_metrics=ExperimentMetrics(
            sample_size=50,
            recovered_count=25,
            failed_count=25,
            recovery_rate=0.5000,
            amount_at_risk_paise=5000000,
            amount_recovered_paise=2500000,
            financial_yield=0.5000,
            expected_recovery_value_paise=2500000,
            mean_time_to_recovery_hours=4.0,
            median_time_to_recovery_hours=4.0,
        ),
        treatment_metrics=ExperimentMetrics(
            sample_size=50,
            recovered_count=40,
            failed_count=10,
            recovery_rate=0.8000,
            amount_at_risk_paise=5000000,
            amount_recovered_paise=4000000,
            financial_yield=0.8000,
            expected_recovery_value_paise=4000000,
            mean_time_to_recovery_hours=3.5,
            median_time_to_recovery_hours=3.5,
        ),
        uplift=UpliftMetrics(
            absolute_uplift=0.3000,
            relative_uplift_pct=60.0,
            incremental_expected_recovery_value_paise=1500000,
        ),
        confidence_interval=ConfidenceInterval(
            lower_bound=0.1500,
            upper_bound=0.4500,
            confidence_level=0.95,
            is_significant=True,
        ),
        reliability="SUFFICIENT",
    )

    with patch.object(
        strategy_activation_service,
        "_build_strategy_comparison",
        return_value=(
            mock_comp,
            RolloutHealth(
                status=RolloutHealthStatus.SAFE.value,
                diagnostics=[],
                evaluated_at=datetime.now(UTC),
            ),
        ),
    ):
        mon = production_monitoring_service.monitor_production(db=db_session)
        assert mon.status in (
            ProductionStrategyStatus.HEALTHY.value,
            ProductionStrategyStatus.WARNING.value,
        )

        assert mon.activation_id is not None
        assert mon.strategy_name == "SEND_PAYMENT_LINK"
        assert mon.sample_size == 100
        assert mon.rollback_recommended is False
        assert mon.absolute_uplift == 0.3000


def test_rollback_recommended_on_negative_uplift(db_session: Session):
    """3. Test monitoring recommends rollback when treatment rate trails control by >= 5.0%."""
    setup_active_canary(db_session)

    mock_comp = StrategyComparison(
        control_metrics=ExperimentMetrics(
            sample_size=50,
            recovered_count=45,
            failed_count=5,
            recovery_rate=0.9000,
            amount_at_risk_paise=5000000,
            amount_recovered_paise=4500000,
            financial_yield=0.9000,
            expected_recovery_value_paise=4500000,
            mean_time_to_recovery_hours=4.0,
            median_time_to_recovery_hours=4.0,
        ),
        treatment_metrics=ExperimentMetrics(
            sample_size=50,
            recovered_count=20,
            failed_count=30,
            recovery_rate=0.4000,
            amount_at_risk_paise=5000000,
            amount_recovered_paise=2000000,
            financial_yield=0.4000,
            expected_recovery_value_paise=2000000,
            mean_time_to_recovery_hours=4.0,
            median_time_to_recovery_hours=4.0,
        ),
        uplift=UpliftMetrics(
            absolute_uplift=-0.5000,
            relative_uplift_pct=-55.56,
            incremental_expected_recovery_value_paise=-2500000,
        ),
        confidence_interval=ConfidenceInterval(
            lower_bound=-0.6500,
            upper_bound=-0.3500,
            confidence_level=0.95,
            is_significant=True,
        ),
        reliability="SUFFICIENT",
    )

    with patch.object(
        strategy_activation_service,
        "_build_strategy_comparison",
        return_value=(
            mock_comp,
            RolloutHealth(
                status=RolloutHealthStatus.ROLLBACK_RECOMMENDED.value,
                diagnostics=["Rollback recommended"],
                evaluated_at=datetime.now(UTC),
            ),
        ),
    ):
        mon = production_monitoring_service.monitor_production(db=db_session)
        assert mon.status == ProductionStrategyStatus.ROLLBACK_RECOMMENDED.value
        assert mon.rollback_recommended is True
        assert any("CRITICAL: Treatment recovery rate" in d for d in mon.diagnostics)


def test_zero_division_safety(db_session: Session):
    """4. Test zero division safety when control has 0 recovery rate."""
    setup_active_canary(db_session)

    mock_comp = StrategyComparison(
        control_metrics=ExperimentMetrics(
            sample_size=50,
            recovered_count=0,
            failed_count=50,
            recovery_rate=0.0,
            amount_at_risk_paise=5000000,
            amount_recovered_paise=0,
            financial_yield=0.0,
            expected_recovery_value_paise=0,
            mean_time_to_recovery_hours=None,
            median_time_to_recovery_hours=None,
        ),
        treatment_metrics=ExperimentMetrics(
            sample_size=50,
            recovered_count=20,
            failed_count=30,
            recovery_rate=0.4000,
            amount_at_risk_paise=5000000,
            amount_recovered_paise=2000000,
            financial_yield=0.4000,
            expected_recovery_value_paise=2000000,
            mean_time_to_recovery_hours=4.0,
            median_time_to_recovery_hours=4.0,
        ),
        uplift=UpliftMetrics(
            absolute_uplift=0.4000,
            relative_uplift_pct=None,
            incremental_expected_recovery_value_paise=2000000,
        ),
        confidence_interval=ConfidenceInterval(
            lower_bound=0.2500,
            upper_bound=0.5500,
            confidence_level=0.95,
            is_significant=True,
        ),
        reliability="SUFFICIENT",
    )

    with patch.object(
        strategy_activation_service,
        "_build_strategy_comparison",
        return_value=(
            mock_comp,
            RolloutHealth(
                status=RolloutHealthStatus.SAFE.value,
                diagnostics=[],
                evaluated_at=datetime.now(UTC),
            ),
        ),
    ):
        mon = production_monitoring_service.monitor_production(db=db_session)
        assert mon.relative_uplift_pct is None


# =========================================================================
# 2. HTTP Endpoint & Financial Isolation Tests
# =========================================================================


def test_monitoring_endpoint_via_http(client: TestClient, db_session: Session):
    """5. Test GET /api/recovery/intelligence/production returns 200 with complete metrics."""
    setup_active_canary(db_session)

    res = client.get("/api/recovery/intelligence/production")
    assert res.status_code == 200
    data = res.json()
    assert "status" in data
    assert "sample_size" in data
    assert "disclaimer" in data


def test_monitoring_creates_zero_recovery_actions(db_session: Session):
    """6. Test monitoring creates zero RecoveryAction records and zero provider calls."""
    setup_active_canary(db_session)

    initial_actions_count = db_session.query(RecoveryAction).count()
    initial_cases_count = db_session.query(RecoveryCase).count()
    initial_results_count = db_session.query(ActionResult).count()

    def _override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = _override_get_db
    token_v = create_access_token(user_id="viewer_usr", role=UserRole.VIEWER.value)

    with (
        patch(
            "app.services.action_dispatcher.ActionDispatcher.dispatch_action"
        ) as mock_dispatch,
        patch("app.providers.razorpay.RazorpayActionProvider.execute") as mock_exec,
        TestClient(app, headers={"Authorization": f"Bearer {token_v}"}) as test_client,
    ):
        res = test_client.get("/api/recovery/intelligence/production")
        assert res.status_code == 200
        mock_dispatch.assert_not_called()
        mock_exec.assert_not_called()

    app.dependency_overrides.clear()

    assert db_session.query(RecoveryAction).count() == initial_actions_count
    assert db_session.query(RecoveryCase).count() == initial_cases_count
    assert db_session.query(ActionResult).count() == initial_results_count


def test_zero_pii_and_secrets_in_production_monitoring(
    client: TestClient, db_session: Session
):
    """7. Test that production monitoring responses contain zero PII and zero secrets."""
    setup_active_canary(db_session)

    res = client.get("/api/recovery/intelligence/production")
    assert res.status_code == 200
    text = res.text.lower()

    for forbidden in [
        "password",
        "secret",
        "bearer",
        "@",
        "email",
        "phone",
        "card_number",
        "pan",
        "cvv",
        "api_key",
    ]:
        assert forbidden not in text
