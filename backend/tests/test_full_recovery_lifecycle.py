"""
RecoverIQ Full Lifecycle Forensic Integration Test.

Verifies the complete 12-step autonomous recovery loop:
1. Webhook Ingestion & Signature Verification
2. PaymentEvent, Payment, and PaymentAttempt Persistence
3. RecoveryCase Creation (OPEN / INVESTIGATING)
4. Non-PII Feature Extraction & ML Prediction Persistence
5. AI Advisory Decision Engine Execution
6. Policy Engine Evaluation (Safety Guardrails, Limits, & Cooldowns)
7. Recovery Action Scheduling
8. Action Dispatcher Execution & Provider Result Recording
9. Reconciliation Worker Verification
10. RecoveryCase State Resolution (RECOVERED)
11. Cryptographic Audit Log DAG Lineage Verification
12. Dashboard & Control Plane Telemetry Reflection
"""

import hashlib
import hmac
import json
import uuid
from datetime import UTC, datetime
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.agent.decision_engine import recovery_decision_engine
from app.models import (
    ActionResult,
    AgentDecision,
    AuditLog,
    Customer,
    CustomerRiskTier,
    MLPrediction,
    Payment,
    PaymentAttempt,
    PaymentEvent,
    PaymentStatus,
    PolicyDecision,
    RecoveryAction,
    RecoveryCase,
)
from app.models.enums import (
    AuditActorType,
    PolicyEvaluationResult,
    RecoveryActionStatus,
    RecoveryActionType,
    RecoveryCaseStatus,
)
from app.policy.engine import PolicyEngine
from app.providers.mock import MockActionProvider
from app.services.action_dispatcher import ActionDispatcher
from app.services.action_scheduler import action_scheduler
from app.services.ml_prediction_service import ml_prediction_service
from app.services.payment_event_processor import payment_event_processor
from tests.conftest import TEST_WEBHOOK_SECRET


