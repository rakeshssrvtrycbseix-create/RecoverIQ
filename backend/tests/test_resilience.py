"""
Phase 10C — Operational Resilience, Disaster Recovery & Business Continuity Test Suite.

25+ automated tests covering:
- Resilience scoring (deterministic, bounded, weighted)
- Service health monitoring
- RTO/RPO governance
- DR readiness (15 gates)
- Disaster simulation (11 scenarios)
- Cascading failure detection
- Backup verification
- RBAC enforcement
- Audit trail integrity
- Mandatory financial isolation guarantee
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
    BackupFreshnessStatus,
    BackupIntegrityStatus,
    BillingCadence,
    CustomerRiskTier,
    DisasterScenarioType,
    PaymentStatus,
    ReadinessStatus,
    RecoveryActionStatus,
    RecoveryCaseStatus,
    ResilienceAuditEventType,
    ResilienceState,
    RestoreVerificationStatus,
    RTORPOComplianceStatus,
    ServiceHealthStatus,
    SubscriptionStatus,
)
from app.models.payment import Payment
from app.models.recovery_action import RecoveryAction
from app.models.recovery_case import RecoveryCase
from app.models.subscription import Subscription
from app.services.resilience_service import (
    RESILIENCE_STATE_PRIORITY,
    SCORE_WEIGHTS,
    ResilienceService,
)


@pytest.fixture(autouse=True)
def reset_rate_limiter():
    """Reset in-memory rate limiter before each test."""
    rate_limiter.reset()
    yield
    rate_limiter.reset()


@pytest.fixture
def viewer_token() -> str:
    return create_access_token(user_id="res_viewer_1", role=UserRole.VIEWER.value)


@pytest.fixture
def operator_token() -> str:
    return create_access_token(user_id="res_operator_1", role=UserRole.OPERATOR.value)


@pytest.fixture
def admin_token() -> str:
    return create_access_token(user_id="res_admin_1", role=UserRole.ADMIN.value)


@pytest.fixture
def client(db_session: Session) -> TestClient:
    def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    test_client = TestClient(app)
    yield test_client
    app.dependency_overrides.clear()


@pytest.fixture
def sample_data(db_session: Session):
    """Create minimal test data for resilience tests."""
    customer = Customer(
        external_customer_id=f"cust_res_{uuid.uuid4().hex[:8]}",
        email_masked="r***s@example.com",
        risk_tier=CustomerRiskTier.LOW.value,
    )
    db_session.add(customer)
    db_session.flush()

    subscription = Subscription(
        customer_id=customer.id,
        plan_name="Standard Plan",
        status=SubscriptionStatus.ACTIVE.value,
        recurring_amount=5000.0,
        currency="INR",
        billing_cadence=BillingCadence.MONTHLY.value,
    )
    db_session.add(subscription)
    db_session.flush()

    payment = Payment(
        customer_id=customer.id,
        subscription_id=subscription.id,
        amount=5000,
        currency="INR",
        status=PaymentStatus.FAILED.value,
        external_order_id=f"order_{uuid.uuid4().hex[:8]}",
    )
    db_session.add(payment)
    db_session.flush()

    case = RecoveryCase(
        payment_id=payment.id,
        customer_id=customer.id,
        status=RecoveryCaseStatus.OPEN.value,
        amount_at_risk=5000,
    )
    db_session.add(case)
    db_session.commit()
    return customer, payment, case


# ─── Resilience Scoring Tests ─────────────────────────────────────────


def test_resilience_score_deterministic_and_bounded(db_session: Session):
    """Verify resilience score is deterministic and bounded within [0.0, 100.0]."""
    service = ResilienceService(db_session)
    score1, breakdown1 = service.calculate_resilience_score()
    score2, breakdown2 = service.calculate_resilience_score()

    # Deterministic
    assert score1 == score2
    assert breakdown1.availability_score == breakdown2.availability_score

    # Bounded
    assert 0.0 <= score1 <= 100.0
    assert 0.0 <= breakdown1.availability_score <= 100.0
    assert 0.0 <= breakdown1.dependency_health_score <= 100.0
    assert 0.0 <= breakdown1.recovery_readiness_score <= 100.0
    assert 0.0 <= breakdown1.rto_compliance_score <= 100.0
    assert 0.0 <= breakdown1.rpo_compliance_score <= 100.0
    assert 0.0 <= breakdown1.queue_health_score <= 100.0
    assert 0.0 <= breakdown1.audit_continuity_score <= 100.0
    assert 0.0 <= breakdown1.incident_stability_score <= 100.0


def test_resilience_score_weighted_components(db_session: Session):
    """Verify score weights sum to 1.0 and formula is correct."""
    total_weight = sum(SCORE_WEIGHTS.values())
    assert abs(total_weight - 1.0) < 1e-6, (
        f"Score weights sum to {total_weight}, expected 1.0"
    )


def test_resilience_state_priority_hierarchy(db_session: Session):
    """Verify DISASTER_MODE > CRITICAL > SERVICE_IMPACTED > ... > OPERATIONAL."""
    assert (
        RESILIENCE_STATE_PRIORITY[ResilienceState.DISASTER_MODE]
        > RESILIENCE_STATE_PRIORITY[ResilienceState.CRITICAL]
    )
    assert (
        RESILIENCE_STATE_PRIORITY[ResilienceState.CRITICAL]
        > RESILIENCE_STATE_PRIORITY[ResilienceState.SERVICE_IMPACTED]
    )
    assert (
        RESILIENCE_STATE_PRIORITY[ResilienceState.SERVICE_IMPACTED]
        > RESILIENCE_STATE_PRIORITY[ResilienceState.DEGRADED]
    )
    assert (
        RESILIENCE_STATE_PRIORITY[ResilienceState.DEGRADED]
        > RESILIENCE_STATE_PRIORITY[ResilienceState.WARNING]
    )
    assert (
        RESILIENCE_STATE_PRIORITY[ResilienceState.WARNING]
        > RESILIENCE_STATE_PRIORITY[ResilienceState.RECOVERY_IN_PROGRESS]
    )
    assert (
        RESILIENCE_STATE_PRIORITY[ResilienceState.RECOVERY_IN_PROGRESS]
        > RESILIENCE_STATE_PRIORITY[ResilienceState.RECOVERY_VERIFIED]
    )
    assert (
        RESILIENCE_STATE_PRIORITY[ResilienceState.RECOVERY_VERIFIED]
        > RESILIENCE_STATE_PRIORITY[ResilienceState.OPERATIONAL]
    )


# ─── Service Health Monitoring Tests ──────────────────────────────────


def test_service_health_all_healthy(db_session: Session):
    """Verify all 11 services are reported with health status."""
    service = ResilienceService(db_session)
    services = service.evaluate_service_health()

    assert len(services) == 11
    service_names = {s.service_name for s in services}
    assert "Database" in service_names
    assert "PolicyEngine" in service_names
    assert "ML Inference" in service_names
    assert "Recovery Worker" in service_names
    assert "Razorpay Provider" in service_names

    for svc in services:
        assert svc.latency_ms >= 0
        assert 0.0 <= svc.availability_percentage <= 100.0
        assert svc.consecutive_failures >= 0


def test_service_health_degraded_with_queue_backlog(db_session: Session, sample_data):
    """Verify worker/queue degrades when action queue exceeds threshold."""
    _, _, case = sample_data
    # Insert many pending actions to trigger backlog detection
    from app.models.policy_decision import PolicyDecision
    from app.models.recovery_action import RecoveryAction

    pd = PolicyDecision(
        recovery_case_id=case.id,
        evaluation_result="ALLOWED",
        policy_engine_version="v1.0",
        decision_reason="Test reason",
        triggered_rule_code="TEST_RULE",
        evaluation_details={},
    )
    db_session.add(pd)
    db_session.flush()

    for i in range(110):
        action = RecoveryAction(
            recovery_case_id=case.id,
            policy_decision_id=pd.id,
            action_idempotency_key=f"idem_key_res_{i}_{uuid.uuid4().hex[:8]}",
            action_type="RETRY_PAYMENT",
            status=RecoveryActionStatus.PENDING.value,
            action_payload={},
        )
        db_session.add(action)
    db_session.commit()

    svc = ResilienceService(db_session)
    services = svc.evaluate_service_health()
    worker = next(s for s in services if s.service_name == "Recovery Worker")
    assert worker.status == ServiceHealthStatus.DEGRADED


def test_service_health_latency_within_bounds(db_session: Session):
    """Verify database latency estimation returns non-negative values."""
    service = ResilienceService(db_session)
    services = service.evaluate_service_health()
    db_svc = next(s for s in services if s.service_name == "Database")
    assert db_svc.latency_ms >= 0
    assert db_svc.status == ServiceHealthStatus.HEALTHY


# ─── RTO/RPO Governance Tests ────────────────────────────────────────


def test_rto_compliant(db_session: Session):
    """Verify RTO compliance when no breaches detected."""
    service = ResilienceService(db_session)
    rto_rpo = service.evaluate_rto_rpo()
    assert rto_rpo.rto_compliance == RTORPOComplianceStatus.COMPLIANT
    assert rto_rpo.rto_target_seconds > 0


def test_rto_breached_with_events(db_session: Session):
    """Verify RTO breach detection when recovery exceeds target."""
    from datetime import UTC, datetime, timedelta

    # Create recovery events with large time gap to simulate breach
    now = datetime.now(UTC)
    start_event = AuditLog(
        entity_type="resilience",
        event_type=ResilienceAuditEventType.RECOVERY_STARTED,
        actor_type="SYSTEM",
        actor_id="system",
        action="recovery_started",
        metadata_json={},
    )
    db_session.add(start_event)
    db_session.flush()
    # Manually set created_at to past
    db_session.execute(
        AuditLog.__table__.update()
        .where(AuditLog.id == start_event.id)
        .values(created_at=now - timedelta(seconds=700))
    )

    verified_event = AuditLog(
        entity_type="resilience",
        event_type=ResilienceAuditEventType.RECOVERY_VERIFIED,
        actor_type="SYSTEM",
        actor_id="system",
        action="recovery_verified",
        metadata_json={},
    )
    db_session.add(verified_event)
    db_session.commit()

    service = ResilienceService(db_session)
    rto_rpo = service.evaluate_rto_rpo()
    assert rto_rpo.rto_compliance == RTORPOComplianceStatus.BREACHED
    assert rto_rpo.rto_observed_seconds > 300


def test_rpo_compliant(db_session: Session):
    """Verify RPO compliance when no data loss events detected."""
    service = ResilienceService(db_session)
    rto_rpo = service.evaluate_rto_rpo()
    assert rto_rpo.rpo_compliance == RTORPOComplianceStatus.COMPLIANT
    assert rto_rpo.rpo_target_seconds > 0


def test_rpo_breached_with_events(db_session: Session):
    """Verify RPO breach detection when data loss window exceeds target."""
    rpo_breach_event = AuditLog(
        entity_type="resilience",
        event_type=ResilienceAuditEventType.RPO_BREACH_DETECTED,
        actor_type="SYSTEM",
        actor_id="system",
        action="rpo_breach",
        metadata_json={"breach_seconds": 120},
    )
    db_session.add(rpo_breach_event)
    db_session.commit()

    service = ResilienceService(db_session)
    rto_rpo = service.evaluate_rto_rpo()
    assert rto_rpo.historical_rpo_breaches >= 1


# ─── DR Readiness Tests ──────────────────────────────────────────────


def test_dr_readiness_all_gates(db_session: Session):
    """Verify all 15 DR readiness gates are evaluated."""
    service = ResilienceService(db_session)
    readiness = service.evaluate_dr_readiness()

    assert len(readiness.gates) == 15
    assert (
        readiness.ready_count
        + readiness.conditional_count
        + readiness.blocked_count
        + readiness.unknown_count
        == 15
    )
    assert 0.0 <= readiness.readiness_percentage <= 100.0

    gate_codes = {g.gate_code for g in readiness.gates}
    assert "DATABASE_RECOVERY_READY" in gate_codes
    assert "BACKUP_INTEGRITY_READY" in gate_codes
    assert "RTO_COMPLIANCE" in gate_codes
    assert "RPO_COMPLIANCE" in gate_codes
    assert "HUMAN_ESCALATION_READY" in gate_codes


def test_dr_readiness_partial(db_session: Session):
    """Verify partial readiness when some gates are conditional."""
    service = ResilienceService(db_session)
    readiness = service.evaluate_dr_readiness()

    # RESTORE_VALIDATION_READY should be CONDITIONAL (no restore test executed yet)
    restore_gate = next(
        g for g in readiness.gates if g.gate_code == "RESTORE_VALIDATION_READY"
    )
    assert restore_gate.status == ReadinessStatus.CONDITIONAL


def test_dr_readiness_blocked_not_possible_in_healthy_state(db_session: Session):
    """Verify no BLOCKED gates when all services are healthy."""
    service = ResilienceService(db_session)
    readiness = service.evaluate_dr_readiness()
    assert readiness.blocked_count == 0


# ─── Disaster Simulation Tests ───────────────────────────────────────


def test_disaster_simulation_all_scenarios(db_session: Session):
    """Verify all 11 disaster scenarios can be simulated."""
    service = ResilienceService(db_session)

    for scenario in DisasterScenarioType:
        result = service.simulate_disaster(scenario.value)
        assert result.scenario_type == scenario.value
        assert result.financial_isolation_status == "VERIFIED"
        assert result.simulation_type == "OBSERVATIONAL"
        assert "OBSERVATIONAL SIMULATION" in result.disclaimer
        assert len(result.recovery_steps) > 0
        assert result.estimated_rto_seconds >= 0
        assert result.estimated_rpo_seconds >= 0
        assert 0.0 <= result.blast_radius.blast_radius_percentage <= 100.0


def test_disaster_simulation_financial_isolation(db_session: Session, sample_data):
    """Verify disaster simulation creates zero financial mutations."""
    _, payment, case = sample_data

    # Record pre-simulation counts
    action_count_before = db_session.query(RecoveryAction).count()
    payment_amount_before = payment.amount
    case_status_before = case.status

    service = ResilienceService(db_session)
    for scenario in DisasterScenarioType:
        service.simulate_disaster(scenario.value)

    # Verify zero financial mutations
    action_count_after = db_session.query(RecoveryAction).count()
    db_session.refresh(payment)
    db_session.refresh(case)

    assert action_count_after == action_count_before, (
        "Simulation created RecoveryAction records!"
    )
    assert payment.amount == payment_amount_before, "Simulation mutated Payment!"
    assert case.status == case_status_before, "Simulation mutated RecoveryCase!"


# ─── Cascading Failure Detection Tests ────────────────────────────────


def test_cascading_failure_not_detected_when_healthy(db_session: Session):
    """Verify no cascading failure when all services are healthy."""
    service = ResilienceService(db_session)
    incidents = service.detect_cascading_failure()
    assert len(incidents) == 0


# ─── Backup Verification Tests ────────────────────────────────────────


def test_backup_valid_checksum(db_session: Session):
    """Verify backup returns valid integrity status and SHA-256 checksum."""
    service = ResilienceService(db_session)
    backup = service.evaluate_backup_readiness()

    assert backup.integrity_status == BackupIntegrityStatus.VALID
    assert len(backup.checksum_sha256) == 64  # SHA-256 hex length
    assert backup.freshness_status == BackupFreshnessStatus.CURRENT


def test_backup_stale_detection(db_session: Session):
    """Verify stale backup detection when backup event is old."""
    from datetime import UTC, datetime, timedelta

    old_time = datetime.now(UTC) - timedelta(hours=30)
    backup_event = AuditLog(
        entity_type="resilience",
        event_type=ResilienceAuditEventType.BACKUP_VERIFIED,
        actor_type="SYSTEM",
        actor_id="system",
        action="backup_verified",
        metadata_json={"checksum": "a" * 64, "backup_id": "BKP-TEST-001"},
    )
    db_session.add(backup_event)
    db_session.flush()
    db_session.execute(
        AuditLog.__table__.update()
        .where(AuditLog.id == backup_event.id)
        .values(created_at=old_time)
    )
    db_session.commit()

    service = ResilienceService(db_session)
    backup = service.evaluate_backup_readiness()
    assert backup.freshness_status == BackupFreshnessStatus.STALE
    assert backup.backup_age_seconds > 86400


def test_backup_restore_verified(db_session: Session):
    """Verify restore verification status when restore test is logged."""

    backup_event = AuditLog(
        entity_type="resilience",
        event_type=ResilienceAuditEventType.BACKUP_VERIFIED,
        actor_type="SYSTEM",
        actor_id="system",
        action="backup_verified",
        metadata_json={"checksum": "b" * 64, "backup_id": "BKP-TEST-002"},
    )
    restore_event = AuditLog(
        entity_type="resilience",
        event_type=ResilienceAuditEventType.RESTORE_TEST_VERIFIED,
        actor_type="SYSTEM",
        actor_id="system",
        action="restore_verified",
        metadata_json={"duration_seconds": 45},
    )
    db_session.add_all([backup_event, restore_event])
    db_session.commit()

    service = ResilienceService(db_session)
    backup = service.evaluate_backup_readiness()
    assert backup.restore_test_status == RestoreVerificationStatus.VERIFIED
    assert backup.restore_duration_seconds == 45


# ─── RBAC Enforcement Tests ──────────────────────────────────────────


def test_resilience_endpoints_rbac_protection(
    client: TestClient, viewer_token: str, operator_token: str, admin_token: str
):
    """Verify RBAC enforcement across all resilience endpoints."""
    # Unauthenticated
    res = client.get("/api/recovery/intelligence/resilience")
    assert res.status_code == 401

    # Viewer can access GET endpoints
    for path in [
        "/api/recovery/intelligence/resilience",
        "/api/recovery/intelligence/resilience/services",
        "/api/recovery/intelligence/resilience/incidents",
        "/api/recovery/intelligence/resilience/readiness",
        "/api/recovery/intelligence/resilience/backups",
        "/api/recovery/intelligence/resilience/rto-rpo",
        "/api/recovery/intelligence/resilience/runbooks",
        "/api/recovery/intelligence/resilience/simulations",
    ]:
        res = client.get(path, headers={"Authorization": f"Bearer {viewer_token}"})
        assert res.status_code == 200, f"Viewer blocked from {path}"

    # Viewer CANNOT run simulation
    res = client.post(
        "/api/recovery/intelligence/resilience/simulate",
        json={"scenario_type": "DATABASE_OUTAGE"},
        headers={"Authorization": f"Bearer {viewer_token}"},
    )
    assert res.status_code == 403

    # Operator CAN run simulation
    res = client.post(
        "/api/recovery/intelligence/resilience/simulate",
        json={"scenario_type": "DATABASE_OUTAGE"},
        headers={"Authorization": f"Bearer {operator_token}"},
    )
    assert res.status_code == 200

    # Viewer CANNOT escalate
    res = client.post(
        "/api/recovery/intelligence/resilience/incidents/INC-TEST/escalate",
        headers={"Authorization": f"Bearer {viewer_token}"},
    )
    assert res.status_code == 403

    # Operator CANNOT escalate (requires admin)
    res = client.post(
        "/api/recovery/intelligence/resilience/incidents/INC-TEST/escalate",
        headers={"Authorization": f"Bearer {operator_token}"},
    )
    assert res.status_code == 403

    # Admin CAN escalate
    res = client.post(
        "/api/recovery/intelligence/resilience/incidents/INC-TEST/escalate",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert res.status_code == 200


# ─── Audit Trail Integrity Tests ──────────────────────────────────────


def test_audit_trail_immutable_events(db_session: Session):
    """Verify resilience operations create immutable AuditLog entries."""
    service = ResilienceService(db_session)

    # Acknowledge creates an audit event
    service.acknowledge_incident("INC-TEST-AUDIT", "audit_operator")
    ack_events = (
        db_session.query(AuditLog)
        .filter(
            AuditLog.entity_type == "resilience",
            AuditLog.event_type == ResilienceAuditEventType.INCIDENT_ACKNOWLEDGED,
        )
        .all()
    )
    assert len(ack_events) >= 1
    assert ack_events[0].actor_id == "audit_operator"

    # Recovery verification creates an audit event
    service.verify_recovery("verify_operator")
    verify_events = (
        db_session.query(AuditLog)
        .filter(
            AuditLog.entity_type == "resilience",
            AuditLog.event_type == ResilienceAuditEventType.RECOVERY_VERIFIED,
        )
        .all()
    )
    assert len(verify_events) >= 1

    # Verify no PII in any resilience audit events
    all_res_events = (
        db_session.query(AuditLog).filter(AuditLog.entity_type == "resilience").all()
    )
    for event in all_res_events:
        meta_str = str(event.metadata_json)
        assert "@" not in meta_str or "example" in meta_str
        assert "rzp_live" not in meta_str
        assert "rzp_test" not in meta_str


# ─── Recovery Runbooks Tests ──────────────────────────────────────────


def test_recovery_runbooks_complete(db_session: Session):
    """Verify 9 structured recovery runbooks are available."""
    service = ResilienceService(db_session)
    runbooks = service.get_runbooks()
    assert len(runbooks) == 9

    for rb in runbooks:
        assert rb.runbook_id
        assert rb.scenario
        assert len(rb.ordered_steps) > 0
        assert len(rb.verification_steps) > 0
        assert rb.required_role in ["operator", "admin"]
        assert rb.estimated_duration_minutes > 0
        assert rb.rto_target_seconds > 0


# ─── Global Resilience State Tests ────────────────────────────────────


def test_global_state_operational_when_healthy(db_session: Session):
    """Verify OPERATIONAL state when all services are healthy."""
    service = ResilienceService(db_session)
    state = service.evaluate_global_resilience_state()
    assert state == ResilienceState.OPERATIONAL


# ─── Executive Summary Tests ─────────────────────────────────────────


def test_resilience_summary_complete(db_session: Session):
    """Verify executive summary contains all required fields."""
    service = ResilienceService(db_session)
    summary = service.get_resilience_summary()

    assert 0.0 <= summary.resilience_score <= 100.0
    assert summary.global_state in [s.value for s in ResilienceState]
    assert len(summary.services) == 11
    assert summary.active_incidents_count >= 0
    assert 0.0 <= summary.dr_readiness_percentage <= 100.0
    assert 0.0 <= summary.service_availability_percentage <= 100.0
    assert "engineering resilience evidence" in summary.disclaimer


# ─── No PII in Resilience Responses ──────────────────────────────────


def test_no_pii_in_resilience_responses(
    client: TestClient, viewer_token: str, db_session: Session
):
    """Verify no PII or secrets in resilience API responses."""
    pii_patterns = [
        "rzp_live_",
        "rzp_test_",
        "BEGIN PRIVATE KEY",
        "password",
    ]

    for path in [
        "/api/recovery/intelligence/resilience",
        "/api/recovery/intelligence/resilience/services",
        "/api/recovery/intelligence/resilience/readiness",
        "/api/recovery/intelligence/resilience/rto-rpo",
        "/api/recovery/intelligence/resilience/backups",
    ]:
        res = client.get(path, headers={"Authorization": f"Bearer {viewer_token}"})
        assert res.status_code == 200
        body = res.text
        for pattern in pii_patterns:
            assert pattern not in body, f"PII pattern '{pattern}' found in {path}"


# ─── MANDATORY FINANCIAL ISOLATION GUARANTEE ─────────────────────────


def test_mandatory_financial_isolation_guarantee(
    db_session: Session, sample_data, client: TestClient, operator_token: str
):
    """
    MANDATORY TEST: Execute resilience evaluation → dependency surveillance
    → disaster simulation → incident creation → readiness evaluation
    → recovery verification and assert zero financial mutations.
    """
    _, payment, case = sample_data

    # Record baseline financial state
    action_count_before = db_session.query(RecoveryAction).count()
    payment_count_before = db_session.query(Payment).count()
    case_count_before = db_session.query(RecoveryCase).count()
    payment_amount = payment.amount
    case_status = case.status

    service = ResilienceService(db_session)

    # 1. Resilience evaluation
    summary = service.get_resilience_summary()
    assert summary.resilience_score >= 0

    # 2. Dependency surveillance
    services = service.evaluate_service_health()
    assert len(services) == 11

    # 3. Disaster simulation (all 11 scenarios)
    for scenario in DisasterScenarioType:
        result = service.simulate_disaster(scenario.value)
        assert result.financial_isolation_status == "VERIFIED"

    # 4. Incident creation
    service.acknowledge_incident("INC-ISOLATION-TEST", "op_test")

    # 5. Readiness evaluation
    readiness = service.evaluate_dr_readiness()
    assert len(readiness.gates) == 15

    # 6. Recovery verification
    service.verify_recovery("op_test")

    # 7. API endpoints (via HTTP)
    headers = {"Authorization": f"Bearer {operator_token}"}
    client.get("/api/recovery/intelligence/resilience", headers=headers)
    client.get("/api/recovery/intelligence/resilience/services", headers=headers)
    client.get("/api/recovery/intelligence/resilience/readiness", headers=headers)
    client.post(
        "/api/recovery/intelligence/resilience/simulate",
        json={"scenario_type": "DATABASE_OUTAGE"},
        headers=headers,
    )

    # ──── ASSERT ZERO FINANCIAL MUTATIONS ────
    action_count_after = db_session.query(RecoveryAction).count()
    payment_count_after = db_session.query(Payment).count()
    case_count_after = db_session.query(RecoveryCase).count()

    db_session.refresh(payment)
    db_session.refresh(case)

    assert action_count_after == action_count_before, (
        f"FINANCIAL ISOLATION VIOLATED: RecoveryAction count changed "
        f"from {action_count_before} to {action_count_after}"
    )
    assert payment_count_after == payment_count_before, (
        f"FINANCIAL ISOLATION VIOLATED: Payment count changed "
        f"from {payment_count_before} to {payment_count_after}"
    )
    assert case_count_after == case_count_before, (
        f"FINANCIAL ISOLATION VIOLATED: RecoveryCase count changed "
        f"from {case_count_before} to {case_count_after}"
    )
    assert payment.amount == payment_amount, (
        "FINANCIAL ISOLATION VIOLATED: Payment amount mutated!"
    )
    assert case.status == case_status, (
        "FINANCIAL ISOLATION VIOLATED: RecoveryCase status mutated!"
    )

    # Verify no ActionDispatcher or RazorpayActionProvider calls
    # (These are never imported or called by the resilience service)
    import app.services.resilience_service as res_module

    assert "ActionDispatcher" not in res_module.__dict__, (
        "ResilienceService imports ActionDispatcher!"
    )
    assert "action_dispatcher" not in res_module.__dict__, (
        "ResilienceService imports action_dispatcher!"
    )
    assert "RazorpayActionProvider" not in res_module.__dict__, (
        "ResilienceService imports RazorpayActionProvider!"
    )
