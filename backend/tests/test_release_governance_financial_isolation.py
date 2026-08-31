"""Phase 10G — Mandatory Financial Isolation End-to-End Test.

NON-NEGOTIABLE FINANCIAL ISOLATION INVARIANT:
Phase 10G Fintech Architecture Governance, Change Management, Release Safety & Deployment Assurance must NEVER:
1. Create RecoveryAction records (Δ RecoveryAction = 0)
2. Modify Payment financial states (Δ Payment = 0)
3. Modify RecoveryCase financial states (Δ RecoveryCase = 0)
4. Invoke ActionDispatcher (ActionDispatcher calls = 0)
5. Invoke RazorpayActionProvider (RazorpayActionProvider calls = 0)
6. Execute automated financial retries or production deployments.

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
        user_id="admin_financial_isolation_rel", role=UserRole.ADMIN.value
    )
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def seed_financial_pipeline_data(db_session: Session):
    run_id = uuid.uuid4().hex[:6]
    cust = Customer(
        external_customer_id=f"cust_rel_fin_iso_{run_id}",
        risk_tier=CustomerRiskTier.STANDARD.value,
    )
    db_session.add(cust)
    db_session.flush()

    sub = Subscription(
        customer_id=cust.id,
        external_subscription_id=f"sub_rel_fin_iso_{run_id}",
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
        external_order_id=f"pay_rel_fin_iso_{run_id}",
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
        status="ACTIVE",
    )
    db_session.add(case)
    db_session.commit()

    return {"customer": cust, "subscription": sub, "payment": pay, "case": case}


def test_mandatory_release_governance_financial_isolation(
    client: TestClient,
    db_session: Session,
    admin_headers: dict,
    seed_financial_pipeline_data,
):
    """MANDATORY FINANCIAL ISOLATION VERIFICATION.

    Assert that calling ALL Phase 10G Release Governance endpoints:
    1. Does NOT create any RecoveryAction records (Δ RecoveryAction = 0)
    2. Does NOT mutate Payment amounts, statuses, or records (Δ Payment = 0)
    3. Does NOT mutate RecoveryCase balances or statuses (Δ RecoveryCase = 0)
    4. Does NOT invoke ActionDispatcher (calls = 0)
    5. Does NOT invoke RazorpayActionProvider (calls = 0)
    """
    # 1. Snapshot baseline financial database counts and states
    baseline_actions_count = db_session.query(RecoveryAction).count()
    baseline_payments = {
        p.id: (p.amount, p.status) for p in db_session.query(Payment).all()
    }
    baseline_cases = {
        c.id: (c.amount_at_risk, c.recovered_amount, c.status)
        for c in db_session.query(RecoveryCase).all()
    }

    with (
        patch(
            "app.services.action_dispatcher.ActionDispatcher.dispatch_action"
        ) as mock_dispatcher,
        patch(
            "app.services.recovery_action_service.RecoveryActionService.create_recovery_action"
        ) as mock_create_action,
        patch(
            "app.providers.razorpay.RazorpayActionProvider.execute"
        ) as mock_rzp_execute,
    ):
        # 3. Execute ALL Phase 10G Release Governance operations

        # 3.1. Executive summary
        resp_sum = client.get(
            "/api/recovery/intelligence/release-governance", headers=admin_headers
        )
        assert resp_sum.status_code == 200

        # 3.2. List Change Requests
        resp_changes = client.get(
            "/api/recovery/intelligence/release-governance/changes",
            headers=admin_headers,
        )
        assert resp_changes.status_code == 200

        # 3.3. Create Change Request
        resp_create_cr = client.post(
            "/api/recovery/intelligence/release-governance/changes",
            json={
                "title": "Staging Redis Pipelining Verification",
                "description": "Validates connection buffer scaling in controlled staging.",
                "change_type": "CONFIGURATION",
                "affected_services": ["Redis Cache"],
                "is_financial_path": False,
                "requires_downtime": False,
                "rollback_procedure": "Revert environment configuration.",
            },
            headers=admin_headers,
        )
        assert resp_create_cr.status_code == 201

        # 3.4. Change Details & Risk
        cr_id = resp_create_cr.json()["change_id"]
        resp_cr_det = client.get(
            f"/api/recovery/intelligence/release-governance/changes/{cr_id}",
            headers=admin_headers,
        )
        assert resp_cr_det.status_code == 200

        resp_risk = client.get(
            f"/api/recovery/intelligence/release-governance/risk/{cr_id}",
            headers=admin_headers,
        )
        assert resp_risk.status_code == 200

        # 3.5. 11-Service Dependency Coupling Graph
        resp_deps = client.get(
            "/api/recovery/intelligence/release-governance/dependencies",
            headers=admin_headers,
        )
        assert resp_deps.status_code == 200

        # 3.6. Architecture Findings
        resp_arch = client.get(
            "/api/recovery/intelligence/release-governance/architecture-findings",
            headers=admin_headers,
        )
        assert resp_arch.status_code == 200

        # 3.7. API Compatibility
        resp_api = client.get(
            "/api/recovery/intelligence/release-governance/api-compatibility",
            headers=admin_headers,
        )
        assert resp_api.status_code == 200

        # 3.8. Database Compatibility
        resp_db = client.get(
            "/api/recovery/intelligence/release-governance/database-compatibility",
            headers=admin_headers,
        )
        assert resp_db.status_code == 200

        # 3.9. Configuration Drift
        resp_drift = client.get(
            "/api/recovery/intelligence/release-governance/configuration-drift",
            headers=admin_headers,
        )
        assert resp_drift.status_code == 200

        # 3.10. Feature Flags
        resp_ff = client.get(
            "/api/recovery/intelligence/release-governance/feature-flags",
            headers=admin_headers,
        )
        assert resp_ff.status_code == 200

        resp_ff_up = client.post(
            "/api/recovery/intelligence/release-governance/feature-flags/FF-001",
            json={
                "status": "ACTIVE",
                "rollout_percentage": 100,
                "rationale": "Financial isolation test verification",
            },
            headers=admin_headers,
        )
        assert resp_ff_up.status_code == 200

        # 3.11. Release Candidates
        resp_rcs = client.get(
            "/api/recovery/intelligence/release-governance/releases",
            headers=admin_headers,
        )
        assert resp_rcs.status_code == 200

        resp_create_rc = client.post(
            "/api/recovery/intelligence/release-governance/releases",
            json={
                "version": "v2.12.0-fin-iso",
                "commit_sha": "a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0",
                "deployment_strategy": "CANARY",
                "change_request_ids": [cr_id],
            },
            headers=admin_headers,
        )
        assert resp_create_rc.status_code == 201
        rc_id = resp_create_rc.json()["rc_id"]

        resp_rc_det = client.get(
            f"/api/recovery/intelligence/release-governance/releases/{rc_id}",
            headers=admin_headers,
        )
        assert resp_rc_det.status_code == 200

        # 3.12. Readiness Gates
        resp_read = client.get(
            "/api/recovery/intelligence/release-governance/readiness",
            headers=admin_headers,
        )
        assert resp_read.status_code == 200

        # 3.13. Canary Evaluation
        resp_canary = client.get(
            "/api/recovery/intelligence/release-governance/canary",
            headers=admin_headers,
        )
        assert resp_canary.status_code == 200

        # 3.14. Rollback Readiness
        resp_rb = client.get(
            "/api/recovery/intelligence/release-governance/rollback-readiness",
            headers=admin_headers,
        )
        assert resp_rb.status_code == 200

        # 3.15. Lineage & Incidents
        resp_lin = client.get(
            "/api/recovery/intelligence/release-governance/lineage",
            headers=admin_headers,
        )
        assert resp_lin.status_code == 200

        resp_inc = client.get(
            "/api/recovery/intelligence/release-governance/incidents",
            headers=admin_headers,
        )
        assert resp_inc.status_code == 200

        # 3.16. Human Approval Sign-off
        resp_approve = client.post(
            f"/api/recovery/intelligence/release-governance/approve/{rc_id}",
            json={
                "decision": "APPROVE",
                "comments": "Financial isolation test sign-off",
            },
            headers=admin_headers,
        )
        assert resp_approve.status_code == 200

        # 3.17. Signed Governance Report
        resp_rpt = client.get(
            "/api/recovery/intelligence/release-governance/report",
            headers=admin_headers,
        )
        assert resp_rpt.status_code == 200
        assert resp_rpt.json()["isolation_verified"] is True

        # 4. ASSERT ABSOLUTE FINANCIAL ISOLATION INVARIANTS

        # 4.1. Zero RecoveryAction records created
        current_actions_count = db_session.query(RecoveryAction).count()
        assert current_actions_count == baseline_actions_count, (
            f"VIOLATION: RecoveryAction count changed from {baseline_actions_count} to {current_actions_count}"
        )

        # 4.2. Zero Payment financial mutations
        current_payments = {
            p.id: (p.amount, p.status) for p in db_session.query(Payment).all()
        }
        assert current_payments == baseline_payments, (
            f"VIOLATION: Payment financial states mutated! Baseline: {baseline_payments}, Current: {current_payments}"
        )

        # 4.3. Zero RecoveryCase financial mutations
        current_cases = {
            c.id: (c.amount_at_risk, c.recovered_amount, c.status)
            for c in db_session.query(RecoveryCase).all()
        }
        assert current_cases == baseline_cases, (
            f"VIOLATION: RecoveryCase financial states mutated! Baseline: {baseline_cases}, Current: {current_cases}"
        )

        # 4.4. ActionDispatcher NEVER invoked
        assert mock_dispatcher.call_count == 0, (
            f"VIOLATION: ActionDispatcher called {mock_dispatcher.call_count} times during release governance!"
        )
        assert mock_create_action.call_count == 0, (
            f"VIOLATION: RecoveryActionService.create_recovery_action called {mock_create_action.call_count} times!"
        )

        # 4.5. Razorpay provider NEVER invoked
        assert mock_rzp_execute.call_count == 0, (
            f"VIOLATION: Razorpay execute called {mock_rzp_execute.call_count} times!"
        )
