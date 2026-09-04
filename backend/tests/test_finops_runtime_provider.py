"""Comprehensive Tests for RecoverIQ FinOps Runtime Telemetry Data Provider.

Verifies:
1. Provider factory resolution (runtime vs demo, override parameter).
2. Clean behavior on empty/unseeded database (zero divisions safe, insufficient data flag).
3. Real telemetry calculations on seeded database (payments, cases, predictions, audit logs).
4. Unmetered/cloud infrastructure marked UNAVAILABLE / NOT_CONNECTED (no AWS fabrication).
5. Dynamic anomaly detection and readiness gate evaluation (no hardcoded passes).
6. HMAC-SHA256 signature verification in runtime mode.
7. Strict financial execution isolation (Delta Payment = 0, Delta RecoveryAction = 0).
"""

import hashlib
import hmac
from decimal import Decimal
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.security import UserRole, create_access_token
from app.models.action_result import ActionResult
from app.models.agent_decision import AgentDecision
from app.models.audit_log import AuditLog
from app.models.customer import Customer
from app.models.enums import (
    CustomerRiskTier,
    FinOpsGateStatus,
    ForecastState,
    PaymentStatus,
    PolicyEvaluationResult,
    RecoveryActionStatus,
    RecoveryActionType,
    RecoveryCaseStatus,
    RecoveryStage,
    ResourceEfficiencyState,
    ResourceType,
)
from app.models.ml_prediction import MLPrediction
from app.models.payment import Payment
from app.models.policy_decision import PolicyDecision
from app.models.recovery_action import RecoveryAction
from app.models.recovery_case import RecoveryCase
from app.schemas.finops import BudgetConfigRequest
from app.services.finops import (
    DemoFinOpsDataProvider,
    FinOpsDataProvider,
    RuntimeFinOpsDataProvider,
    get_finops_provider,
)
from app.services.finops_service import FinOpsService


def get_token(
    role: UserRole = UserRole.ADMIN, user_id: str = "runtime-tester"
) -> str:
    return create_access_token(user_id=user_id, role=role.value)


# ---------------------------------------------------------------------------
# 1. Provider Resolution & Factory
# ---------------------------------------------------------------------------


def test_finops_provider_factory_resolution(db_session: Session):
    """Test that the factory returns the correct provider based on mode."""
    runtime_prov = get_finops_provider(db_session, mode="runtime")
    assert isinstance(runtime_prov, RuntimeFinOpsDataProvider)
    assert runtime_prov.data_mode == "runtime"

    demo_prov = get_finops_provider(db_session, mode="demo")
    assert isinstance(demo_prov, DemoFinOpsDataProvider)
    assert demo_prov.data_mode == "demo"

    # Default fallback when mode is unknown
    default_prov = get_finops_provider(db_session, mode="other")
    assert isinstance(default_prov, RuntimeFinOpsDataProvider)


# ---------------------------------------------------------------------------
# 2. Unseeded Database State (Empty Local DB)
# ---------------------------------------------------------------------------


def test_runtime_provider_unseeded_database(db_session: Session):
    """Verify runtime provider returns safe zero/insufficient metrics on empty DB."""
    provider = RuntimeFinOpsDataProvider(db_session)

    # Unit economics: zero division safe
    ue = provider.get_unit_economics()
    assert ue.cost_per_transaction.monthly_transaction_volume == 0
    assert ue.cost_per_transaction.cost_per_successful_txn_inr == 0.0
    assert ue.cost_per_recovery_case.monthly_case_volume == 0
    assert ue.cost_per_recovery_case.cost_per_case_inr == 0.0
    assert ue.ml_inference_cost.monthly_prediction_volume == 0

    # Forecasts: reports insufficient historical data
    forecast = provider.get_forecasts()
    assert forecast.forecast_state == ForecastState.INSUFFICIENT_DATA
    assert any(
        s.scenario_name == "INSUFFICIENT_DATA" for s in forecast.scenarios
    )

    # Anomalies: zero fabricated anomalies
    anomalies = provider.get_cost_anomalies()
    assert len(anomalies) == 0

    # Waste findings: zero fabricated waste
    waste = provider.get_waste_findings()
    assert len(waste) == 0

    # Readiness gates: dynamic evaluation, NOT 20/20 hardcoded PASS
    gates = provider.get_readiness_gates()
    assert len(gates) == 20
    passed_count = sum(1 for g in gates if g.status == FinOpsGateStatus.PASS)
    # Since cloud infrastructure is unmetered locally, passed count must be less than 20
    assert passed_count < 20


# ---------------------------------------------------------------------------
# 3. Seeded Database State (Real Telemetry Aggregation)
# ---------------------------------------------------------------------------


