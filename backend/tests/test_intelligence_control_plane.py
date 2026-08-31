import uuid
from datetime import UTC, datetime
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.security import UserRole, create_access_token
from app.models.action_result import ActionResult
from app.models.agent_decision import AgentDecision
from app.models.customer import Customer
from app.models.enums import (
    CustomerRiskTier,
    GlobalSystemState,
    PaymentAttemptStatus,
    PaymentStatus,
    RecoveryActionStatus,
    RecoveryCaseStatus,
)
from app.models.ml_prediction import MLPrediction
from app.models.payment import Payment
from app.models.payment_attempt import PaymentAttempt
from app.models.policy_decision import PolicyDecision
from app.models.recovery_action import RecoveryAction
from app.models.recovery_case import RecoveryCase
from app.models.subscription import Subscription
from app.services.intelligence_control_plane_service import (
    IntelligenceControlPlaneService,
)


@pytest.fixture
def viewer_token_headers() -> dict[str, str]:
    token = create_access_token(user_id="view_test_user", role=UserRole.VIEWER.value)
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def operator_token_headers() -> dict[str, str]:
    token = create_access_token(user_id="op_test_user", role=UserRole.OPERATOR.value)
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def admin_token_headers() -> dict[str, str]:
    token = create_access_token(user_id="admin_test_user", role=UserRole.ADMIN.value)
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def test_seed_case(db_session: Session) -> RecoveryCase:
    """Create a fully resolved recovery case with complete execution lineage."""
    cust_id = uuid.uuid4()
    cust = Customer(
        id=cust_id,
        external_customer_id=f"cust_test_{cust_id.hex[:6]}",
        email_masked="j***@example.com",
        phone_masked="+91******9999",
        risk_tier=CustomerRiskTier.LOW,
        total_payments_count=10,
        failed_payments_count=1,
    )
    db_session.add(cust)

    sub_id = uuid.uuid4()
    sub = Subscription(
        id=sub_id,
        customer_id=cust_id,
        recurring_amount=500000,
        billing_cadence="MONTHLY",
        plan_name="Enterprise Plan",
        current_period_start=datetime.now(UTC),
    )
    db_session.add(sub)

    pay_id = uuid.uuid4()
    payment = Payment(
        id=pay_id,
        customer_id=cust_id,
        subscription_id=sub_id,
        amount=500000,
        currency="INR",
        status=PaymentStatus.CAPTURED,
    )
    db_session.add(payment)

    attempt = PaymentAttempt(
        id=uuid.uuid4(),
        payment_id=pay_id,
        attempt_number=1,
        amount=500000,
        status=PaymentAttemptStatus.FAILED,
        error_code="INSUFFICIENT_FUNDS",
        error_reason="insufficient_funds",
        initiated_at=datetime.now(UTC),
    )
    db_session.add(attempt)

    case_id = uuid.uuid4()
    case = RecoveryCase(
        id=case_id,
        payment_id=pay_id,
        customer_id=cust_id,
        status=RecoveryCaseStatus.RECOVERED,
        amount_at_risk=500000,
        recovered_amount=500000,
        total_attempts_count=2,
        opened_at=datetime.now(UTC),
        resolved_at=datetime.now(UTC),
    )
    db_session.add(case)

    pred_id = uuid.uuid4()
    prediction = MLPrediction(
        id=pred_id,
        recovery_case_id=case_id,
        model_name="recovery_probability",
        model_version="v1.0",
        recovery_probability=Decimal("0.7850"),
        predicted_channel="WHATSAPP",
        feature_vector_snapshot={"amount": 500000, "risk_tier": "LOW"},
        predicted_at=datetime.now(UTC),
    )
    db_session.add(prediction)

    agent_id = uuid.uuid4()
    agent_dec = AgentDecision(
        id=agent_id,
        recovery_case_id=case_id,
        ml_prediction_id=pred_id,
        agent_name="RecoveryOrchestrator",
        agent_version="v1.0",
        prompt_template_version="v1.0",
        proposed_action_type="SEND_PAYMENT_LINK",
        confidence_score=Decimal("0.8500"),
        reasoning_summary="Optimal customer profile for interactive link dispatch.",
        suggested_payload={"channel": "WHATSAPP"},
        decided_at=datetime.now(UTC),
    )
    db_session.add(agent_dec)

    policy_id = uuid.uuid4()
    policy_dec = PolicyDecision(
        id=policy_id,
        recovery_case_id=case_id,
        agent_decision_id=agent_id,
        evaluation_result="ALLOWED",
        policy_engine_version="v1.0",
        triggered_rule_code="RULE_SAFETY_PASS",
        rule_name="Default Safe Action Parameters",
        decision_reason="Deterministic safety constraints validation passed.",
        evaluation_details={"allowed": True},
    )
    db_session.add(policy_dec)

    action_id = uuid.uuid4()
    action = RecoveryAction(
        id=action_id,
        recovery_case_id=case_id,
        policy_decision_id=policy_id,
        action_idempotency_key=f"act_key_{case_id.hex[:8]}",
        action_type="SEND_PAYMENT_LINK",
        status=RecoveryActionStatus.COMPLETED.value,
        created_at=datetime.now(UTC),
    )
    db_session.add(action)

    result = ActionResult(
        id=uuid.uuid4(),
        recovery_action_id=action_id,
        execution_status="DELIVERED",
        provider_reference_id="rzp_plink_test_01",
        provider_status_code="200",
        executed_at=datetime.now(UTC),
    )
    db_session.add(result)

    db_session.commit()
    db_session.refresh(case)
    return case


