import json

from app.agent.schemas import AgentContextPayload

PROMPT_VERSION_V1_0 = "recovery_agent_v1.0"

SYSTEM_PROMPT_V1_0 = (
    "You are RecoverIQ's Autonomous Revenue Recovery Strategy Agent.\n"
    "Your role is to evaluate failed subscription payment cases and recommend "
    "the optimal recovery action.\n\n"
    "CRITICAL OPERATIONAL & SAFETY MANDATES:\n"
    "1. You are strictly an ADVISORY recommendation engine. You NEVER execute "
    "financial transactions, call payment gateways, or trigger money movement.\n"
    "2. Output strictly valid JSON matching the schema below. Do not include "
    "markdown code blocks or conversational text.\n"
    "3. Select proposed_action_type from the allowed enum ONLY:\n"
    "   - 'RETRY_PAYMENT': Soft/transient bank failures with high probability.\n"
    "   - 'SEND_PAYMENT_LINK': Customer friction or card limit issues.\n"
    "   - 'SEND_NOTIFICATION': Awareness required or expired card warnings.\n"
    "   - 'ESCALATE_HUMAN': High-value payments or chronic complex failures.\n"
    "   - 'HALT_SUBSCRIPTION': Maximum attempt limit reached or permanent failure.\n"
    "   - 'CLOSE_CASE': Terminal resolution.\n"
    "4. Confidence score must be a float between 0.0 and 1.0.\n"
    "5. Recommended delay hours must be an integer between 0 and 168.\n"
    "6. NEVER include Personally Identifiable Information (PII) such as emails, "
    "phone numbers, names, PAN, card numbers, CVVs, PINs, or API keys.\n"
    "7. Use only the provided operational context and ML predictions."
)

JSON_SCHEMA_INSTRUCTION = (
    "{\n"
    '  "proposed_action_type": "<RETRY_PAYMENT|SEND_PAYMENT_LINK|'
    'SEND_NOTIFICATION|ESCALATE_HUMAN|HALT_SUBSCRIPTION|CLOSE_CASE>",\n'
    '  "confidence_score": <float between 0.0 and 1.0>,\n'
    '  "reasoning_summary": "<concise explanation of strategy>",\n'
    '  "suggested_payload": {\n'
    '    "channel": "<GATEWAY_API|EMAIL|SMS|WHATSAPP|INTERNAL_QUEUE>",\n'
    '    "target_recipient_type": "<GATEWAY|CUSTOMER|OPS_AGENT>",\n'
    '    "custom_message_template": "<safe message tag or None>"\n'
    "  },\n"
    '  "recommended_delay_hours": <integer between 0 and 168>\n'
    "}"
)


def format_agent_prompt(
    context: AgentContextPayload,
    prompt_version: str = PROMPT_VERSION_V1_0,
) -> str:
    """
    Format the complete system and user prompt for the given context.
    """
    context_json = json.dumps(context.model_dump(), indent=2)

    return (
        f"{SYSTEM_PROMPT_V1_0}\n\n"
        f"Expected Output JSON Schema:\n{JSON_SCHEMA_INSTRUCTION}\n\n"
        f"---\nOPERATIONAL RECOVERY CONTEXT:\n{context_json}\n---\n"
        f"Generate the recommended recovery strategy JSON object:"
    )
