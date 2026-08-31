import uuid
from datetime import timedelta
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import UserRole, create_access_token
from app.main import app
from app.models import (
    AgentDecision,
    AuditLog,
    Customer,
    CustomerRiskTier,
    Payment,
    PaymentStatus,
    PolicyDecision,
    PolicyEvaluationResult,
    RecoveryActionType,
    RecoveryCase,
    RecoveryCaseStatus,
    RecoveryStage,
)


@pytest.fixture
def client(db_session: Session):
    """Test client with overridden database session dependency."""

    def _override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = _override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def make_auth_headers(
    user_id: str = "op_test_1", role: str = UserRole.OPERATOR.value
) -> dict[str, str]:
    """Helper to generate Authorization header with valid signed JWT."""
    token = create_access_token(user_id=user_id, role=role)
    return {"Authorization": f"Bearer {token}"}


def create_sample_review_case(
    db_session: Session,
    amount: int = 250000,
) -> tuple[Customer, Payment, RecoveryCase, PolicyDecision]:
    """Helper to provision a case in active HUMAN_REVIEW state."""
    cust_uid = uuid.uuid4().hex[:8]
    customer = Customer(
        external_customer_id=f"cust_sec_{cust_uid}",
        email_masked="s***y@example.com",
        phone_masked="+91******8888",
        risk_tier=CustomerRiskTier.HIGH.value,
        total_payments_count=3,
        failed_payments_count=1,
        recovered_payments_count=2,
    )
    db_session.add(customer)
    db_session.flush()

    payment = Payment(
        customer_id=customer.id,
        razorpay_order_id=f"order_sec_{cust_uid}",
        amount=amount,
        currency="INR",
        status=PaymentStatus.FAILED.value,
    )
    db_session.add(payment)
    db_session.flush()

    case = RecoveryCase(
        payment_id=payment.id,
        customer_id=customer.id,
        status=RecoveryCaseStatus.OPEN.value,
        recovery_stage=RecoveryStage.INITIAL_FAILURE.value,
        amount_at_risk=amount,
        recovered_amount=0,
        total_attempts_count=1,
        max_allowed_attempts=3,
        latest_failure_reason="high_risk_flagged",
    )
    db_session.add(case)
    db_session.flush()

    agent_dec = AgentDecision(
        recovery_case_id=case.id,
        agent_name="RecoveryOrchestrator",
        agent_version="v1.0",
        prompt_template_version="recovery_agent_v1.0",
        proposed_action_type=RecoveryActionType.RETRY_PAYMENT.value,
        confidence_score=Decimal("0.85"),
        reasoning_summary="Flagged for high value review before retry.",
        suggested_payload={"channel": "GATEWAY_API"},
    )
    db_session.add(agent_dec)
    db_session.flush()

    pol_dec = PolicyDecision(
        recovery_case_id=case.id,
        agent_decision_id=agent_dec.id,
        evaluation_result=PolicyEvaluationResult.HUMAN_REVIEW.value,
        policy_engine_version="policy_v1.0",
        triggered_rule_code="RULE_HIGH_VALUE_TRANSACTION",
        rule_name="High Value Safety Review",
        decision_reason="Transaction value exceeds automatic threshold.",
    )
    db_session.add(pol_dec)
    db_session.commit()

    return customer, payment, case, pol_dec


# =========================================================================
# 1. Unauthenticated Access Tests (401 Unauthorized)
# =========================================================================


def test_unauthenticated_get_metrics_rejected(client: TestClient):
    """1. Test unauthenticated request to /metrics is rejected with 401."""
    res = client.get("/api/recovery/metrics")
    assert res.status_code == 401
    assert "Authentication required" in res.json()["detail"]


def test_unauthenticated_get_cases_rejected(client: TestClient):
    """2. Test unauthenticated request to /cases is rejected with 401."""
    res = client.get("/api/recovery/cases")
    assert res.status_code == 401


def test_unauthenticated_get_human_review_rejected(client: TestClient):
    """3. Test unauthenticated request to /human-review is rejected with 401."""
    res = client.get("/api/recovery/human-review")
    assert res.status_code == 401


def test_unauthenticated_post_approve_rejected(client: TestClient, db_session: Session):
    """4. Test unauthenticated request to approve is rejected with 401."""
    _, _, case, _ = create_sample_review_case(db_session)
    res = client.post(
        f"/api/recovery/human-review/{case.id}/approve",
        json={"notes": "Unauthorized attempt"},
    )
    assert res.status_code == 401


def test_unauthenticated_post_dismiss_rejected(client: TestClient, db_session: Session):
    """5. Test unauthenticated request to dismiss is rejected with 401."""
    _, _, case, _ = create_sample_review_case(db_session)
    res = client.post(
        f"/api/recovery/human-review/{case.id}/dismiss",
        json={"notes": "Unauthorized attempt"},
    )
    assert res.status_code == 401


def test_unauthenticated_get_worker_health_rejected(client: TestClient):
    """6. Test unauthenticated request to /health/worker is rejected with 401."""
    res = client.get("/health/worker")
    assert res.status_code == 401


# =========================================================================
# 2. RBAC Authorization Tests (403 Forbidden vs 200 OK)
# =========================================================================


def test_viewer_role_cannot_approve_human_review(
    client: TestClient, db_session: Session
):
    """7. Test viewer role is rejected from approving human review with 403."""
    _, _, case, _ = create_sample_review_case(db_session)
    viewer_headers = make_auth_headers(user_id="viewer_bob", role="viewer")

    res = client.post(
        f"/api/recovery/human-review/{case.id}/approve",
        headers=viewer_headers,
        json={"notes": "Viewer attempt to approve"},
    )
    assert res.status_code == 403
    assert "does not have required permission 'operator'" in res.json()["detail"]


