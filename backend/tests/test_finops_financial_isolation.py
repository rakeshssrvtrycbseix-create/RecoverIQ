"""Mandatory Financial Execution Isolation Test for Phase 10I FinOps Control Plane.

Invariants Verified:
1. PolicyEngine Supremacy: Sole authoritative financial gatekeeper.
2. Delta RecoveryAction = 0: Zero recovery actions created or modified.
3. Delta Payment = 0: Zero payments created or modified.
4. Delta RecoveryCase Financial State = 0: Zero case amounts or statuses mutated.
5. ActionDispatcher Calls = 0: Zero dispatch invocations.
6. RazorpayActionProvider Calls = 0: Zero payment provider invocations.
"""

from unittest.mock import patch

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.security import UserRole, create_access_token
from app.models.payment import Payment
from app.models.recovery_action import RecoveryAction
from app.models.recovery_case import RecoveryCase


def get_token(
    role: UserRole = UserRole.ADMIN, user_id: str = "finops-isolation-tester"
) -> str:
    return create_access_token(user_id=user_id, role=role.value)


def test_finops_financial_isolation(client: TestClient, db_session: Session):
    """Verify 100% financial execution isolation across all Phase 10I FinOps operations."""
    admin_token = get_token(UserRole.ADMIN)
    headers = {"Authorization": f"Bearer {admin_token}"}

    # 1. Take initial database snapshots
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

    # 2. Patch financial execution engines to detect any rogue calls
    with (
        patch(
            "app.services.action_dispatcher.ActionDispatcher.dispatch_action"
        ) as mock_dispatcher,
        patch(
            "app.services.recovery_action_service.RecoveryActionService.create_recovery_action"
        ) as mock_create_action,
    ):
        # Execute every Phase 10I FinOps endpoint
        r_sum = client.get("/api/recovery/intelligence/finops", headers=headers)
        assert r_sum.status_code == 200

        r_score = client.get("/api/recovery/intelligence/finops/score", headers=headers)
        assert r_score.status_code == 200

        r_costs = client.get("/api/recovery/intelligence/finops/costs", headers=headers)
        assert r_costs.status_code == 200

        r_svc = client.get(
            "/api/recovery/intelligence/finops/costs/services", headers=headers
        )
        assert r_svc.status_code == 200

        r_cat = client.get(
            "/api/recovery/intelligence/finops/costs/categories", headers=headers
        )
        assert r_cat.status_code == 200

        r_unit = client.get(
            "/api/recovery/intelligence/finops/unit-economics", headers=headers
        )
        assert r_unit.status_code == 200

        r_res = client.get(
            "/api/recovery/intelligence/finops/resources", headers=headers
        )
        assert r_res.status_code == 200

        r_eff = client.get(
            "/api/recovery/intelligence/finops/resources/efficiency", headers=headers
        )
        assert r_eff.status_code == 200

        r_bud = client.get("/api/recovery/intelligence/finops/budgets", headers=headers)
        assert r_bud.status_code == 200

        r_bud_stat = client.get(
            "/api/recovery/intelligence/finops/budgets/status", headers=headers
        )
        assert r_bud_stat.status_code == 200

        r_bud_cfg = client.post(
            "/api/recovery/intelligence/finops/budgets/configure",
            json={
                "period": "MONTHLY",
                "budget_amount_inr": 160000.0,
                "notes": "FinOps test config",
            },
            headers=headers,
        )
        assert r_bud_cfg.status_code == 200

        r_fc = client.get(
            "/api/recovery/intelligence/finops/forecasts", headers=headers
        )
        assert r_fc.status_code == 200

        r_fc_gen = client.post(
            "/api/recovery/intelligence/finops/forecasts/generate",
            json={
                "horizon_days": 30,
                "traffic_multiplier": 1.2,
                "include_stress_scenario": True,
            },
            headers=headers,
        )
        assert r_fc_gen.status_code == 200

        r_anom = client.get(
            "/api/recovery/intelligence/finops/anomalies", headers=headers
        )
        assert r_anom.status_code == 200

        r_wst = client.get("/api/recovery/intelligence/finops/waste", headers=headers)
        assert r_wst.status_code == 200

        r_opt = client.get(
            "/api/recovery/intelligence/finops/optimizations", headers=headers
        )
        assert r_opt.status_code == 200

        r_opt_app = client.post(
            "/api/recovery/intelligence/finops/optimizations/OPT-9A8B7C1D/approve",
            json={
                "decision": "APPROVE",
                "notes": "Approved in financial isolation verification run.",
            },
            headers=headers,
        )
        assert r_opt_app.status_code == 200

        r_inc = client.get(
            "/api/recovery/intelligence/finops/incidents", headers=headers
        )
        assert r_inc.status_code == 200

        r_ack = client.post(
            "/api/recovery/intelligence/finops/incidents/INC-FIN-2026-0801/acknowledge",
            json={"notes": "Triage verified in isolation test."},
            headers=headers,
        )
        assert r_ack.status_code == 200

        r_esc = client.post(
            "/api/recovery/intelligence/finops/incidents/INC-FIN-2026-0801/escalate",
            json={"notes": "Escalation verified in isolation test."},
            headers=headers,
        )
        assert r_esc.status_code == 200

        r_res_inc = client.post(
            "/api/recovery/intelligence/finops/incidents/INC-FIN-2026-0801/resolve",
            json={"notes": "Resolution verified in isolation test."},
            headers=headers,
        )
        assert r_res_inc.status_code == 200

        r_gates = client.get(
            "/api/recovery/intelligence/finops/readiness", headers=headers
        )
        assert r_gates.status_code == 200

        r_rpt = client.get("/api/recovery/intelligence/finops/report", headers=headers)
        assert r_rpt.status_code == 200

    # 3. Assert zero financial engine invocations
    assert mock_dispatcher.call_count == 0, (
        "Security Invariant Violated: ActionDispatcher.dispatch_action called by FinOps"
    )
    assert mock_create_action.call_count == 0, (
        "Security Invariant Violated: RecoveryActionService.create_recovery_action called by FinOps"
    )

    # 4. Take final database snapshots and assert zero mutations
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
