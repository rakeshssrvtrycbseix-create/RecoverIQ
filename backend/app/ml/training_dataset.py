import hashlib
import json
import logging
from datetime import UTC, datetime
from typing import Any

from sqlalchemy.orm import Session, selectinload

from app.ml.features import extract_features, validate_no_pii_in_features
from app.ml.schemas import RecoveryFeatures
from app.models import (
    Customer,
    Payment,
    PaymentAttempt,
    PaymentStatus,
    RecoveryCase,
    RecoveryCaseStatus,
)
from app.schemas.model_lifecycle import TrainingDatasetMetadata, TrainingDatasetSplit

logger = logging.getLogger(__name__)

FEATURE_SCHEMA_VERSION = "v1"

FEATURE_NAMES = [
    "payment_amount",
    "customer_success_rate",
    "customer_failed_payments",
    "customer_total_payments",
    "attempt_number",
    "total_attempts_count",
    "error_reason",
    "hours_since_failure",
    "subscription_age_days",
]

RESOLVED_POSITIVE_STATUSES = {RecoveryCaseStatus.RECOVERED.value}
RESOLVED_NEGATIVE_STATUSES = {
    RecoveryCaseStatus.CLOSED.value,
    RecoveryCaseStatus.EXHAUSTED.value,
}


def _to_utc(dt: datetime | None) -> datetime | None:
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=UTC)
    return dt.astimezone(UTC)


