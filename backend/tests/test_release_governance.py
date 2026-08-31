"""Automated test suite for Phase 10G: Fintech Architecture Governance, Change Management,

Release Safety & Deployment Assurance.
"""

import re

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.security import UserRole, create_access_token
from app.models.audit_log import AuditLog
from app.models.enums import (
    ChangeRiskLevel,
    ChangeStatus,
    ChangeType,
    CompatibilityStatus,
    DeploymentStrategy,
    GovernanceDecision,
    ReleaseDecision,
    ReleaseHealth,
)
from app.services.release_governance_service import ReleaseGovernanceService


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
# 1. Governance Summary, Score Formula & State Hierarchy
# -------------------------------------------------------------------------


def test_governance_summary_score_and_breakdown(client: TestClient, viewer_token: str):
    """Test 0-100 Governance Score formula calculation, bounds, and classification."""
    response = client.get(
        "/api/recovery/intelligence/release-governance",
        headers={"Authorization": f"Bearer {viewer_token}"},
    )
    assert response.status_code == 200
    data = response.json()

    assert "governance_score" in data
    assert 0.0 <= data["governance_score"] <= 100.0
    assert data["classification"] in [e.value for e in ReleaseHealth]
    assert data["global_state"] in [e.value for e in ReleaseDecision]
    assert data["open_changes_count"] >= 0
    assert data["release_candidates_count"] >= 0
    assert data["readiness_score"] == 100.0
    assert "PolicyEngine" in data["disclaimer"]


def test_governance_score_math_bounds(db_session: Session):
    """Verify 10-factor mathematical weighting bounds."""
    service = ReleaseGovernanceService(db_session)
    summary = service.get_governance_summary()

    assert isinstance(summary.governance_score, float)
    assert 0.0 <= summary.governance_score <= 100.0
    assert summary.classification in (ReleaseHealth.EXCELLENT, ReleaseHealth.HEALTHY)
    assert summary.global_state in (ReleaseDecision.GO, ReleaseDecision.CONDITIONAL_GO)


# -------------------------------------------------------------------------
# 2. Change Request & Risk Assessment Engine
# -------------------------------------------------------------------------


def test_list_change_requests(client: TestClient, viewer_token: str):
    """Test listing all governed change requests."""
    response = client.get(
        "/api/recovery/intelligence/release-governance/changes",
        headers={"Authorization": f"Bearer {viewer_token}"},
    )
    assert response.status_code == 200
    changes = response.json()
    assert isinstance(changes, list)
    assert len(changes) >= 4

    first = changes[0]
    assert "change_id" in first
    assert "title" in first
    assert "risk_level" in first
    assert "risk_assessment" in first
    assert "risk_score" in first["risk_assessment"]


def test_create_change_request_low_risk(
    client: TestClient, operator_token: str, db_session: Session
):
    """Test submitting a low-risk non-financial change request."""
    payload = {
        "title": "Optimized Redis Command Buffer Caching",
        "description": "Increases pipeline cache buffer size from 64KB to 128KB.",
        "change_type": "CONFIGURATION",
        "affected_services": ["Redis Cache"],
        "is_financial_path": False,
        "requires_downtime": False,
        "rollback_procedure": "Revert environment variable REDIS_BUFFER_KB to 64.",
    }

    response = client.post(
        "/api/recovery/intelligence/release-governance/changes",
        json=payload,
        headers={"Authorization": f"Bearer {operator_token}"},
    )
    assert response.status_code == 201
    created = response.json()

    assert created["change_id"].startswith("CR-")
    assert created["title"] == payload["title"]
    assert created["risk_level"] in (
        ChangeRiskLevel.LOW.value,
        ChangeRiskLevel.MEDIUM.value,
    )
    assert created["is_financial_path"] is False
    assert created["status"] == ChangeStatus.PROPOSED.value

    # Verify AuditLog row
    log_entry = (
        db_session.query(AuditLog)
        .filter(AuditLog.entity_type == "change_request")
        .order_by(AuditLog.created_at.desc())
        .first()
    )
    assert log_entry is not None
    assert log_entry.metadata_json.get("change_id") == created["change_id"]


