import hashlib
import hmac
import json
import logging
import time
from typing import Any

from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.core.database import get_db
from app.core.rate_limiter import rate_limit_webhooks
from app.models.enums import SecurityEventType, SecurityThreatSeverity
from app.services.payment_event_service import payment_event_service
from app.services.security_threat_service import SecurityThreatService
from app.webhooks.sanitizer import sanitize_razorpay_payload

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/webhooks", tags=["webhooks"])


def verify_razorpay_signature(
    raw_body: bytes,
    signature: str,
    secret: str,
) -> bool:
    """
    Verify the HMAC-SHA256 signature over raw request bytes.

    Uses constant-time comparison (hmac.compare_digest) to prevent timing attacks.
    """
    if not signature or not secret:
        return False

    computed = hmac.new(
        key=secret.encode("utf-8"),
        msg=raw_body,
        digestmod=hashlib.sha256,
    ).hexdigest()

    return hmac.compare_digest(computed, signature)


@router.post(
    "/razorpay",
    status_code=status.HTTP_200_OK,
    summary="Ingest Razorpay webhook events",
    dependencies=[Depends(rate_limit_webhooks)],
)
async def handle_razorpay_webhook(
    request: Request,
    x_razorpay_signature: str | None = Header(
        default=None,
        alias="X-Razorpay-Signature",
    ),
    x_razorpay_event_id: str | None = Header(
        default=None,
        alias="X-Razorpay-Event-Id",
    ),
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> dict[str, Any]:
    """
    Receive, authenticate, sanitize, deduplicate, and persist Razorpay webhooks.

    Lifecycle:
    1. Rate limit check (120 req/min per IP).
    2. Validate required headers (X-Razorpay-Signature, X-Razorpay-Event-Id).
    3. Extract exact raw request body bytes.
    4. Verify HMAC-SHA256 signature against raw bytes in constant time.
    5. Parse raw bytes as JSON and verify timestamp age (Replay protection).
    6. Deterministically sanitize payload (mask PII, redact forbidden secrets).
    7. Persist event to database with unique idempotency constraints.
    8. Return HTTP 200 immediately (< 5.0s acknowledgment requirement).
    """
    security_service = SecurityThreatService(db=db)
    client_ip = request.client.host if request.client else "127.0.0.1"

    # 1. Header Presence Validation
    if not x_razorpay_signature:
        logger.warning("missing_header: X-Razorpay-Signature")
        security_service.record_security_event(
            event_type=SecurityEventType.WEBHOOK_SIGNATURE_FAILED,
            severity=SecurityThreatSeverity.MEDIUM,
            actor_id="anonymous_webhook_sender",
            ip_address=client_ip,
            details={"reason": "Missing X-Razorpay-Signature header"},
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing X-Razorpay-Signature header",
        )

    if not x_razorpay_event_id:
        logger.warning("missing_header: X-Razorpay-Event-Id")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing X-Razorpay-Event-Id header",
        )

    # 2. Extract Raw Request Body Bytes
    raw_body = await request.body()

    logger.info(
        "webhook_received",
        extra={
            "event_id": x_razorpay_event_id,
            "body_size_bytes": len(raw_body),
        },
    )

    # 3. Cryptographic Signature Verification on RAW Bytes
    webhook_secret = settings.razorpay_webhook_secret
    if not webhook_secret:
        logger.error("webhook_secret_not_configured")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Webhook secret not configured on server",
        )

    is_valid = verify_razorpay_signature(
        raw_body=raw_body,
        signature=x_razorpay_signature,
        secret=webhook_secret,
    )
    if not is_valid:
        logger.warning(
            "invalid_signature",
            extra={"event_id": x_razorpay_event_id},
        )
        security_service.record_security_event(
            event_type=SecurityEventType.WEBHOOK_SIGNATURE_FAILED,
            severity=SecurityThreatSeverity.HIGH,
            actor_id="unauthorized_webhook_sender",
            ip_address=client_ip,
            details={
                "event_id": x_razorpay_event_id,
                "signature": x_razorpay_signature[:10] + "...",
            },
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid webhook signature",
        )

    logger.info(
        "signature_verified",
        extra={"event_id": x_razorpay_event_id},
    )

    # 4. JSON Payload Parsing & Replay Protection
    try:
        parsed_payload = json.loads(raw_body)
        if not isinstance(parsed_payload, dict):
            raise ValueError("Payload must be a JSON object")
    except Exception as exc:
        logger.warning(
            "malformed_json_payload",
            extra={"event_id": x_razorpay_event_id, "error": str(exc)},
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Malformed JSON payload",
        ) from exc

    # Replay Protection: Check created_at timestamp if present
    created_at_ts = parsed_payload.get("created_at")
    if created_at_ts is not None and isinstance(created_at_ts, (int, float)):
        now_epoch = time.time()
        tolerance = settings.webhook_timestamp_tolerance_seconds
        # If timestamp is more than tolerance seconds in the past
        if (now_epoch - created_at_ts) > tolerance and tolerance > 0:
            logger.warning(
                "webhook_replay_detected",
                extra={
                    "event_id": x_razorpay_event_id,
                    "age_seconds": now_epoch - created_at_ts,
                },
            )
            security_service.record_security_event(
                event_type=SecurityEventType.WEBHOOK_REPLAY_DETECTED,
                severity=SecurityThreatSeverity.HIGH,
                actor_id="replay_attacker",
                ip_address=client_ip,
                details={
                    "event_id": x_razorpay_event_id,
                    "event_created_at": created_at_ts,
                    "age_seconds": round(now_epoch - created_at_ts, 1),
                    "tolerance": tolerance,
                },
            )
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Webhook event timestamp exceeds tolerance window of {tolerance}s (potential replay attack).",
            )

    event_type = parsed_payload.get("event", "unknown")

    # 5. Deterministic Payload Sanitization (Post-Signature Verification)
    sanitized_payload = sanitize_razorpay_payload(parsed_payload)

    # 6. Persist Event with Idempotency Guarantee
    try:
        result = payment_event_service.ingest_event(
            db=db,
            event_id=x_razorpay_event_id,
            event_type=event_type,
            payload=sanitized_payload,
        )
    except Exception as exc:
        logger.error(
            "webhook_ingestion_failure",
            extra={"event_id": x_razorpay_event_id, "error": str(exc)},
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to persist webhook event",
        ) from exc

    return {
        "status": "ok",
        "event_id": result.event_id,
        "is_duplicate": result.is_duplicate,
    }
