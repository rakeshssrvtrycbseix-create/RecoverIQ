"""Mandatory End-to-End Financial Isolation Test Suite for Phase 10H: Zero-Trust Security Control Plane.

Proves:
  Δ RecoveryAction = 0
  Δ Payment = 0
  Δ RecoveryCase financial state = 0
  ActionDispatcher calls = 0
  RazorpayActionProvider calls = 0
"""

from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.security import UserRole, create_access_token
from app.models.payment import Payment
from app.models.recovery_action import RecoveryAction
from app.models.recovery_case import RecoveryCase


@pytest.fixture
def admin_token() -> str:
    """JWT token for admin role."""
    return create_access_token(user_id="admin_user", role=UserRole.ADMIN.value)


def test_zero_trust_financial_isolation(
    client: TestClient, db_session: Session, admin_token: str
):
    """Mandatory test verifying that executing all Phase 10H Zero-Trust operations

    produces zero financial mutations and zero provider/dispatcher calls.
    """
    headers = {"Authorization": f"Bearer {admin_token}"}

    # 1. Snapshot initial financial state
    initial_actions_count = db_session.query(RecoveryAction).count()
    initial_payments_count = db_session.query(Payment).count()

    initial_cases = db_session.query(RecoveryCase).all()
    initial_case_snapshots = {
        c.case_id: {
            "amount_due": str(c.amount_due),
            "recovered_amount": str(c.recovered_amount),
            "status": c.status,
        }
        for c in initial_cases
    }

    # 2. Mock ActionDispatcher and RazorpayActionProvider
    with (
        patch(
            "app.services.action_dispatcher.ActionDispatcher.dispatch_action"
        ) as mock_dispatch,
        patch("app.providers.razorpay.RazorpayActionProvider.execute") as mock_provider,
    ):
        mock_dispatch.side_effect = RuntimeError(
            "CRITICAL INVARIANT BREACH: ActionDispatcher invoked during Phase 10H!"
        )
        mock_provider.side_effect = RuntimeError(
            "CRITICAL INVARIANT BREACH: Razorpay Provider invoked during Phase 10H!"
        )

        # 3. Execute all Phase 10H Control Plane Endpoints
        r_sum = client.get(
            "/api/recovery/intelligence/zero-trust/summary", headers=headers
        )
        assert r_sum.status_code == 200

        r_ident = client.get(
            "/api/recovery/intelligence/zero-trust/service-identities", headers=headers
        )
        assert r_ident.status_code == 200

        r_ident_name = client.get(
            "/api/recovery/intelligence/zero-trust/service-identities/Policy%20Engine",
            headers=headers,
        )
        assert r_ident_name.status_code == 200

        r_matrix = client.get(
            "/api/recovery/intelligence/zero-trust/authorization-matrix",
            headers=headers,
        )
        assert r_matrix.status_code == 200

        r_viol = client.get(
            "/api/recovery/intelligence/zero-trust/trust-violations", headers=headers
        )
        assert r_viol.status_code == 200

        r_threats = client.get(
            "/api/recovery/intelligence/zero-trust/threat-indicators", headers=headers
        )
        assert r_threats.status_code == 200

        r_score = client.get(
            "/api/recovery/intelligence/zero-trust/threat-score", headers=headers
        )
        assert r_score.status_code == 200

        r_chains = client.get(
            "/api/recovery/intelligence/zero-trust/attack-chains", headers=headers
        )
        assert r_chains.status_code == 200
        chain_id = r_chains.json()[0]["chain_id"]

        r_chain_id = client.get(
            f"/api/recovery/intelligence/zero-trust/attack-chains/{chain_id}",
            headers=headers,
        )
        assert r_chain_id.status_code == 200

        r_runt = client.get(
            "/api/recovery/intelligence/zero-trust/runtime-security", headers=headers
        )
        assert r_runt.status_code == 200

        r_sec = client.get(
            "/api/recovery/intelligence/zero-trust/secret-exposure", headers=headers
        )
        assert r_sec.status_code == 200

        r_inc = client.get(
            "/api/recovery/intelligence/zero-trust/security-incidents", headers=headers
        )
        assert r_inc.status_code == 200

        inc_id = r_inc.json()[0]["incident_id"]

        r_ack = client.post(
            f"/api/recovery/intelligence/zero-trust/security-incidents/{inc_id}/acknowledge",
            headers=headers,
        )
        assert r_ack.status_code == 200

        r_esc = client.post(
            f"/api/recovery/intelligence/zero-trust/security-incidents/{inc_id}/escalate",
            headers=headers,
        )
        assert r_esc.status_code == 200

        r_res = client.post(
            f"/api/recovery/intelligence/zero-trust/security-incidents/{inc_id}/resolve",
            headers=headers,
        )
        assert r_res.status_code == 200

        r_gates = client.get(
            "/api/recovery/intelligence/zero-trust/readiness", headers=headers
        )
        assert r_gates.status_code == 200

        r_evid = client.get(
            "/api/recovery/intelligence/zero-trust/evidence", headers=headers
        )
        assert r_evid.status_code == 200

        r_rpt = client.get(
            "/api/recovery/intelligence/zero-trust/report", headers=headers
        )
        assert r_rpt.status_code == 200

        # 4. Assert zero calls to dispatcher/provider
        assert mock_dispatch.call_count == 0
        assert mock_provider.call_count == 0

    # 5. Verify post-execution financial state invariants
    db_session.expire_all()

    final_actions_count = db_session.query(RecoveryAction).count()
    final_payments_count = db_session.query(Payment).count()

    assert final_actions_count == initial_actions_count, (
        f"Financial Mutation Detected: RecoveryActions count changed by {final_actions_count - initial_actions_count}"
    )
    assert final_payments_count == initial_payments_count, (
        f"Financial Mutation Detected: Payments count changed by {final_payments_count - initial_payments_count}"
    )

    final_cases = db_session.query(RecoveryCase).all()
    for c in final_cases:
        initial = initial_case_snapshots[c.case_id]
        assert str(c.amount_due) == initial["amount_due"], (
            f"Financial Mutation on Case {c.case_id}: amount_due mutated"
        )
        assert str(c.recovered_amount) == initial["recovered_amount"], (
            f"Financial Mutation on Case {c.case_id}: recovered_amount mutated"
        )
        assert c.status == initial["status"], (
            f"Financial Mutation on Case {c.case_id}: status mutated"
        )