def test_viewer_role_cannot_dismiss_human_review(
    client: TestClient, db_session: Session
):
    """8. Test viewer role is rejected from dismissing human review with 403."""
    _, _, case, _ = create_sample_review_case(db_session)
    viewer_headers = make_auth_headers(user_id="viewer_bob", role="viewer")

    res = client.post(
        f"/api/recovery/human-review/{case.id}/dismiss",
        headers=viewer_headers,
        json={"notes": "Viewer attempt to dismiss"},
    )
    assert res.status_code == 403
    assert "does not have required permission 'operator'" in res.json()["detail"]


def test_viewer_role_can_read_metrics_and_cases(
    client: TestClient, db_session: Session
):
    """9. Test viewer role can successfully read dashboard and cases."""
    _, _, case, _ = create_sample_review_case(db_session)
    viewer_headers = make_auth_headers(user_id="viewer_alice", role="viewer")

    res_metrics = client.get("/api/recovery/metrics", headers=viewer_headers)
    assert res_metrics.status_code == 200

    res_cases = client.get("/api/recovery/cases", headers=viewer_headers)
    assert res_cases.status_code == 200


def test_operator_role_can_approve_human_review(
    client: TestClient, db_session: Session
):
    """10. Test authenticated operator can approve case and schedule action."""
    _, _, case, _ = create_sample_review_case(db_session)
    operator_headers = make_auth_headers(
        user_id="op_charlie", role=UserRole.OPERATOR.value
    )

    res = client.post(
        f"/api/recovery/human-review/{case.id}/approve",
        headers=operator_headers,
        json={"notes": "Authorized by operator charlie"},
    )
    assert res.status_code == 200
    data = res.json()
    assert data["success"] is True
    assert data["action"] == "APPROVED"
    assert data["scheduled_action_id"] is not None


def test_operator_role_can_dismiss_human_review(
    client: TestClient, db_session: Session
):
    """11. Test authenticated operator can dismiss case with audit trail."""
    _, _, case, _ = create_sample_review_case(db_session)
    operator_headers = make_auth_headers(
        user_id="op_diana", role=UserRole.OPERATOR.value
    )

    res = client.post(
        f"/api/recovery/human-review/{case.id}/dismiss",
        headers=operator_headers,
        json={"notes": "Customer dispute confirmed. Dismissed."},
    )
    assert res.status_code == 200
    data = res.json()
    assert data["success"] is True
    assert data["action"] == "DISMISSED"


# =========================================================================
# 3. Trust Boundary & Identity Forgery Tests
# =========================================================================


def test_forged_operator_id_in_request_body_is_ignored(
    client: TestClient, db_session: Session
):
    """
    12. Test that a forged operator_id in request body is completely ignored,
    and AuditLog records the authentic identity from the verified JWT.
    """
    _, _, case, _ = create_sample_review_case(db_session)
    actual_auth_headers = make_auth_headers(
        user_id="authenticated_operator_999", role=UserRole.OPERATOR.value
    )

    # Forgery attempt: body claims to be "super_admin_root"
    forgery_payload = {
        "operator_id": "super_admin_root",
        "notes": "Attempting identity spoofing",
    }

    res = client.post(
        f"/api/recovery/human-review/{case.id}/approve",
        headers=actual_auth_headers,
        json=forgery_payload,
    )
    assert res.status_code == 200

    # Verify AuditLog recorded authentic user ID, NOT forged body identity
    audit = (
        db_session.query(AuditLog)
        .filter_by(
            recovery_case_id=case.id,
            event_type="HUMAN_REVIEW_APPROVED",
        )
        .first()
    )
    assert audit is not None
    assert audit.actor_id == "authenticated_operator_999"
    assert audit.actor_id != "super_admin_root"


# =========================================================================
# 4. Token Validation & Expiry Tests
# =========================================================================


def test_invalid_jwt_signature_rejected(client: TestClient):
    """13. Test tampering with JWT signature is rejected with 401."""
    tampered_headers = {"Authorization": "Bearer eyJhbGciOiJIUzI1NiJ9.tampered.token"}
    res = client.get("/api/recovery/metrics", headers=tampered_headers)
    assert res.status_code == 401
    assert "Invalid or malformed authentication token" in res.json()["detail"]


def test_expired_jwt_token_rejected(client: TestClient):
    """14. Test expired JWT token is rejected with 401."""
    # Create token expired 1 hour ago
    expired_token = create_access_token(
        user_id="expired_op",
        role=UserRole.OPERATOR.value,
        expires_delta=timedelta(hours=-1),
    )
    expired_headers = {"Authorization": f"Bearer {expired_token}"}

    res = client.get("/api/recovery/metrics", headers=expired_headers)
    assert res.status_code == 401
    assert "Authentication token has expired" in res.json()["detail"]


# =========================================================================
# 5. Strict Zero-PII Response Contract Tests
# =========================================================================


def test_case_detail_strict_zero_pii_contract(client: TestClient, db_session: Session):
    """15. Test case detail strictly omits customer email and phone fields entirely."""
    _, _, case, _ = create_sample_review_case(db_session)
    headers = make_auth_headers(user_id="op_zero_pii", role=UserRole.VIEWER.value)

    res = client.get(f"/api/recovery/cases/{case.id}", headers=headers)
    assert res.status_code == 200
    data = res.json()

    customer_data = data["customer"]
    assert "email" not in customer_data
    assert "email_masked" not in customer_data
    assert "phone" not in customer_data
    assert "phone_masked" not in customer_data
    assert "external_customer_id" in customer_data
    assert "risk_tier" in customer_data