def test_create_change_request_financial_path_elevated_risk(
    client: TestClient, operator_token: str
):
    """Test that financial path changes automatically receive elevated risk."""
    payload = {
        "title": "PolicyEngine Dynamic Escalation Rule Refactor",
        "description": "Modifies escalation eligibility criteria in authoritative PolicyEngine.",
        "change_type": "FEATURE",
        "affected_services": ["Policy Engine", "Recovery Worker"],
        "is_financial_path": True,
        "requires_downtime": False,
        "rollback_procedure": "Revert to PolicyEngine AST commit hash 9840ef.",
    }

    response = client.post(
        "/api/recovery/intelligence/release-governance/changes",
        json=payload,
        headers={"Authorization": f"Bearer {operator_token}"},
    )
    assert response.status_code == 201
    created = response.json()

    assert created["is_financial_path"] is True
    assert created["risk_level"] in (
        ChangeRiskLevel.HIGH.value,
        ChangeRiskLevel.CRITICAL.value,
    )
    assert created["risk_assessment"]["financial_risk_multiplier"] > 1.0
    assert any(
        "financial recovery path" in rf
        for rf in created["risk_assessment"]["risk_factors"]
    )


def test_get_change_request_by_id(client: TestClient, viewer_token: str):
    """Test fetching a specific change request by change_id."""
    response = client.get(
        "/api/recovery/intelligence/release-governance/changes/CR-2026-0801",
        headers={"Authorization": f"Bearer {viewer_token}"},
    )
    assert response.status_code == 200
    change = response.json()
    assert change["change_id"] == "CR-2026-0801"
    assert change["change_type"] == ChangeType.ML_MODEL.value


def test_get_change_request_not_found(client: TestClient, viewer_token: str):
    """Test 404 for unknown change request ID."""
    response = client.get(
        "/api/recovery/intelligence/release-governance/changes/CR-NONEXISTENT",
        headers={"Authorization": f"Bearer {viewer_token}"},
    )
    assert response.status_code == 404


def test_get_change_risk_assessment(client: TestClient, viewer_token: str):
    """Test retrieving risk breakdown for a change request."""
    response = client.get(
        "/api/recovery/intelligence/release-governance/risk/CR-2026-0803",
        headers={"Authorization": f"Bearer {viewer_token}"},
    )
    assert response.status_code == 200
    risk = response.json()
    assert "risk_score" in risk
    assert "risk_level" in risk
    assert "risk_factors" in risk
    assert "mitigation_recommendations" in risk


# -------------------------------------------------------------------------
# 3. 11-Service Dependency Coupling & Architecture Findings
# -------------------------------------------------------------------------


def test_dependency_impact_graph(client: TestClient, viewer_token: str):
    """Test retrieving 11-service coupling graph and blast radius."""
    response = client.get(
        "/api/recovery/intelligence/release-governance/dependencies",
        headers={"Authorization": f"Bearer {viewer_token}"},
    )
    assert response.status_code == 200
    deps = response.json()
    assert isinstance(deps, list)
    assert len(deps) >= 6

    # Verify critical financial path dependency exists
    fin_deps = [d for d in deps if d["is_financial_path"]]
    assert len(fin_deps) >= 3
    assert any(
        d["source_service"] == "Policy Engine"
        and d["target_service"] == "Recovery Worker"
        for d in fin_deps
    )


def test_architecture_findings(client: TestClient, viewer_token: str):
    """Test retrieving active architecture findings and anti-patterns."""
    response = client.get(
        "/api/recovery/intelligence/release-governance/architecture-findings",
        headers={"Authorization": f"Bearer {viewer_token}"},
    )
    assert response.status_code == 200
    findings = response.json()
    assert isinstance(findings, list)
    assert len(findings) >= 2
    assert all("finding_id" in f and "remediation" in f for f in findings)


# -------------------------------------------------------------------------
# 4. API & Database Compatibility Governance
# -------------------------------------------------------------------------


def test_api_compatibility_report(client: TestClient, viewer_token: str):
    """Test API backward compatibility validation."""
    response = client.get(
        "/api/recovery/intelligence/release-governance/api-compatibility",
        headers={"Authorization": f"Bearer {viewer_token}"},
    )
    assert response.status_code == 200
    report = response.json()
    assert (
        report["compatibility_status"] == CompatibilityStatus.BACKWARD_COMPATIBLE.value
    )
    assert report["breaking_changes_count"] == 0
    assert report["total_endpoints"] >= 40


def test_database_compatibility_report_zero_migration(
    client: TestClient, viewer_token: str
):
    """Test database schema compatibility under the zero-migration invariant."""
    response = client.get(
        "/api/recovery/intelligence/release-governance/database-compatibility",
        headers={"Authorization": f"Bearer {viewer_token}"},
    )
    assert response.status_code == 200
    report = response.json()
    assert (
        report["compatibility_status"] == CompatibilityStatus.BACKWARD_COMPATIBLE.value
    )
    assert report["is_migration_required"] is False
    assert report["schema_modifications_count"] == 0


