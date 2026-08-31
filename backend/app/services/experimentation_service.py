"""Causal Experimentation, Statistical Hypothesis Testing & Decision Intelligence Service (Phase 9H).

Authoritative Invariants:
- Strictly observational from a financial perspective.
- Zero RecoveryAction creation, zero Payment mutation, zero gateway calls.
- PolicyEngine remains 100% authoritative over all actions.
- Deterministic SHA-256 cohort assignment.
- Wilson/Newcombe 95% confidence intervals and two-proportion z-tests.
- AuditLog persistence with 0 database schema migrations.
"""

import hashlib
import math
import uuid
from datetime import UTC, datetime
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models import (
    AuditActorType,
    AuditLog,
    BalanceStatus,
    CausalEvidenceLevel,
    CohortType,
    Customer,
    ExperimentAuditEventType,
    ExperimentDecisionType,
    ExperimentStatus,
    MLPrediction,
    Payment,
    RecoveryCase,
    RecoveryCaseStatus,
)
from app.schemas.experimentation import (
    BalanceDiagnostics,
    BalanceFeatureMetric,
    CausalEffectEstimate,
    DataQualityReport,
    ExperimentAnalysisResponse,
    ExperimentCohortMetrics,
    ExperimentDecisionResult,
    ExperimentRequest,
    ExperimentResponse,
    OverlapDiagnostics,
    PaginatedExperimentsResponse,
    PopulationDefinition,
    StatisticalTestResult,
    StoppingDiagnostics,
)
from app.services.model_governance_service import model_governance_service

ASSIGNMENT_METHOD = "SHA256_DETERMINISTIC"
MIN_TOTAL_SAMPLE_SIZE = 100
MIN_COHORT_SAMPLE_SIZE = 50


class ExperimentConflictError(HTTPException):
    """Exception raised when an invalid experiment state transition is requested."""

    def __init__(self, detail: str) -> None:
        super().__init__(status_code=status.HTTP_409_CONFLICT, detail=detail)


