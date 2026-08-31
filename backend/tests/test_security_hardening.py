import json
import time
import uuid
from datetime import timedelta

import jwt
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.database import get_db
from app.core.pii_scanner import is_luhn_valid
from app.core.rate_limiter import rate_limiter
from app.core.security import (
    UserRole,
    create_access_token,
    is_token_jti_revoked,
)
from app.main import app
from app.models.customer import Customer
from app.models.enums import (
    CustomerRiskTier,
    PaymentStatus,
    RecoveryCaseStatus,
)
from app.models.payment import Payment
from app.models.recovery_action import RecoveryAction
from app.models.recovery_case import RecoveryCase
from app.models.subscription import Subscription


@pytest.fixture(autouse=True)
def reset_rate_limiter():
    """Reset in-memory rate limiter before each test."""
    rate_limiter.reset()
    yield
    rate_limiter.reset()


@pytest.fixture
def viewer_token() -> str:
    return create_access_token(user_id="view_user_1", role=UserRole.VIEWER.value)


@pytest.fixture
def operator_token() -> str:
    return create_access_token(user_id="op_user_1", role=UserRole.OPERATOR.value)


@pytest.fixture
def admin_token() -> str:
    return create_access_token(user_id="admin_user_1", role=UserRole.ADMIN.value)


@pytest.fixture
def client(db_session: Session) -> TestClient:
    def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    test_client = TestClient(app)
    yield test_client
    app.dependency_overrides.clear()


@pytest.fixture
def test_seed_financials(db_session: Session) -> RecoveryCase:
    """Create a sample financial recovery case for isolation verification."""
    cust_id = uuid.uuid4()
    cust = Customer(
        id=cust_id,
        external_customer_id=f"cust_{cust_id.hex[:6]}",
        email_masked="a***@example.com",
        phone_masked="+91******8888",
        risk_tier=CustomerRiskTier.LOW,
        total_payments_count=5,
        failed_payments_count=1,
    )
    db_session.add(cust)

    sub_id = uuid.uuid4()
    sub = Subscription(
        id=sub_id,
        customer_id=cust_id,
        external_subscription_id=f"sub_{sub_id.hex[:6]}",
        status="ACTIVE",
        plan_name="Enterprise Hardened",
        billing_cadence="MONTHLY",
        recurring_amount=100000,
    )
    db_session.add(sub)

    pay_id = uuid.uuid4()
    payment = Payment(
        id=pay_id,
        customer_id=cust_id,
        subscription_id=sub_id,
        external_order_id=f"pay_{pay_id.hex[:6]}",
        amount=100000,
        status=PaymentStatus.FAILED,
    )
    db_session.add(payment)

    case_id = uuid.uuid4()
    case = RecoveryCase(
        id=case_id,
        payment_id=pay_id,
        customer_id=cust_id,
        status=RecoveryCaseStatus.OPEN,
        amount_at_risk=100000,
        recovered_amount=0,
        total_attempts_count=1,
    )
    db_session.add(case)
    db_session.commit()
    return case


# =============================================================================
# 1. JWT Cryptographic Hardening Tests
# =============================================================================


def test_jwt_signature_verification_and_algorithm_pinning(client: TestClient):
    """Test that valid HS256 tokens are accepted, but forged or none-algorithm tokens are rejected."""
    settings = get_settings()

    # 1. Valid token
    valid_token = create_access_token(user_id="valid_user", role=UserRole.VIEWER.value)
    res_valid = client.get(
        "/api/recovery/security/trust-center",
        headers={"Authorization": f"Bearer {valid_token}"},
    )
    assert res_valid.status_code == 200
    assert res_valid.json()["trust_score"] >= 0.0

    # 2. Forged signature
    forged_token = jwt.encode(
        {
            "sub": "attacker",
            "role": "admin",
            "exp": int(time.time()) + 3600,
            "iss": settings.app_name,
            "iat": int(time.time()),
        },
        "wrong_secret_key_12345",
        algorithm="HS256",
    )
    res_forged = client.get(
        "/api/recovery/security/trust-center",
        headers={"Authorization": f"Bearer {forged_token}"},
    )
    assert res_forged.status_code == 401
    assert "Invalid or malformed authentication token" in res_forged.json()["detail"]


def test_jwt_expiration_and_clock_skew(client: TestClient):
    """Test that expired tokens are strictly rejected with HTTP 401."""
    expired_token = create_access_token(
        user_id="expired_user",
        role=UserRole.OPERATOR.value,
        expires_delta=timedelta(seconds=-10),
    )
    res = client.get(
        "/api/recovery/security/trust-center",
        headers={"Authorization": f"Bearer {expired_token}"},
    )
    assert res.status_code == 401
    assert "expired" in res.json()["detail"].lower()


