"""Automated test suite for Phase 10H: Zero-Trust Infrastructure, Runtime Security,

Advanced Threat Intelligence & Security Operations Control Plane.
"""

import pytest
from fastapi.testclient import TestClient

from app.core.security import UserRole, create_access_token


@pytest.fixture
def viewer_token() -> str:
    """JWT token for viewer role."""
    return create_access_token(user_id="viewer_user", role=UserRole.VIEWER.value)


@pytest.fixture
def operator_token() -> str:
    """JWT token for operator role."""
    return create_access_token(user_id="operator_user", role=UserRole.OPERATOR.value)


@pytest.fixture
def admin_token() -> str:
    """JWT token for admin role."""
    return create_access_token(user_id="admin_user", role=UserRole.ADMIN.value)


# -------------------------------------------------------------------------
# 1. Summary & Zero-Trust Health Scoring
# -------------------------------------------------------------------------


def test_zero_trust_summary_and_scoring(client: TestClient, viewer_token: str):
    """Test 0-100 Zero Trust score formula, bounds, and global classification."""
    response = client.get(
        "/api/recovery/intelligence/zero-trust/summary",
        headers={"Authorization": f"Bearer {viewer_token}"},
    )
    assert response.status_code == 200
    data = response.json()

    assert "zero_trust_score" in data
    assert 0.0 <= data["zero_trust_score"] <= 100.0
    assert data["score_classification"] in [
        "TRUSTED",
        "ACCEPTABLE",
        "DEGRADED",
        "HIGH_RISK",
        "CRITICAL",
    ]
    assert data["global_security_state"] == "SECURE"
    assert data["financial_isolation_verified"] is True
    assert data["automatic_financial_response"] == "DISABLED"


def test_unauthenticated_request_rejected(client: TestClient):
    """Test unauthenticated endpoint access returns 401 Unauthorized."""
    response = client.get("/api/recovery/intelligence/zero-trust/summary")
    assert response.status_code == 401


# -------------------------------------------------------------------------
# 2. Service Identity Registry & Authorization Matrix
# -------------------------------------------------------------------------


def test_service_identities_registry(client: TestClient, viewer_token: str):
    """Test 11 core microservice identities telemetry and trust scores."""
    response = client.get(
        "/api/recovery/intelligence/zero-trust/service-identities",
        headers={"Authorization": f"Bearer {viewer_token}"},
    )
    assert response.status_code == 200
    identities = response.json()

    assert len(identities) == 11
    service_names = {i["service_name"] for i in identities}
    assert "Policy Engine" in service_names
    assert "Action Dispatcher" in service_names
    assert "Razorpay Action Provider" in service_names

    for item in identities:
        assert 0.0 <= item["trust_score"] <= 100.0
        assert item["identity_status"] in [
            "AUTHENTICATED",
            "VALIDATED",
            "DEGRADED",
            "STALE_CREDENTIAL",
            "REVOKED",
            "UNTRUSTED",
        ]


