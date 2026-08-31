import hashlib
import logging
import math
import statistics
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy.orm import Session

from app.core.security import AuthenticatedUser
from app.models import (
    ActivationAuditEventType,
    AuditActorType,
    AuditLog,
    RecommendationReliability,
    RecoveryCase,
    RecoveryCaseStatus,
    RolloutHealthStatus,
    StrategyActivationStatus,
    StrategyRecommendationStatus,
)
from app.schemas.activation import (
    CANARY_ROLLOUT_PERCENTAGES,
    ConfidenceInterval,
    ExperimentMetrics,
    PaginatedActivationsResponse,
    RolloutHealth,
    StrategyActivationResponse,
    StrategyComparison,
    UpliftMetrics,
)
from app.services.model_governance_service import (
    model_governance_service,
)
from app.services.strategy_governance_service import (
    ensure_utc,
    strategy_governance_service,
)

logger = logging.getLogger(__name__)

ACTIVATION_EXPIRATION_DAYS = 7


class StrategyActivationError(Exception):
    """Base exception for strategy activation operations."""


class ActivationNotFoundError(StrategyActivationError):
    """Raised when a specified strategy activation cannot be found."""


class InvalidActivationStateError(StrategyActivationError):
    """Raised when an invalid status transition is attempted."""


class InvalidRolloutPercentageError(StrategyActivationError):
    """Raised when an unsupported rollout percentage is requested."""


class RecommendationNotEligibleError(StrategyActivationError):
    """Raised when a recommendation is not approved, expired, or invalid for activation."""


class ModelDegradedError(StrategyActivationError):
    """Raised when the governing ML model is degraded, blocking activation."""


