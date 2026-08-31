import logging
import re
import uuid
from typing import Any

from fastapi import HTTPException, Request, status

from app.core.config import get_settings

logger = logging.getLogger(__name__)

# Common SQL injection patterns
SQLI_PATTERNS = [
    re.compile(r"(\b(UNION(\s+ALL)?)\b\s+SELECT)", re.IGNORECASE),
    re.compile(r"(\bOR\b\s+['\"]?1['\"]?\s*=\s*['\"]?1)", re.IGNORECASE),
    re.compile(r"(;\s*DROP\s+TABLE)", re.IGNORECASE),
    re.compile(r"(--\s*$|/\*.*?\*/)", re.IGNORECASE),
    re.compile(r"(\bEXEC(\s+sp_|\s+xp_))", re.IGNORECASE),
]

# NoSQL injection patterns
NOSQLI_PATTERNS = [
    re.compile(r"(\$where|\$gt|\$ne|\$regex|\$in)", re.IGNORECASE),
]

# Path traversal patterns
PATH_TRAVERSAL_PATTERN = re.compile(r"(\.\./|\.\.\\)", re.IGNORECASE)


def validate_uuid_param(val: str, param_name: str = "id") -> uuid.UUID:
    """Validate that a route or query parameter is a valid RFC 4122 UUID."""
    if not val:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Parameter '{param_name}' cannot be empty.",
        )
    try:
        return uuid.UUID(str(val).strip())
    except (ValueError, TypeError, AttributeError) as exc:
        logger.warning(
            "invalid_uuid_parameter", extra={"param": param_name, "value": val}
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Parameter '{param_name}' must be a valid UUID.",
        ) from exc


def contains_injection_patterns(text: str) -> tuple[bool, str]:
    """
    Check if an input string contains dangerous SQL, NoSQL, or Path Traversal injection patterns.
    Returns (is_malicious, detected_pattern_description).
    """
    if not text or not isinstance(text, str):
        return False, ""

    for pat in SQLI_PATTERNS:
        if pat.search(text):
            return True, f"SQL Injection pattern: {pat.pattern}"

    for pat in NOSQLI_PATTERNS:
        if pat.search(text):
            return True, f"NoSQL Injection pattern: {pat.pattern}"

    if PATH_TRAVERSAL_PATTERN.search(text):
        return True, "Path traversal sequence"

    return False, ""


def inspect_payload_for_injections(obj: Any) -> tuple[bool, str]:
    """Recursively inspect an arbitrary dictionary or list for injection attempts."""
    if isinstance(obj, str):
        return contains_injection_patterns(obj)
    elif isinstance(obj, dict):
        for k, v in obj.items():
            malicious_k, desc_k = contains_injection_patterns(str(k))
            if malicious_k:
                return True, f"Key injection: {desc_k}"
            malicious_v, desc_v = inspect_payload_for_injections(v)
            if malicious_v:
                return True, desc_v
    elif isinstance(obj, list):
        for item in obj:
            malicious, desc = inspect_payload_for_injections(item)
            if malicious:
                return True, desc
    return False, ""


async def verify_request_body_size(request: Request) -> None:
    """Enforce maximum allowable request payload size to prevent resource exhaustion / DoS."""
    settings = get_settings()
    content_length = request.headers.get("Content-Length")
    if content_length:
        try:
            length = int(content_length)
            if length > settings.max_request_body_bytes:
                logger.warning(
                    "request_body_too_large",
                    extra={"length": length, "limit": settings.max_request_body_bytes},
                )
                raise HTTPException(
                    status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                    detail=f"Request body size ({length} bytes) exceeds maximum limit of {settings.max_request_body_bytes} bytes.",
                )
        except ValueError:
            pass
