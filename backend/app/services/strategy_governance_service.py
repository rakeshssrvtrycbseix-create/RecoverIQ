import logging
import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy.orm import Session

from app.core.security import AuthenticatedUser
from app.models import (
    AuditActorType,
    AuditLog,
    RecommendationAuditEventType,
    RecommendationReliability,
    RecoveryActionType,
    StrategyRecommendationStatus,
)
from app.schemas.recommendation import (
    EvaluationEvidence,
    EvidenceBundle,
    GovernanceEvidence,
    OptimizationEvidence,
    PaginatedRecommendationsResponse,
    SimulationEvidence,
    StrategyRecommendationResponse,
)
from app.schemas.simulation import SimulationRequest
from app.services.counterfactual_simulation_service import (
    counterfactual_simulation_service,
)
from app.services.intelligence_evaluation_service import (
    intelligence_evaluation_service,
)
from app.services.model_governance_service import (
    model_governance_service,
)
from app.services.strategy_optimization_service import (
    strategy_optimization_service,
)

logger = logging.getLogger(__name__)

RECOMMENDATION_EXPIRATION_DAYS = 7


def ensure_utc(dt: datetime) -> datetime:
    """Ensure a datetime is timezone-aware in UTC."""
    if dt.tzinfo is None:
        return dt.replace(tzinfo=UTC)
    return dt.astimezone(UTC)


class RecommendationGovernanceError(Exception):
    """Base exception for recommendation governance operations."""


class RecommendationNotFoundError(RecommendationGovernanceError):
    """Raised when a specified recommendation does not exist."""


class InvalidRecommendationStateError(RecommendationGovernanceError):
    """Raised when an invalid status transition is requested."""


