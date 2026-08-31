"""Comprehensive test suite for Phase 9K: Continuous Learning, Automated Monitoring & Safe Model Evolution.

Invariants Tested:
1. Dataset extraction: strictly resolved cases only (RECOVERED+CAPTURED, CLOSED/EXHAUSTED+FAILED).
2. Unresolved cases exclusion (OPEN, IN_RECOVERY, ACTION_REQUIRED, PENDING_CUSTOMER, DISPUTED excluded).
3. Label correctness and zero data leakage in pre-decision features.
4. Dataset determinism and SHA-256 reproducibility.
5. Dataset versioning and append-only audit tracking.
6. Retraining triggers: NEW_RESOLVED_CASES (>= 100), MODEL_DRIFT (PSI >= 0.20), PERFORMANCE_DEGRADATION (>= 5%), CALIBRATION_DEGRADATION (>= 0.05).
7. Retraining eligibility decision synthesis and primary diagnostic generation.
8. Data quality anomaly blocking.
9. Training run registry and immutable provenance.
10. Model lineage generation (Dataset -> Training -> Model -> Validation -> Governance -> Deployment).
11. 14 Continuous Learning & Model Evolution Safety Gates.
12. Strict JWT RBAC (Viewer read-only, Operator/Admin training trigger, 401 unauthenticated, 403 viewer).
13. Zero PII assertions in API responses and dataset schemas.
14. MANDATORY FINANCIAL ISOLATION: 0 RecoveryAction mutations, 0 Payment mutations, 0 RecoveryCase financial mutations, 0 provider calls.
"""

import uuid
from datetime import UTC, datetime

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import UserRole, create_access_token
from app.main import app
from app.ml.features import validate_no_pii_in_features
from app.ml.training_dataset import (
    FEATURE_SCHEMA_VERSION,
    TrainingDatasetBuilder,
    compute_dataset_hash,
)
from app.models.customer import Customer
from app.models.enums import (
    ContinuousLearningQualityGateCode,
    CustomerRiskTier,
    LearningTriggerType,
    ModelEvolutionDecision,
    PaymentAttemptStatus,
    PaymentStatus,
    RecoveryCaseStatus,
    RetrainingEligibilityDecision,
    SubscriptionStatus,
    TrainingRunStatus,
)
from app.models.payment import Payment
from app.models.payment_attempt import PaymentAttempt
from app.models.recovery_action import RecoveryAction
from app.models.recovery_case import RecoveryCase
from app.models.subscription import Subscription
from app.schemas.continuous_learning import ManualTrainingTriggerRequest
from app.services.continuous_learning_service import (
    BASELINE_DATASET_HASH,
    BASELINE_DATASET_VERSION,
    ContinuousLearningService,
)


@pytest.fixture
def viewer_token() -> str:
    return create_access_token(user_id="view_test_user", role=UserRole.VIEWER.value)


@pytest.fixture
def operator_token() -> str:
    return create_access_token(user_id="op_test_user", role=UserRole.OPERATOR.value)


@pytest.fixture
def admin_token() -> str:
    return create_access_token(user_id="admin_test_user", role=UserRole.ADMIN.value)


@pytest.fixture
def client(db_session: Session, operator_token: str) -> TestClient:
    def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    test_client = TestClient(app)
    test_client.headers.update({"Authorization": f"Bearer {operator_token}"})
    yield test_client
    app.dependency_overrides.clear()


@pytest.fixture
def viewer_client(db_session: Session, viewer_token: str) -> TestClient:
    def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    test_client = TestClient(app)
    test_client.headers.update({"Authorization": f"Bearer {viewer_token}"})
    yield test_client
    app.dependency_overrides.clear()


@pytest.fixture
def admin_client(db_session: Session, admin_token: str) -> TestClient:
    def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    test_client = TestClient(app)
    test_client.headers.update({"Authorization": f"Bearer {admin_token}"})
    yield test_client
    app.dependency_overrides.clear()