def test_service_identity_by_name_lookup(client: TestClient, viewer_token: str):
    """Test retrieving specific service identity by name."""
    response = client.get(
        "/api/recovery/intelligence/zero-trust/service-identities/Policy%20Engine",
        headers={"Authorization": f"Bearer {viewer_token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["service_name"] == "Policy Engine"
    assert data["trust_score"] == 100.0


def test_authorization_matrix_and_violations(client: TestClient, viewer_token: str):
    """Test service-to-service authorization matrix topology and violation detection."""
    response = client.get(
        "/api/recovery/intelligence/zero-trust/authorization-matrix",
        headers={"Authorization": f"Bearer {viewer_token}"},
    )
    assert response.status_code == 200
    data = response.json()

    assert data["total_pairs"] > 0
    assert data["allowed_pairs"] >= 10
    assert data["denied_pairs"] >= 3
    assert data["violations_count"] >= 2


def test_trust_violations_endpoint(client: TestClient, viewer_token: str):
    """Test zero-trust boundary and authorization violations endpoint."""
    response = client.get(
        "/api/recovery/intelligence/zero-trust/trust-violations",
        headers={"Authorization": f"Bearer {viewer_token}"},
    )
    assert response.status_code == 200
    violations = response.json()
    assert len(violations) >= 2
    for v in violations:
        assert v["violation_id"].startswith("ZT-VIOLATION-")


# -------------------------------------------------------------------------
# 3. Threat Intelligence & Behavioral Threat Scoring
# -------------------------------------------------------------------------


def test_threat_indicators_sanitized(client: TestClient, viewer_token: str):
    """Test threat indicators return hashed fingerprints with zero PII exposure."""
    response = client.get(
        "/api/recovery/intelligence/zero-trust/threat-indicators",
        headers={"Authorization": f"Bearer {viewer_token}"},
    )
    assert response.status_code == 200
    indicators = response.json()
    assert len(indicators) >= 2

    for ind in indicators:
        assert ind["indicator_id"].startswith("IND-")
        assert ind["fingerprint"].startswith("sha256:")
        assert "password" not in ind["description"].lower()
        assert (
            "key" not in ind["description"].lower()
            or "public" in ind["description"].lower()
            or "header" in ind["description"].lower()
        )


def test_behavioral_threat_score(client: TestClient, viewer_token: str):
    """Test behavioral threat score calculation and sub-anomaly dimensions."""
    response = client.get(
        "/api/recovery/intelligence/zero-trust/threat-score",
        headers={"Authorization": f"Bearer {viewer_token}"},
    )
    assert response.status_code == 200
    data = response.json()

    assert 0.0 <= data["overall_threat_score"] <= 100.0
    assert data["classification"] in [
        "INFORMATIONAL",
        "LOW",
        "MEDIUM",
        "HIGH",
        "CRITICAL",
    ]


# -------------------------------------------------------------------------
# 4. Attack-Chain Correlation Engine
# -------------------------------------------------------------------------


def test_attack_chains_reconstruction(client: TestClient, viewer_token: str):
    """Test reconstruction of 8-stage correlated attack propagation chains."""
    response = client.get(
        "/api/recovery/intelligence/zero-trust/attack-chains",
        headers={"Authorization": f"Bearer {viewer_token}"},
    )
    assert response.status_code == 200
    chains = response.json()
    assert len(chains) >= 1

    chain = chains[0]
    assert chain["chain_id"].startswith("CHAIN-")
    assert len(chain["stages"]) == 8
    assert chain["stages"][0]["stage"] == "INITIAL_SIGNAL"
    assert chain["stages"][-1]["stage"] == "THREAT_INCIDENT"
    assert chain["human_review_required"] is True


def test_attack_chain_by_id_lookup(client: TestClient, viewer_token: str):
    """Test retrieving specific attack chain by ID."""
    chains_resp = client.get(
        "/api/recovery/intelligence/zero-trust/attack-chains",
        headers={"Authorization": f"Bearer {viewer_token}"},
    )
    chain_id = chains_resp.json()[0]["chain_id"]

    response = client.get(
        f"/api/recovery/intelligence/zero-trust/attack-chains/{chain_id}",
        headers={"Authorization": f"Bearer {viewer_token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["chain_id"] == chain_id


# -------------------------------------------------------------------------
# 5. Runtime Security & Secret Exposure Surveillance
# -------------------------------------------------------------------------


def test_runtime_security_posture(client: TestClient, viewer_token: str):
    """Test runtime security surveillance metrics."""
    response = client.get(
        "/api/recovery/intelligence/zero-trust/runtime-security",
        headers={"Authorization": f"Bearer {viewer_token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["process_integrity_status"] == "VERIFIED"
    assert data["dependency_cve_count_critical"] == 0


def test_secret_exposure_sanitized_masks(client: TestClient, viewer_token: str):
    """Test secret exposure findings return masked values and SHA-256 fingerprints."""
    response = client.get(
        "/api/recovery/intelligence/zero-trust/secret-exposure",
        headers={"Authorization": f"Bearer {viewer_token}"},
    )
    assert response.status_code == 200
    findings = response.json()
    assert len(findings) >= 1

    finding = findings[0]
    assert "[MASKED]" in finding["masked_value"]
    assert finding["fingerprint"].startswith("sha256:")


# -------------------------------------------------------------------------
# 6. Security Incident Command Center & RBAC
# -------------------------------------------------------------------------


def test_security_incidents_list(client: TestClient, viewer_token: str):
    """Test security incident list endpoint."""
    response = client.get(
        "/api/recovery/intelligence/zero-trust/security-incidents",
        headers={"Authorization": f"Bearer {viewer_token}"},
    )
    assert response.status_code == 200
    incidents = response.json()
    assert len(incidents) >= 2


def test_incident_operator_actions_and_rbac(
    client: TestClient, viewer_token: str, operator_token: str, admin_token: str
):
    """Test operator incident lifecycle actions (Acknowledge, Escalate, Resolve) and RBAC permissions."""
    inc_id = "INC-ZT-PRIVILEGE-ESCALATION"

    # Viewer role cannot perform operator POST actions
    fail_resp = client.post(
        f"/api/recovery/intelligence/zero-trust/security-incidents/{inc_id}/acknowledge",
        headers={"Authorization": f"Bearer {viewer_token}"},
    )
    assert fail_resp.status_code == 403

    # Operator acknowledges
    ack_resp = client.post(
        f"/api/recovery/intelligence/zero-trust/security-incidents/{inc_id}/acknowledge?notes=Triage_started",
        headers={"Authorization": f"Bearer {operator_token}"},
    )
    assert ack_resp.status_code == 200
    assert ack_resp.json()["status"] == "ACKNOWLEDGED"

    # Operator escalates
    esc_resp = client.post(
        f"/api/recovery/intelligence/zero-trust/security-incidents/{inc_id}/escalate?notes=Escalated_to_tier3",
        headers={"Authorization": f"Bearer {operator_token}"},
    )
    assert esc_resp.status_code == 200
    assert esc_resp.json()["status"] == "ESCALATED"

    # Operator cannot resolve (requires ADMIN)
    op_res_fail = client.post(
        f"/api/recovery/intelligence/zero-trust/security-incidents/{inc_id}/resolve",
        headers={"Authorization": f"Bearer {operator_token}"},
    )
    assert op_res_fail.status_code == 403

    # Admin resolves
    adm_res = client.post(
        f"/api/recovery/intelligence/zero-trust/security-incidents/{inc_id}/resolve?notes=Resolution_verified",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert adm_res.status_code == 200
    assert adm_res.json()["status"] == "RESOLVED"


# -------------------------------------------------------------------------
# 7. 22 Zero-Trust Readiness Gates
# -------------------------------------------------------------------------


def test_22_zero_trust_readiness_gates(client: TestClient, viewer_token: str):
    """Test evaluation of all 22 Zero-Trust Security Readiness Gates."""
    response = client.get(
        "/api/recovery/intelligence/zero-trust/readiness",
        headers={"Authorization": f"Bearer {viewer_token}"},
    )
    assert response.status_code == 200
    gates = response.json()
    assert len(gates) == 22

    gate_ids = {g["gate_id"] for g in gates}
    for i in range(1, 23):
        assert f"GATE-ZT-{i:02d}" in gate_ids

    for g in gates:
        assert g["status"] in ["PASS", "WARN", "FAIL", "BLOCKED"]


# -------------------------------------------------------------------------
# 8. Cryptographic Evidence & Signed Security Report
# -------------------------------------------------------------------------


def test_cryptographic_evidence_chain(client: TestClient, viewer_token: str):
    """Test retrieval of tamper-evident cryptographic evidence nodes."""
    response = client.get(
        "/api/recovery/intelligence/zero-trust/evidence",
        headers={"Authorization": f"Bearer {viewer_token}"},
    )
    assert response.status_code == 200
    nodes = response.json()
    assert len(nodes) >= 1
    assert nodes[0]["evidence_hash"].startswith("sha256:")
    assert nodes[0]["signature"].startswith("sig_zt_sha256:")


def test_signed_security_report_generation(client: TestClient, viewer_token: str):
    """Test generation of cryptographically signed Zero-Trust Security Report."""
    response = client.get(
        "/api/recovery/intelligence/zero-trust/report",
        headers={"Authorization": f"Bearer {viewer_token}"},
    )
    assert response.status_code == 200
    data = response.json()

    assert data["report_id"].startswith("RPT-ZT-")
    assert 0.0 <= data["zero_trust_score"] <= 100.0
    assert data["verification_signature"].startswith("sha256:")
    assert data["financial_isolation_verified"] is True
    assert len(data["readiness_gates"]) == 22