class StrategyGovernanceService:
    """
    Governed Strategy Recommendation & Decision Governance Engine.
    Synthesizes Phase 9A-9D intelligence layers into versioned, evidence-backed
    recommendations subject to deterministic safety gates and human operator review.
    Persisted via immutable AuditLog entities (0 database migrations).
    Zero autonomous financial execution.
    """

    def _calculate_recommendation_confidence(
        self,
        sample_size: int,
        model_health: str,
        invalid_predictions: int,
        relative_uplift_pct: float | None,
    ) -> tuple[float, str]:
        """
        Deterministic recommendation confidence score combining sample reliability,
        model health, data quality, and relative uplift strength.
        Distinct from ML prediction confidence.
        """
        score = 0.0

        # 1. Sample reliability score (0.0 to 0.40)
        if sample_size >= 30:
            score += 0.40
        elif sample_size >= 10:
            score += 0.20

        # 2. Model health score (0.0 to 0.30)
        if model_health == "HEALTHY":
            score += 0.30
        elif model_health == "WARNING":
            score += 0.15

        # 3. Data quality score (0.0 to 0.15)
        if invalid_predictions == 0:
            score += 0.15

        # 4. Relative uplift strength score (0.0 to 0.15)
        if relative_uplift_pct is not None and relative_uplift_pct >= 10.0:
            score += 0.15
        elif relative_uplift_pct is not None and relative_uplift_pct > 0.0:
            score += 0.08

        score = round(min(1.0, max(0.0, score)), 2)

        if score >= 0.75:
            level = "HIGH"
        elif score >= 0.45:
            level = "MEDIUM"
        else:
            level = "LOW"

        return score, level

    def _audit_to_response_dto(
        self,
        audit_records: list[AuditLog],
    ) -> StrategyRecommendationResponse | None:
        """Reconstruct a StrategyRecommendationResponse from chronological AuditLog entries."""
        if not audit_records:
            return None

        # Sort chronological
        sorted_audits = sorted(audit_records, key=lambda a: a.created_at)
        create_audit = sorted_audits[0]
        latest_audit = sorted_audits[-1]

        meta = create_audit.metadata_json or {}
        rec_data = meta.get("recommendation_payload", {})
        if not rec_data:
            return None

        # Determine current status from latest audit
        current_status = (
            latest_audit.new_state.get("status", rec_data.get("status"))
            if latest_audit.new_state
            else rec_data.get("status")
        )

        # Review info
        reviewed_by = None
        reviewed_at = None
        review_notes = None
        for a in reversed(sorted_audits):
            if a.event_type in (
                RecommendationAuditEventType.RECOMMENDATION_APPROVED.value,
                RecommendationAuditEventType.RECOMMENDATION_REJECTED.value,
            ):
                reviewed_by = a.actor_id
                reviewed_at = a.created_at
                review_notes = a.new_state.get("notes") if a.new_state else None
                break

        evidence_dict = rec_data.get("evidence", {})
        eval_snap = evidence_dict.get("evaluation", {})
        gov_snap = evidence_dict.get("governance", {})
        opt_snap = evidence_dict.get("optimization", {})
        sim_snap = evidence_dict.get("simulation", {})

        evidence = EvidenceBundle(
            evaluation=EvaluationEvidence(
                sample_size=eval_snap.get("sample_size", 0),
                accuracy=eval_snap.get("accuracy"),
                precision=eval_snap.get("precision"),
                recall=eval_snap.get("recall"),
                f1_score=eval_snap.get("f1_score"),
                brier_score=eval_snap.get("brier_score"),
            ),
            governance=GovernanceEvidence(
                model_health=gov_snap.get("model_health", "HEALTHY"),
                drift_status=gov_snap.get("drift_status", "LOW"),
                prediction_psi=gov_snap.get("prediction_psi"),
                data_quality_status=gov_snap.get("data_quality_status", "HEALTHY"),
                model_version=gov_snap.get("model_version", "v1.0"),
            ),
            optimization=OptimizationEvidence(
                champion_strategy=opt_snap.get("champion_strategy"),
                champion_recovery_rate=opt_snap.get("champion_recovery_rate"),
                champion_financial_yield=opt_snap.get("champion_financial_yield"),
                champion_erv_paise=opt_snap.get("champion_erv_paise"),
                strategy_sample_size=opt_snap.get("strategy_sample_size", 0),
            ),
            simulation=SimulationEvidence(
                baseline_strategy=sim_snap.get("baseline_strategy", "RETRY_PAYMENT"),
                alternative_strategy=sim_snap.get(
                    "alternative_strategy", "SEND_PAYMENT_LINK"
                ),
                comparable_population_size=sim_snap.get(
                    "comparable_population_size", 0
                ),
                population_match_type=sim_snap.get(
                    "population_match_type", "GLOBAL_BASELINE"
                ),
                baseline_recovery_rate=sim_snap.get("baseline_recovery_rate"),
                alternative_recovery_rate=sim_snap.get("alternative_recovery_rate"),
                rate_delta=sim_snap.get("rate_delta"),
                relative_uplift_pct=sim_snap.get("relative_uplift_pct"),
                incremental_erv_paise=sim_snap.get("incremental_erv_paise"),
                simulation_reliability=sim_snap.get(
                    "simulation_reliability", "INSUFFICIENT_DATA"
                ),
            ),
        )

        conf_val = float(rec_data.get("recommendation_confidence", 0.0))
        conf_lvl = (
            "HIGH" if conf_val >= 0.75 else ("MEDIUM" if conf_val >= 0.45 else "LOW")
        )

        created_at = create_audit.created_at
        expires_at_str = rec_data.get("expires_at")
        if expires_at_str:
            try:
                expires_at = datetime.fromisoformat(expires_at_str)
            except Exception:
                expires_at = created_at + timedelta(days=RECOMMENDATION_EXPIRATION_DAYS)
        else:
            expires_at = created_at + timedelta(days=RECOMMENDATION_EXPIRATION_DAYS)

        return StrategyRecommendationResponse(
            recommendation_id=rec_data.get(
                "recommendation_id", f"rec_{create_audit.id}"
            ),
            strategy_type=rec_data.get("strategy_type", "SEND_PAYMENT_LINK"),
            retry_delay_hours=rec_data.get("retry_delay_hours", 4),
            status=current_status,
            created_at=created_at,
            expires_at=expires_at,
            model_version=rec_data.get("model_version", "v1.0"),
            sample_size=rec_data.get("sample_size", 0),
            reliability=rec_data.get("reliability", "INSUFFICIENT_DATA"),
            recommendation_confidence=conf_val,
            confidence_level=conf_lvl,
            baseline_recovery_rate=rec_data.get("baseline_recovery_rate"),
            alternative_recovery_rate=rec_data.get("alternative_recovery_rate"),
            rate_delta=rec_data.get("rate_delta"),
            relative_uplift_pct=rec_data.get("relative_uplift_pct"),
            baseline_erv_paise=rec_data.get("baseline_erv_paise"),
            alternative_erv_paise=rec_data.get("alternative_erv_paise"),
            incremental_erv_paise=rec_data.get("incremental_erv_paise"),
            governance_status=rec_data.get("governance_status", "HEALTHY"),
            reasoning=rec_data.get("reasoning", ""),
            diagnostics=rec_data.get("diagnostics", []),
            evidence=evidence,
            reviewed_by=reviewed_by,
            reviewed_at=reviewed_at,
            review_notes=review_notes,
        )

    def _get_recommendations_map(self, db: Session) -> dict[str, list[AuditLog]]:
        """Fetch all recommendation audit logs grouped by recommendation_id."""
        audits = (
            db.query(AuditLog)
            .filter(AuditLog.entity_type == "strategy_recommendation")
            .order_by(AuditLog.created_at.asc())
            .all()
        )
        grouped: dict[str, list[AuditLog]] = {}
        for a in audits:
            meta = a.metadata_json or {}
            rec_id = meta.get("recommendation_id") or (
                a.new_state.get("recommendation_id") if a.new_state else None
            )
            if not rec_id:
                rec_payload = meta.get("recommendation_payload", {})
                rec_id = rec_payload.get("recommendation_id")
            if rec_id:
                grouped.setdefault(rec_id, []).append(a)
        return grouped

    def evaluate_and_sync_recommendation(
        self,
        db: Session,
        as_of: datetime | None = None,
    ) -> StrategyRecommendationResponse | None:
        """
        Evaluate full intelligence telemetry (9A-9D) and generate or refresh governed recommendations.
        Deterministic rules enforce safety gates. Zero financial execution.
        """
        now_utc = as_of or datetime.now(UTC)
        if now_utc.tzinfo is None:
            now_utc = now_utc.replace(tzinfo=UTC)

        # 1. Fetch intelligence from 9A, 9B, 9C
        eval_report = intelligence_evaluation_service.evaluate(db=db)
        gov_report = model_governance_service.evaluate_governance(db=db)
        opt_report = strategy_optimization_service.optimize(db=db)

        # 2. Check for active unexpired recommendations in AuditLog history
        grouped = self._get_recommendations_map(db)
        active_rec_dto = None

        for rec_id, audit_list in grouped.items():
            dto = self._audit_to_response_dto(audit_list)
            if not dto:
                continue

            if dto.status == StrategyRecommendationStatus.REVIEW_REQUIRED.value:
                # Check expiration
                exp_dt = ensure_utc(dto.expires_at)
                if now_utc > exp_dt:
                    # Transition to EXPIRED
                    audit = AuditLog(
                        event_type=RecommendationAuditEventType.RECOMMENDATION_EXPIRED.value,
                        actor_type=AuditActorType.POLICY_ENGINE.value,
                        actor_id="system_governance",
                        entity_type="strategy_recommendation",
                        action="expire_stale_recommendation",
                        previous_state={
                            "status": StrategyRecommendationStatus.REVIEW_REQUIRED.value
                        },
                        new_state={
                            "status": StrategyRecommendationStatus.EXPIRED.value,
                            "recommendation_id": rec_id,
                        },
                        metadata_json={
                            "recommendation_id": rec_id,
                            "reason": "Expiration timestamp elapsed",
                        },
                        created_at=now_utc,
                    )
                    db.add(audit)
                    db.commit()
                elif gov_report.status == "DEGRADED":
                    # Stale due to model degradation
                    audit = AuditLog(
                        event_type=RecommendationAuditEventType.RECOMMENDATION_EXPIRED.value,
                        actor_type=AuditActorType.POLICY_ENGINE.value,
                        actor_id="system_governance",
                        entity_type="strategy_recommendation",
                        action="expire_degraded_recommendation",
                        previous_state={
                            "status": StrategyRecommendationStatus.REVIEW_REQUIRED.value
                        },
                        new_state={
                            "status": StrategyRecommendationStatus.EXPIRED.value,
                            "recommendation_id": rec_id,
                        },
                        metadata_json={
                            "recommendation_id": rec_id,
                            "reason": "Model degraded",
                        },
                        created_at=now_utc,
                    )
                    db.add(audit)
                    db.commit()
                else:
                    active_rec_dto = dto
                    break

        if active_rec_dto:
            return active_rec_dto

        # 3. Apply Deterministic Governance Gates
        sample_size = opt_report.sample_size
        diagnostics: list[str] = []

        # Rule 1: Insufficient historical data (N < 10)
        if sample_size < 10:
            return None

        # Rule 4: Model governance degraded
        if gov_report.status == "DEGRADED":
            return None

        # Rule 6: Data quality anomalies
        if gov_report.data_quality.invalid_predictions > 0:
            return None

        # Check champion recommendation from 9C
        champ = opt_report.overall_recommendation
        if not champ or not champ.action_type:
            return None

        target_action = champ.action_type
        target_delay = champ.recommended_delay_hours or 4
        baseline_action = RecoveryActionType.RETRY_PAYMENT.value
        baseline_delay = 12

        # 4. Run Counterfactual Simulation (9D)
        sim_res = counterfactual_simulation_service.simulate(
            db=db,
            req=SimulationRequest(
                current_action_type=baseline_action,
                current_delay_hours=baseline_delay,
                alternative_action_type=target_action,
                alternative_delay_hours=target_delay,
            ),
        )

        base_strat = sim_res.current_strategy
        alt_strat = sim_res.alternative_strategy
        uplift = sim_res.estimated_uplift

        # Rule 7 & 8: Positive improvement requirement
        if alt_strat.recovery_rate is None or base_strat.recovery_rate is None:
            return None

        if uplift.recovery_rate_delta is None or uplift.recovery_rate_delta <= 0.0:
            return None

        if (
            uplift.estimated_incremental_erv_paise is None
            or uplift.estimated_incremental_erv_paise <= 0
        ):
            return None

        # Determine reliability
        if sample_size >= 30:
            reliability = RecommendationReliability.SUFFICIENT.value
        else:
            reliability = RecommendationReliability.LIMITED.value
            diagnostics.append(
                "Limited historical evidence sample size (10 <= N < 30)."
            )

        conf_score, conf_level = self._calculate_recommendation_confidence(
            sample_size=sample_size,
            model_health=gov_report.status,
            invalid_predictions=gov_report.data_quality.invalid_predictions,
            relative_uplift_pct=uplift.relative_uplift_pct,
        )

        # 5. Assemble Evidence Snapshot Bundle
        evidence_dict = {
            "evaluation": {
                "sample_size": eval_report.classification.sample_size,
                "accuracy": eval_report.classification.accuracy,
                "precision": eval_report.classification.precision,
                "recall": eval_report.classification.recall,
                "f1_score": eval_report.classification.f1_score,
                "brier_score": eval_report.classification.brier_score,
            },
            "governance": {
                "model_health": gov_report.status,
                "drift_status": gov_report.prediction_drift.drift_level,
                "prediction_psi": gov_report.prediction_drift.psi,
                "data_quality_status": "HEALTHY"
                if gov_report.data_quality.invalid_predictions == 0
                else "WARNING",
                "model_version": gov_report.model_version,
            },
            "optimization": {
                "champion_strategy": champ.action_type,
                "champion_recovery_rate": champ.recovery_rate,
                "champion_financial_yield": None,
                "champion_erv_paise": champ.expected_recovery_value,
                "strategy_sample_size": champ.sample_size,
            },
            "simulation": {
                "baseline_strategy": base_strat.action_type,
                "alternative_strategy": alt_strat.action_type,
                "comparable_population_size": sim_res.population.total_cases_analyzed,
                "population_match_type": sim_res.population.segmentation_level_used,
                "baseline_recovery_rate": base_strat.recovery_rate,
                "alternative_recovery_rate": alt_strat.recovery_rate,
                "rate_delta": uplift.recovery_rate_delta,
                "relative_uplift_pct": uplift.relative_uplift_pct,
                "incremental_erv_paise": uplift.estimated_incremental_erv_paise,
                "simulation_reliability": alt_strat.reliability,
            },
        }

        reasoning = (
            f"Alternative strategy '{target_action}' (delay {target_delay}h) demonstrated +{uplift.recovery_rate_delta:.1%} "
            f"recovery rate improvement over baseline with ₹{(uplift.estimated_incremental_erv_paise or 0) / 100:,.2f} "
            f"estimated incremental ERV."
        )

        rec_id = f"rec_{uuid.uuid4().hex[:10]}"
        expires_at = now_utc + timedelta(days=RECOMMENDATION_EXPIRATION_DAYS)

        rec_payload = {
            "recommendation_id": rec_id,
            "strategy_type": target_action,
            "retry_delay_hours": target_delay,
            "status": StrategyRecommendationStatus.REVIEW_REQUIRED.value,
            "created_at": now_utc.isoformat(),
            "expires_at": expires_at.isoformat(),
            "model_version": gov_report.model_version,
            "sample_size": sample_size,
            "reliability": reliability,
            "recommendation_confidence": conf_score,
            "baseline_recovery_rate": base_strat.recovery_rate,
            "alternative_recovery_rate": alt_strat.recovery_rate,
            "rate_delta": uplift.recovery_rate_delta,
            "relative_uplift_pct": uplift.relative_uplift_pct,
            "baseline_erv_paise": base_strat.expected_recovery_value_paise,
            "alternative_erv_paise": alt_strat.expected_recovery_value_paise,
            "incremental_erv_paise": uplift.estimated_incremental_erv_paise,
            "governance_status": gov_report.status,
            "reasoning": reasoning,
            "diagnostics": diagnostics,
            "evidence": evidence_dict,
        }

        # Record creation audit log
        audit = AuditLog(
            event_type=RecommendationAuditEventType.RECOMMENDATION_CREATED.value,
            actor_type=AuditActorType.POLICY_ENGINE.value,
            actor_id="strategy_governance_engine",
            entity_type="strategy_recommendation",
            action="create_governed_recommendation",
            previous_state=None,
            new_state={
                "recommendation_id": rec_id,
                "strategy_type": target_action,
                "status": StrategyRecommendationStatus.REVIEW_REQUIRED.value,
                "confidence": conf_score,
            },
            metadata_json={
                "recommendation_id": rec_id,
                "recommendation_payload": rec_payload,
                "evidence_version": "v1.0",
            },
            created_at=now_utc,
        )
        db.add(audit)
        db.commit()

        logger.info(
            "strategy_recommendation_created",
            extra={
                "recommendation_id": rec_id,
                "strategy": target_action,
                "confidence": conf_score,
                "reliability": reliability,
            },
        )

        return self._audit_to_response_dto([audit])

    def list_recommendations(
        self,
        db: Session,
    ) -> PaginatedRecommendationsResponse:
        """List all historical recommendations with active recommendation sync."""
        active = self.evaluate_and_sync_recommendation(db=db)
        grouped = self._get_recommendations_map(db)
        items: list[StrategyRecommendationResponse] = []
        for rec_id, audit_list in grouped.items():
            dto = self._audit_to_response_dto(audit_list)
            if dto:
                items.append(dto)

        # Sort newest first
        items.sort(key=lambda x: x.created_at, reverse=True)

        return PaginatedRecommendationsResponse(
            items=items,
            total=len(items),
            active_recommendation=active,
        )

    def get_recommendation_detail(
        self,
        db: Session,
        recommendation_id: str,
    ) -> StrategyRecommendationResponse:
        """Get detail for a specific recommendation by its public recommendation_id."""
        grouped = self._get_recommendations_map(db)
        audit_list = grouped.get(recommendation_id)
        if not audit_list:
            raise RecommendationNotFoundError(
                f"Strategy recommendation '{recommendation_id}' not found."
            )
        dto = self._audit_to_response_dto(audit_list)
        if not dto:
            raise RecommendationNotFoundError(
                f"Strategy recommendation '{recommendation_id}' payload is invalid."
            )
        return dto

    def approve_recommendation(
        self,
        db: Session,
        recommendation_id: str,
        current_user: AuthenticatedUser,
        notes: str | None = None,
        as_of: datetime | None = None,
    ) -> StrategyRecommendationResponse:
        """
        Operator approves a strategy recommendation in REVIEW_REQUIRED state.
        Transitions status strictly to APPROVED.
        Zero financial action execution.
        """
        now_utc = as_of or datetime.now(UTC)
        if now_utc.tzinfo is None:
            now_utc = now_utc.replace(tzinfo=UTC)

        grouped = self._get_recommendations_map(db)
        audit_list = grouped.get(recommendation_id)
        if not audit_list:
            raise RecommendationNotFoundError(
                f"Strategy recommendation '{recommendation_id}' not found."
            )

        dto = self._audit_to_response_dto(audit_list)
        if not dto:
            raise RecommendationNotFoundError(
                f"Strategy recommendation '{recommendation_id}' payload is invalid."
            )

        exp_dt = ensure_utc(dto.expires_at)
        if now_utc > exp_dt:
            # Expire recommendation
            audit = AuditLog(
                event_type=RecommendationAuditEventType.RECOMMENDATION_EXPIRED.value,
                actor_type=AuditActorType.POLICY_ENGINE.value,
                actor_id="system_governance",
                entity_type="strategy_recommendation",
                action="expire_stale_recommendation",
                previous_state={"status": dto.status},
                new_state={
                    "status": StrategyRecommendationStatus.EXPIRED.value,
                    "recommendation_id": recommendation_id,
                },
                metadata_json={
                    "recommendation_id": recommendation_id,
                    "reason": "Expiration timestamp elapsed",
                },
                created_at=now_utc,
            )
            db.add(audit)
            db.commit()
            raise InvalidRecommendationStateError(
                "Recommendation has expired and cannot be approved."
            )

        if dto.status != StrategyRecommendationStatus.REVIEW_REQUIRED.value:
            raise InvalidRecommendationStateError(
                f"Recommendation in status '{dto.status}' cannot be approved. Only 'REVIEW_REQUIRED' is eligible."
            )

        # Record Approval Audit Entry
        audit = AuditLog(
            event_type=RecommendationAuditEventType.RECOMMENDATION_APPROVED.value,
            actor_type=AuditActorType.HUMAN_ADMIN.value,
            actor_id=current_user.id,
            entity_type="strategy_recommendation",
            action="approve_governed_recommendation",
            previous_state={"status": dto.status},
            new_state={
                "status": StrategyRecommendationStatus.APPROVED.value,
                "reviewed_by": current_user.id,
                "notes": notes,
                "recommendation_id": recommendation_id,
            },
            metadata_json={
                "recommendation_id": recommendation_id,
                "actor_role": current_user.role,
                "strategy_type": dto.strategy_type,
            },
            created_at=now_utc,
        )
        db.add(audit)
        db.commit()

        logger.info(
            "strategy_recommendation_approved",
            extra={
                "recommendation_id": recommendation_id,
                "actor_id": current_user.id,
                "actor_role": current_user.role,
            },
        )

        audit_list.append(audit)
        return self._audit_to_response_dto(audit_list)  # type: ignore

    def reject_recommendation(
        self,
        db: Session,
        recommendation_id: str,
        current_user: AuthenticatedUser,
        notes: str | None = None,
        as_of: datetime | None = None,
    ) -> StrategyRecommendationResponse:
        """
        Operator rejects a strategy recommendation in REVIEW_REQUIRED state.
        Transitions status strictly to REJECTED.
        Zero financial action execution.
        """
        now_utc = as_of or datetime.now(UTC)
        if now_utc.tzinfo is None:
            now_utc = now_utc.replace(tzinfo=UTC)

        grouped = self._get_recommendations_map(db)
        audit_list = grouped.get(recommendation_id)
        if not audit_list:
            raise RecommendationNotFoundError(
                f"Strategy recommendation '{recommendation_id}' not found."
            )

        dto = self._audit_to_response_dto(audit_list)
        if not dto:
            raise RecommendationNotFoundError(
                f"Strategy recommendation '{recommendation_id}' payload is invalid."
            )

        exp_dt = ensure_utc(dto.expires_at)
        if now_utc > exp_dt:
            audit = AuditLog(
                event_type=RecommendationAuditEventType.RECOMMENDATION_EXPIRED.value,
                actor_type=AuditActorType.POLICY_ENGINE.value,
                actor_id="system_governance",
                entity_type="strategy_recommendation",
                action="expire_stale_recommendation",
                previous_state={"status": dto.status},
                new_state={
                    "status": StrategyRecommendationStatus.EXPIRED.value,
                    "recommendation_id": recommendation_id,
                },
                metadata_json={
                    "recommendation_id": recommendation_id,
                    "reason": "Expiration timestamp elapsed",
                },
                created_at=now_utc,
            )
            db.add(audit)
            db.commit()
            raise InvalidRecommendationStateError(
                "Recommendation has expired and cannot be rejected."
            )

        if dto.status != StrategyRecommendationStatus.REVIEW_REQUIRED.value:
            raise InvalidRecommendationStateError(
                f"Recommendation in status '{dto.status}' cannot be rejected. Only 'REVIEW_REQUIRED' is eligible."
            )

        # Record Rejection Audit Entry
        audit = AuditLog(
            event_type=RecommendationAuditEventType.RECOMMENDATION_REJECTED.value,
            actor_type=AuditActorType.HUMAN_ADMIN.value,
            actor_id=current_user.id,
            entity_type="strategy_recommendation",
            action="reject_governed_recommendation",
            previous_state={"status": dto.status},
            new_state={
                "status": StrategyRecommendationStatus.REJECTED.value,
                "reviewed_by": current_user.id,
                "notes": notes,
                "recommendation_id": recommendation_id,
            },
            metadata_json={
                "recommendation_id": recommendation_id,
                "actor_role": current_user.role,
                "strategy_type": dto.strategy_type,
            },
            created_at=now_utc,
        )
        db.add(audit)
        db.commit()

        logger.info(
            "strategy_recommendation_rejected",
            extra={
                "recommendation_id": recommendation_id,
                "actor_id": current_user.id,
                "actor_role": current_user.role,
            },
        )

        audit_list.append(audit)
        return self._audit_to_response_dto(audit_list)  # type: ignore


strategy_governance_service = StrategyGovernanceService()
