import uuid
from decimal import Decimal
from unittest.mock import patch

import pytest
from sqlalchemy.orm import Session

from app.ml.features import extract_features, validate_no_pii_in_features
from app.ml.model import LogisticRegressionModel
from app.ml.predictor import RecoveryPredictor, recovery_predictor
from app.ml.schemas import (
    RecoveryFeatures,
    RecoveryPriority,
)
from app.ml.training import (
    calculate_pr_auc,
    calculate_roc_auc,
    evaluate_model,
    generate_synthetic_development_dataset,
    train_development_model,
)
from app.models import (
    Customer,
    MLPrediction,
    Payment,
    PaymentAttempt,
    PaymentAttemptStatus,
    PaymentStatus,
    RecoveryCase,
    RecoveryCaseStatus,
)
from app.services.ml_prediction_service import ml_prediction_service


def create_test_fixtures(
    db_session: Session,
) -> tuple[Customer, Payment, RecoveryCase]:
    """Helper to provision test database entities."""
    customer = Customer(
        external_customer_id=f"cust_ml_test_{uuid.uuid4().hex[:8]}",
        email_masked="m***l@example.com",
        phone_masked="+91******1234",
        total_payments_count=5,
        failed_payments_count=1,
        recovered_payments_count=4,
    )
    db_session.add(customer)
    db_session.flush()

    payment = Payment(
        customer_id=customer.id,
        razorpay_order_id=f"order_ml_{uuid.uuid4().hex[:8]}",
        amount=199900,
        currency="INR",
        status=PaymentStatus.FAILED.value,
    )
    db_session.add(payment)
    db_session.flush()

    attempt = PaymentAttempt(
        payment_id=payment.id,
        attempt_number=1,
        amount=199900,
        status=PaymentAttemptStatus.FAILED.value,
        error_code="BAD_REQUEST_ERROR",
        error_source="bank",
        error_step="payment_authorization",
        error_reason="insufficient_funds",
    )
    db_session.add(attempt)
    db_session.flush()

    case = RecoveryCase(
        payment_id=payment.id,
        customer_id=customer.id,
        status=RecoveryCaseStatus.OPEN.value,
        amount_at_risk=199900,
        recovered_amount=0,
        total_attempts_count=1,
        latest_failure_reason="insufficient_funds",
    )
    db_session.add(case)
    db_session.commit()
    db_session.refresh(case)

    return customer, payment, case


# =========================================================================
# Feature Extraction & PII Validation Tests
# =========================================================================


def test_feature_extraction_with_valid_entities(db_session: Session):
    """1. Test feature extraction accurately builds feature vector."""
    customer, payment, case = create_test_fixtures(db_session)
    attempts = (
        db_session.query(PaymentAttempt)
        .filter_by(payment_id=payment.id)
        .all()
    )

    features = extract_features(case, payment, customer, attempts)

    assert features.payment_amount == 199900
    assert features.currency == "INR"
    assert features.attempt_number == 1
    assert features.customer_total_payments == 5
    assert features.customer_failed_payments == 1
    assert features.customer_success_rate == 0.80
    assert features.error_reason == "insufficient_funds"
    assert features.hours_since_failure >= 0.0


def test_no_pii_enters_model_features():
    """2. Test that validate_no_pii_in_features blocks sensitive fields."""
    safe_dict = {
        "payment_amount": 10000,
        "error_reason": "insufficient_funds",
    }
    validate_no_pii_in_features(safe_dict)  # Must pass

    with pytest.raises(
        ValueError, match="PII violation: Forbidden keyword 'email'"
    ):
        validate_no_pii_in_features({"email": "user@example.com"})

    with pytest.raises(
        ValueError, match="PII violation: Forbidden keyword 'card_number'"
    ):
        validate_no_pii_in_features({"card_number": "4111111111111111"})

    with pytest.raises(
        ValueError, match="PII violation: Forbidden keyword 'cvv'"
    ):
        validate_no_pii_in_features({"cvv": "123"})


