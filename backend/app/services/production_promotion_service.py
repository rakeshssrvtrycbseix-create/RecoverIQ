import logging
from datetime import UTC, datetime

from sqlalchemy.orm import Session

from app.core.security import AuthenticatedUser
from app.models import (
    ActivationAuditEventType,
    AuditActorType,
    AuditLog,
    PromotionBlockerCode,
    RolloutHealthStatus,
    StrategyActivationStatus,
)
from app.schemas.activation import StrategyActivationResponse
from app.schemas.production import (
    PromotionCheckItem,
    PromotionReadinessResponse,
)
from app.services.model_governance_service import (
    model_governance_service,
)
from app.services.strategy_activation_service import (
    ActivationNotFoundError,
    ensure_utc,
    strategy_activation_service,
)

logger = logging.getLogger(__name__)

MIN_PROMOTION_SAMPLE_SIZE = 100
MIN_PROMOTION_PRACTICAL_UPLIFT = 0.02  # 2 percentage points


class ProductionPromotionError(Exception):
    """Base exception for production promotion operations."""


class PromotionBlockedError(ProductionPromotionError):
    """Raised when an activation fails promotion safety checks (HTTP 409 Conflict)."""

    def __init__(
        self, message: str, blockers: list[str], checks: list[PromotionCheckItem]
    ) -> None:
        super().__init__(message)
        self.blockers = blockers
        self.checks = checks


