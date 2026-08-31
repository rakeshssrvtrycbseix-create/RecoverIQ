import uuid
from decimal import Decimal
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.pii_scanner import scan_for_pii_and_secrets
from app.core.rate_limiter import rate_limiter
from app.core.security import (
    UserRole,
    create_access_token,
)
from app.main import app
from app.models.agent_decision import AgentDecision
from app.models.audit_log import AuditLog
from app.models.customer import Customer
from app.models.enums import (
    BillingCadence,
    CustomerRiskTier,
    PaymentStatus,
    RecoveryActionStatus,
    RecoveryCaseStatus,
    SecurityEventType,
    SubscriptionStatus,
)
from app.models.ml_prediction import MLPrediction
from app.models.payment import Payment
from app.models.policy_decision import PolicyDecision
from app.models.recovery_action import RecoveryAction
from app.models.recovery_case import RecoveryCase
from app.models.subscription import Subscription
from app.schemas.compliance import (
    ComplianceControlCategory,
    ComplianceControlStatus,
    CompliancePosture,
    ComplianceSeverity,
)
from app.services.compliance_governance_service import ComplianceGovernanceService


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
def sample_customer_and_payment(db_session: Session):
    customer = Customer(
        external_customer_id=f"cust_comp_{uuid.uuid4().hex[:8]}",
        email_masked="t***p@example.com",
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


def test_compliance_score_calculation_deterministic(db_session: Session):
    """Verify deterministic calculation of compliance score and posture mapping."""
    service = ComplianceGovernanceService(db_session)
    summary = service.get_compliance_summary()

    assert 0.0 <= summary.compliance_score <= 100.0
    assert summary.compliance_posture in [
        CompliancePosture.EXCELLENT,
        CompliancePosture.GOOD,
        CompliancePosture.WARNING,
        CompliancePosture.HIGH_RISK,
        CompliancePosture.CRITICAL,
    ]
    assert len(summary.category_scores) == 5
    assert summary.total_controls_count >= 18
    assert "software engineering control evidence" in summary.disclaimer


def test_compliance_controls_evaluation_and_filtering(
    db_session: Session, client: TestClient, viewer_token: str
):
    """Verify evaluation of all 18 controls and category/status query filtering."""
    service = ComplianceGovernanceService(db_session)
    controls = service.get_compliance_controls()

    assert len(controls) >= 18
    categories = {c.control_category for c in controls}
    assert ComplianceControlCategory.SECURITY in categories
    assert ComplianceControlCategory.FINANCIAL_CONTROL in categories
    assert ComplianceControlCategory.ML_GOVERNANCE in categories
    assert ComplianceControlCategory.DATA_GOVERNANCE in categories
    assert ComplianceControlCategory.HUMAN_GOVERNANCE in categories

    # Test API with query filter
    res = client.get(
        "/api/recovery/intelligence/compliance/controls?category=SECURITY",
        headers={"Authorization": f"Bearer {viewer_token}"},
    )
    assert res.status_code == 200
    sec_controls = res.json()
    assert len(sec_controls) >= 7
    assert all(c["control_category"] == "SECURITY" for c in sec_controls)


def test_audit_coverage_calculation(db_session: Session):
    """Verify audit coverage calculations against required lifecycle event categories."""
    service = ComplianceGovernanceService(db_session)

    # Insert a few audit logs for known event types
    log1 = AuditLog(
        entity_type="security_event",
        entity_id=uuid.uuid4(),
        event_type="AUTH_SUCCESS",
        actor_type="user",
        actor_id="test_user",
        action="login",
        metadata_json={"ip": "127.0.0.1"},
    )
    log2 = AuditLog(
        entity_type="recovery_case",
        entity_id=uuid.uuid4(),
        event_type="RECOVERY_CASE_CREATED",
        actor_type="system",
        actor_id="system",
        action="create",
        metadata_json={},
    )
    db_session.add_all([log1, log2])
    db_session.commit()

    coverage = service.get_audit_coverage()
    assert coverage.total_required_event_categories == 10
    assert coverage.observed_event_categories >= 2
    assert coverage.audit_coverage_percentage >= 20.0
    assert "AUTHENTICATION" in coverage.lifecycle_chains_status
    assert coverage.lifecycle_chains_status["AUTHENTICATION"] == "OBSERVED"


def test_missing_audit_events_detection(db_session: Session):
    """Verify missing audit event types are accurately identified."""
    service = ComplianceGovernanceService(db_session)
    coverage = service.get_audit_coverage()

    assert isinstance(coverage.missing_categories, list)
    assert (
        len(coverage.missing_categories)
        == coverage.total_required_event_categories - coverage.observed_event_categories
    )


def test_decision_trace_completeness_validation(
    db_session: Session, sample_customer_and_payment
):
    """Verify 6-stage lifecycle decision trace compliance analysis."""
    _, _, case = sample_customer_and_payment
    service = ComplianceGovernanceService(db_session)

    # Initial case without prediction/policy/action should be untraced or partial
    traces = service.get_decision_trace_compliance()
    assert traces.total_resolved_cases_sampled >= 1
    assert traces.pii_exposed_in_traces is False

    # Add complete chain
    pred = MLPrediction(
        recovery_case_id=case.id,
        model_name="RecoverIQ-Model",
        model_version="v1.0.0",
        recovery_probability=Decimal("0.8500"),
        predicted_channel="CALL",
        feature_vector_snapshot={"amount": 5000, "risk_tier": "LOW"},
    )
    db_session.add(pred)
    db_session.flush()

    agent = AgentDecision(
        recovery_case_id=case.id,
        ml_prediction_id=pred.id,
        agent_name="RecoveryOrchestrator",
        agent_version="1.0.0",
        prompt_template_version="1.0",
        proposed_action_type="CALL",
        confidence_score=Decimal("0.8500"),
        reasoning_summary="Customer has high willingness to pay",
    )
    db_session.add(agent)
    db_session.flush()

    policy = PolicyDecision(
        recovery_case_id=case.id,
        agent_decision_id=agent.id,
        evaluation_result="APPROVED",
        policy_engine_version="1.0.0",
        triggered_rule_code="RULE-ALLOW",
        rule_name="Standard Retry Rule",
        evaluation_details={"approved": True},
        decision_reason="Approved under standard limits",
    )
    db_session.add(policy)
    db_session.flush()

    action = RecoveryAction(
        recovery_case_id=case.id,
        policy_decision_id=policy.id,
        action_idempotency_key=f"act_idem_{uuid.uuid4().hex[:12]}",
        action_type="CALL",
        status=RecoveryActionStatus.SCHEDULED.value,
    )
    db_session.add(action)
    db_session.commit()

    updated_traces = service.get_decision_trace_compliance()
    assert updated_traces.complete_traces_count >= 1


def test_financial_governance_integrity(
    db_session: Session, sample_customer_and_payment
):
    """Verify financial governance checks detecting unlinked actions and verifying PolicyEngine supremacy."""
    _, _, case = sample_customer_and_payment
    service = ComplianceGovernanceService(db_session)

    policy = PolicyDecision(
        recovery_case_id=case.id,
        evaluation_result="APPROVED",
        policy_engine_version="1.0.0",
        triggered_rule_code="RULE-ALLOW",
        rule_name="Fin Rule",
        evaluation_details={"approved": True},
        decision_reason="Approved for testing",
    )
    db_session.add(policy)
    db_session.flush()

    action = RecoveryAction(
        recovery_case_id=case.id,
        policy_decision_id=policy.id,
        action_idempotency_key=f"act_idem_{uuid.uuid4().hex[:12]}",
        action_type="WHATSAPP",
        status=RecoveryActionStatus.SCHEDULED.value,
    )
    db_session.add(action)
    db_session.commit()

    fin_gov = service.get_financial_governance_audit()
    assert fin_gov.policy_engine_supremacy_verified is True
    assert fin_gov.unauthorized_financial_mutations_count == 0
    assert fin_gov.actions_with_policy_decision_percentage == 100.0
    assert fin_gov.status == ComplianceControlStatus.PASS


def test_rbac_compliance_audit_and_violation_detection(db_session: Session):
    """Verify RBAC compliance audits detecting privilege escalation and role denial logs."""
    service = ComplianceGovernanceService(db_session)

    # Insert a privilege escalation audit event
    esc_log = AuditLog(
        entity_type="security_event",
        entity_id=uuid.uuid4(),
        event_type=SecurityEventType.PRIVILEGE_ESCALATION_BLOCKED.value,
        actor_type="user",
        actor_id="rogue_viewer",
        action="attempt_escalation",
        metadata_json={"attempted_role": "admin"},
    )
    db_session.add(esc_log)
    db_session.commit()

    rbac_audit = service.get_rbac_compliance_audit()
    assert rbac_audit.privilege_escalation_attempts_count == 1
    assert len(rbac_audit.findings) == 1
    assert rbac_audit.findings[0].severity == ComplianceSeverity.HIGH
    assert rbac_audit.status == ComplianceControlStatus.WARNING


def test_model_and_strategy_governance_compliance(db_session: Session):
    """Verify ML and Strategy governance audit telemetry."""
    service = ComplianceGovernanceService(db_session)
    model_gov = service.get_model_governance_compliance()

    assert model_gov.dataset_lineage_coverage_pct == 100.0
    assert model_gov.active_champion_has_approved_gates is True
    assert model_gov.unapproved_deployments_count == 0
    assert model_gov.status == ComplianceControlStatus.PASS


def test_data_protection_and_zero_pii_audit(db_session: Session):
    """Verify data protection audit validates active PII scanner and zero leaks."""
    service = ComplianceGovernanceService(db_session)
    data_prot = service.get_data_protection_audit()

    assert data_prot.pii_scanner_active is True
    assert data_prot.unmasked_cards_detected_count == 0
    assert data_prot.unmasked_tokens_detected_count == 0
    assert data_prot.status == ComplianceControlStatus.PASS


def test_compliance_incidents_generation_and_severity(db_session: Session):
    """Verify deterministic generation of compliance incidents from system state."""
    service = ComplianceGovernanceService(db_session)
    incidents = service.get_compliance_incidents()

    assert isinstance(incidents, list)
    if len(incidents) > 0:
        for inc in incidents:
            assert inc.incident_id.startswith("INC-")
            assert inc.severity in [
                ComplianceSeverity.LOW,
                ComplianceSeverity.MEDIUM,
                ComplianceSeverity.HIGH,
                ComplianceSeverity.CRITICAL,
            ]
            assert inc.status == "OPEN"


def test_compliance_endpoints_rbac_protection(
    client: TestClient, viewer_token: str, operator_token: str, admin_token: str
):
    """Verify RBAC access boundaries on all compliance endpoints: 401 for unauthenticated, 200 for Viewer, Operator, Admin."""
    endpoints = [
        "/api/recovery/intelligence/compliance",
        "/api/recovery/intelligence/compliance/controls",
        "/api/recovery/intelligence/compliance/incidents",
        "/api/recovery/intelligence/compliance/audit-coverage",
        "/api/recovery/intelligence/compliance/report",
    ]

    for ep in endpoints:
        # Unauthenticated -> 401
        res_unauth = client.get(ep)
        assert res_unauth.status_code == 401, f"Failed for {ep} unauth"

        # Viewer -> 200
        res_view = client.get(ep, headers={"Authorization": f"Bearer {viewer_token}"})
        assert res_view.status_code == 200, f"Failed for {ep} viewer"

        # Operator -> 200
        res_op = client.get(ep, headers={"Authorization": f"Bearer {operator_token}"})
        assert res_op.status_code == 200, f"Failed for {ep} operator"

        # Admin -> 200
        res_admin = client.get(ep, headers={"Authorization": f"Bearer {admin_token}"})
        assert res_admin.status_code == 200, f"Failed for {ep} admin"


def test_mandatory_financial_isolation_guarantee(
    client: TestClient,
    admin_token: str,
    db_session: Session,
    sample_customer_and_payment,
):
    """
    CRITICAL MANDATORY INVARIANT TEST:
    Calling all Phase 10B compliance endpoints MUST NEVER create RecoveryAction records,
    MUST NEVER mutate Payment or RecoveryCase financial balances, and MUST NEVER invoke payment providers.
    """
    _, payment, case = sample_customer_and_payment
    initial_action_count = db_session.query(RecoveryAction).count()
    initial_payment_amount = payment.amount
    initial_payment_status = payment.status
    initial_case_amount = case.amount_at_risk

    with (
        patch(
            "app.services.action_dispatcher.ActionDispatcher.dispatch_action"
        ) as mock_dispatcher,
        patch("app.providers.razorpay.RazorpayActionProvider.execute") as mock_provider,
    ):
        # Call all compliance endpoints
        endpoints = [
            "/api/recovery/intelligence/compliance",
            "/api/recovery/intelligence/compliance/controls",
            "/api/recovery/intelligence/compliance/incidents",
            "/api/recovery/intelligence/compliance/audit-coverage",
            "/api/recovery/intelligence/compliance/report",
        ]

        for ep in endpoints:
            res = client.get(ep, headers={"Authorization": f"Bearer {admin_token}"})
            assert res.status_code == 200

        # Assert no dispatching occurred
        assert mock_dispatcher.call_count == 0
        assert mock_provider.call_count == 0

    # Refresh DB objects and assert financial isolation
    db_session.expire_all()
    final_action_count = db_session.query(RecoveryAction).count()
    final_payment = db_session.query(Payment).filter(Payment.id == payment.id).first()
    final_case = (
        db_session.query(RecoveryCase).filter(RecoveryCase.id == case.id).first()
    )

    assert final_action_count == initial_action_count, (
        "Financial Isolation Violated: RecoveryAction count changed!"
    )
    assert final_payment.amount == initial_payment_amount, (
        "Financial Isolation Violated: Payment amount mutated!"
    )
    assert final_payment.status == initial_payment_status, (
        "Financial Isolation Violated: Payment status mutated!"
    )
    assert final_case.amount_at_risk == initial_case_amount, (
        "Financial Isolation Violated: Case amount mutated!"
    )


def test_no_pii_or_secrets_in_compliance_responses(
    client: TestClient,
    viewer_token: str,
):
    """Verify deep PII & secret scanner detects no raw credit cards, Aadhaar, or API secrets in responses."""
    endpoints = [
        "/api/recovery/intelligence/compliance",
        "/api/recovery/intelligence/compliance/controls",
        "/api/recovery/intelligence/compliance/incidents",
        "/api/recovery/intelligence/compliance/audit-coverage",
        "/api/recovery/intelligence/compliance/report",
    ]

    for ep in endpoints:
        res = client.get(ep, headers={"Authorization": f"Bearer {viewer_token}"})
        assert res.status_code == 200
        data = res.json()

        scan_res = scan_for_pii_and_secrets(data)
        # Should have 0 PII leaks and 0 secrets
        assert scan_res["findings_count"] == 0, (
            f"PII or secret detected in {ep} response: {scan_res['findings']}"
        )


def test_exportable_compliance_report_format(
    client: TestClient,
    viewer_token: str,
):
    """Verify the structured format of the exportable compliance report."""
    res = client.get(
        "/api/recovery/intelligence/compliance/report",
        headers={"Authorization": f"Bearer {viewer_token}"},
    )
    assert res.status_code == 200
    report = res.json()

    assert "report_id" in report
    assert report["report_id"].startswith("REP-COMP-")
    assert "executive_summary" in report
    assert "disclaimer" in report
    assert "category_scores" in report
    assert "controls" in report
    assert "remediation_roadmap" in report
    assert len(report["remediation_roadmap"]) >= 3
    assert all(
        "priority" in r and "milestone" in r for r in report["remediation_roadmap"]
    )
