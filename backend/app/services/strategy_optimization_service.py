import logging
from datetime import UTC, datetime

from sqlalchemy.orm import Session, joinedload, selectinload

from app.models import (
    CustomerRiskTier,
    RecoveryActionType,
    RecoveryCase,
    RecoveryCaseStatus,
)
from app.schemas.optimization import (
    DelayPerformance,
    ExpectedRecoveryValue,
    OptimizationFinding,
    OptimizationRecommendation,
    SegmentStrategyRecommendation,
    StrategyOptimizationResponse,
    StrategyPerformance,
)

logger = logging.getLogger(__name__)

MIN_OPTIMIZATION_SAMPLE_SIZE = 30
LIMITED_SAMPLE_SIZE = 10

RESOLVED_CASE_STATUSES = {
    RecoveryCaseStatus.RECOVERED.value,
    RecoveryCaseStatus.CLOSED.value,
    RecoveryCaseStatus.EXHAUSTED.value,
}

KNOWN_ACTION_TYPES = [
    RecoveryActionType.RETRY_PAYMENT.value,
    RecoveryActionType.SEND_PAYMENT_LINK.value,
    RecoveryActionType.SEND_NOTIFICATION.value,
    RecoveryActionType.ESCALATE_HUMAN.value,
    RecoveryActionType.HALT_SUBSCRIPTION.value,
    RecoveryActionType.CLOSE_CASE.value,
]

STANDARD_DELAYS = [2, 4, 12, 24]


class CaseOptimizationRecord:
    """In-memory projection of a resolved recovery case for empirical strategy analysis."""

    def __init__(self, case: RecoveryCase) -> None:
        self.case_id = case.id
        self.is_recovered = case.status == RecoveryCaseStatus.RECOVERED.value or (
            case.recovered_amount > 0 and case.status in RESOLVED_CASE_STATUSES
        )
        self.amount_at_risk = case.amount_at_risk
        self.recovered_amount = case.recovered_amount if self.is_recovered else 0
        self.risk_tier = (
            case.customer.risk_tier
            if case.customer
            else CustomerRiskTier.STANDARD.value
        )
        self.failure_reason = case.latest_failure_reason or "unknown"
        self.attempt_number = max(1, case.total_attempts_count or 1)

        # Monetary Amount Band
        if self.amount_at_risk < 100000:
            self.amount_band = "< ₹1,000"
        elif self.amount_at_risk < 500000:
            self.amount_band = "₹1,000–₹5,000"
        elif self.amount_at_risk < 1000000:
            self.amount_band = "₹5,000–₹10,000"
        elif self.amount_at_risk < 5000000:
            self.amount_band = "₹10,000–₹50,000"
        else:
            self.amount_band = "> ₹50,000"

        # Intelligence Trail
        latest_pred = case.predictions[-1] if case.predictions else None
        self.probability = (
            float(latest_pred.recovery_probability) if latest_pred else None
        )
        self.delay_hours = (
            latest_pred.predicted_delay_hours
            if latest_pred and latest_pred.predicted_delay_hours is not None
            else 4
        )

        latest_dec = case.agent_decisions[-1] if case.agent_decisions else None
        self.action_type = (
            latest_dec.proposed_action_type
            if latest_dec and latest_dec.proposed_action_type
            else (
                case.actions[-1].action_type
                if case.actions
                else RecoveryActionType.RETRY_PAYMENT.value
            )
        )
        self.confidence_score = (
            float(latest_dec.confidence_score) if latest_dec else None
        )


