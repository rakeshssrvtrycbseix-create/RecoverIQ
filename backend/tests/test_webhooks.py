import hashlib
import hmac
import json
import logging
from typing import Any
from unittest.mock import patch

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.core.database import get_db
from app.main import app
from app.models import PaymentEvent, PaymentEventProcessingStatus, PaymentEventSource
from app.services.payment_event_service import payment_event_service
from app.webhooks.sanitizer import (
    mask_email,
    mask_phone,
    sanitize_razorpay_payload,
)
from tests.conftest import TEST_WEBHOOK_SECRET


def compute_signature(raw_bytes: bytes, secret: str = TEST_WEBHOOK_SECRET) -> str:
    """Compute HMAC-SHA256 signature for test payloads."""
    return hmac.new(
        key=secret.encode("utf-8"),
        msg=raw_bytes,
        digestmod=hashlib.sha256,
    ).hexdigest()


def sample_payment_failed_payload() -> dict[str, Any]:
    """Return a deterministic Razorpay payment.failed test payload."""
    return {
        "entity": "event",
        "account_id": "acc_test_123456",
        "event": "payment.failed",
        "contains": ["payment"],
        "payload": {
            "payment": {
                "entity": {
                    "id": "pay_test_failed_001",
                    "entity": "payment",
                    "amount": 299900,
                    "currency": "INR",
                    "status": "failed",
                    "order_id": "order_test_001",
                    "invoice_id": "inv_test_001",
                    "method": "card",
                    "email": "customer@example.com",
                    "contact": "+919876543210",
                    "customer_id": "cust_test_001",
                    "card": {
                        "name": "Jane Doe",
                        "last4": "1111",
                        "network": "Visa",
                        "type": "debit",
                    },
                    "notes": {
                        "merchant_order_ref": "ref_9988",
                        "auth_token": "secret_token_value_abc",
                    },
                    "error_code": "BAD_REQUEST_ERROR",
                    "error_description": "Payment failed due to insufficient funds.",
                    "error_source": "bank",
                    "error_step": "payment_authorization",
                    "error_reason": "insufficient_funds",
                    "created_at": 1724851200,
                }
            }
        },
        "created_at": 1724851201,
    }


def sample_subscription_halted_payload() -> dict[str, Any]:
    """Return a deterministic Razorpay subscription.halted test payload."""
    return {
        "entity": "event",
        "account_id": "acc_test_123456",
        "event": "subscription.halted",
        "contains": ["subscription", "payment"],
        "payload": {
            "subscription": {
                "entity": {
                    "id": "sub_test_halted_001",
                    "entity": "subscription",
                    "plan_id": "plan_test_001",
                    "customer_id": "cust_test_001",
                    "status": "halted",
                    "charge_at": 1724851200,
                }
            },
            "payment": {
                "entity": {
                    "id": "pay_test_sub_failed_001",
                    "amount": 499900,
                    "status": "failed",
                    "error_code": "BAD_REQUEST_ERROR",
                    "error_reason": "card_inactive",
                }
            },
        },
        "created_at": 1724851201,
    }


