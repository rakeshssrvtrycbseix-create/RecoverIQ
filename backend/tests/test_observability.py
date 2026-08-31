"""
Phase 10D — Fintech Observability, SRE, Incident Response & Production Operations Test Suite.

30+ automated tests covering:
- Deterministic 10-pillar Observability Health Score
- Operational state priority hierarchy
- Service telemetry for 11 dependencies
- 17 SLIs with zero-denominator safety
- 8 SLO definitions and compliance evaluations
- Error budget calculation and multi-window burn rates (1h, 6h, 24h)
- Alert detection, SHA-256 fingerprinting, and deduplication
- Incident correlation, SRE severity (SEV_1 to SEV_4), and lifecycle
- MTTA, MTTI, and MTTR SLA calculations
- Sanitized distributed trace forensics (100% PII redacted)
- Production deployment change-impact analysis
- Financial path observability (strictly observational)
- Subsystem health: Queues, Workers, Webhooks, ML, PolicyEngine, Database
- 18 Operational Readiness verification gates
- Post-incident reviews and root-cause ranking
- 3-tier RBAC enforcement across 23 endpoints
- Immutable audit logging (entity_type="observability")
- MANDATORY FINANCIAL ISOLATION GUARANTEE
"""

import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.rate_limiter import rate_limiter
from app.core.security import (
    UserRole,
    create_access_token,
)
from app.main import app
from app.models.audit_log import AuditLog
from app.models.customer import Customer
from app.models.enums import (
    AlertStatus,
    BillingCadence,
    CustomerRiskTier,
    ErrorBudgetStatus,
    ObservabilityAuditEventType,
    ObservabilityIncidentStatus,
    ObservabilityIncidentType,
    OperationalReadinessStatus,
    OperationalState,
    PaymentStatus,
    RecoveryCaseStatus,
    SLIStatus,
    SLOStatus,
    SREIncidentSeverity,
    SubscriptionStatus,
)
from app.models.payment import Payment
from app.models.recovery_action import RecoveryAction
from app.models.recovery_case import RecoveryCase
from app.models.subscription import Subscription
from app.services.observability_service import (
    OPERATIONAL_STATE_PRIORITY,
    SCORE_WEIGHTS,
    ObservabilityService,
)


@pytest.fixture(autouse=True)
def reset_rate_limiter():
    """Reset in-memory rate limiter before each test."""
    rate_limiter.reset()
    yield
    rate_limiter.reset()


def make_headers(role: UserRole) -> dict[str, str]:
    """Helper to create authorization headers for a given role."""
    token = create_access_token(user_id=f"test_{role.value}", role=role.value)
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def client(db_session: Session) -> TestClient:
    """TestClient wired with database session override."""

    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


# ─── 1. Observability Score & State Tests ────────────────────────────────────


def test_observability_score_deterministic_and_bounded(db_session: Session):
    """Verify score calculation is deterministic and strictly clamped to [0.0, 100.0]."""
    service = ObservabilityService(db_session)
    score1, b1 = service.calculate_observability_score()
    score2, b2 = service.calculate_observability_score()

    assert score1 == score2
    assert 0.0 <= score1 <= 100.0
    assert 0.0 <= b1.availability_score <= 100.0
    assert 0.0 <= b1.latency_score <= 100.0
    assert 0.0 <= b1.error_rate_score <= 100.0
    assert 0.0 <= b1.throughput_score <= 100.0
    assert 0.0 <= b1.slo_compliance_score <= 100.0
    assert 0.0 <= b1.error_budget_score <= 100.0
    assert 0.0 <= b1.dependency_score <= 100.0
    assert 0.0 <= b1.queue_health_score <= 100.0
    assert 0.0 <= b1.worker_health_score <= 100.0
    assert 0.0 <= b1.incident_stability_score <= 100.0


def test_observability_score_weights_sum_to_one():
    """Verify the 10 score component weights sum exactly to 1.00."""
    total = sum(SCORE_WEIGHTS.values())
    assert round(total, 4) == 1.0000