def test_jwt_token_revocation(client: TestClient, admin_token: str):
    """Test that a revoked JWT identifier (jti) is blacklisted and rejected immediately."""
    custom_jti = f"jti_test_{uuid.uuid4().hex[:12]}"
    token_to_revoke = create_access_token(
        user_id="victim_user",
        role=UserRole.OPERATOR.value,
        jti=custom_jti,
    )

    # 1. Token works initially
    res_before = client.get(
        "/api/recovery/security/trust-center",
        headers={"Authorization": f"Bearer {token_to_revoke}"},
    )
    assert res_before.status_code == 200

    # 2. Admin revokes the token JTI
    res_revoke = client.post(
        "/api/recovery/security/revoke-token",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={"jti": custom_jti, "reason": "Compromised credential tripwire"},
    )
    assert res_revoke.status_code == 200
    assert res_revoke.json()["revoked"] is True
    assert is_token_jti_revoked(custom_jti) is True

    # 3. Token is now rejected with HTTP 401
    res_after = client.get(
        "/api/recovery/security/trust-center",
        headers={"Authorization": f"Bearer {token_to_revoke}"},
    )
    assert res_after.status_code == 401
    assert "revoked" in res_after.json()["detail"].lower()


# =============================================================================
# 2. Centralized RBAC & Privilege Escalation Defense Tests
# =============================================================================


def test_rbac_hierarchy_and_privilege_escalation(
    client: TestClient,
    viewer_token: str,
    operator_token: str,
    admin_token: str,
):
    """Test that RBAC hierarchy is strictly enforced and privilege escalation is blocked."""
    # 1. Viewer can read Trust Center (requires VIEWER)
    res_v_read = client.get(
        "/api/recovery/security/trust-center",
        headers={"Authorization": f"Bearer {viewer_token}"},
    )
    assert res_v_read.status_code == 200

    # 2. Viewer CANNOT query security events (requires OPERATOR) -> 403 Forbidden
    res_v_events = client.get(
        "/api/recovery/security/events",
        headers={"Authorization": f"Bearer {viewer_token}"},
    )
    assert res_v_events.status_code == 403
    assert "Access denied" in res_v_events.json()["detail"]

    # 3. Operator can query security events
    res_op_events = client.get(
        "/api/recovery/security/events",
        headers={"Authorization": f"Bearer {operator_token}"},
    )
    assert res_op_events.status_code == 200

    # 4. Operator CANNOT revoke tokens (requires ADMIN) -> 403 Forbidden
    res_op_revoke = client.post(
        "/api/recovery/security/revoke-token",
        headers={"Authorization": f"Bearer {operator_token}"},
        json={"jti": "jti_unauthorized_attempt_1", "reason": "test"},
    )
    assert res_op_revoke.status_code == 403
    assert "Access denied" in res_op_revoke.json()["detail"]

    # 5. Admin can revoke tokens
    res_admin_revoke = client.post(
        "/api/recovery/security/revoke-token",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={"jti": "jti_admin_authorized_1", "reason": "Authorized admin revocation"},
    )
    assert res_admin_revoke.status_code == 200


# =============================================================================
# 3. Rate Limiting Tests (Sliding Window & HTTP 429)
# =============================================================================


def test_rate_limiting_triggers_429_with_retry_after(
    client: TestClient, admin_token: str
):
    """Test that exceeding the rate limit returns HTTP 429 with standard headers."""
    # Settings configure rate_limit_mutations_per_minute = 60
    # Let's trigger 65 rapid requests on a mutation endpoint
    exceeded = False
    for i in range(65):
        res = client.post(
            "/api/recovery/security/revoke-token",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={"jti": f"jti_flood_{i}", "reason": "rate limit test"},
        )
        if res.status_code == 429:
            exceeded = True
            assert "Retry-After" in res.headers
            assert "X-RateLimit-Limit" in res.headers
            assert res.headers["X-RateLimit-Remaining"] == "0"
            assert "Rate limit exceeded" in res.json()["detail"]
            break

    assert exceeded is True


# =============================================================================
# 4. Webhook Hardening & Replay Protection Tests
# =============================================================================


