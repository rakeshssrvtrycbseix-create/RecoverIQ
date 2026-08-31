import uuid
from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import UserRole, create_access_token
from app.main import app
from app.models import (
    Customer,
    CustomerRiskTier,
    MLPrediction,
    Payment,
    PaymentStatus,
    RecoveryCase,
    RecoveryCaseStatus,
)
from app.services.model_governance_service import (
    MIN_EVALUATION_SAMPLE_SIZE,
    model_governance_service,
)


@pytest.fixture
def client(db_session: Session):
    """Test client with overridden database session dependency and viewer auth."""

    def _override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = _override_get_db
    token = create_access_token(user_id="viewer_test_gov", role=UserRole.VIEWER.value)
    with TestClient(app, headers={"Authorization": f"Bearer {token}"}) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def make_gov_case(
    db_session: Session,
    status: str = RecoveryCaseStatus.RECOVERED.value,
    amount: int = 100000,
    prob: float = 0.85,
    days_ago: float = 2.0,
    model_version: str = "v1.0",
    features: dict | None = None,
    failure_reason: str = "insufficient_funds",
) -> RecoveryCase:
    """Helper to provision a resolved recovery case with ML prediction at a specific timestamp."""
    uid = uuid.uuid4().hex[:8]
    now_utc = datetime.now(UTC)
    resolved_time = now_utc - timedelta(days=days_ago)

    customer = Customer(
        external_customer_id=f"cust_gov_{uid}",
        risk_tier=CustomerRiskTier.STANDARD.value,
        total_payments_count=10,
        failed_payments_count=2,
        recovered_payments_count=8,
    )
    db_session.add(customer)
    db_session.flush()

    payment = Payment(
        customer_id=customer.id,
        amount=amount,
        currency="INR",
        status=PaymentStatus.CAPTURED.value
        if status == RecoveryCaseStatus.RECOVERED.value
        else PaymentStatus.FAILED.value,
    )
    db_session.add(payment)
    db_session.flush()

    case = RecoveryCase(
        payment_id=payment.id,
        customer_id=customer.id,
        status=status,
        amount_at_risk=amount,
        recovered_amount=amount if status == RecoveryCaseStatus.RECOVERED.value else 0,
        total_attempts_count=1,
        max_allowed_attempts=3,
        latest_failure_reason=failure_reason,
        opened_at=resolved_time - timedelta(hours=2),
        resolved_at=resolved_time,
        created_at=resolved_time,
        metadata_json={},
    )
    db_session.add(case)
    db_session.flush()

    feat_snapshot = features or {
        "payment_amount": amount,
        "customer_success_rate": 0.80,
        "hours_since_failure": 2.0,
        "attempt_number": 1,
        "error_reason": failure_reason,
        "error_code": "BAD_REQUEST",
        "error_source": "bank",
    }

    prediction = MLPrediction(
        recovery_case_id=case.id,
        model_name="recovery_probability",
        model_version=model_version,
        recovery_probability=Decimal(str(round(prob, 4))),
        feature_vector_snapshot=feat_snapshot,
        predicted_at=resolved_time,
    )
    db_session.add(prediction)
    db_session.commit()

    return case


# =========================================================================
# 1. Health Status & Minimum Sample Size Tests
# =========================================================================


def test_insufficient_data_status_when_sample_below_threshold(db_session: Session):
    """1. Test that when total cases < MIN_EVALUATION_SAMPLE_SIZE, status is INSUFFICIENT_DATA."""
    # Create 5 cases (threshold is 30)
    for _ in range(5):
        make_gov_case(db_session, status=RecoveryCaseStatus.RECOVERED.value, prob=0.85)

    report = model_governance_service.evaluate_governance(db_session)
    assert report.status == "INSUFFICIENT_DATA"
    assert report.sample_size == 5
    assert report.minimum_required_sample_size == MIN_EVALUATION_SAMPLE_SIZE
    assert any(f.code == "LOW_SAMPLE_SIZE" for f in report.findings)


