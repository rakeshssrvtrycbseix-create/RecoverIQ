"""Deterministic Development & Demo Mode Seeder for RecoverIQ.

Populates realistic, synthetic Indian Fintech recovery cases, payments, customers,
ML predictions, AI agent decisions, PolicyEngine validations, scheduled recovery actions,
and compliance audit records.

Strictly non-destructive, zero PII, fictional synthetic data only.
"""

import logging
import os
import random
import sys
import uuid
from datetime import UTC, datetime, timedelta
from decimal import Decimal

# Add project root to sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy.orm import Session
from app.core.database import Base, get_db, get_engine
from app.models import (
    Customer,
    Payment,
    Subscription,
    PaymentAttempt,
    PaymentEvent,
    RecoveryCase,
    MLPrediction,
    AgentDecision,
    PolicyDecision,
    RecoveryAction,
    ActionResult,
    AuditLog,
)
from app.models.enums import (
    CustomerRiskTier,
    PaymentStatus,
    RecoveryCaseStatus,
    RecoveryStage,
    RecoveryCaseClosedReason,
    PolicyEvaluationResult,
    RecoveryActionType,
    RecoveryActionStatus,
    ActionResultExecutionStatus,
    AuditActorType,
)

logger = logging.getLogger("recoveriq.seeder")
logging.basicConfig(level=logging.INFO)

DEMO_CUSTOMERS = [
    {"name": "Aarav Mehta", "email": "aarav.m****@example.in", "phone": "+91 98**** 1029", "tier": CustomerRiskTier.LOW.value},
    {"name": "Priya Nair", "email": "priya.n****@example.in", "phone": "+91 97**** 4821", "tier": CustomerRiskTier.STANDARD.value},
    {"name": "Karthik Rao", "email": "karthik.r****@example.in", "phone": "+91 99**** 8832", "tier": CustomerRiskTier.STANDARD.value},
    {"name": "Ananya Iyer", "email": "ananya.i****@example.in", "phone": "+91 98**** 3391", "tier": CustomerRiskTier.HIGH.value},
    {"name": "Rohan Sharma", "email": "rohan.s****@example.in", "phone": "+91 96**** 7741", "tier": CustomerRiskTier.STANDARD.value},
    {"name": "Divya Patel", "email": "divya.p****@example.in", "phone": "+91 94**** 2209", "tier": CustomerRiskTier.LOW.value},
    {"name": "Vikram Malhotra", "email": "vikram.m****@example.in", "phone": "+91 91**** 9042", "tier": CustomerRiskTier.BLOCKED.value},
    {"name": "Meera Joshi", "email": "meera.j****@example.in", "phone": "+91 93**** 6612", "tier": CustomerRiskTier.HIGH.value},
    {"name": "Siddharth Verma", "email": "sid.v****@example.in", "phone": "+91 98**** 5519", "tier": CustomerRiskTier.STANDARD.value},
    {"name": "Pooja Reddy", "email": "pooja.r****@example.in", "phone": "+91 95**** 1184", "tier": CustomerRiskTier.LOW.value},
    {"name": "Aditya Kapoor", "email": "aditya.k****@example.in", "phone": "+91 99**** 4432", "tier": CustomerRiskTier.STANDARD.value},
    {"name": "Sneha Kulkarni", "email": "sneha.k****@example.in", "phone": "+91 97**** 8891", "tier": CustomerRiskTier.HIGH.value},
    {"name": "Rahul Gupta", "email": "rahul.g****@example.in", "phone": "+91 92**** 3302", "tier": CustomerRiskTier.STANDARD.value},
    {"name": "Neha Desai", "email": "neha.d****@example.in", "phone": "+91 98**** 7714", "tier": CustomerRiskTier.LOW.value},
    {"name": "Amit Singhal", "email": "amit.s****@example.in", "phone": "+91 90**** 5521", "tier": CustomerRiskTier.BLOCKED.value},
    {"name": "Tanvi Chawla", "email": "tanvi.c****@example.in", "phone": "+91 93**** 9918", "tier": CustomerRiskTier.STANDARD.value},
    {"name": "Varun Bhat", "email": "varun.b****@example.in", "phone": "+91 96**** 1234", "tier": CustomerRiskTier.LOW.value},
    {"name": "Ishaan Sen", "email": "ishaan.s****@example.in", "phone": "+91 98**** 6789", "tier": CustomerRiskTier.STANDARD.value},
    {"name": "Ritu Mathur", "email": "ritu.m****@example.in", "phone": "+91 95**** 4321", "tier": CustomerRiskTier.HIGH.value},
    {"name": "Gaurav Roy", "email": "gaurav.r****@example.in", "phone": "+91 94**** 8765", "tier": CustomerRiskTier.LOW.value},
]