# -------------------------------------------------------------------------
# 5. Configuration Drift & Feature Flag Governance
# -------------------------------------------------------------------------


def test_configuration_drift_detection(client: TestClient, viewer_token: str):
    """Test configuration parity and drift detection."""
    response = client.get(
        "/api/recovery/intelligence/release-governance/configuration-drift",
        headers={"Authorization": f"Bearer {viewer_token}"},
    )
    assert response.status_code == 200
    drifts = response.json()
    assert isinstance(drifts, list)
    assert len(drifts) >= 4
    assert all("key" in d and "expected_value_masked" in d for d in drifts)


def test_configuration_drift_secret_masking(client: TestClient, viewer_token: str):
    """Verify that configuration drift endpoint never exposes raw secrets."""
    response = client.get(
        "/api/recovery/intelligence/release-governance/configuration-drift",
        headers={"Authorization": f"Bearer {viewer_token}"},
    )
    assert response.status_code == 200
    text = response.text

    # Verify no raw secret leaks
    assert "razorpay_secret_" not in text.lower()
    assert "jwt_secret_key_" not in text.lower()
    assert "supersecret" not in text.lower()


def test_list_feature_flags(client: TestClient, viewer_token: str):
    """Test listing governed feature flags."""
    response = client.get(
        "/api/recovery/intelligence/release-governance/feature-flags",
        headers={"Authorization": f"Bearer {viewer_token}"},
    )
    assert response.status_code == 200
    flags = response.json()
    assert isinstance(flags, list)
    assert len(flags) >= 4

    flag = flags[0]
    assert "flag_id" in flag
    assert "rollout_percentage" in flag
    assert "is_financial_path" in flag


def test_update_feature_flag_rollout(
    client: TestClient, operator_token: str, db_session: Session
):
    """Test updating feature flag rollout percentage."""
    payload = {
        "status": "ACTIVE",
        "rollout_percentage": 75,
        "rationale": "Canary observation metrics verified with zero errors.",
    }

    response = client.post(
        "/api/recovery/intelligence/release-governance/feature-flags/FF-002",
        json=payload,
        headers={"Authorization": f"Bearer {operator_token}"},
    )
    assert response.status_code == 200
    updated = response.json()
    assert updated["flag_id"] == "FF-002"
    assert updated["rollout_percentage"] == 75

    # Verify AuditLog update entry
    log_entry = (
        db_session.query(AuditLog)
        .filter(AuditLog.entity_type == "feature_flag", AuditLog.action == "update")
        .order_by(AuditLog.created_at.desc())
        .first()
    )
    assert log_entry is not None
    assert log_entry.metadata_json.get("flag_id") == "FF-002"


def test_update_feature_flag_not_found(client: TestClient, operator_token: str):
    """Test 404 when updating non-existent feature flag."""
    payload = {
        "status": "ACTIVE",
        "rollout_percentage": 50,
        "rationale": "Test invalid flag",
    }
    response = client.post(
        "/api/recovery/intelligence/release-governance/feature-flags/FF-NONEXISTENT",
        json=payload,
        headers={"Authorization": f"Bearer {operator_token}"},
    )
    assert response.status_code == 404


# -------------------------------------------------------------------------
# 6. Release Candidates & 18 Deterministic Readiness Gates
# -------------------------------------------------------------------------


def test_release_candidates_list(client: TestClient, viewer_token: str):
    """Test listing release candidates."""
    response = client.get(
        "/api/recovery/intelligence/release-governance/releases",
        headers={"Authorization": f"Bearer {viewer_token}"},
    )
    assert response.status_code == 200
    rcs = response.json()
    assert isinstance(rcs, list)
    assert len(rcs) >= 2
    assert "rc_id" in rcs[0]
    assert "version" in rcs[0]
    assert "readiness_summary" in rcs[0]