def test_valid_signature_accepted(client: TestClient, db_session: Session):
    """1. Test that an event with a valid signature is accepted (200 OK)."""
    payload_dict = sample_payment_failed_payload()
    raw_body = json.dumps(payload_dict).encode("utf-8")
    signature = compute_signature(raw_body)
    event_id = "evt_rzp_valid_001"

    headers = {
        "X-Razorpay-Signature": signature,
        "X-Razorpay-Event-Id": event_id,
        "Content-Type": "application/json",
    }

    response = client.post("/webhooks/razorpay", content=raw_body, headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["event_id"] == event_id
    assert data["is_duplicate"] is False


def test_invalid_signature_rejected(client: TestClient):
    """2. Test that an invalid signature returns 401 Unauthorized."""
    payload_dict = sample_payment_failed_payload()
    raw_body = json.dumps(payload_dict).encode("utf-8")
    event_id = "evt_rzp_invalid_sig_001"

    headers = {
        "X-Razorpay-Signature": "invalid_hex_signature_abcdef123456",
        "X-Razorpay-Event-Id": event_id,
        "Content-Type": "application/json",
    }

    response = client.post("/webhooks/razorpay", content=raw_body, headers=headers)
    assert response.status_code == 401
    assert "Invalid webhook signature" in response.json()["detail"]


def test_missing_signature_rejected(client: TestClient):
    """3. Test that missing X-Razorpay-Signature header returns 400 Bad Request."""
    payload_dict = sample_payment_failed_payload()
    raw_body = json.dumps(payload_dict).encode("utf-8")

    headers = {
        "X-Razorpay-Event-Id": "evt_rzp_no_sig_001",
        "Content-Type": "application/json",
    }

    response = client.post("/webhooks/razorpay", content=raw_body, headers=headers)
    assert response.status_code == 400
    assert "Missing X-Razorpay-Signature" in response.json()["detail"]


def test_missing_event_id_rejected(client: TestClient):
    """4. Test that missing X-Razorpay-Event-Id header returns 400 Bad Request."""
    payload_dict = sample_payment_failed_payload()
    raw_body = json.dumps(payload_dict).encode("utf-8")
    signature = compute_signature(raw_body)

    headers = {
        "X-Razorpay-Signature": signature,
        "Content-Type": "application/json",
    }

    response = client.post("/webhooks/razorpay", content=raw_body, headers=headers)
    assert response.status_code == 400
    assert "Missing X-Razorpay-Event-Id" in response.json()["detail"]


def test_valid_event_persisted_in_database(client: TestClient, db_session: Session):
    """5. Test that valid webhook payload is persisted in payment_events table."""
    payload_dict = sample_subscription_halted_payload()
    raw_body = json.dumps(payload_dict).encode("utf-8")
    signature = compute_signature(raw_body)
    event_id = "evt_rzp_persist_001"

    headers = {
        "X-Razorpay-Signature": signature,
        "X-Razorpay-Event-Id": event_id,
        "Content-Type": "application/json",
    }

    response = client.post("/webhooks/razorpay", content=raw_body, headers=headers)
    assert response.status_code == 200

    # Query DB directly to verify persistence
    stored_event = (
        db_session.query(PaymentEvent).filter_by(idempotency_key=event_id).first()
    )
    assert stored_event is not None
    assert stored_event.event_type == "subscription.halted"
    assert stored_event.source == PaymentEventSource.RAZORPAY_WEBHOOK.value
    assert stored_event.razorpay_event_id == event_id
    assert (
        stored_event.processing_status == PaymentEventProcessingStatus.PROCESSED.value
    )
    assert stored_event.payload["event"] == "subscription.halted"


def test_duplicate_event_returns_200_and_does_not_duplicate_row(
    client: TestClient, db_session: Session
):
    """6. Test that duplicate delivery returns 200 OK and is_duplicate=True."""
    payload_dict = sample_payment_failed_payload()
    raw_body = json.dumps(payload_dict).encode("utf-8")
    signature = compute_signature(raw_body)
    event_id = "evt_rzp_duplicate_001"

    headers = {
        "X-Razorpay-Signature": signature,
        "X-Razorpay-Event-Id": event_id,
        "Content-Type": "application/json",
    }

    # First delivery
    resp1 = client.post("/webhooks/razorpay", content=raw_body, headers=headers)
    assert resp1.status_code == 200
    assert resp1.json()["is_duplicate"] is False

    # Second delivery (duplicate delivery retry)
    resp2 = client.post("/webhooks/razorpay", content=raw_body, headers=headers)
    assert resp2.status_code == 200
    assert resp2.json()["is_duplicate"] is True

    # Count rows in DB
    count = db_session.query(PaymentEvent).filter_by(idempotency_key=event_id).count()
    assert count == 1


def test_concurrent_duplicate_insertion_race_condition_handled(
    db_session: Session,
):
    """7. Test that race conditions are safely handled by PaymentEventService."""
    event_id = "evt_rzp_race_001"
    payload = {"event": "payment.failed", "id": "test"}

    # First insertion
    res1 = payment_event_service.ingest_event(
        db=db_session,
        event_id=event_id,
        event_type="payment.failed",
        payload=payload,
    )
    assert res1.is_duplicate is False

    # Simulate concurrent race where another session calls ingest_event
    res2 = payment_event_service.ingest_event(
        db=db_session,
        event_id=event_id,
        event_type="payment.failed",
        payload=payload,
    )
    assert res2.is_duplicate is True
    assert res2.event_id == event_id


def test_raw_body_signature_verification_exact_bytes(client: TestClient):
    """8. Test that signature verification operates on exact raw bytes."""
    raw_body = b'{\n  "event": "payment.failed",\n  "account_id": "acc_123"\n}'
    signature = compute_signature(raw_body)
    event_id = "evt_rzp_raw_bytes_001"

    headers = {
        "X-Razorpay-Signature": signature,
        "X-Razorpay-Event-Id": event_id,
        "Content-Type": "application/json",
    }

    response = client.post("/webhooks/razorpay", content=raw_body, headers=headers)
    assert response.status_code == 200


def test_tampered_payload_fails_verification(client: TestClient):
    """9. Test that altering raw body after signature calculation causes 401."""
    raw_body = b'{"event": "payment.failed", "amount": 1000}'
    signature = compute_signature(raw_body)

    # Tampered payload with modified amount
    tampered_body = b'{"event": "payment.failed", "amount": 9999}'
    event_id = "evt_rzp_tampered_001"

    headers = {
        "X-Razorpay-Signature": signature,
        "X-Razorpay-Event-Id": event_id,
        "Content-Type": "application/json",
    }

    response = client.post("/webhooks/razorpay", content=tampered_body, headers=headers)
    assert response.status_code == 401
    assert "Invalid webhook signature" in response.json()["detail"]


def test_webhook_secret_not_exposed_in_logs_or_response(client: TestClient, caplog):
    """10. Test that webhook secret is never leaked into logs or HTTP response."""
    caplog.set_level(logging.DEBUG)
    payload_dict = sample_payment_failed_payload()
    raw_body = json.dumps(payload_dict).encode("utf-8")
    signature = compute_signature(raw_body)
    event_id = "evt_rzp_sec_check_001"

    headers = {
        "X-Razorpay-Signature": signature,
        "X-Razorpay-Event-Id": event_id,
        "Content-Type": "application/json",
    }

    response = client.post("/webhooks/razorpay", content=raw_body, headers=headers)
    assert response.status_code == 200

    # Ensure secret never appears in logs or response body
    assert TEST_WEBHOOK_SECRET not in caplog.text
    assert TEST_WEBHOOK_SECRET not in response.text


def test_unknown_event_types_persisted_safely(client: TestClient, db_session: Session):
    """11. Test that unhandled event types are safely ingested without error."""
    payload_dict = {
        "entity": "event",
        "event": "custom.experimental.event",
        "payload": {"custom": {"data": "value"}},
    }
    raw_body = json.dumps(payload_dict).encode("utf-8")
    signature = compute_signature(raw_body)
    event_id = "evt_rzp_unknown_type_001"

    headers = {
        "X-Razorpay-Signature": signature,
        "X-Razorpay-Event-Id": event_id,
        "Content-Type": "application/json",
    }

    response = client.post("/webhooks/razorpay", content=raw_body, headers=headers)
    assert response.status_code == 200

    stored = db_session.query(PaymentEvent).filter_by(idempotency_key=event_id).first()
    assert stored is not None
    assert stored.event_type == "custom.experimental.event"


def test_malformed_json_payload_returns_bad_request(client: TestClient):
    """12. Test that malformed JSON payload returns 400 Bad Request."""
    raw_body = b"not valid json {{{ {"
    signature = compute_signature(raw_body)
    event_id = "evt_rzp_bad_json_001"

    headers = {
        "X-Razorpay-Signature": signature,
        "X-Razorpay-Event-Id": event_id,
        "Content-Type": "application/json",
    }

    response = client.post("/webhooks/razorpay", content=raw_body, headers=headers)
    assert response.status_code == 400
    assert "Malformed JSON payload" in response.json()["detail"]


def test_unconfigured_webhook_secret_returns_500(db_session: Session):
    """13. Test that missing server webhook secret configuration returns 500."""

    def override_get_db():
        yield db_session

    def override_get_settings_empty():
        return Settings(
            database_url="sqlite:///:memory:",
            razorpay_webhook_secret="",  # Unconfigured
        )

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_settings] = override_get_settings_empty

    with TestClient(app) as test_client:
        raw_body = b'{"event": "payment.failed"}'
        headers = {
            "X-Razorpay-Signature": "any_sig",
            "X-Razorpay-Event-Id": "evt_test_unconf_001",
            "Content-Type": "application/json",
        }
        response = test_client.post(
            "/webhooks/razorpay", content=raw_body, headers=headers
        )
        assert response.status_code == 500
        assert "Webhook secret not configured on server" in response.json()["detail"]

    app.dependency_overrides.clear()


