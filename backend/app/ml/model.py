import math
from typing import Any

from app.ml.schemas import RecoveryFeatures

# Error categorization weights
ERROR_REASON_WEIGHTS: dict[str, float] = {
    # Soft / transient errors (High recovery likelihood with retry/link)
    "insufficient_funds": 0.85,
    "network_timeout": 1.10,
    "bank_technical_error": 1.05,
    "gateway_error": 0.95,
    "issuer_down": 0.90,
    "temporary_failure": 0.80,
    # User friction / auth errors (Medium recovery likelihood with communication)
    "payment_authentication": 0.35,
    "payment_authorization": 0.20,
    "otp_timeout": 0.40,
    "incorrect_pin": 0.25,
    "card_limit_exceeded": 0.30,
    # Hard / permanent errors (Low recovery likelihood)
    "card_inactive": -2.20,
    "card_blocked": -2.50,
    "expired_card": -2.10,
    "account_closed": -3.00,
    "fraud_suspected": -3.50,
    "invalid_card_details": -2.00,
    "unknown": 0.00,
}


class LogisticRegressionModel:
    """
    Deterministic calibrated Logistic Regression model for payment recovery prediction.

    Computes recovery probability p in [0, 1] using standard logit transform:
        z = beta_0 + sum(beta_i * x_i)
        p = 1.0 / (1.0 + exp(-z))
    """

    def __init__(
        self,
        model_name: str = "recovery_probability",
        model_version: str = "v1.0",
        intercept: float = 0.55,
    ) -> None:
        self.model_name = model_name
        self.model_version = model_version
        self.intercept = intercept

        # Feature coefficients
        self.coef_success_rate = 2.10
        self.coef_failed_payments = -0.30
        self.coef_attempt_number = -0.65
        self.coef_total_attempts = -0.40
        self.coef_log_amount = -0.10
        self.coef_hours_decay = -0.015
        self.coef_subscription_age = 0.35

    def _extract_numeric_vector(self, features: RecoveryFeatures) -> dict[str, float]:
        """Convert structured RecoveryFeatures into scaled numerical components."""
        # Log-scaled amount (in INR)
        amount_inr = max(1.0, features.payment_amount / 100.0)
        log_amount = math.log(amount_inr)

        # Error reason categorization
        reason_clean = features.error_reason.lower().strip()
        error_weight = ERROR_REASON_WEIGHTS.get(reason_clean, 0.0)

        # Subscription tenure factor (capped at 1.0 for >= 90 days)
        sub_tenure_factor = min(1.0, features.subscription_age_days / 90.0)

        return {
            "success_rate": features.customer_success_rate,
            "failed_payments": float(min(10, features.customer_failed_payments)),
            "attempt_number": float(min(5, features.attempt_number)),
            "total_attempts": float(min(5, features.total_attempts_count)),
            "log_amount": log_amount,
            "error_weight": error_weight,
            "hours_since_failure": float(min(168.0, features.hours_since_failure)),
            "subscription_tenure": sub_tenure_factor,
        }

    def compute_logit(self, features: RecoveryFeatures) -> float:
        """Compute the linear logit score z."""
        vec = self._extract_numeric_vector(features)

        z = (
            self.intercept
            + (self.coef_success_rate * (vec["success_rate"] - 0.50))
            + (self.coef_failed_payments * vec["failed_payments"])
            + (self.coef_attempt_number * (vec["attempt_number"] - 1.0))
            + (self.coef_total_attempts * (vec["total_attempts"] - 1.0))
            + (self.coef_log_amount * (vec["log_amount"] - 6.0))
            + vec["error_weight"]
            + (self.coef_hours_decay * vec["hours_since_failure"])
            + (self.coef_subscription_age * vec["subscription_tenure"])
        )
        return z

    def predict_proba(self, features: RecoveryFeatures) -> float:
        """
        Evaluate probability of successful payment recovery.

        Output is strictly clamped to [0.0001, 0.9999].
        """
        z = self.compute_logit(features)

        # Numerically stable sigmoid
        if z >= 35.0:
            prob = 0.9999
        elif z <= -35.0:
            prob = 0.0001
        else:
            prob = 1.0 / (1.0 + math.exp(-z))

        return max(0.0001, min(0.9999, round(prob, 4)))

    def calculate_confidence(self, features: RecoveryFeatures) -> float:
        """
        Estimate statistical prediction confidence in [0.0, 1.0].

        Higher history volume and known error reasons yield higher confidence.
        """
        # Base confidence
        conf = 0.50

        # Customer history bonus (up to +0.30)
        history_pts = min(0.30, features.customer_total_payments * 0.05)
        conf += history_pts

        # Known error reason bonus (+0.15) vs unknown (-0.10)
        reason_clean = features.error_reason.lower().strip()
        if reason_clean in ERROR_REASON_WEIGHTS and reason_clean != "unknown":
            conf += 0.15
        else:
            conf -= 0.10

        return max(0.10, min(0.99, round(conf, 4)))

    def get_metadata(self) -> dict[str, Any]:
        """Return model metadata."""
        return {
            "model_name": self.model_name,
            "model_version": self.model_version,
            "algorithm": "calibrated_logistic_regression",
        }
