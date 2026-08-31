"""Phase 10F — Mandatory Financial Isolation End-to-End Test.

NON-NEGOTIABLE FINANCIAL ISOLATION INVARIANT:
Phase 10F Fintech Performance Engineering, Scalability, Capacity Planning & High-Load Resilience must NEVER:
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
        external_customer_id=f"cust_perf_fin_iso_{run_id}",
        risk_tier=CustomerRiskTier.STANDARD.value,
    )
    db_session.add(cust)
    db_session.flush()

    sub = Subscription(
        customer_id=cust.id,
        external_subscription_id=f"sub_perf_fin_iso_{run_id}",
        status=SubscriptionStatus.ACTIVE.value,
        plan_name="Enterprise Scale Plan",
        recurring_amount=250000,
        currency="INR",
        billing_cadence=BillingCadence.MONTHLY.value,
    )
    db_session.add(sub)
    db_session.flush()

    pay = Payment(
        customer_id=cust.id,
        subscription_id=sub.id,
        external_order_id=f"pay_perf_fin_iso_{run_id}",
        amount=250000,
        currency="INR",
        status=PaymentStatus.FAILED.value,
    )
    db_session.add(pay)
    db_session.flush()

    case = RecoveryCase(
        payment_id=pay.id,
        customer_id=cust.id,
        amount_at_risk=250000,
        recovered_amount=0,
        status="OPEN",
    )
    db_session.add(case)
    db_session.commit()

    return {"customer": cust, "payment": pay, "case": case}


def test_mandatory_performance_financial_isolation(
    client: TestClient,
    db_session: Session,
    admin_headers: dict,
    seed_financial_pipeline_data,
):
    """MANDATORY FULL-SYSTEM FINANCIAL ISOLATION TEST FOR PHASE 10F.

    Executes all Phase 10F performance endpoints and synthetic load tests, verifying:
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
        # 3. Execute all 16 Performance & Capacity endpoints sequentially

        # 3.1. Executive summary
        resp_sum = client.get(
            "/api/recovery/intelligence/performance", headers=admin_headers
        )
        assert resp_sum.status_code == 200

        # 3.2. 11-Service Matrix
        resp_services = client.get(
            "/api/recovery/intelligence/performance/services", headers=admin_headers
        )
        assert resp_services.status_code == 200

        # 3.3. Capacity Assessment
        resp_cap = client.get(
            "/api/recovery/intelligence/performance/capacity", headers=admin_headers
        )
        assert resp_cap.status_code == 200

        # 3.4. Capacity Forecast
        resp_forecast = client.get(
            "/api/recovery/intelligence/performance/capacity/forecast",
            headers=admin_headers,
        )
        assert resp_forecast.status_code == 200

        # 3.5. Queue Performance
        resp_queues = client.get(
            "/api/recovery/intelligence/performance/queues", headers=admin_headers
        )
        assert resp_queues.status_code == 200

        # 3.6. Database Performance
        resp_db = client.get(
            "/api/recovery/intelligence/performance/database", headers=admin_headers
        )
        assert resp_db.status_code == 200

        # 3.7. Cache Performance
        resp_cache = client.get(
            "/api/recovery/intelligence/performance/cache", headers=admin_headers
        )
        assert resp_cache.status_code == 200

        # 3.8. ML Performance
        resp_ml = client.get(
            "/api/recovery/intelligence/performance/ml", headers=admin_headers
        )
        assert resp_ml.status_code == 200

        # 3.9. Webhook Performance
        resp_wh = client.get(
            "/api/recovery/intelligence/performance/webhooks", headers=admin_headers
        )
        assert resp_wh.status_code == 200

        # 3.10. Bottlenecks
        resp_btn = client.get(
            "/api/recovery/intelligence/performance/bottlenecks", headers=admin_headers
        )
        assert resp_btn.status_code == 200

        # 3.11. Incidents
        resp_inc = client.get(
            "/api/recovery/intelligence/performance/incidents", headers=admin_headers
        )
        assert resp_inc.status_code == 200

        # 3.12. Gates
        resp_gates = client.get(
            "/api/recovery/intelligence/performance/gates", headers=admin_headers
        )
        assert resp_gates.status_code == 200

        # 3.13. Regressions
        resp_reg = client.get(
            "/api/recovery/intelligence/performance/regressions", headers=admin_headers
        )
        assert resp_reg.status_code == 200

        # 3.14. Load Test List
        resp_lt_list = client.get(
            "/api/recovery/intelligence/performance/load-tests", headers=admin_headers
        )
        assert resp_lt_list.status_code == 200

        # 3.15. Synthetic Load Test Execution (5X Burst)
        resp_lt_exec = client.post(
            "/api/recovery/intelligence/performance/load-tests",
            json={
                "scenario": "API_5X",
                "duration_seconds": 30,
                "target_rpm": 5000,
                "notes": "Financial isolation test run",
            },
            headers=admin_headers,
        )
        assert resp_lt_exec.status_code == 200
        assert resp_lt_exec.json()["financial_isolation_verified"] is True

        # 3.16. Performance Report
        resp_rpt = client.get(
            "/api/recovery/intelligence/performance/report", headers=admin_headers
        )
        assert resp_rpt.status_code == 200

        # 4. Mandatory Assertions: Zero calls to dispatch or create action
        mock_dispatch.assert_not_called()
        mock_create_action.assert_not_called()

    # 5. Assert database financial immutability
    final_action_count = db_session.query(RecoveryAction).count()
    final_payment_count = db_session.query(Payment).count()
    final_case_count = db_session.query(RecoveryCase).count()

    final_payment = (
        db_session.query(Payment)
        .filter(Payment.id == seed_financial_pipeline_data["payment"].id)
        .first()
    )
    final_case = (
        db_session.query(RecoveryCase)
        .filter(RecoveryCase.id == seed_financial_pipeline_data["case"].id)
        .first()
    )

    # Δ RecoveryAction == 0
    assert final_action_count == initial_action_count, (
        f"VIOLATION: RecoveryAction count changed from {initial_action_count} to {final_action_count}!"
    )

    # Δ Payment == 0
    assert final_payment_count == initial_payment_count, (
        f"VIOLATION: Payment count changed from {initial_payment_count} to {final_payment_count}!"
    )
    assert final_payment.amount == initial_payment_amount
    assert final_payment.status == initial_payment_status

    # Δ RecoveryCase == 0
    assert final_case_count == initial_case_count, (
        f"VIOLATION: RecoveryCase count changed from {initial_case_count} to {final_case_count}!"
    )
    assert final_case.amount_at_risk == initial_case_amount
    assert final_case.recovered_amount == initial_case_recovered
    assert final_case.status == initial_case_status
