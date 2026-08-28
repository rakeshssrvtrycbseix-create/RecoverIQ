from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class RecoveryPriority(StrEnum):
    """Deterministic recovery prioritization classification."""

    HIGH_RECOVERY_POTENTIAL = "HIGH_RECOVERY_POTENTIAL"
    MEDIUM_RECOVERY_POTENTIAL = "MEDIUM_RECOVERY_POTENTIAL"
    LOW_RECOVERY_POTENTIAL = "LOW_RECOVERY_POTENTIAL"


class RecoveryFeatures(BaseModel):
    """
    Structured feature vector for recovery probability estimation.

    Strict Leakage & PII Policy:
    - Contains ONLY pre-decision features known at prediction time.
    - Excludes all target variables (recovered_amount, resolution status).
    - Excludes all raw PII (emails, phone numbers, customer names, cards).
    """

    model_config = ConfigDict(frozen=True)

    # Transaction parameters
    payment_amount: int = Field(
        ge=0,
        description="Transaction amount in integer minor units (paise)",
    )
    currency: str = Field(
        default="INR",
        description="ISO 4217 3-letter currency code",
    )
    attempt_number: int = Field(
        ge=1,
        description="Current sequential payment attempt number",
    )

    # Customer behavioral telemetry
    customer_total_payments: int = Field(
        ge=0,
        description="Historical total payment count for this customer",
    )
    customer_successful_payments: int = Field(
        ge=0,
        description="Historical successful payment count for this customer",
    )
    customer_failed_payments: int = Field(
        ge=0,
        description="Historical failed payment count for this customer",
    )
    customer_success_rate: float = Field(
        ge=0.0,
        le=1.0,
        description="Ratio of historical successful to total payments",
    )

    # Gateway error taxonomy
    error_code: str = Field(
        default="UNKNOWN",
        description="Gateway error code category",
    )
    error_source: str = Field(
        default="UNKNOWN",
        description="Origin of error (bank, customer, gateway)",
    )
    error_step: str = Field(
        default="UNKNOWN",
        description="Transaction step where failure occurred",
    )
    error_reason: str = Field(
        default="UNKNOWN",
        description="Specific failure reason code",
    )

    # Temporal & cadence features
    hours_since_failure: float = Field(
        ge=0.0,
        description="Elapsed time in hours since initial case opening",
    )
    subscription_age_days: int = Field(
        ge=0,
        default=0,
        description="Days since subscription creation, or 0 if one-off order",
    )
    total_attempts_count: int = Field(
        ge=1,
        description="Total failure attempts recorded on active recovery case",
    )


class PredictionResult(BaseModel):
    """Complete prediction payload produced by the RecoveryPredictor."""

    model_config = ConfigDict(frozen=True)

    recovery_probability: float = Field(
        ge=0.0,
        le=1.0,
        description="Predicted probability of successful payment recovery",
    )
    risk_score: float = Field(
        ge=0.0,
        le=1.0,
        description="Complement of probability (1.0 - recovery_probability)",
    )
    confidence: float = Field(
        ge=0.0,
        le=1.0,
        description="Statistical confidence metric based on feature density",
    )
    priority: RecoveryPriority = Field(
        description="Deterministic priority category",
    )
    predicted_channel: str = Field(
        description="Recommended operational recovery channel",
    )
    predicted_delay_hours: int = Field(
        ge=0,
        description="Recommended delay before next recovery touchpoint",
    )
    model_name: str = Field(
        default="recovery_probability",
        description="Registered model architecture identifier",
    )
    model_version: str = Field(
        default="v1.0",
        description="Semantic version of model weights/rules",
    )
    features_used: dict[str, Any] = Field(
        description="Audit-safe snapshot of feature vector inputs",
    )


class EvaluationMetrics(BaseModel):
    """Evaluation metrics for validation and offline performance scoring."""

    model_config = ConfigDict(frozen=True)

    accuracy: float = Field(ge=0.0, le=1.0)
    precision: float = Field(ge=0.0, le=1.0)
    recall: float = Field(ge=0.0, le=1.0)
    f1_score: float = Field(ge=0.0, le=1.0)
    roc_auc: float = Field(ge=0.0, le=1.0)
    pr_auc: float = Field(ge=0.0, le=1.0)
    brier_score: float = Field(ge=0.0, le=1.0)
    confusion_matrix: dict[str, int]
    sample_size: int = Field(ge=1)
