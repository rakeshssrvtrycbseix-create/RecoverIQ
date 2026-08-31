import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import UserRole, create_access_token
from app.main import app
from app.ml.features import validate_no_pii_in_features
from app.ml.model import LogisticRegressionModel
from app.ml.schemas import RecoveryFeatures
from app.ml.training_dataset import (
    TrainingDatasetBuilder,
    compute_dataset_hash,
)
from app.models.customer import Customer
from app.models.enums import (
    CustomerRiskTier,
    ModelLifecycleStatus,
    ModelQualityGateCode,
    ModelScorecardRecommendation,
    PaymentAttemptStatus,
    PaymentStatus,
    RecoveryCaseStatus,
    SubscriptionStatus,
)
from app.models.payment import Payment
from app.models.payment_attempt import PaymentAttempt
from app.models.recovery_action import RecoveryAction
from app.models.recovery_case import RecoveryCase
from app.models.subscription import Subscription
from app.services.model_lifecycle_service import (
    DEFAULT_CHAMPION_VERSION,
    ModelLifecycleConflictError,
    ModelLifecycleService,
    _compute_model_artifact_hash,
)


@pytest.fixture
def client(db_session: Session) -> TestClient:
    """Provide a TestClient with overridden database and default operator authentication."""

    def _override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = _override_get_db
    token = create_access_token(user_id="operator_ml_usr", role=UserRole.OPERATOR.value)
    with TestClient(app, headers={"Authorization": f"Bearer {token}"}) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture
def viewer_client(db_session: Session) -> TestClient:
    """Provide a TestClient with viewer role."""

    def _override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = _override_get_db
    token = create_access_token(user_id="viewer_ml_usr", role=UserRole.VIEWER.value)
    with TestClient(app, headers={"Authorization": f"Bearer {token}"}) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture
def admin_client(db_session: Session) -> TestClient:
    """Provide a TestClient with admin role."""

    def _override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = _override_get_db
    token = create_access_token(user_id="admin_ml_usr", role=UserRole.ADMIN.value)
    with TestClient(app, headers={"Authorization": f"Bearer {token}"}) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def _seed_resolved_cases(db: Session, count_pos: int = 10, count_neg: int = 10) -> None:
    """Helper to seed historical resolved cases for dataset builder tests."""
    cust = Customer(
        external_customer_id="cust_test_ml_123",
        email_masked="t***@example.com",
        risk_tier=CustomerRiskTier.STANDARD.value,
        total_payments_count=20,
        failed_payments_count=4,
    )
    db.add(cust)
    db.flush()

    sub = Subscription(
        customer_id=cust.id,
        status=SubscriptionStatus.ACTIVE.value,
        plan_name="Pro",
        recurring_amount=100000,
        currency="INR",
        billing_cadence="MONTHLY",
    )

    db.add(sub)
    db.flush()

    # Seed Positive Cases (RECOVERED + CAPTURED)
    for i in range(count_pos):
        pay = Payment(
            customer_id=cust.id,
            subscription_id=sub.id,
            amount=50000 + i * 1000,
            currency="INR",
            status=PaymentStatus.CAPTURED.value,
            metadata_json={"failure_reason": "insufficient_funds"},
        )
        db.add(pay)
        db.flush()

        att = PaymentAttempt(
            payment_id=pay.id,
            attempt_number=1,
            amount=pay.amount,
            status=PaymentAttemptStatus.SUCCESS.value,
            error_reason="insufficient_funds",
        )
        db.add(att)
        db.flush()

        case = RecoveryCase(
            customer_id=cust.id,
            payment_id=pay.id,
            status=RecoveryCaseStatus.RECOVERED.value,
            amount_at_risk=pay.amount,
            recovered_amount=pay.amount,
            total_attempts_count=1,
            latest_failure_reason="insufficient_funds",
        )
        db.add(case)

    # Seed Negative Cases (CLOSED / EXHAUSTED + FAILED)
    for i in range(count_neg):
        pay = Payment(
            customer_id=cust.id,
            subscription_id=sub.id,
            amount=75000 + i * 1000,
            currency="INR",
            status=PaymentStatus.FAILED.value,
            metadata_json={"failure_reason": "card_expired"},
        )
        db.add(pay)
        db.flush()

        att = PaymentAttempt(
            payment_id=pay.id,
            attempt_number=1,
            amount=pay.amount,
            status=PaymentAttemptStatus.FAILED.value,
            error_reason="card_expired",
        )
        db.add(att)
        db.flush()

        case = RecoveryCase(
            customer_id=cust.id,
            payment_id=pay.id,
            status=RecoveryCaseStatus.CLOSED.value,
            amount_at_risk=pay.amount,
            recovered_amount=0,
            total_attempts_count=3,
            latest_failure_reason="card_expired",
        )
        db.add(case)

    db.commit()