def compute_dataset_hash(records: list[dict[str, Any]]) -> str:
    """
    Deterministically compute a SHA-256 hash of a list of feature-label instances.
    """
    canonical_items = []
    for r in records:
        feat: RecoveryFeatures = r["features"]
        feat_dict = {
            "payment_amount": feat.payment_amount,
            "customer_success_rate": round(feat.customer_success_rate, 4),
            "customer_failed_payments": feat.customer_failed_payments,
            "customer_total_payments": feat.customer_total_payments,
            "attempt_number": feat.attempt_number,
            "total_attempts_count": feat.total_attempts_count,
            "error_reason": feat.error_reason.lower().strip(),
            "hours_since_failure": round(feat.hours_since_failure, 2),
            "subscription_age_days": feat.subscription_age_days,
            "label": r["label"],
        }
        canonical_items.append(feat_dict)

    # Sort deterministically by feature representation
    serialized = json.dumps(canonical_items, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


class TrainingDatasetBuilder:
    """
    Offline governed training dataset builder.

    Extracts resolved historical cases with ground truth recovery labels:
    - Positive (1): RecoveryCase == RECOVERED and Payment == CAPTURED
    - Negative (0): RecoveryCase in [CLOSED, EXHAUSTED] and Payment == FAILED
    - Excludes all unresolved cases.

    Strict Leakage Guards:
    - Features represent only telemetry established at or before case initiation.
    - Zero future or post-recovery fields (no recovered_amount, resolved_at, final status).
    - Zero customer PII.
    """

    def __init__(self, db: Session) -> None:
        self.db = db

    def extract_resolved_dataset(
        self, as_of: datetime | None = None
    ) -> list[dict[str, Any]]:
        """
        Query resolved historical cases from DB and extract strict pre-resolution feature vectors.
        """
        query = (
            self.db.query(RecoveryCase)
            .options(
                selectinload(RecoveryCase.payment).selectinload(Payment.attempts),
                selectinload(RecoveryCase.payment).selectinload(Payment.subscription),
                selectinload(RecoveryCase.customer),
            )
            .order_by(RecoveryCase.created_at.asc())
        )

        all_cases = query.all()
        dataset: list[dict[str, Any]] = []

        eval_cutoff = _to_utc(as_of) if as_of else None

        for case in all_cases:
            # Check resolution status and payment status
            payment: Payment | None = case.payment
            customer: Customer | None = case.customer

            if not payment or not customer:
                continue

            case_status = case.status
            payment_status = payment.status

            # Strict outcome labeling
            is_positive = (
                case_status in RESOLVED_POSITIVE_STATUSES
                and payment_status == PaymentStatus.CAPTURED.value
            )
            is_negative = (
                case_status in RESOLVED_NEGATIVE_STATUSES
                and payment_status == PaymentStatus.FAILED.value
            )

            if not (is_positive or is_negative):
                # Unresolved case (e.g. OPEN, IN_RECOVERY, ACTION_REQUIRED) -> EXCLUDE
                continue

            label = 1 if is_positive else 0

            # Determine timestamp for strict feature evaluation (pre-resolution)
            case_open_time = _to_utc(case.opened_at or case.created_at)
            if eval_cutoff and case_open_time and case_open_time > eval_cutoff:
                continue

            # Extract attempts strictly initiated at or before case open time
            attempts: list[PaymentAttempt] = payment.attempts or []

            # Deterministic feature extraction
            features = extract_features(
                recovery_case=case,
                payment=payment,
                customer=customer,
                attempts=attempts,
                as_of=case_open_time,
            )

            # Validate zero PII
            validate_no_pii_in_features(features.model_dump())

            dataset.append(
                {
                    "case_id": str(case.id),
                    "features": features,
                    "label": label,
                    "created_at": (
                        case_open_time.isoformat() if case_open_time else None
                    ),
                }
            )

        return dataset

    def build_metadata(self, records: list[dict[str, Any]]) -> TrainingDatasetMetadata:
        """
        Compute deterministic summary metadata for the dataset.
        """
        sample_size = len(records)
        pos_count = sum(1 for r in records if r["label"] == 1)
        neg_count = sum(1 for r in records if r["label"] == 0)
        class_balance = round(pos_count / sample_size, 4) if sample_size > 0 else 0.0

        dates = [r["created_at"] for r in records if r.get("created_at")]
        start_date = min(dates) if dates else None
        end_date = max(dates) if dates else None

        dataset_hash = compute_dataset_hash(records)

        return TrainingDatasetMetadata(
            sample_size=sample_size,
            positive_count=pos_count,
            negative_count=neg_count,
            class_balance=class_balance,
            feature_names=FEATURE_NAMES,
            feature_schema_version=FEATURE_SCHEMA_VERSION,
            dataset_hash=dataset_hash,
            temporal_range_start=start_date,
            temporal_range_end=end_date,
        )

    def partition_temporal_split(
        self, records: list[dict[str, Any]], split_ratio: float = 0.70
    ) -> tuple[list[dict[str, Any]], list[dict[str, Any]], TrainingDatasetSplit]:
        """
        Deterministically split records into training and validation sets.
        Earlier resolved cases -> Training (70%)
        Later resolved cases -> Validation (30%)
        """
        if not records:
            empty_split = TrainingDatasetSplit(
                training_sample_size=0,
                validation_sample_size=0,
                training_dataset_hash=hashlib.sha256(b"").hexdigest(),
                validation_dataset_hash=hashlib.sha256(b"").hexdigest(),
                split_ratio=split_ratio,
            )
            return [], [], empty_split

        # Sort deterministically by creation timestamp, fallback to case_id
        sorted_records = sorted(
            records,
            key=lambda r: (r.get("created_at") or "", str(r.get("case_id", ""))),
        )

        n = len(sorted_records)
        split_idx = int(n * split_ratio)
        # Ensure at least 1 in each partition if n >= 2
        if n >= 2:
            split_idx = max(1, min(n - 1, split_idx))

        train_set = sorted_records[:split_idx]
        val_set = sorted_records[split_idx:]

        train_hash = compute_dataset_hash(train_set)
        val_hash = compute_dataset_hash(val_set)

        split_meta = TrainingDatasetSplit(
            training_sample_size=len(train_set),
            validation_sample_size=len(val_set),
            training_dataset_hash=train_hash,
            validation_dataset_hash=val_hash,
            split_ratio=split_ratio,
        )

        return train_set, val_set, split_meta
