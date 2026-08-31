import logging
import math
import statistics
from datetime import UTC, datetime

from sqlalchemy.orm import Session, joinedload, selectinload

from app.models import (
    CustomerRiskTier,
    PolicyEvaluationResult,
    RecoveryActionType,
    RecoveryCase,
    RecoveryCaseStatus,
)
from app.schemas.evaluation import (
    ActionAttributionItem,
    ActionDurationItem,
    CalibrationBucket,
    ClassificationMetrics,
    ConfidenceOutcomeMetrics,
    FailureReasonSegmentItem,
    IntelligenceEvaluationResponse,
    ModelMetadata,
    PolicyAlignmentItem,
    PriorityDurationItem,
    RecoveryDurationMetrics,
    RiskSegmentItem,
)

logger = logging.getLogger(__name__)

RESOLVED_CASE_STATUSES = {
    RecoveryCaseStatus.RECOVERED.value,
    RecoveryCaseStatus.CLOSED.value,
    RecoveryCaseStatus.EXHAUSTED.value,
}

CALIBRATION_INTERVALS = [
    (0.0, 0.2),
    (0.2, 0.4),
    (0.4, 0.6),
    (0.6, 0.8),
    (0.8, 1.0),
]

KNOWN_ACTION_TYPES = [
    RecoveryActionType.RETRY_PAYMENT.value,
    RecoveryActionType.SEND_PAYMENT_LINK.value,
    RecoveryActionType.SEND_NOTIFICATION.value,
    RecoveryActionType.ESCALATE_HUMAN.value,
    RecoveryActionType.HALT_SUBSCRIPTION.value,
    RecoveryActionType.CLOSE_CASE.value,
]

KNOWN_POLICY_OUTCOMES = [
    PolicyEvaluationResult.ALLOWED.value,
    PolicyEvaluationResult.BLOCKED.value,
    PolicyEvaluationResult.HUMAN_REVIEW.value,
]

KNOWN_RISK_TIERS = [
    CustomerRiskTier.LOW.value,
    CustomerRiskTier.STANDARD.value,
    CustomerRiskTier.HIGH.value,
    CustomerRiskTier.BLOCKED.value,
]


class CaseObservation:
    """Immutable in-memory projection of a resolved recovery case and its intelligence trail."""

    def __init__(
        self,
        case: RecoveryCase,
    ) -> None:
        self.case_id = case.id
        self.is_recovered = case.status == RecoveryCaseStatus.RECOVERED.value or (
            case.recovered_amount > 0 and case.status in RESOLVED_CASE_STATUSES
        )
        self.amount_at_risk = case.amount_at_risk
        self.recovered_amount = case.recovered_amount
        self.opened_at = case.opened_at
        self.resolved_at = case.resolved_at
        self.failure_reason = case.latest_failure_reason or "unknown"
        self.risk_tier = (
            case.customer.risk_tier
            if case.customer
            else CustomerRiskTier.STANDARD.value
        )

        # Duration in hours (only applicable if resolved)
        self.duration_hours: float | None = None
        if self.is_recovered and case.resolved_at and case.opened_at:
            delta_sec = max(0.0, (case.resolved_at - case.opened_at).total_seconds())
            self.duration_hours = round(delta_sec / 3600.0, 4)

        # Intelligence Trail
        latest_pred = case.predictions[-1] if case.predictions else None
        self.has_prediction = latest_pred is not None
        self.model_name = (
            latest_pred.model_name if latest_pred else "recovery_probability"
        )
        self.model_version = latest_pred.model_version if latest_pred else "v1.0"
        self.recovery_probability = (
            float(latest_pred.recovery_probability) if latest_pred else None
        )
        self.priority = (
            latest_pred.feature_vector_snapshot.get("priority")
            if latest_pred and isinstance(latest_pred.feature_vector_snapshot, dict)
            else (
                "HIGH_RECOVERY_POTENTIAL"
                if (self.recovery_probability or 0) >= 0.75
                else "MEDIUM_RECOVERY_POTENTIAL"
                if (self.recovery_probability or 0) >= 0.40
                else "LOW_RECOVERY_POTENTIAL"
            )
        )

        latest_dec = case.agent_decisions[-1] if case.agent_decisions else None
        self.has_decision = latest_dec is not None
        self.proposed_action_type = (
            latest_dec.proposed_action_type if latest_dec else None
        )
        self.confidence_score = (
            float(latest_dec.confidence_score) if latest_dec else None
        )

        latest_pol = case.policy_decisions[-1] if case.policy_decisions else None
        self.has_policy = latest_pol is not None
        self.policy_outcome = latest_pol.evaluation_result if latest_pol else None


