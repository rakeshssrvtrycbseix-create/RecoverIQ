import logging

from app.ml.model import LogisticRegressionModel
from app.ml.schemas import PredictionResult, RecoveryFeatures, RecoveryPriority

logger = logging.getLogger(__name__)


class RecoveryPredictor:
    """
    Inference coordinator combining model scoring, deterministic risk/priority
    classification, and operational channel recommendations.
    """

    def __init__(self, model: LogisticRegressionModel | None = None) -> None:
        self.model = model or LogisticRegressionModel()

    def classify_priority(self, probability: float) -> RecoveryPriority:
        """
        Deterministic priority classification rule:
        - probability >= 0.75 -> HIGH_RECOVERY_POTENTIAL
        - probability >= 0.40 and < 0.75 -> MEDIUM_RECOVERY_POTENTIAL
        - probability < 0.40 -> LOW_RECOVERY_POTENTIAL
        """
        if probability >= 0.75:
            return RecoveryPriority.HIGH_RECOVERY_POTENTIAL
        elif probability >= 0.40:
            return RecoveryPriority.MEDIUM_RECOVERY_POTENTIAL
        else:
            return RecoveryPriority.LOW_RECOVERY_POTENTIAL

    def recommend_channel_and_delay(
        self,
        features: RecoveryFeatures,
        probability: float,
    ) -> tuple[str, int]:
        """
        Recommend operational recovery channel and optimal delay in hours.
        """
        reason = features.error_reason.lower().strip()

        # Temporary bank/gateway downtime: short smart retry delay
        if reason in {"bank_technical_error", "gateway_error", "issuer_down"}:
            return "SMART_RETRY", 4

        # Soft card/funds issue with high recovery potential
        if probability >= 0.75:
            return "SMART_RETRY", 2

        # Medium potential or user authentication issues: send payment link
        if probability >= 0.40 or reason in {
            "payment_authentication",
            "otp_timeout",
            "card_limit_exceeded",
        }:
            return "PAYMENT_LINK", 12

        # Low recovery potential / permanent failures: notification / customer action
        return "NOTIFICATION", 24

    def predict(self, features: RecoveryFeatures) -> PredictionResult:
        """
        Execute prediction pipeline for a validated feature vector.
        """
        # 1. Model inference
        prob = self.model.predict_proba(features)
        prob_clamped = max(0.0, min(1.0, prob))

        # 2. Risk & Confidence metrics
        risk_score = max(0.0, min(1.0, round(1.0 - prob_clamped, 4)))
        confidence = self.model.calculate_confidence(features)

        # 3. Deterministic Priority & Channel Recommendation
        priority = self.classify_priority(prob_clamped)
        channel, delay_hours = self.recommend_channel_and_delay(features, prob_clamped)

        logger.info(
            "ml_prediction_calculated",
            extra={
                "model_name": self.model.model_name,
                "model_version": self.model.model_version,
                "recovery_probability": prob_clamped,
                "risk_score": risk_score,
                "priority": priority.value,
                "channel": channel,
            },
        )

        return PredictionResult(
            recovery_probability=prob_clamped,
            risk_score=risk_score,
            confidence=confidence,
            priority=priority,
            predicted_channel=channel,
            predicted_delay_hours=delay_hours,
            model_name=self.model.model_name,
            model_version=self.model.model_version,
            features_used=features.model_dump(),
        )


recovery_predictor = RecoveryPredictor()