class ProductionPromotionService:
    """
    Production Strategy Promotion Gate Service.
    Enforces deterministic safety rules 1-8 before allowing a canary strategy
    to be promoted to full production (100% rollout).
    Zero direct financial mutations.
    """

    def evaluate_promotion_readiness(
        self,
        db: Session,
        activation_id: str,
        as_of: datetime | None = None,
    ) -> PromotionReadinessResponse:
        """
        Deterministically evaluates all 8 promotion safety gates for a strategy activation.
        Read-only. Returns detailed check outcomes and blocker codes.
        """
        now_utc = as_of or datetime.now(UTC)
        if now_utc.tzinfo is None:
            now_utc = now_utc.replace(tzinfo=UTC)

        # 1. Fetch activation detail
        try:
            act: StrategyActivationResponse = (
                strategy_activation_service.get_activation_detail(
                    db=db, activation_id=activation_id, as_of=now_utc
                )
            )
        except ActivationNotFoundError as err:
            raise err

        checks: list[PromotionCheckItem] = []
        blockers: list[str] = []

        comp = act.comparison
        gov_rep = model_governance_service.evaluate_governance(db=db)

        # Extract sample sizes and metrics
        total_sample = (
            (comp.control_metrics.sample_size + comp.treatment_metrics.sample_size)
            if comp
            else 0
        )
        p_t = comp.treatment_metrics.recovery_rate if comp else None
        p_c = comp.control_metrics.recovery_rate if comp else None
        abs_uplift = comp.uplift.absolute_uplift if comp else None
        rel_uplift = comp.uplift.relative_uplift_pct if comp else None
        inc_erv = (
            comp.uplift.incremental_expected_recovery_value_paise if comp else None
        )
        ci_low = comp.confidence_interval.lower_bound if comp else None
        ci_high = comp.confidence_interval.upper_bound if comp else None
        model_health = gov_rep.status
        invalid_preds = gov_rep.data_quality.invalid_predictions
        data_quality = "CLEAN" if invalid_preds == 0 else "ANOMALIES_DETECTED"
        rollback_active = (
            act.health.status == RolloutHealthStatus.ROLLBACK_RECOMMENDED.value
        )

        # -------------------------------------------------------------
        # State Check: Eligible for promotion
        # -------------------------------------------------------------
        eligible_statuses = (
            StrategyActivationStatus.CANARY.value,
            StrategyActivationStatus.MONITORING.value,
            StrategyActivationStatus.APPROVED.value,
            StrategyActivationStatus.PROMOTION_READY.value,
        )
        if act.status not in eligible_statuses:
            blockers.append(PromotionBlockerCode.PROMOTION_BLOCKED_INVALID_STATE.value)
            checks.append(
                PromotionCheckItem(
                    rule="VALID_ACTIVATION_STATE",
                    passed=False,
                    value=act.status,
                    required="CANARY or MONITORING",
                    message=f"Activation in '{act.status}' status cannot enter production promotion.",
                )
            )
        else:
            checks.append(
                PromotionCheckItem(
                    rule="VALID_ACTIVATION_STATE",
                    passed=True,
                    value=act.status,
                    required="CANARY or MONITORING",
                    message="Activation is in an eligible staging status.",
                )
            )

        # -------------------------------------------------------------
        # RULE 1 — Minimum Sample Size (N >= 100)
        # -------------------------------------------------------------
        if total_sample >= MIN_PROMOTION_SAMPLE_SIZE:
            checks.append(
                PromotionCheckItem(
                    rule="MIN_SAMPLE_SIZE",
                    passed=True,
                    value=total_sample,
                    required=MIN_PROMOTION_SAMPLE_SIZE,
                    message=f"Sample size ({total_sample}) meets minimum threshold (>= {MIN_PROMOTION_SAMPLE_SIZE}).",
                )
            )
        else:
            blockers.append(
                PromotionBlockerCode.PROMOTION_BLOCKED_INSUFFICIENT_SAMPLE.value
            )
            checks.append(
                PromotionCheckItem(
                    rule="MIN_SAMPLE_SIZE",
                    passed=False,
                    value=total_sample,
                    required=MIN_PROMOTION_SAMPLE_SIZE,
                    message=f"Sample size ({total_sample}) is below minimum requirement ({MIN_PROMOTION_SAMPLE_SIZE}).",
                )
            )

        # -------------------------------------------------------------
        # RULE 2 — Positive Treatment Uplift (treatment_rate > control_rate)
        # -------------------------------------------------------------
        if p_t is not None and p_c is not None and p_t > p_c:
            checks.append(
                PromotionCheckItem(
                    rule="POSITIVE_UPLIFT",
                    passed=True,
                    value=f"{p_t:.1%} vs {p_c:.1%}",
                    required="treatment_rate > control_rate",
                    message="Treatment recovery rate is strictly positive relative to control.",
                )
            )
        else:
            blockers.append(PromotionBlockerCode.PROMOTION_BLOCKED_NO_UPLIFT.value)
            pt_str = f"{p_t:.1%}" if p_t is not None else "N/A"
            pc_str = f"{p_c:.1%}" if p_c is not None else "N/A"
            checks.append(
                PromotionCheckItem(
                    rule="POSITIVE_UPLIFT",
                    passed=False,
                    value=f"{pt_str} vs {pc_str}",
                    required="treatment_rate > control_rate",
                    message="Treatment recovery rate does not exceed control baseline.",
                )
            )

        # -------------------------------------------------------------
        # RULE 3 — Minimum Practical Uplift (absolute_uplift >= 0.02)
        # -------------------------------------------------------------
        if abs_uplift is not None and abs_uplift >= MIN_PROMOTION_PRACTICAL_UPLIFT:
            checks.append(
                PromotionCheckItem(
                    rule="MIN_PRACTICAL_UPLIFT",
                    passed=True,
                    value=f"+{abs_uplift * 100:.1f}%",
                    required=f"+{MIN_PROMOTION_PRACTICAL_UPLIFT * 100:.1f}%",
                    message=f"Absolute recovery uplift (+{abs_uplift * 100:.1f}%) meets practical significance threshold.",
                )
            )
        else:
            blockers.append(PromotionBlockerCode.PROMOTION_BLOCKED_LOW_EFFECT.value)
            val_str = (
                f"+{abs_uplift * 100:.1f}%"
                if abs_uplift is not None and abs_uplift >= 0
                else f"{abs_uplift * 100:.1f}%"
                if abs_uplift is not None
                else "N/A"
            )
            checks.append(
                PromotionCheckItem(
                    rule="MIN_PRACTICAL_UPLIFT",
                    passed=False,
                    value=val_str,
                    required=f"+{MIN_PROMOTION_PRACTICAL_UPLIFT * 100:.1f}%",
                    message=f"Absolute recovery uplift ({val_str}) is below the required 2.0 percentage points.",
                )
            )

        # -------------------------------------------------------------
        # RULE 4 — Confidence Interval (CI High >= 0)
        # -------------------------------------------------------------
        if ci_high is not None and ci_high >= 0:
            checks.append(
                PromotionCheckItem(
                    rule="CONFIDENCE_INTERVAL",
                    passed=True,
                    value=f"[{ci_low:+.3f}, {ci_high:+.3f}]"
                    if ci_low is not None
                    else "N/A",
                    required="Upper bound >= 0",
                    message="Confidence interval confirms non-negative upper bound.",
                )
            )
        else:
            blockers.append(
                PromotionBlockerCode.PROMOTION_BLOCKED_NEGATIVE_EFFECT.value
            )
            checks.append(
                PromotionCheckItem(
                    rule="CONFIDENCE_INTERVAL",
                    passed=False,
                    value=f"[{ci_low:+.3f}, {ci_high:+.3f}]"
                    if ci_low is not None and ci_high is not None
                    else "N/A",
                    required="Upper bound >= 0",
                    message="Confidence interval strongly indicates negative treatment effect.",
                )
            )

        # -------------------------------------------------------------
        # RULE 5 — Model Governance
        # -------------------------------------------------------------
        if model_health == "DEGRADED":
            blockers.append(PromotionBlockerCode.PROMOTION_BLOCKED_MODEL_DEGRADED.value)
            checks.append(
                PromotionCheckItem(
                    rule="MODEL_GOVERNANCE",
                    passed=False,
                    value=model_health,
                    required="HEALTHY or WARNING",
                    message="Underlying recovery ML model is in DEGRADED status.",
                )
            )
        elif model_health == "INSUFFICIENT_DATA" and gov_rep.sample_size < 10:
            blockers.append(
                PromotionBlockerCode.PROMOTION_BLOCKED_GOVERNANCE_DATA.value
            )
            checks.append(
                PromotionCheckItem(
                    rule="MODEL_GOVERNANCE",
                    passed=False,
                    value=model_health,
                    required="HEALTHY or WARNING",
                    message="Insufficient governance sample data for underlying model.",
                )
            )
        else:
            checks.append(
                PromotionCheckItem(
                    rule="MODEL_GOVERNANCE",
                    passed=True,
                    value=model_health,
                    required="HEALTHY or WARNING",
                    message=f"Model governance status is acceptable ({model_health}).",
                )
            )

        # -------------------------------------------------------------
        # RULE 6 — Data Quality
        # -------------------------------------------------------------
        if invalid_preds > 0:
            blockers.append(PromotionBlockerCode.PROMOTION_BLOCKED_DATA_QUALITY.value)
            checks.append(
                PromotionCheckItem(
                    rule="DATA_QUALITY",
                    passed=False,
                    value=f"{invalid_preds} invalid predictions",
                    required="0 invalid predictions",
                    message="Critical data quality anomalies detected in model feature/prediction store.",
                )
            )

        else:
            checks.append(
                PromotionCheckItem(
                    rule="DATA_QUALITY",
                    passed=True,
                    value=data_quality,
                    required="CLEAN",
                    message="Data quality telemetry is clean with 0 invalid predictions.",
                )
            )

        # -------------------------------------------------------------
        # RULE 7 — Rollback Diagnostics
        # -------------------------------------------------------------
        if rollback_active:
            blockers.append(
                PromotionBlockerCode.PROMOTION_BLOCKED_ROLLBACK_ACTIVE.value
            )
            checks.append(
                PromotionCheckItem(
                    rule="ROLLBACK_STATUS",
                    passed=False,
                    value="ROLLBACK_RECOMMENDED",
                    required="SAFE or WARNING",
                    message="Active canary has an open ROLLBACK_RECOMMENDED safety alert.",
                )
            )
        else:
            checks.append(
                PromotionCheckItem(
                    rule="ROLLBACK_STATUS",
                    passed=True,
                    value=act.health.status,
                    required="SAFE or WARNING",
                    message="No active rollback recommendation on this activation.",
                )
            )

        # -------------------------------------------------------------
        # RULE 8 — Strategy Expiration
        # -------------------------------------------------------------
        if now_utc > ensure_utc(act.expires_at):
            blockers.append(PromotionBlockerCode.PROMOTION_BLOCKED_EXPIRED.value)
            checks.append(
                PromotionCheckItem(
                    rule="RECOMMENDATION_TTL",
                    passed=False,
                    value=f"Expired at {act.expires_at.isoformat()}",
                    required=f"Valid as of {now_utc.isoformat()}",
                    message="Strategy activation TTL has elapsed and cannot be promoted.",
                )
            )
        else:
            checks.append(
                PromotionCheckItem(
                    rule="RECOMMENDATION_TTL",
                    passed=True,
                    value=f"Valid until {act.expires_at.isoformat()}",
                    required="Active TTL",
                    message="Strategy activation remains within active TTL validity window.",
                )
            )

        eligible = len(blockers) == 0
        readiness_status = "PROMOTION_READY" if eligible else "PROMOTION_BLOCKED"

        strategy_ver = (
            act.target_segment.get("strategy_version", "strategy-v1.0")
            if act.target_segment
            else "strategy-v1.0"
        )

        return PromotionReadinessResponse(
            activation_id=activation_id,
            strategy_type=act.strategy_type,
            strategy_version=strategy_ver,
            model_version=act.model_version,
            eligible=eligible,
            status=readiness_status,
            sample_size=total_sample,
            treatment_recovery_rate=p_t,
            control_recovery_rate=p_c,
            absolute_uplift=abs_uplift,
            relative_uplift_pct=rel_uplift,
            incremental_erv_paise=inc_erv,
            confidence_interval_low=ci_low,
            confidence_interval_high=ci_high,
            model_health=model_health,
            data_quality=data_quality,
            rollback_recommended=rollback_active,
            checks=checks,
            blockers=blockers,
            evaluated_at=now_utc,
        )

    def promote_to_production(
        self,
        db: Session,
        activation_id: str,
        current_user: AuthenticatedUser,
        reason: str | None = None,
        as_of: datetime | None = None,
    ) -> StrategyActivationResponse:
        """
        Promotes an activation to full 100% PRODUCTION status after validating all 8 safety gates.
        Strictly requires admin role. Zero financial mutations.
        """
        now_utc = as_of or datetime.now(UTC)
        if now_utc.tzinfo is None:
            now_utc = now_utc.replace(tzinfo=UTC)

        # 1. Run deterministic readiness evaluation
        readiness = self.evaluate_promotion_readiness(
            db=db, activation_id=activation_id, as_of=now_utc
        )

        if not readiness.eligible:
            msg = (
                f"Production promotion blocked for activation '{activation_id}'. "
                f"Blockers: {', '.join(readiness.blockers)}"
            )
            logger.warning(
                "production_promotion_blocked",
                extra={
                    "activation_id": activation_id,
                    "blockers": readiness.blockers,
                    "actor_id": current_user.id,
                },
            )
            raise PromotionBlockedError(
                message=msg, blockers=readiness.blockers, checks=readiness.checks
            )

        # 2. Persist audit log event for promotion evaluation & promotion action
        audit_eval = AuditLog(
            event_type=ActivationAuditEventType.PRODUCTION_PROMOTION_EVALUATED.value,
            actor_type=AuditActorType.HUMAN_ADMIN.value,
            actor_id=current_user.id,
            entity_type="strategy_activation",
            action="evaluate_production_promotion",
            previous_state=None,
            new_state={"status": "PROMOTION_READY", "eligible": True},
            metadata_json={
                "activation_id": activation_id,
                "actor_role": current_user.role,
                "readiness_summary": readiness.model_dump(mode="json"),
            },
            created_at=now_utc,
        )
        db.add(audit_eval)

        # 3. Transition activation state to PRODUCTION (100% rollout)
        audit_promote = AuditLog(
            event_type=ActivationAuditEventType.PRODUCTION_PROMOTED.value,
            actor_type=AuditActorType.HUMAN_ADMIN.value,
            actor_id=current_user.id,
            entity_type="strategy_activation",
            action="promote_strategy_to_production",
            previous_state={"rollout_percentage": 50},
            new_state={
                "activation_id": activation_id,
                "status": StrategyActivationStatus.PRODUCTION.value,
                "rollout_percentage": 100,
                "strategy_version": readiness.strategy_version,
                "promotion_reason": reason
                or "Canary demonstrated statistically positive recovery uplift",
            },
            metadata_json={
                "activation_id": activation_id,
                "actor_role": current_user.role,
                "rollout_percentage": 100,
                "strategy_version": readiness.strategy_version,
                "model_version": readiness.model_version,
                "promotion_reason": reason,
            },
            created_at=now_utc,
        )
        db.add(audit_promote)
        db.commit()

        logger.info(
            "production_strategy_promoted",
            extra={
                "activation_id": activation_id,
                "strategy_version": readiness.strategy_version,
                "actor_id": current_user.id,
            },
        )

        return strategy_activation_service.get_activation_detail(
            db=db, activation_id=activation_id, as_of=now_utc
        )


production_promotion_service = ProductionPromotionService()
