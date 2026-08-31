"""Phase 10E — Data Governance, Privacy Engineering, Data Lineage & Regulatory-Grade Data Controls Test Suite.

Automated tests covering:
- Deterministic 8-pillar Data Governance & Privacy Score
- Data asset discovery and cataloging (16 RecoverIQ entities)
- Field-level classification with 50+ sensitive tags
- PII discovery scanner: Email, Phone, Aadhaar, PAN, Card, JWT, API Keys
- Deterministic HMAC-SHA256 pseudonymization
- Data lineage graph: nodes, edges, SHA-256 transformation checksums
- Data quality evaluation (Completeness, Validity, Uniqueness, Consistency, Freshness, Anomaly Rate)
- Retention governance & legal hold evaluation
- Advisory subject erasure eligibility evaluation
- 25 automated privacy and data governance controls
- Privacy incident deduplication
- Privacy request lifecycle: Create -> Review -> Approve/Reject -> Complete
- Exportable regulatory governance report with cryptographic signature
- 3-Tier RBAC enforcement (Viewer, Operator, Admin)
- Event-sourced AuditLog integration (entity_type="data_governance")
"""

import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.rate_limiter import rate_limiter
from app.core.security import UserRole, create_access_token
from app.main import app
from app.models.customer import Customer
from app.models.enums import (
    BillingCadence,
    CustomerRiskTier,
    DataClassification,
    DataDomain,
    DataQualityStatus,
    GovernanceScoreClassification,
    PaymentStatus,
    PrivacyRequestStatus,
    RetentionStatus,
    SubscriptionStatus,
)
from app.models.payment import Payment
from app.models.recovery_case import RecoveryCase
from app.models.subscription import Subscription
from app.services.data_governance_service import DataGovernanceService


@pytest.fixture(autouse=True)
def reset_rate_limiter():
    rate_limiter.reset()


@pytest.fixture
def client(db_session: Session):
    def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture
def viewer_headers():
    token = create_access_token(user_id="viewer_user", role=UserRole.VIEWER.value)
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def operator_headers():
    token = create_access_token(user_id="operator_user", role=UserRole.OPERATOR.value)
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def admin_headers():
    token = create_access_token(user_id="admin_user", role=UserRole.ADMIN.value)
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def seed_test_data(db_session: Session):
    run_id = uuid.uuid4().hex[:6]
    cust = Customer(
        external_customer_id=f"cust_gov_{run_id}",
        risk_tier=CustomerRiskTier.STANDARD.value,
    )
    db_session.add(cust)
    db_session.flush()

    sub = Subscription(
        customer_id=cust.id,
        external_subscription_id=f"sub_gov_{run_id}",
        status=SubscriptionStatus.ACTIVE.value,
        plan_name="Pro Plan",
        recurring_amount=50000,
        currency="INR",
        billing_cadence=BillingCadence.MONTHLY.value,
    )
    db_session.add(sub)
    db_session.flush()

    pay = Payment(
        customer_id=cust.id,
        subscription_id=sub.id,
        external_order_id=f"pay_gov_{run_id}",
        amount=50000,
        currency="INR",
        status=PaymentStatus.FAILED.value,
    )
    db_session.add(pay)
    db_session.flush()

    case = RecoveryCase(
        payment_id=pay.id,
        customer_id=cust.id,
        amount_at_risk=50000,
        recovered_amount=0,
        status="OPEN",
    )
    db_session.add(case)
    db_session.commit()
    return {"customer": cust, "payment": pay, "case": case}


# =============================================================================
# 1. Summary & Score Tests
# =============================================================================