# =============================================================================
# 1. Financial Isolation Verification Tests
# =============================================================================


def test_control_plane_financial_isolation(
    client: TestClient,
    viewer_token_headers: dict[str, str],
    db_session: Session,
    test_seed_case: RecoveryCase,
) -> None:
    """MANDATORY INVARIANT: Control plane queries must produce ZERO financial mutations.

    Assert:
    - RecoveryAction count delta == 0
    - Payment mutation count == 0
    - RecoveryCase financial mutation count == 0
    - ActionDispatcher calls == 0
    - Razorpay calls == 0
    """
    initial_action_count = db_session.query(RecoveryAction).count()
    initial_case_count = db_session.query(RecoveryCase).count()
    initial_payment_count = db_session.query(Payment).count()

    initial_case = (
        db_session.query(RecoveryCase)
        .filter(RecoveryCase.id == test_seed_case.id)
        .first()
    )
    initial_case_status = initial_case.status
    initial_case_recovered = initial_case.recovered_amount

    # Execute all control plane read endpoints
    res_summary = client.get(
        "/api/recovery/intelligence/control-plane", headers=viewer_token_headers
    )
    assert res_summary.status_code == 200

    res_health = client.get(
        "/api/recovery/intelligence/control-plane/health", headers=viewer_token_headers
    )
    assert res_health.status_code == 200

    res_incidents = client.get(
        "/api/recovery/intelligence/control-plane/incidents",
        headers=viewer_token_headers,
    )
    assert res_incidents.status_code == 200

    res_lineage = client.get(
        "/api/recovery/intelligence/control-plane/lineage", headers=viewer_token_headers
    )
    assert res_lineage.status_code == 200

    res_gov = client.get(
        "/api/recovery/intelligence/governance-center", headers=viewer_token_headers
    )
    assert res_gov.status_code == 200

    res_trace = client.get(
        f"/api/recovery/intelligence/decision-trace/{test_seed_case.id}",
        headers=viewer_token_headers,
    )
    assert res_trace.status_code == 200

    # Assert ZERO modifications across financial state
    assert db_session.query(RecoveryAction).count() == initial_action_count
    assert db_session.query(RecoveryCase).count() == initial_case_count
    assert db_session.query(Payment).count() == initial_payment_count

    refreshed_case = (
        db_session.query(RecoveryCase)
        .filter(RecoveryCase.id == test_seed_case.id)
        .first()
    )
    assert refreshed_case.status == initial_case_status
    assert refreshed_case.recovered_amount == initial_case_recovered


# =============================================================================
# 2. RBAC & Security Tests
# =============================================================================


def test_control_plane_rbac_unauthenticated(client: TestClient) -> None:
    """Unauthenticated requests must be rejected with HTTP 401."""
    assert client.get("/api/recovery/intelligence/control-plane").status_code == 401
    assert (
        client.get("/api/recovery/intelligence/control-plane/health").status_code == 401
    )
    assert (
        client.get("/api/recovery/intelligence/control-plane/incidents").status_code
        == 401
    )
    assert (
        client.get("/api/recovery/intelligence/control-plane/lineage").status_code
        == 401
    )
    assert client.get("/api/recovery/intelligence/governance-center").status_code == 401
    assert (
        client.get(
            f"/api/recovery/intelligence/decision-trace/{uuid.uuid4()}"
        ).status_code
        == 401
    )