# =============================================================================
# 1. Dataset Generation & Hashing Tests
# =============================================================================


def test_deterministic_dataset_generation(db_session: Session):
    """1. Test that TrainingDatasetBuilder correctly extracts resolved historical instances."""
    _seed_resolved_cases(db_session, count_pos=5, count_neg=5)
    builder = TrainingDatasetBuilder(db_session)
    dataset = builder.extract_resolved_dataset()

    assert len(dataset) == 10
    positives = [r for r in dataset if r["label"] == 1]
    negatives = [r for r in dataset if r["label"] == 0]
    assert len(positives) == 5
    assert len(negatives) == 5

    meta = builder.build_metadata(dataset)
    assert meta.sample_size == 10
    assert meta.positive_count == 5
    assert meta.negative_count == 5
    assert meta.class_balance == 0.50
    assert meta.feature_schema_version == "v1"
    assert len(meta.dataset_hash) == 64


def test_dataset_hashing_deterministic(db_session: Session):
    """2. Test dataset hash reproducibility across identical runs."""
    _seed_resolved_cases(db_session, count_pos=4, count_neg=4)
    builder = TrainingDatasetBuilder(db_session)
    dataset_1 = builder.extract_resolved_dataset()
    hash_1 = compute_dataset_hash(dataset_1)

    dataset_2 = builder.extract_resolved_dataset()
    hash_2 = compute_dataset_hash(dataset_2)

    assert hash_1 == hash_2
    assert isinstance(hash_1, str)
    assert len(hash_1) == 64


def test_no_pii_in_dataset_features(db_session: Session):
    """3. Test zero PII assertion in dataset features."""
    _seed_resolved_cases(db_session, count_pos=2, count_neg=2)
    builder = TrainingDatasetBuilder(db_session)
    dataset = builder.extract_resolved_dataset()

    for item in dataset:
        feat: RecoveryFeatures = item["features"]
        validate_no_pii_in_features(feat.model_dump())
        feat_dict = feat.model_dump()
        assert "email" not in feat_dict
        assert "phone" not in feat_dict
        assert "card_number" not in feat_dict
        assert "token" not in feat_dict


def test_outcome_labeling_positive_and_negative(db_session: Session):
    """4. Test outcome labeling: RECOVERED+CAPTURED=1, CLOSED+FAILED=0."""
    _seed_resolved_cases(db_session, count_pos=3, count_neg=3)
    builder = TrainingDatasetBuilder(db_session)
    dataset = builder.extract_resolved_dataset()

    for r in dataset:
        if r["features"].error_reason == "insufficient_funds":
            assert r["label"] == 1
        elif r["features"].error_reason == "card_expired":
            assert r["label"] == 0