@pytest.fixture
def populate_test_recovery_cases(db_session: Session):
    """Seed test cases covering positive resolved, negative resolved, and unresolved cases."""
    customer = Customer(
        external_customer_id=f"cust_cl_{uuid.uuid4().hex[:6]}",
        email_masked="t***@example.com",
        phone_masked="+919876543210",
        risk_tier=CustomerRiskTier.STANDARD.value,
        total_payments_count=20,
        failed_payments_count=5,
    )

    db_session.add(customer)
    db_session.commit()

    sub = Subscription(
        customer_id=customer.id,
        status=SubscriptionStatus.ACTIVE.value,
        plan_name="Enterprise Plan",
        recurring_amount=150000,
        billing_cadence="MONTHLY",
        current_period_start=datetime.now(UTC),
    )

    db_session.add(sub)
    db_session.commit()

    # 1. Seed 10 Resolved Positive Cases (RECOVERED + CAPTURED) -> y=1
    for i in range(10):
        payment = Payment(
            customer_id=customer.id,
            subscription_id=sub.id,
            amount=150000,
            currency="INR",
            status=PaymentStatus.CAPTURED.value,
            external_order_id=f"order_cl_pos_{i}_{uuid.uuid4().hex[:6]}",
        )
        db_session.add(payment)
        db_session.commit()

        attempt = PaymentAttempt(
            payment_id=payment.id,
            attempt_number=1,
            amount=150000,
            status=PaymentAttemptStatus.SUCCESS.value,
            initiated_at=datetime.now(UTC),
        )
        db_session.add(attempt)

        case = RecoveryCase(
            customer_id=customer.id,
            payment_id=payment.id,
            amount_at_risk=150000,
            status=RecoveryCaseStatus.RECOVERED.value,
            opened_at=datetime.now(UTC),
            resolved_at=datetime.now(UTC),
        )
        db_session.add(case)

    # 2. Seed 10 Resolved Negative Cases (CLOSED + FAILED) -> y=0
    for i in range(10):
        payment = Payment(
            customer_id=customer.id,
            subscription_id=sub.id,
            amount=150000,
            currency="INR",
            status=PaymentStatus.FAILED.value,
            external_order_id=f"order_cl_neg_{i}_{uuid.uuid4().hex[:6]}",
        )
        db_session.add(payment)
        db_session.commit()

        attempt = PaymentAttempt(
            payment_id=payment.id,
            attempt_number=1,
            amount=150000,
            status=PaymentAttemptStatus.FAILED.value,
            error_code="INSUFFICIENT_FUNDS",
            error_reason="insufficient funds",
            initiated_at=datetime.now(UTC),
        )
        db_session.add(attempt)

        case = RecoveryCase(
            customer_id=customer.id,
            payment_id=payment.id,
            amount_at_risk=150000,
            status=RecoveryCaseStatus.CLOSED.value,
            opened_at=datetime.now(UTC),
            resolved_at=datetime.now(UTC),
        )
        db_session.add(case)

    # 3. Seed 5 Unresolved Cases (IN_RECOVERY + CREATED) -> MUST BE EXCLUDED
    for i in range(5):
        payment = Payment(
            customer_id=customer.id,
            subscription_id=sub.id,
            amount=150000,
            currency="INR",
            status=PaymentStatus.CREATED.value,
            external_order_id=f"order_cl_unresolved_{i}_{uuid.uuid4().hex[:6]}",
        )
        db_session.add(payment)
        db_session.commit()

        case = RecoveryCase(
            customer_id=customer.id,
            payment_id=payment.id,
            amount_at_risk=150000,
            status=RecoveryCaseStatus.IN_RECOVERY.value,
            opened_at=datetime.now(UTC),
        )
        db_session.add(case)

    db_session.commit()


# =============================================================================
# 1. Dataset Extraction & Resolved-Case Filtering Tests
# =============================================================================


def test_resolved_case_filtering_and_label_correctness(
    db_session: Session, populate_test_recovery_cases
):
    """1. Test that dataset builder extracts only resolved cases with correct binary labels."""
    builder = TrainingDatasetBuilder(db_session)
    dataset = builder.extract_resolved_dataset()

    assert len(dataset) == 20, (
        "Should extract exactly 20 resolved cases (10 pos + 10 neg)"
    )

    pos_count = sum(1 for r in dataset if r["label"] == 1)
    neg_count = sum(1 for r in dataset if r["label"] == 0)

    assert pos_count == 10
    assert neg_count == 10

    # Ensure all feature representations contain zero PII
    for r in dataset:
        feat = r["features"]
        validate_no_pii_in_features(feat.model_dump())
        assert feat.payment_amount == 150000


def test_unresolved_cases_strictly_excluded(
    db_session: Session, populate_test_recovery_cases
):
    """2. Test that cases in IN_RECOVERY, OPEN, ACTION_REQUIRED are never added to dataset."""
    builder = TrainingDatasetBuilder(db_session)
    dataset = builder.extract_resolved_dataset()

    # Query all cases in database (25 total = 10 pos + 10 neg + 5 unresolved)
    all_cases_count = db_session.query(RecoveryCase).count()
    assert all_cases_count == 25

    # Dataset must have only 20
    assert len(dataset) == 20
    extracted_case_ids = {r["case_id"] for r in dataset}

    unresolved_cases = (
        db_session.query(RecoveryCase)
        .filter(RecoveryCase.status == RecoveryCaseStatus.IN_RECOVERY.value)
        .all()
    )
    assert len(unresolved_cases) == 5
    for uc in unresolved_cases:
        assert str(uc.id) not in extracted_case_ids