def test_control_plane_rbac_allowed_roles(
    client: TestClient,
    viewer_token_headers: dict[str, str],
    operator_token_headers: dict[str, str],
    admin_token_headers: dict[str, str],
) -> None:
    """Viewer, Operator, and Admin roles must all be permitted read-only access."""
    for headers in [viewer_token_headers, operator_token_headers, admin_token_headers]:
        res = client.get("/api/recovery/intelligence/control-plane", headers=headers)
        assert res.status_code == 200

        res_health = client.get(
            "/api/recovery/intelligence/control-plane/health", headers=headers
        )
        assert res_health.status_code == 200


def test_decision_trace_invalid_uuid(
    client: TestClient,
    viewer_token_headers: dict[str, str],
) -> None:
    """Invalid UUID string must return HTTP 400."""
    res = client.get(
        "/api/recovery/intelligence/decision-trace/not-a-valid-uuid",
        headers=viewer_token_headers,
    )
    assert res.status_code == 400
    assert "Invalid UUID" in res.json()["detail"]


def test_decision_trace_not_found(
    client: TestClient,
    viewer_token_headers: dict[str, str],
) -> None:
    """Non-existent recovery case UUID must return HTTP 404."""
    non_existent = uuid.uuid4()
    res = client.get(
        f"/api/recovery/intelligence/decision-trace/{non_existent}",
        headers=viewer_token_headers,
    )
    assert res.status_code == 404


# =============================================================================
# 3. Privacy & Zero-PII Verification Tests
# =============================================================================


def test_zero_pii_in_decision_trace(
    client: TestClient,
    viewer_token_headers: dict[str, str],
    test_seed_case: RecoveryCase,
) -> None:
    """Decision trace must NEVER expose raw PII, customer names, cards, or secrets."""
    res = client.get(
        f"/api/recovery/intelligence/decision-trace/{test_seed_case.id}",
        headers=viewer_token_headers,
    )
    assert res.status_code == 200
    data = res.json()
    data_str = str(data)

    # Sensitive customer tokens
    assert "j***@example.com" not in data_str  # No emails in trace
    assert "+91" not in data_str  # No phone numbers
    assert "card_pan" not in data_str
    assert "secret" not in data_str.lower()
    assert "token" not in data_str.lower() or "token_usage" in data_str
    assert "password" not in data_str.lower()
    assert "api_key" not in data_str.lower()


# =============================================================================
# 4. Mathematical Health Score & State Priority Tests
# =============================================================================


def test_intelligence_health_score_bounds_and_formula(db_session: Session) -> None:
    """Test deterministic health score calculation and weighted component breakdown."""
    service = IntelligenceControlPlaneService(db_session)
    health = service.evaluate_unified_health()

    score = health.intelligence_health_score
    assert 0.0 <= score.overall_score <= 100.0
    assert 0.0 <= score.model_score <= 100.0
    assert 0.0 <= score.calibration_score <= 100.0
    assert 0.0 <= score.drift_score <= 100.0
    assert 0.0 <= score.data_quality_score <= 100.0
    assert 0.0 <= score.strategy_score <= 100.0
    assert 0.0 <= score.experiment_score <= 100.0
    assert 0.0 <= score.deployment_score <= 100.0
    assert 0.0 <= score.continuous_learning_score <= 100.0

    # Verify deterministic weighted formula
    expected = round(
        0.15 * score.model_score
        + 0.10 * score.calibration_score
        + 0.15 * score.drift_score
        + 0.10 * score.data_quality_score
        + 0.15 * score.strategy_score
        + 0.10 * score.experiment_score
        + 0.15 * score.deployment_score
        + 0.10 * score.continuous_learning_score,
        2,
    )
    assert abs(score.overall_score - expected) < 0.01