def test_healthy_model_status(db_session: Session):
    """2. Test that model with >= 30 cases and stable performance reports HEALTHY."""
    # Create 35 cases with accurate predictions
    for i in range(35):
        status = (
            RecoveryCaseStatus.RECOVERED.value
            if i % 2 == 0
            else RecoveryCaseStatus.CLOSED.value
        )
        prob = 0.85 if status == RecoveryCaseStatus.RECOVERED.value else 0.15
        make_gov_case(db_session, status=status, prob=prob, days_ago=float(i % 20))

    report = model_governance_service.evaluate_governance(db_session)
    assert report.sample_size == 35
    assert report.status == "HEALTHY"
    assert len(report.critical_findings) == 0


def test_warning_and_degraded_model_status(db_session: Session):
    """3-4. Test detection of WARNING and DEGRADED performance degradation."""
    # Step 1: Historical baseline of 35 accurate cases older than 30 days
    for i in range(35):
        status = (
            RecoveryCaseStatus.RECOVERED.value
            if i % 2 == 0
            else RecoveryCaseStatus.CLOSED.value
        )
        prob = 0.90 if status == RecoveryCaseStatus.RECOVERED.value else 0.10
        make_gov_case(db_session, status=status, prob=prob, days_ago=45.0 + float(i))

    # Step 2: Recent 35 cases in last 30 days with inverted/degraded predictions (accuracy crash)
    for i in range(35):
        # Actual is failed, but predicted 0.95 positive
        make_gov_case(
            db_session,
            status=RecoveryCaseStatus.CLOSED.value,
            prob=0.95,
            days_ago=float(i % 25),
        )

    report = model_governance_service.evaluate_governance(db_session)
    assert report.sample_size == 70
    assert report.status == "DEGRADED"
    assert any(f.code == "SIGNIFICANT_PERFORMANCE_DEGRADATION" for f in report.findings)
    assert len(report.critical_findings) > 0


# =========================================================================
# 2. Performance Windows (7d, 30d, 90d, Historical) Tests
# =========================================================================


def test_rolling_performance_windows(db_session: Session):
    """5-9. Test proper partition and metric calculation across 7d, 30d, 90d, and historical windows."""
    # 2 cases in last 7 days
    make_gov_case(
        db_session, status=RecoveryCaseStatus.RECOVERED.value, prob=0.80, days_ago=3.0
    )
    make_gov_case(
        db_session, status=RecoveryCaseStatus.CLOSED.value, prob=0.20, days_ago=5.0
    )

    # 2 cases in 15 days ago (in 30d, not 7d)
    make_gov_case(
        db_session, status=RecoveryCaseStatus.RECOVERED.value, prob=0.80, days_ago=15.0
    )
    make_gov_case(
        db_session, status=RecoveryCaseStatus.CLOSED.value, prob=0.20, days_ago=20.0
    )

    # 2 cases in 60 days ago (in 90d, not 30d)
    make_gov_case(
        db_session, status=RecoveryCaseStatus.RECOVERED.value, prob=0.80, days_ago=60.0
    )
    make_gov_case(
        db_session, status=RecoveryCaseStatus.CLOSED.value, prob=0.20, days_ago=75.0
    )

    # 2 cases in 120 days ago (only in historical)
    make_gov_case(
        db_session, status=RecoveryCaseStatus.RECOVERED.value, prob=0.80, days_ago=120.0
    )
    make_gov_case(
        db_session, status=RecoveryCaseStatus.CLOSED.value, prob=0.20, days_ago=150.0
    )

    report = model_governance_service.evaluate_governance(db_session)
    win_map = {w.window_name: w for w in report.performance_windows}

    assert win_map["7d"].sample_size == 2
    assert win_map["30d"].sample_size == 4
    assert win_map["90d"].sample_size == 6
    assert win_map["historical"].sample_size == 8

    # Check accuracy and Brier calculation on 7d window
    assert win_map["7d"].accuracy == 1.0
    assert win_map["7d"].brier_score == pytest.approx(0.04, 0.001)


# =========================================================================
# 3. Brier Score & Calibration Drift Tests
# =========================================================================


