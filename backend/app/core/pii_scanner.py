import copy
import re
from typing import Any

# Regex patterns for sensitive fintech PII and credentials
AADHAAR_PATTERN = re.compile(r"\b[2-9]\d{3}[\s-]?[0-9]{4}[\s-]?[0-9]{4}\b")
CARD_CANDIDATE_PATTERN = re.compile(r"\b(?:\d[ -]*?){13,19}\b")
EMAIL_PATTERN = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b")
PHONE_INDIAN_PATTERN = re.compile(r"(?:\+91|91)?[\s-]?[6-9]\d{9}\b")
CVV_KEY_PATTERN = re.compile(r"\b(cvv|cvc|security_code|cid)\b", re.IGNORECASE)
SECRET_PATTERNS = [
    re.compile(r"-----BEGIN[ A-Z0-9_-]+PRIVATE KEY-----", re.IGNORECASE),
    re.compile(r"\b(rzp_(?:live|test)_[a-zA-Z0-9]{14,32})\b"),
    re.compile(
        r"\b(ey[a-zA-Z0-9_-]{10,}\.ey[a-zA-Z0-9_-]{10,}\.[a-zA-Z0-9_-]{10,})\b"
    ),  # JWT
]

FORBIDDEN_KEYS = {
    "password",
    "secret",
    "api_key",
    "webhook_secret",
    "jwt_secret",
    "private_key",
    "access_token",
    "auth_token",
    "bearer",
    "cvv",
    "cvc",
    "pin",
    "card_number",
    "pan",
}


def is_luhn_valid(card_str: str) -> bool:
    """Verify if a string of digits passes the Luhn checksum algorithm."""
    digits = [int(c) for c in card_str if c.isdigit()]
    if len(digits) < 13 or len(digits) > 19:
        return False
    checksum = 0
    reverse_digits = digits[::-1]
    for i, d in enumerate(reverse_digits):
        if i % 2 == 1:
            doubled = d * 2
            checksum += doubled - 9 if doubled > 9 else doubled
        else:
            checksum += d
    return checksum % 10 == 0


def mask_email(email: str | None) -> str:
    """Mask an email address (e.g. 'alice.smith@example.com' -> 'a***h@example.com')."""
    if not email or "@" not in email:
        return email or ""
    parts = email.split("@", 1)
    username, domain = parts[0], parts[1]
    if len(username) <= 2:
        masked_user = username[0] + "***"
    else:
        masked_user = username[0] + "***" + username[-1]
    return f"{masked_user}@{domain}"


def mask_phone(phone: str | None) -> str:
    """Mask a phone number (e.g. '+919876543210' -> '+91******3210')."""
    if not phone:
        return ""
    digits = re.sub(r"\D", "", phone)
    if len(digits) <= 4:
        return "****"
    last4 = digits[-4:]
    prefix = (
        "+91" if phone.startswith("+91") else ("+" if phone.startswith("+") else "")
    )
    return f"{prefix}******{last4}"


def mask_card_number(card: str | None) -> str:
    """Mask a credit card PAN showing only first 2 and last 4 digits."""
    if not card:
        return ""
    digits = re.sub(r"\D", "", card)
    if len(digits) < 13:
        return "[REDACTED_CARD]"
    return f"{digits[:2]}******{digits[-4:]}"


def mask_aadhaar(aadhaar: str | None) -> str:
    """Mask an Indian Aadhaar number (e.g. '9876 5432 1098' -> 'XXXX-XXXX-1098')."""
    if not aadhaar:
        return ""
    digits = re.sub(r"\D", "", aadhaar)
    if len(digits) != 12:
        return "[REDACTED_ID]"
    return f"XXXX-XXXX-{digits[-4:]}"


def scan_for_pii_and_secrets(payload: Any) -> dict[str, Any]:
    """
    Deep-scans a payload (dict, list, or string) and returns detailed forensic findings.

    Returns:
        {
            "has_pii": bool,
            "has_secrets": bool,
            "findings_count": int,
            "findings": list[dict[str, Any]],
            "sanitized_payload": Any,
        }
    """
    findings: list[dict[str, Any]] = []

    def _scan_and_redact(node: Any, current_path: str = "$") -> Any:
        if isinstance(node, dict):
            clean_dict = {}
            for k, v in node.items():
                k_lower = str(k).lower()
                child_path = f"{current_path}.{k}"

                # Check forbidden keys
                if any(forbidden in k_lower for forbidden in FORBIDDEN_KEYS):
                    findings.append(
                        {
                            "type": "FORBIDDEN_SECRET_KEY",
                            "path": child_path,
                            "description": f"Key name '{k}' matches sensitive credential pattern.",
                        }
                    )
                    clean_dict[k] = "[REDACTED_SECRET]"
                elif k_lower in {"email", "customer_email"}:
                    if isinstance(v, str) and "@" in v:
                        clean_dict[k] = mask_email(v)
                    else:
                        clean_dict[k] = v
                elif k_lower in {"phone", "contact", "customer_phone"}:
                    if isinstance(v, str):
                        clean_dict[k] = mask_phone(v)
                    else:
                        clean_dict[k] = v
                else:
                    clean_dict[k] = _scan_and_redact(v, child_path)
            return clean_dict

        elif isinstance(node, list):
            return [
                _scan_and_redact(item, f"{current_path}[{i}]")
                for i, item in enumerate(node)
            ]

        elif isinstance(node, str):
            clean_str = node

            # Check Secret patterns (Private keys, Razorpay secrets, JWT tokens)
            for pat in SECRET_PATTERNS:
                if pat.search(clean_str):
                    findings.append(
                        {
                            "type": "EXPOSED_SECRET_TOKEN",
                            "path": current_path,
                            "description": "Exposed cryptographic secret, API key, or JWT string.",
                        }
                    )
                    clean_str = pat.sub("[REDACTED_TOKEN]", clean_str)

            # Check Card PAN candidates
            for match in CARD_CANDIDATE_PATTERN.finditer(clean_str):
                cand = match.group(0)
                clean_cand = re.sub(r"\D", "", cand)
                if is_luhn_valid(clean_cand):
                    findings.append(
                        {
                            "type": "UNMASKED_CARD_PAN",
                            "path": current_path,
                            "description": "Luhn-valid Credit/Debit card PAN detected.",
                        }
                    )
                    clean_str = clean_str.replace(cand, mask_card_number(clean_cand))

            # Check Aadhaar numbers
            for match in AADHAAR_PATTERN.finditer(clean_str):
                cand = match.group(0)
                findings.append(
                    {
                        "type": "UNMASKED_AADHAAR",
                        "path": current_path,
                        "description": "Indian National Identity (Aadhaar) number detected.",
                    }
                )
                clean_str = clean_str.replace(cand, mask_aadhaar(cand))

            return clean_str

        return node

    sanitized = _scan_and_redact(copy.deepcopy(payload))

    has_pii = any(
        f["type"] in {"UNMASKED_CARD_PAN", "UNMASKED_AADHAAR"} for f in findings
    )
    has_secrets = any(
        f["type"] in {"FORBIDDEN_SECRET_KEY", "EXPOSED_SECRET_TOKEN"} for f in findings
    )

    return {
        "has_pii": has_pii,
        "has_secrets": has_secrets,
        "findings_count": len(findings),
        "findings": findings,
        "sanitized_payload": sanitized,
    }
