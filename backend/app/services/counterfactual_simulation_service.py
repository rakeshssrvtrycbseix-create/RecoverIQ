import logging
from datetime import UTC, datetime
from typing import Any

from sqlalchemy.orm import Session, joinedload, selectinload

from app.models import (
    CustomerRiskTier,
    RecoveryActionType,
    RecoveryCase,
    RecoveryCaseStatus,
)
from app.schemas.simulation import (
    ComparablePopulationMetadata,
    CounterfactualSimulationResponse,
    EstimatedStrategyUplift,
    SimulationDiagnostic,
    SimulationRequest,
    StrategyMetrics,
)

logger = logging.getLogger(__name__)

MIN_SIMULATION_SAMPLE_SIZE = 30
LIMITED_SAMPLE_SIZE = 10

RESOLVED_CASE_STATUSES = {
    RecoveryCaseStatus.RECOVERED.value,
    RecoveryCaseStatus.CLOSED.value,
    RecoveryCaseStatus.EXHAUSTED.value,
}


class SimCaseRecord:
    """In-memory projection of a resolved recovery case for simulation analysis."""

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

        # Amount band
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


class CounterfactualSimulationService:
    """
    Read-only Counterfactual Recovery Simulation Service.
    Compares historical baseline strategy against alternative counterfactual strategies
    using empirical comparable populations. Zero database mutations. Zero external calls.
    """

    def _load_resolved_records(self, db: Session) -> list[SimCaseRecord]:
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
        return [SimCaseRecord(c) for c in cases]

    def _get_reliability(self, sample_size: int) -> str:
        """Classify sample size reliability."""
        if sample_size >= MIN_SIMULATION_SAMPLE_SIZE:
            return "SUFFICIENT"
        elif sample_size >= LIMITED_SAMPLE_SIZE:
            return "LIMITED"
        return "INSUFFICIENT_DATA"

    def _filter_comparable_population(
        self,
        records: list[SimCaseRecord],
        req: SimulationRequest,
    ) -> tuple[list[SimCaseRecord], str, list[SimulationDiagnostic]]:
        """
        Progressively filter comparable populations:
        Level 1: EXACT_MATCH on all provided segment filters.
        Level 2: RELAXED_MATCH on primary filters (risk_tier, failure_reason).
        Level 3: GLOBAL_BASELINE if specific segments lack adequate data.
        """
        diagnostics: list[SimulationDiagnostic] = []

        if not records:
            return [], "GLOBAL_BASELINE", diagnostics

        # 1. Try Exact Match
        exact = records
        if req.risk_tier:
            exact = [r for r in exact if r.risk_tier.upper() == req.risk_tier.upper()]
        if req.failure_reason:
            exact = [
                r
                for r in exact
                if r.failure_reason.lower() == req.failure_reason.lower()
            ]
        if req.attempt_number:
            exact = [r for r in exact if r.attempt_number == req.attempt_number]
        if req.amount_band:
            exact = [r for r in exact if r.amount_band == req.amount_band]

        if len(exact) >= LIMITED_SAMPLE_SIZE or (
            not req.risk_tier
            and not req.failure_reason
            and not req.attempt_number
            and not req.amount_band
        ):
            return exact, "EXACT_MATCH", diagnostics

        # 2. Try Relaxed Match (Primary: risk_tier, failure_reason)
        relaxed = records
        if req.risk_tier:
            relaxed = [
                r for r in relaxed if r.risk_tier.upper() == req.risk_tier.upper()
            ]
        if req.failure_reason:
            relaxed = [
                r
                for r in relaxed
                if r.failure_reason.lower() == req.failure_reason.lower()
            ]

        if len(relaxed) >= LIMITED_SAMPLE_SIZE:
            diagnostics.append(
                SimulationDiagnostic(
                    code="FALLBACK_SEGMENTATION",
                    severity="INFO",
                    message=f"Exact segment match contained only {len(exact)} cases. Relaxed segmentation on Risk Tier and Failure Reason was applied ({len(relaxed)} comparable cases).",
                )
            )
            return relaxed, "RELAXED_MATCH", diagnostics

        # 3. Global Baseline Fallback
        diagnostics.append(
            SimulationDiagnostic(
                code="GLOBAL_BASELINE_FALLBACK",
                severity="WARNING",
                message=f"Filtered segment contained insufficient observations ({len(exact)} cases). Global historical baseline ({len(records)} cases) was utilized.",
            )
        )
        return records, "GLOBAL_BASELINE", diagnostics

    def _compute_strategy_metrics(
        self,
        population: list[SimCaseRecord],
        action_type: str,
        delay_hours: int,
        hypothetical_principal: int | None,
    ) -> StrategyMetrics:
        """Calculate historical recovery rate, yield, probability, and ERV for a strategy."""
        # Match cases with same action type in the population
        matching = [r for r in population if r.action_type == action_type]
        n = len(matching)

        if n == 0:
            return StrategyMetrics(
                action_type=action_type,
                delay_hours=delay_hours,
                sample_size=0,
                recovered_count=0,
                failed_count=0,
                recovery_rate=None,
                financial_yield=None,
                average_recovery_probability=None,
                amount_at_risk_paise=hypothetical_principal or 0,
                amount_recovered_paise=0,
                expected_recovery_value_paise=None,
                reliability="INSUFFICIENT_DATA",
            )

        recovered = sum(1 for r in matching if r.is_recovered)
        failed = n - recovered
        rec_rate = round(recovered / n, 4)

        tot_risk = sum(r.amount_at_risk for r in matching)
        tot_recovered = sum(r.recovered_amount for r in matching)
        fin_yield = round(tot_recovered / tot_risk, 4) if tot_risk > 0 else None

        probs = [r.probability for r in matching if r.probability is not None]
        avg_prob = round(sum(probs) / len(probs), 4) if probs else rec_rate

        principal = (
            hypothetical_principal if hypothetical_principal is not None else tot_risk
        )
        erv = int(round(principal * avg_prob))

        reliability = self._get_reliability(n)

        return StrategyMetrics(
            action_type=action_type,
            delay_hours=delay_hours,
            sample_size=n,
            recovered_count=recovered,
            failed_count=failed,
            recovery_rate=rec_rate,
            financial_yield=fin_yield,
            average_recovery_probability=avg_prob,
            amount_at_risk_paise=principal,
            amount_recovered_paise=tot_recovered,
            expected_recovery_value_paise=erv,
            reliability=reliability,
        )

    def _compute_uplift(
        self,
        current: StrategyMetrics,
        alternative: StrategyMetrics,
    ) -> EstimatedStrategyUplift:
        """Calculate differential recovery rate, relative uplift percentage, and incremental ERV."""
        if current.sample_size == 0 or alternative.sample_size == 0:
            return EstimatedStrategyUplift(
                recovery_rate_delta=None,
                relative_uplift_pct=None,
                financial_yield_delta=None,
                estimated_incremental_erv_paise=None,
                confidence_assessment="INSUFFICIENT_DATA",
            )

        rr_delta = (
            round(alternative.recovery_rate - current.recovery_rate, 4)
            if (
                alternative.recovery_rate is not None
                and current.recovery_rate is not None
            )
            else None
        )

        rel_uplift = None
        if (
            current.recovery_rate is not None
            and current.recovery_rate > 0.0
            and alternative.recovery_rate is not None
        ):
            rel_uplift = round(
                (
                    (alternative.recovery_rate - current.recovery_rate)
                    / current.recovery_rate
                )
                * 100.0,
                2,
            )

        fy_delta = (
            round(alternative.financial_yield - current.financial_yield, 4)
            if (
                alternative.financial_yield is not None
                and current.financial_yield is not None
            )
            else None
        )

        erv_delta = (
            alternative.expected_recovery_value_paise
            - current.expected_recovery_value_paise
            if (
                alternative.expected_recovery_value_paise is not None
                and current.expected_recovery_value_paise is not None
            )
            else None
        )

        # Confidence Assessment
        if (
            current.reliability == "INSUFFICIENT_DATA"
            or alternative.reliability == "INSUFFICIENT_DATA"
        ):
            assessment = "INSUFFICIENT_DATA"
        elif rr_delta is not None and rr_delta >= 0.10:
            assessment = "STRONG_POSITIVE_EVIDENCE"
        elif rr_delta is not None and rr_delta >= 0.03:
            assessment = "MODERATE_EVIDENCE"
        elif rr_delta is not None and rr_delta <= -0.03:
            assessment = "NEGATIVE_OUTCOME_INDICATED"
        else:
            assessment = "COMPARABLE_PERFORMANCE"

        return EstimatedStrategyUplift(
            recovery_rate_delta=rr_delta,
            relative_uplift_pct=rel_uplift,
            financial_yield_delta=fy_delta,
            estimated_incremental_erv_paise=erv_delta,
            confidence_assessment=assessment,
        )

    def simulate(
        self,
        db: Session,
        req: SimulationRequest,
    ) -> CounterfactualSimulationResponse:
        """
        Execute observational counterfactual recovery strategy simulation.
        Zero database writes. Zero financial actions dispatched.
        """
        now_utc = datetime.now(UTC)
        all_records = self._load_resolved_records(db)

        # Filter comparable population
        pop_records, seg_level, diagnostics = self._filter_comparable_population(
            all_records, req
        )

        filter_parts = []
        matching_dict: dict[str, Any] = {}
        if req.risk_tier:
            filter_parts.append(f"Risk Tier: {req.risk_tier}")
            matching_dict["risk_tier"] = req.risk_tier
        if req.failure_reason:
            filter_parts.append(f"Failure Reason: {req.failure_reason}")
            matching_dict["failure_reason"] = req.failure_reason
        if req.attempt_number:
            filter_parts.append(f"Attempt: {req.attempt_number}")
            matching_dict["attempt_number"] = req.attempt_number
        if req.amount_band:
            filter_parts.append(f"Amount Band: {req.amount_band}")
            matching_dict["amount_band"] = req.amount_band

        filter_summary = (
            ", ".join(filter_parts) if filter_parts else "All Historical Cases"
        )

        population_meta = ComparablePopulationMetadata(
            total_cases_analyzed=len(pop_records),
            matching_criteria=matching_dict,
            segmentation_level_used=seg_level,
            filter_summary=filter_summary,
        )

        current_metrics = self._compute_strategy_metrics(
            pop_records,
            req.current_action_type,
            req.current_delay_hours,
            req.amount_at_risk_paise,
        )

        alternative_metrics = self._compute_strategy_metrics(
            pop_records,
            req.alternative_action_type,
            req.alternative_delay_hours,
            req.amount_at_risk_paise,
        )

        uplift = self._compute_uplift(current_metrics, alternative_metrics)

        # Generate Diagnostics
        if current_metrics.reliability == "INSUFFICIENT_DATA":
            diagnostics.append(
                SimulationDiagnostic(
                    code="CURRENT_STRATEGY_LOW_SAMPLE",
                    severity="WARNING",
                    message=f"Current strategy '{req.current_action_type}' has only {current_metrics.sample_size} historical observations in the comparable population.",
                )
            )
        if alternative_metrics.reliability == "INSUFFICIENT_DATA":
            diagnostics.append(
                SimulationDiagnostic(
                    code="ALTERNATIVE_STRATEGY_LOW_SAMPLE",
                    severity="WARNING",
                    message=f"Alternative strategy '{req.alternative_action_type}' has only {alternative_metrics.sample_size} historical observations in the comparable population.",
                )
            )
        if uplift.confidence_assessment == "STRONG_POSITIVE_EVIDENCE":
            diagnostics.append(
                SimulationDiagnostic(
                    code="STRONG_UPLIFT_OBSERVED",
                    severity="POSITIVE",
                    message=f"Alternative strategy '{req.alternative_action_type}' demonstrates strong positive historical uplift (Δ={uplift.recovery_rate_delta:+.1%}).",
                )
            )

        logger.info(
            "counterfactual_simulation_executed",
            extra={
                "current_action": req.current_action_type,
                "alternative_action": req.alternative_action_type,
                "population_size": len(pop_records),
                "assessment": uplift.confidence_assessment,
            },
        )

        return CounterfactualSimulationResponse(
            generated_at=now_utc,
            request_parameters=req,
            population=population_meta,
            current_strategy=current_metrics,
            alternative_strategy=alternative_metrics,
            estimated_uplift=uplift,
            diagnostics=diagnostics,
        )


counterfactual_simulation_service = CounterfactualSimulationService()