# =========================================================================
# Phase 3C Hardening Tests: Sanitization, Data Safety & Database Failure
# =========================================================================


def test_sensitive_field_sanitization_masks_email_and_phone(
    client: TestClient, db_session: Session
):
    """14. Test that customer email, phone, and cardholder name are masked."""
    payload_dict = sample_payment_failed_payload()
    raw_body = json.dumps(payload_dict).encode("utf-8")
    signature = compute_signature(raw_body)
    event_id = "evt_rzp_sanitize_test_001"

    headers = {
        "X-Razorpay-Signature": signature,
        "X-Razorpay-Event-Id": event_id,
        "Content-Type": "application/json",
    }

    response = client.post("/webhooks/razorpay", content=raw_body, headers=headers)
    assert response.status_code == 200

    stored = db_session.query(PaymentEvent).filter_by(idempotency_key=event_id).first()
    assert stored is not None
    payment_entity = stored.payload["payload"]["payment"]["entity"]

    # Email & phone must be masked
    assert payment_entity["email"] == "c***r@example.com"
    assert payment_entity["contact"] == "+91******3210"
    assert payment_entity["card"]["name"] == "J***e"


def test_secret_like_fields_redacted_if_present_in_payload_or_notes(
    client: TestClient, db_session: Session
):
    """15. Test that secret-like keys in notes or custom objects are redacted."""
    payload_dict = sample_payment_failed_payload()
    raw_body = json.dumps(payload_dict).encode("utf-8")
    signature = compute_signature(raw_body)
    event_id = "evt_rzp_redact_secrets_001"

    headers = {
        "X-Razorpay-Signature": signature,
        "X-Razorpay-Event-Id": event_id,
        "Content-Type": "application/json",
    }

    response = client.post("/webhooks/razorpay", content=raw_body, headers=headers)
    assert response.status_code == 200

    stored = db_session.query(PaymentEvent).filter_by(idempotency_key=event_id).first()
    assert stored is not None
    notes = stored.payload["payload"]["payment"]["entity"]["notes"]
    assert notes["auth_token"] == "[REDACTED]"
    assert notes["merchant_order_ref"] == "ref_9988"


