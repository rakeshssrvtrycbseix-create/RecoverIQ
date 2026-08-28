import logging
import uuid
from decimal import Decimal

from sqlalchemy.orm import Session

from app.ml.features import extract_features
from app.ml.predictor import recovery_predictor
from app.models import (
    AuditActorType,
    AuditLog,
    Customer,
    MLPrediction,
    Payment,
    PaymentAttempt,
    RecoveryCase,
)

logger = logging.getLogger(__name__)


class MLPredictionService:
    """
    Service orchestrating feature extraction, model inference, and
    prediction persistence.
    """

    def predict_recovery(
        self,
        db: Session,
        recovery_case_id: uuid.UUID,
    ) -> MLPrediction:
        """
        Execute recovery probability inference for a RecoveryCase and persist an
        immutable record in the ml_predictions table.

        Guarantees:
        1. Pure deterministic prediction based on pre-decision telemetry.
        2. Strict feature leakage and PII avoidance.
        3. Append-only persistence in ml_predictions (never overwrites prior runs).
        4. Atomic transaction boundary for prediction recording.
        """
        logger.info(
            "ml_prediction_pipeline_started",
            extra={"recovery_case_id": str(recovery_case_id)},
        )

        # 1. Load RecoveryCase aggregate
        case = (
            db.query(RecoveryCase)
            .filter_by(id=recovery_case_id)
            .first()
        )
        if not case:
            raise ValueError(f"RecoveryCase '{recovery_case_id}' not found")

        # 2. Load associated Payment and Customer
        payment = db.query(Payment).filter_by(id=case.payment_id).first()
        if not payment:
            raise ValueError(
                f"Payment '{case.payment_id}' for RecoveryCase not found"
            )

        customer = db.query(Customer).filter_by(id=case.customer_id).first()
        if not customer:
            raise ValueError(
                f"Customer '{case.customer_id}' for RecoveryCase not found"
            )

        # 3. Load historical payment attempts
        attempts = (
            db.query(PaymentAttempt)
            .filter_by(payment_id=payment.id)
            .order_by(PaymentAttempt.attempt_number.asc())
            .all()
        )

        # 4. Extract and validate pre-decision features
        features = extract_features(
            recovery_case=case,
            payment=payment,
            customer=customer,
            attempts=attempts,
        )

        # 5. Execute ML prediction
        result = recovery_predictor.predict(features)

        # 6. Prepare immutable MLPrediction record
        snapshot = {
            "features": result.features_used,
            "risk_score": result.risk_score,
            "confidence": result.confidence,
            "priority": result.priority.value,
        }

        prob_decimal = Decimal(str(round(result.recovery_probability, 4)))

        prediction = MLPrediction(
            recovery_case_id=case.id,
            model_name=result.model_name,
            model_version=result.model_version,
            recovery_probability=prob_decimal,
            predicted_channel=result.predicted_channel,
            predicted_delay_hours=result.predicted_delay_hours,
            feature_vector_snapshot=snapshot,
        )

        # 7. Atomic transaction persistence
        try:
            db.add(prediction)
            db.flush()

            # Record audit trail
            audit = AuditLog(
                event_type="ML_PREDICTION_GENERATED",
                actor_type=AuditActorType.SYSTEM_EVENT.value,
                actor_id="ml_prediction_engine",
                recovery_case_id=case.id,
                entity_type="ml_predictions",
                entity_id=prediction.id,
                action="ML_RECOVERY_PROBABILITY_PREDICTED",
                previous_state=None,
                new_state={
                    "recovery_probability": float(prob_decimal),
                    "priority": result.priority.value,
                    "risk_score": result.risk_score,
                    "model_version": result.model_version,
                },
                metadata_json={"model_name": result.model_name},
            )
            db.add(audit)
            db.commit()
            db.refresh(prediction)

            logger.info(
                "ml_prediction_persisted",
                extra={
                    "prediction_id": str(prediction.id),
                    "case_id": str(case.id),
                    "recovery_probability": float(prob_decimal),
                    "priority": result.priority.value,
                },
            )
            return prediction

        except Exception as exc:
            db.rollback()
            logger.error(
                "ml_prediction_persistence_failed",
                extra={"case_id": str(case.id), "error": str(exc)},
            )
            raise


ml_prediction_service = MLPredictionService()