FAILURE_REASONS = [
    ("insufficient_funds", "Account balance below transaction threshold (NSF). Recommended retry on salary cycle."),
    ("bank_server_down", "Issuing bank core switch timed out (HDFC/ICICI UPI gateway degradation)."),
    ("authentication_failed", "Customer did not complete 3D Secure / OTP verification within window."),
    ("velocity_limit_exceeded", "Daily transaction volume limit exceeded on customer card instrument."),
    ("upi_pin_incorrect", "Customer entered invalid UPI MPIN during collect request."),
    ("card_expired", "Card instrument validity expired; fallback payment link required."),
    ("mandate_temporarily_suspended", "E-mandate auto-debit rejected due to technical hold by beneficiary bank."),
]

PROPOSED_ACTIONS = [
    (RecoveryActionType.RETRY_PAYMENT.value, 0.88, 4, "Optimal retry window scheduled during low bank failure rate period."),
    (RecoveryActionType.SEND_PAYMENT_LINK.value, 0.92, 1, "Instant customized payment link delivered with UPI intent deeplink."),
    (RecoveryActionType.SEND_NOTIFICATION.value, 0.79, 2, "Real-time interactive payment reminder dispatched via SMS & WhatsApp."),
    (RecoveryActionType.ESCALATE_HUMAN.value, 0.84, 6, "High value risk exception escalated to human operations queue for review."),
]


