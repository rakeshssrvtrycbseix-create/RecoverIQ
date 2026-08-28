from typing import Protocol

from app.agent.prompts import PROMPT_VERSION_V1_0
from app.agent.schemas import AgentContextPayload, AgentDecisionOutput
from app.models.enums import RecoveryActionType

PERMANENT_FAILURE_REASONS = {
    "card_inactive",
    "card_blocked",
    "account_closed",
    "fraud_suspected",
    "invalid_card_details",
}


class AIProvider(Protocol):
    """Protocol interface for AI recommendation providers."""

    async def generate_decision(
        self,
        context: AgentContextPayload,
        prompt_version: str = PROMPT_VERSION_V1_0,
    ) -> AgentDecisionOutput:
        """Generate a recovery strategy recommendation from the given context."""
        ...


class MockAIProvider:
    """
    Deterministic mock AI provider for local development and unit testing.

    Guarantees:
    - Zero randomness (bitwise deterministic output for identical input).
    - No external network or LLM API calls.
    - Full conformance with AgentDecisionOutput schema.
    """

    async def generate_decision(
        self,
        context: AgentContextPayload,
        prompt_version: str = PROMPT_VERSION_V1_0,
    ) -> AgentDecisionOutput:
        case = context.recovery_case
        payment = context.payment
        ml = context.ml_prediction
        reason = (case.latest_failure_reason or "").lower().strip()

        # 1. Exhausted attempt ceiling
        if case.total_attempts_count >= case.max_allowed_attempts:
            return AgentDecisionOutput(
                proposed_action_type=RecoveryActionType.HALT_SUBSCRIPTION,
                confidence_score=0.95,
                reasoning_summary=(
                    f"Maximum attempt ceiling ({case.max_allowed_attempts}) reached. "
                    "Halting subscription to prevent customer disruption."
                ),
                suggested_payload={
                    "channel": "GATEWAY_API",
                    "target_recipient_type": "GATEWAY",
                    "reason_code": "MAX_ATTEMPTS_EXCEEDED",
                },
                recommended_delay_hours=0,
                agent_name="MockRecoveryOrchestrator",
                agent_version="v1.0",
                prompt_template_version=prompt_version,
            )

        # 2. High-value transaction at risk
        if payment.amount >= 5000000:  # >= ₹50,000
            return AgentDecisionOutput(
                proposed_action_type=RecoveryActionType.ESCALATE_HUMAN,
                confidence_score=0.88,
                reasoning_summary=(
                    f"High-value recovery case (amount ₹{payment.amount / 100:.2f}) "
                    "requires manual operational review before money movement."
                ),
                suggested_payload={
                    "channel": "INTERNAL_QUEUE",
                    "target_recipient_type": "OPS_AGENT",
                    "priority_level": "HIGH",
                },
                recommended_delay_hours=0,
                agent_name="MockRecoveryOrchestrator",
                agent_version="v1.0",
                prompt_template_version=prompt_version,
            )

        # 3. Permanent payment or account failure
        if reason in PERMANENT_FAILURE_REASONS:
            return AgentDecisionOutput(
                proposed_action_type=RecoveryActionType.SEND_PAYMENT_LINK,
                confidence_score=0.90,
                reasoning_summary=(
                    f"Permanent gateway failure detected ('{reason}'). "
                    "Direct retry will fail; dispatching payment link."
                ),
                suggested_payload={
                    "channel": "EMAIL",
                    "target_recipient_type": "CUSTOMER",
                    "custom_message_template": "UPDATE_PAYMENT_METHOD",
                },
                recommended_delay_hours=0,
                agent_name="MockRecoveryOrchestrator",
                agent_version="v1.0",
                prompt_template_version=prompt_version,
            )

        # 4. High recovery probability (soft/transient failure)
        if ml and (
            ml.priority == "HIGH_RECOVERY_POTENTIAL"
            or ml.recovery_probability >= 0.75
        ):
            pred_delay = (
                ml.predicted_delay_hours
                if ml.predicted_delay_hours is not None
                else 2
            )
            return AgentDecisionOutput(
                proposed_action_type=RecoveryActionType.RETRY_PAYMENT,
                confidence_score=round(min(0.95, ml.confidence), 4),
                reasoning_summary=(
                    f"High recovery probability ({ml.recovery_probability:.2%}) "
                    f"for transient failure ('{reason}'). Smart retry recommended."
                ),
                suggested_payload={
                    "channel": "GATEWAY_API",
                    "target_recipient_type": "GATEWAY",
                },
                recommended_delay_hours=pred_delay,
                agent_name="MockRecoveryOrchestrator",
                agent_version="v1.0",
                prompt_template_version=prompt_version,
            )

        # 5. Medium recovery probability / user friction
        if ml and (
            ml.priority == "MEDIUM_RECOVERY_POTENTIAL"
            or ml.recovery_probability >= 0.40
        ):
            return AgentDecisionOutput(
                proposed_action_type=RecoveryActionType.SEND_PAYMENT_LINK,
                confidence_score=0.75,
                reasoning_summary=(
                    f"Medium recovery probability ({ml.recovery_probability:.2%}). "
                    "Dispatching authenticated payment link to customer."
                ),
                suggested_payload={
                    "channel": "WHATSAPP",
                    "target_recipient_type": "CUSTOMER",
                },
                recommended_delay_hours=12,
                agent_name="MockRecoveryOrchestrator",
                agent_version="v1.0",
                prompt_template_version=prompt_version,
            )

        # 6. Default low recovery / awareness needed
        return AgentDecisionOutput(
            proposed_action_type=RecoveryActionType.SEND_NOTIFICATION,
            confidence_score=0.65,
            reasoning_summary=(
                f"Low recovery probability for reason '{reason}'. "
                "Sending awareness notification to customer prior to further retry."
            ),
            suggested_payload={
                "channel": "EMAIL",
                "target_recipient_type": "CUSTOMER",
            },
            recommended_delay_hours=24,
            agent_name="MockRecoveryOrchestrator",
            agent_version="v1.0",
            prompt_template_version=prompt_version,
        )


mock_ai_provider = MockAIProvider()