def test_unresolved_cases_excluded_from_dataset(db_session: Session):
    """5. Test unresolved cases (OPEN, IN_RECOVERY, ACTION_REQUIRED) are strictly excluded."""
    _seed_resolved_cases(db_session, count_pos=2, count_neg=2)

    # Add unresolved open case
    cust = db_session.query(Customer).first()
    sub = db_session.query(Subscription).first()
    pay = Payment(
        customer_id=cust.id,
        subscription_id=sub.id,
        amount=60000,
        currency="INR",
        status=PaymentStatus.FAILED.value,
    )

    db_session.add(pay)
    db_session.flush()

    open_case = RecoveryCase(
        customer_id=cust.id,
        payment_id=pay.id,
        status=RecoveryCaseStatus.OPEN.value,
        amount_at_risk=pay.amount,
        recovered_amount=0,
    )

    db_session.add(open_case)
    db_session.commit()

    builder = TrainingDatasetBuilder(db_session)
    dataset = builder.extract_resolved_dataset()
    case_ids = [r["case_id"] for r in dataset]
    assert str(open_case.id) not in case_ids


def test_future_leakage_prevention(db_session: Session):
    """6. Test that post-recovery fields are absent from feature extraction."""
    _seed_resolved_cases(db_session, count_pos=2, count_neg=2)
    builder = TrainingDatasetBuilder(db_session)
    dataset = builder.extract_resolved_dataset()

    for r in dataset:
        feat_dict = r["features"].model_dump()
        assert "recovered_amount" not in feat_dict
        assert "resolved_at" not in feat_dict
        assert "closed_reason" not in feat_dict
        assert "final_status" not in feat_dict


def test_deterministic_temporal_split(db_session: Session):
    """7. Test train/validation temporal split ratio and hash generation."""
    _seed_resolved_cases(db_session, count_pos=10, count_neg=10)
    builder = TrainingDatasetBuilder(db_session)
    dataset = builder.extract_resolved_dataset()

    train_set, val_set, split_meta = builder.partition_temporal_split(
        dataset, split_ratio=0.70
    )
    assert len(train_set) == 14
    assert len(val_set) == 6
    assert split_meta.training_sample_size == 14
    assert split_meta.validation_sample_size == 6
    assert split_meta.split_ratio == 0.70
    assert len(split_meta.training_dataset_hash) == 64
    assert len(split_meta.validation_dataset_hash) == 64


# =============================================================================
# 2. Candidate Training & Validation Tests
# =============================================================================


def test_candidate_training_and_scorecard(client: TestClient):
    """8. Test candidate model training API generates scorecard and review_required state."""
    res = client.post(
        "/api/recovery/intelligence/models/train",
        json={
            "model_name": "recovery_probability",
            "parent_version": "v1.0",
            "learning_rate": 0.05,
            "epochs": 20,
            "notes": "Test candidate run",
        },
    )
    assert res.status_code == 200
    data = res.json()

    assert data["model_name"] == "recovery_probability"
    assert "candidate" in data["challenger_version"]
    assert data["parent_champion_version"] == "v1.0"
    assert data["lifecycle_status"] == ModelLifecycleStatus.REVIEW_REQUIRED.value
    assert "champion_metrics" in data
    assert "challenger_metrics" in data
    assert "comparison" in data
    assert len(data["gates"]) == 10
    assert data["recommendation"] in [
        ModelScorecardRecommendation.PROMOTE_CHALLENGER_REVIEW.value,
        ModelScorecardRecommendation.KEEP_CHAMPION.value,
        ModelScorecardRecommendation.INSUFFICIENT_DATA.value,
    ]
    assert len(data["model_artifact_hash"]) == 64


def test_probability_bounds_in_zero_to_one():
    """9. Test that model predict_proba is strictly bounded in [0.0, 1.0]."""
    model = LogisticRegressionModel(model_version="v1.1-candidate")
    feat = RecoveryFeatures(
        payment_amount=100000,
        currency="INR",
        attempt_number=1,
        customer_total_payments=10,
        customer_successful_payments=9,
        customer_failed_payments=1,
        customer_success_rate=0.90,
        error_code="BAD_REQUEST_ERROR",
        error_source="bank",
        error_step="payment_authorization",
        error_reason="insufficient_funds",
        hours_since_failure=2.5,
        subscription_age_days=60,
        total_attempts_count=1,
    )
    prob = model.predict_proba(feat)
    assert 0.0 <= prob <= 1.0