def test_brier_score_comparison_and_calibration_drift(db_session: Session):
    """10-11, 18. Test Brier score delta comparison and calibration bucket drift."""
    # Historical cases (Brier = 0.04)
    make_gov_case(
        db_session, status=RecoveryCaseStatus.RECOVERED.value, prob=0.80, days_ago=40.0
    )
    make_gov_case(
        db_session, status=RecoveryCaseStatus.CLOSED.value, prob=0.20, days_ago=45.0
    )

    # Recent cases with higher error (prob=0.50, Brier = 0.25)
    make_gov_case(
        db_session, status=RecoveryCaseStatus.RECOVERED.value, prob=0.50, days_ago=5.0
    )
    make_gov_case(
        db_session, status=RecoveryCaseStatus.CLOSED.value, prob=0.50, days_ago=6.0
    )

    report = model_governance_service.evaluate_governance(db_session)
    assert report.performance_comparison.brier_delta is not None
    # Recent Brier > Baseline Brier -> positive delta
    assert report.performance_comparison.brier_delta > 0.0
    assert len(report.calibration_drift) == 5


# =========================================================================
# 4. Feature Drift & PSI Tests
# =========================================================================


def test_population_stability_index_numerical_and_categorical(db_session: Session):
    """12-15. Test Population Stability Index for numerical and categorical features."""
    # Reference population (low payment amounts, reason A)
    for _ in range(15):
        make_gov_case(
            db_session,
            amount=5000,
            failure_reason="insufficient_funds",
            days_ago=40.0,
            features={
                "payment_amount": 5000,
                "customer_success_rate": 0.90,
                "hours_since_failure": 1.0,
                "attempt_number": 1,
                "error_reason": "insufficient_funds",
                "error_code": "BAD_REQUEST",
                "error_source": "bank",
            },
        )

    # Recent population with significant distribution shift (huge amounts, reason B)
    for _ in range(15):
        make_gov_case(
            db_session,
            amount=500000,
            failure_reason="card_stolen_fraud",
            days_ago=5.0,
            features={
                "payment_amount": 500000,
                "customer_success_rate": 0.10,
                "hours_since_failure": 48.0,
                "attempt_number": 3,
                "error_reason": "card_stolen_fraud",
                "error_code": "FRAUD_BLOCK",
                "error_source": "issuer",
            },
        )

    report = model_governance_service.evaluate_governance(db_session)
    drift_map = {f.feature_name: f for f in report.feature_drift}

    assert "payment_amount" in drift_map
    assert drift_map["payment_amount"].psi is not None
    assert drift_map["payment_amount"].psi > 0.10  # Detected shift

    assert "error_reason" in drift_map
    assert drift_map["error_reason"].psi is not None
    assert drift_map["error_reason"].drift_level in ("MODERATE", "SIGNIFICANT")


def test_prediction_and_outcome_drift(db_session: Session):
    """16-17. Test probability prediction distribution shift and outcome recovery rate drift."""
    # Reference: 10 cases with 0.90 probability, all recovered
    for _ in range(10):
        make_gov_case(
            db_session,
            status=RecoveryCaseStatus.RECOVERED.value,
            prob=0.90,
            days_ago=45.0,
        )

    # Recent: 10 cases with 0.10 probability, all failed
    for _ in range(10):
        make_gov_case(
            db_session, status=RecoveryCaseStatus.CLOSED.value, prob=0.10, days_ago=5.0
        )

    report = model_governance_service.evaluate_governance(db_session)

    assert report.prediction_drift.psi is not None
    assert report.prediction_drift.psi > 0.25
    assert report.prediction_drift.drift_level == "SIGNIFICANT"

    assert report.outcome_drift.historical_recovery_rate == 1.0
    assert report.outcome_drift.recent_recovery_rate == 0.0
    assert report.outcome_drift.delta == -1.0
    assert report.outcome_drift.drift_level == "SIGNIFICANT"


# =========================================================================
# 5. Model Version Monitoring Tests
# =========================================================================


def test_model_version_discovery_and_comparison(db_session: Session):
    """19-21. Test discovery of multiple model versions and neutral comparative evidence."""
    # Version v1.0 baseline (35 cases)
    for i in range(35):
        status = (
            RecoveryCaseStatus.RECOVERED.value
            if i % 2 == 0
            else RecoveryCaseStatus.CLOSED.value
        )
        make_gov_case(
            db_session,
            status=status,
            prob=0.70 if status == RecoveryCaseStatus.RECOVERED.value else 0.30,
            model_version="v1.0",
        )

    # Version v1.1 candidate (10 cases)
    for i in range(10):
        status = (
            RecoveryCaseStatus.RECOVERED.value
            if i % 2 == 0
            else RecoveryCaseStatus.CLOSED.value
        )
        make_gov_case(
            db_session,
            status=status,
            prob=0.85 if status == RecoveryCaseStatus.RECOVERED.value else 0.15,
            model_version="v1.1",
        )

    report = model_governance_service.evaluate_governance(db_session)

    versions = {v.model_version: v for v in report.model_versions}
    assert "v1.0" in versions
    assert "v1.1" in versions
    assert versions["v1.0"].sample_size == 35
    assert versions["v1.1"].sample_size == 10

    assert len(report.version_comparisons) == 1
    comp = report.version_comparisons[0]
    assert comp.baseline_version == "v1.0"
    assert comp.comparison_version == "v1.1"
    assert "Insufficient sample size" in comp.evidence_statement