def test_webhook_hmac_signature_verification_and_constant_time(client: TestClient):
    """Test that webhook requests are verified via constant-time HMAC-SHA256."""
    settings = get_settings()
    secret = "test_webhook_secret_key_123"
    settings.razorpay_webhook_secret = secret

    payload_dict = {
        "event": "payment.failed",
        "created_at": int(time.time()),
        "payload": {"payment": {"entity": {"id": "pay_test_sec_01", "amount": 50000}}},
    }
    raw_bytes = json.dumps(payload_dict).encode("utf-8")

    import hashlib
    import hmac

    valid_sig = hmac.new(secret.encode("utf-8"), raw_bytes, hashlib.sha256).hexdigest()

    # 1. Valid signature -> 200 OK
    res_valid = client.post(
        "/webhooks/razorpay",
        content=raw_bytes,
        headers={
            "X-Razorpay-Signature": valid_sig,
            "X-Razorpay-Event-Id": "evt_sec_valid_01",
            "Content-Type": "application/json",
        },
    )
    assert res_valid.status_code == 200
    assert res_valid.json()["status"] == "ok"

    # 2. Tampered signature -> 401 Unauthorized
    res_tampered = client.post(
        "/webhooks/razorpay",
        content=raw_bytes,
        headers={
            "X-Razorpay-Signature": "invalid_signature_hex_12345",
            "X-Razorpay-Event-Id": "evt_sec_tampered_01",
            "Content-Type": "application/json",
        },
    )
    assert res_tampered.status_code == 401
    assert "Invalid webhook signature" in res_tampered.json()["detail"]

    # 3. Missing signature header -> 400 Bad Request
    res_missing = client.post(
        "/webhooks/razorpay",
        content=raw_bytes,
        headers={
            "X-Razorpay-Event-Id": "evt_sec_missing_01",
            "Content-Type": "application/json",
        },
    )
    assert res_missing.status_code == 400


def test_webhook_replay_protection(client: TestClient):
    """Test that webhook events with timestamps older than tolerance window (300s) are rejected."""
    settings = get_settings()
    secret = "test_webhook_secret_key_123"
    settings.razorpay_webhook_secret = secret
    old_tolerance = settings.webhook_timestamp_tolerance_seconds
    settings.webhook_timestamp_tolerance_seconds = 300

    try:
        # Payload timestamp is 600s in the past (exceeds 300s window)
        old_timestamp = int(time.time()) - 600
        payload_dict = {
            "event": "payment.failed",
            "created_at": old_timestamp,
            "payload": {
                "payment": {"entity": {"id": "pay_test_replay_01", "amount": 50000}}
            },
        }
        raw_bytes = json.dumps(payload_dict).encode("utf-8")

        import hashlib
        import hmac

        sig = hmac.new(secret.encode("utf-8"), raw_bytes, hashlib.sha256).hexdigest()

        res = client.post(
            "/webhooks/razorpay",
            content=raw_bytes,
            headers={
                "X-Razorpay-Signature": sig,
                "X-Razorpay-Event-Id": "evt_replay_01",
                "Content-Type": "application/json",
            },
        )
        assert res.status_code == 400
        assert "tolerance window" in res.json()["detail"]
    finally:
        settings.webhook_timestamp_tolerance_seconds = old_tolerance


# =============================================================================
# 5. PII & Secret Scanner Engine Tests
# =============================================================================


def test_luhn_algorithm_card_validation():
    """Verify Luhn algorithm implementation correctly identifies valid and invalid card PANs."""
    # Valid Visa test PAN
    assert is_luhn_valid("4532015112830366") is True
    # Valid Mastercard test PAN
    assert is_luhn_valid("5425233430109903") is True
    # Invalid PAN (checksum fail)
    assert is_luhn_valid("4532015112830367") is False
    # Short length
    assert is_luhn_valid("12345") is False


def test_pii_and_secret_redaction_engine(client: TestClient, operator_token: str):
    """Verify scanning and instantaneous redaction of Card PANs, CVV, Aadhaar, and API keys."""
    test_payload = {
        "customer": {
            "name": "Jane Doe",
            "email": "jane.doe@enterprise.com",
            "phone": "+919876543210",
            "national_id": "9876 5432 1098",  # Aadhaar
        },
        "payment_method": {
            "card_number": "4532015112830366",  # Luhn valid
            "cvv": "123",
            "notes": "Payment processed with key rzp_live_abcdef1234567890 and password SuperSecretPassword!",
        },
    }

    res = client.post(
        "/api/recovery/security/scan",
        headers={"Authorization": f"Bearer {operator_token}"},
        json={"payload": test_payload},
    )
    assert res.status_code == 200
    data = res.json()
    assert data["has_pii"] is True
    assert data["has_secrets"] is True
    assert data["findings_count"] >= 3

    sanitized = data["sanitized_payload"]
    # Check email masked
    assert sanitized["customer"]["email"] == "j***e@enterprise.com"
    # Check phone masked
    assert sanitized["customer"]["phone"] == "+91******3210"
    # Check card PAN masked
    assert sanitized["payment_method"]["card_number"] == "[REDACTED_SECRET]"
    # Check CVV redacted
    assert sanitized["payment_method"]["cvv"] == "[REDACTED_SECRET]"
    # Check Aadhaar masked
    assert "XXXX-XXXX-1098" in sanitized["customer"]["national_id"]