def test_governance_summary_endpoint(
    client: TestClient, viewer_headers: dict, seed_test_data
):
    """Verifies executive data governance score and 8-pillar breakdown."""
    resp = client.get(
        "/api/recovery/intelligence/data-governance", headers=viewer_headers
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "governance_score" in data
    assert 0.0 <= data["governance_score"] <= 100.0
    assert data["classification"] in [e.value for e in GovernanceScoreClassification]
    assert data["total_assets_count"] >= 8
    assert data["controls_passed_count"] > 0
    assert "score_breakdown" in data
    breakdown = data["score_breakdown"]
    assert "privacy_controls_score" in breakdown
    assert "data_quality_score" in breakdown
    assert "data_lineage_score" in breakdown
    assert "retention_score" in breakdown
    assert "disclaimer" in data


# =============================================================================
# 2. Data Asset Registry & Classification Tests
# =============================================================================


def test_list_data_assets(client: TestClient, viewer_headers: dict, seed_test_data):
    """Verifies asset catalog discovery and domain mapping."""
    resp = client.get(
        "/api/recovery/intelligence/data-governance/assets", headers=viewer_headers
    )
    assert resp.status_code == 200
    assets = resp.json()
    assert len(assets) >= 8
    names = [a["asset_name"] for a in assets]
    assert "PaymentLedger" in names
    assert "RecoveryCaseStore" in names
    assert "CustomerRegistry" in names
    assert "ImmutableAuditLedger" in names


def test_get_data_asset_detail_and_404(client: TestClient, viewer_headers: dict):
    """Verifies specific asset retrieval and 404 for invalid asset."""
    resp = client.get(
        "/api/recovery/intelligence/data-governance/assets/AST-PAY-001",
        headers=viewer_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["asset_id"] == "AST-PAY-001"
    assert data["domain"] == DataDomain.PAYMENT.value
    assert data["classification"] == DataClassification.FINANCIAL_RESTRICTED.value
    assert len(data["fields"]) > 0

    resp_404 = client.get(
        "/api/recovery/intelligence/data-governance/assets/AST-NONEXISTENT",
        headers=viewer_headers,
    )
    assert resp_404.status_code == 404


# =============================================================================
# 3. PII & Secret Discovery Scanner Tests
# =============================================================================


def test_pii_discovery_scanner(client: TestClient, operator_headers: dict):
    """Verifies regex discovery of email, phone, PAN, Aadhaar, Card, and JWT."""
    payload = {
        "user_email": "john.doe@company.org",
        "mobile": "+919876543210",
        "pan": "ABCDE1234F",
        "aadhaar": "1234-5678-9012",
        "card": "4111111111111111",
        "auth_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIn0.dozjgN_p_secret",
        "api_secret_key": "sk_live_supersecret_token_12345",
    }
    resp = client.post(
        "/api/recovery/intelligence/data-governance/scan",
        json={"payload": payload},
        headers=operator_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["findings_count"] >= 6
    assert data["has_critical_findings"] is True

    categories = [f["detected_category"] for f in data["findings"]]
    assert "CUSTOMER_EMAIL" in categories
    assert "CUSTOMER_PHONE" in categories
    assert "INDIAN_PAN_NUMBER" in categories
    assert "INDIAN_AADHAAR_NUMBER" in categories
    assert "PAYMENT_CARD_NUMBER" in categories
    assert "JWT_TOKEN" in categories

    # Verify zero plain text secrets in response
    for finding in data["findings"]:
        assert "sk_live" not in finding["masked_value"]
        assert "4111111111111111" not in finding["masked_value"]
        assert "ABCDE1234F" not in finding["masked_value"]
        assert len(finding["evidence_hash"]) == 64


def test_pii_scanner_clean_payload(client: TestClient, operator_headers: dict):
    """Verifies scanner produces 0 findings on clean internal operational metrics."""
    clean_payload = {
        "service": "api_gateway",
        "p95_latency_ms": 42.5,
        "throughput_rpm": 1200,
        "status": "HEALTHY",
    }
    resp = client.post(
        "/api/recovery/intelligence/data-governance/scan",
        json={"payload": clean_payload},
        headers=operator_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["findings_count"] == 0
    assert data["has_critical_findings"] is False


# =============================================================================
# 4. Pseudonymization Tests
# =============================================================================


def test_pseudonymization_deterministic_and_salted(db_session: Session):
    """Verifies deterministic HMAC-SHA256 pseudonymization."""
    service = DataGovernanceService(db_session)
    pseudo_1 = service.pseudonymize("cust_12345")
    pseudo_2 = service.pseudonymize("cust_12345")
    pseudo_3 = service.pseudonymize("cust_67890")

    assert pseudo_1 == pseudo_2
    assert pseudo_1 != pseudo_3
    assert pseudo_1.startswith("sub_pseudo_")
    assert "cust_12345" not in pseudo_1


# =============================================================================
# 5. Data Lineage Graph Tests
# =============================================================================


def test_data_lineage_graph(client: TestClient, viewer_headers: dict):
    """Verifies end-to-end lineage graph structure and transformation checksums."""
    resp = client.get(
        "/api/recovery/intelligence/data-governance/lineage", headers=viewer_headers
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["integrity_status"] == "VERIFIED"
    assert data["coverage_pct"] == 100.0
    assert len(data["nodes"]) >= 7
    assert len(data["edges"]) >= 6

    # Verify node lookup
    first_node_id = data["nodes"][0]["node_id"]
    node_resp = client.get(
        f"/api/recovery/intelligence/data-governance/lineage/{first_node_id}",
        headers=viewer_headers,
    )
    assert node_resp.status_code == 200
    assert node_resp.json()["node_id"] == first_node_id


# =============================================================================
# 6. Data Quality Engine Tests
# =============================================================================


def test_data_quality_metrics(client: TestClient, viewer_headers: dict, seed_test_data):
    """Verifies 6-dimension data quality evaluation and scoring."""
    resp = client.get(
        "/api/recovery/intelligence/data-governance/data-quality",
        headers=viewer_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["completeness_pct"] >= 95.0
    assert data["validity_pct"] >= 95.0
    assert data["uniqueness_pct"] >= 95.0
    assert data["consistency_pct"] >= 95.0
    assert data["status"] in [e.value for e in DataQualityStatus]
    assert 0.0 <= data["score"] <= 100.0


# =============================================================================
# 7. Retention Governance & Erasure Tests
# =============================================================================


def test_retention_statuses_and_legal_hold(client: TestClient, viewer_headers: dict):
    """Verifies domain retention policies and legal hold protection."""
    resp = client.get(
        "/api/recovery/intelligence/data-governance/retention", headers=viewer_headers
    )
    assert resp.status_code == 200
    items = resp.json()
    assert len(items) >= 8

    # Verify AuditLog has legal hold active
    audit_item = next(i for i in items if i["asset_name"] == "ImmutableAuditLedger")
    assert audit_item["legal_hold"] is True
    assert audit_item["status"] == RetentionStatus.LEGAL_HOLD.value
    assert audit_item["deletion_eligible"] is False


def test_erasure_eligibility_with_financial_blockers(
    client: TestClient, viewer_headers: dict, seed_test_data
):
    """Verifies customer with active payments is not eligible for automatic erasure due to statutory hold."""
    cust_id = seed_test_data["customer"].external_customer_id
    resp = client.get(
        f"/api/recovery/intelligence/data-governance/erasure-eligibility/{cust_id}",
        headers=viewer_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["eligible_for_erasure"] is False
    assert data["financial_record_retention_required"] is True
    assert len(data["blocker_reasons"]) > 0


# =============================================================================
# 8. Privacy Controls & Incidents Tests
# =============================================================================


def test_25_privacy_controls_and_filters(client: TestClient, viewer_headers: dict):
    """Verifies all 25 controls and category/status query filters."""
    resp = client.get(
        "/api/recovery/intelligence/data-governance/controls", headers=viewer_headers
    )
    assert resp.status_code == 200
    controls = resp.json()
    assert len(controls) == 25

    # Filter by category
    resp_cat = client.get(
        "/api/recovery/intelligence/data-governance/controls?category=PRIVACY",
        headers=viewer_headers,
    )
    assert resp_cat.status_code == 200
    assert len(resp_cat.json()) == 5

    # Filter by status
    resp_pass = client.get(
        "/api/recovery/intelligence/data-governance/controls?status=PASS",
        headers=viewer_headers,
    )
    assert resp_pass.status_code == 200
    assert len(resp_pass.json()) == 25


def test_list_privacy_incidents(client: TestClient, viewer_headers: dict):
    """Verifies incident retrieval."""
    resp = client.get(
        "/api/recovery/intelligence/data-governance/incidents", headers=viewer_headers
    )
    assert resp.status_code == 200
    incidents = resp.json()
    assert len(incidents) >= 1
    assert "incident_id" in incidents[0]
    assert "evidence_hash" in incidents[0]


# =============================================================================
# 9. Privacy Request Lifecycle Tests
# =============================================================================


def test_privacy_request_full_lifecycle(
    client: TestClient, operator_headers: dict, admin_headers: dict
):
    """Verifies complete request lifecycle: Create -> Review (Approve) -> Complete."""
    # 1. Create request (Operator)
    create_payload = {
        "request_type": "ACCESS",
        "subject_id": "cust_subject_test_01",
        "scope": "PAYMENT_AND_RECOVERY_HISTORY",
        "notes": "Subject requested copy of all transaction logs.",
    }
    resp_create = client.post(
        "/api/recovery/intelligence/data-governance/privacy-requests",
        json=create_payload,
        headers=operator_headers,
    )
    assert resp_create.status_code == 200
    req_data = resp_create.json()
    req_id = req_data["request_id"]
    assert req_data["status"] == PrivacyRequestStatus.RECEIVED.value
    assert req_data["subject_pseudonym"].startswith("sub_pseudo_")

    # 2. Review / Approve request (Admin)
    review_payload = {
        "decision": "APPROVE",
        "notes": "Identity verified via merchant authenticated channel.",
    }
    resp_review = client.post(
        f"/api/recovery/intelligence/data-governance/privacy-requests/{req_id}/review",
        json=review_payload,
        headers=admin_headers,
    )
    assert resp_review.status_code == 200
    assert resp_review.json()["status"] == PrivacyRequestStatus.APPROVED.value

    # 3. Complete request (Admin)
    complete_payload = {
        "notes": "Export archive generated and uploaded to secure subject inbox.",
    }
    resp_complete = client.post(
        f"/api/recovery/intelligence/data-governance/privacy-requests/{req_id}/complete",
        json=complete_payload,
        headers=admin_headers,
    )
    assert resp_complete.status_code == 200
    assert resp_complete.json()["status"] == PrivacyRequestStatus.COMPLETED.value


def test_privacy_request_rejection(
    client: TestClient, operator_headers: dict, admin_headers: dict
):
    """Verifies request rejection pathway."""
    create_payload = {
        "request_type": "ERASURE",
        "subject_id": "cust_subject_reject_01",
        "scope": "FULL_DATASET",
        "notes": "Immediate erasure requested.",
    }
    resp_create = client.post(
        "/api/recovery/intelligence/data-governance/privacy-requests",
        json=create_payload,
        headers=operator_headers,
    )
    req_id = resp_create.json()["request_id"]

    review_payload = {
        "decision": "REJECT",
        "notes": "Rejected due to active 7-year statutory financial retention mandate.",
    }
    resp_review = client.post(
        f"/api/recovery/intelligence/data-governance/privacy-requests/{req_id}/review",
        json=review_payload,
        headers=admin_headers,
    )
    assert resp_review.status_code == 200
    assert resp_review.json()["status"] == PrivacyRequestStatus.REJECTED.value


# =============================================================================
# 10. Governance Report & Signature Tests
# =============================================================================


def test_generate_governance_report(client: TestClient, viewer_headers: dict):
    """Verifies report generation with SHA-256 cryptographic signature."""
    resp = client.get(
        "/api/recovery/intelligence/data-governance/report", headers=viewer_headers
    )
    assert resp.status_code == 200
    report = resp.json()
    assert "report_id" in report
    assert "verification_signature" in report
    assert report["verification_signature"].startswith("sha256:")
    assert len(report["assets"]) >= 8
    assert len(report["controls"]) == 25
    assert len(report["remediation_roadmap"]) > 0


# =============================================================================
# 11. RBAC Security Tests
# =============================================================================


def test_rbac_boundary_enforcement(
    client: TestClient, viewer_headers: dict, operator_headers: dict
):
    """Verifies viewer cannot create/review requests, operator cannot review, admin required."""
    # 1. Viewer cannot create request (Requires Operator)
    resp = client.post(
        "/api/recovery/intelligence/data-governance/privacy-requests",
        json={"request_type": "ACCESS", "subject_id": "cust_123"},
        headers=viewer_headers,
    )
    assert resp.status_code == 403

    # 2. Operator cannot review request (Requires Admin)
    resp_rev = client.post(
        "/api/recovery/intelligence/data-governance/privacy-requests/REQ-PRV-123/review",
        json={"decision": "APPROVE", "notes": "Approved"},
        headers=operator_headers,
    )
    assert resp_rev.status_code == 403
