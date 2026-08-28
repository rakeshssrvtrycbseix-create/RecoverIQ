import logging
import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy.orm import Session

from app.agent.context_builder import build_agent_context
from app.agent.exceptions import (
    AgentDecisionError,
    AIProviderError,
    DecisionPersistenceError,
    RecoveryCaseNotFoundError,
)
from app.agent.prompts import PROMPT_VERSION_V1_0
from app.agent.provider import AIProvider, mock_ai_provider
from app.agent.validators import validate_agent_decision_output
from app.models import (
    AgentDecision,
    AuditActorType,
    AuditLog,
    Customer,
    MLPrediction,
    Payment,
    PaymentAttempt,
    RecoveryCase,
)

logger = logging.getLogger(__name__)


class RecoveryDecisionEngine:
    """
    Core AI Decision Engine that analyzes RecoveryCase aggregates and generates
    advisory recovery strategy proposals.

    Guarantees:
    - Purely advisory: Never creates RecoveryAction records or triggers gateway APIs.
    - Zero-PII input context and recursive output safety validation.
    - Atomic persistence of AgentDecision and AuditLog.
    """

    def __init__(self, default_provider: AIProvider | None = None) -> None:
        self.default_provider = default_provider or mock_ai_provider

    async def generate_decision(
        self,
        db: Session,
        recovery_case_id: uuid.UUID,
        ai_provider: AIProvider | None = None,
        prompt_version: str = PROMPT_VERSION_V1_0,
        as_of: datetime | None = None,
    ) -> AgentDecision:
        """
        Generate and persist an advisory AgentDecision for an active RecoveryCase.
        """
        provider = ai_provider or self.default_provider

        logger.info(
            "ai_decision_generation_started",
            extra={
                "recovery_case_id": str(recovery_case_id),
                "prompt_version": prompt_version,
            },
        )

        # 1. Load RecoveryCase aggregate
        case = (
            db.query(RecoveryCase)
            .filter_by(id=recovery_case_id)
            .first()
        )
        if not case:
            raise RecoveryCaseNotFoundError(
                f"RecoveryCase '{recovery_case_id}' not found"
            )

        # 2. Load associated Payment and Customer
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

        # 3. Load latest ML Prediction (if available)
        ml_prediction = (
            db.query(MLPrediction)
            .filter_by(recovery_case_id=case.id)
            .order_by(MLPrediction.predicted_at.desc())
            .first()
        )

        # 4. Load historical PaymentAttempts
        attempts = (
            db.query(PaymentAttempt)
            .filter_by(payment_id=payment.id)
            .order_by(PaymentAttempt.attempt_number.asc())
            .all()
        )

        # 5. Build Zero-PII Context Payload
        context = build_agent_context(
            recovery_case=case,
            payment=payment,
            customer=customer,
            attempts=attempts,
            ml_prediction=ml_prediction,
            as_of=as_of,
        )

        # 6. Generate Decision via AI Provider
        try:
            decision_output = await provider.generate_decision(
                context=context,
                prompt_version=prompt_version,
            )
        except Exception as exc:
            logger.error(
                "ai_provider_inference_failed",
                extra={"case_id": str(case.id), "error": str(exc)},
            )
            raise AIProviderError(
                f"AI Provider failed to generate decision: {exc}"
            ) from exc

        # 7. Validate Output Safety & Schema Conformance
        validate_agent_decision_output(decision_output)

        # 8. Prepare AgentDecision ORM Entity
        conf_decimal = Decimal(str(round(decision_output.confidence_score, 4)))
        action_type_str = (
            decision_output.proposed_action_type.value
            if hasattr(decision_output.proposed_action_type, "value")
            else str(decision_output.proposed_action_type)
        )

        suggested_payload_full = dict(decision_output.suggested_payload)
        suggested_payload_full["recommended_delay_hours"] = (
            decision_output.recommended_delay_hours
        )

        agent_decision = AgentDecision(
            recovery_case_id=case.id,
            ml_prediction_id=ml_prediction.id if ml_prediction else None,
            agent_name=decision_output.agent_name,
            agent_version=decision_output.agent_version,
            prompt_template_version=decision_output.prompt_template_version,
            proposed_action_type=action_type_str,
            confidence_score=conf_decimal,
            reasoning_summary=decision_output.reasoning_summary,
            suggested_payload=suggested_payload_full,
            token_usage=decision_output.token_usage,
        )

        # 9. Atomic Transaction Persistence
        try:
            db.add(agent_decision)
            db.flush()

            # Create immutable audit log entry
            audit = AuditLog(
                event_type="AGENT_DECISION_GENERATED",
                actor_type=AuditActorType.AI_AGENT.value,
                actor_id="RecoverIQ-Agent-v1",
                recovery_case_id=case.id,
                entity_type="agent_decisions",
                entity_id=agent_decision.id,
                action="PROPOSE_ACTION",
                previous_state=None,
                new_state={
                    "proposed_action_type": action_type_str,
                    "confidence_score": float(conf_decimal),
                    "prompt_template_version": decision_output.prompt_template_version,
                    "recommended_delay_hours": decision_output.recommended_delay_hours,
                },
                metadata_json={
                    "agent_name": decision_output.agent_name,
                    "agent_version": decision_output.agent_version,
                },
            )
            db.add(audit)
            db.commit()
            db.refresh(agent_decision)

            logger.info(
                "ai_decision_persisted",
                extra={
                    "decision_id": str(agent_decision.id),
                    "case_id": str(case.id),
                    "action_type": action_type_str,
                    "confidence": float(conf_decimal),
                },
            )
            return agent_decision

        except Exception as exc:
            db.rollback()
            if isinstance(exc, AgentDecisionError):
                raise
            logger.error(
                "ai_decision_persistence_failed",
                extra={"case_id": str(case.id), "error": str(exc)},
            )
            raise DecisionPersistenceError(
                f"Failed to persist AgentDecision: {exc}"
            ) from exc


recovery_decision_engine = RecoveryDecisionEngine()