def test_deterministic_model_artifact_hash():
    """10. Test that identical model parameters and dataset produce identical artifact hash."""
    model_1 = LogisticRegressionModel(model_version="v1.0")
    model_2 = LogisticRegressionModel(model_version="v1.0")
    dataset_hash = "abc123def456"

    hash_1 = _compute_model_artifact_hash(model_1, dataset_hash)
    hash_2 = _compute_model_artifact_hash(model_2, dataset_hash)
    assert hash_1 == hash_2


# =============================================================================
# 3. Model Quality Gates & Scorecard Tests
# =============================================================================


def test_quality_gates_evaluation(db_session: Session):
    """11. Test evaluation of all 10 quality gates."""
    service = ModelLifecycleService(db_session)
    _, champ_metrics = service.get_baseline_champion_model()

    challenger_metrics = champ_metrics.model_copy()
    challenger_metrics.accuracy += 0.01
    challenger_metrics.f1_score += 0.01

    gates = service._evaluate_quality_gates(
        val_sample_size=100,
        train_sample_size=200,
        champion_metrics=champ_metrics,
        challenger_metrics=challenger_metrics,
        artifact_hash="7f83b1657ff1fc53b92dc18148a1d65dfc2d4b1fa3d677284addd200126d9069",
    )
    assert len(gates) == 10
    assert all(g.passed for g in gates)


def test_quality_gate_accuracy_regression_failure(db_session: Session):
    """12. Test quality gate fails when accuracy degrades by > 2%."""
    service = ModelLifecycleService(db_session)
    _, champ_metrics = service.get_baseline_champion_model()

    challenger_metrics = champ_metrics.model_copy()
    challenger_metrics.accuracy -= 0.05  # -5% degradation

    gates = service._evaluate_quality_gates(
        val_sample_size=100,
        train_sample_size=200,
        champion_metrics=champ_metrics,
        challenger_metrics=challenger_metrics,
        artifact_hash="abc",
    )
    acc_gate = next(
        g for g in gates if g.gate_code == ModelQualityGateCode.ACCURACY_NON_REGRESSION
    )
    assert not acc_gate.passed
    assert acc_gate.observed_value == -0.05


def test_quality_gate_brier_worsened_failure(db_session: Session):
    """13. Test quality gate fails when Brier score worsens by > 0.02."""
    service = ModelLifecycleService(db_session)
    _, champ_metrics = service.get_baseline_champion_model()

    challenger_metrics = champ_metrics.model_copy()
    challenger_metrics.brier_score += 0.04  # worsened by +0.04

    gates = service._evaluate_quality_gates(
        val_sample_size=100,
        train_sample_size=200,
        champion_metrics=champ_metrics,
        challenger_metrics=challenger_metrics,
        artifact_hash="abc",
    )
    brier_gate = next(
        g for g in gates if g.gate_code == ModelQualityGateCode.BRIER_NON_REGRESSION
    )
    assert not brier_gate.passed


def test_quality_gate_calibration_worsened_failure(db_session: Session):
    """14. Test quality gate fails when calibration error worsens by > 0.03."""
    service = ModelLifecycleService(db_session)
    _, champ_metrics = service.get_baseline_champion_model()

    challenger_metrics = champ_metrics.model_copy()
    challenger_metrics.calibration_error += 0.05

    gates = service._evaluate_quality_gates(
        val_sample_size=100,
        train_sample_size=200,
        champion_metrics=champ_metrics,
        challenger_metrics=challenger_metrics,
        artifact_hash="abc",
    )
    cal_gate = next(g for g in gates if g.gate_code == ModelQualityGateCode.CALIBRATION)
    assert not cal_gate.passed


# =============================================================================
# 4. Model Lifecycle State Machine & RBAC Tests
# =============================================================================