def test_create_release_candidate(
    client: TestClient, operator_token: str, db_session: Session
):
    """Test creating a new release candidate."""
    payload = {
        "version": "v2.11.0-rc1",
        "commit_sha": "f1e2d3c4b5a69788091a2b3c4d5e6f7a8b9c0d1e",
        "deployment_strategy": "CANARY",
        "change_request_ids": ["CR-2026-0801", "CR-2026-0802"],
    }

    response = client.post(
        "/api/recovery/intelligence/release-governance/releases",
        json=payload,
        headers={"Authorization": f"Bearer {operator_token}"},
    )
    assert response.status_code == 201
    rc = response.json()
    assert rc["version"] == "v2.11.0-rc1"
    assert rc["deployment_strategy"] == DeploymentStrategy.CANARY.value
    assert rc["decision"] in (
        ReleaseDecision.GO.value,
        ReleaseDecision.CONDITIONAL_GO.value,
    )

    # Verify AuditLog entry
    log_entry = (
        db_session.query(AuditLog)
        .filter(AuditLog.entity_type == "release_candidate")
        .order_by(AuditLog.created_at.desc())
        .first()
    )
    assert log_entry is not None
    assert log_entry.metadata_json.get("rc_id") == rc["rc_id"]


def test_get_release_candidate_by_id(client: TestClient, viewer_token: str):
    """Test getting release candidate details by ID."""
    response = client.get(
        "/api/recovery/intelligence/release-governance/releases/RC-2026.08.30-v2.10.0",
        headers={"Authorization": f"Bearer {viewer_token}"},
    )
    assert response.status_code == 200
    rc = response.json()
    assert rc["rc_id"] == "RC-2026.08.30-v2.10.0"
    assert rc["version"] == "v2.10.0"


def test_get_release_candidate_not_found(client: TestClient, viewer_token: str):
    """Test 404 for non-existent release candidate."""
    response = client.get(
        "/api/recovery/intelligence/release-governance/releases/RC-NONEXISTENT",
        headers={"Authorization": f"Bearer {viewer_token}"},
    )
    assert response.status_code == 404


def test_18_release_readiness_gates_verification(client: TestClient, viewer_token: str):
    """Test that all 18 deterministic release readiness gates are evaluated."""
    response = client.get(
        "/api/recovery/intelligence/release-governance/readiness",
        headers={"Authorization": f"Bearer {viewer_token}"},
    )
    assert response.status_code == 200
    summary = response.json()

    assert summary["total_gates"] == 18
    assert summary["passed_gates"] == 18
    assert summary["overall_status"] == "PASS"

    gates = summary["gates"]
    assert len(gates) == 18

    # Verify key mandatory gates
    gate_codes = [g["code"] for g in gates]
    assert "GATE-REL-01" in gate_codes  # Change Traceability
    assert "GATE-REL-02" in gate_codes  # Test Coverage
    assert "GATE-REL-03" in gate_codes  # Financial Isolation
    assert "GATE-REL-04" in gate_codes  # Security Validation
    assert "GATE-REL-05" in gate_codes  # Compliance Validation
    assert "GATE-REL-06" in gate_codes  # Data Governance
    assert "GATE-REL-07" in gate_codes  # Performance SLAs
    assert "GATE-REL-08" in gate_codes  # Operational Resilience
    assert "GATE-REL-09" in gate_codes  # Observability Instrumentation
    assert "GATE-REL-10" in gate_codes  # Dependency Safety
    assert "GATE-REL-11" in gate_codes  # API Compatibility
    assert "GATE-REL-12" in gate_codes  # Database Compatibility
    assert "GATE-REL-13" in gate_codes  # Configuration Integrity
    assert "GATE-REL-14" in gate_codes  # Rollback Readiness
    assert "GATE-REL-15" in gate_codes  # Human Governance
    assert "GATE-REL-16" in gate_codes  # Canary Readiness
    assert "GATE-REL-17" in gate_codes  # Post-Deployment Verification
    assert "GATE-REL-18" in gate_codes  # Financial Path Protection


# -------------------------------------------------------------------------
# 7. Canary Evaluation & Rollback Readiness
# -------------------------------------------------------------------------


def test_canary_evaluation_recommendation(client: TestClient, viewer_token: str):
    """Test canary comparison telemetry and advisory recommendation."""
    response = client.get(
        "/api/recovery/intelligence/release-governance/canary",
        headers={"Authorization": f"Bearer {viewer_token}"},
    )
    assert response.status_code == 200
    canary = response.json()

    assert canary["canary_version"] == "v2.10.0"
    assert canary["traffic_percentage"] == 10
    assert canary["canary_p95_ms"] <= canary["baseline_p95_ms"]
    assert canary["decision"] in (
        ReleaseDecision.GO.value,
        ReleaseDecision.CONDITIONAL_GO.value,
    )
    assert len(canary["recommendation_reason"]) > 10


