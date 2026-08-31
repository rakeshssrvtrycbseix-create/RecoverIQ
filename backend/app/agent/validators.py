import re
from typing import Any

from app.agent.exceptions import InvalidAIOutputError, UnsafeAIOutputError
from app.agent.schemas import AgentDecisionOutput
from app.models.enums import RecoveryActionType

# Forbidden sensitive keywords in keys or data
FORBIDDEN_OUTPUT_KEYS = {
    "email",
    "phone",
    "contact",
    "card_number",
    "pan",
    "cvv",
    "cvc",
    "pin",
    "password",
    "secret",
    "token",
    "api_key",
    "secret_key",
    "private_key",
    "auth_token",
    "access_token",
    "webhook_secret",
    "razorpay_key",
    "razorpay_secret",
    "bearer",
    "authorization",
    "cookie",
    "signature",
}

FORBIDDEN_KEY_SUBSTRINGS = {
    "password",
    "secret",
    "cvv",
    "cvc",
    "api_key",
    "auth_token",
    "access_token",
    "private_key",
    "razorpay_",
}

# Regex patterns for accidental PII or credential leaks in text values
EMAIL_PATTERN = re.compile(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+")
CARD_PATTERN = re.compile(r"\b(?:\d[ -]*?){13,19}\b")
SECRET_TOKEN_PATTERN = re.compile(
    r"(?:sk_live_|sk_test_|rzp_live_|rzp_test_|Bearer\s+|eyJh)[A-Za-z0-9_\-\.]{8,}"
)
FORBIDDEN_VALUE_LITERALS = [
    "razorpay_secret",
    "webhook_secret",
    "razorpay_key",
    "api_key",
    "private_key",
]


def _recursive_inspect_payload(data: Any, path: str = "payload") -> None:
    """Recursively validate dictionaries and lists for forbidden secrets and PII."""
    if isinstance(data, dict):
        for k, v in data.items():
            key_str = str(k).lower()
            current_path = f"{path}.{k}"
            is_forbidden_key = (
                key_str in FORBIDDEN_OUTPUT_KEYS
                or any(sub in key_str for sub in FORBIDDEN_KEY_SUBSTRINGS)
                or key_str.startswith("card_")
            )
            if is_forbidden_key:
                raise UnsafeAIOutputError(
                    f"Unsafe AI output: Forbidden key '{k}' at {current_path}"
                )
            _recursive_inspect_payload(v, current_path)
    elif isinstance(data, list | tuple | set):
        for i, item in enumerate(data):
            _recursive_inspect_payload(item, f"{path}[{i}]")
    elif isinstance(data, str):
        _inspect_string_content(data, path)


def _inspect_string_content(text: str, path: str) -> None:
    """Inspect raw text content for email, card numbers, or secret tokens."""
    if EMAIL_PATTERN.search(text):
        raise UnsafeAIOutputError(f"Unsafe AI output: Email address detected at {path}")
    digits_only = re.sub(r"\D", "", text)
    if len(digits_only) >= 13 and CARD_PATTERN.search(text):
        raise UnsafeAIOutputError(
            f"Unsafe AI output: Card-like number detected at {path}"
        )
    if SECRET_TOKEN_PATTERN.search(text):
        raise UnsafeAIOutputError(
            f"Unsafe AI output: Secret token prefix detected at {path}"
        )
    text_lower = text.lower()
    for literal in FORBIDDEN_VALUE_LITERALS:
        if literal in text_lower:
            raise UnsafeAIOutputError(
                f"Unsafe AI output: Forbidden credential literal '{literal}' at {path}"
            )


def validate_agent_decision_output(output: AgentDecisionOutput) -> None:
    """
    Strict safety and structural validation for generated AgentDecisionOutput.

    Guarantees:
    1. proposed_action_type is an authorized RecoveryActionType enum.
    2. confidence_score is bounded in [0.0, 1.0].
    3. recommended_delay_hours is bounded in [0, 168].
    4. reasoning_summary is free from PII, card numbers, and secret tokens.
    5. suggested_payload is deeply inspected for forbidden keys, PII, and credentials.
    """
    if not isinstance(output, AgentDecisionOutput):
        raise InvalidAIOutputError(
            f"Expected AgentDecisionOutput, got {type(output).__name__}"
        )

    # 1. Action type validation
    if output.proposed_action_type not in RecoveryActionType:
        raise InvalidAIOutputError(
            f"Invalid proposed_action_type: '{output.proposed_action_type}'. "
            f"Must be one of {[a.value for a in RecoveryActionType]}"
        )

    # 2. Confidence score validation
    if not (0.0 <= output.confidence_score <= 1.0):
        raise InvalidAIOutputError(
            f"Confidence score {output.confidence_score} out of bounds [0.0, 1.0]"
        )

    # 3. Recommended delay validation
    if not (0 <= output.recommended_delay_hours <= 168):
        raise InvalidAIOutputError(
            f"Recommended delay {output.recommended_delay_hours} out of bounds [0, 168]"
        )

    # 4. Reasoning content safety
    if not output.reasoning_summary or not output.reasoning_summary.strip():
        raise InvalidAIOutputError("Reasoning summary cannot be empty")
    _inspect_string_content(output.reasoning_summary, "reasoning_summary")

    # 5. Suggested payload deep safety
    _recursive_inspect_payload(output.suggested_payload, "suggested_payload")