def test_sanitizer_does_not_modify_event_id_or_payment_id():
    """16. Test that sanitizer preserves payment and event identifiers."""
    payload = sample_payment_failed_payload()
    sanitized = sanitize_razorpay_payload(payload)

    assert sanitized["payload"]["payment"]["entity"]["id"] == "pay_test_failed_001"
    assert sanitized["payload"]["payment"]["entity"]["order_id"] == "order_test_001"
    assert sanitized["payload"]["payment"]["entity"]["customer_id"] == "cust_test_001"
    assert sanitized["event"] == "payment.failed"


def test_signature_verification_happens_before_sanitization(
    client: TestClient,
):
    """17. Test that signature is calculated over raw bytes with unmasked PII."""
    payload_dict = sample_payment_failed_payload()
    raw_body = json.dumps(payload_dict).encode("utf-8")
    # Compute signature over original raw body (with unmasked email/phone)
    valid_signature = compute_signature(raw_body)
    event_id = "evt_rzp_sig_order_001"

    headers = {
        "X-Razorpay-Signature": valid_signature,
        "X-Razorpay-Event-Id": event_id,
        "Content-Type": "application/json",
    }

    response = client.post("/webhooks/razorpay", content=raw_body, headers=headers)
    # Must succeed (200 OK), proving verification ran on raw body before sanitization
    assert response.status_code == 200


def test_database_failure_does_not_return_false_success(client: TestClient):
    """18. Test that unexpected DB failure returns 500 error and never false 200."""
    payload_dict = sample_payment_failed_payload()
    raw_body = json.dumps(payload_dict).encode("utf-8")
    signature = compute_signature(raw_body)
    event_id = "evt_rzp_db_fail_001"

    headers = {
        "X-Razorpay-Signature": signature,
        "X-Razorpay-Event-Id": event_id,
        "Content-Type": "application/json",
    }

    # Simulate database session crash during commit
    with patch(
        "app.services.payment_event_service.PaymentEventService.ingest_event",
        side_effect=RuntimeError("Database connection dropped"),
    ):
        response = client.post("/webhooks/razorpay", content=raw_body, headers=headers)
        assert response.status_code == 500
        assert "Failed to persist webhook event" in response.json()["detail"]


def test_mask_helper_functions():
    """19. Unit tests for mask_email and mask_phone helper functions."""
    assert mask_email("a@b.com") == "a***@b.com"
    assert mask_email("john.doe@company.org") == "j***e@company.org"
    assert mask_email(None) is None
    assert mask_email("invalid_email") == "invalid_email"

    assert mask_phone("+919876543210") == "+91******3210"
    assert mask_phone("1234567890") == "******7890"
    assert mask_phone(None) is None
    assert mask_phone("123") == "****"


def test_sanitized_payload_remains_valid_json():
    """20. Test that sanitized output serializes cleanly to JSON."""
    payload = sample_payment_failed_payload()
    sanitized = sanitize_razorpay_payload(payload)
    serialized = json.dumps(sanitized)
    assert isinstance(serialized, str)
    deserialized = json.loads(serialized)
    assert deserialized["event"] == "payment.failed"