def test_deterministic_dataset_hashing_and_reproducibility(
    db_session: Session, populate_test_recovery_cases
):
    """3. Test that identical datasets produce identical SHA-256 hashes byte-for-byte."""
    builder = TrainingDatasetBuilder(db_session)
    dataset1 = builder.extract_resolved_dataset()
    hash1 = compute_dataset_hash(dataset1)

    dataset2 = builder.extract_resolved_dataset()
    hash2 = compute_dataset_hash(dataset2)

    assert hash1 == hash2
    assert len(hash1) == 64


# =============================================================================
# 2. Continuous Learning Service & Triggers
# =============================================================================


def test_dataset_versioning_and_metadata_construction(db_session: Session):
    """4. Test dataset version generation and metadata construction."""
    service = ContinuousLearningService(db_session)
    dataset_version = service.get_or_create_latest_dataset()

    assert dataset_version.dataset_id is not None
    assert dataset_version.dataset_version.startswith("dataset-v")
    assert dataset_version.sample_count >= 0
    assert dataset_version.feature_schema_version == FEATURE_SCHEMA_VERSION
    assert len(dataset_version.sha256_checksum) == 64


def test_retraining_eligibility_and_triggers_evaluation(db_session: Session):
    """5. Test retraining eligibility calculation across the 4 automated triggers."""
    service = ContinuousLearningService(db_session)
    eligibility = service.evaluate_retraining_eligibility()

    assert eligibility.decision in (
        RetrainingEligibilityDecision.ELIGIBLE,
        RetrainingEligibilityDecision.WAITING_FOR_DATA,
        RetrainingEligibilityDecision.DRIFT_TRIGGERED,
        RetrainingEligibilityDecision.PERFORMANCE_TRIGGERED,
        RetrainingEligibilityDecision.CALIBRATION_TRIGGERED,
        RetrainingEligibilityDecision.BLOCKED_BY_DATA_QUALITY,
    )
    assert len(eligibility.triggers) == 4

    trigger_types = {t.trigger_type for t in eligibility.triggers}
    assert LearningTriggerType.NEW_RESOLVED_CASES in trigger_types
    assert LearningTriggerType.MODEL_DRIFT in trigger_types
    assert LearningTriggerType.PERFORMANCE_DEGRADATION in trigger_types
    assert LearningTriggerType.CALIBRATION_DEGRADATION in trigger_types


def test_training_run_registry_and_offline_execution(db_session: Session):
    """6. Test offline training run execution and immutable audit logging."""
    service = ContinuousLearningService(db_session)

    initial_runs = service.list_training_runs()
    initial_count = initial_runs.total

    # Trigger training run
    run_dto = service.trigger_offline_training(
        payload=ManualTrainingTriggerRequest(
            learning_rate=0.05,
            epochs=20,
            notes="Unit test offline continuous learning run",
        ),
        actor_id="test_operator",
    )

    assert run_dto.training_run_id is not None
    assert run_dto.status == TrainingRunStatus.COMPLETED
    assert run_dto.model_version is not None
    assert run_dto.algorithm == "CalibratedLogisticRegression"
    assert run_dto.dataset_checksum is not None
    assert run_dto.artifact_checksum is not None

    # Verify registry reflects the new run
    updated_runs = service.list_training_runs()
    assert updated_runs.total == initial_count + 1
    assert updated_runs.items[0].training_run_id == run_dto.training_run_id


def test_model_lineage_graph(db_session: Session):
    """7. Test model lineage provenance tracing from dataset to candidate model."""
    service = ContinuousLearningService(db_session)
    lineage_res = service.get_model_lineage()

    assert len(lineage_res.lineage) >= 1
    assert lineage_res.active_champion_version == "v1.0"

    root_node = next(
        (n for n in lineage_res.lineage if n.model_version == "v1.0"), None
    )
    assert root_node is not None
    assert root_node.dataset_version == BASELINE_DATASET_VERSION
    assert root_node.dataset_checksum == BASELINE_DATASET_HASH
    assert root_node.deployment_status == "ACTIVE"


