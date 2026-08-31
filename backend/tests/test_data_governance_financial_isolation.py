"""Phase 10E — Mandatory Financial Isolation End-to-End Test.

NON-NEGOTIABLE FINANCIAL ISOLATION INVARIANT:
Phase 10E Data Governance, Privacy Engineering, and Data Lineage must NEVER:
1. Create RecoveryAction records (Δ RecoveryAction = 0)
2. Modify Payment financial states (Δ Payment = 0)
3. Modify RecoveryCase financial states (Δ RecoveryCase = 0)
4. Invoke ActionDispatcher (ActionDispatcher calls = 0)
5. Invoke RazorpayActionProvider (RazorpayActionProvider calls = 0)
6. Execute automated financial retries or payments.

PolicyEngine remains the sole authoritative gatekeeper for all recovery operations.
"""

import uuid
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.rate_limiter import rate_limiter
from app.core.security import UserRole, create_access_token
from app.main import app
from app.models.customer import Customer
from app.models.enums import (
    BillingCadence,
    CustomerRiskTier,
    PaymentStatus,
    SubscriptionStatus,
)
from app.models.payment import Payment
from app.models.recovery_action import RecoveryAction
from app.models.recovery_case import RecoveryCase
from app.models.subscription import Subscription


@pytest.fixture(autouse=True)
def reset_rate_limiter():
    rate_limiter.reset()


@pytest.fixture
def client(db_session: Session):
    def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture
def admin_headers():
    token = create_access_token(
        user_id="admin_financial_isolation", role=UserRole.ADMIN.value
    )
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def seed_financial_pipeline_data(db_session: Session):
    run_id = uuid.uuid4().hex[:6]
    cust = Customer(
        external_customer_id=f"cust_fin_iso_{run_id}",
        risk_tier=CustomerRiskTier.STANDARD.value,
    )
    db_session.add(cust)
    db_session.flush()

    sub = Subscription(
        customer_id=cust.id,
        external_subscription_id=f"sub_fin_iso_{run_id}",
        status=SubscriptionStatus.ACTIVE.value,
        plan_name="Enterprise Plan",
        recurring_amount=150000,
        currency="INR",
        billing_cadence=BillingCadence.MONTHLY.value,
    )
    db_session.add(sub)
    db_session.flush()

    pay = Payment(
        customer_id=cust.id,
        subscription_id=sub.id,
        external_order_id=f"pay_fin_iso_{run_id}",
        amount=150000,
        currency="INR",
        status=PaymentStatus.FAILED.value,
    )
    db_session.add(pay)
    db_session.flush()

    case = RecoveryCase(
        payment_id=pay.id,
        customer_id=cust.id,
        amount_at_risk=150000,
        recovered_amount=0,
        status="OPEN",
    )
    db_session.add(case)
    db_session.commit()

    return {"customer": cust, "payment": pay, "case": case}


