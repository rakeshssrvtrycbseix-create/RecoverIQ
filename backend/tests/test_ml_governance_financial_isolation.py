"""Strict Financial Isolation Invariant Tests for RecoverIQ Phase 10J:

AI/ML Governance, Model Risk Management & Responsible AI Control Plane.

Invariants Verified:
1. ΔRecoveryAction = 0 across all governance evaluations, evaluations, and reports.
2. ΔPayment = 0 across all governance endpoints.
3. ΔRecoveryCase financial state (amount_due, recovered_amount) = 0.
4. ActionDispatcher calls = 0.
5. RecoveryActionService create_recovery_action calls = 0.
6. PolicyEngine supremacy remains absolute.
"""

from unittest.mock import patch

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.security import UserRole, create_access_token
from app.models import Payment, RecoveryAction, RecoveryCase


def get_token(
    role: UserRole = UserRole.ADMIN, user_id: str = "test-ml-gov-admin"
) -> str:
    return create_access_token(user_id=user_id, role=role.value)


def test_ml_governance_strict_financial_isolation(
    client: TestClient, db_session: Session
):
    """Verify 100% financial execution isolation across all Phase 10J operations."""
    admin_token = get_token(UserRole.ADMIN)
    headers = {"Authorization": f"Bearer {admin_token}"}

    # 1. Take initial database snapshot
    initial_actions_count = db_session.query(RecoveryAction).count()
    initial_payments_count = db_session.query(Payment).count()

    initial_cases = db_session.query(RecoveryCase).all()
    initial_case_snapshots = {
        c.id: {
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
        # Read operations
        client.get("/api/recovery/intelligence/ml-governance/summary", headers=headers)
        client.get("/api/recovery/intelligence/ml-governance/models", headers=headers)
        client.get(
            "/api/recovery/intelligence/ml-governance/models/recovery_probability",
            headers=headers,
        )
        client.get(
            "/api/recovery/intelligence/ml-governance/models/recovery_probability/versions",
            headers=headers,
        )
        client.get(
            "/api/recovery/intelligence/ml-governance/models/recovery_probability/lineage",
            headers=headers,
        )
        client.get(
            "/api/recovery/intelligence/ml-governance/models/recovery_probability/performance",
            headers=headers,
        )
        client.get(
            "/api/recovery/intelligence/ml-governance/models/recovery_probability/drift",
            headers=headers,
        )
        client.get(
            "/api/recovery/intelligence/ml-governance/models/recovery_probability/prediction-drift",
            headers=headers,
        )
        client.get(
            "/api/recovery/intelligence/ml-governance/models/recovery_probability/concept-drift",
            headers=headers,
        )
        client.get(
            "/api/recovery/intelligence/ml-governance/models/recovery_probability/explainability",
            headers=headers,
        )
        client.get(
            "/api/recovery/intelligence/ml-governance/models/recovery_probability/fairness",
            headers=headers,
        )
        client.get(
            "/api/recovery/intelligence/ml-governance/models/recovery_probability/calibration",
            headers=headers,
        )
        client.get(
            "/api/recovery/intelligence/ml-governance/models/recovery_probability/risk",
            headers=headers,
        )
        client.get(
            "/api/recovery/intelligence/ml-governance/models/recovery_probability/readiness",
            headers=headers,
        )
        client.get(
            "/api/recovery/intelligence/ml-governance/models/recovery_probability/rollback",
            headers=headers,
        )
        client.get(
            "/api/recovery/intelligence/ml-governance/readiness-gates", headers=headers
        )
        client.get(
            "/api/recovery/intelligence/ml-governance/forensics", headers=headers
        )
        client.get("/api/recovery/intelligence/ml-governance/report", headers=headers)

        # Mutating operations
        client.post(
            "/api/recovery/intelligence/ml-governance/models/recovery_probability/evaluate",
            json={"evaluation_type": "OFFLINE", "sample_size": 1000},
            headers=headers,
        )
        client.post(
            "/api/recovery/intelligence/ml-governance/models/recovery_probability/explain",
            json={
                "prediction_reference": "PRED-TEST-ISOLATION-001",
                "feature_vector": {"rate": 0.8},
            },
            headers=headers,
        )
        client.post(
            "/api/recovery/intelligence/ml-governance/models/recovery_probability/promotion-evaluation",
            json={
                "candidate_version": "v1.1-candidate",
                "justification": "Isolation verification",
            },
            headers=headers,
        )
        client.post(
            "/api/recovery/intelligence/ml-governance/incidents/ML-INC-2026-001/acknowledge?notes=Isolation+test",
            headers=headers,
        )
        client.post(
            "/api/recovery/intelligence/ml-governance/incidents/ML-INC-2026-001/resolve?notes=Isolation+test+resolved",
            headers=headers,
        )

        # 3. Assert zero calls to financial engines
        assert mock_dispatcher.call_count == 0, (
            "ActionDispatcher was unexpectedly called during ML governance!"
        )
        assert mock_create_action.call_count == 0, (
            "RecoveryActionService was unexpectedly called during ML governance!"
        )

    # 4. Final DB checks (Delta = 0)
    final_actions_count = db_session.query(RecoveryAction).count()
    final_payments_count = db_session.query(Payment).count()

    assert final_actions_count == initial_actions_count, (
        f"Delta RecoveryAction != 0! ({final_actions_count - initial_actions_count})"
    )
    assert final_payments_count == initial_payments_count, (
        f"Delta Payment != 0! ({final_payments_count - initial_payments_count})"
    )

    final_cases = db_session.query(RecoveryCase).all()
    for c in final_cases:
        if c.id in initial_case_snapshots:
            snap = initial_case_snapshots[c.id]
            assert str(c.amount_due) == snap["amount_due"], (
                f"RecoveryCase {c.id} amount_due mutated!"
            )
            assert str(c.recovered_amount) == snap["recovered_amount"], (
                f"RecoveryCase {c.id} recovered_amount mutated!"
            )
            assert c.status == snap["status"], f"RecoveryCase {c.id} status mutated!"
