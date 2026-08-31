import uuid
from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import UserRole, create_access_token
from app.main import app
from app.models import (
    AgentDecision,
    AuditActorType,
    AuditLog,
    Customer,
    CustomerRiskTier,
    Payment,
    PaymentStatus,
    PolicyDecision,
    PolicyEvaluationResult,
    RecoveryAction,
    RecoveryActionStatus,
    RecoveryActionType,
    RecoveryCase,
    RecoveryCaseStatus,
    RecoveryStage,
)


@pytest.fixture
def client(db_session: Session):
    """Test client with overridden database session dependency and valid auth token."""

    def _override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = _override_get_db
    token = create_access_token(user_id="op_dash_test", role=UserRole.ADMIN.value)
    with TestClient(app, headers={"Authorization": f"Bearer {token}"}) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def create_sample_case(
    db_session: Session,
    amount: int = 100000,
    recovered_amount: int = 0,
    status: str = RecoveryCaseStatus.OPEN.value,
    policy_result: str = PolicyEvaluationResult.ALLOWED.value,
    with_action: bool = True,
    action_status: str = RecoveryActionStatus.SCHEDULED.value,
) -> tuple[Customer, Payment, RecoveryCase, PolicyDecision, RecoveryAction | None]:
    """Helper to provision complete case fixtures."""
    cust_uid = uuid.uuid4().hex[:8]
    customer = Customer(
        external_customer_id=f"cust_dash_{cust_uid}",
        email_masked="d***h@example.com",
        phone_masked="+91******4444",
        risk_tier=CustomerRiskTier.STANDARD.value,
        total_payments_count=5,
        failed_payments_count=1,
        recovered_payments_count=4,
    )
    db_session.add(customer)
    db_session.flush()

    payment = Payment(
        customer_id=customer.id,
        razorpay_order_id=f"order_dash_{cust_uid}",
        amount=amount,
        currency="INR",
        status=PaymentStatus.FAILED.value,
    )
    db_session.add(payment)
    db_session.flush()

    case = RecoveryCase(
        payment_id=payment.id,
        customer_id=customer.id,
        status=status,
        recovery_stage=RecoveryStage.INITIAL_FAILURE.value,
        amount_at_risk=amount,
        recovered_amount=recovered_amount,
        total_attempts_count=1,
        max_allowed_attempts=3,
        latest_failure_reason="insufficient_funds",
    )
    db_session.add(case)
    db_session.flush()

    agent_dec = AgentDecision(
        recovery_case_id=case.id,
        agent_name="RecoveryOrchestrator",
        agent_version="v1.0",
        prompt_template_version="recovery_agent_v1.0",
        proposed_action_type=RecoveryActionType.RETRY_PAYMENT.value,
        confidence_score=Decimal("0.88"),
        reasoning_summary="Optimal time for retry based on historical pattern.",
        suggested_payload={"channel": "GATEWAY_API"},
    )
    db_session.add(agent_dec)
    db_session.flush()

    pol_dec = PolicyDecision(
        recovery_case_id=case.id,
        agent_decision_id=agent_dec.id,
        evaluation_result=policy_result,
        policy_engine_version="policy_v1.0",
        triggered_rule_code="RULE_RETRY_LIMIT" if policy_result != "ALLOWED" else None,
        rule_name="Retry Safety Rule",
        decision_reason="Evaluation completed.",
    )
    db_session.add(pol_dec)
    db_session.flush()

    action = None
    if with_action and policy_result == PolicyEvaluationResult.ALLOWED.value:
        action = RecoveryAction(
            recovery_case_id=case.id,
            policy_decision_id=pol_dec.id,
            action_idempotency_key=f"act_dash_{case.id}_{pol_dec.id}_{uuid.uuid4().hex[:6]}",
            action_type=RecoveryActionType.RETRY_PAYMENT.value,
            status=action_status,
            scheduled_for=datetime.now(UTC) + timedelta(hours=1),
            action_payload={"channel": "GATEWAY_API"},
        )
        db_session.add(action)

    audit = AuditLog(
        event_type="CASE_CREATED",
        actor_type=AuditActorType.SYSTEM_EVENT.value,
        actor_id="test_suite",
        recovery_case_id=case.id,
        entity_type="recovery_cases",
        entity_id=case.id,
        action="CASE_CREATED",
    )
    db_session.add(audit)
    db_session.commit()

    return customer, payment, case, pol_dec, action


# =========================================================================
# 1. Metrics API Tests
# =========================================================================