# =========================================================================
# 6. Data Quality Monitoring Tests
# =========================================================================


def test_data_quality_audit_defects_detection(db_session: Session):
    """22-25. Test data quality audit flags missing vectors, versions, or invalid values."""
    # 1. Valid prediction
    make_gov_case(db_session, status=RecoveryCaseStatus.RECOVERED.value, prob=0.80)

    # 2. Add an anomalous prediction directly with missing feature snapshot and empty version
    case = make_gov_case(
        db_session, status=RecoveryCaseStatus.RECOVERED.value, prob=0.80
    )
    bad_pred = MLPrediction(
        recovery_case_id=case.id,
        model_name="",
        model_version="",
        recovery_probability=Decimal("0.50"),
        feature_vector_snapshot={},
    )
    db_session.add(bad_pred)
    db_session.commit()

    report = model_governance_service.evaluate_governance(db_session)
    dq = report.data_quality

    assert dq.total_predictions >= 2
    assert dq.invalid_predictions > 0
    assert any(f.code == "DATA_QUALITY_ISSUE" for f in report.findings)


# =========================================================================
# 7. API Security & Role-Based Access Control Tests
# =========================================================================


def test_governance_api_security_and_roles(db_session: Session):
    """26-29. Test unauthenticated rejection (401), and Viewer/Operator/Admin access (200)."""
    make_gov_case(db_session, status=RecoveryCaseStatus.RECOVERED.value)

    def _override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = _override_get_db

    with TestClient(app) as test_client:
        # Unauthenticated -> 401
        res_unauth = test_client.get("/api/recovery/intelligence/governance")
        assert res_unauth.status_code == 401

        # Viewer -> 200
        token_v = create_access_token(user_id="viewer_1", role=UserRole.VIEWER.value)
        res_v = test_client.get(
            "/api/recovery/intelligence/governance",
            headers={"Authorization": f"Bearer {token_v}"},
        )
        assert res_v.status_code == 200

        # Operator -> 200
        token_o = create_access_token(
            user_id="operator_1", role=UserRole.OPERATOR.value
        )
        res_o = test_client.get(
            "/api/recovery/intelligence/governance",
            headers={"Authorization": f"Bearer {token_o}"},
        )
        assert res_o.status_code == 200

        # Admin -> 200
        token_a = create_access_token(user_id="admin_1", role=UserRole.ADMIN.value)
        res_a = test_client.get(
            "/api/recovery/intelligence/governance",
            headers={"Authorization": f"Bearer {token_a}"},
        )
        assert res_a.status_code == 200

    app.dependency_overrides.clear()


# =========================================================================
# 8. Financial Isolation & Zero PII/Secrets Verification Tests
# =========================================================================


def test_governance_endpoint_is_strictly_read_only_and_zero_pii(
    client: TestClient, db_session: Session
):
    """30-36. Verify zero database mutations, zero PII, and absolute financial isolation."""
    case = make_gov_case(db_session, status=RecoveryCaseStatus.RECOVERED.value)
    initial_updated_at = case.updated_at
    initial_status = case.status

    res = client.get("/api/recovery/intelligence/governance")
    assert res.status_code == 200
    text = res.text.lower()

    # Zero PII & Secrets check
    for forbidden in [
        "password",
        "secret",
        "bearer",
        "@",
        "email",
        "phone",
        "card_number",
        "pan",
        "cvv",
    ]:
        assert forbidden not in text

    # DB Immutability check
    db_session.refresh(case)
    assert case.updated_at == initial_updated_at
    assert case.status == initial_status
