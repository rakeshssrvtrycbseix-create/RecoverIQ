import hashlib
import hmac
import json
import logging
from typing import Any

from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.core.database import get_db
from app.services.payment_event_service import payment_event_service

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
    Receive, authenticate, deduplicate, and persist incoming Razorpay webhook events.

    1. Validates presence of X-Razorpay-Signature and X-Razorpay-Event-Id headers.
    2. Cryptographically validates signature over the raw unparsed request body.
    3. Persists the event with database-level idempotency to prevent duplicate handling.
    4. Returns HTTP 200 immediately for fast acknowledgment (< 5.0s requirement).
    """
    # 1. Header Presence Validation
    if not x_razorpay_signature:
        logger.warning("missing_header: X-Razorpay-Signature")
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

    # 2. Extract Raw Request Body Bytes (Prior to JSON Parsing)
    raw_body = await request.body()

    logger.info(
        "webhook_received",
        extra={
            "event_id": x_razorpay_event_id,
            "body_size_bytes": len(raw_body),
        },
    )

    # 3. Cryptographic Signature Verification
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
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid webhook signature",
        )

    logger.info(
        "signature_verified",
        extra={"event_id": x_razorpay_event_id},
    )

    # 4. JSON Payload Parsing
    try:
        payload = json.loads(raw_body)
        if not isinstance(payload, dict):
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

    event_type = payload.get("event", "unknown")

    # 5. Persist Event with Idempotency Guarantee
    result = payment_event_service.ingest_event(
        db=db,
        event_id=x_razorpay_event_id,
        event_type=event_type,
        payload=payload,
    )

    return {
        "status": "ok",
        "event_id": result.event_id,
        "is_duplicate": result.is_duplicate,
    }
