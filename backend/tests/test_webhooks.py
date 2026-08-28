import hashlib
import hmac
import json
import logging
from typing import Any

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.core.database import get_db
from app.main import app
from app.models import PaymentEvent, PaymentEventProcessingStatus, PaymentEventSource
from app.services.payment_event_service import payment_event_service
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


def test_valid_event_persisted_in_database(
    client: TestClient, db_session: Session
):
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
        stored_event.processing_status
        == PaymentEventProcessingStatus.RECEIVED.value
    )
    assert stored_event.payload["event"] == "subscription.halted"


def test_duplicate_event_returns_200_and_does_not_duplicate_row(
    client: TestClient, db_session: Session
):
    """6. Test that duplicate webhook delivery returns 200 OK and is_duplicate=True."""
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
    count = (
        db_session.query(PaymentEvent).filter_by(idempotency_key=event_id).count()
    )
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
    # Payload with specific whitespace formatting
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
        "X-Razorpay-Signature": signature,  # Signed for original amount
        "X-Razorpay-Event-Id": event_id,
        "Content-Type": "application/json",
    }

    response = client.post(
        "/webhooks/razorpay", content=tampered_body, headers=headers
    )
    assert response.status_code == 401
    assert "Invalid webhook signature" in response.json()["detail"]


def test_webhook_secret_not_exposed_in_logs_or_response(
    client: TestClient, caplog
):
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

    # Ensure secret never appears in logs
    log_text = caplog.text
    assert TEST_WEBHOOK_SECRET not in log_text

    # Ensure secret never appears in response body
    resp_text = response.text
    assert TEST_WEBHOOK_SECRET not in resp_text


def test_unknown_event_types_persisted_safely(
    client: TestClient, db_session: Session
):
    """11 & 12. Test that unhandled event types are safely ingested without error."""
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

    stored = (
        db_session.query(PaymentEvent).filter_by(idempotency_key=event_id).first()
    )
    assert stored is not None
    assert stored.event_type == "custom.experimental.event"


def test_malformed_json_payload_returns_bad_request(client: TestClient):
    """13. Test that malformed JSON payload returns 400 Bad Request."""
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
    """14. Test that missing server webhook secret configuration returns 500."""

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
        assert (
            "Webhook secret not configured on server"
            in response.json()["detail"]
        )

    app.dependency_overrides.clear()