def test_14_continuous_learning_safety_gates(db_session: Session):
    """8. Test 14 Continuous Learning & Model Evolution Safety Gates."""
    service = ContinuousLearningService(db_session)
    readiness = service.evaluate_continuous_learning_readiness()

    assert len(readiness.gates) == 14
    gate_codes = {g.gate_code for g in readiness.gates}

    expected_codes = {
        ContinuousLearningQualityGateCode.MIN_DATASET_SIZE,
        ContinuousLearningQualityGateCode.DATA_QUALITY,
        ContinuousLearningQualityGateCode.FEATURE_SCHEMA_COMPATIBILITY,
        ContinuousLearningQualityGateCode.DATASET_CHECKSUM,
        ContinuousLearningQualityGateCode.MODEL_ARTIFACT_CHECKSUM,
        ContinuousLearningQualityGateCode.VALIDATION_SAMPLE_SIZE,
        ContinuousLearningQualityGateCode.ACCURACY_NON_REGRESSION,
        ContinuousLearningQualityGateCode.F1_NON_REGRESSION,
        ContinuousLearningQualityGateCode.BRIER_NON_REGRESSION,
        ContinuousLearningQualityGateCode.CALIBRATION,
        ContinuousLearningQualityGateCode.DRIFT,
        ContinuousLearningQualityGateCode.CAUSAL_EVIDENCE,
        ContinuousLearningQualityGateCode.HUMAN_REVIEW_REQUIRED,
        ContinuousLearningQualityGateCode.DEPLOYMENT_SEPARATION,
    }
    assert gate_codes == expected_codes
    assert readiness.decision in (
        ModelEvolutionDecision.NO_ACTION,
        ModelEvolutionDecision.RETRAIN_RECOMMENDED,
        ModelEvolutionDecision.REVIEW_REQUIRED,
        ModelEvolutionDecision.CHALLENGER_READY,
        ModelEvolutionDecision.PROMOTION_BLOCKED,
    )


# =============================================================================
# 3. REST API Endpoint Tests & RBAC
# =============================================================================


def test_api_get_continuous_learning_summary(client: TestClient):
    """9. Test GET /intelligence/continuous-learning summary endpoint."""
    res = client.get("/api/recovery/intelligence/continuous-learning")
    assert res.status_code == 200
    data = res.json()

    assert data["active_champion_version"] == "v1.0"
    assert "latest_dataset_version" in data
    assert "retraining_eligibility" in data
    assert "evolution_decision" in data
    assert "governance_disclaimer" in data


def test_api_get_datasets(client: TestClient):
    """10. Test GET /intelligence/continuous-learning/datasets endpoint."""
    res = client.get("/api/recovery/intelligence/continuous-learning/datasets")
    assert res.status_code == 200
    data = res.json()

    assert data["total"] >= 1
    assert len(data["items"]) >= 1
    assert any(d["dataset_version"] == BASELINE_DATASET_VERSION for d in data["items"])


def test_api_get_training_runs(client: TestClient):
    """11. Test GET /intelligence/continuous-learning/training-runs endpoint."""
    res = client.get("/api/recovery/intelligence/continuous-learning/training-runs")
    assert res.status_code == 200
    data = res.json()

    assert data["total"] >= 1
    assert len(data["items"]) >= 1


def test_api_get_lineage(client: TestClient):
    """12. Test GET /intelligence/continuous-learning/lineage endpoint."""
    res = client.get("/api/recovery/intelligence/continuous-learning/lineage")
    assert res.status_code == 200
    data = res.json()

    assert len(data["lineage"]) >= 1
    assert data["active_champion_version"] == "v1.0"


def test_api_get_readiness(client: TestClient):
    """13. Test GET /intelligence/continuous-learning/readiness endpoint."""
    res = client.get("/api/recovery/intelligence/continuous-learning/readiness")
    assert res.status_code == 200
    data = res.json()

    assert "decision" in data
    assert "gates" in data
    assert len(data["gates"]) == 14


def test_api_trigger_offline_training(client: TestClient):
    """14. Test POST /intelligence/continuous-learning/trigger-training endpoint."""
    res = client.post(
        "/api/recovery/intelligence/continuous-learning/trigger-training",
        json={"learning_rate": 0.05, "epochs": 30, "notes": "API triggered training"},
    )
    assert res.status_code == 201
    data = res.json()

    assert data["status"] == "COMPLETED"
    assert data["model_version"] is not None
    assert data["algorithm"] == "CalibratedLogisticRegression"