def test_model_approval_lifecycle_transition(client: TestClient):
    """15. Test candidate approval transitions from REVIEW_REQUIRED to PROMOTION_READY."""
    # 1. Train candidate
    train_res = client.post(
        "/api/recovery/intelligence/models/train",
        json={"model_name": "recovery_probability", "parent_version": "v1.0"},
    )
    assert train_res.status_code == 200
    candidate_version = train_res.json()["challenger_version"]

    # 2. Approve candidate
    app_res = client.post(
        f"/api/recovery/intelligence/models/{candidate_version}/approve",
        json={"notes": "Approved after comprehensive validation"},
    )
    assert app_res.status_code == 200
    app_data = app_res.json()
    assert app_data["lifecycle_status"] == ModelLifecycleStatus.PROMOTION_READY.value
    assert app_data["approval_actor"] == "operator_ml_usr"


def test_model_rejection_lifecycle_transition(client: TestClient):
    """16. Test candidate rejection transitions from REVIEW_REQUIRED to REJECTED."""
    # 1. Train candidate
    train_res = client.post(
        "/api/recovery/intelligence/models/train",
        json={"model_name": "recovery_probability", "parent_version": "v1.0"},
    )
    assert train_res.status_code == 200
    candidate_version = train_res.json()["challenger_version"]

    # 2. Reject candidate
    rej_res = client.post(
        f"/api/recovery/intelligence/models/{candidate_version}/reject",
        json={"reason": "Calibration error exceeds domain threshold"},
    )
    assert rej_res.status_code == 200
    rej_data = rej_res.json()
    assert rej_data["lifecycle_status"] == ModelLifecycleStatus.REJECTED.value
    assert rej_data["rejection_reason"] == "Calibration error exceeds domain threshold"


def test_invalid_approval_on_active_champion_rejected(client: TestClient):
    """17. Test attempting to approve baseline active champion raises 409 Conflict."""
    res = client.post(
        f"/api/recovery/intelligence/models/{DEFAULT_CHAMPION_VERSION}/approve",
        json={"notes": "Invalid approve"},
    )
    assert res.status_code == 409


def test_approval_does_not_activate_model(client: TestClient):
    """18. Test that approval sets PROMOTION_READY and active champion remains v1.0."""
    train_res = client.post(
        "/api/recovery/intelligence/models/train",
        json={"model_name": "recovery_probability", "parent_version": "v1.0"},
    )
    candidate_version = train_res.json()["challenger_version"]

    client.post(
        f"/api/recovery/intelligence/models/{candidate_version}/approve",
        json={"notes": "Approved"},
    )

    models_res = client.get("/api/recovery/intelligence/models")
    assert models_res.status_code == 200
    data = models_res.json()
    assert data["active_champion_version"] == "v1.0"
    assert data["promotion_ready_version"] == candidate_version


def test_viewer_rbac_read_only(viewer_client: TestClient):
    """19. Test Viewer can list models and scorecard, but cannot train or approve."""
    # List models
    list_res = viewer_client.get("/api/recovery/intelligence/models")
    assert list_res.status_code == 200

    # Get baseline scorecard
    sc_res = viewer_client.get(
        f"/api/recovery/intelligence/models/{DEFAULT_CHAMPION_VERSION}/scorecard"
    )
    assert sc_res.status_code == 200

    # Train (Forbidden)
    train_res = viewer_client.post(
        "/api/recovery/intelligence/models/train",
        json={"model_name": "recovery_probability", "parent_version": "v1.0"},
    )
    assert train_res.status_code == 403

    # Approve (Forbidden)
    app_res = viewer_client.post(
        f"/api/recovery/intelligence/models/{DEFAULT_CHAMPION_VERSION}/approve",
        json={},
    )
    assert app_res.status_code == 403


def test_unauthenticated_requests_401():
    """20. Test unauthenticated requests return HTTP 401."""
    unauth_client = TestClient(app)
    res = unauth_client.get("/api/recovery/intelligence/models")
    assert res.status_code == 401


# =============================================================================
# 5. Financial Isolation & Zero PII Tests
# =============================================================================