def test_get_metrics_empty_database(client: TestClient):
    """Test metrics calculation on empty database returns zero values cleanly."""
    response = client.get("/api/recovery/metrics")
    assert response.status_code == 200
    data = response.json()

    assert data["cases"]["total"] == 0
    assert data["cases"]["active"] == 0
    assert data["financial"]["amount_at_risk"] == 0
    assert data["financial"]["amount_recovered"] == 0
    assert data["financial"]["recovery_rate_pct"] == 0.0
    assert data["actions"]["total"] == 0
    assert data["policy"]["total"] == 0
    assert data["failure_reasons"] == []
    assert data["action_types"] == []


def test_get_metrics_aggregated_values(client: TestClient, db_session: Session):
    """Test metrics aggregation with active, recovered, and human review cases."""
    # Case 1: Active case (1000 INR at risk)
    create_sample_case(db_session, amount=100000, recovered_amount=0, status="OPEN")
    # Case 2: Recovered case (2000 INR at risk, 2000 INR recovered)
    create_sample_case(
        db_session, amount=200000, recovered_amount=200000, status="RECOVERED"
    )
    # Case 3: Human Review case (5000 INR at risk)
    create_sample_case(
        db_session,
        amount=500000,
        recovered_amount=0,
        status="OPEN",
        policy_result="HUMAN_REVIEW",
        with_action=False,
    )

    response = client.get("/api/recovery/metrics")
    assert response.status_code == 200
    data = response.json()

    assert data["cases"]["total"] == 3
    assert data["cases"]["active"] == 2
    assert data["cases"]["recovered"] == 1

    assert data["financial"]["amount_at_risk"] == 800000
    assert data["financial"]["amount_recovered"] == 200000
    assert data["financial"]["recovery_rate_pct"] == 25.0

    assert data["policy"]["allowed"] == 2
    assert data["policy"]["human_review"] == 1
    assert data["policy"]["total"] == 3


def test_metrics_contains_zero_pii_or_secrets(client: TestClient, db_session: Session):
    """Test that metrics response payload contains zero personal data or credentials."""
    create_sample_case(db_session)
    response = client.get("/api/recovery/metrics")
    assert response.status_code == 200
    text = response.text.lower()

    assert "secret" not in text
    assert "password" not in text
    assert "token" not in text
    assert "@example.com" not in text
    assert "+91" not in text


# =========================================================================
# 2. Recovery Cases Listing & Detail Tests
# =========================================================================


def test_list_recovery_cases_pagination(client: TestClient, db_session: Session):
    """Test paginated retrieval of recovery cases."""
    for _ in range(5):
        create_sample_case(db_session)

    response = client.get("/api/recovery/cases?page=1&page_size=3")
    assert response.status_code == 200
    data = response.json()

    assert len(data["items"]) == 3
    assert data["total"] == 5
    assert data["page"] == 1
    assert data["page_size"] == 3
    assert data["total_pages"] == 2


def test_list_recovery_cases_filtering(client: TestClient, db_session: Session):
    """Test recovery case filtering by status."""
    create_sample_case(db_session, status="OPEN")
    create_sample_case(db_session, status="RECOVERED")

    # Filter for OPEN
    res_open = client.get("/api/recovery/cases?status=OPEN")
    assert res_open.status_code == 200
    assert len(res_open.json()["items"]) == 1
    assert res_open.json()["items"][0]["status"] == "OPEN"

    # Filter for RECOVERED
    res_rec = client.get("/api/recovery/cases?status=RECOVERED")
    assert res_rec.status_code == 200
    assert len(res_rec.json()["items"]) == 1
    assert res_rec.json()["items"][0]["status"] == "RECOVERED"


def test_get_recovery_case_detail_complete_trail(
    client: TestClient, db_session: Session
):
    """Test retrieving complete case detail lifecycle trail."""
    _, _, case, _, action = create_sample_case(db_session)

    response = client.get(f"/api/recovery/cases/{case.id}")
    assert response.status_code == 200
    data = response.json()

    assert data["case"]["id"] == str(case.id)
    assert data["payment"]["amount"] == case.amount_at_risk
    assert data["customer"]["external_customer_id"].startswith("cust_dash_")
    assert "email_masked" not in data["customer"]
    assert len(data["agent_decisions"]) >= 1
    assert len(data["policy_decisions"]) >= 1
    assert len(data["actions"]) >= 1
    assert len(data["audit_logs"]) >= 1


def test_get_recovery_case_detail_not_found(client: TestClient):
    """Test 404 response for non-existent case ID."""
    fake_id = uuid.uuid4()
    response = client.get(f"/api/recovery/cases/{fake_id}")
    assert response.status_code == 404


# =========================================================================
# 3. Human Review Queue & Actions Tests
# =========================================================================


