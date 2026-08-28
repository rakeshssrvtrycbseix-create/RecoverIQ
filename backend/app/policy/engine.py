import logging
import uuid
from datetime import datetime

from sqlalchemy.orm import Session

from app.models import (
    AgentDecision,
    AuditActorType,
    AuditLog,
    Customer,
    Payment,
    PaymentAttempt,
    PolicyDecision,
    RecoveryCase,
)
from app.policy.exceptions import (
    AgentDecisionNotFoundError,
    PolicyPersistenceError,
    RecoveryCaseNotFoundError,
)
from app.policy.rules import evaluate_rules

logger = logging.getLogger(__name__)


class PolicyEngine:
    """
    Authoritative deterministic Policy Engine that validates proposed AgentDecision
    recommendations against hard financial, security, and operational guardrails.

    Guarantees:
    - 100% deterministic rule evaluation (zero LLM/network calls).
    - Immutable append-only persistence in policy_decisions.
    - Zero money movement or RecoveryAction creation.
    - Atomic transaction boundary for PolicyDecision and AuditLog.
    """

    def evaluate(
        self,
        db: Session,
        agent_decision_id: uuid.UUID,
        as_of: datetime | None = None,
    ) -> PolicyDecision:
        """
        Evaluate an AgentDecision and persist the authoritative PolicyDecision.
        """
        logger.info(
            "policy_evaluation_started",
            extra={"agent_decision_id": str(agent_decision_id)},
        )

        # 1. Load AgentDecision
        agent_decision = (
            db.query(AgentDecision)
            .filter_by(id=agent_decision_id)
            .first()
        )
        if not agent_decision:
            raise AgentDecisionNotFoundError(
                f"AgentDecision '{agent_decision_id}' not found"
            )

        # 2. Load associated RecoveryCase aggregate
        case = (
            db.query(RecoveryCase)
            .filter_by(id=agent_decision.recovery_case_id)
            .first()
        )
        if not case:
            raise RecoveryCaseNotFoundError(
                f"RecoveryCase '{agent_decision.recovery_case_id}' not found"
            )

        payment = db.query(Payment).filter_by(id=case.payment_id).first()
        if not payment:
            raise RecoveryCaseNotFoundError(
                f"Payment '{case.payment_id}' for RecoveryCase not found"
            )

        customer = db.query(Customer).filter_by(id=case.customer_id).first()
        if not customer:
            raise RecoveryCaseNotFoundError(
                f"Customer '{case.customer_id}' for RecoveryCase not found"
            )

        # 3. Load historical PaymentAttempts
        attempts = (
            db.query(PaymentAttempt)
            .filter_by(payment_id=payment.id)
            .order_by(PaymentAttempt.attempt_number.asc())
            .all()
        )

        # 4. Evaluate deterministic rules
        outcome = evaluate_rules(
            case=case,
            payment=payment,
            customer=customer,
            agent_decision=agent_decision,
            attempts=attempts,
            as_of=as_of,
        )

        # 5. Prepare PolicyDecision ORM entity
        policy_decision = PolicyDecision(
            recovery_case_id=case.id,
            agent_decision_id=agent_decision.id,
            evaluation_result=outcome.evaluation_result.value,
            policy_engine_version=outcome.policy_engine_version,
            triggered_rule_code=outcome.triggered_rule_code,
            rule_name=outcome.rule_name,
            evaluation_details=outcome.evaluation_details,
            decision_reason=outcome.decision_reason,
        )

        # 6. Atomic transaction persistence
        try:
            db.add(policy_decision)
            db.flush()

            # Record audit trail
            audit = AuditLog(
                event_type="POLICY_DECISION_EVALUATED",
                actor_type=AuditActorType.POLICY_ENGINE.value,
                actor_id="policy_engine_v1",
                recovery_case_id=case.id,
                entity_type="policy_decisions",
                entity_id=policy_decision.id,
                action="EVALUATE_POLICY",
                previous_state=None,
                new_state={
                    "evaluation_result": policy_decision.evaluation_result,
                    "triggered_rule_code": policy_decision.triggered_rule_code,
                    "rule_name": policy_decision.rule_name,
                    "policy_engine_version": policy_decision.policy_engine_version,
                },
                metadata_json={
                    "proposed_action_type": str(agent_decision.proposed_action_type),
                },
            )
            db.add(audit)
            db.commit()
            db.refresh(policy_decision)

            logger.info(
                "policy_decision_persisted",
                extra={
                    "policy_decision_id": str(policy_decision.id),
                    "case_id": str(case.id),
                    "evaluation_result": policy_decision.evaluation_result,
                    "triggered_rule": policy_decision.triggered_rule_code,
                },
            )
            return policy_decision

        except Exception as exc:
            db.rollback()
            logger.error(
                "policy_decision_persistence_failed",
                extra={"case_id": str(case.id), "error": str(exc)},
            )
            raise PolicyPersistenceError(
                f"Failed to persist PolicyDecision: {exc}"
            ) from exc


policy_engine = PolicyEngine()