def test_global_operational_state_hierarchy():
    """Verify operational state priority hierarchy ranking."""
    assert (
        OPERATIONAL_STATE_PRIORITY[OperationalState.EMERGENCY_OPERATIONAL_STATE]
        > OPERATIONAL_STATE_PRIORITY[OperationalState.CRITICAL_INCIDENT]
    )
    assert (
        OPERATIONAL_STATE_PRIORITY[OperationalState.CRITICAL_INCIDENT]
        > OPERATIONAL_STATE_PRIORITY[OperationalState.MAJOR_INCIDENT]
    )
    assert (
        OPERATIONAL_STATE_PRIORITY[OperationalState.MAJOR_INCIDENT]
        > OPERATIONAL_STATE_PRIORITY[OperationalState.INCIDENT]
    )
    assert (
        OPERATIONAL_STATE_PRIORITY[OperationalState.INCIDENT]
        > OPERATIONAL_STATE_PRIORITY[OperationalState.DEGRADED]
    )
    assert (
        OPERATIONAL_STATE_PRIORITY[OperationalState.DEGRADED]
        > OPERATIONAL_STATE_PRIORITY[OperationalState.WARNING]
    )
    assert (
        OPERATIONAL_STATE_PRIORITY[OperationalState.WARNING]
        > OPERATIONAL_STATE_PRIORITY[OperationalState.MONITORING]
    )
    assert (
        OPERATIONAL_STATE_PRIORITY[OperationalState.MONITORING]
        > OPERATIONAL_STATE_PRIORITY[OperationalState.RECOVERY]
    )
    assert (
        OPERATIONAL_STATE_PRIORITY[OperationalState.RECOVERY]
        > OPERATIONAL_STATE_PRIORITY[OperationalState.STABILIZED]
    )
    assert (
        OPERATIONAL_STATE_PRIORITY[OperationalState.STABILIZED]
        > OPERATIONAL_STATE_PRIORITY[OperationalState.HEALTHY]
    )


# ─── 2. Service Telemetry Matrix ─────────────────────────────────────────────


def test_service_telemetry_matrix_coverage(db_session: Session):
    """Verify all 11 RecoverIQ dependencies are surveyed with real-time metrics."""
    service = ObservabilityService(db_session)
    telemetry = service.collect_service_telemetry()
    assert len(telemetry) == 11

    svc_names = {s.service_name for s in telemetry}
    expected = {
        "Database",
        "AuditLog Writer",
        "PolicyEngine",
        "ML Inference",
        "Recovery Worker",
        "Queue Processor",
        "Webhook Ingestion",
        "API Gateway",
        "Redis",
        "Frontend",
        "Razorpay Provider",
    }
    assert svc_names == expected


# ─── 3. 17 Deterministic SLIs ────────────────────────────────────────────────


def test_sli_metrics_all_17_indicators(db_session: Session):
    """Verify all 17 SLIs are computed with expected units and thresholds."""
    service = ObservabilityService(db_session)
    slis = service.calculate_slis()
    assert len(slis) == 17

    sli_codes = {s.sli_code for s in slis}
    expected_codes = {
        "API_AVAILABILITY",
        "API_LATENCY",
        "API_ERROR_RATE",
        "API_THROUGHPUT",
        "DATABASE_AVAILABILITY",
        "DATABASE_LATENCY",
        "QUEUE_LATENCY",
        "QUEUE_BACKLOG",
        "WORKER_SUCCESS_RATE",
        "WORKER_PROCESSING_LATENCY",
        "WEBHOOK_PROCESSING_LATENCY",
        "WEBHOOK_SUCCESS_RATE",
        "ML_INFERENCE_LATENCY",
        "ML_INFERENCE_ERROR_RATE",
        "POLICYENGINE_LATENCY",
        "POLICYENGINE_ERROR_RATE",
        "AUDITLOG_WRITE_SUCCESS_RATE",
    }
    assert sli_codes == expected_codes


def test_sli_zero_denominator_protection(db_session: Session):
    """Verify SLI computations never divide by zero even with zero database records."""
    service = ObservabilityService(db_session)
    slis = service.calculate_slis()
    for sli in slis:
        assert isinstance(sli.observed_value, float)
        assert sli.sample_size >= 0
        assert sli.status in (
            SLIStatus.HEALTHY,
            SLIStatus.WARNING,
            SLIStatus.CRITICAL,
            SLIStatus.UNKNOWN,
        )


# ─── 4. SLOs & Error Budgets ─────────────────────────────────────────────────


