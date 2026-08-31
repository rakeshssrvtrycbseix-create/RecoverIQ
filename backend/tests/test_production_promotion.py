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
    RecoveryAction,
    RecoveryActionStatus,
    RecoveryActionType,
    RecoveryCase,
    RecoveryCaseStatus,
    RolloutHealthStatus,
    StrategyActivationStatus,
)
from app.schemas.activation import (
    ConfidenceInterval,
    ExperimentMetrics,
    RolloutHealth,
    StrategyComparison,
    UpliftMetrics,
)
from app.services.production_promotion_service import (
    PromotionBlockedError,
    production_promotion_service,
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
    token = create_access_token(user_id="viewer_test_prom", role=UserRole.VIEWER.value)
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
        external_customer_id=f"cust_prom_{uid}",
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
        reasoning_summary="Promotion test decision.",
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


def setup_standard_canary_activation(db_session: Session) -> str:
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

    op_user = type("AuthUser", (), {"id": "test_op_prom", "role": "operator"})()
    appr_rec = strategy_governance_service.approve_recommendation(
        db=db_session,
        recommendation_id=rec.recommendation_id,
        current_user=op_user,  # type: ignore
        notes="Approved for canary",
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
# 1. Promotion Safety Rules Evaluation Tests
# =========================================================================


def test_insufficient_sample_blocks_promotion(db_session: Session):
    """1. Test that sample size < 100 blocks promotion with PROMOTION_BLOCKED_INSUFFICIENT_SAMPLE."""
    act_id = setup_standard_canary_activation(db_session)

    readiness = production_promotion_service.evaluate_promotion_readiness(
        db=db_session, activation_id=act_id
    )
    assert readiness.eligible is False
    assert "PROMOTION_BLOCKED_INSUFFICIENT_SAMPLE" in readiness.blockers
    sample_check = next(c for c in readiness.checks if c.rule == "MIN_SAMPLE_SIZE")
    assert sample_check.passed is False


def test_zero_or_negative_uplift_blocks_promotion(db_session: Session):
    """2. Test that zero or negative uplift blocks promotion with PROMOTION_BLOCKED_NO_UPLIFT."""
    act_id = setup_standard_canary_activation(db_session)

    mock_comp = StrategyComparison(
        control_metrics=ExperimentMetrics(
            sample_size=60,
            recovered_count=50,
            failed_count=10,
            recovery_rate=0.8333,
            amount_at_risk_paise=6000000,
            amount_recovered_paise=5000000,
            financial_yield=0.8333,
            expected_recovery_value_paise=5000000,
            mean_time_to_recovery_hours=4.0,
            median_time_to_recovery_hours=4.0,
        ),
        treatment_metrics=ExperimentMetrics(
            sample_size=60,
            recovered_count=20,
            failed_count=40,
            recovery_rate=0.3333,
            amount_at_risk_paise=6000000,
            amount_recovered_paise=2000000,
            financial_yield=0.3333,
            expected_recovery_value_paise=2000000,
            mean_time_to_recovery_hours=4.0,
            median_time_to_recovery_hours=4.0,
        ),
        uplift=UpliftMetrics(
            absolute_uplift=-0.5000,
            relative_uplift_pct=-60.0,
            incremental_expected_recovery_value_paise=-3000000,
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
        readiness = production_promotion_service.evaluate_promotion_readiness(
            db=db_session, activation_id=act_id
        )
        assert readiness.eligible is False
        assert "PROMOTION_BLOCKED_NO_UPLIFT" in readiness.blockers


def test_low_practical_uplift_blocks_promotion(db_session: Session):
    """3. Test that absolute uplift < 2.0 percentage points blocks promotion with PROMOTION_BLOCKED_LOW_EFFECT."""
    act_id = setup_standard_canary_activation(db_session)

    mock_comp = StrategyComparison(
        control_metrics=ExperimentMetrics(
            sample_size=60,
            recovered_count=42,
            failed_count=18,
            recovery_rate=0.7000,
            amount_at_risk_paise=6000000,
            amount_recovered_paise=4200000,
            financial_yield=0.7000,
            expected_recovery_value_paise=4200000,
            mean_time_to_recovery_hours=4.0,
            median_time_to_recovery_hours=4.0,
        ),
        treatment_metrics=ExperimentMetrics(
            sample_size=60,
            recovered_count=43,
            failed_count=17,
            recovery_rate=0.7100,
            amount_at_risk_paise=6000000,
            amount_recovered_paise=4300000,
            financial_yield=0.7100,
            expected_recovery_value_paise=4300000,
            mean_time_to_recovery_hours=4.0,
            median_time_to_recovery_hours=4.0,
        ),
        uplift=UpliftMetrics(
            absolute_uplift=0.0100,
            relative_uplift_pct=1.43,
            incremental_expected_recovery_value_paise=100000,
        ),
        confidence_interval=ConfidenceInterval(
            lower_bound=-0.1200,
            upper_bound=0.1400,
            confidence_level=0.95,
            is_significant=False,
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
        readiness = production_promotion_service.evaluate_promotion_readiness(
            db=db_session, activation_id=act_id
        )
        assert readiness.eligible is False
        assert "PROMOTION_BLOCKED_LOW_EFFECT" in readiness.blockers


def test_valid_canary_is_promotion_ready(db_session: Session):
    """4. Test that a healthy canary with sufficient sample and positive uplift is PROMOTION_READY."""
    act_id = setup_standard_canary_activation(db_session)

    mock_comp = StrategyComparison(
        control_metrics=ExperimentMetrics(
            sample_size=75,
            recovered_count=35,
            failed_count=40,
            recovery_rate=0.4667,
            amount_at_risk_paise=7500000,
            amount_recovered_paise=3500000,
            financial_yield=0.4667,
            expected_recovery_value_paise=3500000,
            mean_time_to_recovery_hours=4.0,
            median_time_to_recovery_hours=4.0,
        ),
        treatment_metrics=ExperimentMetrics(
            sample_size=75,
            recovered_count=60,
            failed_count=15,
            recovery_rate=0.8000,
            amount_at_risk_paise=7500000,
            amount_recovered_paise=6000000,
            financial_yield=0.8000,
            expected_recovery_value_paise=6000000,
            mean_time_to_recovery_hours=3.5,
            median_time_to_recovery_hours=3.5,
        ),
        uplift=UpliftMetrics(
            absolute_uplift=0.3333,
            relative_uplift_pct=71.42,
            incremental_expected_recovery_value_paise=2500000,
        ),
        confidence_interval=ConfidenceInterval(
            lower_bound=0.1800,
            upper_bound=0.4800,
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
        readiness = production_promotion_service.evaluate_promotion_readiness(
            db=db_session, activation_id=act_id
        )
        assert readiness.eligible is True
        assert readiness.status == "PROMOTION_READY"
        assert len(readiness.blockers) == 0
        assert readiness.sample_size == 150
        assert readiness.absolute_uplift == 0.3333


def test_promotion_blocked_on_invalid_attempt_raises_409(db_session: Session):
    """5. Test that promoting an ineligible activation raises PromotionBlockedError."""
    act_id = setup_standard_canary_activation(db_session)
    admin_user = type("AuthUser", (), {"id": "test_admin", "role": "admin"})()

    with pytest.raises(PromotionBlockedError):
        production_promotion_service.promote_to_production(
            db=db_session,
            activation_id=act_id,
            current_user=admin_user,  # type: ignore
        )


def test_admin_successful_production_promotion(db_session: Session):
    """6. Test that admin can successfully promote a PROMOTION_READY activation to 100% PRODUCTION."""
    act_id = setup_standard_canary_activation(db_session)
    admin_user = type("AuthUser", (), {"id": "test_admin_usr", "role": "admin"})()

    mock_comp = StrategyComparison(
        control_metrics=ExperimentMetrics(
            sample_size=75,
            recovered_count=35,
            failed_count=40,
            recovery_rate=0.4667,
            amount_at_risk_paise=7500000,
            amount_recovered_paise=3500000,
            financial_yield=0.4667,
            expected_recovery_value_paise=3500000,
            mean_time_to_recovery_hours=4.0,
            median_time_to_recovery_hours=4.0,
        ),
        treatment_metrics=ExperimentMetrics(
            sample_size=75,
            recovered_count=60,
            failed_count=15,
            recovery_rate=0.8000,
            amount_at_risk_paise=7500000,
            amount_recovered_paise=6000000,
            financial_yield=0.8000,
            expected_recovery_value_paise=6000000,
            mean_time_to_recovery_hours=3.5,
            median_time_to_recovery_hours=3.5,
        ),
        uplift=UpliftMetrics(
            absolute_uplift=0.3333,
            relative_uplift_pct=71.42,
            incremental_expected_recovery_value_paise=2500000,
        ),
        confidence_interval=ConfidenceInterval(
            lower_bound=0.1800,
            upper_bound=0.4800,
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
        res = production_promotion_service.promote_to_production(
            db=db_session,
            activation_id=act_id,
            current_user=admin_user,  # type: ignore
            reason="Empirical canary confirmed +33% recovery uplift",
        )
        assert res.status in (
            StrategyActivationStatus.PRODUCTION.value,
            StrategyActivationStatus.ACTIVE.value,
        )
        assert res.rollout_percentage == 100


# =========================================================================
# 2. RBAC & HTTP Authorization Tests
# =========================================================================


def test_unauthenticated_requests_rejected(db_session: Session):
    """7. Test unauthenticated requests return 401."""

    def _override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = _override_get_db

    with TestClient(app) as test_client:
        assert (
            test_client.get("/api/recovery/intelligence/production").status_code == 401
        )
        assert (
            test_client.get(
                "/api/recovery/intelligence/activations/act_1/promotion-readiness"
            ).status_code
            == 401
        )
        assert (
            test_client.post(
                "/api/recovery/intelligence/activations/act_1/promote", json={}
            ).status_code
            == 401
        )

    app.dependency_overrides.clear()


def test_viewer_can_read_readiness_cannot_promote(db_session: Session):
    """8. Test viewer role can read promotion readiness (200) but cannot execute promote (403)."""
    act_id = setup_standard_canary_activation(db_session)

    def _override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = _override_get_db
    token_v = create_access_token(user_id="viewer_usr", role=UserRole.VIEWER.value)

    with TestClient(app, headers={"Authorization": f"Bearer {token_v}"}) as test_client:
        res_readiness = test_client.get(
            f"/api/recovery/intelligence/activations/{act_id}/promotion-readiness"
        )
        assert res_readiness.status_code == 200

        # Viewer tries to promote -> 403 Forbidden
        res_promote = test_client.post(
            f"/api/recovery/intelligence/activations/{act_id}/promote", json={}
        )
        assert res_promote.status_code == 403

    app.dependency_overrides.clear()


def test_operator_cannot_execute_full_production_promotion(db_session: Session):
    """9. Test operator role is rejected with 403 on promote endpoint (requires admin)."""
    act_id = setup_standard_canary_activation(db_session)

    def _override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = _override_get_db
    token_op = create_access_token(user_id="operator_usr", role=UserRole.OPERATOR.value)

    with TestClient(
        app, headers={"Authorization": f"Bearer {token_op}"}
    ) as test_client:
        res_promote = test_client.post(
            f"/api/recovery/intelligence/activations/{act_id}/promote", json={}
        )
        assert res_promote.status_code == 403

    app.dependency_overrides.clear()


def test_admin_http_promote_endpoint(db_session: Session):
    """10. Test admin can execute promote endpoint successfully when ready (200)."""
    act_id = setup_standard_canary_activation(db_session)

    mock_comp = StrategyComparison(
        control_metrics=ExperimentMetrics(
            sample_size=75,
            recovered_count=35,
            failed_count=40,
            recovery_rate=0.4667,
            amount_at_risk_paise=7500000,
            amount_recovered_paise=3500000,
            financial_yield=0.4667,
            expected_recovery_value_paise=3500000,
            mean_time_to_recovery_hours=4.0,
            median_time_to_recovery_hours=4.0,
        ),
        treatment_metrics=ExperimentMetrics(
            sample_size=75,
            recovered_count=60,
            failed_count=15,
            recovery_rate=0.8000,
            amount_at_risk_paise=7500000,
            amount_recovered_paise=6000000,
            financial_yield=0.8000,
            expected_recovery_value_paise=6000000,
            mean_time_to_recovery_hours=3.5,
            median_time_to_recovery_hours=3.5,
        ),
        uplift=UpliftMetrics(
            absolute_uplift=0.3333,
            relative_uplift_pct=71.42,
            incremental_expected_recovery_value_paise=2500000,
        ),
        confidence_interval=ConfidenceInterval(
            lower_bound=0.1800,
            upper_bound=0.4800,
            confidence_level=0.95,
            is_significant=True,
        ),
        reliability="SUFFICIENT",
    )

    def _override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = _override_get_db
    token_admin = create_access_token(user_id="admin_usr", role=UserRole.ADMIN.value)

    with (
        patch.object(
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
        ),
        TestClient(
            app, headers={"Authorization": f"Bearer {token_admin}"}
        ) as test_client,
    ):
        res_promote = test_client.post(
            f"/api/recovery/intelligence/activations/{act_id}/promote",
            json={"reason": "Empirical canary verified"},
        )
        assert res_promote.status_code == 200
        assert res_promote.json()["rollout_percentage"] == 100

    app.dependency_overrides.clear()


# =========================================================================
# 3. Financial Isolation & Zero PII/Secrets Verification
# =========================================================================


def test_promotion_creates_zero_recovery_actions_or_gateway_calls(db_session: Session):
    """11. Test that promotion creates zero RecoveryAction records and zero provider calls."""
    act_id = setup_standard_canary_activation(db_session)

    mock_comp = StrategyComparison(
        control_metrics=ExperimentMetrics(
            sample_size=75,
            recovered_count=35,
            failed_count=40,
            recovery_rate=0.4667,
            amount_at_risk_paise=7500000,
            amount_recovered_paise=3500000,
            financial_yield=0.4667,
            expected_recovery_value_paise=3500000,
            mean_time_to_recovery_hours=4.0,
            median_time_to_recovery_hours=4.0,
        ),
        treatment_metrics=ExperimentMetrics(
            sample_size=75,
            recovered_count=60,
            failed_count=15,
            recovery_rate=0.8000,
            amount_at_risk_paise=7500000,
            amount_recovered_paise=6000000,
            financial_yield=0.8000,
            expected_recovery_value_paise=6000000,
            mean_time_to_recovery_hours=3.5,
            median_time_to_recovery_hours=3.5,
        ),
        uplift=UpliftMetrics(
            absolute_uplift=0.3333,
            relative_uplift_pct=71.42,
            incremental_expected_recovery_value_paise=2500000,
        ),
        confidence_interval=ConfidenceInterval(
            lower_bound=0.1800,
            upper_bound=0.4800,
            confidence_level=0.95,
            is_significant=True,
        ),
        reliability="SUFFICIENT",
    )

    initial_actions_count = db_session.query(RecoveryAction).count()
    initial_cases_count = db_session.query(RecoveryCase).count()
    initial_results_count = db_session.query(ActionResult).count()

    def _override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = _override_get_db
    token_admin = create_access_token(user_id="admin_usr", role=UserRole.ADMIN.value)

    with (
        patch.object(
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
        ),
        patch(
            "app.services.action_dispatcher.ActionDispatcher.dispatch_action"
        ) as mock_dispatch,
        patch("app.providers.razorpay.RazorpayActionProvider.execute") as mock_exec,
        TestClient(
            app, headers={"Authorization": f"Bearer {token_admin}"}
        ) as test_client,
    ):
        res = test_client.post(
            f"/api/recovery/intelligence/activations/{act_id}/promote", json={}
        )
        assert res.status_code == 200
        mock_dispatch.assert_not_called()
        mock_exec.assert_not_called()

    app.dependency_overrides.clear()

    # Zero DB changes in operational entities
    assert db_session.query(RecoveryAction).count() == initial_actions_count
    assert db_session.query(RecoveryCase).count() == initial_cases_count
    assert db_session.query(ActionResult).count() == initial_results_count


def test_zero_pii_and_zero_secrets_in_promotion_readiness(
    client: TestClient, db_session: Session
):
    """12. Test that promotion readiness responses contain no PII and no secrets."""
    act_id = setup_standard_canary_activation(db_session)

    res = client.get(
        f"/api/recovery/intelligence/activations/{act_id}/promotion-readiness"
    )
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