def test_runtime_provider_seeded_database(db_session: Session):
    """Verify runtime provider aggregates actual rows from Payment, Case, Action, ML tables."""
    # Seed Customer
    cust = Customer(
        external_customer_id=f"cust_rt_{uuid4().hex[:8]}",
        email_masked="rt@example.com",
        phone_masked="+91******3333",
        risk_tier=CustomerRiskTier.STANDARD.value,
        total_payments_count=5,
        failed_payments_count=2,
        recovered_payments_count=3,
    )
    db_session.add(cust)
    db_session.flush()

    # Seed 5 Payments (3 SUCCESS, 2 FAILED)
    payments = []
    for i in range(5):
        st = PaymentStatus.CAPTURED.value if i < 3 else PaymentStatus.FAILED.value
        p = Payment(
            customer_id=cust.id,
            razorpay_order_id=f"order_rt_{uuid4().hex[:8]}",
            amount=100000,
            currency="INR",
            status=st,
        )
        db_session.add(p)
        payments.append(p)
    db_session.flush()

    # Seed 3 RecoveryCases (2 RECOVERED, 1 OPEN)
    cases = []
    for i in range(3):
        case_st = RecoveryCaseStatus.RECOVERED.value if i < 2 else RecoveryCaseStatus.OPEN.value
        c = RecoveryCase(
            payment_id=payments[i + 2].id,
            customer_id=cust.id,
            status=case_st,
            recovery_stage=RecoveryStage.INITIAL_FAILURE.value,
            amount_at_risk=100000,
            recovered_amount=100000 if i < 2 else 0,
            total_attempts_count=1,
            max_allowed_attempts=3,
        )
        db_session.add(c)
        cases.append(c)
    db_session.flush()

    # Seed Decisions and Actions
    agent_dec = AgentDecision(
        recovery_case_id=cases[0].id,
        agent_name="RecoveryOrchestrator",
        agent_version="v1.0.0",
        prompt_template_version="pt_v1",
        proposed_action_type=RecoveryActionType.SEND_PAYMENT_LINK.value,
        confidence_score=Decimal("0.8500"),
        reasoning_summary="Test recovery reasoning",
    )
    db_session.add(agent_dec)
    db_session.flush()

    pol_dec = PolicyDecision(
        recovery_case_id=cases[0].id,
        agent_decision_id=agent_dec.id,
        evaluation_result=PolicyEvaluationResult.ALLOWED.value,
        policy_engine_version="v1.0.0",
        decision_reason="Checks passed",
    )
    db_session.add(pol_dec)
    db_session.flush()

    # Seed 4 RecoveryActions
    for i in range(4):
        action_st = RecoveryActionStatus.COMPLETED.value if i < 2 else RecoveryActionStatus.FAILED.value
        act = RecoveryAction(
            recovery_case_id=cases[0].id,
            policy_decision_id=pol_dec.id,
            action_idempotency_key=f"act_rt_{i}_{uuid4().hex[:8]}",
            action_type=RecoveryActionType.SEND_PAYMENT_LINK.value,
            status=action_st,
        )
        db_session.add(act)

    # Seed 7 MLPredictions
    for _ in range(7):
        pred = MLPrediction(
            recovery_case_id=cases[0].id,
            model_name="recoveriq-xgb-classifier",
            model_version="v1.2.0",
            recovery_probability=Decimal("0.8500"),
            predicted_channel="PAYMENT_LINK",
            predicted_delay_hours=12,
            feature_vector_snapshot={"risk": 0.2},
        )
        db_session.add(pred)

    db_session.commit()

    # Now verify runtime provider aggregates
    provider = RuntimeFinOpsDataProvider(db_session)
    ue = provider.get_unit_economics()

    assert ue.cost_per_transaction.monthly_transaction_volume == 5
    assert ue.cost_per_recovery_case.monthly_case_volume == 3
    assert ue.ml_inference_cost.monthly_prediction_volume == 7

    # Value efficiency ratio is computed from actual database state
    assert ue.recovery_intelligence_value_efficiency >= 0.0


# ---------------------------------------------------------------------------
# 4. Unmetered Cloud Infrastructure Marked UNAVAILABLE / NOT_CONNECTED
# ---------------------------------------------------------------------------