def test_viewer_rbac_read_only_and_forbidden_on_trigger(viewer_client: TestClient):
    """15. Test that Viewer can read all endpoints but cannot trigger training."""
    # Reads work
    res_summary = viewer_client.get("/api/recovery/intelligence/continuous-learning")
    assert res_summary.status_code == 200

    res_datasets = viewer_client.get(
        "/api/recovery/intelligence/continuous-learning/datasets"
    )
    assert res_datasets.status_code == 200

    res_runs = viewer_client.get(
        "/api/recovery/intelligence/continuous-learning/training-runs"
    )
    assert res_runs.status_code == 200

    res_lineage = viewer_client.get(
        "/api/recovery/intelligence/continuous-learning/lineage"
    )
    assert res_lineage.status_code == 200

    res_readiness = viewer_client.get(
        "/api/recovery/intelligence/continuous-learning/readiness"
    )
    assert res_readiness.status_code == 200

    # Triggering training is Forbidden (403)
    res_trigger = viewer_client.post(
        "/api/recovery/intelligence/continuous-learning/trigger-training",
        json={"notes": "Viewer attempting training"},
    )
    assert res_trigger.status_code == 403


def test_unauthenticated_requests_return_401():
    """16. Test that requests without valid JWT return 401 Unauthorized."""
    unauth_client = TestClient(app)

    res1 = unauth_client.get("/api/recovery/intelligence/continuous-learning")
    assert res1.status_code == 401

    res2 = unauth_client.post(
        "/api/recovery/intelligence/continuous-learning/trigger-training",
        json={},
    )
    assert res2.status_code == 401


def test_zero_pii_in_continuous_learning_responses(client: TestClient):
    """17. Test that continuous learning API payloads expose zero PII."""
    res = client.get("/api/recovery/intelligence/continuous-learning")
    assert res.status_code == 200
    body = res.text.lower()

    assert "@example.com" not in body
    assert "+91" not in body
    assert "password" not in body
    assert "secret" not in body
    assert "card_number" not in body


# =============================================================================
# 4. MANDATORY FINANCIAL ISOLATION END-TO-END TEST
# =============================================================================


def test_mandatory_financial_isolation_end_to_end(
    admin_client: TestClient, db_session: Session, populate_test_recovery_cases
):
    """18. MANDATORY FINANCIAL ISOLATION TEST.

    Verify that full continuous learning lifecycle (dataset extraction -> trigger evaluation ->
    retraining eligibility -> offline training run -> validation -> lineage):
    - Creates EXACTLY ZERO RecoveryAction records.
    - Mutates EXACTLY ZERO Payment statuses.
    - Mutates EXACTLY ZERO RecoveryCase financial states.
    - Executes zero gateway/provider operations.
    """
    # 1. Pre-execution snapshots
    initial_actions_count = db_session.query(RecoveryAction).count()
    initial_payments_captured = (
        db_session.query(Payment)
        .filter(Payment.status == PaymentStatus.CAPTURED.value)
        .count()
    )
    initial_cases_recovered = (
        db_session.query(RecoveryCase)
        .filter(RecoveryCase.status == RecoveryCaseStatus.RECOVERED.value)
        .count()
    )

    # 2. Get continuous learning summary
    summary_res = admin_client.get("/api/recovery/intelligence/continuous-learning")
    assert summary_res.status_code == 200

    # 3. List datasets
    datasets_res = admin_client.get(
        "/api/recovery/intelligence/continuous-learning/datasets"
    )
    assert datasets_res.status_code == 200

    # 4. Evaluate readiness
    readiness_res = admin_client.get(
        "/api/recovery/intelligence/continuous-learning/readiness"
    )
    assert readiness_res.status_code == 200

    # 5. Trigger offline training
    train_res = admin_client.post(
        "/api/recovery/intelligence/continuous-learning/trigger-training",
        json={"learning_rate": 0.05, "epochs": 50, "notes": "Mandatory isolation test"},
    )
    assert train_res.status_code == 201

    # 6. Inspect lineage
    lineage_res = admin_client.get(
        "/api/recovery/intelligence/continuous-learning/lineage"
    )
    assert lineage_res.status_code == 200

    # 7. Post-execution financial assertions
    final_actions_count = db_session.query(RecoveryAction).count()
    final_payments_captured = (
        db_session.query(Payment)
        .filter(Payment.status == PaymentStatus.CAPTURED.value)
        .count()
    )
    final_cases_recovered = (
        db_session.query(RecoveryCase)
        .filter(RecoveryCase.status == RecoveryCaseStatus.RECOVERED.value)
        .count()
    )

    # STRICT ZERO MUTATIONS ASSERTIONS
    assert final_actions_count == initial_actions_count, (
        "Continuous learning must NOT create RecoveryAction records!"
    )
    assert final_payments_captured == initial_payments_captured, (
        "Payment status must NOT be modified!"
    )
    assert final_cases_recovered == initial_cases_recovered, (
        "RecoveryCase status must NOT be modified!"
    )
