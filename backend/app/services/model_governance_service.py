import logging
import math
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload, selectinload

from app.models import (
    CustomerRiskTier,
    MLPrediction,
    RecoveryCase,
    RecoveryCaseStatus,
)
from app.schemas.governance import (
    CalibrationBucketDrift,
    DataQualitySummary,
    FeatureDrift,
    GovernanceFinding,
    ModelGovernanceResponse,
    ModelVersionComparison,
    ModelVersionSummary,
    OutcomeDrift,
    PerformanceComparison,
    PerformanceWindow,
    PredictionBucketDrift,
    PredictionDistributionDrift,
)

logger = logging.getLogger(__name__)

# Governance Policy Constants
MIN_EVALUATION_SAMPLE_SIZE = 30
RECENT_WINDOW_DAYS = 30
MODEL_WARNING_DEGRADATION = 0.05  # 5 percentage points
MODEL_DEGRADED_DEGRADATION = 0.10  # 10 percentage points
BRIER_WARNING_DELTA = 0.05  # 0.05 MSE increase
BRIER_DEGRADED_DELTA = 0.10  # 0.10 MSE increase
PSI_WARNING_THRESHOLD = 0.10
PSI_CRITICAL_THRESHOLD = 0.25
EPSILON = 1e-4

RESOLVED_CASE_STATUSES = {
    RecoveryCaseStatus.RECOVERED.value,
    RecoveryCaseStatus.CLOSED.value,
    RecoveryCaseStatus.EXHAUSTED.value,
}

PROBABILITY_BINS = [
    (0.0, 0.2),
    (0.2, 0.4),
    (0.4, 0.6),
    (0.6, 0.8),
    (0.8, 1.0),
]


def _to_utc(dt: datetime | None) -> datetime | None:
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=UTC)
    return dt.astimezone(UTC)


class CasePredictionRecord:
    """In-memory projection of a resolved recovery case and its associated prediction."""

    def __init__(self, case: RecoveryCase) -> None:
        self.case_id = case.id
        self.is_recovered = case.status == RecoveryCaseStatus.RECOVERED.value or (
            case.recovered_amount > 0 and case.status in RESOLVED_CASE_STATUSES
        )
        self.resolved_at = _to_utc(
            case.resolved_at or case.opened_at or case.created_at
        )
        self.risk_tier = (
            case.customer.risk_tier
            if case.customer
            else CustomerRiskTier.STANDARD.value
        )
        self.failure_reason = case.latest_failure_reason or "unknown"

        latest_pred = case.predictions[-1] if case.predictions else None
        self.has_prediction = latest_pred is not None
        self.model_name = (
            latest_pred.model_name if latest_pred else "recovery_probability"
        )
        self.model_version = latest_pred.model_version if latest_pred else "v1.0"
        self.probability = (
            float(latest_pred.recovery_probability) if latest_pred else None
        )
        self.predicted_at = (
            _to_utc(latest_pred.predicted_at) if latest_pred else self.resolved_at
        )
        self.features: dict[str, Any] = (
            latest_pred.feature_vector_snapshot
            if latest_pred and isinstance(latest_pred.feature_vector_snapshot, dict)
            else {}
        )