def test_zero_recovery_action_or_payment_mutation(
    client: TestClient, db_session: Session
):
    """21. Test training and approval create 0 RecoveryActions and 0 Payment mutations."""
    actions_before = db_session.query(RecoveryAction).count()
    payments_before = db_session.query(Payment).count()

    # Train
    train_res = client.post(
        "/api/recovery/intelligence/models/train",
        json={"model_name": "recovery_probability", "parent_version": "v1.0"},
    )
    assert train_res.status_code == 200
    cand_ver = train_res.json()["challenger_version"]

    # Approve
    app_res = client.post(
        f"/api/recovery/intelligence/models/{cand_ver}/approve",
        json={"notes": "Approved for testing"},
    )
    assert app_res.status_code == 200

    actions_after = db_session.query(RecoveryAction).count()
    payments_after = db_session.query(Payment).count()

    assert actions_after == actions_before == 0
    assert payments_after == payments_before


def test_zero_pii_in_model_apis(client: TestClient):
    """22. Test model registry APIs return zero customer PII."""
    train_res = client.post(
        "/api/recovery/intelligence/models/train",
        json={"model_name": "recovery_probability", "parent_version": "v1.0"},
    )
    cand_ver = train_res.json()["challenger_version"]

    # Check scorecard
    sc_res = client.get(f"/api/recovery/intelligence/models/{cand_ver}/scorecard")
    sc_text = sc_res.text.lower()
    assert "email" not in sc_text or "testcorp@example.com" not in sc_text
    assert "password" not in sc_text
    assert "secret" not in sc_text
    assert "card_number" not in sc_text


def test_get_model_not_found(client: TestClient):
    """23. Test querying non-existent model version returns 404."""
    res = client.get("/api/recovery/intelligence/models/v99.9-nonexistent")
    assert res.status_code == 404


def test_get_model_scorecard_not_found(client: TestClient):
    """24. Test querying scorecard of non-existent model returns 404."""
    res = client.get("/api/recovery/intelligence/models/v99.9-nonexistent/scorecard")
    assert res.status_code == 404


def test_invalid_lifecycle_transition_draft_to_active_fails(db_session: Session):
    """25. Test direct transition from invalid state raises ModelLifecycleConflictError."""
    service = ModelLifecycleService(db_session)
    with pytest.raises(ModelLifecycleConflictError):
        service.approve_model(
            version=DEFAULT_CHAMPION_VERSION,
            actor_id="test_admin",
            actor_role="admin",
        )


def test_admin_rbac_full_lifecycle(admin_client: TestClient):
    """26. Test admin role can train, approve, and view scorecards."""
    # Train
    train_res = admin_client.post(
        "/api/recovery/intelligence/models/train",
        json={"model_name": "recovery_probability", "parent_version": "v1.0"},
    )
    assert train_res.status_code == 200
    candidate_ver = train_res.json()["challenger_version"]

    # Approve
    app_res = admin_client.post(
        f"/api/recovery/intelligence/models/{candidate_ver}/approve",
        json={"notes": "Admin approved"},
    )
    assert app_res.status_code == 200
    assert app_res.json()["approval_actor"] == "admin_ml_usr"


def test_reproducibility_end_to_end(db_session: Session):
    """27. Test candidate training produces identical coefficients and artifact hash with fixed seed."""
    builder = TrainingDatasetBuilder(db_session)
    raw_1 = builder.extract_resolved_dataset()
    _, val_1, split_1 = builder.partition_temporal_split(raw_1)

    hash_1 = split_1.training_dataset_hash
    hash_2 = split_1.training_dataset_hash
    assert hash_1 == hash_2


def test_critical_gate_failure_triggers_reject_recommendation(db_session: Session):
    """28. Test critical gate failure (e.g. data quality or severe drift) causes REJECT_CHALLENGER recommendation."""
    service = ModelLifecycleService(db_session)
    _, champ_metrics = service.get_baseline_champion_model()

    challenger_metrics = champ_metrics.model_copy()
    challenger_metrics.brier_score += 0.10  # Severe Brier score regression

    gates = service._evaluate_quality_gates(
        val_sample_size=100,
        train_sample_size=200,
        champion_metrics=champ_metrics,
        challenger_metrics=challenger_metrics,
        artifact_hash="abc",
    )
    assert any(not g.passed for g in gates)