class StrategyOptimizationService:
    """
    Read-only Strategy Optimization Engine.
    Analyzes historical recovery performance across action types, delay cadences,
    customer risk tiers, and failure segments to recommend optimal recovery paths.
    """

    def _load_resolved_records(self, db: Session) -> list[CaseOptimizationRecord]:
        """Fetch and project resolved recovery cases."""
        cases = (
            db.query(RecoveryCase)
            .options(
                joinedload(RecoveryCase.customer),
                selectinload(RecoveryCase.predictions),
                selectinload(RecoveryCase.agent_decisions),
                selectinload(RecoveryCase.actions),
            )
            .filter(RecoveryCase.status.in_(RESOLVED_CASE_STATUSES))
            .order_by(RecoveryCase.created_at.asc())
            .all()
        )
        return [CaseOptimizationRecord(c) for c in cases]

    def _get_reliability(self, sample_size: int) -> str:
        """Categorize statistical confidence level based on observation count."""
        if sample_size >= MIN_OPTIMIZATION_SAMPLE_SIZE:
            return "SUFFICIENT"
        elif sample_size >= LIMITED_SAMPLE_SIZE:
            return "LIMITED"
        return "INSUFFICIENT_DATA"

    def _compute_strategies_performance(
        self, records: list[CaseOptimizationRecord]
    ) -> list[StrategyPerformance]:
        """Measure recovery rate, financial yield, and model confidence per action type."""
        groups: dict[str, list[CaseOptimizationRecord]] = {
            act: [] for act in KNOWN_ACTION_TYPES
        }

        for r in records:
            groups.setdefault(r.action_type, []).append(r)

        results: list[StrategyPerformance] = []
        for act_type, items in groups.items():
            n = len(items)
            recovered = sum(1 for r in items if r.is_recovered)
            failed = n - recovered
            rec_rate = round(recovered / n, 4) if n > 0 else None

            tot_risk = sum(r.amount_at_risk for r in items)
            tot_recovered = sum(r.recovered_amount for r in items)
            amount_rate = round(tot_recovered / tot_risk, 4) if tot_risk > 0 else None

            probs = [r.probability for r in items if r.probability is not None]
            avg_prob = round(sum(probs) / len(probs), 4) if probs else None

            confs = [
                r.confidence_score for r in items if r.confidence_score is not None
            ]
            avg_conf = round(sum(confs) / len(confs), 4) if confs else None

            results.append(
                StrategyPerformance(
                    action_type=act_type,
                    sample_size=n,
                    recovered_count=recovered,
                    failed_count=failed,
                    recovery_rate=rec_rate,
                    average_recovery_probability=avg_prob,
                    average_confidence=avg_conf,
                    amount_at_risk=tot_risk,
                    amount_recovered=tot_recovered,
                    recovery_amount_rate=amount_rate,
                    reliability=self._get_reliability(n),
                )
            )

        return results

    def _compute_delay_performance(
        self, records: list[CaseOptimizationRecord]
    ) -> list[DelayPerformance]:
        """Measure empirical recovery effectiveness across retry cadence delay intervals."""
        delay_map: dict[int, list[CaseOptimizationRecord]] = {
            d: [] for d in STANDARD_DELAYS
        }

        for r in records:
            delay_map.setdefault(r.delay_hours, []).append(r)

        results: list[DelayPerformance] = []
        for delay_hrs in sorted(delay_map.keys()):
            items = delay_map[delay_hrs]
            n = len(items)
            recovered = sum(1 for r in items if r.is_recovered)
            rec_rate = round(recovered / n, 4) if n > 0 else None

            probs = [r.probability for r in items if r.probability is not None]
            avg_prob = round(sum(probs) / len(probs), 4) if probs else None

            tot_risk = sum(r.amount_at_risk for r in items)
            tot_recovered = sum(r.recovered_amount for r in items)

            results.append(
                DelayPerformance(
                    delay_hours=delay_hrs,
                    sample_size=n,
                    recovered_count=recovered,
                    recovery_rate=rec_rate,
                    average_recovery_probability=avg_prob,
                    amount_at_risk=tot_risk,
                    amount_recovered=tot_recovered,
                    reliability=self._get_reliability(n),
                )
            )

        return results

    def _select_champion_strategy(
        self,
        strategies: list[StrategyPerformance],
        delays: list[DelayPerformance],
        total_risk: int,
    ) -> OptimizationRecommendation:
        """
        Deterministic champion strategy selection.
        Ranking hierarchy:
        1. Sample reliability: SUFFICIENT (3) > LIMITED (2) > INSUFFICIENT_DATA (1)
        2. Recovery rate (descending)
        3. Financial recovery amount rate (descending)
        4. Expected Recovery Value in paise (descending)
        5. Average confidence score (descending)
        6. Action type alphabetically
        """
        populated = [s for s in strategies if s.sample_size > 0]
        if not populated:
            return OptimizationRecommendation(
                action_type=None,
                recommended_delay_hours=4,
                sample_size=0,
                recovery_probability=None,
                recovery_rate=None,
                average_confidence=None,
                expected_recovery_value=0,
                confidence_level="INSUFFICIENT_DATA",
                recommendation_reason="No resolved historical recovery cases available for optimization analysis.",
            )

        def score_strategy(
            s: StrategyPerformance,
        ) -> tuple[int, float, float, int, float, str]:
            rel_rank = (
                3
                if s.reliability == "SUFFICIENT"
                else (2 if s.reliability == "LIMITED" else 1)
            )
            rec_r = s.recovery_rate or 0.0
            amt_r = s.recovery_amount_rate or 0.0
            p_val = s.average_recovery_probability or rec_r
            erv = int(round(total_risk * p_val))
            conf = s.average_confidence or 0.0
            return (rel_rank, rec_r, amt_r, erv, conf, s.action_type)

        champion = max(populated, key=score_strategy)

        # Best delay
        populated_delays = [d for d in delays if d.sample_size > 0]
        best_delay = (
            max(
                populated_delays, key=lambda d: (d.recovery_rate or 0.0, d.sample_size)
            ).delay_hours
            if populated_delays
            else 4
        )

        p_eff = champion.average_recovery_probability or (champion.recovery_rate or 0.0)
        erv_champion = int(round(total_risk * p_eff))

        if champion.reliability == "SUFFICIENT":
            reason = f"{champion.action_type} demonstrates the strongest observed recovery rate ({champion.recovery_rate:.1%}) and financial yield across {champion.sample_size} cases."
        elif champion.reliability == "LIMITED":
            reason = f"{champion.action_type} is the top emerging strategy ({champion.recovery_rate:.1%}), but sample size ({champion.sample_size}) remains below the 30-case statistical significance threshold."
        else:
            reason = f"Preliminary observation suggests {champion.action_type}; however, sample size ({champion.sample_size}) is insufficient for confident operational deployment."

        return OptimizationRecommendation(
            action_type=champion.action_type,
            recommended_delay_hours=best_delay,
            sample_size=champion.sample_size,
            recovery_probability=champion.average_recovery_probability,
            recovery_rate=champion.recovery_rate,
            average_confidence=champion.average_confidence,
            expected_recovery_value=erv_champion,
            confidence_level=champion.reliability,
            recommendation_reason=reason,
        )

    def _compute_segment_recommendations(
        self, records: list[CaseOptimizationRecord]
    ) -> list[SegmentStrategyRecommendation]:
        """Segment-level champion strategy and delay recommendations."""
        segments_def = [
            ("risk_tier", lambda r: r.risk_tier),
            ("failure_reason", lambda r: r.failure_reason),
            (
                "attempt_number",
                lambda r: (
                    f"Attempt {min(r.attempt_number, 4)}{'+' if r.attempt_number >= 4 else ''}"
                ),
            ),
            ("amount_band", lambda r: r.amount_band),
        ]

        recommendations: list[SegmentStrategyRecommendation] = []

        for seg_type, getter in segments_def:
            grouped: dict[str, list[CaseOptimizationRecord]] = {}
            for r in records:
                val = getter(r)
                if val:
                    grouped.setdefault(val, []).append(r)

            for seg_val, items in grouped.items():
                n_seg = len(items)
                tot_risk = sum(r.amount_at_risk for r in items)

                # Group by action in this segment
                action_counts: dict[str, list[CaseOptimizationRecord]] = {}
                for r in items:
                    action_counts.setdefault(r.action_type, []).append(r)

                best_act: str | None = None
                best_rec_rate: float | None = None

                if action_counts:
                    best_act_items = max(
                        action_counts.items(),
                        key=lambda kv: (
                            sum(1 for x in kv[1] if x.is_recovered) / len(kv[1]),
                            len(kv[1]),
                        ),
                    )
                    best_act = best_act_items[0]
                    rec_count = sum(1 for x in best_act_items[1] if x.is_recovered)
                    best_rec_rate = round(rec_count / len(best_act_items[1]), 4)

                # Best delay in this segment
                delay_counts: dict[int, list[CaseOptimizationRecord]] = {}
                for r in items:
                    delay_counts.setdefault(r.delay_hours, []).append(r)

                best_delay: int = 4
                if delay_counts:
                    best_delay = max(
                        delay_counts.items(),
                        key=lambda kv: (
                            sum(1 for x in kv[1] if x.is_recovered) / len(kv[1]),
                            len(kv[1]),
                        ),
                    )[0]

                # ERV calculation
                probs = [r.probability for r in items if r.probability is not None]
                p_seg = (sum(probs) / len(probs)) if probs else (best_rec_rate or 0.0)
                erv_seg = int(round(tot_risk * p_seg))

                reliability = self._get_reliability(n_seg)
                if reliability == "SUFFICIENT":
                    reason = f"Reliable empirical signal: {best_act} achieved {best_rec_rate:.1%} recovery rate across {n_seg} cases in segment '{seg_val}'."
                elif reliability == "LIMITED":
                    reason = f"Emerging signal for {best_act} ({best_rec_rate:.1%}), sample size {n_seg} in segment '{seg_val}'."
                else:
                    reason = (
                        f"Limited observation ({n_seg} cases) for segment '{seg_val}'."
                    )

                recommendations.append(
                    SegmentStrategyRecommendation(
                        segment_type=seg_type,
                        segment_value=seg_val,
                        sample_size=n_seg,
                        best_action_type=best_act,
                        best_delay_hours=best_delay,
                        recovery_rate=best_rec_rate,
                        amount_at_risk=tot_risk,
                        expected_recovery_value=erv_seg,
                        reliability=reliability,
                        recommendation_reason=reason,
                    )
                )

        return recommendations

    def _generate_findings(
        self,
        champion: OptimizationRecommendation,
        strategies: list[StrategyPerformance],
        delays: list[DelayPerformance],
        segments: list[SegmentStrategyRecommendation],
        total_sample: int,
    ) -> list[OptimizationFinding]:
        """Generate deterministic analytical optimization findings."""
        findings: list[OptimizationFinding] = []

        if total_sample < MIN_OPTIMIZATION_SAMPLE_SIZE:
            findings.append(
                OptimizationFinding(
                    code="INSUFFICIENT_DATA",
                    severity="INFO",
                    message=f"Total historical sample size ({total_sample}) is below the statistical threshold ({MIN_OPTIMIZATION_SAMPLE_SIZE}). All strategy rankings are tentative.",
                )
            )
        elif champion.action_type:
            findings.append(
                OptimizationFinding(
                    code="STRATEGY_PERFORMING_WELL",
                    severity="POSITIVE",
                    message=f"{champion.action_type} is the top champion strategy with an observed recovery rate of {champion.recovery_rate:.1%} across {champion.sample_size} cases.",
                )
            )

        # Delay effect finding
        valid_delays = [
            d
            for d in delays
            if d.sample_size >= LIMITED_SAMPLE_SIZE and d.recovery_rate is not None
        ]
        if len(valid_delays) >= 2:
            best_d = max(valid_delays, key=lambda d: d.recovery_rate or 0.0)
            worst_d = min(valid_delays, key=lambda d: d.recovery_rate or 0.0)
            if (best_d.recovery_rate or 0.0) - (worst_d.recovery_rate or 0.0) >= 0.10:
                findings.append(
                    OptimizationFinding(
                        code="DELAY_EFFECT_DETECTED",
                        severity="POSITIVE",
                        message=f"{best_d.delay_hours}-hour delay shows stronger empirical recovery ({best_d.recovery_rate:.1%}) than {worst_d.delay_hours}-hour delay ({worst_d.recovery_rate:.1%}).",
                    )
                )

        # High value opportunity segment
        high_val_segs = [
            s
            for s in segments
            if s.expected_recovery_value > 10000000
            and s.sample_size >= LIMITED_SAMPLE_SIZE
        ]
        if high_val_segs:
            top_seg = max(high_val_segs, key=lambda s: s.expected_recovery_value)
            findings.append(
                OptimizationFinding(
                    code="HIGH_VALUE_OPPORTUNITY",
                    severity="INFO",
                    message=f"High recovery potential in segment '{top_seg.segment_value}' ({top_seg.segment_type}) with expected recovery value ₹{top_seg.expected_recovery_value / 100:,.2f}.",
                )
            )

        return findings

    def optimize(self, db: Session) -> StrategyOptimizationResponse:
        """
        Execute read-only strategy optimization, delay cadence analysis, and ERV modeling.
        Zero database writes, zero external calls.
        """
        now_utc = datetime.now(UTC)
        records = self._load_resolved_records(db)
        total_sample = len(records)

        total_risk = sum(r.amount_at_risk for r in records)
        probs = [r.probability for r in records if r.probability is not None]
        overall_avg_prob = (
            (sum(probs) / len(probs))
            if probs
            else (
                sum(1 for r in records if r.is_recovered) / total_sample
                if total_sample > 0
                else 0.0
            )
        )
        total_erv = int(round(total_risk * overall_avg_prob))

        erv_summary = ExpectedRecoveryValue(
            amount_at_risk=total_risk,
            recovery_probability=round(overall_avg_prob, 4),
            expected_recovery_value=total_erv,
        )

        strategies = self._compute_strategies_performance(records)
        delays = self._compute_delay_performance(records)
        champion = self._select_champion_strategy(strategies, delays, total_risk)
        segment_recommendations = self._compute_segment_recommendations(records)
        findings = self._generate_findings(
            champion, strategies, delays, segment_recommendations, total_sample
        )

        logger.info(
            "strategy_optimization_computed",
            extra={
                "sample_size": total_sample,
                "champion_action": champion.action_type,
                "total_erv": total_erv,
            },
        )

        return StrategyOptimizationResponse(
            generated_at=now_utc,
            sample_size=total_sample,
            overall_recommendation=champion,
            expected_recovery_value_summary=erv_summary,
            strategies=strategies,
            delay_analysis=delays,
            segment_recommendations=segment_recommendations,
            diagnostic_findings=findings,
        )


strategy_optimization_service = StrategyOptimizationService()