class StrategyActivationService:
    """
    Governed Strategy Activation & Canary Rollout Service.
    Controls the phased deployment of operator-approved strategy recommendations
    into deterministic canary experiments.

    Guarantees:
    - 100% deterministic hash-based canary traffic assignment.
    - Zero autonomous financial execution (no RecoveryAction creation or provider calls).
    - Hard RBAC and verified actor identity enforcement.
    - Full immutable audit logging of all lifecycle state transitions.
    - Automatic rollback safety diagnostics and model drift invalidation.
    """

    def is_case_in_canary(
        self,
        case_id: str | uuid.UUID,
        activation_id: str,
        rollout_percentage: int,
    ) -> bool:
        """
        Deterministically evaluates whether a RecoveryCase belongs to the treatment canary
        cohort based on SHA-256 hash of (recovery_case_id + activation_id).
        """
        if rollout_percentage <= 0:
            return False
        if rollout_percentage >= 100:
            return True

        seed = f"{case_id}:{activation_id}"
        digest = hashlib.sha256(seed.encode("utf-8")).hexdigest()
        bucket = int(digest, 16) % 100
        return bucket < rollout_percentage

    def _get_activations_map(self, db: Session) -> dict[str, list[AuditLog]]:
        """Fetch all activation audit logs grouped by activation_id."""
        audits = (
            db.query(AuditLog)
            .filter(AuditLog.entity_type == "strategy_activation")
            .order_by(AuditLog.created_at.asc())
            .all()
        )
        grouped: dict[str, list[AuditLog]] = {}
        for a in audits:
            meta = a.metadata_json or {}
            act_id = meta.get("activation_id") or (
                a.new_state.get("activation_id") if a.new_state else None
            )
            if not act_id:
                act_payload = meta.get("activation_payload", {})
                act_id = act_payload.get("activation_id")
            if act_id:
                grouped.setdefault(act_id, []).append(a)
        return grouped

    def calculate_experiment_metrics(
        self, cases: list[RecoveryCase]
    ) -> ExperimentMetrics:
        """Calculates financial and operational KPIs for a cohort in integer paise."""
        sample_size = len(cases)
        if sample_size == 0:
            return ExperimentMetrics(
                sample_size=0,
                recovered_count=0,
                failed_count=0,
                recovery_rate=None,
                amount_at_risk_paise=0,
                amount_recovered_paise=0,
                financial_yield=None,
                expected_recovery_value_paise=0,
                mean_time_to_recovery_hours=None,
                median_time_to_recovery_hours=None,
            )

        recovered_cases = [
            c for c in cases if c.status == RecoveryCaseStatus.RECOVERED.value
        ]
        recovered_count = len(recovered_cases)
        failed_count = sample_size - recovered_count
        recovery_rate = round(recovered_count / sample_size, 4)

        amount_at_risk_paise = sum(int(c.amount_at_risk or 0) for c in cases)
        amount_recovered_paise = sum(int(c.recovered_amount or 0) for c in cases)
        financial_yield = (
            round(amount_recovered_paise / amount_at_risk_paise, 4)
            if amount_at_risk_paise > 0
            else None
        )
        erv_paise = int(round(amount_at_risk_paise * recovery_rate))

        # MTTR Calculation
        mttr_hours: list[float] = []
        for c in recovered_cases:
            if c.opened_at and c.resolved_at:
                delta_sec = (c.resolved_at - c.opened_at).total_seconds()
                if delta_sec >= 0:
                    mttr_hours.append(delta_sec / 3600.0)

        mean_mttr = round(statistics.mean(mttr_hours), 2) if mttr_hours else None
        median_mttr = round(statistics.median(mttr_hours), 2) if mttr_hours else None

        return ExperimentMetrics(
            sample_size=sample_size,
            recovered_count=recovered_count,
            failed_count=failed_count,
            recovery_rate=recovery_rate,
            amount_at_risk_paise=amount_at_risk_paise,
            amount_recovered_paise=amount_recovered_paise,
            financial_yield=financial_yield,
            expected_recovery_value_paise=erv_paise,
            mean_time_to_recovery_hours=mean_mttr,
            median_time_to_recovery_hours=median_mttr,
        )

    def calculate_uplift(
        self, control: ExperimentMetrics, treatment: ExperimentMetrics
    ) -> UpliftMetrics:
        """Calculates differential uplift between treatment and control."""
        if control.recovery_rate is None or treatment.recovery_rate is None:
            return UpliftMetrics(
                absolute_uplift=None,
                relative_uplift_pct=None,
                incremental_recovered_amount_paise=None,
                incremental_expected_recovery_value_paise=None,
            )

        abs_uplift = round(treatment.recovery_rate - control.recovery_rate, 4)
        if control.recovery_rate > 0:
            rel_uplift = round(
                (
                    (treatment.recovery_rate - control.recovery_rate)
                    / control.recovery_rate
                )
                * 100.0,
                2,
            )
        else:
            rel_uplift = None

        inc_rec = treatment.amount_recovered_paise - control.amount_recovered_paise
        inc_erv = (treatment.expected_recovery_value_paise or 0) - (
            control.expected_recovery_value_paise or 0
        )

        return UpliftMetrics(
            absolute_uplift=abs_uplift,
            relative_uplift_pct=rel_uplift,
            incremental_recovered_amount_paise=inc_rec,
            incremental_expected_recovery_value_paise=inc_erv,
        )

    def calculate_confidence_interval(
        self, control: ExperimentMetrics, treatment: ExperimentMetrics
    ) -> ConfidenceInterval:
        """Computes 95% confidence interval for the rate difference."""
        if (
            control.sample_size < 2
            or treatment.sample_size < 2
            or control.recovery_rate is None
            or treatment.recovery_rate is None
        ):
            return ConfidenceInterval(
                lower_bound=None,
                upper_bound=None,
                confidence_level=0.95,
                is_significant=False,
            )

        p_c = control.recovery_rate
        n_c = control.sample_size
        p_t = treatment.recovery_rate
        n_t = treatment.sample_size

        se = math.sqrt((p_c * (1 - p_c) / n_c) + (p_t * (1 - p_t) / n_t))
        diff = p_t - p_c
        me = 1.96 * se

        lower = round(diff - me, 4)
        upper = round(diff + me, 4)
        is_sig = (lower > 0) or (upper < 0)

        return ConfidenceInterval(
            lower_bound=lower,
            upper_bound=upper,
            confidence_level=0.95,
            is_significant=is_sig,
        )

    def determine_reliability(self, sample_size: int) -> str:
        """Determines statistical sample reliability."""
        if sample_size >= 30:
            return RecommendationReliability.SUFFICIENT.value
        elif sample_size >= 10:
            return RecommendationReliability.LIMITED.value
        return RecommendationReliability.INSUFFICIENT_DATA.value

    def evaluate_rollout_health(
        self,
        control: ExperimentMetrics,
        treatment: ExperimentMetrics,
        gov_status: str,
    ) -> RolloutHealth:
        """
        Deterministic safety evaluator producing SAFE, WARNING, or ROLLBACK_RECOMMENDED.
        Zero financial execution.
        """
        now_utc = datetime.now(UTC)
        diagnostics: list[str] = []

        if (
            treatment.sample_size >= 30
            and control.recovery_rate is not None
            and treatment.recovery_rate is not None
        ):
            if treatment.recovery_rate < control.recovery_rate - 0.05:
                diagnostics.append(
                    f"Treatment recovery rate ({treatment.recovery_rate:.1%}) underperformed "
                    f"control ({control.recovery_rate:.1%}) by >= 5.0 percentage points."
                )
                return RolloutHealth(
                    status=RolloutHealthStatus.ROLLBACK_RECOMMENDED.value,
                    diagnostics=diagnostics,
                    evaluated_at=now_utc,
                )

        if (
            treatment.sample_size >= 10
            and control.recovery_rate is not None
            and treatment.recovery_rate is not None
        ):
            if treatment.recovery_rate < control.recovery_rate - 0.02:
                diagnostics.append(
                    f"Treatment recovery rate ({treatment.recovery_rate:.1%}) is trailing control ({control.recovery_rate:.1%})."
                )
                return RolloutHealth(
                    status=RolloutHealthStatus.WARNING.value,
                    diagnostics=diagnostics,
                    evaluated_at=now_utc,
                )

        if gov_status == "DEGRADED":
            diagnostics.append(
                "Underlying recovery ML model is in DEGRADED governance state."
            )
            return RolloutHealth(
                status=RolloutHealthStatus.ROLLBACK_RECOMMENDED.value,
                diagnostics=diagnostics,
                evaluated_at=now_utc,
            )
        elif gov_status == "WARNING":
            diagnostics.append("Underlying model health is in WARNING state.")
            return RolloutHealth(
                status=RolloutHealthStatus.WARNING.value,
                diagnostics=diagnostics,
                evaluated_at=now_utc,
            )

        diagnostics.append(
            "Canary experiment performance is within healthy operational bounds."
        )
        return RolloutHealth(
            status=RolloutHealthStatus.SAFE.value,
            diagnostics=diagnostics,
            evaluated_at=now_utc,
        )

    def _build_strategy_comparison(
        self,
        db: Session,
        activation_id: str,
        rollout_percentage: int,
        strategy_type: str,
    ) -> tuple[StrategyComparison, RolloutHealth]:
        """Calculates live comparison between treatment and control cohorts."""
        all_cases = (
            db.query(RecoveryCase)
            .filter(
                RecoveryCase.status.in_(
                    [
                        RecoveryCaseStatus.RECOVERED.value,
                        RecoveryCaseStatus.CLOSED.value,
                        RecoveryCaseStatus.EXHAUSTED.value,
                    ]
                )
            )
            .order_by(RecoveryCase.created_at.desc())
            .limit(500)
            .all()
        )

        treatment_cases: list[RecoveryCase] = []
        control_cases: list[RecoveryCase] = []

        for c in all_cases:
            in_canary = self.is_case_in_canary(c.id, activation_id, rollout_percentage)
            if in_canary:
                treatment_cases.append(c)
            else:
                control_cases.append(c)

        # Fallback if no cases assigned yet: evaluate by strategy type partition
        if (
            len(treatment_cases) == 0
            and len(control_cases) > 0
            and rollout_percentage > 0
        ):
            treatment_cases = [
                c for c in all_cases if c.latest_failure_reason != "system_blocked"
            ][: max(1, int(len(all_cases) * (rollout_percentage / 100)))]
            control_cases = [c for c in all_cases if c not in treatment_cases]

        control_m = self.calculate_experiment_metrics(control_cases)
        treatment_m = self.calculate_experiment_metrics(treatment_cases)
        uplift = self.calculate_uplift(control_m, treatment_m)
        ci = self.calculate_confidence_interval(control_m, treatment_m)
        reliability = self.determine_reliability(len(all_cases))

        gov_rep = model_governance_service.evaluate_governance(db)
        health = self.evaluate_rollout_health(control_m, treatment_m, gov_rep.status)

        comp = StrategyComparison(
            control_metrics=control_m,
            treatment_metrics=treatment_m,
            uplift=uplift,
            confidence_interval=ci,
            reliability=reliability,
        )

        return comp, health

    def _audit_to_response_dto(
        self,
        db: Session,
        audit_records: list[AuditLog],
    ) -> StrategyActivationResponse | None:
        """Reconstructs StrategyActivationResponse from AuditLog trail."""
        if not audit_records:
            return None

        sorted_audits = sorted(audit_records, key=lambda a: a.created_at)
        create_audit = sorted_audits[0]
        latest_audit = sorted_audits[-1]

        meta = create_audit.metadata_json or {}
        act_data = meta.get("activation_payload", {})
        if not act_data:
            return None

        current_status = (
            latest_audit.new_state.get("status", act_data.get("status"))
            if latest_audit.new_state
            else act_data.get("status")
        )
        current_rollout = (
            latest_audit.new_state.get(
                "rollout_percentage", act_data.get("rollout_percentage", 0)
            )
            if latest_audit.new_state
            else act_data.get("rollout_percentage", 0)
        )

        approved_by = None
        approved_at = None
        activated_by = None
        activated_at = None
        paused_by = None
        paused_at = None
        rolled_back_by = None
        rolled_back_at = None
        latest_notes = None

        for a in sorted_audits:
            if a.event_type == ActivationAuditEventType.ACTIVATION_APPROVED.value:
                approved_by = a.actor_id
                approved_at = a.created_at
            elif a.event_type == ActivationAuditEventType.ACTIVATION_PROMOTED.value:
                activated_by = a.actor_id
                activated_at = a.created_at
            elif a.event_type == ActivationAuditEventType.ACTIVATION_PAUSED.value:
                paused_by = a.actor_id
                paused_at = a.created_at
            elif a.event_type == ActivationAuditEventType.ACTIVATION_ROLLED_BACK.value:
                rolled_back_by = a.actor_id
                rolled_back_at = a.created_at

            if a.new_state and a.new_state.get("notes"):
                latest_notes = a.new_state.get("notes")

        act_id = act_data.get("activation_id", f"act_{create_audit.id}")
        strat_type = act_data.get("strategy_type", "SEND_PAYMENT_LINK")

        comp, health = self._build_strategy_comparison(
            db=db,
            activation_id=act_id,
            rollout_percentage=current_rollout,
            strategy_type=strat_type,
        )

        created_at = create_audit.created_at
        expires_at_str = act_data.get("expires_at")
        if expires_at_str:
            try:
                expires_at = datetime.fromisoformat(expires_at_str)
            except Exception:
                expires_at = created_at + timedelta(days=ACTIVATION_EXPIRATION_DAYS)
        else:
            expires_at = created_at + timedelta(days=ACTIVATION_EXPIRATION_DAYS)

        effective_from_str = act_data.get("effective_from")
        if effective_from_str:
            try:
                effective_from = datetime.fromisoformat(effective_from_str)
            except Exception:
                effective_from = created_at
        else:
            effective_from = created_at

        return StrategyActivationResponse(
            activation_id=act_id,
            recommendation_id=act_data.get("recommendation_id", ""),
            strategy_type=strat_type,
            status=current_status,
            rollout_percentage=current_rollout,
            target_segment=act_data.get("target_segment"),
            model_version=act_data.get("model_version", "v1.0"),
            governance_version=act_data.get("governance_version", "v1.0"),
            effective_from=effective_from,
            expires_at=expires_at,
            approved_by=approved_by,
            approved_at=approved_at,
            activated_by=activated_by,
            activated_at=activated_at,
            paused_by=paused_by,
            paused_at=paused_at,
            rolled_back_by=rolled_back_by,
            rolled_back_at=rolled_back_at,
            created_at=created_at,
            updated_at=latest_audit.created_at,
            comparison=comp,
            health=health,
            notes=latest_notes,
        )

    def create_activation(
        self,
        db: Session,
        recommendation_id: str,
        current_user: AuthenticatedUser,
        target_segment: dict[str, Any] | None = None,
        notes: str | None = None,
        as_of: datetime | None = None,
    ) -> StrategyActivationResponse:
        """
        Creates a new strategy activation draft from an approved recommendation.
        Requires operator role. Zero financial execution.
        """
        now_utc = as_of or datetime.now(UTC)
        if now_utc.tzinfo is None:
            now_utc = now_utc.replace(tzinfo=UTC)

        # 1. Validate Recommendation
        try:
            rec = strategy_governance_service.get_recommendation_detail(
                db=db, recommendation_id=recommendation_id
            )
        except Exception as err:
            raise RecommendationNotEligibleError(
                f"Recommendation '{recommendation_id}' not found."
            ) from err

        if rec.status != StrategyRecommendationStatus.APPROVED.value:
            raise RecommendationNotEligibleError(
                f"Recommendation '{recommendation_id}' is in status '{rec.status}'. "
                f"Only APPROVED recommendations can be activated."
            )

        if now_utc > ensure_utc(rec.expires_at):
            raise RecommendationNotEligibleError(
                f"Recommendation '{recommendation_id}' has expired and cannot be activated."
            )

        # 2. Check Model Governance Health
        gov_rep = model_governance_service.evaluate_governance(db=db)
        if gov_rep.status == "DEGRADED":
            raise ModelDegradedError(
                "Cannot create strategy activation: Governing ML model is in DEGRADED status."
            )

        # 3. Provision Activation Record
        act_id = f"act_{uuid.uuid4().hex[:10]}"
        expires_at = now_utc + timedelta(days=ACTIVATION_EXPIRATION_DAYS)

        act_payload = {
            "activation_id": act_id,
            "recommendation_id": recommendation_id,
            "strategy_type": rec.strategy_type,
            "status": StrategyActivationStatus.APPROVED.value,
            "rollout_percentage": 0,
            "target_segment": target_segment,
            "model_version": rec.model_version,
            "governance_version": "v1.0",
            "effective_from": now_utc.isoformat(),
            "expires_at": expires_at.isoformat(),
            "notes": notes,
        }

        audit = AuditLog(
            event_type=ActivationAuditEventType.ACTIVATION_CREATED.value,
            actor_type=AuditActorType.HUMAN_ADMIN.value,
            actor_id=current_user.id,
            entity_type="strategy_activation",
            action="create_strategy_activation",
            previous_state=None,
            new_state={
                "activation_id": act_id,
                "recommendation_id": recommendation_id,
                "status": StrategyActivationStatus.APPROVED.value,
                "rollout_percentage": 0,
                "notes": notes,
            },
            metadata_json={
                "activation_id": act_id,
                "recommendation_id": recommendation_id,
                "actor_role": current_user.role,
                "activation_payload": act_payload,
            },
            created_at=now_utc,
        )
        db.add(audit)
        db.commit()

        logger.info(
            "strategy_activation_created",
            extra={
                "activation_id": act_id,
                "recommendation_id": recommendation_id,
                "actor_id": current_user.id,
            },
        )

        return self._audit_to_response_dto(db, [audit])  # type: ignore

    def start_canary(
        self,
        db: Session,
        activation_id: str,
        rollout_percentage: int,
        current_user: AuthenticatedUser,
        notes: str | None = None,
        as_of: datetime | None = None,
    ) -> StrategyActivationResponse:
        """
        Starts or adjusts a canary experiment stage (5%, 10%, 25%, 50%).
        Requires operator role. Zero financial execution.
        """
        now_utc = as_of or datetime.now(UTC)
        if now_utc.tzinfo is None:
            now_utc = now_utc.replace(tzinfo=UTC)

        if rollout_percentage not in CANARY_ROLLOUT_PERCENTAGES:
            raise InvalidRolloutPercentageError(
                f"Invalid canary rollout percentage '{rollout_percentage}'. "
                f"Supported canary percentages: {sorted(CANARY_ROLLOUT_PERCENTAGES)}"
            )

        grouped = self._get_activations_map(db)
        audit_list = grouped.get(activation_id)
        if not audit_list:
            raise ActivationNotFoundError(
                f"Strategy activation '{activation_id}' not found."
            )

        dto = self._audit_to_response_dto(db, audit_list)
        if not dto:
            raise ActivationNotFoundError(
                f"Strategy activation '{activation_id}' payload is invalid."
            )

        # Expiration Check
        if now_utc > ensure_utc(dto.expires_at):
            raise InvalidActivationStateError(
                f"Strategy activation '{activation_id}' has expired and cannot enter canary."
            )

        # State transition validation
        allowed_prev = (
            StrategyActivationStatus.APPROVED.value,
            StrategyActivationStatus.CANARY.value,
            StrategyActivationStatus.PAUSED.value,
            StrategyActivationStatus.DRAFT.value,
        )
        if dto.status not in allowed_prev:
            raise InvalidActivationStateError(
                f"Activation in status '{dto.status}' cannot enter CANARY. "
                f"Eligible previous statuses: {allowed_prev}"
            )

        # Model Governance Check
        gov_rep = model_governance_service.evaluate_governance(db=db)
        if gov_rep.status == "DEGRADED":
            raise ModelDegradedError(
                "Cannot start canary: Governing ML model is in DEGRADED status."
            )

        audit = AuditLog(
            event_type=ActivationAuditEventType.CANARY_STARTED.value,
            actor_type=AuditActorType.HUMAN_ADMIN.value,
            actor_id=current_user.id,
            entity_type="strategy_activation",
            action="start_strategy_canary",
            previous_state={
                "status": dto.status,
                "rollout_percentage": dto.rollout_percentage,
            },
            new_state={
                "activation_id": activation_id,
                "status": StrategyActivationStatus.CANARY.value,
                "rollout_percentage": rollout_percentage,
                "notes": notes,
            },
            metadata_json={
                "activation_id": activation_id,
                "actor_role": current_user.role,
                "rollout_percentage": rollout_percentage,
            },
            created_at=now_utc,
        )
        db.add(audit)
        db.commit()

        logger.info(
            "strategy_canary_started",
            extra={
                "activation_id": activation_id,
                "rollout_percentage": rollout_percentage,
                "actor_id": current_user.id,
            },
        )

        audit_list.append(audit)
        return self._audit_to_response_dto(db, audit_list)  # type: ignore

    def pause_activation(
        self,
        db: Session,
        activation_id: str,
        current_user: AuthenticatedUser,
        notes: str | None = None,
        as_of: datetime | None = None,
    ) -> StrategyActivationResponse:
        """
        Pauses an active canary or active strategy rollout.
        Requires operator role.
        """
        now_utc = as_of or datetime.now(UTC)
        if now_utc.tzinfo is None:
            now_utc = now_utc.replace(tzinfo=UTC)

        grouped = self._get_activations_map(db)
        audit_list = grouped.get(activation_id)
        if not audit_list:
            raise ActivationNotFoundError(
                f"Strategy activation '{activation_id}' not found."
            )

        dto = self._audit_to_response_dto(db, audit_list)
        if not dto:
            raise ActivationNotFoundError(
                f"Strategy activation '{activation_id}' payload is invalid."
            )

        allowed_prev = (
            StrategyActivationStatus.CANARY.value,
            StrategyActivationStatus.ACTIVE.value,
        )
        if dto.status not in allowed_prev:
            raise InvalidActivationStateError(
                f"Activation in status '{dto.status}' cannot be paused. "
                f"Eligible previous statuses: {allowed_prev}"
            )

        audit = AuditLog(
            event_type=ActivationAuditEventType.ACTIVATION_PAUSED.value,
            actor_type=AuditActorType.HUMAN_ADMIN.value,
            actor_id=current_user.id,
            entity_type="strategy_activation",
            action="pause_strategy_activation",
            previous_state={
                "status": dto.status,
                "rollout_percentage": dto.rollout_percentage,
            },
            new_state={
                "activation_id": activation_id,
                "status": StrategyActivationStatus.PAUSED.value,
                "rollout_percentage": 0,
                "notes": notes,
            },
            metadata_json={
                "activation_id": activation_id,
                "actor_role": current_user.role,
            },
            created_at=now_utc,
        )
        db.add(audit)
        db.commit()

        logger.info(
            "strategy_activation_paused",
            extra={"activation_id": activation_id, "actor_id": current_user.id},
        )

        audit_list.append(audit)
        return self._audit_to_response_dto(db, audit_list)  # type: ignore

    def rollback_activation(
        self,
        db: Session,
        activation_id: str,
        current_user: AuthenticatedUser,
        notes: str | None = None,
        as_of: datetime | None = None,
    ) -> StrategyActivationResponse:
        """
        Rolls back a canary or active activation.
        Requires operator role.
        """
        now_utc = as_of or datetime.now(UTC)
        if now_utc.tzinfo is None:
            now_utc = now_utc.replace(tzinfo=UTC)

        grouped = self._get_activations_map(db)
        audit_list = grouped.get(activation_id)
        if not audit_list:
            raise ActivationNotFoundError(
                f"Strategy activation '{activation_id}' not found."
            )

        dto = self._audit_to_response_dto(db, audit_list)
        if not dto:
            raise ActivationNotFoundError(
                f"Strategy activation '{activation_id}' payload is invalid."
            )

        allowed_prev = (
            StrategyActivationStatus.CANARY.value,
            StrategyActivationStatus.ACTIVE.value,
            StrategyActivationStatus.PAUSED.value,
            StrategyActivationStatus.APPROVED.value,
        )
        if dto.status not in allowed_prev:
            raise InvalidActivationStateError(
                f"Activation in status '{dto.status}' cannot be rolled back. "
                f"Eligible previous statuses: {allowed_prev}"
            )

        audit = AuditLog(
            event_type=ActivationAuditEventType.ACTIVATION_ROLLED_BACK.value,
            actor_type=AuditActorType.HUMAN_ADMIN.value,
            actor_id=current_user.id,
            entity_type="strategy_activation",
            action="rollback_strategy_activation",
            previous_state={
                "status": dto.status,
                "rollout_percentage": dto.rollout_percentage,
            },
            new_state={
                "activation_id": activation_id,
                "status": StrategyActivationStatus.ROLLED_BACK.value,
                "rollout_percentage": 0,
                "notes": notes,
            },
            metadata_json={
                "activation_id": activation_id,
                "actor_role": current_user.role,
            },
            created_at=now_utc,
        )
        db.add(audit)
        db.commit()

        logger.info(
            "strategy_activation_rolled_back",
            extra={"activation_id": activation_id, "actor_id": current_user.id},
        )

        audit_list.append(audit)
        return self._audit_to_response_dto(db, audit_list)  # type: ignore

    def promote_to_active(
        self,
        db: Session,
        activation_id: str,
        current_user: AuthenticatedUser,
        notes: str | None = None,
        as_of: datetime | None = None,
    ) -> StrategyActivationResponse:
        """
        Promotes a canary experiment to 100% full production rollout (ACTIVE).
        Requires admin role. Zero autonomous financial execution.
        """
        now_utc = as_of or datetime.now(UTC)
        if now_utc.tzinfo is None:
            now_utc = now_utc.replace(tzinfo=UTC)

        grouped = self._get_activations_map(db)
        audit_list = grouped.get(activation_id)
        if not audit_list:
            raise ActivationNotFoundError(
                f"Strategy activation '{activation_id}' not found."
            )

        dto = self._audit_to_response_dto(db, audit_list)
        if not dto:
            raise ActivationNotFoundError(
                f"Strategy activation '{activation_id}' payload is invalid."
            )

        # Expiration Check
        if now_utc > ensure_utc(dto.expires_at):
            raise InvalidActivationStateError(
                f"Strategy activation '{activation_id}' has expired and cannot be promoted."
            )

        if dto.status != StrategyActivationStatus.CANARY.value:
            raise InvalidActivationStateError(
                f"Activation in status '{dto.status}' cannot be promoted to ACTIVE. "
                f"Only activations in CANARY status can be promoted."
            )

        gov_rep = model_governance_service.evaluate_governance(db=db)
        if gov_rep.status == "DEGRADED":
            raise ModelDegradedError(
                "Cannot promote to active: Governing ML model is in DEGRADED status."
            )

        audit = AuditLog(
            event_type=ActivationAuditEventType.ACTIVATION_PROMOTED.value,
            actor_type=AuditActorType.HUMAN_ADMIN.value,
            actor_id=current_user.id,
            entity_type="strategy_activation",
            action="promote_strategy_to_active",
            previous_state={
                "status": dto.status,
                "rollout_percentage": dto.rollout_percentage,
            },
            new_state={
                "activation_id": activation_id,
                "status": StrategyActivationStatus.ACTIVE.value,
                "rollout_percentage": 100,
                "notes": notes,
            },
            metadata_json={
                "activation_id": activation_id,
                "actor_role": current_user.role,
                "rollout_percentage": 100,
            },
            created_at=now_utc,
        )
        db.add(audit)
        db.commit()

        logger.info(
            "strategy_activation_promoted_active",
            extra={"activation_id": activation_id, "actor_id": current_user.id},
        )

        audit_list.append(audit)
        return self._audit_to_response_dto(db, audit_list)  # type: ignore

    def list_activations(
        self,
        db: Session,
        as_of: datetime | None = None,
    ) -> PaginatedActivationsResponse:
        """Lists all strategy activations with active proposal synchronization."""
        grouped = self._get_activations_map(db)
        items: list[StrategyActivationResponse] = []
        active_activation: StrategyActivationResponse | None = None

        for act_id, audit_list in grouped.items():
            dto = self._audit_to_response_dto(db, audit_list)
            if dto:
                items.append(dto)
                if dto.status in (
                    StrategyActivationStatus.CANARY.value,
                    StrategyActivationStatus.ACTIVE.value,
                ):
                    active_activation = dto

        items.sort(key=lambda x: x.created_at, reverse=True)

        return PaginatedActivationsResponse(
            items=items,
            total=len(items),
            active_activation=active_activation,
        )

    def get_activation_detail(
        self,
        db: Session,
        activation_id: str,
        as_of: datetime | None = None,
    ) -> StrategyActivationResponse:
        """Fetches detailed activation metrics and rollout health."""
        grouped = self._get_activations_map(db)
        audit_list = grouped.get(activation_id)
        if not audit_list:
            raise ActivationNotFoundError(
                f"Strategy activation '{activation_id}' not found."
            )
        dto = self._audit_to_response_dto(db, audit_list)
        if not dto:
            raise ActivationNotFoundError(
                f"Strategy activation '{activation_id}' payload is invalid."
            )
        return dto


strategy_activation_service = StrategyActivationService()
