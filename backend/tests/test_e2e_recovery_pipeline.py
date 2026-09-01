"""
End-to-End Recovery Pipeline Integration Test.

Tests the complete primary objective recovery workflow:
Authentication
      ↓
Dashboard Metrics
      ↓
Payments & Webhook Ingestion
      ↓
Failed Payment / Recovery Case
      ↓
Risk / ML Prediction
      ↓
PolicyEngine Authoritative Decision
      ↓
Review Queue (Human Review)
      ↓
Approved Recovery Action
      ↓
Action Dispatcher / Payment Result
      ↓
Immutable Audit Trail
      ↓
Analytics & Control Planes (9L, 10A–10J)
"""

import hmac
import hashlib
import json
import uuid
from datetime import UTC, datetime
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.security import create_access_token
from app.models import (
    Customer,
    CustomerRiskTier,
    Payment,
    PaymentAttempt,
    PaymentEvent,
    PaymentStatus,
    RecoveryCase,
    RecoveryCaseStatus,
    MLPrediction,
    AgentDecision,
    PolicyDecision,
    RecoveryAction,
    ActionResult,
    AuditLog,
)
from app.services.payment_event_processor import payment_event_processor
from app.models.enums import (
    PolicyEvaluationResult,
    RecoveryActionType,
    RecoveryActionStatus,
    AuditActorType,
)
from app.policy.engine import PolicyEngine
from app.services.action_dispatcher import ActionDispatcher
from app.providers.mock import MockActionProvider
from tests.conftest import TEST_WEBHOOK_SECRET


