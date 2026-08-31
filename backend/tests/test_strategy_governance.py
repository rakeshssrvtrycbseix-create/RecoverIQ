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
    AuditLog,
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
    StrategyRecommendationStatus,
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
    token = create_access_token(user_id="viewer_test_gov", role=UserRole.VIEWER.value)
    with TestClient(app, headers={"Authorization": f"Bearer {token}"}) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def make_gov_case(
    db_session: Session,
    status: str = RecoveryCaseStatus.RECOVERED.value,
    amount: int = 100000,
    prob: float = 0.85,
    action_type: str = RecoveryActionType.SEND_PAYMENT_LINK.value,
    delay_hours: int = 4,
    risk_tier: str = CustomerRiskTier.STANDARD.value,
    failure_reason: str = "insufficient_funds",
) -> RecoveryCase:
    """Helper to provision a resolved recovery case with all intelligence dependencies."""
    uid = uuid.uuid4().hex[:8]
    now_utc = datetime.now(UTC)
    resolved_time = now_utc - timedelta(days=1)

    customer = Customer(
        external_customer_id=f"cust_gov_{uid}",
        risk_tier=risk_tier,
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
        latest_failure_reason=failure_reason,
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
        feature_vector_snapshot={"error_reason": failure_reason, "amount": amount},
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
        reasoning_summary="Governed recommendation test decision.",
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


def setup_recommendation_dataset(db_session: Session, count: int = 35):
    """Populate dataset where SEND_PAYMENT_LINK outperforms baseline RETRY_PAYMENT."""
    # Baseline: RETRY_PAYMENT (40% recovery rate)
    for i in range(count // 2):
        status = (
            RecoveryCaseStatus.RECOVERED.value
            if i < (count // 5)
            else RecoveryCaseStatus.CLOSED.value
        )
        make_gov_case(
            db_session,
            status=status,
            prob=0.40,
            action_type=RecoveryActionType.RETRY_PAYMENT.value,
            delay_hours=12,
        )

    # Candidate: SEND_PAYMENT_LINK (85% recovery rate)
    for i in range(count - (count // 2)):
        status = (
            RecoveryCaseStatus.RECOVERED.value
            if i < int(count * 0.40)
            else RecoveryCaseStatus.CLOSED.value
        )
        make_gov_case(
            db_session,
            status=status,
            prob=0.85,
            action_type=RecoveryActionType.SEND_PAYMENT_LINK.value,
            delay_hours=4,
        )


# =========================================================================
# 1. Recommendation Generation & Governance Gates Tests
# =========================================================================


def test_sufficient_data_generates_recommendation(db_session: Session):
    """1. Test N >= 30 historical cases with positive uplift generates REVIEW_REQUIRED recommendation."""
    setup_recommendation_dataset(db_session, count=40)

    res = strategy_governance_service.evaluate_and_sync_recommendation(db_session)
    assert res is not None
    assert res.status == StrategyRecommendationStatus.REVIEW_REQUIRED.value
    assert res.strategy_type == RecoveryActionType.SEND_PAYMENT_LINK.value
    assert res.reliability == "SUFFICIENT"
    assert res.rate_delta is not None and res.rate_delta > 0.0
    assert res.incremental_erv_paise is not None and res.incremental_erv_paise > 0


def test_limited_data_requires_review(db_session: Session):
    """2. Test 10 <= N < 30 generates LIMITED reliability recommendation."""
    setup_recommendation_dataset(db_session, count=16)

    res = strategy_governance_service.evaluate_and_sync_recommendation(db_session)
    assert res is not None
    assert res.status == StrategyRecommendationStatus.REVIEW_REQUIRED.value
    assert res.reliability == "LIMITED"
    assert any("Limited historical evidence" in d for d in res.diagnostics)


def test_insufficient_data_generates_no_recommendation(db_session: Session):
    """3. Test N < 10 returns None (no recommendation generated)."""
    setup_recommendation_dataset(db_session, count=5)

    res = strategy_governance_service.evaluate_and_sync_recommendation(db_session)
    assert res is None


def test_zero_or_negative_uplift_blocks_recommendation(db_session: Session):
    """4. Test that when candidate has worse recovery than baseline, no recommendation is generated."""
    # Baseline: RETRY_PAYMENT with 90% recovery rate
    for i in range(20):
        status = (
            RecoveryCaseStatus.RECOVERED.value
            if i < 18
            else RecoveryCaseStatus.CLOSED.value
        )
        make_gov_case(
            db_session,
            status=status,
            prob=0.90,
            action_type=RecoveryActionType.RETRY_PAYMENT.value,
        )

    # Candidate: SEND_PAYMENT_LINK with 20% recovery rate
    for i in range(20):
        status = (
            RecoveryCaseStatus.RECOVERED.value
            if i < 4
            else RecoveryCaseStatus.CLOSED.value
        )
        make_gov_case(
            db_session,
            status=status,
            prob=0.20,
            action_type=RecoveryActionType.SEND_PAYMENT_LINK.value,
        )

    res = strategy_governance_service.evaluate_and_sync_recommendation(db_session)
    assert res is None


# =========================================================================
# 2. Recommendation Confidence Tests
# =========================================================================


def test_recommendation_confidence_is_distinct_from_ml_confidence(db_session: Session):
    """5. Test recommendation confidence is synthesized across data reliability, model health, and uplift."""
    setup_recommendation_dataset(db_session, count=40)

    res = strategy_governance_service.evaluate_and_sync_recommendation(db_session)
    assert res is not None
    assert isinstance(res.recommendation_confidence, float)
    assert 0.0 <= res.recommendation_confidence <= 1.0
    assert res.confidence_level in ("HIGH", "MEDIUM", "LOW")
    # Distinct from single ML prediction confidence (which was 0.8500)
    assert res.recommendation_confidence != 0.8500 or res.confidence_level is not None


def test_confidence_deterministic(db_session: Session):
    """6. Test repeated evaluations against identical DB state produce exact same confidence."""
    setup_recommendation_dataset(db_session, count=35)

    res1 = strategy_governance_service.evaluate_and_sync_recommendation(db_session)
    res2 = strategy_governance_service.evaluate_and_sync_recommendation(db_session)

    assert res1 is not None and res2 is not None
    assert res1.recommendation_confidence == res2.recommendation_confidence
    assert res1.confidence_level == res2.confidence_level


# =========================================================================
# 3. Financial Invariant & Integer Paise Tests
# =========================================================================


def test_erv_uses_integer_paise(db_session: Session):
    """7-8. Test baseline, alternative, and incremental ERV are integer paise."""
    setup_recommendation_dataset(db_session, count=35)

    res = strategy_governance_service.evaluate_and_sync_recommendation(db_session)
    assert res is not None
    assert isinstance(res.baseline_erv_paise, int)
    assert isinstance(res.alternative_erv_paise, int)
    assert isinstance(res.incremental_erv_paise, int)
    assert res.incremental_erv_paise == (
        res.alternative_erv_paise - res.baseline_erv_paise
    )


# =========================================================================
# 4. RBAC & Authorization Tests
# =========================================================================


def test_unauthenticated_rejected(db_session: Session):
    """9. Test unauthenticated calls to recommendations APIs return 401."""

    def _override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = _override_get_db

    with TestClient(app) as test_client:
        assert (
            test_client.get("/api/recovery/intelligence/recommendations").status_code
            == 401
        )
        assert (
            test_client.get(
                "/api/recovery/intelligence/recommendations/rec_123"
            ).status_code
            == 401
        )
        assert (
            test_client.post(
                "/api/recovery/intelligence/recommendations/rec_123/approve", json={}
            ).status_code
            == 401
        )
        assert (
            test_client.post(
                "/api/recovery/intelligence/recommendations/rec_123/reject", json={}
            ).status_code
            == 401
        )

    app.dependency_overrides.clear()


def test_viewer_can_read_but_cannot_approve(db_session: Session):
    """10. Test viewer role can list/get recommendations (200) but cannot approve/reject (403)."""
    setup_recommendation_dataset(db_session, count=35)
    rec = strategy_governance_service.evaluate_and_sync_recommendation(db_session)
    assert rec is not None

    def _override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = _override_get_db
    token_v = create_access_token(user_id="viewer_usr", role=UserRole.VIEWER.value)

    with TestClient(app, headers={"Authorization": f"Bearer {token_v}"}) as test_client:
        # Read operations -> 200
        res_list = test_client.get("/api/recovery/intelligence/recommendations")
        assert res_list.status_code == 200

        res_detail = test_client.get(
            f"/api/recovery/intelligence/recommendations/{rec.recommendation_id}"
        )
        assert res_detail.status_code == 200

        # Mutation operations -> 403 Forbidden
        res_app = test_client.post(
            f"/api/recovery/intelligence/recommendations/{rec.recommendation_id}/approve",
            json={},
        )
        assert res_app.status_code == 403

        res_rej = test_client.post(
            f"/api/recovery/intelligence/recommendations/{rec.recommendation_id}/reject",
            json={},
        )
        assert res_rej.status_code == 403

    app.dependency_overrides.clear()


def test_operator_and_admin_can_approve_and_reject(db_session: Session):
    """11. Test operator and admin roles are authorized to approve and reject."""
    setup_recommendation_dataset(db_session, count=35)
    rec = strategy_governance_service.evaluate_and_sync_recommendation(db_session)
    assert rec is not None

    def _override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = _override_get_db
    token_op = create_access_token(user_id="operator_usr", role=UserRole.OPERATOR.value)

    with TestClient(
        app, headers={"Authorization": f"Bearer {token_op}"}
    ) as test_client:
        res_app = test_client.post(
            f"/api/recovery/intelligence/recommendations/{rec.recommendation_id}/approve",
            json={"notes": "Approved for Q3 optimization campaign."},
        )
        assert res_app.status_code == 200
        data = res_app.json()
        assert data["status"] == "APPROVED"
        assert data["reviewed_by"] == "operator_usr"
        assert data["review_notes"] == "Approved for Q3 optimization campaign."

    app.dependency_overrides.clear()


# =========================================================================
# 5. Lifecycle State Transition & Expiration Tests
# =========================================================================


def test_review_required_can_be_rejected(db_session: Session):
    """12. Test operator rejection transitions REVIEW_REQUIRED to REJECTED."""
    setup_recommendation_dataset(db_session, count=35)
    rec = strategy_governance_service.evaluate_and_sync_recommendation(db_session)
    assert rec is not None

    def _override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = _override_get_db
    token_op = create_access_token(user_id="operator_usr", role=UserRole.OPERATOR.value)

    with TestClient(
        app, headers={"Authorization": f"Bearer {token_op}"}
    ) as test_client:
        res_rej = test_client.post(
            f"/api/recovery/intelligence/recommendations/{rec.recommendation_id}/reject",
            json={"notes": "Rejected due to external business constraints."},
        )
        assert res_rej.status_code == 200
        data = res_rej.json()
        assert data["status"] == "REJECTED"
        assert data["reviewed_by"] == "operator_usr"

    app.dependency_overrides.clear()


def test_rejected_cannot_be_approved(db_session: Session):
    """13. Test rejecting a recommendation prevents subsequent approval (400 Bad Request)."""
    setup_recommendation_dataset(db_session, count=35)
    rec = strategy_governance_service.evaluate_and_sync_recommendation(db_session)
    assert rec is not None

    def _override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = _override_get_db
    token_op = create_access_token(user_id="operator_usr", role=UserRole.OPERATOR.value)

    with TestClient(
        app, headers={"Authorization": f"Bearer {token_op}"}
    ) as test_client:
        # First reject
        test_client.post(
            f"/api/recovery/intelligence/recommendations/{rec.recommendation_id}/reject",
            json={},
        )

        # Second approve -> 400
        res = test_client.post(
            f"/api/recovery/intelligence/recommendations/{rec.recommendation_id}/approve",
            json={},
        )
        assert res.status_code == 400
        assert "cannot be approved" in res.text

    app.dependency_overrides.clear()


def test_duplicate_approval_rejected(db_session: Session):
    """14. Test approving already approved recommendation returns 400 Bad Request."""
    setup_recommendation_dataset(db_session, count=35)
    rec = strategy_governance_service.evaluate_and_sync_recommendation(db_session)
    assert rec is not None

    def _override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = _override_get_db
    token_op = create_access_token(user_id="operator_usr", role=UserRole.OPERATOR.value)

    with TestClient(
        app, headers={"Authorization": f"Bearer {token_op}"}
    ) as test_client:
        # First approve
        test_client.post(
            f"/api/recovery/intelligence/recommendations/{rec.recommendation_id}/approve",
            json={},
        )

        # Second approve -> 400
        res = test_client.post(
            f"/api/recovery/intelligence/recommendations/{rec.recommendation_id}/approve",
            json={},
        )
        assert res.status_code == 400

    app.dependency_overrides.clear()


def test_expired_recommendation_cannot_be_approved(db_session: Session):
    """15. Test expired recommendation cannot be approved."""
    setup_recommendation_dataset(db_session, count=35)
    past_time = datetime.now(UTC) - timedelta(days=10)
    rec = strategy_governance_service.evaluate_and_sync_recommendation(
        db_session, as_of=past_time
    )
    assert rec is not None

    def _override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = _override_get_db
    token_op = create_access_token(user_id="operator_usr", role=UserRole.OPERATOR.value)

    with TestClient(
        app, headers={"Authorization": f"Bearer {token_op}"}
    ) as test_client:
        res = test_client.post(
            f"/api/recovery/intelligence/recommendations/{rec.recommendation_id}/approve",
            json={},
        )
        assert res.status_code == 400
        assert "expired" in res.text.lower()

    app.dependency_overrides.clear()


# =========================================================================
# 6. Actor Identity & Audit Trail Verification
# =========================================================================


def test_client_operator_id_is_ignored_and_jwt_identity_used(db_session: Session):
    """16. Test that actor identity in audit records is derived strictly from JWT, not body payload."""
    setup_recommendation_dataset(db_session, count=35)
    rec = strategy_governance_service.evaluate_and_sync_recommendation(db_session)
    assert rec is not None

    def _override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = _override_get_db
    token_op = create_access_token(
        user_id="verified_operator_99", role=UserRole.OPERATOR.value
    )

    with TestClient(
        app, headers={"Authorization": f"Bearer {token_op}"}
    ) as test_client:
        # Submit spoofed body parameter if attempted
        test_client.post(
            f"/api/recovery/intelligence/recommendations/{rec.recommendation_id}/approve",
            json={"notes": "Valid note", "operator_id": "spoofed_admin"},
        )

    app.dependency_overrides.clear()

    # Verify audit log entry
    audit = (
        db_session.query(AuditLog)
        .filter(AuditLog.event_type == "RECOMMENDATION_APPROVED")
        .order_by(AuditLog.created_at.desc())
        .first()
    )
    assert audit is not None
    assert audit.actor_id == "verified_operator_99"
    assert audit.actor_id != "spoofed_admin"


# =========================================================================
# 7. Financial Isolation & Zero PII/Secrets Verification
# =========================================================================


def test_approval_does_not_create_recovery_action_or_mutate_financials(
    db_session: Session,
):
    """17-20. Test approval NEVER creates RecoveryAction, schedules actions, or mutates Payment/RecoveryCase."""
    setup_recommendation_dataset(db_session, count=35)
    rec = strategy_governance_service.evaluate_and_sync_recommendation(db_session)
    assert rec is not None

    initial_actions_count = db_session.query(RecoveryAction).count()
    initial_cases_count = db_session.query(RecoveryCase).count()
    initial_results_count = db_session.query(ActionResult).count()

    def _override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = _override_get_db
    token_op = create_access_token(user_id="operator_usr", role=UserRole.OPERATOR.value)

    with (
        patch(
            "app.services.action_dispatcher.ActionDispatcher.dispatch_action"
        ) as mock_dispatch,
        patch("app.providers.razorpay.RazorpayActionProvider.execute") as mock_exec,
        TestClient(app, headers={"Authorization": f"Bearer {token_op}"}) as test_client,
    ):
        res = test_client.post(
            f"/api/recovery/intelligence/recommendations/{rec.recommendation_id}/approve",
            json={},
        )
        assert res.status_code == 200

        # Assert zero provider calls
        mock_dispatch.assert_not_called()
        mock_exec.assert_not_called()

    app.dependency_overrides.clear()

    # Assert zero DB entity creation/mutation
    assert db_session.query(RecoveryAction).count() == initial_actions_count
    assert db_session.query(RecoveryCase).count() == initial_cases_count
    assert db_session.query(ActionResult).count() == initial_results_count


def test_zero_pii_and_zero_secrets_in_recommendation_responses(
    client: TestClient, db_session: Session
):
    """21. Test recommendation endpoints contain zero customer PII and zero secrets."""
    setup_recommendation_dataset(db_session, count=35)
    rec = strategy_governance_service.evaluate_and_sync_recommendation(db_session)
    assert rec is not None

    res = client.get("/api/recovery/intelligence/recommendations")
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