def test_human_review_queue_filters_eligible_cases_only(
    client: TestClient, db_session: Session
):
    """Test that human review queue only shows active cases with HUMAN_REVIEW outcome."""
    # Case 1: ALLOWED case (not in review queue)
    create_sample_case(db_session, policy_result="ALLOWED")
    # Case 2: HUMAN_REVIEW case (should appear)
    _, _, review_case, _, _ = create_sample_case(
        db_session, policy_result="HUMAN_REVIEW", with_action=False
    )

    response = client.get("/api/recovery/human-review")
    assert response.status_code == 200
    data = response.json()

    assert data["total"] == 1
    assert data["items"][0]["case_id"] == str(review_case.id)
    assert data["items"][0]["triggered_rule_code"] == "RULE_RETRY_LIMIT"


def test_approve_human_review_success(client: TestClient, db_session: Session):
    """Test human operator approval creates ALLOWED PolicyDecision, schedules action, and logs audit."""
    _, _, review_case, _, _ = create_sample_case(
        db_session, policy_result="HUMAN_REVIEW", with_action=False
    )

    payload = {
        "operator_id": "operator_alice",
        "notes": "Reviewed with customer success. Authorized retry.",
    }
    response = client.post(
        f"/api/recovery/human-review/{review_case.id}/approve",
        json=payload,
    )
    assert response.status_code == 200
    data = response.json()

    assert data["success"] is True
    assert data["action"] == "APPROVED"
    assert data["scheduled_action_id"] is not None

    # Verify new action created in SCHEDULED state
    scheduled_action = (
        db_session.query(RecoveryAction)
        .filter_by(id=uuid.UUID(data["scheduled_action_id"]))
        .first()
    )
    assert scheduled_action is not None
    assert scheduled_action.status == RecoveryActionStatus.SCHEDULED.value

    # Verify AuditLog created with verified authenticated identity
    audit = (
        db_session.query(AuditLog)
        .filter_by(
            recovery_case_id=review_case.id,
            event_type="HUMAN_REVIEW_APPROVED",
        )
        .first()
    )
    assert audit is not None
    assert audit.actor_id == "op_dash_test"


def test_dismiss_human_review_success(client: TestClient, db_session: Session):
    """Test human operator dismissal creates BLOCKED decision and logs audit."""
    _, _, review_case, _, _ = create_sample_case(
        db_session, policy_result="HUMAN_REVIEW", with_action=False
    )

    payload = {
        "notes": "Customer requested cancellation. Dismissing recovery attempt.",
    }
    response = client.post(
        f"/api/recovery/human-review/{review_case.id}/dismiss",
        json=payload,
    )
    assert response.status_code == 200
    data = response.json()

    assert data["success"] is True
    assert data["action"] == "DISMISSED"
    assert data["scheduled_action_id"] is None

    # Verify AuditLog created with verified authenticated identity
    audit = (
        db_session.query(AuditLog)
        .filter_by(
            recovery_case_id=review_case.id,
            event_type="HUMAN_REVIEW_DISMISSED",
        )
        .first()
    )
    assert audit is not None
    assert audit.actor_id == "op_dash_test"


def test_duplicate_human_review_prevention(client: TestClient, db_session: Session):
    """Test that a case already approved cannot be approved again."""
    _, _, review_case, _, _ = create_sample_case(
        db_session, policy_result="HUMAN_REVIEW", with_action=False
    )

    payload = {"operator_id": "operator_alice", "notes": "First approval"}
    res1 = client.post(
        f"/api/recovery/human-review/{review_case.id}/approve",
        json=payload,
    )
    assert res1.status_code == 200

    # Second approval attempt should be rejected
    res2 = client.post(
        f"/api/recovery/human-review/{review_case.id}/approve",
        json=payload,
    )
    assert res2.status_code == 400
    assert (
        "already has an active action" in res2.json()["detail"]
        or "does not have an active HUMAN_REVIEW" in res2.json()["detail"]
    )


# =========================================================================
# 4. Audit Logs API Tests
# =========================================================================


def test_list_audit_logs_pagination_and_filtering(
    client: TestClient, db_session: Session
):
    """Test retrieving and filtering audit logs."""
    _, _, case1, _, _ = create_sample_case(db_session)
    _, _, case2, _, _ = create_sample_case(db_session)

    # Filter by case 1
    res = client.get(f"/api/recovery/audit-logs?case_id={case1.id}")
    assert res.status_code == 200
    data = res.json()
    assert len(data["items"]) >= 1
    assert all(i["entity_id"] == str(case1.id) for i in data["items"])


# =========================================================================
# 5. Security & Architecture Audit Tests
# =========================================================================


