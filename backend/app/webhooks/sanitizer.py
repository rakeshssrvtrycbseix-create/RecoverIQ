import copy
import re
from typing import Any

# Forbidden sensitive field names to redact if present in any dictionary or notes
FORBIDDEN_KEY_PATTERNS = {
    "cvv",
    "cvc",
    "pin",
    "password",
    "secret",
    "webhook_secret",
    "key_secret",
    "api_secret",
    "auth_token",
    "access_token",
    "bearer",
    "private_key",
    "otp",
    "card_number",
    "pan",
    "security_code",
}


def mask_email(email: str | None) -> str | None:
    """Mask email for privacy (e.g. 'john.doe@example.com' -> 'j***e@example.com')."""
    if not email or not isinstance(email, str) or "@" not in email:
        return email

    parts = email.split("@", 1)
    username, domain = parts[0], parts[1]

    if len(username) <= 2:
        masked_user = username[0] + "***"
    else:
        masked_user = username[0] + "***" + username[-1]

    return f"{masked_user}@{domain}"


def mask_phone(phone: str | None) -> str | None:
    """Mask a phone number (e.g. '+919876543210' -> '+91******3210')."""
    if not phone or not isinstance(phone, str):
        return phone

    digits_only = re.sub(r"\D", "", phone)
    if len(digits_only) <= 4:
        return "****"

    # Keep leading country indicator if present, mask middle, show last 4 digits
    prefix = "+" if phone.startswith("+") else ""
    if phone.startswith("+91") and len(digits_only) == 12:
        return f"+91******{digits_only[-4:]}"

    last4 = digits_only[-4:]
    return f"{prefix}******{last4}"


def mask_vpa(vpa: str | None) -> str | None:
    """Mask a UPI VPA (e.g. 'user@okhdfcbank' -> 'u***r@okhdfcbank')."""
    if not vpa or not isinstance(vpa, str) or "@" not in vpa:
        return vpa
    return mask_email(vpa)


def sanitize_dict_recursively(obj: Any) -> Any:
    """Recursively redact sensitive keys and sanitize values in arbitrary structures."""
    if isinstance(obj, dict):
        sanitized = {}
        for key, val in obj.items():
            key_lower = str(key).lower()
            # Redact forbidden keys
            if any(forbidden in key_lower for forbidden in FORBIDDEN_KEY_PATTERNS):
                sanitized[key] = "[REDACTED]"
            elif key_lower in {"email", "customer_email"}:
                sanitized[key] = mask_email(val) if isinstance(val, str) else val
            elif key_lower in {"contact", "phone", "customer_phone"}:
                sanitized[key] = mask_phone(val) if isinstance(val, str) else val
            elif key_lower == "vpa":
                sanitized[key] = mask_vpa(val) if isinstance(val, str) else val
            else:
                sanitized[key] = sanitize_dict_recursively(val)
        return sanitized
    elif isinstance(obj, list):
        return [sanitize_dict_recursively(item) for item in obj]
    else:
        return obj


def sanitize_razorpay_payload(payload: dict[str, Any]) -> dict[str, Any]:
    """
    Deterministically sanitize a parsed Razorpay webhook payload for storage.

    - Preserves all event, payment, subscription, error, and order references.
    - Masks customer email and phone numbers.
    - Redacts cardholder name to initial/masked format if present.
    - Redacts any sensitive authentication tokens or secrets if present.
    """
    if not isinstance(payload, dict):
        return payload

    sanitized = copy.deepcopy(payload)
    sanitized = sanitize_dict_recursively(sanitized)

    # Specific check for payment entity cardholder name
    payment_entity = (
        sanitized.get("payload", {}).get("payment", {}).get("entity", {})
    )
    if isinstance(payment_entity, dict):
        card = payment_entity.get("card")
        if isinstance(card, dict) and "name" in card and card["name"]:
            name_val = str(card["name"]).strip()
            if len(name_val) > 2:
                card["name"] = name_val[0] + "***" + name_val[-1]
            else:
                card["name"] = "***"

    return sanitized