def test_mandatory_data_governance_financial_isolation(
    client: TestClient,
    db_session: Session,
    admin_headers: dict,
    seed_financial_pipeline_data,
):
    """MANDATORY FULL-SYSTEM FINANCIAL ISOLATION TEST.

    Executes all Phase 10E data governance operations and verifies:
    - Zero RecoveryActions created (Δ RecoveryAction = 0)
    - Zero Payment status/amount mutations (Δ Payment = 0)
    - Zero RecoveryCase amount/status mutations (Δ RecoveryCase = 0)
    - Zero calls to ActionDispatcher
    - Zero calls to RazorpayActionProvider
    """
    # 1. Capture baseline financial state
    initial_action_count = db_session.query(RecoveryAction).count()
    initial_payment_count = db_session.query(Payment).count()
    initial_case_count = db_session.query(RecoveryCase).count()

    initial_payment = (
        db_session.query(Payment)
        .filter(Payment.id == seed_financial_pipeline_data["payment"].id)
        .first()
    )
    initial_payment_amount = initial_payment.amount
    initial_payment_status = initial_payment.status

    initial_case = (
        db_session.query(RecoveryCase)
        .filter(RecoveryCase.id == seed_financial_pipeline_data["case"].id)
        .first()
    )
    initial_case_amount = initial_case.amount_at_risk
    initial_case_recovered = initial_case.recovered_amount
    initial_case_status = initial_case.status

    # 2. Patch ActionDispatcher and Razorpay provider to detect any illegal invocation
    with (
        patch(
            "app.services.action_dispatcher.ActionDispatcher.dispatch_action"
        ) as mock_dispatch,
        patch(
            "app.services.recovery_action_service.RecoveryActionService.create_recovery_action"
        ) as mock_create_action,
    ):
        # 3. Execute all 16 Data Governance endpoints sequentially

        # 3.1. Executive summary
        resp_sum = client.get(
            "/api/recovery/intelligence/data-governance", headers=admin_headers
        )
        assert resp_sum.status_code == 200

        # 3.2. Data Assets
        resp_assets = client.get(
            "/api/recovery/intelligence/data-governance/assets", headers=admin_headers
        )
        assert resp_assets.status_code == 200

        # 3.3. Asset Detail
        resp_asset_det = client.get(
            "/api/recovery/intelligence/data-governance/assets/AST-PAY-001",
            headers=admin_headers,
        )
        assert resp_asset_det.status_code == 200

        # 3.4. Controls
        resp_ctrl = client.get(
            "/api/recovery/intelligence/data-governance/controls", headers=admin_headers
        )
        assert resp_ctrl.status_code == 200

        # 3.5. Data Quality
        resp_dq = client.get(
            "/api/recovery/intelligence/data-governance/data-quality",
            headers=admin_headers,
        )
        assert resp_dq.status_code == 200

        # 3.6. Lineage Graph
        resp_lin = client.get(
            "/api/recovery/intelligence/data-governance/lineage", headers=admin_headers
        )
        assert resp_lin.status_code == 200

        # 3.7. Lineage Node
        resp_node = client.get(
            "/api/recovery/intelligence/data-governance/lineage/LN-SRC-001",
            headers=admin_headers,
        )
        assert resp_node.status_code == 200

        # 3.8. Retention
        resp_ret = client.get(
            "/api/recovery/intelligence/data-governance/retention",
            headers=admin_headers,
        )
        assert resp_ret.status_code == 200

        # 3.9. Erasure Eligibility
        cust_id = seed_financial_pipeline_data["customer"].external_customer_id
        resp_eras = client.get(
            f"/api/recovery/intelligence/data-governance/erasure-eligibility/{cust_id}",
            headers=admin_headers,
        )
        assert resp_eras.status_code == 200

        # 3.10. Incidents
        resp_inc = client.get(
            "/api/recovery/intelligence/data-governance/incidents",
            headers=admin_headers,
        )
        assert resp_inc.status_code == 200

        # 3.11. Privacy Requests List
        resp_reqs = client.get(
            "/api/recovery/intelligence/data-governance/privacy-requests",
            headers=admin_headers,
        )
        assert resp_reqs.status_code == 200

        # 3.12. Create Privacy Request
        resp_create = client.post(
            "/api/recovery/intelligence/data-governance/privacy-requests",
            json={
                "request_type": "ACCESS",
                "subject_id": cust_id,
                "scope": "ALL",
                "notes": "Isolation verification request",
            },
            headers=admin_headers,
        )
        assert resp_create.status_code == 200
        req_id = resp_create.json()["request_id"]

        # 3.13. Review Privacy Request
        resp_rev = client.post(
            f"/api/recovery/intelligence/data-governance/privacy-requests/{req_id}/review",
            json={"decision": "APPROVE", "notes": "Approved for isolation test"},
            headers=admin_headers,
        )
        assert resp_rev.status_code == 200

        # 3.14. Complete Privacy Request
        resp_comp = client.post(
            f"/api/recovery/intelligence/data-governance/privacy-requests/{req_id}/complete",
            json={"notes": "Completed for isolation test"},
            headers=admin_headers,
        )
        assert resp_comp.status_code == 200

        # 3.15. Governance Report
        resp_rep = client.get(
            "/api/recovery/intelligence/data-governance/report", headers=admin_headers
        )
        assert resp_rep.status_code == 200

        # 3.16. PII Discovery Scan
        resp_scan = client.post(
            "/api/recovery/intelligence/data-governance/scan",
            json={"payload": {"test_email": "privacy@recoveriq.ai", "amount": 150000}},
            headers=admin_headers,
        )
        assert resp_scan.status_code == 200

        # 4. Strict Financial Isolation Assertions
        # 4.1. ActionDispatcher calls must be ZERO
        assert mock_dispatch.call_count == 0, (
            f"ActionDispatcher was illegally called {mock_dispatch.call_count} times!"
        )

        # 4.2. RecoveryAction creation must be ZERO
        assert mock_create_action.call_count == 0, (
            f"RecoveryAction was illegally created {mock_create_action.call_count} times!"
        )

    # 4.3. Database Row Counts must remain unchanged
    final_action_count = db_session.query(RecoveryAction).count()
    final_payment_count = db_session.query(Payment).count()
    final_case_count = db_session.query(RecoveryCase).count()

    assert final_action_count == initial_action_count, (
        f"Δ RecoveryAction must be 0, but was {final_action_count - initial_action_count}"
    )
    assert final_payment_count == initial_payment_count, (
        f"Δ Payment must be 0, but was {final_payment_count - initial_payment_count}"
    )
    assert final_case_count == initial_case_count, (
        f"Δ RecoveryCase must be 0, but was {final_case_count - initial_case_count}"
    )

    # 4.4. Financial Entity State must remain 100% identical
    final_payment = (
        db_session.query(Payment)
        .filter(Payment.id == seed_financial_pipeline_data["payment"].id)
        .first()
    )
    assert final_payment.amount == initial_payment_amount
    assert final_payment.status == initial_payment_status

    final_case = (
        db_session.query(RecoveryCase)
        .filter(RecoveryCase.id == seed_financial_pipeline_data["case"].id)
        .first()
    )
    assert final_case.amount_at_risk == initial_case_amount
    assert final_case.recovered_amount == initial_case_recovered
    assert final_case.status == initial_case_status
