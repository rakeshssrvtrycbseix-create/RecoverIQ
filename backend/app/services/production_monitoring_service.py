import logging
from datetime import UTC, datetime

from sqlalchemy.orm import Session

from app.models import (
    ProductionStrategyStatus,
    RolloutHealthStatus,
)
from app.schemas.activation import StrategyActivationResponse
from app.schemas.production import ProductionMonitoringResponse
from app.services.model_governance_service import (
    model_governance_service,
)
from app.services.strategy_activation_service import (
    strategy_activation_service,
)

logger = logging.getLogger(__name__)


class ProductionMonitoringService:
    """
    Continuous Production Strategy Monitoring Service.
    Tracks real-time performance, model health, prediction drift, and automated
    safety guardrails for production-promoted recovery strategies.

    Guarantees:
    - Strictly observational telemetry.
    - Zero autonomous money movement or RecoveryAction creation.
    - Multi-factor automated guardrails generating ROLLBACK_RECOMMENDED on regressions.
    - Safe cold-start and zero-division handling.
    """

    def monitor_production(
        self,
        db: Session,
        as_of: datetime | None = None,
    ) -> ProductionMonitoringResponse:
        """
        Gathers live continuous monitoring telemetry for the active production strategy.
        Read-only. Zero financial execution.
        """
        now_utc = as_of or datetime.now(UTC)
        if now_utc.tzinfo is None:
            now_utc = now_utc.replace(tzinfo=UTC)

        # 1. Fetch active activations list
        act_list = strategy_activation_service.list_activations(db=db, as_of=now_utc)
        active_act: StrategyActivationResponse | None = act_list.active_activation

        if not active_act:
            return ProductionMonitoringResponse(
                status=ProductionStrategyStatus.NO_ACTIVE_STRATEGY.value,
                strategy_id=None,
                strategy_name=None,
                strategy_version=None,
                model_version=None,
                activation_id=None,
                recommendation_id=None,
                rollout_percentage=0,
                sample_size=0,
                treatment_sample_size=0,
                control_sample_size=0,
                recovery_rate=None,
                control_recovery_rate=None,
                absolute_uplift=None,
                relative_uplift_pct=None,
                incremental_erv_paise=None,
                financial_yield=None,
                mttr_hours=None,
                model_health="UNKNOWN",
                prediction_psi=None,
                drift_status="UNKNOWN",
                rollback_recommended=False,
                diagnostics=[
                    "No active production recovery strategy currently deployed."
                ],
                promoted_at=None,
                promoted_by=None,
                last_evaluated=now_utc,
            )

        # 2. Query Phase 9B model governance
        gov_rep = model_governance_service.evaluate_governance(db=db)

        # 3. Extract metrics & comparison
        comp = active_act.comparison
        control_m = comp.control_metrics if comp else None
        treatment_m = comp.treatment_metrics if comp else None
        uplift = comp.uplift if comp else None

        t_sample = treatment_m.sample_size if treatment_m else 0
        c_sample = control_m.sample_size if control_m else 0
        total_sample = t_sample + c_sample

        rec_rate = treatment_m.recovery_rate if treatment_m else None
        c_rec_rate = control_m.recovery_rate if control_m else None
        abs_uplift = uplift.absolute_uplift if uplift else None
        rel_uplift = uplift.relative_uplift_pct if uplift else None
        inc_erv = uplift.incremental_expected_recovery_value_paise if uplift else None
        yield_ratio = treatment_m.financial_yield if treatment_m else None
        mttr = treatment_m.mean_time_to_recovery_hours if treatment_m else None

        # 4. Automated Safety Guardrails Evaluation
        diagnostics: list[str] = []
        overall_status = ProductionStrategyStatus.HEALTHY.value
        rollback_rec = False

        # Guardrail A: Severe Negative Uplift
        if t_sample >= 30 and rec_rate is not None and c_rec_rate is not None:
            if rec_rate <= c_rec_rate - 0.05:
                overall_status = ProductionStrategyStatus.ROLLBACK_RECOMMENDED.value
                rollback_rec = True
                diagnostics.append(
                    f"CRITICAL: Treatment recovery rate ({rec_rate:.1%}) has deteriorated by "
                    f">= 5.0 percentage points below control ({c_rec_rate:.1%}). Rollback recommended."
                )
            elif rec_rate < c_rec_rate - 0.02:
                if (
                    overall_status
                    != ProductionStrategyStatus.ROLLBACK_RECOMMENDED.value
                ):
                    overall_status = ProductionStrategyStatus.WARNING.value
                diagnostics.append(
                    f"WARNING: Treatment recovery rate ({rec_rate:.1%}) is trailing control ({c_rec_rate:.1%})."
                )

        # Guardrail B: Model Health Degradation
        if gov_rep.status == "DEGRADED":
            overall_status = ProductionStrategyStatus.DEGRADED.value
            rollback_rec = True
            diagnostics.append(
                "CRITICAL: Governing ML model health is in DEGRADED state."
            )
        elif gov_rep.status == "WARNING":
            if overall_status == ProductionStrategyStatus.HEALTHY.value:
                overall_status = ProductionStrategyStatus.WARNING.value
            diagnostics.append(
                "WARNING: Governing ML model health is in WARNING state."
            )

        # Guardrail C: Prediction Drift
        drift_level = gov_rep.prediction_drift.drift_level
        psi_val = gov_rep.prediction_drift.psi
        if drift_level == "SIGNIFICANT":
            if overall_status == ProductionStrategyStatus.HEALTHY.value:
                overall_status = ProductionStrategyStatus.WARNING.value
            psi_str = f"{psi_val:.3f}" if psi_val is not None else "N/A"
            diagnostics.append(
                f"WARNING: Significant prediction drift detected (PSI = {psi_str})."
            )

        # Guardrail D: Data Quality
        invalid_preds = gov_rep.data_quality.invalid_predictions
        if invalid_preds > 0:
            if overall_status == ProductionStrategyStatus.HEALTHY.value:
                overall_status = ProductionStrategyStatus.WARNING.value
            diagnostics.append(
                f"WARNING: Data quality alerts ({invalid_preds} invalid predictions)."
            )

        # Guardrail E: Phase 9F Rollback status
        if active_act.health.status == RolloutHealthStatus.ROLLBACK_RECOMMENDED.value:
            overall_status = ProductionStrategyStatus.ROLLBACK_RECOMMENDED.value
            rollback_rec = True
            if not any("CRITICAL: Treatment" in d for d in diagnostics):
                diagnostics.append(
                    "CRITICAL: Canary health diagnostics triggered ROLLBACK_RECOMMENDED."
                )

        if not diagnostics:
            diagnostics.append(
                "Production recovery strategy is operating stably within safe operational parameters."
            )

        strat_version = (
            active_act.target_segment.get("strategy_version", "strategy-v1.0")
            if active_act.target_segment
            else "strategy-v1.0"
        )

        return ProductionMonitoringResponse(
            status=overall_status,
            strategy_id=f"strat_{active_act.activation_id}",
            strategy_name=active_act.strategy_type,
            strategy_version=strat_version,
            model_version=active_act.model_version,
            activation_id=active_act.activation_id,
            recommendation_id=active_act.recommendation_id,
            rollout_percentage=active_act.rollout_percentage,
            sample_size=total_sample,
            treatment_sample_size=t_sample,
            control_sample_size=c_sample,
            recovery_rate=rec_rate,
            control_recovery_rate=c_rec_rate,
            absolute_uplift=abs_uplift,
            relative_uplift_pct=rel_uplift,
            incremental_erv_paise=inc_erv,
            financial_yield=yield_ratio,
            mttr_hours=mttr,
            model_health=gov_rep.status,
            prediction_psi=psi_val,
            drift_status=drift_level,
            rollback_recommended=rollback_rec,
            diagnostics=diagnostics,
            promoted_at=active_act.activated_at,
            promoted_by=active_act.activated_by,
            last_evaluated=now_utc,
        )


production_monitoring_service = ProductionMonitoringService()