def seed_database(db: Session, force_reset: bool = False) -> dict:
    """Deterministic seeder populating rich development & demo data."""
    logger.info("Initializing RecoverIQ Demo Data Seeder...")

    # Ensure tables exist
    engine = get_engine()
    Base.metadata.create_all(bind=engine)

    if force_reset:
        logger.warning("Clearing existing development tables...")
        for table in reversed(Base.metadata.sorted_tables):
            db.execute(table.delete())
        db.commit()

    # Check if data already exists
    existing_cases = db.query(RecoveryCase).count()
    if existing_cases > 0 and not force_reset:
        logger.info(f"Database already contains {existing_cases} recovery cases. Skipping seed.")
        return {"cases_count": existing_cases, "status": "ALREADY_POPULATED"}

    rng = random.Random(42)  # Deterministic seed
    now = datetime.now(UTC)

    seeded_customers = []
    seeded_cases = []
    seeded_actions = []

    # 1. Create Customers
    for i, c_data in enumerate(DEMO_CUSTOMERS):
        cust = Customer(
            id=uuid.uuid4(),
            external_customer_id=f"cust_demo_{i+1001}",
            razorpay_customer_id=f"cust_rzp_{i+5001}",
            email_masked=c_data["email"],
            phone_masked=c_data["phone"],
            risk_tier=c_data["tier"],
            total_payments_count=rng.randint(3, 25),
            failed_payments_count=rng.randint(1, 4),
            recovered_payments_count=rng.randint(1, 8),
            metadata_json={"demo_mode": True, "display_name": c_data["name"], "city": rng.choice(["Bengaluru", "Mumbai", "Delhi NCR", "Hyderabad", "Pune"])},
            created_at=now - timedelta(days=rng.randint(30, 180)),
        )
        db.add(cust)
        seeded_customers.append(cust)
    db.flush()

    logger.info(f"Created {len(seeded_customers)} synthetic customers.")

    # 2. Create Recovery Cases with Full Interconnected Lifecycles
    # Case profiles:
    # 10 RECOVERED
    # 8 IN_RECOVERY / ACTION_PENDING
    # 6 ESCALATED_HUMAN (Pending Review in Human Review Queue)
    # 4 OPEN / ANALYZING
    # 4 CLOSED
    case_configs = [
        # (status, stage, count, is_human_review, is_recovered)
        (RecoveryCaseStatus.RECOVERED.value, RecoveryStage.SMART_RETRY.value, 10, False, True),
        (RecoveryCaseStatus.IN_RECOVERY.value, RecoveryStage.COMMUNICATION.value, 5, False, False),
        (RecoveryCaseStatus.ACTION_PENDING.value, RecoveryStage.SMART_RETRY.value, 3, False, False),
        (RecoveryCaseStatus.ESCALATED_HUMAN.value, RecoveryStage.ESCALATION.value, 6, True, False),
        (RecoveryCaseStatus.OPEN.value, RecoveryStage.INITIAL_FAILURE.value, 2, False, False),
        (RecoveryCaseStatus.ANALYZING.value, RecoveryStage.INITIAL_FAILURE.value, 2, False, False),
        (RecoveryCaseStatus.CLOSED.value, RecoveryStage.ESCALATION.value, 4, False, False),
    ]

    case_counter = 1

    for status_val, stage_val, count, is_human, is_rec in case_configs:
        for _ in range(count):
            cust = seeded_customers[case_counter % len(seeded_customers)]
            amount_rupees = rng.choice([899, 1499, 2999, 4999, 9999, 14999, 28500, 48000, 75000, 120000])
            amount_paise = amount_rupees * 100
            
            created_offset = rng.randint(1, 28)
            opened_time = now - timedelta(days=created_offset, hours=rng.randint(1, 12))
            
            reason_code, reason_desc = rng.choice(FAILURE_REASONS)
            action_code, action_prob, delay_hrs, action_desc = rng.choice(PROPOSED_ACTIONS)

            # Payment
            payment = Payment(
                id=uuid.uuid4(),
                customer_id=cust.id,
                amount=amount_paise,
                currency="INR",
                status=PaymentStatus.CAPTURED.value if is_rec else PaymentStatus.FAILED.value,
                razorpay_order_id=f"order_demo_{10000 + case_counter}",
                razorpay_invoice_id=f"inv_demo_{20000 + case_counter}",
                due_date=opened_time,
                captured_at=now - timedelta(hours=rng.randint(2, 48)) if is_rec else None,
                metadata_json={"gateway": "razorpay_test", "failure_code": reason_code},
                created_at=opened_time,
            )
            db.add(payment)
            db.flush()

            # Recovery Case
            rec_amount = amount_paise if is_rec else (amount_paise // 2 if status_val == RecoveryCaseStatus.IN_RECOVERY.value else 0)
            
            rec_case = RecoveryCase(
                id=uuid.uuid4(),
                payment_id=payment.id,
                customer_id=cust.id,
                status=status_val,
                recovery_stage=stage_val,
                amount_at_risk=amount_paise,
                recovered_amount=rec_amount,
                total_attempts_count=rng.randint(1, 3) if status_val != RecoveryCaseStatus.OPEN.value else 0,
                max_allowed_attempts=3,
                latest_failure_reason=reason_code,
                opened_at=opened_time,
                next_action_due_at=now + timedelta(hours=delay_hrs) if status_val in [RecoveryCaseStatus.ACTION_PENDING.value, RecoveryCaseStatus.IN_RECOVERY.value] else None,
                resolved_at=now - timedelta(hours=rng.randint(1, 24)) if (is_rec or status_val == RecoveryCaseStatus.CLOSED.value) else None,
                closed_reason=RecoveryCaseClosedReason.PAYMENT_RECOVERED.value if is_rec else (RecoveryCaseClosedReason.MAX_ATTEMPTS_EXCEEDED.value if status_val == RecoveryCaseStatus.CLOSED.value else None),
                metadata_json={"priority": "HIGH" if amount_rupees > 25000 else "STANDARD", "customer_name": cust.metadata_json.get("display_name")},
                created_at=opened_time,
            )
            db.add(rec_case)
            db.flush()
            seeded_cases.append(rec_case)

            # ML Prediction
            prob_val = Decimal(str(round(min(max(action_prob + rng.uniform(-0.05, 0.05), 0.05), 0.98), 4)))
            pred = MLPrediction(
                id=uuid.uuid4(),
                recovery_case_id=rec_case.id,
                model_name="xgboost_revenue_recovery_v2",
                model_version="2.4.1",
                recovery_probability=prob_val,
                predicted_channel=action_code,
                predicted_delay_hours=delay_hrs,
                feature_vector_snapshot={"failure_code": reason_code, "risk_tier": cust.risk_tier, "amount_paise": amount_paise},
                predicted_at=opened_time + timedelta(minutes=2),
            )
            db.add(pred)
            db.flush()

            # Agent Decision
            conf_val = Decimal(str(round(rng.uniform(0.82, 0.96), 4)))
            decision = AgentDecision(
                id=uuid.uuid4(),
                recovery_case_id=rec_case.id,
                ml_prediction_id=pred.id,
                agent_name="AutonomousRevenueAgent_v3",
                agent_version="3.2.0",
                prompt_template_version="v2.1_structured_json",
                proposed_action_type=action_code,
                confidence_score=conf_val,
                reasoning_summary=f"{action_desc} Root cause: {reason_desc}",
                suggested_payload={"channel": action_code, "delay_hours": delay_hrs, "priority": "HIGH" if amount_rupees > 25000 else "STANDARD"},
                token_usage={"prompt_tokens": 340, "completion_tokens": 120, "total_tokens": 460},
                decided_at=opened_time + timedelta(minutes=4),
            )
            db.add(decision)
            db.flush()

            # Policy Decision (PolicyEngine is the authoritative boundary)
            if is_human:
                pol_result = PolicyEvaluationResult.HUMAN_REVIEW.value
                pol_rule = "PR-003_HIGH_VALUE_THRESHOLD" if amount_rupees > 40000 else "PR-005_RISK_TIER_OVERRIDE"
                pol_reason = f"Deterministic threshold triggered: {pol_rule}. Manual safety signoff required before action dispatch."
            elif status_val == RecoveryCaseStatus.CLOSED.value:
                pol_result = PolicyEvaluationResult.BLOCKED.value
                pol_rule = "PR-002_MAX_ATTEMPTS_EXCEEDED"
                pol_reason = "Safety limit reached: Maximum allowed recovery attempts (3) exhausted."
            else:
                pol_result = PolicyEvaluationResult.ALLOWED.value
                pol_rule = "PR-001_POLICY_CLEARED"
                pol_reason = "Deterministic validation passed: Customer cooling period, velocity limits & channel safety verified."

            policy_dec = PolicyDecision(
                id=uuid.uuid4(),
                recovery_case_id=rec_case.id,
                agent_decision_id=decision.id,
                evaluation_result=pol_result,
                policy_engine_version="2.1.0_deterministic",
                triggered_rule_code=pol_rule,
                rule_name=pol_rule.replace("_", " ").title(),
                evaluation_details={"checks_passed": 7, "checks_failed": 0 if pol_result == "ALLOWED" else 1},
                decision_reason=pol_reason,
                decided_at=opened_time + timedelta(minutes=5),
            )
            db.add(policy_dec)
            db.flush()

            # Recovery Action & Result if allowed or completed
            if pol_result == PolicyEvaluationResult.ALLOWED.value or is_rec:
                action_status = RecoveryActionStatus.COMPLETED.value if is_rec else (
                    RecoveryActionStatus.EXECUTING.value if status_val == RecoveryCaseStatus.IN_RECOVERY.value else RecoveryActionStatus.SCHEDULED.value
                )
                
                rec_action = RecoveryAction(
                    id=uuid.uuid4(),
                    recovery_case_id=rec_case.id,
                    policy_decision_id=policy_dec.id,
                    action_idempotency_key=f"act_idem_{rec_case.id}_{case_counter}",
                    action_type=action_code,
                    status=action_status,
                    scheduled_for=opened_time + timedelta(hours=delay_hrs),
                    dispatched_at=opened_time + timedelta(hours=delay_hrs, minutes=1) if action_status in [RecoveryActionStatus.COMPLETED.value, RecoveryActionStatus.EXECUTING.value] else None,
                    completed_at=now - timedelta(hours=rng.randint(1, 10)) if action_status == RecoveryActionStatus.COMPLETED.value else None,
                    action_payload={"channel": action_code, "amount_paise": amount_paise, "recipient_masked": cust.email_masked},
                    created_at=opened_time + timedelta(minutes=6),
                )
                db.add(rec_action)
                db.flush()
                seeded_actions.append(rec_action)

                if action_status == RecoveryActionStatus.COMPLETED.value:
                    act_result = ActionResult(
                        id=uuid.uuid4(),
                        recovery_action_id=rec_action.id,
                        execution_status=ActionResultExecutionStatus.SUCCESS.value,
                        provider_reference_id=f"rzp_recov_txn_{rng.randint(1000000, 9999999)}",
                        provider_status_code="200_OK",
                        response_payload_summary={"status": "captured", "currency": "INR", "amount": amount_paise},
                        executed_at=now - timedelta(hours=rng.randint(1, 10)),
                    )
                    db.add(act_result)

            # Audit Trail
            audit_events = [
                ("PAYMENT_FAILURE_INGESTED", AuditActorType.SYSTEM_EVENT.value, "event_ingestion_pipeline", {"failure_reason": reason_code}),
                ("ML_PREDICTION_GENERATED", AuditActorType.AI_AGENT.value, "xgboost_v2.4", {"confidence": float(pred.recovery_probability)}),
                ("AI_DECISION_PROPOSED", AuditActorType.AI_AGENT.value, "revenue_agent_v3", {"action": action_code}),
                ("POLICY_EVALUATION_RECORDED", AuditActorType.POLICY_ENGINE.value, "policy_engine_v2", {"result": pol_result, "rule": pol_rule}),
            ]
            if is_rec:
                audit_events.append(("RECOVERY_ACTION_EXECUTED", AuditActorType.ACTION_EXECUTOR.value, "worker_worker_pool_1", {"status": "SUCCESS"}))
                audit_events.append(("RECOVERY_CASE_RESOLVED", AuditActorType.ACTION_EXECUTOR.value, "reconciliation_sweep", {"amount_recovered": amount_paise}))

            for ev_type, actor_type, actor_id, meta in audit_events:
                audit = AuditLog(
                    event_type=ev_type,
                    actor_type=actor_type,
                    actor_id=actor_id,
                    recovery_case_id=rec_case.id,
                    entity_type="RecoveryCase",
                    entity_id=rec_case.id,
                    action=ev_type.lower(),
                    previous_state={"status": "OPEN"},
                    new_state={"status": rec_case.status},
                    metadata_json=meta,
                    created_at=opened_time + timedelta(minutes=rng.randint(1, 30)),
                )
                db.add(audit)

            case_counter += 1

    db.commit()
    logger.info(f"Successfully seeded database: {len(seeded_customers)} customers, {len(seeded_cases)} cases, {len(seeded_actions)} recovery actions.")
    
    return {
        "customers_count": len(seeded_customers),
        "cases_count": len(seeded_cases),
        "actions_count": len(seeded_actions),
        "status": "SUCCESSFULLY_SEEDED"
    }


if __name__ == "__main__":
    force = "--reset" in sys.argv or "--force" in sys.argv
    db_gen = get_db()
    session = next(db_gen)
    try:
        res = seed_database(session, force_reset=force)
        print(f"Seed Result: {res}")
    finally:
        session.close()