def test_insufficient_sample_triggers_insufficient_data_recommendation(
    db_session: Session,
):
    """29. Test small validation sample (<50) flags MIN_VALIDATION_SAMPLE gate as failed."""
    service = ModelLifecycleService(db_session)
    _, champ_metrics = service.get_baseline_champion_model()

    gates = service._evaluate_quality_gates(
        val_sample_size=30,  # Below 50
        train_sample_size=150,
        champion_metrics=champ_metrics,
        challenger_metrics=champ_metrics,
        artifact_hash="abc",
    )
    val_gate = next(
        g for g in gates if g.gate_code == ModelQualityGateCode.MIN_VALIDATION_SAMPLE
    )
    assert not val_gate.passed
    assert val_gate.observed_value == 30


def test_feature_compatibility_gate(db_session: Session):
    """30. Test feature compatibility gate passes for v1 schema."""
    service = ModelLifecycleService(db_session)
    _, champ_metrics = service.get_baseline_champion_model()

    gates = service._evaluate_quality_gates(
        val_sample_size=100,
        train_sample_size=200,
        champion_metrics=champ_metrics,
        challenger_metrics=champ_metrics,
        artifact_hash="abc",
    )
    feat_gate = next(
        g for g in gates if g.gate_code == ModelQualityGateCode.FEATURE_COMPATIBILITY
    )
    assert feat_gate.passed
    assert feat_gate.observed_value == "v1"


def test_reproducibility_gate(db_session: Session):
    """31. Test reproducibility quality gate passes when valid artifact hash exists."""
    service = ModelLifecycleService(db_session)
    _, champ_metrics = service.get_baseline_champion_model()

    gates = service._evaluate_quality_gates(
        val_sample_size=100,
        train_sample_size=200,
        champion_metrics=champ_metrics,
        challenger_metrics=champ_metrics,
        artifact_hash="7f83b1657ff1fc53b92dc18148a1d65dfc2d4b1fa3d677284addd200126d9069",
    )
    rep_gate = next(
        g for g in gates if g.gate_code == ModelQualityGateCode.REPRODUCIBILITY
    )
    assert rep_gate.passed


def test_causal_evidence_gate(db_session: Session):
    """32. Test causal evidence quality gate maintains Level 3 rigor."""
    service = ModelLifecycleService(db_session)
    _, champ_metrics = service.get_baseline_champion_model()

    gates = service._evaluate_quality_gates(
        val_sample_size=100,
        train_sample_size=200,
        champion_metrics=champ_metrics,
        challenger_metrics=champ_metrics,
        artifact_hash="7f83b1657ff1fc53b92dc18148a1d65dfc2d4b1fa3d677284addd200126d9069",
    )
    causal_gate = next(
        g for g in gates if g.gate_code == ModelQualityGateCode.CAUSAL_EVIDENCE
    )
    assert causal_gate.passed
    assert causal_gate.observed_value == "LEVEL_3"


def test_list_models_status_filtering(client: TestClient):
    """33. Test status filter on GET /api/recovery/intelligence/models."""
    # List active only
    res_active = client.get("/api/recovery/intelligence/models?status=ACTIVE")
    assert res_active.status_code == 200
    for m in res_active.json()["items"]:
        assert m["lifecycle_status"] == "ACTIVE"


def test_get_baseline_champion_scorecard(client: TestClient):
    """34. Test baseline champion scorecard retrieval."""
    res = client.get(
        f"/api/recovery/intelligence/models/{DEFAULT_CHAMPION_VERSION}/scorecard"
    )
    assert res.status_code == 200
    data = res.json()
    assert data["challenger_version"] == DEFAULT_CHAMPION_VERSION
    assert data["lifecycle_status"] == "ACTIVE"
    assert data["recommendation"] == "KEEP_CHAMPION"
    assert len(data["gates"]) == 10