class IntelligenceEvaluationService:
    """
    Observational analytical engine for evaluating ML model performance,
    AI recommendation alignment, policy clearance, and recovery outcomes.
    """

    def _load_resolved_observations(self, db: Session) -> list[CaseObservation]:
        """Fetch and project resolved recovery cases with complete intelligence trail."""
        cases = (
            db.query(RecoveryCase)
            .options(
                joinedload(RecoveryCase.customer),
                selectinload(RecoveryCase.predictions),
                selectinload(RecoveryCase.agent_decisions),
                selectinload(RecoveryCase.policy_decisions),
            )
            .filter(RecoveryCase.status.in_(RESOLVED_CASE_STATUSES))
            .order_by(RecoveryCase.created_at.asc())
            .all()
        )
        return [CaseObservation(c) for c in cases]

    def _compute_classification_and_brier(
        self, observations: list[CaseObservation], threshold: float = 0.50
    ) -> ClassificationMetrics:
        """Calculate confusion matrix, classification metrics, and Brier score."""
        pred_obs = [o for o in observations if o.recovery_probability is not None]
        sample_size = len(pred_obs)

        if sample_size == 0:
            return ClassificationMetrics(
                sample_size=0,
                threshold=threshold,
                true_positive=0,
                false_positive=0,
                true_negative=0,
                false_negative=0,
                accuracy=None,
                precision=None,
                recall=None,
                f1_score=None,
                brier_score=None,
            )

        tp = 0
        fp = 0
        tn = 0
        fn = 0
        brier_sum = 0.0

        for obs in pred_obs:
            prob = obs.recovery_probability or 0.0
            actual = 1.0 if obs.is_recovered else 0.0
            brier_sum += (prob - actual) ** 2

            pred_pos = prob >= threshold
            if pred_pos and obs.is_recovered:
                tp += 1
            elif pred_pos and not obs.is_recovered:
                fp += 1
            elif not pred_pos and not obs.is_recovered:
                tn += 1
            else:
                fn += 1

        accuracy = round((tp + tn) / sample_size, 4)
        precision = round(tp / (tp + fp), 4) if (tp + fp) > 0 else None
        recall = round(tp / (tp + fn), 4) if (tp + fn) > 0 else None

        f1: float | None = None
        if precision is not None and recall is not None and (precision + recall) > 0:
            f1 = round(2.0 * (precision * recall) / (precision + recall), 4)

        brier = round(brier_sum / sample_size, 4)

        return ClassificationMetrics(
            sample_size=sample_size,
            threshold=threshold,
            true_positive=tp,
            false_positive=fp,
            true_negative=tn,
            false_negative=fn,
            accuracy=accuracy,
            precision=precision,
            recall=recall,
            f1_score=f1,
            brier_score=brier,
        )

    def _compute_calibration(
        self, observations: list[CaseObservation]
    ) -> list[CalibrationBucket]:
        """Compute empirical calibration across discrete probability bins."""
        pred_obs = [o for o in observations if o.recovery_probability is not None]
        buckets: list[CalibrationBucket] = []

        for b_min, b_max in CALIBRATION_INTERVALS:
            if b_max == 1.0:
                in_bucket = [
                    o
                    for o in pred_obs
                    if o.recovery_probability is not None
                    and b_min <= o.recovery_probability <= b_max
                ]
            else:
                in_bucket = [
                    o
                    for o in pred_obs
                    if o.recovery_probability is not None
                    and b_min <= o.recovery_probability < b_max
                ]

            n = len(in_bucket)
            if n == 0:
                buckets.append(
                    CalibrationBucket(
                        bucket_min=b_min,
                        bucket_max=b_max,
                        sample_size=0,
                        predicted_probability_avg=None,
                        actual_recovery_rate=None,
                        calibration_error=None,
                    )
                )
            else:
                pred_avg = round(
                    sum(o.recovery_probability or 0.0 for o in in_bucket) / n, 4
                )
                rec_rate = round(sum(1.0 for o in in_bucket if o.is_recovered) / n, 4)
                cal_err = round(abs(pred_avg - rec_rate), 4)
                buckets.append(
                    CalibrationBucket(
                        bucket_min=b_min,
                        bucket_max=b_max,
                        sample_size=n,
                        predicted_probability_avg=pred_avg,
                        actual_recovery_rate=rec_rate,
                        calibration_error=cal_err,
                    )
                )

        return buckets

    def _compute_action_attribution(
        self, observations: list[CaseObservation]
    ) -> list[ActionAttributionItem]:
        """Evaluate recovery rates associated with different proposed AI action types."""
        action_map: dict[str, list[CaseObservation]] = {
            act: [] for act in KNOWN_ACTION_TYPES
        }

        for obs in observations:
            if obs.proposed_action_type:
                action_map.setdefault(obs.proposed_action_type, []).append(obs)

        results: list[ActionAttributionItem] = []
        for act_type, items in action_map.items():
            n = len(items)
            recovered = sum(1 for o in items if o.is_recovered)
            failed = n - recovered
            rec_rate = round(recovered / n, 4) if n > 0 else None

            conf_items = [
                o.confidence_score for o in items if o.confidence_score is not None
            ]
            avg_conf = (
                round(sum(conf_items) / len(conf_items), 4) if conf_items else None
            )

            prob_items = [
                o.recovery_probability
                for o in items
                if o.recovery_probability is not None
            ]
            avg_prob = (
                round(sum(prob_items) / len(prob_items), 4) if prob_items else None
            )

            results.append(
                ActionAttributionItem(
                    action_type=act_type,
                    sample_size=n,
                    recovered_count=recovered,
                    failed_count=failed,
                    recovery_rate=rec_rate,
                    average_confidence=avg_conf,
                    average_recovery_probability=avg_prob,
                )
            )

        return results

    def _compute_confidence_outcomes(
        self, observations: list[CaseObservation]
    ) -> ConfidenceOutcomeMetrics:
        """Measure the relationship between AI confidence and actual recovery outcomes."""
        conf_obs = [o for o in observations if o.confidence_score is not None]
        n = len(conf_obs)

        if n == 0:
            return ConfidenceOutcomeMetrics(
                sample_size=0,
                average_confidence_recovered=None,
                average_confidence_failed=None,
                confidence_difference=None,
                correlation=None,
            )

        recovered_confs = [
            o.confidence_score
            for o in conf_obs
            if o.is_recovered and o.confidence_score is not None
        ]
        failed_confs = [
            o.confidence_score
            for o in conf_obs
            if not o.is_recovered and o.confidence_score is not None
        ]

        avg_rec = (
            round(sum(recovered_confs) / len(recovered_confs), 4)
            if recovered_confs
            else None
        )
        avg_fail = (
            round(sum(failed_confs) / len(failed_confs), 4) if failed_confs else None
        )

        conf_diff: float | None = None
        if avg_rec is not None and avg_fail is not None:
            conf_diff = round(avg_rec - avg_fail, 4)

        # Pearson Point-Biserial correlation between confidence and recovery outcome
        correlation: float | None = None
        if n >= 2 and len(recovered_confs) > 0 and len(failed_confs) > 0:
            try:
                confs = [o.confidence_score or 0.0 for o in conf_obs]
                ys = [1.0 if o.is_recovered else 0.0 for o in conf_obs]
                mean_c = sum(confs) / n
                mean_y = sum(ys) / n

                var_c = sum((c - mean_c) ** 2 for c in confs)
                var_y = sum((y - mean_y) ** 2 for y in ys)

                if var_c > 1e-12 and var_y > 1e-12:
                    cov = sum((confs[i] - mean_c) * (ys[i] - mean_y) for i in range(n))
                    r = cov / math.sqrt(var_c * var_y)
                    correlation = round(max(-1.0, min(1.0, r)), 4)
            except Exception as exc:
                logger.debug(
                    "correlation_calculation_skipped", extra={"error": str(exc)}
                )
                correlation = None

        return ConfidenceOutcomeMetrics(
            sample_size=n,
            average_confidence_recovered=avg_rec,
            average_confidence_failed=avg_fail,
            confidence_difference=conf_diff,
            correlation=correlation,
        )

    def _compute_policy_alignment(
        self, observations: list[CaseObservation]
    ) -> list[PolicyAlignmentItem]:
        """Aggregate recovery outcomes by deterministic Policy evaluation result."""
        pol_map: dict[str, list[CaseObservation]] = {
            pol: [] for pol in KNOWN_POLICY_OUTCOMES
        }

        for obs in observations:
            if obs.policy_outcome:
                pol_map.setdefault(obs.policy_outcome, []).append(obs)

        results: list[PolicyAlignmentItem] = []
        for outcome, items in pol_map.items():
            n = len(items)
            recovered = sum(1 for o in items if o.is_recovered)
            failed = n - recovered
            rec_rate = round(recovered / n, 4) if n > 0 else None

            results.append(
                PolicyAlignmentItem(
                    policy_outcome=outcome,
                    sample_size=n,
                    recovered_count=recovered,
                    failed_count=failed,
                    recovery_rate=rec_rate,
                )
            )

        return results

    def _compute_risk_segments(
        self, observations: list[CaseObservation]
    ) -> list[RiskSegmentItem]:
        """Segment recovery rates and predicted probabilities by CustomerRiskTier."""
        risk_map: dict[str, list[CaseObservation]] = {
            tier: [] for tier in KNOWN_RISK_TIERS
        }

        for obs in observations:
            risk_map.setdefault(obs.risk_tier, []).append(obs)

        results: list[RiskSegmentItem] = []
        for tier, items in risk_map.items():
            n = len(items)
            recovered = sum(1 for o in items if o.is_recovered)
            failed = n - recovered
            rec_rate = round(recovered / n, 4) if n > 0 else None

            probs = [
                o.recovery_probability
                for o in items
                if o.recovery_probability is not None
            ]
            avg_prob = round(sum(probs) / len(probs), 4) if probs else None

            results.append(
                RiskSegmentItem(
                    risk_tier=tier,
                    sample_size=n,
                    recovered_count=recovered,
                    failed_count=failed,
                    recovery_rate=rec_rate,
                    average_recovery_probability=avg_prob,
                )
            )

        return results

    def _compute_failure_reason_segments(
        self, observations: list[CaseObservation]
    ) -> list[FailureReasonSegmentItem]:
        """Segment recovery rates by initial transaction failure reason."""
        reason_map: dict[str, list[CaseObservation]] = {}

        for obs in observations:
            reason_map.setdefault(obs.failure_reason, []).append(obs)

        # Sort by sample size descending for operational usefulness
        sorted_reasons = sorted(
            reason_map.items(), key=lambda kv: len(kv[1]), reverse=True
        )

        results: list[FailureReasonSegmentItem] = []
        for reason, items in sorted_reasons:
            n = len(items)
            recovered = sum(1 for o in items if o.is_recovered)
            failed = n - recovered
            rec_rate = round(recovered / n, 4) if n > 0 else None

            probs = [
                o.recovery_probability
                for o in items
                if o.recovery_probability is not None
            ]
            avg_prob = round(sum(probs) / len(probs), 4) if probs else None

            results.append(
                FailureReasonSegmentItem(
                    failure_reason=reason,
                    sample_size=n,
                    recovered_count=recovered,
                    failed_count=failed,
                    recovery_rate=rec_rate,
                    average_recovery_probability=avg_prob,
                )
            )

        return results

    def _compute_recovery_durations(
        self, observations: list[CaseObservation]
    ) -> RecoveryDurationMetrics:
        """Calculate mean and median recovery latency (hours) for successfully recovered cases."""
        recovered_obs = [
            o for o in observations if o.is_recovered and o.duration_hours is not None
        ]
        total_rec = len(recovered_obs)

        if total_rec == 0:
            return RecoveryDurationMetrics(
                sample_size=0,
                overall_average_hours=None,
                overall_median_hours=None,
                by_action_type=[],
                by_priority=[],
            )

        durations = [
            o.duration_hours for o in recovered_obs if o.duration_hours is not None
        ]
        overall_avg = round(sum(durations) / len(durations), 2)
        overall_med = round(statistics.median(durations), 2)

        # By proposed action type
        by_action: list[ActionDurationItem] = []
        action_grouped: dict[str, list[float]] = {}
        for o in recovered_obs:
            act = o.proposed_action_type or "UNASSIGNED"
            if o.duration_hours is not None:
                action_grouped.setdefault(act, []).append(o.duration_hours)

        for act_type, d_list in action_grouped.items():
            by_action.append(
                ActionDurationItem(
                    action_type=act_type,
                    sample_size=len(d_list),
                    average_hours=round(sum(d_list) / len(d_list), 2),
                    median_hours=round(statistics.median(d_list), 2),
                )
            )

        # By prediction priority
        by_priority: list[PriorityDurationItem] = []
        priority_grouped: dict[str, list[float]] = {}
        for o in recovered_obs:
            prio = o.priority or "UNASSIGNED"
            if o.duration_hours is not None:
                priority_grouped.setdefault(prio, []).append(o.duration_hours)

        for prio, d_list in priority_grouped.items():
            by_priority.append(
                PriorityDurationItem(
                    priority=prio,
                    sample_size=len(d_list),
                    average_hours=round(sum(d_list) / len(d_list), 2),
                    median_hours=round(statistics.median(d_list), 2),
                )
            )

        return RecoveryDurationMetrics(
            sample_size=total_rec,
            overall_average_hours=overall_avg,
            overall_median_hours=overall_med,
            by_action_type=by_action,
            by_priority=by_priority,
        )

    def evaluate(self, db: Session) -> IntelligenceEvaluationResponse:
        """
        Execute comprehensive, read-only recovery intelligence evaluation.
        Zero database mutations. Zero external calls.
        """
        now_utc = datetime.now(UTC)
        observations = self._load_resolved_observations(db)

        # Model metadata
        model_name = "recovery_probability"
        model_version = "v1.0"
        for o in observations:
            if o.has_prediction:
                model_name = o.model_name
                model_version = o.model_version
                break

        classification = self._compute_classification_and_brier(observations)
        calibration = self._compute_calibration(observations)
        action_attribution = self._compute_action_attribution(observations)
        confidence_outcomes = self._compute_confidence_outcomes(observations)
        policy_alignment = self._compute_policy_alignment(observations)
        risk_segments = self._compute_risk_segments(observations)
        failure_reason_segments = self._compute_failure_reason_segments(observations)
        recovery_durations = self._compute_recovery_durations(observations)

        logger.info(
            "intelligence_evaluation_computed",
            extra={
                "total_resolved_cases": len(observations),
                "classification_sample_size": classification.sample_size,
                "brier_score": classification.brier_score,
            },
        )

        return IntelligenceEvaluationResponse(
            generated_at=now_utc,
            model=ModelMetadata(
                model_name=model_name,
                model_version=model_version,
            ),
            classification=classification,
            calibration=calibration,
            action_attribution=action_attribution,
            confidence_outcomes=confidence_outcomes,
            policy_alignment=policy_alignment,
            risk_segments=risk_segments,
            failure_reason_segments=failure_reason_segments,
            recovery_duration=recovery_durations,
        )


intelligence_evaluation_service = IntelligenceEvaluationService()