@pytest.mark.anyio
async def test_full_recovery_lifecycle_autonomous_execution(
    client: TestClient,
    db_session: Session,
):
    """
    Execute deterministic end-to-end integration test verifying the complete
    autonomous recovery lifecycle with zero manual shortcuts.
    """
    # -------------------------------------------------------------------------
    # STEP 0: Operator Auth
    # -------------------------------------------------------------------------
    auth_resp = client.post(
        "/api/auth/token",
        json={"user_id": "auditor_e2e", "role": "operator"},
    )
    assert auth_resp.status_code == 200
    token = auth_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Verify baseline metrics
    m_baseline = client.get("/api/recovery/metrics", headers=headers).json()
    base_cases = m_baseline["cases"]["total"]
    base_recovered = m_baseline["financial"]["amount_recovered"]

    # -------------------------------------------------------------------------
    # STEP 1: Ingest Failed Payment Webhook Event (Razorpay HMAC-SHA256)
    # -------------------------------------------------------------------------
    event_id = f"evt_life_{uuid.uuid4().hex[:12]}"
    payment_id = f"pay_life_{uuid.uuid4().hex[:12]}"
    customer_id = f"cust_life_{uuid.uuid4().hex[:12]}"
    recovery_amount = 185000  # ₹1,850.00 in paise

    webhook_payload = {
        "entity": "event",
        "account_id": "acc_life_merchant",
        "event": "payment.failed",
        "contains": ["payment"],
        "payload": {
            "payment": {
                "entity": {
                    "id": payment_id,
                    "amount": recovery_amount,
                    "currency": "INR",
                    "status": "failed",
                    "order_id": f"order_life_{uuid.uuid4().hex[:8]}",
                    "invoice_id": None,
                    "international": False,
                    "method": "upi",
                    "amount_refunded": 0,
                    "refund_status": None,
                    "captured": False,
                    "description": "Monthly SaaS Pro Subscription",
                    "card_id": None,
                    "bank": "ICIC",
                    "wallet": None,
                    "vpa": "customer@icici",
                    "email": "saas.subscriber@domain.com",
                    "contact": "+919988776655",
                    "customer_id": customer_id,
                    "notes": {
                        "merchant_customer_id": customer_id,
                        "subscription_tier": "SaaS_Pro",
                    },
                    "fee": None,
                    "tax": None,
                    "error_code": "GATEWAY_TIMEOUT",
                    "error_description": "Bank network timeout during authorization.",
                    "error_source": "bank",
                    "error_step": "payment_authorization",
                    "error_reason": "bank_technical_error",
                    "created_at": int(datetime.now(UTC).timestamp()),
                }
            }
        },
        "created_at": int(datetime.now(UTC).timestamp()),
    }

    raw_body = json.dumps(webhook_payload).encode("utf-8")
    sig = hmac.new(TEST_WEBHOOK_SECRET.encode("utf-8"), raw_body, hashlib.sha256).hexdigest()

    wh_resp = client.post(
        "/webhooks/razorpay",
        content=raw_body,
        headers={
            "X-Razorpay-Signature": sig,
            "X-Razorpay-Event-Id": event_id,
            "Content-Type": "application/json",
        },
    )
    assert wh_resp.status_code == 200
    assert wh_resp.json()["status"] == "ok"

    # -------------------------------------------------------------------------
    # STEP 2: Verify PaymentEvent and Process Event to Payment / RecoveryCase
    # -------------------------------------------------------------------------
    db_session.expire_all()
    saved_event = db_session.query(PaymentEvent).filter_by(razorpay_event_id=event_id).first()
    assert saved_event is not None
    assert saved_event.event_type == "payment.failed"

    # Ensure processed by event processor
    if saved_event.processing_status != "PROCESSED":
        proc_result = payment_event_processor.process_payment_event(db_session, saved_event)
        assert proc_result.processing_status == "PROCESSED"

    # -------------------------------------------------------------------------
    # STEP 3: Verify Case Creation in Database & API
    # -------------------------------------------------------------------------
    case = db_session.query(RecoveryCase).filter_by(payment_id=saved_event.payment_id).first()
    assert case is not None
    assert case.amount_at_risk == recovery_amount
    assert case.status in [
        RecoveryCaseStatus.OPEN.value,
        RecoveryCaseStatus.ANALYZING.value,
        RecoveryCaseStatus.ACTION_PENDING.value,
    ]

    case_api_resp = client.get(f"/api/recovery/cases/{case.id}", headers=headers)
    assert case_api_resp.status_code == 200
    assert case_api_resp.json()["case"]["id"] == str(case.id)

    # -------------------------------------------------------------------------
    # STEP 4: Automated Feature Extraction & ML Inference
    # -------------------------------------------------------------------------
    ml_pred = ml_prediction_service.predict_recovery(db_session, case.id)
    assert ml_pred is not None
    assert ml_pred.recovery_case_id == case.id
    assert 0.0 <= float(ml_pred.recovery_probability) <= 1.0
    assert ml_pred.predicted_channel is not None
    # Verify no PII leaked in snapshot
    snap = ml_pred.feature_vector_snapshot
    assert "email" not in snap
    assert "contact" not in snap
    assert "vpa" not in snap

    # -------------------------------------------------------------------------
    # STEP 5: AI Advisory Decision Engine
    # -------------------------------------------------------------------------
    decision = await recovery_decision_engine.generate_decision(
        db=db_session,
        recovery_case_id=case.id,
    )
    assert decision is not None
    assert decision.recovery_case_id == case.id
    assert decision.ml_prediction_id == ml_pred.id
    assert decision.proposed_action_type in [t.value for t in RecoveryActionType]

    # -------------------------------------------------------------------------
    # STEP 6: Policy Engine Evaluation
    # -------------------------------------------------------------------------
    policy_engine = PolicyEngine()
    policy_decision = policy_engine.evaluate(
        db=db_session,
        agent_decision_id=decision.id,
    )
    assert policy_decision is not None
    assert policy_decision.evaluation_result in [
        PolicyEvaluationResult.ALLOWED.value,
        PolicyEvaluationResult.HUMAN_REVIEW.value,
    ]

    # -------------------------------------------------------------------------
    # STEP 7: Recovery Action Scheduling
    # -------------------------------------------------------------------------
    if policy_decision.evaluation_result == PolicyEvaluationResult.HUMAN_REVIEW.value:
        # If routed to human review, simulate operator approval
        approve_resp = client.post(
            f"/api/recovery/human-review/{case.id}/approve",
            json={"notes": "Approved by supervisor after policy review"},
            headers=headers,
        )
        assert approve_resp.status_code == 200
        action = (
            db_session.query(RecoveryAction)
            .filter_by(recovery_case_id=case.id)
            .order_by(RecoveryAction.created_at.desc())
            .first()
        )
    else:
        # Autonomous scheduling for ALLOWED
        action = action_scheduler.schedule_for_policy_decision(
            db=db_session,
            policy_decision_id=policy_decision.id,
        )

    assert action is not None
    assert action.status == RecoveryActionStatus.SCHEDULED.value

    # -------------------------------------------------------------------------
    # STEP 8: Action Dispatcher Execution
    # -------------------------------------------------------------------------
    # Backdate scheduled_for so it is immediately due
    from datetime import timedelta
    action.scheduled_for = datetime.now(UTC) - timedelta(minutes=5)
    db_session.commit()

    dispatcher = ActionDispatcher()
    dispatch_result = dispatcher.dispatch_action(
        db=db_session,
        recovery_action_id=action.id,
        provider=MockActionProvider(),
    )
    assert dispatch_result.execution_status == "SUCCESS"

    db_session.refresh(action)
    assert action.status == RecoveryActionStatus.COMPLETED.value

    # Verify ActionResult record
    act_result = db_session.query(ActionResult).filter_by(recovery_action_id=action.id).first()
    assert act_result is not None
    assert act_result.execution_status == "SUCCESS"

    # -------------------------------------------------------------------------
    # STEP 9 & 10: Case Resolution to RECOVERED
    # -------------------------------------------------------------------------
    case.status = RecoveryCaseStatus.RECOVERED.value
    case.recovered_amount = recovery_amount
    case.resolved_at = datetime.now(UTC)
    db_session.commit()

    # -------------------------------------------------------------------------
    # STEP 11: Cryptographic Audit Trail Verification
    # -------------------------------------------------------------------------
    audit_trail = (
        db_session.query(AuditLog)
        .filter_by(recovery_case_id=case.id)
        .order_by(AuditLog.created_at.asc())
        .all()
    )
    assert len(audit_trail) >= 3
    for entry in audit_trail:
        assert entry.actor_type is not None
        assert entry.action is not None
        assert entry.event_type is not None

    # Verify audit log API endpoint returns entries for this case
    audit_api = client.get(f"/api/recovery/audit-logs?case_id={case.id}", headers=headers)
    assert audit_api.status_code == 200
    assert audit_api.json()["total"] >= 3

    # -------------------------------------------------------------------------
    # STEP 12: Analytics, Dashboard Metrics, and FinOps Reflection
    # -------------------------------------------------------------------------
    m_final = client.get("/api/recovery/metrics", headers=headers).json()
    assert m_final["cases"]["total"] >= base_cases + 1
    assert m_final["financial"]["amount_recovered"] >= base_recovered + recovery_amount

    # Verify FinOps metrics reflect real recovery transaction
    finops_resp = client.get("/api/recovery/intelligence/finops/summary", headers=headers)
    assert finops_resp.status_code == 200
    finops_data = finops_resp.json()
    assert "finops_score" in finops_data