def test_rollback_readiness_verification(client: TestClient, viewer_token: str):
    """Test rollback reversibility and recovery time estimation."""
    response = client.get(
        "/api/recovery/intelligence/release-governance/rollback-readiness",
        headers={"Authorization": f"Bearer {viewer_token}"},
    )
    assert response.status_code == 200
    rollback = response.json()

    assert rollback["previous_version_available"] is True
    assert rollback["artifact_digest"].startswith("sha256:")
    assert rollback["database_reversible"] is True
    assert rollback["config_reversible"] is True
    assert rollback["estimated_recovery_time_sec"] <= 60
    assert rollback["readiness_status"] == "ROLLBACK_READY"


# -------------------------------------------------------------------------
# 8. Human Approval Workflow
# -------------------------------------------------------------------------


def test_human_release_approval_workflow(
    client: TestClient, admin_token: str, db_session: Session
):
    """Test human governance sign-off approval on release candidate."""
    payload = {
        "decision": "APPROVE",
        "comments": "All 18 release readiness gates verified. Approved for 10% canary progression.",
    }

    response = client.post(
        "/api/recovery/intelligence/release-governance/approve/RC-2026.08.30-v2.10.0",
        json=payload,
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 200
    approval = response.json()

    assert approval["release_id"] == "RC-2026.08.30-v2.10.0"
    assert approval["decision"] == GovernanceDecision.APPROVE.value
    assert approval["approver_role"] == UserRole.ADMIN.value

    # Verify AuditLog entry
    log_entry = (
        db_session.query(AuditLog)
        .filter(AuditLog.entity_type == "release_approval")
        .order_by(AuditLog.created_at.desc())
        .first()
    )
    assert log_entry is not None
    assert log_entry.metadata_json.get("approval_id") == approval["approval_id"]


def test_human_release_rejection_workflow(client: TestClient, admin_token: str):
    """Test human governance rejection on release candidate."""
    payload = {
        "decision": "REJECT",
        "comments": "Rejected pending additional staging benchmark evidence.",
    }

    response = client.post(
        "/api/recovery/intelligence/release-governance/approve/RC-2026.08.30-v2.10.0",
        json=payload,
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 200
    approval = response.json()
    assert approval["decision"] == GovernanceDecision.REJECT.value


def test_human_approval_not_found(client: TestClient, admin_token: str):
    """Test 404 when approving unknown release candidate."""
    payload = {
        "decision": "APPROVE",
        "comments": "Approve invalid RC",
    }
    response = client.post(
        "/api/recovery/intelligence/release-governance/approve/RC-NONEXISTENT",
        json=payload,
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 404


# -------------------------------------------------------------------------
# 9. Release Lineage DAG & Incident Correlation
# -------------------------------------------------------------------------


def test_10_node_release_lineage_dag(client: TestClient, viewer_token: str):
    """Test retrieving the 10-stage cryptographic release lineage DAG."""
    response = client.get(
        "/api/recovery/intelligence/release-governance/lineage",
        headers={"Authorization": f"Bearer {viewer_token}"},
    )
    assert response.status_code == 200
    nodes = response.json()

    assert isinstance(nodes, list)
    assert len(nodes) == 10

    stages = [n["stage"] for n in nodes]
    assert stages == [
        "CHANGE_REQUEST",
        "RISK_ASSESSMENT",
        "ARCHITECTURE_ANALYSIS",
        "DEPENDENCY_ANALYSIS",
        "TEST_EVIDENCE",
        "RELEASE_CANDIDATE",
        "GOVERNANCE_APPROVAL",
        "CANARY_OBSERVATION",
        "PRODUCTION_DEPLOYMENT",
        "PRODUCTION_VERIFICATION",
    ]
    assert all(len(n["evidence_hash"]) == 64 for n in nodes)


def test_release_incident_correlation(client: TestClient, viewer_token: str):
    """Test retrieving release-correlated incidents."""
    response = client.get(
        "/api/recovery/intelligence/release-governance/incidents",
        headers={"Authorization": f"Bearer {viewer_token}"},
    )
    assert response.status_code == 200
    incidents = response.json()
    assert isinstance(incidents, list)
    assert len(incidents) >= 1
    assert "incident_id" in incidents[0]


# -------------------------------------------------------------------------
# 10. Signed Governance Audit Report
# -------------------------------------------------------------------------


def test_generate_release_governance_report_with_signature(
    client: TestClient, viewer_token: str
):
    """Test generating signed release governance report with SHA-256 integrity signature."""
    response = client.get(
        "/api/recovery/intelligence/release-governance/report",
        headers={"Authorization": f"Bearer {viewer_token}"},
    )
    assert response.status_code == 200
    report = response.json()

    assert report["report_id"].startswith("RPT-REL-")
    assert report["verification_signature"].startswith("sha256:")
    assert report["isolation_verified"] is True
    assert len(report["readiness_gates"]) == 18
    assert len(report["change_requests"]) >= 4
    assert len(report["config_drift"]) >= 4
    assert len(report["feature_flags"]) >= 4


# -------------------------------------------------------------------------
# 11. Security, RBAC & Zero-PII Guarantees
# -------------------------------------------------------------------------


def test_rbac_unauthenticated_requests(client: TestClient):
    """Verify unauthenticated requests are rejected with 401."""
    endpoints = [
        "/api/recovery/intelligence/release-governance",
        "/api/recovery/intelligence/release-governance/changes",
        "/api/recovery/intelligence/release-governance/dependencies",
        "/api/recovery/intelligence/release-governance/readiness",
        "/api/recovery/intelligence/release-governance/canary",
        "/api/recovery/intelligence/release-governance/report",
    ]
    for ep in endpoints:
        resp = client.get(ep)
        assert resp.status_code in (401, 403)


def test_rbac_viewer_vs_operator_vs_admin_permissions(
    client: TestClient, viewer_token: str, operator_token: str, admin_token: str
):
    """Verify RBAC role separation between VIEWER, OPERATOR, and ADMIN."""
    # 1. Viewer cannot create change requests (403), but Operator can (201)
    change_payload = {
        "title": "RBAC Test Change",
        "description": "Testing role separation on change submission.",
        "change_type": "BUGFIX",
        "affected_services": ["API Gateway"],
        "is_financial_path": False,
        "requires_downtime": False,
        "rollback_procedure": "Revert commit",
    }
    resp_viewer_post = client.post(
        "/api/recovery/intelligence/release-governance/changes",
        json=change_payload,
        headers={"Authorization": f"Bearer {viewer_token}"},
    )
    assert resp_viewer_post.status_code == 403

    resp_op_post = client.post(
        "/api/recovery/intelligence/release-governance/changes",
        json=change_payload,
        headers={"Authorization": f"Bearer {operator_token}"},
    )
    assert resp_op_post.status_code == 201

    # 2. Operator cannot approve release candidate (403), but Admin can (200)
    approval_payload = {"decision": "APPROVE", "comments": "Admin sign-off"}
    resp_op_approve = client.post(
        "/api/recovery/intelligence/release-governance/approve/RC-2026.08.30-v2.10.0",
        json=approval_payload,
        headers={"Authorization": f"Bearer {operator_token}"},
    )
    assert resp_op_approve.status_code == 403

    resp_admin_approve = client.post(
        "/api/recovery/intelligence/release-governance/approve/RC-2026.08.30-v2.10.0",
        json=approval_payload,
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp_admin_approve.status_code == 200


def test_zero_pii_across_all_release_governance_endpoints(
    client: TestClient, viewer_token: str
):
    """Verify that all Phase 10G responses are free of customer PII and credentials."""
    endpoints = [
        "/api/recovery/intelligence/release-governance",
        "/api/recovery/intelligence/release-governance/changes",
        "/api/recovery/intelligence/release-governance/dependencies",
        "/api/recovery/intelligence/release-governance/architecture-findings",
        "/api/recovery/intelligence/release-governance/api-compatibility",
        "/api/recovery/intelligence/release-governance/database-compatibility",
        "/api/recovery/intelligence/release-governance/configuration-drift",
        "/api/recovery/intelligence/release-governance/feature-flags",
        "/api/recovery/intelligence/release-governance/releases",
        "/api/recovery/intelligence/release-governance/readiness",
        "/api/recovery/intelligence/release-governance/canary",
        "/api/recovery/intelligence/release-governance/rollback-readiness",
        "/api/recovery/intelligence/release-governance/lineage",
        "/api/recovery/intelligence/release-governance/incidents",
        "/api/recovery/intelligence/release-governance/report",
    ]

    card_pattern = re.compile(r"\b(?:4[0-9]{12}(?:[0-9]{3})?|5[1-5][0-9]{14})\b")

    for ep in endpoints:
        res = client.get(ep, headers={"Authorization": f"Bearer {viewer_token}"})
        assert res.status_code == 200
        text = res.text

        assert "password" not in text.lower()
        assert "secret_key" not in text.lower()
        assert "rzp_live_" not in text.lower()
        assert not card_pattern.search(text)