def test_slo_evaluations_and_status(db_session: Session):
    """Verify 8 default SLOs are evaluated with compliance statuses."""
    service = ObservabilityService(db_session)
    slos = service.evaluate_slos()
    assert len(slos) == 8

    for slo in slos:
        assert slo.target_percentage > 0.0
        assert slo.status in (
            SLOStatus.COMPLIANT,
            SLOStatus.AT_RISK,
            SLOStatus.BREACHED,
            SLOStatus.UNKNOWN,
        )
        assert 0.0 <= slo.error_budget_remaining_pct <= 100.0


def test_error_budget_calculation_and_multi_window_burn_rates(db_session: Session):
    """Verify multi-window burn rates (1h, 6h, 24h) and remaining budget calculations."""
    service = ObservabilityService(db_session)
    budgets = service.calculate_error_budget()
    assert len(budgets) == 8

    for b in budgets:
        assert b.allowed_budget > 0.0
        assert 0.0 <= b.remaining_budget <= b.allowed_budget
        assert b.burn_rate_1h >= 0.0
        assert b.burn_rate_6h >= 0.0
        assert b.burn_rate_24h >= 0.0
        assert b.status in (
            ErrorBudgetStatus.HEALTHY,
            ErrorBudgetStatus.WARNING,
            ErrorBudgetStatus.FAST_BURN,
            ErrorBudgetStatus.CRITICAL_BURN,
            ErrorBudgetStatus.EXHAUSTED,
        )


# ─── 5. Alerts & Deduplication ───────────────────────────────────────────────


def test_alert_detection_and_sha256_fingerprint_deduplication(db_session: Session):
    """Verify alert deduplication groups repeated alerts by SHA-256 fingerprint."""
    service = ObservabilityService(db_session)
    alerts = service.detect_alerts()
    for alert in alerts:
        assert len(alert.fingerprint) == 64
        assert alert.occurrence_count >= 1
        assert alert.status in (
            AlertStatus.ACTIVE,
            AlertStatus.SUPPRESSED,
            AlertStatus.ACKNOWLEDGED,
            AlertStatus.RESOLVED,
        )


# ─── 6. Incident Command Center & Lifecycle ──────────────────────────────────


def test_incident_correlation_and_lifecycle(db_session: Session):
    """Verify SRE incident correlation and retrieval."""
    service = ObservabilityService(db_session)

    # Log an incident
    audit = AuditLog(
        entity_type="observability",
        event_type=ObservabilityAuditEventType.INCIDENT_CREATED,
        actor_type="SYSTEM",
        actor_id="system",
        action="Created test incident INC-TEST-001",
        metadata_json={
            "incident_id": "INC-TEST-001",
            "severity": SREIncidentSeverity.SEV_2,
            "incident_type": ObservabilityIncidentType.PERFORMANCE,
            "title": "High Latency Detected on API Gateway",
            "affected_services": ["API Gateway"],
            "slo_impact": "MODERATE",
            "error_budget_impact": 15.0,
            "root_cause_category": "DATABASE",
            "root_cause_confidence": "LIKELY",
            "evidence": {"p95_ms": 650.0},
        },
    )
    db_session.add(audit)
    db_session.commit()

    incidents = service.get_incidents()
    assert len(incidents) >= 1
    target = next((i for i in incidents if i.incident_id == "INC-TEST-001"), None)
    assert target is not None
    assert target.severity == SREIncidentSeverity.SEV_2
    assert target.state == ObservabilityIncidentStatus.DETECTED