def test_complete_end_to_end_recovery_pipeline(client: TestClient, db_session: Session):
    """
    Execute deterministic end-to-end integration test verifying the full revenue recovery loop.
    """
    # -------------------------------------------------------------------------
    # STEP 1: Authentication & RBAC Verification
    # -------------------------------------------------------------------------
    auth_resp = client.post(
        "/api/auth/token",
        json={"user_id": "op_e2e_lead", "role": "operator"},
    )
    assert auth_resp.status_code == 200
    token_data = auth_resp.json()
    assert "access_token" in token_data
    assert token_data["role"] == "operator"
    operator_token = token_data["access_token"]
    headers = {"Authorization": f"Bearer {operator_token}"}

    # Verify /api/auth/me
    me_resp = client.get("/api/auth/me", headers=headers)
    assert me_resp.status_code == 200
    assert me_resp.json()["id"] == "op_e2e_lead"
    assert me_resp.json()["role"] == "operator"

    # -------------------------------------------------------------------------
    # STEP 2: Initial Dashboard Metrics (Baseline)
    # -------------------------------------------------------------------------
    metrics_resp = client.get("/api/recovery/metrics", headers=headers)
    assert metrics_resp.status_code == 200
    initial_metrics = metrics_resp.json()
    assert "cases" in initial_metrics
    assert "financial" in initial_metrics
    assert "policy" in initial_metrics
    assert initial_metrics["cases"]["total"] == 0

    # -------------------------------------------------------------------------
    # STEP 3: Ingest Failed Payment Webhook Event
    # -------------------------------------------------------------------------
    event_id = f"evt_e2e_{uuid.uuid4().hex[:12]}"
    payment_id = f"pay_e2e_{uuid.uuid4().hex[:12]}"
    customer_id = f"cust_e2e_{uuid.uuid4().hex[:12]}"
    webhook_payload = {
        "entity": "event",
        "account_id": "acc_e2e_merchant",
        "event": "payment.failed",
        "contains": ["payment"],
        "payload": {
            "payment": {
                "entity": {
                    "id": payment_id,
                    "amount": 250000,  # ₹2,500.00 in paise
                    "currency": "INR",
                    "status": "failed",
                    "order_id": f"order_e2e_{uuid.uuid4().hex[:8]}",
                    "invoice_id": None,
                    "international": False,
                    "method": "card",
                    "amount_refunded": 0,
                    "refund_status": None,
                    "captured": False,
                    "description": "Enterprise Subscription Renewal",
                    "card_id": f"card_e2e_{uuid.uuid4().hex[:8]}",
                    "bank": "HDFC",
                    "wallet": None,
                    "vpa": None,
                    "email": "e2e.customer@enterprise.io",
                    "contact": "+919876543210",
                    "customer_id": customer_id,
                    "notes": {
                        "merchant_customer_id": customer_id,
                        "plan": "Enterprise Pro",
                    },
                    "fee": None,
                    "tax": None,
                    "error_code": "BAD_REQUEST_ERROR",
                    "error_description": "Card velocity limit exceeded on customer instrument.",
                    "error_source": "issuer",
                    "error_step": "payment_authentication",
                    "error_reason": "velocity_limit_exceeded",
                    "created_at": int(datetime.now(UTC).timestamp()),
                }
            }
        },
        "created_at": int(datetime.now(UTC).timestamp()),
    }

    raw_body = json.dumps(webhook_payload).encode("utf-8")
    signature = hmac.new(
        TEST_WEBHOOK_SECRET.encode("utf-8"),
        raw_body,
        hashlib.sha256,
    ).hexdigest()

    wh_resp = client.post(
        "/webhooks/razorpay",
        content=raw_body,
        headers={
            "X-Razorpay-Signature": signature,
            "X-Razorpay-Event-Id": event_id,
            "Content-Type": "application/json",
        },
    )
    assert wh_resp.status_code == 200
    assert wh_resp.json()["status"] == "ok"

    # Process the ingested payment event
    saved_event = db_session.query(PaymentEvent).filter_by(razorpay_event_id=event_id).first()
    assert saved_event is not None
    proc_result = payment_event_processor.process_payment_event(db_session, saved_event)
    assert proc_result.processing_status == "PROCESSED"

    # -------------------------------------------------------------------------
    # STEP 4: Verify Recovery Case Persistence
    # -------------------------------------------------------------------------
    case = db_session.query(RecoveryCase).first()
    assert case is not None
    assert case.amount_at_risk == 250000
    assert case.recovered_amount == 0

    # Verify case listing via API
    cases_resp = client.get("/api/recovery/cases", headers=headers)
    assert cases_resp.status_code == 200
    cases_list = cases_resp.json()
    assert cases_list["total"] >= 1
    case_item = cases_list["items"][0]
    assert case_item["amount_at_risk"] == 250000

    # -------------------------------------------------------------------------
    # STEP 5: ML Prediction Generation & Persistence
    # -------------------------------------------------------------------------
    prediction = MLPrediction(
        recovery_case_id=case.id,
        model_name="CanonicalRecoveryScorer",
        model_version="v1.0",
        recovery_probability=0.8800,
        predicted_channel="payment_link",
        predicted_delay_hours=4,
        feature_vector_snapshot={
            "amount_paise": 250000,
            "failure_reason": "velocity_limit_exceeded",
            "historical_recovery_rate": 0.75,
            "customer_tier": "HIGH",
        },
    )
    db_session.add(prediction)

    agent_decision = AgentDecision(
        recovery_case_id=case.id,
        ml_prediction_id=prediction.id,
        agent_name="RecoveryOrchestrator",
        agent_version="v1.0",
        prompt_template_version="v1.0",
        proposed_action_type=RecoveryActionType.SEND_PAYMENT_LINK.value,
        confidence_score=0.3500,
        reasoning_summary="High value recovery with velocity limit error; recommended instant payment link delivery.",
        suggested_payload={"amount_paise": 250000},
    )
    db_session.add(agent_decision)
    db_session.commit()

    # -------------------------------------------------------------------------
    # STEP 6: PolicyEngine Authoritative Decision Evaluation
    # -------------------------------------------------------------------------
    # Set customer to HIGH risk to trigger HUMAN_REVIEW policy rule
    customer = db_session.query(Customer).filter_by(id=case.customer_id).first()
    customer.risk_tier = CustomerRiskTier.HIGH.value
    db_session.commit()

    policy_engine = PolicyEngine()
    policy_decision = policy_engine.evaluate(
        db=db_session,
        agent_decision_id=agent_decision.id,
    )
    assert policy_decision is not None
    # High risk or amount threshold routes to HUMAN_REVIEW
    assert policy_decision.evaluation_result == PolicyEvaluationResult.HUMAN_REVIEW.value

    # Update case status
    case.status = RecoveryCaseStatus.ESCALATED_HUMAN.value
    db_session.commit()

    # -------------------------------------------------------------------------
    # STEP 7: Human Review Queue Visibility & Operator Approval
    # -------------------------------------------------------------------------
    review_resp = client.get("/api/recovery/human-review", headers=headers)
    assert review_resp.status_code == 200
    review_queue = review_resp.json()
    assert review_queue["total"] >= 1
    assert any(item["case_id"] == str(case.id) for item in review_queue["items"])

    # Approve the case via Operator API
    approve_resp = client.post(
        f"/api/recovery/human-review/{case.id}/approve",
        json={"notes": "Approved by senior recovery officer after customer verification."},
        headers=headers,
    )
    assert approve_resp.status_code == 200
    approve_result = approve_resp.json()
    assert approve_result["success"] is True
    assert approve_result["action"] == "APPROVED"
    assert approve_result["scheduled_action_id"] is not None

    # -------------------------------------------------------------------------
    # STEP 8: Action Dispatcher Execution & Result Recording
    # -------------------------------------------------------------------------
    action = db_session.query(RecoveryAction).filter_by(recovery_case_id=case.id).first()
    assert action is not None
    assert action.status == RecoveryActionStatus.SCHEDULED.value

    dispatcher = ActionDispatcher()
    dispatch_result = dispatcher.dispatch_action(
        db=db_session,
        recovery_action_id=action.id,
        provider=MockActionProvider(),
    )
    assert dispatch_result.execution_status == "SUCCESS"

    db_session.refresh(action)
    assert action.status == RecoveryActionStatus.COMPLETED.value

    # Mark recovery completed
    case.status = RecoveryCaseStatus.RECOVERED.value
    case.recovered_amount = 250000
    db_session.commit()

    # -------------------------------------------------------------------------
    # STEP 9: Verify Immutable Audit Trail
    # -------------------------------------------------------------------------
    audit_logs = db_session.query(AuditLog).filter_by(recovery_case_id=case.id).all()
    assert len(audit_logs) >= 3
    event_types = {log.event_type for log in audit_logs}
    assert "POLICY_DECISION_EVALUATED" in event_types
    assert "HUMAN_REVIEW_APPROVED" in event_types
    assert "RECOVERY_ACTION_SCHEDULED" in event_types
    assert "RECOVERY_ACTION_EXECUTED" in event_types

    # Query audit logs via API
    audit_resp = client.get(f"/api/recovery/audit-logs?case_id={case.id}", headers=headers)
    assert audit_resp.status_code == 200
    assert audit_resp.json()["total"] >= 3

    # -------------------------------------------------------------------------
    # STEP 10: Verify Updated Analytics & Control Planes (9L, 10A–10J)
    # -------------------------------------------------------------------------
    final_metrics_resp = client.get("/api/recovery/metrics", headers=headers)
    assert final_metrics_resp.status_code == 200
    final_metrics = final_metrics_resp.json()
    assert final_metrics["cases"]["recovered"] >= 1
    assert final_metrics["financial"]["amount_recovered"] >= 250000

    # 10A: Security Trust Center
    sec_resp = client.get("/api/recovery/security/trust-center", headers=headers)
    assert sec_resp.status_code == 200
    assert "trust_score" in sec_resp.json()

    # 10B: Compliance
    comp_resp = client.get("/api/recovery/intelligence/compliance", headers=headers)
    assert comp_resp.status_code == 200
    assert "compliance_score" in comp_resp.json()

    # 10C: Resilience
    res_resp = client.get("/api/recovery/intelligence/resilience", headers=headers)
    assert res_resp.status_code == 200
    assert "resilience_score" in res_resp.json()

    # 10D: Observability
    obs_resp = client.get("/api/recovery/intelligence/observability", headers=headers)
    assert obs_resp.status_code == 200
    assert "observability_score" in obs_resp.json()

    # 10E: Data Governance
    dg_resp = client.get("/api/recovery/intelligence/data-governance", headers=headers)
    assert dg_resp.status_code == 200
    assert "governance_score" in dg_resp.json()

    # 10F: Performance
    perf_resp = client.get("/api/recovery/intelligence/performance", headers=headers)
    assert perf_resp.status_code == 200
    assert "score" in perf_resp.json()

    # 10G: Release Governance
    rel_resp = client.get("/api/recovery/intelligence/release-governance/summary", headers=headers)
    assert rel_resp.status_code == 200
    assert "governance_score" in rel_resp.json()

    # 10H: Zero Trust
    zt_resp = client.get("/api/recovery/intelligence/zero-trust/summary", headers=headers)
    assert zt_resp.status_code == 200
    assert "zero_trust_score" in zt_resp.json()

    # 10I: FinOps
    fin_resp = client.get("/api/recovery/intelligence/finops/summary", headers=headers)
    assert fin_resp.status_code == 200
    assert "finops_score" in fin_resp.json()

    # 10J: AI/ML Governance
    mlg_resp = client.get("/api/recovery/intelligence/ml-governance/summary", headers=headers)
    assert mlg_resp.status_code == 200
    assert "governance_score" in mlg_resp.json()