class ExperimentationService:
    """Service governing causal experimentation lifecycle, cohort assignment, and statistical analysis."""

    def assign_cohort(
        self, experiment_id: str, case_id: str, allocation_percentage: int = 50
    ) -> CohortType:
        """Deterministically assigns a recovery case to CONTROL or TREATMENT using SHA-256."""
        if allocation_percentage <= 0:
            return CohortType.CONTROL
        if allocation_percentage >= 100:
            return CohortType.TREATMENT

        seed = f"{experiment_id}:{case_id}"
        digest = hashlib.sha256(seed.encode("utf-8")).hexdigest()
        bucket = int(digest, 16) % 10000

        control_threshold = (100 - allocation_percentage) * 100
        if bucket < control_threshold:
            return CohortType.CONTROL
        return CohortType.TREATMENT

    def _get_experiments_map(self, db: Session) -> dict[str, list[AuditLog]]:
        """Fetches all experiment audit logs grouped by experiment_id."""
        audits = (
            db.query(AuditLog)
            .filter(AuditLog.entity_type == "experiment")
            .order_by(AuditLog.created_at.asc())
            .all()
        )
        grouped: dict[str, list[AuditLog]] = {}
        for a in audits:
            meta = a.metadata_json or {}
            exp_id = meta.get("experiment_id") or (
                str(a.entity_id) if a.entity_id else None
            )
            if exp_id:
                grouped.setdefault(exp_id, []).append(a)
        return grouped

    def _reconstruct_experiment(
        self, experiment_id: str, logs: list[AuditLog]
    ) -> dict[str, Any] | None:
        """Reconstructs current experiment state from immutable audit trail."""
        if not logs:
            return None

        creation_log = next(
            (
                entry
                for entry in logs
                if entry.action == ExperimentAuditEventType.EXPERIMENT_CREATED.value
                or entry.event_type == ExperimentAuditEventType.EXPERIMENT_CREATED.value
            ),
            logs[0],
        )
        meta = creation_log.metadata_json or {}

        name = meta.get("name", f"Experiment {experiment_id[:8]}")
        description = meta.get("description")
        treatment_strategy = meta.get("treatment_strategy", "SEND_PAYMENT_LINK")
        control_strategy = meta.get("control_strategy", "RETRY_PAYMENT")
        allocation_percentage = int(meta.get("allocation_percentage", 50))
        pop_def = meta.get("population_definition", {})
        model_version = meta.get("model_version", "v1.0")
        created_by = creation_log.actor_id or "system"
        created_at = creation_log.created_at.isoformat()

        status_val = ExperimentStatus.DRAFT.value
        started_at: str | None = None
        ended_at: str | None = None
        notes: str | None = meta.get("notes")

        for log_item in logs:
            l_meta = log_item.metadata_json or {}
            action_name = log_item.action or log_item.event_type
            if action_name == ExperimentAuditEventType.EXPERIMENT_APPROVED.value:
                status_val = ExperimentStatus.APPROVED.value
            elif action_name == ExperimentAuditEventType.EXPERIMENT_STARTED.value:
                status_val = ExperimentStatus.RUNNING.value
                if not started_at:
                    started_at = log_item.created_at.isoformat()
            elif action_name == ExperimentAuditEventType.EXPERIMENT_PAUSED.value:
                status_val = ExperimentStatus.PAUSED.value
            elif action_name == ExperimentAuditEventType.EXPERIMENT_STOPPED.value:
                status_val = ExperimentStatus.STOPPED.value
                ended_at = log_item.created_at.isoformat()
            elif action_name == ExperimentAuditEventType.EXPERIMENT_COMPLETED.value:
                status_val = ExperimentStatus.COMPLETED.value
                ended_at = log_item.created_at.isoformat()

            if l_meta.get("notes"):
                notes = l_meta.get("notes")

        runtime_hours: float | None = None
        if started_at:
            start_dt = datetime.fromisoformat(started_at)
            if start_dt.tzinfo is None:
                start_dt = start_dt.replace(tzinfo=UTC)
            end_dt = datetime.fromisoformat(ended_at) if ended_at else datetime.now(UTC)
            if end_dt.tzinfo is None:
                end_dt = end_dt.replace(tzinfo=UTC)
            runtime_hours = round(
                max(0.0, (end_dt - start_dt).total_seconds() / 3600.0), 2
            )

        return {
            "experiment_id": experiment_id,
            "name": name,
            "description": description,
            "status": status_val,
            "treatment_strategy": treatment_strategy,
            "control_strategy": control_strategy,
            "allocation_percentage": allocation_percentage,
            "population_definition": PopulationDefinition(**pop_def)
            if isinstance(pop_def, dict)
            else PopulationDefinition(),
            "model_version": model_version,
            "created_by": created_by,
            "created_at": created_at,
            "started_at": started_at,
            "ended_at": ended_at,
            "runtime_hours": runtime_hours,
            "notes": notes,
        }

    def create_experiment(
        self,
        db: Session,
        payload: ExperimentRequest,
        actor_id: str,
        actor_role: str,
    ) -> ExperimentResponse:
        """Creates a new causal experiment in DRAFT status."""
        exp_id = str(uuid.uuid4())
        pop_dict = (
            payload.population_definition.model_dump()
            if payload.population_definition
            else {}
        )

        audit_entry = AuditLog(
            event_type=ExperimentAuditEventType.EXPERIMENT_CREATED.value,
            actor_type=AuditActorType.HUMAN_ADMIN.value
            if actor_role.upper() == "ADMIN"
            else AuditActorType.POLICY_ENGINE.value,
            actor_id=actor_id,
            entity_type="experiment",
            entity_id=uuid.UUID(exp_id),
            action=ExperimentAuditEventType.EXPERIMENT_CREATED.value,
            metadata_json={
                "experiment_id": exp_id,
                "name": payload.name,
                "description": payload.description,
                "treatment_strategy": payload.treatment_strategy,
                "control_strategy": payload.control_strategy,
                "allocation_percentage": payload.allocation_percentage,
                "population_definition": pop_dict,
                "model_version": payload.model_version or "v1.0",
                "notes": payload.notes,
                "created_by": actor_id,
                "created_at": datetime.now(UTC).isoformat(),
            },
        )
        db.add(audit_entry)
        db.commit()

        exp_data = self._reconstruct_experiment(exp_id, [audit_entry])
        return self._to_response_dto(exp_data, sample_size=0)

    def list_experiments(
        self,
        db: Session,
        status_filter: str | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> PaginatedExperimentsResponse:
        """Lists all experiments with pagination."""
        exp_map = self._get_experiments_map(db)
        reconstructed = []
        for exp_id, logs in exp_map.items():
            exp_data = self._reconstruct_experiment(exp_id, logs)
            if exp_data:
                if status_filter and exp_data["status"] != status_filter.upper():
                    continue
                reconstructed.append(exp_data)

        # Sort descending by created_at
        reconstructed.sort(key=lambda x: x["created_at"], reverse=True)
        total = len(reconstructed)
        active_count = sum(
            1 for e in reconstructed if e["status"] == ExperimentStatus.RUNNING.value
        )

        start_idx = (page - 1) * page_size
        paged = reconstructed[start_idx : start_idx + page_size]

        items = [self._to_response_dto(e) for e in paged]
        return PaginatedExperimentsResponse(
            items=items,
            total=total,
            active_count=active_count,
        )

    def get_experiment(self, db: Session, experiment_id: str) -> ExperimentResponse:
        """Fetches a specific experiment by ID."""
        exp_map = self._get_experiments_map(db)
        logs = exp_map.get(experiment_id)
        if not logs:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Experiment '{experiment_id}' not found.",
            )
        exp_data = self._reconstruct_experiment(experiment_id, logs)
        if not exp_data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Experiment '{experiment_id}' could not be reconstructed.",
            )
        return self._to_response_dto(exp_data)

    def start_experiment(
        self,
        db: Session,
        experiment_id: str,
        actor_id: str,
        notes: str | None = None,
    ) -> ExperimentResponse:
        """Starts or resumes an experiment."""
        exp_map = self._get_experiments_map(db)
        logs = exp_map.get(experiment_id)
        if not logs:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Experiment '{experiment_id}' not found.",
            )
        exp_data = self._reconstruct_experiment(experiment_id, logs)
        current_status = exp_data["status"]

        if current_status not in (
            ExperimentStatus.DRAFT.value,
            ExperimentStatus.APPROVED.value,
            ExperimentStatus.PAUSED.value,
        ):
            raise ExperimentConflictError(
                f"Cannot start experiment in '{current_status}' status. Must be DRAFT, APPROVED, or PAUSED."
            )

        audit_entry = AuditLog(
            event_type=ExperimentAuditEventType.EXPERIMENT_STARTED.value,
            actor_type=AuditActorType.POLICY_ENGINE.value,
            actor_id=actor_id,
            entity_type="experiment",
            entity_id=uuid.UUID(experiment_id),
            action=ExperimentAuditEventType.EXPERIMENT_STARTED.value,
            metadata_json={
                "experiment_id": experiment_id,
                "notes": notes or f"Experiment started by {actor_id}",
                "previous_status": current_status,
                "started_at": datetime.now(UTC).isoformat(),
            },
        )
        db.add(audit_entry)
        db.commit()

        logs.append(audit_entry)
        updated_exp = self._reconstruct_experiment(experiment_id, logs)
        return self._to_response_dto(updated_exp)

    def pause_experiment(
        self,
        db: Session,
        experiment_id: str,
        actor_id: str,
        notes: str | None = None,
    ) -> ExperimentResponse:
        """Pauses a running experiment."""
        exp_map = self._get_experiments_map(db)
        logs = exp_map.get(experiment_id)
        if not logs:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Experiment '{experiment_id}' not found.",
            )
        exp_data = self._reconstruct_experiment(experiment_id, logs)
        current_status = exp_data["status"]

        if current_status != ExperimentStatus.RUNNING.value:
            raise ExperimentConflictError(
                f"Cannot pause experiment in '{current_status}' status. Must be RUNNING."
            )

        audit_entry = AuditLog(
            event_type=ExperimentAuditEventType.EXPERIMENT_PAUSED.value,
            actor_type=AuditActorType.POLICY_ENGINE.value,
            actor_id=actor_id,
            entity_type="experiment",
            entity_id=uuid.UUID(experiment_id),
            action=ExperimentAuditEventType.EXPERIMENT_PAUSED.value,
            metadata_json={
                "experiment_id": experiment_id,
                "notes": notes or f"Experiment paused by {actor_id}",
                "previous_status": current_status,
                "paused_at": datetime.now(UTC).isoformat(),
            },
        )
        db.add(audit_entry)
        db.commit()

        logs.append(audit_entry)
        updated_exp = self._reconstruct_experiment(experiment_id, logs)
        return self._to_response_dto(updated_exp)

    def complete_experiment(
        self,
        db: Session,
        experiment_id: str,
        actor_id: str,
        notes: str | None = None,
    ) -> ExperimentResponse:
        """Completes an experiment."""
        exp_map = self._get_experiments_map(db)
        logs = exp_map.get(experiment_id)
        if not logs:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Experiment '{experiment_id}' not found.",
            )
        exp_data = self._reconstruct_experiment(experiment_id, logs)
        current_status = exp_data["status"]

        if current_status not in (
            ExperimentStatus.RUNNING.value,
            ExperimentStatus.PAUSED.value,
        ):
            raise ExperimentConflictError(
                f"Cannot complete experiment in '{current_status}' status. Must be RUNNING or PAUSED."
            )

        audit_entry = AuditLog(
            event_type=ExperimentAuditEventType.EXPERIMENT_COMPLETED.value,
            actor_type=AuditActorType.POLICY_ENGINE.value,
            actor_id=actor_id,
            entity_type="experiment",
            entity_id=uuid.UUID(experiment_id),
            action=ExperimentAuditEventType.EXPERIMENT_COMPLETED.value,
            metadata_json={
                "experiment_id": experiment_id,
                "notes": notes or f"Experiment completed by {actor_id}",
                "previous_status": current_status,
                "completed_at": datetime.now(UTC).isoformat(),
            },
        )
        db.add(audit_entry)
        db.commit()

        logs.append(audit_entry)
        updated_exp = self._reconstruct_experiment(experiment_id, logs)
        return self._to_response_dto(updated_exp)

    def analyze_experiment(
        self, db: Session, experiment_id: str
    ) -> ExperimentAnalysisResponse:
        """Evaluates causal effect, hypothesis testing, Wilson/Newcombe CI, and balance diagnostics."""
        exp_map = self._get_experiments_map(db)
        logs = exp_map.get(experiment_id)
        if not logs:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Experiment '{experiment_id}' not found.",
            )
        exp_data = self._reconstruct_experiment(experiment_id, logs)

        # 1. Fetch matching resolved cases
        pop_def: PopulationDefinition = exp_data["population_definition"]
        cases_query = (
            db.query(RecoveryCase)
            .join(Payment, RecoveryCase.payment_id == Payment.id)
            .outerjoin(Customer, RecoveryCase.customer_id == Customer.id)
            .filter(
                RecoveryCase.status.in_(
                    [
                        RecoveryCaseStatus.RECOVERED.value,
                        RecoveryCaseStatus.CLOSED.value,
                        RecoveryCaseStatus.EXHAUSTED.value,
                    ]
                )
            )
        )

        if pop_def.risk_tier:
            cases_query = cases_query.filter(Customer.risk_tier == pop_def.risk_tier)

        all_cases = cases_query.order_by(RecoveryCase.created_at.asc()).all()

        if pop_def.failure_reason:
            all_cases = [
                c
                for c in all_cases
                if c.payment
                and (c.payment.metadata_json or {}).get("failure_reason")
                == pop_def.failure_reason
            ]

        # 2. Partition deterministically into Control and Treatment
        control_cases: list[RecoveryCase] = []
        treatment_cases: list[RecoveryCase] = []
        alloc_pct = exp_data["allocation_percentage"]

        for c in all_cases:
            cohort = self.assign_cohort(experiment_id, str(c.id), alloc_pct)
            if cohort == CohortType.CONTROL:
                control_cases.append(c)
            else:
                treatment_cases.append(c)

        ctrl_metrics = self._calculate_cohort_metrics(control_cases, "CONTROL")
        trt_metrics = self._calculate_cohort_metrics(treatment_cases, "TREATMENT")
        total_sample = ctrl_metrics.sample_size + trt_metrics.sample_size

        # 3. Effect estimation (ATE, Relative Uplift, Incremental ERV)
        ate: float | None = None
        rel_uplift: float | None = None
        incremental_cases: float | None = None
        incremental_erv: int | None = None

        if (
            ctrl_metrics.recovery_rate is not None
            and trt_metrics.recovery_rate is not None
        ):
            ate = round(trt_metrics.recovery_rate - ctrl_metrics.recovery_rate, 4)
            if ctrl_metrics.recovery_rate > 0:
                rel_uplift = round((ate / ctrl_metrics.recovery_rate) * 100.0, 2)
            incremental_cases = round(ate * trt_metrics.sample_size, 1)
            incremental_erv = (
                trt_metrics.expected_recovery_value_paise
                - ctrl_metrics.expected_recovery_value_paise
            )

        causal_effect = CausalEffectEstimate(
            absolute_treatment_effect=ate,
            relative_uplift_pct=rel_uplift,
            incremental_recovered_cases_estimate=incremental_cases,
            incremental_erv_paise=incremental_erv,
        )

        # 4. Statistical Testing (Two-proportion z-test & Wilson/Newcombe CI)
        stat_test = self._perform_statistical_test(
            trt_metrics.recovered_count,
            trt_metrics.sample_size,
            ctrl_metrics.recovered_count,
            ctrl_metrics.sample_size,
        )

        # 5. Balance Diagnostics
        balance_diag = self._evaluate_balance(db, control_cases, treatment_cases)

        # 6. Data Quality Report
        data_quality = self._evaluate_data_quality(db, all_cases)

        # 7. Overlap Diagnostics
        overlap_diag = self._evaluate_overlap(db, experiment_id, pop_def)

        # 8. Model Governance Status
        gov_report = model_governance_service.evaluate_governance(db)
        is_model_degraded = gov_report.status.upper() == "DEGRADED"

        # 9. Stopping Diagnostics
        stopping_diag = self._evaluate_stopping_rules(
            causal_effect=causal_effect,
            statistical_test=stat_test,
            is_model_degraded=is_model_degraded,
            data_quality=data_quality,
            overlap=overlap_diag,
        )

        # 10. Causal Evidence Level & Deterministic Decision
        decision_result = self._determine_decision_and_evidence(
            sample_size=total_sample,
            ctrl_sample=ctrl_metrics.sample_size,
            trt_sample=trt_metrics.sample_size,
            causal_effect=causal_effect,
            stat_test=stat_test,
            balance=balance_diag,
            stopping=stopping_diag,
            experiment_status=exp_data["status"],
        )

        return ExperimentAnalysisResponse(
            experiment_id=experiment_id,
            experiment_name=exp_data["name"],
            status=exp_data["status"],
            allocation_percentage=alloc_pct,
            assignment_method=ASSIGNMENT_METHOD,
            sample_size=total_sample,
            control_cohort=ctrl_metrics,
            treatment_cohort=trt_metrics,
            causal_effect=causal_effect,
            statistical_test=stat_test,
            balance_diagnostics=balance_diag,
            data_quality=data_quality,
            overlap_diagnostics=overlap_diag,
            stopping_diagnostics=stopping_diag,
            decision=decision_result,
            evaluated_at=datetime.now(UTC).isoformat(),
            disclaimer=(
                "Observational causal experimentation intelligence. PolicyEngine remains 100% authoritative. "
                "Experiments evaluate empirical historical/active outcomes with zero autonomous financial executions."
            ),
        )

    def _calculate_cohort_metrics(
        self, cases: list[RecoveryCase], cohort_type: str
    ) -> ExperimentCohortMetrics:
        """Calculates cohort recovery and financial KPIs in integer paise."""
        sample_size = len(cases)
        if sample_size == 0:
            return ExperimentCohortMetrics(
                cohort_type=cohort_type,
                sample_size=0,
                recovered_count=0,
                failed_count=0,
                recovery_rate=None,
                amount_at_risk_paise=0,
                amount_recovered_paise=0,
                financial_yield=None,
                expected_recovery_value_paise=0,
                mttr_hours=None,
                failure_rate=None,
                average_attempts=None,
            )

        recovered_cases = [
            c for c in cases if c.status == RecoveryCaseStatus.RECOVERED.value
        ]
        recovered_count = len(recovered_cases)
        failed_count = sample_size - recovered_count
        recovery_rate = round(recovered_count / sample_size, 4)
        failure_rate = round(failed_count / sample_size, 4)

        amount_at_risk_paise = sum(int(c.amount_at_risk or 0) for c in cases)
        amount_recovered_paise = sum(int(c.recovered_amount or 0) for c in cases)
        financial_yield = (
            round(amount_recovered_paise / amount_at_risk_paise, 4)
            if amount_at_risk_paise > 0
            else None
        )
        erv_paise = int(round(amount_at_risk_paise * recovery_rate))

        # MTTR
        durations = []
        for c in recovered_cases:
            if c.opened_at and c.resolved_at:
                hrs = (c.resolved_at - c.opened_at).total_seconds() / 3600.0
                if hrs >= 0:
                    durations.append(hrs)
        mttr_hours = round(sum(durations) / len(durations), 2) if durations else None

        avg_attempts = round(
            sum(getattr(c, "total_attempts_count", 1) or 1 for c in cases)
            / sample_size,
            2,
        )

        return ExperimentCohortMetrics(
            cohort_type=cohort_type,
            sample_size=sample_size,
            recovered_count=recovered_count,
            failed_count=failed_count,
            recovery_rate=recovery_rate,
            amount_at_risk_paise=amount_at_risk_paise,
            amount_recovered_paise=amount_recovered_paise,
            financial_yield=financial_yield,
            expected_recovery_value_paise=erv_paise,
            mttr_hours=mttr_hours,
            failure_rate=failure_rate,
            average_attempts=avg_attempts,
        )

    def _wilson_interval(
        self, x: int, n: int, z: float = 1.95996
    ) -> tuple[float, float]:
        """Wilson score interval for single proportion."""
        if n == 0:
            return (0.0, 0.0)
        p = x / n
        denom = 1.0 + (z**2) / n
        center = (p + (z**2) / (2.0 * n)) / denom
        spread = (z * math.sqrt((p * (1.0 - p) / n) + (z**2) / (4.0 * (n**2)))) / denom
        return (max(0.0, center - spread), min(1.0, center + spread))

    def _newcombe_difference_interval(
        self, x1: int, n1: int, x2: int, n2: int, z: float = 1.95996
    ) -> tuple[float, float]:
        """Newcombe hybrid two-proportion confidence interval for p1 - p2."""
        if n1 == 0 or n2 == 0:
            return (0.0, 0.0)
        p1 = x1 / n1
        p2 = x2 / n2
        l1, u1 = self._wilson_interval(x1, n1, z)
        l2, u2 = self._wilson_interval(x2, n2, z)

        diff = p1 - p2
        lower = diff - math.sqrt((p1 - l1) ** 2 + (u2 - p2) ** 2)
        upper = diff + math.sqrt((u1 - p1) ** 2 + (p2 - l2) ** 2)
        return (round(max(-1.0, lower), 4), round(min(1.0, upper), 4))

    def _perform_statistical_test(
        self, x1: int, n1: int, x2: int, n2: int, alpha: float = 0.05
    ) -> StatisticalTestResult:
        """Two-proportion pooled z-test and Wilson/Newcombe 95% CI."""
        if n1 < MIN_COHORT_SAMPLE_SIZE or n2 < MIN_COHORT_SAMPLE_SIZE:
            ci_low, ci_high = self._newcombe_difference_interval(x1, n1, x2, n2)
            return StatisticalTestResult(
                test_name="TWO_PROPORTION_Z_TEST",
                test_statistic=None,
                p_value=None,
                alpha=alpha,
                statistically_significant=False,
                confidence_interval_low=ci_low if n1 > 0 and n2 > 0 else None,
                confidence_interval_high=ci_high if n1 > 0 and n2 > 0 else None,
                confidence_level=0.95,
            )

        p1 = x1 / n1
        p2 = x2 / n2
        p_pool = (x1 + x2) / (n1 + n2)

        if p_pool in (0.0, 1.0):
            z = 0.0
            p_val = 1.0
        else:
            se = math.sqrt(p_pool * (1.0 - p_pool) * (1.0 / n1 + 1.0 / n2))
            z = (p1 - p2) / se if se > 0 else 0.0
            p_val = math.erfc(abs(z) / math.sqrt(2.0))

        ci_low, ci_high = self._newcombe_difference_interval(x1, n1, x2, n2)
        sig = bool(p_val is not None and p_val < alpha)

        return StatisticalTestResult(
            test_name="TWO_PROPORTION_Z_TEST",
            test_statistic=round(z, 4),
            p_value=round(p_val, 4),
            alpha=alpha,
            statistically_significant=sig,
            confidence_interval_low=ci_low,
            confidence_interval_high=ci_high,
            confidence_level=0.95,
        )

    def _evaluate_balance(
        self,
        db: Session,
        control_cases: list[RecoveryCase],
        treatment_cases: list[RecoveryCase],
    ) -> BalanceDiagnostics:
        """Evaluates covariate balance across control and treatment cohorts."""
        if not control_cases or not treatment_cases:
            return BalanceDiagnostics(
                overall_status=BalanceStatus.BALANCED.value,
                is_confounded=False,
                features=[],
                diagnostics=[
                    "Insufficient data to calculate covariate balance distributions."
                ],
            )

        # 1. Map features for control & treatment
        def extract_distributions(
            cases: list[RecoveryCase],
        ) -> dict[str, dict[str, float]]:
            risk_counts: dict[str, int] = {}
            failure_counts: dict[str, int] = {}
            amount_counts: dict[str, int] = {}
            attempt_counts: dict[str, int] = {}
            n = len(cases)

            for c in cases:
                # Risk Tier
                rt = (
                    (
                        c.customer.risk_tier.value
                        if c.customer and hasattr(c.customer.risk_tier, "value")
                        else str(c.customer.risk_tier)
                    )
                    if c.customer and c.customer.risk_tier
                    else "STANDARD"
                )
                risk_counts[rt] = risk_counts.get(rt, 0) + 1

                # Failure Reason
                fr = (
                    (c.payment.metadata_json or {}).get("failure_reason", "OTHER")
                    if c.payment
                    else "OTHER"
                )
                failure_counts[fr] = failure_counts.get(fr, 0) + 1

                # Amount Band
                amt = int(c.amount_at_risk or 0)
                if amt < 100000:  # < 1,000 INR
                    b = "<1k"
                elif amt < 500000:  # 1k - 5k INR
                    b = "1k-5k"
                elif amt < 2000000:  # 5k - 20k INR
                    b = "5k-20k"
                else:
                    b = ">20k"
                amount_counts[b] = amount_counts.get(b, 0) + 1

                # Attempt
                att = f"attempt_{min(getattr(c, 'total_attempts_count', 1) or 1, 3)}"
                attempt_counts[att] = attempt_counts.get(att, 0) + 1

            return {
                "risk_tier": {k: round(v / n, 4) for k, v in risk_counts.items()},
                "failure_reason": {
                    k: round(v / n, 4) for k, v in failure_counts.items()
                },
                "amount_band": {k: round(v / n, 4) for k, v in amount_counts.items()},
                "attempt_number": {
                    k: round(v / n, 4) for k, v in attempt_counts.items()
                },
            }

        ctrl_dist = extract_distributions(control_cases)
        trt_dist = extract_distributions(treatment_cases)

        features: list[BalanceFeatureMetric] = []
        has_major = False
        has_minor = False
        diagnostics: list[str] = []

        for feat in ("risk_tier", "failure_reason", "amount_band", "attempt_number"):
            cd = ctrl_dist.get(feat, {})
            td = trt_dist.get(feat, {})
            all_keys = set(cd.keys()) | set(td.keys())
            max_diff = 0.0
            for k in all_keys:
                diff = abs(td.get(k, 0.0) - cd.get(k, 0.0))
                if diff > max_diff:
                    max_diff = diff

            max_diff = round(max_diff, 4)
            if max_diff >= 0.25:
                status_str = BalanceStatus.MAJOR_IMBALANCE.value
                has_major = True
                diagnostics.append(
                    f"Major covariate imbalance detected in '{feat}' (max diff: {max_diff * 100:.1f}%)."
                )
            elif max_diff >= 0.10:
                status_str = BalanceStatus.MINOR_IMBALANCE.value
                has_minor = True
                diagnostics.append(
                    f"Minor covariate imbalance detected in '{feat}' (max diff: {max_diff * 100:.1f}%)."
                )
            else:
                status_str = BalanceStatus.BALANCED.value

            features.append(
                BalanceFeatureMetric(
                    feature_name=feat,
                    control_dist=cd,
                    treatment_dist=td,
                    standardized_difference=max_diff,
                    status=status_str,
                )
            )

        if has_major:
            overall = BalanceStatus.MAJOR_IMBALANCE.value
            is_confounded = True
        elif has_minor:
            overall = BalanceStatus.MINOR_IMBALANCE.value
            is_confounded = False
        else:
            overall = BalanceStatus.BALANCED.value
            is_confounded = False
            diagnostics.append(
                "Randomization balance verified. Covariates are balanced across cohorts."
            )

        return BalanceDiagnostics(
            overall_status=overall,
            is_confounded=is_confounded,
            features=features,
            diagnostics=diagnostics,
        )

    def _evaluate_data_quality(
        self, db: Session, cases: list[RecoveryCase]
    ) -> DataQualityReport:
        """Evaluates prediction and outcome data quality for the experiment cohort."""
        if not cases:
            return DataQualityReport(
                data_quality_status="CLEAN",
                missing_outcomes=0,
                missing_predictions=0,
                diagnostics=["Zero observations in population."],
            )

        missing_outcomes = sum(
            1
            for c in cases
            if not c.resolved_at
            and c.status
            in (RecoveryCaseStatus.RECOVERED.value, RecoveryCaseStatus.CLOSED.value)
        )
        missing_predictions = 0

        # Check prediction linkages
        case_ids = [c.id for c in cases]
        pred_count = (
            db.query(MLPrediction)
            .filter(MLPrediction.recovery_case_id.in_(case_ids))
            .count()
        )
        if pred_count < len(cases):
            missing_predictions = len(cases) - pred_count

        diagnostics = []
        if missing_outcomes > 0:
            diagnostics.append(
                f"Detected {missing_outcomes} cases with missing resolution timestamps."
            )
        if missing_predictions > 0:
            diagnostics.append(
                f"Detected {missing_predictions} cases without associated ML prediction records."
            )

        if missing_outcomes > (len(cases) * 0.10) or missing_predictions > (
            len(cases) * 0.20
        ):
            dq_status = "DEGRADED"
        elif missing_outcomes > 0 or missing_predictions > 0:
            dq_status = "WARNING"
        else:
            dq_status = "CLEAN"
            diagnostics.append("Telemetry data quality verified clean.")

        return DataQualityReport(
            data_quality_status=dq_status,
            missing_outcomes=missing_outcomes,
            missing_predictions=missing_predictions,
            diagnostics=diagnostics,
        )

    def _evaluate_overlap(
        self, db: Session, current_exp_id: str, pop_def: PopulationDefinition
    ) -> OverlapDiagnostics:
        """Detects if multiple active experiments target overlapping populations."""
        exp_map = self._get_experiments_map(db)
        active_exps = []
        for exp_id, logs in exp_map.items():
            if exp_id == current_exp_id:
                continue
            e = self._reconstruct_experiment(exp_id, logs)
            if e and e["status"] == ExperimentStatus.RUNNING.value:
                active_exps.append(e)

        conflicting_ids = []
        diagnostics = []

        for a in active_exps:
            a_pop: PopulationDefinition = a["population_definition"]
            # Check overlap: if filters match or both target broad populations
            risk_overlap = (
                not pop_def.risk_tier
                or not a_pop.risk_tier
                or pop_def.risk_tier == a_pop.risk_tier
            )
            reason_overlap = (
                not pop_def.failure_reason
                or not a_pop.failure_reason
                or pop_def.failure_reason == a_pop.failure_reason
            )

            if risk_overlap and reason_overlap:
                conflicting_ids.append(a["experiment_id"])
                diagnostics.append(
                    f"Population overlaps with active experiment '{a['name']}' ({a['experiment_id']})."
                )

        has_overlap = len(conflicting_ids) > 0
        if not has_overlap:
            diagnostics.append("No active experiment population interference detected.")

        return OverlapDiagnostics(
            has_overlap=has_overlap,
            conflicting_experiment_ids=conflicting_ids,
            diagnostics=diagnostics,
        )

    def _evaluate_stopping_rules(
        self,
        causal_effect: CausalEffectEstimate,
        statistical_test: StatisticalTestResult,
        is_model_degraded: bool,
        data_quality: DataQualityReport,
        overlap: OverlapDiagnostics,
    ) -> StoppingDiagnostics:
        """Evaluates automated stopping guardrails."""
        stop_reasons = []

        if (
            causal_effect.absolute_treatment_effect is not None
            and causal_effect.absolute_treatment_effect <= -0.05
        ):
            stop_reasons.append(
                f"Treatment recovery rate trails control by {abs(causal_effect.absolute_treatment_effect) * 100:.1f}% (<= -5.0%)."
            )

        if (
            statistical_test.confidence_interval_high is not None
            and statistical_test.confidence_interval_high < 0.0
            and statistical_test.statistically_significant
        ):
            stop_reasons.append(
                "95% Confidence Interval upper bound is strictly negative, indicating statistically confirmed underperformance."
            )

        if is_model_degraded:
            stop_reasons.append("Underlying ML model governance is DEGRADED.")

        if data_quality.data_quality_status == "DEGRADED":
            stop_reasons.append("Telemetry data quality is DEGRADED.")

        if overlap.has_overlap:
            stop_reasons.append(
                "Severe population overlap detected with another active experiment."
            )

        return StoppingDiagnostics(
            stop_recommended=len(stop_reasons) > 0,
            reasons=stop_reasons,
        )

    def _determine_decision_and_evidence(
        self,
        sample_size: int,
        ctrl_sample: int,
        trt_sample: int,
        causal_effect: CausalEffectEstimate,
        stat_test: StatisticalTestResult,
        balance: BalanceDiagnostics,
        stopping: StoppingDiagnostics,
        experiment_status: str,
    ) -> ExperimentDecisionResult:
        """Determines evidence level (LEVEL_0..LEVEL_3) and deterministic governance recommendation."""
        diagnostics = []

        # 1. Evidence Level Classification
        if (
            sample_size < MIN_TOTAL_SAMPLE_SIZE
            or ctrl_sample < MIN_COHORT_SAMPLE_SIZE
            or trt_sample < MIN_COHORT_SAMPLE_SIZE
        ):
            evidence_level = CausalEvidenceLevel.LEVEL_0.value
            diagnostics.append(
                f"Cohort sample size is insufficient (Total: {sample_size}/{MIN_TOTAL_SAMPLE_SIZE}, "
                f"Control: {ctrl_sample}/{MIN_COHORT_SAMPLE_SIZE}, Treatment: {trt_sample}/{MIN_COHORT_SAMPLE_SIZE})."
            )
        elif balance.is_confounded or not stat_test.statistically_significant:
            evidence_level = CausalEvidenceLevel.LEVEL_1.value
            if balance.is_confounded:
                diagnostics.append(
                    "Major covariate imbalance detected; observed differences may be confounded."
                )
            else:
                diagnostics.append(
                    "Difference between cohorts is not statistically significant (p >= 0.05)."
                )
        elif (
            balance.overall_status == BalanceStatus.MINOR_IMBALANCE.value
            or experiment_status
            not in (
                ExperimentStatus.RUNNING.value,
                ExperimentStatus.COMPLETED.value,
            )
        ):
            evidence_level = CausalEvidenceLevel.LEVEL_2.value
            diagnostics.append(
                "Statistically significant difference observed with minor balance bounds."
            )
        else:
            evidence_level = CausalEvidenceLevel.LEVEL_3.value
            diagnostics.append(
                "Controlled experiment evidence: statistically significant difference observed in a balanced cohort."
            )

        # 2. Decision Logic
        if evidence_level == CausalEvidenceLevel.LEVEL_0.value:
            decision = ExperimentDecisionType.INSUFFICIENT_DATA.value
        elif stopping.stop_recommended:
            decision = ExperimentDecisionType.STOP_RECOMMENDED.value
            diagnostics.extend(stopping.reasons)
        elif (
            stat_test.statistically_significant
            and (causal_effect.absolute_treatment_effect or 0) >= 0.02
            and (stat_test.confidence_interval_low or 0) > 0
            and evidence_level
            in (CausalEvidenceLevel.LEVEL_2.value, CausalEvidenceLevel.LEVEL_3.value)
        ):
            decision = ExperimentDecisionType.PROMOTE_TO_REVIEW.value
            diagnostics.append(
                "Experiment results demonstrate statistically significant positive uplift and are eligible for governance review."
            )
        else:
            decision = ExperimentDecisionType.CONTINUE.value
            diagnostics.append("Experiment continues to accumulate observations.")

        ci_dict = {
            "low": stat_test.confidence_interval_low,
            "high": stat_test.confidence_interval_high,
        }

        return ExperimentDecisionResult(
            decision=decision,
            evidence_level=evidence_level,
            statistically_significant=stat_test.statistically_significant,
            absolute_uplift=causal_effect.absolute_treatment_effect,
            p_value=stat_test.p_value,
            confidence_interval=ci_dict,
            diagnostics=diagnostics,
        )

    def _to_response_dto(
        self, exp_data: dict[str, Any], sample_size: int = 0
    ) -> ExperimentResponse:
        """Converts internal reconstructed dict to response DTO with zero PII."""
        return ExperimentResponse(
            experiment_id=exp_data["experiment_id"],
            name=exp_data["name"],
            description=exp_data.get("description"),
            status=exp_data["status"],
            treatment_strategy=exp_data["treatment_strategy"],
            control_strategy=exp_data["control_strategy"],
            allocation_percentage=exp_data["allocation_percentage"],
            population_definition=exp_data["population_definition"],
            model_version=exp_data["model_version"],
            created_by=exp_data["created_by"],
            created_at=exp_data["created_at"],
            started_at=exp_data.get("started_at"),
            ended_at=exp_data.get("ended_at"),
            runtime_hours=exp_data.get("runtime_hours"),
            sample_size=sample_size,
            notes=exp_data.get("notes"),
            observational_disclaimer=(
                "Observational causal experimentation intelligence. PolicyEngine remains 100% authoritative."
            ),
        )


experimentation_service = ExperimentationService()