def test_approve_after_dismiss_rejected(client: TestClient, db_session: Session):
    """Test that attempting to approve a previously dismissed case is rejected."""
    _, _, review_case, _, _ = create_sample_case(
        db_session, policy_result="HUMAN_REVIEW", with_action=False
    )

    # 1. Dismiss case
    res_dismiss = client.post(
        f"/api/recovery/human-review/{review_case.id}/dismiss",
        json={"operator_id": "op_bob", "notes": "Dismissed due to dispute"},
    )
    assert res_dismiss.status_code == 200

    # 2. Attempt approve
    res_approve = client.post(
        f"/api/recovery/human-review/{review_case.id}/approve",
        json={"operator_id": "op_alice", "notes": "Attempt approve after dismiss"},
    )
    assert res_approve.status_code == 400
    assert "does not have an active HUMAN_REVIEW" in res_approve.json()["detail"]


def test_dismiss_after_approve_rejected(client: TestClient, db_session: Session):
    """Test that attempting to dismiss an already approved case is rejected."""
    _, _, review_case, _, _ = create_sample_case(
        db_session, policy_result="HUMAN_REVIEW", with_action=False
    )

    # 1. Approve case
    res_approve = client.post(
        f"/api/recovery/human-review/{review_case.id}/approve",
        json={"operator_id": "op_alice", "notes": "Authorized retry"},
    )
    assert res_approve.status_code == 200

    # 2. Attempt dismiss
    res_dismiss = client.post(
        f"/api/recovery/human-review/{review_case.id}/dismiss",
        json={"operator_id": "op_bob", "notes": "Attempt dismiss after approve"},
    )
    assert res_dismiss.status_code == 400
    assert (
        "already has an active action" in res_dismiss.json()["detail"]
        or "does not have an active HUMAN_REVIEW" in res_dismiss.json()["detail"]
    )


def test_human_approval_creates_policy_decision_not_direct_gateway_call(
    client: TestClient, db_session: Session
):
    """Test that human approval creates an authorized PolicyDecision and leaves action in SCHEDULED."""
    _, _, review_case, _, _ = create_sample_case(
        db_session, policy_result="HUMAN_REVIEW", with_action=False
    )

    res = client.post(
        f"/api/recovery/human-review/{review_case.id}/approve",
        json={"operator_id": "op_charlie", "notes": "Policy cleared by supervisor"},
    )
    assert res.status_code == 200
    data = res.json()

    # Verify PolicyDecision record was created
    approved_pol = (
        db_session.query(PolicyDecision)
        .filter_by(
            recovery_case_id=review_case.id,
            evaluation_result=PolicyEvaluationResult.ALLOWED.value,
        )
        .first()
    )
    assert approved_pol is not None
    assert approved_pol.triggered_rule_code == "HUMAN_OVERRIDE_APPROVED"
    assert approved_pol.rule_name == "Human Review Operator Approval"

    # Verify action is SCHEDULED, not EXECUTING or COMPLETED (gateway not called synchronously)
    action = (
        db_session.query(RecoveryAction)
        .filter_by(id=uuid.UUID(data["scheduled_action_id"]))
        .first()
    )
    assert action is not None
    assert action.status == RecoveryActionStatus.SCHEDULED.value


def test_zero_pii_across_all_dashboard_api_endpoints(
    client: TestClient, db_session: Session
):
    """Test that all dashboard API endpoints strictly mask or omit personal data."""
    cust, pay, case, _, _ = create_sample_case(db_session)

    endpoints = [
        "/api/recovery/metrics",
        "/api/recovery/cases",
        f"/api/recovery/cases/{case.id}",
        "/api/recovery/human-review",
        "/api/recovery/audit-logs",
    ]

    for ep in endpoints:
        res = client.get(ep)
        assert res.status_code == 200
        text = res.text

        # Raw PAN, full email, raw passwords, or secrets must not appear
        assert "password" not in text.lower()
        assert "secret" not in text.lower()
        assert "411111111111" not in text  # Example test card PAN full number
        assert "cvv" not in text.lower()


def test_unauthenticated_request_audit(db_session: Session):
    """
    Test that human-review endpoints now enforce authentication and reject
    unauthenticated requests with 401 Unauthorized.
    """

    def _override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = _override_get_db
    _, _, review_case, _, _ = create_sample_case(
        db_session, policy_result="HUMAN_REVIEW", with_action=False
    )

    with TestClient(app) as unauth_client:
        res = unauth_client.post(
            f"/api/recovery/human-review/{review_case.id}/approve",
            json={"notes": "Unauthenticated attempt"},
        )
        assert res.status_code == 401
        assert "Authentication required" in res.json()["detail"]
    app.dependency_overrides.clear()