def test_new_customer_defaults_neutral_prior(db_session: Session):
    """3. Test that a brand new customer defaults to 0.50 success rate."""
    customer = Customer(
        external_customer_id="cust_new_001",
        total_payments_count=0,
        failed_payments_count=0,
    )
    db_session.add(customer)
    db_session.flush()

    payment = Payment(
        customer_id=customer.id,
        amount=50000,
        currency="INR",
        status=PaymentStatus.FAILED.value,
    )
    db_session.add(payment)
    db_session.flush()

    case = RecoveryCase(
        payment_id=payment.id,
        customer_id=customer.id,
        amount_at_risk=50000,
        total_attempts_count=1,
    )
    db_session.add(case)
    db_session.commit()

    features = extract_features(case, payment, customer, [])
    assert features.customer_total_payments == 0
    assert features.customer_success_rate == 0.50


# =========================================================================
# Model Scoring & Deterministic Predictor Tests
# =========================================================================


def test_high_failure_customer_produces_lower_recovery_probability():
    """4. Test high failure rate significantly lowers recovery probability."""
    good_features = RecoveryFeatures(
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
        hours_since_failure=1.0,
        subscription_age_days=60,
        total_attempts_count=1,
    )

    bad_features = RecoveryFeatures(
        payment_amount=100000,
        currency="INR",
        attempt_number=3,
        customer_total_payments=10,
        customer_successful_payments=1,
        customer_failed_payments=9,
        customer_success_rate=0.10,
        error_code="BAD_REQUEST_ERROR",
        error_source="bank",
        error_step="payment_authorization",
        error_reason="card_inactive",
        hours_since_failure=48.0,
        subscription_age_days=0,
        total_attempts_count=3,
    )

    good_pred = recovery_predictor.predict(good_features)
    bad_pred = recovery_predictor.predict(bad_features)

    assert good_pred.recovery_probability > bad_pred.recovery_probability
    assert good_pred.priority == RecoveryPriority.HIGH_RECOVERY_POTENTIAL
    assert bad_pred.priority == RecoveryPriority.LOW_RECOVERY_POTENTIAL


def test_probability_and_risk_score_bounds_and_relationship():
    """5. Test probability is in [0, 1] and risk_score is exactly 1 - prob."""
    features = RecoveryFeatures(
        payment_amount=250000,
        currency="INR",
        attempt_number=1,
        customer_total_payments=3,
        customer_successful_payments=2,
        customer_failed_payments=1,
        customer_success_rate=0.67,
        error_code="GATEWAY_ERROR",
        error_source="bank",
        error_step="payment_authorization",
        error_reason="network_timeout",
        hours_since_failure=0.5,
        subscription_age_days=30,
        total_attempts_count=1,
    )

    result = recovery_predictor.predict(features)

    assert 0.0 <= result.recovery_probability <= 1.0
    assert 0.0 <= result.risk_score <= 1.0
    assert 0.0 <= result.confidence <= 1.0
    assert round(result.recovery_probability + result.risk_score, 4) == 1.0
    assert result.model_name == "recovery_probability"
    assert result.model_version == "v1.0"


def test_deterministic_priority_classification_boundaries():
    """6. Test exact boundary thresholds for priority classification."""
    predictor = RecoveryPredictor()

    assert (
        predictor.classify_priority(0.75)
        == RecoveryPriority.HIGH_RECOVERY_POTENTIAL
    )
    assert (
        predictor.classify_priority(0.95)
        == RecoveryPriority.HIGH_RECOVERY_POTENTIAL
    )
    assert (
        predictor.classify_priority(0.7499)
        == RecoveryPriority.MEDIUM_RECOVERY_POTENTIAL
    )
    assert (
        predictor.classify_priority(0.40)
        == RecoveryPriority.MEDIUM_RECOVERY_POTENTIAL
    )
    assert (
        predictor.classify_priority(0.3999)
        == RecoveryPriority.LOW_RECOVERY_POTENTIAL
    )
    assert (
        predictor.classify_priority(0.05)
        == RecoveryPriority.LOW_RECOVERY_POTENTIAL
    )


def test_prediction_reproducibility_is_strictly_deterministic():
    """7. Test that identical feature inputs produce bitwise identical outputs."""
    features = RecoveryFeatures(
        payment_amount=50000,
        currency="INR",
        attempt_number=1,
        customer_total_payments=2,
        customer_successful_payments=2,
        customer_failed_payments=0,
        customer_success_rate=1.0,
        error_code="BAD_REQUEST_ERROR",
        error_source="bank",
        error_step="payment_authorization",
        error_reason="insufficient_funds",
        hours_since_failure=2.0,
        subscription_age_days=10,
        total_attempts_count=1,
    )

    res1 = recovery_predictor.predict(features)
    res2 = recovery_predictor.predict(features)

    assert res1.recovery_probability == res2.recovery_probability
    assert res1.risk_score == res2.risk_score
    assert res1.priority == res2.priority
    assert res1.predicted_channel == res2.predicted_channel