class ModelGovernanceService:
    """
    Read-only governance, drift monitoring, and intelligence health evaluation service.
    Zero mutations, zero gateway calls, strictly observational.
    """

    def _load_resolved_records(self, db: Session) -> list[CasePredictionRecord]:
        """Fetch all resolved recovery cases with joined prediction data."""
        cases = (
            db.query(RecoveryCase)
            .options(
                joinedload(RecoveryCase.customer),
                selectinload(RecoveryCase.predictions),
            )
            .filter(RecoveryCase.status.in_(RESOLVED_CASE_STATUSES))
            .order_by(RecoveryCase.created_at.asc())
            .all()
        )
        return [CasePredictionRecord(c) for c in cases]

    def _compute_window_metrics(
        self,
        records: list[CasePredictionRecord],
        window_name: str,
        window_days: int | None,
    ) -> PerformanceWindow:
        """Compute classification, Brier, and recovery rate for a subset of records."""
        valid_records = [r for r in records if r.probability is not None]
        n = len(valid_records)

        if n == 0:
            return PerformanceWindow(
                window_name=window_name,
                window_days=window_days,
                sample_size=0,
                accuracy=None,
                precision=None,
                recall=None,
                f1_score=None,
                brier_score=None,
                recovery_rate=None,
            )

        tp = sum(
            1
            for r in valid_records
            if (r.probability or 0.0) >= 0.50 and r.is_recovered
        )
        fp = sum(
            1
            for r in valid_records
            if (r.probability or 0.0) >= 0.50 and not r.is_recovered
        )
        tn = sum(
            1
            for r in valid_records
            if (r.probability or 0.0) < 0.50 and not r.is_recovered
        )
        fn = sum(
            1 for r in valid_records if (r.probability or 0.0) < 0.50 and r.is_recovered
        )

        accuracy = round((tp + tn) / n, 4)
        precision = round(tp / (tp + fp), 4) if (tp + fp) > 0 else None
        recall = round(tp / (tp + fn), 4) if (tp + fn) > 0 else None

        f1: float | None = None
        if precision is not None and recall is not None and (precision + recall) > 0:
            f1 = round(2.0 * (precision * recall) / (precision + recall), 4)

        brier_sum = sum(
            ((r.probability or 0.0) - (1.0 if r.is_recovered else 0.0)) ** 2
            for r in valid_records
        )
        brier = round(brier_sum / n, 4)

        recovered_count = sum(1 for r in valid_records if r.is_recovered)
        recovery_rate = round(recovered_count / n, 4)

        return PerformanceWindow(
            window_name=window_name,
            window_days=window_days,
            sample_size=n,
            accuracy=accuracy,
            precision=precision,
            recall=recall,
            f1_score=f1,
            brier_score=brier,
            recovery_rate=recovery_rate,
        )

    def _compute_psi(
        self,
        ref_values: list[Any],
        recent_values: list[Any],
        is_numerical: bool,
    ) -> tuple[float | None, str, dict[str, Any]]:
        """
        Calculate Population Stability Index (PSI) between reference and recent samples.
        PSI = sum((recent_pct - ref_pct) * ln((recent_pct + eps) / (ref_pct + eps)))
        """
        n_ref = len(ref_values)
        n_rec = len(recent_values)

        if n_ref < 5 or n_rec < 5:
            return None, "INSUFFICIENT_DATA", {}

        bins_detail: dict[str, Any] = {}

        if is_numerical:
            num_ref = [
                float(v)
                for v in ref_values
                if v is not None and not math.isnan(float(v))
            ]
            num_rec = [
                float(v)
                for v in recent_values
                if v is not None and not math.isnan(float(v))
            ]
            if len(num_ref) < 5 or len(num_rec) < 5:
                return None, "INSUFFICIENT_DATA", {}

            combined = num_ref + num_rec
            min_val = min(combined)
            max_val = max(combined)
            if min_val == max_val:
                # Zero variance across entire population
                return 0.0, "LOW", {"note": "Zero variance in feature data"}

            # Create 4 equal intervals based on combined range
            step = (max_val - min_val) / 4.0
            thresholds = [min_val + step * i for i in range(1, 4)]

            def get_bin_idx(val: float) -> int:
                for idx, t in enumerate(thresholds):
                    if val <= t:
                        return idx
                return len(thresholds)

            ref_counts = [0] * (len(thresholds) + 1)
            rec_counts = [0] * (len(thresholds) + 1)

            for v in num_ref:
                ref_counts[get_bin_idx(v)] += 1
            for v in num_rec:
                rec_counts[get_bin_idx(v)] += 1

            psi = 0.0
            for i in range(len(ref_counts)):
                p_ref = ref_counts[i] / len(num_ref)
                p_rec = rec_counts[i] / len(num_rec)
                term = (p_rec - p_ref) * math.log((p_rec + EPSILON) / (p_ref + EPSILON))
                psi += term
                bins_detail[f"bin_{i}"] = {
                    "ref_pct": round(p_ref, 4),
                    "rec_pct": round(p_rec, 4),
                }

        else:
            # Categorical PSI
            categories = sorted(
                set(str(v) for v in ref_values if v is not None)
                | set(str(v) for v in recent_values if v is not None)
            )
            if not categories:
                return None, "INSUFFICIENT_DATA", {}

            ref_str = [str(v) for v in ref_values if v is not None]
            rec_str = [str(v) for v in recent_values if v is not None]

            psi = 0.0
            for cat in categories:
                c_ref = ref_str.count(cat)
                c_rec = rec_str.count(cat)
                p_ref = c_ref / len(ref_str) if ref_str else 0.0
                p_rec = c_rec / len(rec_str) if rec_str else 0.0
                term = (p_rec - p_ref) * math.log((p_rec + EPSILON) / (p_ref + EPSILON))
                psi += term
                bins_detail[cat] = {
                    "ref_pct": round(p_ref, 4),
                    "rec_pct": round(p_rec, 4),
                }

        psi_rounded = round(max(0.0, psi), 4)
        if psi_rounded > PSI_CRITICAL_THRESHOLD:
            level = "SIGNIFICANT"
        elif psi_rounded >= PSI_WARNING_THRESHOLD:
            level = "MODERATE"
        else:
            level = "LOW"

        return psi_rounded, level, bins_detail

    def _compute_feature_drifts(
        self,
        ref_records: list[CasePredictionRecord],
        recent_records: list[CasePredictionRecord],
    ) -> list[FeatureDrift]:
        """Measure Population Stability Index across key feature snapshot dimensions."""
        features_to_monitor = [
            ("payment_amount", True),
            ("customer_success_rate", True),
            ("hours_since_failure", True),
            ("attempt_number", True),
            ("error_reason", False),
            ("error_code", False),
            ("error_source", False),
        ]

        drifts: list[FeatureDrift] = []

        for feat_name, is_num in features_to_monitor:
            ref_vals = [
                r.features.get(feat_name)
                for r in ref_records
                if feat_name in r.features
            ]
            rec_vals = [
                r.features.get(feat_name)
                for r in recent_records
                if feat_name in r.features
            ]

            psi, level, details = self._compute_psi(
                ref_vals, rec_vals, is_numerical=is_num
            )

            drifts.append(
                FeatureDrift(
                    feature_name=feat_name,
                    feature_type="numerical" if is_num else "categorical",
                    psi=psi,
                    drift_level=level,
                    reference_sample_size=len(ref_vals),
                    recent_sample_size=len(rec_vals),
                    details=details,
                )
            )

        return drifts

    def _compute_prediction_distribution_drift(
        self,
        ref_records: list[CasePredictionRecord],
        recent_records: list[CasePredictionRecord],
    ) -> PredictionDistributionDrift:
        """Measure shift in predicted recovery probability distributions over discrete bins."""
        ref_probs = [r.probability for r in ref_records if r.probability is not None]
        rec_probs = [r.probability for r in recent_records if r.probability is not None]

        n_ref = len(ref_probs)
        n_rec = len(rec_probs)

        buckets: list[PredictionBucketDrift] = []
        psi_sum = 0.0

        for b_min, b_max in PROBABILITY_BINS:
            if b_max == 1.0:
                c_ref = sum(
                    1 for p in ref_probs if p is not None and b_min <= p <= b_max
                )
                c_rec = sum(
                    1 for p in rec_probs if p is not None and b_min <= p <= b_max
                )
            else:
                c_ref = sum(
                    1 for p in ref_probs if p is not None and b_min <= p < b_max
                )
                c_rec = sum(
                    1 for p in rec_probs if p is not None and b_min <= p < b_max
                )

            p_ref = round(c_ref / n_ref, 4) if n_ref > 0 else None
            p_rec = round(c_rec / n_rec, 4) if n_rec > 0 else None
            delta = (
                round(p_rec - p_ref, 4)
                if (p_ref is not None and p_rec is not None)
                else None
            )

            if p_ref is not None and p_rec is not None and n_ref >= 5 and n_rec >= 5:
                term = (p_rec - p_ref) * math.log((p_rec + EPSILON) / (p_ref + EPSILON))
                psi_sum += term

            buckets.append(
                PredictionBucketDrift(
                    bucket_min=b_min,
                    bucket_max=b_max,
                    historical_percentage=p_ref,
                    recent_percentage=p_rec,
                    delta=delta,
                )
            )

        if n_ref < 5 or n_rec < 5:
            psi_val = None
            drift_level = "INSUFFICIENT_DATA"
        else:
            psi_val = round(max(0.0, psi_sum), 4)
            drift_level = (
                "SIGNIFICANT"
                if psi_val > PSI_CRITICAL_THRESHOLD
                else "MODERATE"
                if psi_val >= PSI_WARNING_THRESHOLD
                else "LOW"
            )

        return PredictionDistributionDrift(
            psi=psi_val,
            drift_level=drift_level,
            buckets=buckets,
        )

    def _compute_outcome_drift(
        self,
        ref_records: list[CasePredictionRecord],
        recent_records: list[CasePredictionRecord],
    ) -> OutcomeDrift:
        """Measure macro shifts in empirical recovery outcomes between reference and recent periods."""
        n_ref = len(ref_records)
        n_rec = len(recent_records)

        rec_ref = sum(1 for r in ref_records if r.is_recovered)
        rec_rec = sum(1 for r in recent_records if r.is_recovered)

        h_rate = round(rec_ref / n_ref, 4) if n_ref > 0 else None
        r_rate = round(rec_rec / n_rec, 4) if n_rec > 0 else None
        delta = (
            round(r_rate - h_rate, 4)
            if (h_rate is not None and r_rate is not None)
            else None
        )

        if n_ref < 5 or n_rec < 5 or delta is None:
            drift_level = "INSUFFICIENT_DATA"
        elif abs(delta) >= 0.15:
            drift_level = "SIGNIFICANT"
        elif abs(delta) >= 0.05:
            drift_level = "MODERATE"
        else:
            drift_level = "LOW"

        return OutcomeDrift(
            historical_recovery_rate=h_rate,
            recent_recovery_rate=r_rate,
            delta=delta,
            drift_level=drift_level,
        )

    def _compute_calibration_drift(
        self,
        ref_records: list[CasePredictionRecord],
        recent_records: list[CasePredictionRecord],
    ) -> list[CalibrationBucketDrift]:
        """Measure shift in calibration reliability between reference and recent windows."""
        drifts: list[CalibrationBucketDrift] = []

        for b_min, b_max in PROBABILITY_BINS:
            # Reference in bucket
            if b_max == 1.0:
                in_ref = [
                    r
                    for r in ref_records
                    if r.probability is not None and b_min <= r.probability <= b_max
                ]
                in_rec = [
                    r
                    for r in recent_records
                    if r.probability is not None and b_min <= r.probability <= b_max
                ]
            else:
                in_ref = [
                    r
                    for r in ref_records
                    if r.probability is not None and b_min <= r.probability < b_max
                ]
                in_rec = [
                    r
                    for r in recent_records
                    if r.probability is not None and b_min <= r.probability < b_max
                ]

            h_avg = (
                round(sum(r.probability or 0.0 for r in in_ref) / len(in_ref), 4)
                if in_ref
                else None
            )
            h_rec = (
                round(sum(1.0 for r in in_ref if r.is_recovered) / len(in_ref), 4)
                if in_ref
                else None
            )
            h_err = (
                round(abs(h_avg - h_rec), 4)
                if (h_avg is not None and h_rec is not None)
                else None
            )

            r_avg = (
                round(sum(r.probability or 0.0 for r in in_rec) / len(in_rec), 4)
                if in_rec
                else None
            )
            r_rec = (
                round(sum(1.0 for r in in_rec if r.is_recovered) / len(in_rec), 4)
                if in_rec
                else None
            )
            r_err = (
                round(abs(r_avg - r_rec), 4)
                if (r_avg is not None and r_rec is not None)
                else None
            )

            err_delta = (
                round(r_err - h_err, 4)
                if (r_err is not None and h_err is not None)
                else None
            )

            drifts.append(
                CalibrationBucketDrift(
                    bucket_min=b_min,
                    bucket_max=b_max,
                    historical_pred_avg=h_avg,
                    historical_recovery_rate=h_rec,
                    historical_calibration_error=h_err,
                    recent_pred_avg=r_avg,
                    recent_recovery_rate=r_rec,
                    recent_calibration_error=r_err,
                    calibration_error_delta=err_delta,
                )
            )

        return drifts

    def _compute_model_versions(
        self, records: list[CasePredictionRecord]
    ) -> tuple[list[ModelVersionSummary], list[ModelVersionComparison]]:
        """Identify historical model versions and calculate comparative performance."""
        grouped: dict[str, list[CasePredictionRecord]] = {}
        for r in records:
            if r.has_prediction:
                key = f"{r.model_name}:{r.model_version}"
                grouped.setdefault(key, []).append(r)

        summaries: list[ModelVersionSummary] = []
        for key, v_records in grouped.items():
            model_name, model_ver = key.split(":", 1)
            valid_recs = [r for r in v_records if r.probability is not None]
            n = len(valid_recs)

            first_seen = min(
                (r.predicted_at for r in valid_recs if r.predicted_at), default=None
            )
            last_seen = max(
                (r.predicted_at for r in valid_recs if r.predicted_at), default=None
            )

            accuracy = (
                round(
                    sum(
                        1
                        for r in valid_recs
                        if ((r.probability or 0.0) >= 0.50 and r.is_recovered)
                        or ((r.probability or 0.0) < 0.50 and not r.is_recovered)
                    )
                    / n,
                    4,
                )
                if n > 0
                else None
            )

            brier = (
                round(
                    sum(
                        ((r.probability or 0.0) - (1.0 if r.is_recovered else 0.0)) ** 2
                        for r in valid_recs
                    )
                    / n,
                    4,
                )
                if n > 0
                else None
            )

            rec_rate = (
                round(sum(1 for r in valid_recs if r.is_recovered) / n, 4)
                if n > 0
                else None
            )

            summaries.append(
                ModelVersionSummary(
                    model_name=model_name,
                    model_version=model_ver,
                    sample_size=n,
                    first_seen=first_seen,
                    last_seen=last_seen,
                    accuracy=accuracy,
                    brier_score=brier,
                    recovery_rate=rec_rate,
                )
            )

        # Comparative regression analysis across versions
        comparisons: list[ModelVersionComparison] = []
        if len(summaries) >= 2:
            summaries_sorted = sorted(
                summaries, key=lambda s: s.sample_size, reverse=True
            )
            baseline = summaries_sorted[0]
            for candidate in summaries_sorted[1:]:
                acc_delta = (
                    round(candidate.accuracy - baseline.accuracy, 4)
                    if (
                        candidate.accuracy is not None and baseline.accuracy is not None
                    )
                    else None
                )
                brier_delta = (
                    round(candidate.brier_score - baseline.brier_score, 4)
                    if (
                        candidate.brier_score is not None
                        and baseline.brier_score is not None
                    )
                    else None
                )

                if candidate.sample_size < MIN_EVALUATION_SAMPLE_SIZE:
                    statement = f"Insufficient sample size ({candidate.sample_size} cases) to establish conclusive performance comparison against {baseline.model_version}."
                elif (
                    acc_delta is not None
                    and acc_delta > 0.02
                    and brier_delta is not None
                    and brier_delta < -0.02
                ):
                    statement = f"Observed empirical improvement over baseline {baseline.model_version} across evaluated cases."
                elif acc_delta is not None and acc_delta < -0.05:
                    statement = f"Observed empirical degradation relative to baseline {baseline.model_version} across evaluated cases."
                else:
                    statement = f"Comparable empirical performance observed relative to baseline {baseline.model_version}."

                comparisons.append(
                    ModelVersionComparison(
                        baseline_version=baseline.model_version,
                        comparison_version=candidate.model_version,
                        baseline_sample_size=baseline.sample_size,
                        comparison_sample_size=candidate.sample_size,
                        accuracy_delta=acc_delta,
                        f1_delta=None,
                        brier_delta=brier_delta,
                        evidence_statement=statement,
                    )
                )

        return summaries, comparisons

    def _audit_data_quality(self, db: Session) -> DataQualitySummary:
        """Inspect recorded predictions table for structural completeness and value validity."""
        total = db.query(func.count(MLPrediction.id)).scalar() or 0
        if total == 0:
            return DataQualitySummary(
                total_predictions=0,
                valid_predictions=0,
                invalid_predictions=0,
                missing_feature_vectors=0,
                missing_model_versions=0,
                invalid_probability_count=0,
                missing_timestamps=0,
            )

        # Inspect anomalies across stored records
        all_preds = db.query(MLPrediction).all()
        missing_fv = 0
        missing_mv = 0
        invalid_prob = 0
        missing_ts = 0

        for p in all_preds:
            if not p.feature_vector_snapshot or not isinstance(
                p.feature_vector_snapshot, dict
            ):
                missing_fv += 1
            if not p.model_version or not p.model_name:
                missing_mv += 1
            if (
                p.recovery_probability is None
                or float(p.recovery_probability) < 0.0
                or float(p.recovery_probability) > 1.0
            ):
                invalid_prob += 1
            if not p.predicted_at:
                missing_ts += 1

        invalid_count = missing_fv + missing_mv + invalid_prob + missing_ts
        valid_count = max(0, total - invalid_count)

        return DataQualitySummary(
            total_predictions=total,
            valid_predictions=valid_count,
            invalid_predictions=invalid_count,
            missing_feature_vectors=missing_fv,
            missing_model_versions=missing_mv,
            invalid_probability_count=invalid_prob,
            missing_timestamps=missing_ts,
        )

    def evaluate_governance(self, db: Session) -> ModelGovernanceResponse:
        """
        Execute comprehensive model governance, drift detection, and health audit.
        Zero database mutations.
        """
        now_utc = datetime.now(UTC)
        records = self._load_resolved_records(db)
        data_quality = self._audit_data_quality(db)

        # Active model metadata
        model_name = "recovery_probability"
        model_version = "v1.0"
        first_pred_at: datetime | None = None
        last_pred_at: datetime | None = None

        pred_records = [r for r in records if r.has_prediction]
        if pred_records:
            model_name = pred_records[-1].model_name
            model_version = pred_records[-1].model_version
            first_pred_at = min(
                (r.predicted_at for r in pred_records if r.predicted_at), default=None
            )
            last_pred_at = max(
                (r.predicted_at for r in pred_records if r.predicted_at), default=None
            )

        total_sample_size = len(pred_records)

        # 1. Performance Windows (7d, 30d, 90d, historical)
        win_7d_cutoff = now_utc - timedelta(days=7)
        win_30d_cutoff = now_utc - timedelta(days=30)
        win_90d_cutoff = now_utc - timedelta(days=90)

        rec_7d = [
            r for r in pred_records if r.resolved_at and r.resolved_at >= win_7d_cutoff
        ]
        rec_30d = [
            r for r in pred_records if r.resolved_at and r.resolved_at >= win_30d_cutoff
        ]
        rec_90d = [
            r for r in pred_records if r.resolved_at and r.resolved_at >= win_90d_cutoff
        ]

        w_7d = self._compute_window_metrics(rec_7d, "7d", 7)
        w_30d = self._compute_window_metrics(rec_30d, "30d", 30)
        w_90d = self._compute_window_metrics(rec_90d, "90d", 90)
        w_hist = self._compute_window_metrics(pred_records, "historical", None)

        windows = [w_7d, w_30d, w_90d, w_hist]

        # 2. Performance Comparison (Historical vs Recent 30d)
        # If 30d is empty or small, fallback to most populated recent window or comparison
        recent_window = (
            w_30d
            if w_30d.sample_size > 0
            else (w_90d if w_90d.sample_size > 0 else w_hist)
        )
        recent_label = recent_window.window_name

        acc_delta = (
            round(recent_window.accuracy - w_hist.accuracy, 4)
            if (recent_window.accuracy is not None and w_hist.accuracy is not None)
            else None
        )
        prec_delta = (
            round(recent_window.precision - w_hist.precision, 4)
            if (recent_window.precision is not None and w_hist.precision is not None)
            else None
        )
        rec_delta = (
            round(recent_window.recall - w_hist.recall, 4)
            if (recent_window.recall is not None and w_hist.recall is not None)
            else None
        )
        f1_delta = (
            round(recent_window.f1_score - w_hist.f1_score, 4)
            if (recent_window.f1_score is not None and w_hist.f1_score is not None)
            else None
        )
        brier_delta = (
            round(recent_window.brier_score - w_hist.brier_score, 4)
            if (
                recent_window.brier_score is not None and w_hist.brier_score is not None
            )
            else None
        )
        rr_delta = (
            round(recent_window.recovery_rate - w_hist.recovery_rate, 4)
            if (
                recent_window.recovery_rate is not None
                and w_hist.recovery_rate is not None
            )
            else None
        )

        comparison = PerformanceComparison(
            baseline_window="historical",
            recent_window=recent_label,
            baseline_sample_size=w_hist.sample_size,
            recent_sample_size=recent_window.sample_size,
            accuracy_delta=acc_delta,
            precision_delta=prec_delta,
            recall_delta=rec_delta,
            f1_delta=f1_delta,
            brier_delta=brier_delta,
            recovery_rate_delta=rr_delta,
        )

        # 3. Drift Analysis (Historical reference vs Recent 30d records)
        # Partition reference and recent records
        if len(rec_30d) >= 5 and len(pred_records) > len(rec_30d):
            ref_pool = [
                r
                for r in pred_records
                if r.resolved_at and r.resolved_at < win_30d_cutoff
            ]
            rec_pool = rec_30d
        elif len(pred_records) >= 10:
            # If dates are synthetic or tightly clustered, partition 50/50 for drift testing
            midpoint = len(pred_records) // 2
            ref_pool = pred_records[:midpoint]
            rec_pool = pred_records[midpoint:]
        else:
            ref_pool = pred_records
            rec_pool = pred_records

        feature_drifts = self._compute_feature_drifts(ref_pool, rec_pool)
        pred_drift = self._compute_prediction_distribution_drift(ref_pool, rec_pool)
        outcome_drift = self._compute_outcome_drift(ref_pool, rec_pool)
        cal_drift = self._compute_calibration_drift(ref_pool, rec_pool)

        # 4. Model Version Footprint
        version_summaries, version_comparisons = self._compute_model_versions(records)

        # 5. Health Status & Findings Derivation
        findings: list[GovernanceFinding] = []
        warnings_list: list[str] = []
        critical_list: list[str] = []

        if total_sample_size < MIN_EVALUATION_SAMPLE_SIZE:
            status = "INSUFFICIENT_DATA"
            findings.append(
                GovernanceFinding(
                    code="LOW_SAMPLE_SIZE",
                    severity="INFO",
                    message=f"Sample size ({total_sample_size}) is below minimum governance threshold ({MIN_EVALUATION_SAMPLE_SIZE}). Model health status is non-conclusive.",
                    baseline_value=float(MIN_EVALUATION_SAMPLE_SIZE),
                    recent_value=float(total_sample_size),
                    delta=float(total_sample_size - MIN_EVALUATION_SAMPLE_SIZE),
                )
            )
        else:
            # Check degradation signals
            is_degraded = False
            is_warning = False

            # Classification degradation
            if acc_delta is not None and acc_delta <= -MODEL_DEGRADED_DEGRADATION:
                is_degraded = True
                msg = f"Critical accuracy drop: recent accuracy degraded by {abs(acc_delta):.1%} relative to historical baseline."
                critical_list.append(msg)
                findings.append(
                    GovernanceFinding(
                        code="SIGNIFICANT_PERFORMANCE_DEGRADATION",
                        severity="CRITICAL",
                        message=msg,
                        metric_name="accuracy",
                        baseline_value=w_hist.accuracy,
                        recent_value=recent_window.accuracy,
                        delta=acc_delta,
                    )
                )
            elif acc_delta is not None and acc_delta <= -MODEL_WARNING_DEGRADATION:
                is_warning = True
                msg = f"Moderate accuracy drop: recent accuracy degraded by {abs(acc_delta):.1%} relative to historical baseline."
                warnings_list.append(msg)
                findings.append(
                    GovernanceFinding(
                        code="PERFORMANCE_DEGRADATION",
                        severity="WARNING",
                        message=msg,
                        metric_name="accuracy",
                        baseline_value=w_hist.accuracy,
                        recent_value=recent_window.accuracy,
                        delta=acc_delta,
                    )
                )

            # Brier score degradation (positive delta = worse calibration)
            if brier_delta is not None and brier_delta >= BRIER_DEGRADED_DELTA:
                is_degraded = True
                msg = f"Critical Brier calibration degradation: MSE increased by +{brier_delta:.4f} relative to historical baseline."
                critical_list.append(msg)
                findings.append(
                    GovernanceFinding(
                        code="SIGNIFICANT_PERFORMANCE_DEGRADATION",
                        severity="CRITICAL",
                        message=msg,
                        metric_name="brier_score",
                        baseline_value=w_hist.brier_score,
                        recent_value=recent_window.brier_score,
                        delta=brier_delta,
                    )
                )
            elif brier_delta is not None and brier_delta >= BRIER_WARNING_DELTA:
                is_warning = True
                msg = f"Moderate Brier calibration degradation: MSE increased by +{brier_delta:.4f} relative to historical baseline."
                warnings_list.append(msg)
                findings.append(
                    GovernanceFinding(
                        code="PERFORMANCE_DEGRADATION",
                        severity="WARNING",
                        message=msg,
                        metric_name="brier_score",
                        baseline_value=w_hist.brier_score,
                        recent_value=recent_window.brier_score,
                        delta=brier_delta,
                    )
                )

            # Check feature drift findings
            for fd in feature_drifts:
                if fd.drift_level == "SIGNIFICANT":
                    msg = f"Significant feature drift detected on '{fd.feature_name}' (PSI={fd.psi:.4f})."
                    warnings_list.append(msg)
                    findings.append(
                        GovernanceFinding(
                            code="FEATURE_DRIFT",
                            severity="WARNING",
                            message=msg,
                            metric_name=fd.feature_name,
                            delta=fd.psi,
                        )
                    )

            # Check prediction drift findings
            if pred_drift.drift_level == "SIGNIFICANT":
                msg = f"Significant prediction distribution shift detected (PSI={pred_drift.psi:.4f})."
                warnings_list.append(msg)
                findings.append(
                    GovernanceFinding(
                        code="PREDICTION_DRIFT",
                        severity="WARNING",
                        message=msg,
                        metric_name="prediction_psi",
                        delta=pred_drift.psi,
                    )
                )

            # Check outcome drift findings
            if outcome_drift.drift_level == "SIGNIFICANT":
                msg = f"Observed macro outcome recovery rate shift (Δ={outcome_drift.delta:+.1%}). Note: outcome drift reflects changing transaction/gateway composition."
                warnings_list.append(msg)
                findings.append(
                    GovernanceFinding(
                        code="OUTCOME_DRIFT",
                        severity="INFO",
                        message=msg,
                        metric_name="recovery_rate",
                        baseline_value=outcome_drift.historical_recovery_rate,
                        recent_value=outcome_drift.recent_recovery_rate,
                        delta=outcome_drift.delta,
                    )
                )

            if is_degraded:
                status = "DEGRADED"
            elif is_warning:
                status = "WARNING"
            else:
                status = "HEALTHY"

        # Data quality findings
        if data_quality.invalid_predictions > 0:
            dq_msg = f"Data quality alert: {data_quality.invalid_predictions} out of {data_quality.total_predictions} prediction records contain missing features, versions, or invalid values."
            warnings_list.append(dq_msg)
            findings.append(
                GovernanceFinding(
                    code="DATA_QUALITY_ISSUE",
                    severity="WARNING",
                    message=dq_msg,
                    baseline_value=float(data_quality.total_predictions),
                    recent_value=float(data_quality.invalid_predictions),
                )
            )

        logger.info(
            "model_governance_evaluated",
            extra={
                "status": status,
                "sample_size": total_sample_size,
                "warnings_count": len(warnings_list),
                "critical_count": len(critical_list),
            },
        )

        return ModelGovernanceResponse(
            status=status,
            model_name=model_name,
            model_version=model_version,
            sample_size=total_sample_size,
            minimum_required_sample_size=MIN_EVALUATION_SAMPLE_SIZE,
            first_prediction_at=first_pred_at,
            last_prediction_at=last_pred_at,
            performance_windows=windows,
            performance_comparison=comparison,
            feature_drift=feature_drifts,
            prediction_drift=pred_drift,
            outcome_drift=outcome_drift,
            calibration_drift=cal_drift,
            model_versions=version_summaries,
            version_comparisons=version_comparisons,
            data_quality=data_quality,
            findings=findings,
            warnings=warnings_list,
            critical_findings=critical_list,
            generated_at=now_utc,
        )


model_governance_service = ModelGovernanceService()