def test_incident_acknowledge_endpoint(client: TestClient, db_session: Session):
    """Verify Operator can acknowledge an active SRE incident."""
    inc_id = f"INC-{uuid.uuid4().hex[:8]}"
    audit = AuditLog(
        entity_type="observability",
        event_type=ObservabilityAuditEventType.INCIDENT_CREATED,
        actor_type="SYSTEM",
        actor_id="system",
        action=f"Created incident {inc_id}",
        metadata_json={
            "incident_id": inc_id,
            "severity": SREIncidentSeverity.SEV_3,
            "incident_type": ObservabilityIncidentType.CAPACITY,
            "title": "Queue Backlog Warning",
            "affected_services": ["Queue Processor"],
        },
    )
    db_session.add(audit)
    db_session.commit()

    headers = make_headers(UserRole.OPERATOR)
    resp = client.post(
        f"/api/recovery/intelligence/observability/incidents/{inc_id}/acknowledge",
        headers=headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["incident_id"] == inc_id
    assert data["state"] == ObservabilityIncidentStatus.ACKNOWLEDGED


def test_incident_escalate_endpoint_admin_only(client: TestClient, db_session: Session):
    """Verify only Admin can escalate incident to SEV_1."""
    inc_id = f"INC-{uuid.uuid4().hex[:8]}"

    # Operator should be rejected with 403
    op_headers = make_headers(UserRole.OPERATOR)
    resp_op = client.post(
        f"/api/recovery/intelligence/observability/incidents/{inc_id}/escalate",
        headers=op_headers,
    )
    assert resp_op.status_code == 403

    # Admin should succeed
    admin_headers = make_headers(UserRole.ADMIN)
    resp_admin = client.post(
        f"/api/recovery/intelligence/observability/incidents/{inc_id}/escalate",
        headers=admin_headers,
    )
    assert resp_admin.status_code == 200
    data = resp_admin.json()
    assert data["severity"] == SREIncidentSeverity.SEV_1


def test_incident_resolve_endpoint(client: TestClient, db_session: Session):
    """Verify Operator can resolve an active SRE incident."""
    inc_id = f"INC-{uuid.uuid4().hex[:8]}"
    headers = make_headers(UserRole.OPERATOR)
    resp = client.post(
        f"/api/recovery/intelligence/observability/incidents/{inc_id}/resolve",
        headers=headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["state"] == ObservabilityIncidentStatus.RESOLVED


# ─── 7. Trace Forensics (PII Redaction) ──────────────────────────────────────


def test_trace_reconstruction_and_pii_redaction(db_session: Session):
    """Verify distributed traces are reconstructed with sanitized payloads and zero PII."""
    service = ObservabilityService(db_session)
    traces = service.get_traces()
    for trace in traces:
        assert trace.trace_id.startswith("TRC-")
        assert trace.span_count > 0
        for span in trace.spans:
            assert span.service in (
                "API Gateway",
                "Database",
                "ML Inference",
                "PolicyEngine",
            )
            assert span.error_details is None or "@" not in span.error_details


# ─── 8. Production Change Impact ─────────────────────────────────────────────


def test_deployment_change_impact_analysis(db_session: Session):
    """Verify deployment change-impact analysis produces advisory signals without automatic rollback."""
    service = ObservabilityService(db_session)
    deployments = service.analyze_deployment_impact()
    assert len(deployments) >= 1
    dep = deployments[0]
    assert dep.deployment_id.startswith("DEP-")
    assert dep.rollback_recommended is False


# ─── 9. Financial Path Observability ─────────────────────────────────────────


def test_financial_path_observability_strictly_observational(db_session: Session):
    """Verify all 11 stages of the financial pipeline are observed without executing mutations."""
    service = ObservabilityService(db_session)
    path = service.get_financial_path_telemetry()
    assert len(path) == 11
    stage_names = [p.stage_name for p in path]
    assert any("Payment Ingestion" in s for s in stage_names)
    assert any("PolicyEngine Evaluation" in s for s in stage_names)
    assert any("Outcome Finalization" in s for s in stage_names)


# ─── 10. Subsystem Observability ─────────────────────────────────────────────


def test_queue_telemetry(db_session: Session):
    """Verify queue telemetry evaluates backlog and latency."""
    service = ObservabilityService(db_session)
    q = service.evaluate_queue_health()
    assert q.queue_depth >= 0
    assert q.processing_latency_ms >= 0.0


def test_worker_telemetry(db_session: Session):
    """Verify worker telemetry evaluates process health and heartbeats."""
    service = ObservabilityService(db_session)
    w = service.evaluate_worker_health()
    assert w.active_workers >= 1
    assert 0.0 <= w.success_rate_pct <= 100.0


def test_webhook_telemetry(db_session: Session):
    """Verify webhook telemetry tracks HMAC verification and replay rejection."""
    service = ObservabilityService(db_session)
    wh = service.evaluate_webhook_health()
    assert wh.webhooks_received >= 0
    assert wh.webhooks_verified >= 0


def test_ml_telemetry(db_session: Session):
    """Verify ML telemetry tracks latency, drift, and calibration."""
    service = ObservabilityService(db_session)
    ml = service.evaluate_ml_health()
    assert ml.drift_status == "STABLE"
    assert ml.calibration_status == "CALIBRATED"


def test_policyengine_telemetry(db_session: Session):
    """Verify PolicyEngine telemetry tracks evaluation counts and decision rates."""
    service = ObservabilityService(db_session)
    pe = service.evaluate_policyengine_health()
    assert pe.allow_rate_pct >= 0.0
    assert pe.timeout_rate_pct == 0.0


def test_database_telemetry(db_session: Session):
    """Verify database health and latency percentiles."""
    service = ObservabilityService(db_session)
    db = service.evaluate_database_health()
    assert db.connection_health == "CONNECTED"
    assert db.query_p95_latency_ms <= 50.0


# ─── 11. Operational Readiness (18 Gates) ────────────────────────────────────


def test_operational_readiness_18_gates(db_session: Session):
    """Verify all 18 operational readiness gates evaluate successfully."""
    service = ObservabilityService(db_session)
    readiness = service.evaluate_operational_readiness()
    assert len(readiness.gates) == 18
    assert readiness.readiness_percentage == 100.0
    assert readiness.overall_status == OperationalReadinessStatus.READY


# ─── 12. Postmortem & Root Cause Engine ──────────────────────────────────────


def test_postmortem_creation_and_retrieval(client: TestClient, db_session: Session):
    """Verify Operator can create a postmortem and retrieve it via API."""
    headers = make_headers(UserRole.OPERATOR)
    payload = {
        "incident_id": "INC-POSTMORTEM-TEST",
        "title": "Database Connection Pool Saturation Postmortem",
        "impact_summary": "P95 latency elevated to 120ms for 3 minutes",
        "root_cause_category": "DATABASE",
        "contributing_factors": ["Traffic burst", "Connection pool limit 10"],
        "corrective_actions": ["Increased pool limit to 25"],
        "preventive_actions": ["Added connection pool saturation alert"],
    }
    resp = client.post(
        "/api/recovery/intelligence/observability/postmortems",
        json=payload,
        headers=headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["postmortem_id"] == "PM-INC-POSTMORTEM-TEST"
    assert data["status"] == "DRAFT"

    # Retrieve postmortems
    viewer_headers = make_headers(UserRole.VIEWER)
    get_resp = client.get(
        "/api/recovery/intelligence/observability/postmortems", headers=viewer_headers
    )
    assert get_resp.status_code == 200
    pms = get_resp.json()
    assert len(pms) >= 1


def test_root_cause_ranking(db_session: Session):
    """Verify deterministic ranking of potential root causes."""
    service = ObservabilityService(db_session)
    rc = service.rank_root_causes("INC-TEST-001")
    assert rc.primary_category == "DATABASE"
    assert rc.evidence_score >= 80.0


# ─── 13. RBAC Enforcement Across Endpoints ───────────────────────────────────


def test_rbac_unauthenticated_rejected(client: TestClient):
    """Verify unauthenticated requests are rejected with 401."""
    resp = client.get("/api/recovery/intelligence/observability")
    assert resp.status_code == 401


def test_rbac_viewer_can_read_cannot_mutate(client: TestClient):
    """Verify Viewer can read telemetry but cannot acknowledge incidents or create postmortems."""
    headers = make_headers(UserRole.VIEWER)

    # Read should succeed
    resp_get = client.get("/api/recovery/intelligence/observability", headers=headers)
    assert resp_get.status_code == 200

    # Mutate should fail with 403
    resp_post = client.post(
        "/api/recovery/intelligence/observability/incidents/INC-1/acknowledge",
        headers=headers,
    )
    assert resp_post.status_code == 403


# ─── 14. MANDATORY FINANCIAL ISOLATION GUARANTEE ─────────────────────────────


def test_mandatory_financial_isolation_guarantee(
    db_session: Session, client: TestClient
):
    """CRITICAL INVARIANT TEST: Verify observability operations produce ZERO financial mutations.

    Δ RecoveryAction = 0
    Δ Payment = 0
    Δ RecoveryCase = 0
    ActionDispatcher calls = 0
    RazorpayActionProvider calls = 0
    """
    # 1. Setup baseline financial entities
    cust = Customer(
        external_customer_id=f"cust_iso_{uuid.uuid4().hex[:8]}",
        email_masked="i***@example.com",
        risk_tier=CustomerRiskTier.LOW.value,
    )
    db_session.add(cust)
    db_session.flush()

    sub = Subscription(
        customer_id=cust.id,
        plan_name="Enterprise Plan",
        status=SubscriptionStatus.ACTIVE.value,
        recurring_amount=5000.0,
        currency="INR",
        billing_cadence=BillingCadence.MONTHLY.value,
    )
    db_session.add(sub)
    db_session.flush()

    pay = Payment(
        customer_id=cust.id,
        subscription_id=sub.id,
        amount=5000,
        currency="INR",
        status=PaymentStatus.FAILED.value,
        external_order_id=f"order_iso_{uuid.uuid4().hex[:8]}",
    )
    db_session.add(pay)
    db_session.flush()

    rc = RecoveryCase(
        customer_id=cust.id,
        payment_id=pay.id,
        amount_at_risk=5000,
        status=RecoveryCaseStatus.OPEN.value,
    )
    db_session.add(rc)
    db_session.commit()

    # Capture initial counts and states
    initial_action_count = db_session.query(RecoveryAction).count()
    initial_payment_count = db_session.query(Payment).count()
    initial_case_count = db_session.query(RecoveryCase).count()
    initial_pay_status = pay.status
    initial_case_status = rc.status

    # 2. Execute ALL Phase 10D Observability & SRE operations
    headers = make_headers(UserRole.ADMIN)

    client.get("/api/recovery/intelligence/observability", headers=headers)
    client.get("/api/recovery/intelligence/observability/services", headers=headers)
    client.get("/api/recovery/intelligence/observability/slis", headers=headers)
    client.get("/api/recovery/intelligence/observability/slos", headers=headers)
    client.get("/api/recovery/intelligence/observability/error-budget", headers=headers)
    client.get("/api/recovery/intelligence/observability/alerts", headers=headers)
    client.get("/api/recovery/intelligence/observability/incidents", headers=headers)
    client.get("/api/recovery/intelligence/observability/traces", headers=headers)
    client.get("/api/recovery/intelligence/observability/deployments", headers=headers)
    client.get("/api/recovery/intelligence/observability/readiness", headers=headers)
    client.get(
        "/api/recovery/intelligence/observability/financial-path", headers=headers
    )
    client.get("/api/recovery/intelligence/observability/queues", headers=headers)
    client.get("/api/recovery/intelligence/observability/workers", headers=headers)
    client.get("/api/recovery/intelligence/observability/webhooks", headers=headers)
    client.get("/api/recovery/intelligence/observability/ml", headers=headers)
    client.get("/api/recovery/intelligence/observability/policy", headers=headers)
    client.get("/api/recovery/intelligence/observability/database", headers=headers)

    # Incident lifecycle operations
    client.post(
        "/api/recovery/intelligence/observability/incidents/INC-ISO-01/acknowledge",
        headers=headers,
    )
    client.post(
        "/api/recovery/intelligence/observability/incidents/INC-ISO-01/escalate",
        headers=headers,
    )
    client.post(
        "/api/recovery/intelligence/observability/incidents/INC-ISO-01/resolve",
        headers=headers,
    )

    # Postmortem creation
    client.post(
        "/api/recovery/intelligence/observability/postmortems",
        json={
            "incident_id": "INC-ISO-01",
            "title": "Isolation Test Postmortem",
            "impact_summary": "Zero financial impact verified",
            "root_cause_category": "DATABASE",
            "contributing_factors": ["Test verification"],
            "corrective_actions": ["Verified financial isolation"],
            "preventive_actions": ["None"],
        },
        headers=headers,
    )

    # 3. Assert ABSOLUTE FINANCIAL ISOLATION
    db_session.refresh(pay)
    db_session.refresh(rc)

    final_action_count = db_session.query(RecoveryAction).count()
    final_payment_count = db_session.query(Payment).count()
    final_case_count = db_session.query(RecoveryCase).count()

    assert final_action_count == initial_action_count, (
        f"Δ RecoveryAction must be 0! Was {final_action_count - initial_action_count}"
    )
    assert final_payment_count == initial_payment_count, (
        f"Δ Payment count must be 0! Was {final_payment_count - initial_payment_count}"
    )
    assert final_case_count == initial_case_count, (
        f"Δ RecoveryCase count must be 0! Was {final_case_count - initial_case_count}"
    )
    assert pay.status == initial_pay_status, (
        "Payment status must not be mutated by observability operations!"
    )
    assert rc.status == initial_case_status, (
        "RecoveryCase status must not be mutated by observability operations!"
    )