# =========================================================================
# Service Persistence & Append-Only Behavior Tests
# =========================================================================


def test_ml_prediction_service_persistence(db_session: Session):
    """8. Test predict_recovery service persists record in ml_predictions."""
    _, _, case = create_test_fixtures(db_session)

    prediction = ml_prediction_service.predict_recovery(db_session, case.id)

    assert prediction is not None
    assert prediction.recovery_case_id == case.id
    assert prediction.model_name == "recovery_probability"
    assert prediction.model_version == "v1.0"
    assert isinstance(prediction.recovery_probability, Decimal)
    assert 0.0 <= float(prediction.recovery_probability) <= 1.0
    assert "features" in prediction.feature_vector_snapshot
    assert "priority" in prediction.feature_vector_snapshot


def test_append_only_multiple_predictions_for_same_case(db_session: Session):
    """9. Test multiple inferences create multiple rows without overwriting."""
    _, _, case = create_test_fixtures(db_session)

    pred1 = ml_prediction_service.predict_recovery(db_session, case.id)
    pred2 = ml_prediction_service.predict_recovery(db_session, case.id)

    assert pred1.id != pred2.id

    # Verify count in database
    predictions_count = (
        db_session.query(MLPrediction)
        .filter_by(recovery_case_id=case.id)
        .count()
    )
    assert predictions_count == 2


def test_prediction_on_non_existent_case_raises_error(db_session: Session):
    """10. Test predict_recovery raises ValueError for non-existent case."""
    fake_case_id = uuid.uuid4()
    with pytest.raises(ValueError, match="not found"):
        ml_prediction_service.predict_recovery(db_session, fake_case_id)


def test_database_failure_rolls_back_atomically(db_session: Session):
    """11. Test database exception during persistence rolls back cleanly."""
    _, _, case = create_test_fixtures(db_session)

    with patch.object(
        db_session, "commit", side_effect=RuntimeError("DB Commit Crash")
    ):
        with pytest.raises(RuntimeError, match="DB Commit Crash"):
            ml_prediction_service.predict_recovery(db_session, case.id)


# =========================================================================
# Model Training & Evaluation Metric Utilities Tests
# =========================================================================


def test_model_evaluation_metrics_calculation():
    """12. Test evaluation metrics compute Accuracy, Precision, Recall, ROC-AUC."""
    y_true = [1, 0, 1, 1, 0, 0, 1, 0]
    y_scores = [0.90, 0.10, 0.80, 0.70, 0.20, 0.30, 0.85, 0.15]

    metrics = evaluate_model(y_true, y_scores, threshold=0.5)

    assert metrics.accuracy == 1.0
    assert metrics.precision == 1.0
    assert metrics.recall == 1.0
    assert metrics.f1_score == 1.0
    assert metrics.roc_auc == 1.0
    assert metrics.brier_score < 0.10
    assert metrics.confusion_matrix == {"tp": 4, "fp": 0, "tn": 4, "fn": 0}


def test_synthetic_development_dataset_generation_and_training():
    """13. Test generating synthetic dataset and training baseline model."""
    dataset = generate_synthetic_development_dataset(n_samples=100, seed=123)
    assert len(dataset) == 100

    model, metrics = train_development_model(dataset, epochs=10)
    assert isinstance(model, LogisticRegressionModel)
    assert 0.0 <= metrics.accuracy <= 1.0
    assert 0.0 <= metrics.roc_auc <= 1.0


def test_auc_calculation_helpers():
    """14. Test ROC-AUC and PR-AUC helper functions on boundary inputs."""
    assert calculate_roc_auc([], []) == 0.5
    assert calculate_roc_auc([1, 1], [0.8, 0.9]) == 0.5
    assert calculate_roc_auc([1, 0], [0.9, 0.1]) == 1.0
    assert calculate_roc_auc([1, 0], [0.1, 0.9]) == 0.0

    assert calculate_pr_auc([], []) == 0.0
    assert calculate_pr_auc([0, 0], [0.1, 0.2]) == 0.0
    assert calculate_pr_auc([1, 0], [0.9, 0.1]) > 0.0