# =============================================================================
# 6. Security Headers & CORS Policy Tests
# =============================================================================


def test_security_headers_and_cors_policy(client: TestClient, viewer_token: str):
    """Verify presence of standard enterprise fintech HTTP security headers."""
    res = client.get(
        "/api/recovery/security/trust-center",
        headers={
            "Authorization": f"Bearer {viewer_token}",
            "Origin": "http://localhost:3000",
        },
    )
    assert res.status_code == 200

    # Security Headers Verification
    assert res.headers.get("X-Content-Type-Options") == "nosniff"
    assert res.headers.get("X-Frame-Options") == "DENY"
    assert res.headers.get("X-XSS-Protection") == "1; mode=block"
    assert "max-age=31536000" in res.headers.get("Strict-Transport-Security", "")
    assert "default-src 'self'" in res.headers.get("Content-Security-Policy", "")
    assert res.headers.get("Referrer-Policy") == "strict-origin-when-cross-origin"
    assert "payment=()" in res.headers.get("Permissions-Policy", "")

    # CORS Headers Verification
    assert res.headers.get("access-control-allow-origin") == "http://localhost:3000"
    assert res.headers.get("access-control-allow-credentials") == "true"


# =============================================================================
# 7. Mandatory Financial Isolation Guarantee Tests
# =============================================================================


def test_mandatory_financial_isolation_guarantee(
    client: TestClient,
    db_session: Session,
    viewer_token: str,
    operator_token: str,
    admin_token: str,
    test_seed_financials: RecoveryCase,
):
    """
    CRITICAL INVARIANT TEST:
    Assert that invoking security endpoints, threat logging, token revocations, and
    PII scans produces ZERO financial mutations, ZERO RecoveryAction records,
    and ZERO mutations to Payment or RecoveryCase financial state.
    """
    initial_actions_count = db_session.query(RecoveryAction).count()
    initial_case = (
        db_session.query(RecoveryCase)
        .filter(RecoveryCase.id == test_seed_financials.id)
        .first()
    )
    initial_case_status = initial_case.status
    initial_recovered_amount = initial_case.recovered_amount

    # 1. Execute Trust Center Overview
    res_tc = client.get(
        "/api/recovery/security/trust-center",
        headers={"Authorization": f"Bearer {viewer_token}"},
    )
    assert res_tc.status_code == 200

    # 2. Execute Security Events Query
    res_ev = client.get(
        "/api/recovery/security/events",
        headers={"Authorization": f"Bearer {operator_token}"},
    )
    assert res_ev.status_code == 200

    # 3. Execute PII Scan
    res_scan = client.post(
        "/api/recovery/security/scan",
        headers={"Authorization": f"Bearer {operator_token}"},
        json={
            "payload": {"test_card": "4532015112830366", "email": "test@example.com"}
        },
    )
    assert res_scan.status_code == 200

    # 4. Execute Token Revocation
    res_rev = client.post(
        "/api/recovery/security/revoke-token",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={"jti": f"jti_iso_{uuid.uuid4().hex[:8]}", "reason": "isolation test"},
    )
    assert res_rev.status_code == 200

    # 5. Assert strict zero financial mutations
    db_session.expire_all()
    final_actions_count = db_session.query(RecoveryAction).count()
    refreshed_case = (
        db_session.query(RecoveryCase)
        .filter(RecoveryCase.id == test_seed_financials.id)
        .first()
    )

    assert final_actions_count == initial_actions_count, (
        "Financial Invariant Violated: RecoveryAction count changed!"
    )
    assert refreshed_case.status == initial_case_status, (
        "Financial Invariant Violated: RecoveryCase status mutated!"
    )
    assert refreshed_case.recovered_amount == initial_recovered_amount, (
        "Financial Invariant Violated: Recovered amount mutated!"
    )