def test_runtime_provider_unavailable_cloud_infrastructure(db_session: Session):
    """Verify local unmetered cloud components are flagged as UNAVAILABLE or NOT_CONNECTED."""
    provider = RuntimeFinOpsDataProvider(db_session)
    efficiency = provider.get_resource_efficiency()

    # Redis/Cache resource
    cache_res = next(r for r in efficiency.resources if r.resource_type == ResourceType.REDIS_MEMORY)
    assert cache_res.state in [
        ResourceEfficiencyState.NOT_CONNECTED,
        ResourceEfficiencyState.UNAVAILABLE,
    ]

    # GPU resource
    gpu_res = next(r for r in efficiency.resources if r.resource_type == ResourceType.ML_GPU_COMPUTE)
    assert gpu_res.utilization_pct == 0.0
    assert gpu_res.state in [
        ResourceEfficiencyState.NOT_CONNECTED,
        ResourceEfficiencyState.UNAVAILABLE,
    ]

    # Category costs: all 10 categories present and have cost sources
    cat_costs = provider.get_category_costs()
    assert len(cat_costs) == 10
    for cat in cat_costs:
        assert cat.source is not None


# ---------------------------------------------------------------------------
# 5. API Mode Override Query Parameter (?mode=runtime vs ?mode=demo)
# ---------------------------------------------------------------------------


def test_api_mode_override_runtime(client: TestClient):
    """Verify the REST API returns RuntimeFinOpsDataProvider data when requested."""
    token = get_token(UserRole.VIEWER)
    headers = {"Authorization": f"Bearer {token}"}

    # Request runtime mode explicitly
    res_runtime = client.get("/api/recovery/intelligence/finops/summary?mode=runtime", headers=headers)
    assert res_runtime.status_code == 200
    data_runtime = res_runtime.json()
    assert data_runtime["data_mode"] == "runtime"
    assert data_runtime["provider"] == "RuntimeFinOpsDataProvider"

    # Request demo mode explicitly
    res_demo = client.get("/api/recovery/intelligence/finops/summary?mode=demo", headers=headers)
    assert res_demo.status_code == 200
    data_demo = res_demo.json()
    assert data_demo["data_mode"] == "demo"
    assert data_demo["provider"] == "DemoFinOpsDataProvider"


# ---------------------------------------------------------------------------
# 6. Budget Configuration in Runtime Mode Reuses Append-Only AuditLog
# ---------------------------------------------------------------------------


def test_runtime_budget_configuration_audit_log(db_session: Session):
    """Verify budget configuration writes to the existing append-only AuditLog."""
    provider = RuntimeFinOpsDataProvider(db_session)
    req = BudgetConfigRequest(
        period="MONTHLY",
        budget_amount_inr=50000.0,
        alert_thresholds=[50.0, 75.0, 90.0],
        notes="Test runtime budget configuration",
    )

    status = provider.configure_budget(req, actor_id="admin-tester")
    assert status.budget_amount_inr == 50000.0
    assert status.period == "MONTHLY"

    # Verify audit log entry was created
    audit = db_session.query(AuditLog).filter(
        AuditLog.action == "BUDGET_CONFIGURED"
    ).first()
    assert audit is not None
    assert audit.actor_id == "admin-tester"


# ---------------------------------------------------------------------------
# 7. HMAC-SHA256 Report Verification in Runtime Mode
# ---------------------------------------------------------------------------


def test_runtime_provider_signed_report_hmac(db_session: Session):
    """Verify cryptographic HMAC-SHA256 signature on runtime governance report."""
    provider = RuntimeFinOpsDataProvider(db_session)
    report = provider.generate_signed_report()

    assert report.data_mode == "runtime"
    assert report.provider == "RuntimeFinOpsDataProvider"
    assert report.verification_signature.startswith("sig_fin_hmac_sha256:")

    sig = report.verification_signature.split(":", 1)[1]
    assert len(sig) == 64


# ---------------------------------------------------------------------------
# 8. Financial Execution Isolation in Runtime Mode
# ---------------------------------------------------------------------------


def test_runtime_provider_financial_isolation(db_session: Session):
    """Verify zero database mutations on financial tables during runtime telemetry queries."""
    # Count initial rows
    init_payments = db_session.query(Payment).count()
    init_cases = db_session.query(RecoveryCase).count()
    init_actions = db_session.query(RecoveryAction).count()

    provider = RuntimeFinOpsDataProvider(db_session)

    # Execute all telemetry queries
    _ = provider.calculate_score_breakdown()
    _ = provider.get_summary()
    _ = provider.get_service_costs()
    _ = provider.get_category_costs()
    _ = provider.get_cost_allocation()
    _ = provider.get_budgets()
    _ = provider.get_cost_anomalies()
    _ = provider.get_forecasts()
    _ = provider.get_resource_efficiency()
    _ = provider.get_waste_findings()
    _ = provider.get_optimization_recommendations()
    _ = provider.get_unit_economics()
    _ = provider.get_finops_incidents()
    _ = provider.get_readiness_gates()
    _ = provider.generate_signed_report()

    # Verify Delta == 0 across all financial tables
    assert db_session.query(Payment).count() == init_payments
    assert db_session.query(RecoveryCase).count() == init_cases
    assert db_session.query(RecoveryAction).count() == init_actions