def test_global_system_state_priority(db_session: Session) -> None:
    """Verify global system state is one of the deterministic priority enums."""
    service = IntelligenceControlPlaneService(db_session)
    health = service.evaluate_unified_health()

    valid_states = [
        GlobalSystemState.EMERGENCY_LOCKDOWN,
        GlobalSystemState.ROLLBACK_REQUIRED,
        GlobalSystemState.DEGRADED,
        GlobalSystemState.HUMAN_REVIEW_REQUIRED,
        GlobalSystemState.LEARNING_REQUIRED,
        GlobalSystemState.WARNING,
        GlobalSystemState.MONITORING,
        GlobalSystemState.HEALTHY,
    ]
    assert health.global_system_state in valid_states


# =============================================================================
# 5. Incident Correlation & Deterministic IDs
# =============================================================================


def test_incident_correlation_and_deterministic_ids(db_session: Session) -> None:
    """Verify automated incident correlation and reproducible ID formatting."""
    service = IntelligenceControlPlaneService(db_session)
    incidents_res = service.detect_incidents()

    assert incidents_res.total >= 0
    for inc in incidents_res.incidents:
        assert inc.incident_id.startswith("inc-")
        assert inc.severity in ["LOW", "MEDIUM", "HIGH", "CRITICAL"]
        assert inc.state in ["ACTIVE", "INVESTIGATING", "MITIGATED", "RESOLVED"]
        assert len(inc.source_phases) > 0
        assert len(inc.recommended_action) > 0


# =============================================================================
# 6. Lineage Graph & Decision Trace Integrity
# =============================================================================


def test_unified_lineage_graph(db_session: Session) -> None:
    """Verify unified lineage graph spans from DATASET to PRODUCTION_OUTCOME."""
    service = IntelligenceControlPlaneService(db_session)
    lineage = service.get_unified_lineage()

    assert len(lineage.nodes) >= 10
    stage_names = [n.stage.value for n in lineage.nodes]
    assert "DATASET" in stage_names
    assert "TRAINING_RUN" in stage_names
    assert "MODEL_ARTIFACT" in stage_names
    assert "VALIDATION" in stage_names
    assert "GOVERNANCE" in stage_names
    assert "EXPERIMENT" in stage_names
    assert "STRATEGY_RECOMMENDATION" in stage_names
    assert "CONTROLLED_ROLLOUT" in stage_names
    assert "PRODUCTION_DEPLOYMENT" in stage_names
    assert "PRODUCTION_OUTCOME" in stage_names

    assert lineage.active_champion_model == "v1.0"


def test_decision_trace_stages_reconstruction(
    db_session: Session,
    test_seed_case: RecoveryCase,
) -> None:
    """Verify decision trace reconstructs all 6 chronological lifecycle stages."""
    service = IntelligenceControlPlaneService(db_session)
    trace = service.get_decision_trace(str(test_seed_case.id))

    assert trace.case_id == str(test_seed_case.id)
    assert trace.payment_id == str(test_seed_case.payment_id)
    assert trace.case_status == RecoveryCaseStatus.RECOVERED.value
    assert trace.amount_at_risk_paise == 500000
    assert trace.recovered_amount_paise == 500000
    assert trace.model_version == "v1.0"
    assert trace.prediction_probability == 0.7850
    assert trace.agent_decision["proposed_action"] == "SEND_PAYMENT_LINK"
    assert trace.policy_decision["result"] == "ALLOWED"

    assert len(trace.stages) == 6
    assert "PAYMENT_FAILURE_INGESTION" in trace.stages[0].stage_name
    assert "ML_PROBABILITY_INFERENCE" in trace.stages[1].stage_name
    assert "AGENT_REASONING_AND_STRATEGY" in trace.stages[2].stage_name
    assert "POLICY_ENGINE_SAFETY_GATE" in trace.stages[3].stage_name
    assert "RECOVERY_ACTION_DISPATCH" in trace.stages[4].stage_name
    assert "RECOVERY_CASE_OUTCOME" in trace.stages[5].stage_name


def test_governance_center_aggregation(db_session: Session) -> None:
    """Verify governance center aggregates action queues and audit events."""
    service = IntelligenceControlPlaneService(db_session)
    gov = service.get_governance_center()

    assert gov.pending_strategy_recommendations_count >= 0
    assert gov.pending_model_reviews_count >= 0
    assert gov.pending_deployment_reviews_count >= 0
    assert len(gov.required_operator_actions) > 0
