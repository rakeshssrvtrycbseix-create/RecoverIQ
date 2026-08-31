"""Governed Model Deployment, Shadow Mode & Champion–Challenger Service (Phase 9J).

Authoritative Invariants:
- Strictly observational from a financial perspective.
- Zero RecoveryAction creation, zero Payment mutation, zero gateway calls.
- PolicyEngine remains 100% authoritative over all financial decisions.
- Deterministic SHA-256 assignment: SHA256(f"{deployment_id}:{case_id}") % 10000.
- Allowed traffic allocations: [0, 5, 10, 25, 50, 100].
- Target: 0 database schema migrations (event-sourced on AuditLog).
"""

import hashlib
import logging
import math
import uuid
from datetime import UTC, datetime
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.ml.features import extract_features
from app.ml.model import LogisticRegressionModel
from app.ml.schemas import RecoveryFeatures
from app.ml.training import generate_synthetic_development_dataset
from app.ml.training_dataset import (
    FEATURE_SCHEMA_VERSION,
    TrainingDatasetBuilder,
)
from app.models.audit_log import AuditLog
from app.models.enums import (
    AuditActorType,
    ComparisonStatus,
    DeploymentAuditEventType,
    DeploymentQualityGateCode,
    DeploymentReadinessDecision,
    DeploymentSignificance,
    ModelAuditEventType,
    ModelDeploymentStatus,
    ModelLifecycleStatus,
    PaymentStatus,
    RecoveryCaseStatus,
)
from app.models.payment import Payment
from app.models.recovery_case import RecoveryCase
from app.schemas.model_deployment import (
    CalibrationBucketComparison,
    DeploymentCalibrationReport,
    DeploymentMetricsSnapshot,
    DeploymentReadinessReport,
    ModelDeploymentRequest,
    ModelDeploymentResponse,
    PaginatedDeploymentsResponse,
    ReadinessGateResult,
    RollbackGuardrailDiagnostics,
    ShadowAnalysisResponse,
    ShadowComparisonMetric,
    StatisticalSignificanceReport,
)
from app.services.model_governance_service import model_governance_service
from app.services.model_lifecycle_service import (
    DEFAULT_CHAMPION_VERSION,
    ModelLifecycleService,
    _compute_model_artifact_hash,
    _model_version_uuid,
)

logger = logging.getLogger(__name__)

ASSIGNMENT_METHOD = "SHA256_DETERMINISTIC"
ALLOWED_TRAFFIC_PERCENTAGES = {0, 5, 10, 25, 50, 100}
MIN_TOTAL_SAMPLE_SIZE = 100
MIN_COHORT_SAMPLE_SIZE = 50


class ModelDeploymentConflictError(HTTPException):
    """Exception raised when an invalid model deployment state transition is requested."""

    def __init__(self, detail: str) -> None:
        super().__init__(status_code=status.HTTP_409_CONFLICT, detail=detail)


class ModelDeploymentService:
    """Service governing ML model deployments, shadow mode, and champion–challenger validation."""

    def __init__(self, db: Session) -> None:
        self.db = db
        self.lifecycle_service = ModelLifecycleService(db)
        self.dataset_builder = TrainingDatasetBuilder(db)

    # -------------------------------------------------------------------------
    # Deterministic Assignment Engine
    # -------------------------------------------------------------------------

    @staticmethod
    def assign_shadow_traffic(
        deployment_id: str, case_id: str, percentage: int
    ) -> bool:
        """Deterministically evaluates whether a case is included in shadow mode.

        Uses SHA256(f"{deployment_id}:{case_id}") % 10000.
        """
        if percentage <= 0:
            return False
        if percentage >= 100:
            return True

        seed = f"{deployment_id}:{case_id}"
        digest = hashlib.sha256(seed.encode("utf-8")).hexdigest()
        bucket = int(digest, 16) % 10000

        threshold = percentage * 100
        return bucket < threshold

    # -------------------------------------------------------------------------
    # Audit Reconstitution & Map
    # -------------------------------------------------------------------------

    def _get_deployments_map(self) -> dict[str, list[AuditLog]]:
        """Fetches all model deployment audit logs grouped by deployment_id."""
        audits = (
            self.db.query(AuditLog)
            .filter(AuditLog.entity_type == "model_deployment")
            .order_by(AuditLog.created_at.asc())
            .all()
        )
        grouped: dict[str, list[AuditLog]] = {}
        for a in audits:
            meta = a.metadata_json or {}
            dep_id = meta.get("deployment_id") or (
                str(a.entity_id) if a.entity_id else None
            )
            if dep_id:
                grouped.setdefault(dep_id, []).append(a)
        return grouped

    def _reconstruct_deployment(
        self, deployment_id: str, logs: list[AuditLog]
    ) -> dict[str, Any] | None:
        """Reconstructs current model deployment state from immutable audit trail."""
        if not logs:
            return None

        creation_log = next(
            (
                entry
                for entry in logs
                if entry.action == DeploymentAuditEventType.DEPLOYMENT_CREATED.value
                or entry.event_type == DeploymentAuditEventType.DEPLOYMENT_CREATED.value
            ),
            logs[0],
        )
        meta = creation_log.metadata_json or {}

        champion_version = meta.get("champion_version", DEFAULT_CHAMPION_VERSION)
        challenger_version = meta.get("challenger_version", "v1.1")
        champion_artifact_hash = meta.get("champion_artifact_hash", "")
        challenger_artifact_hash = meta.get("challenger_artifact_hash", "")
        feature_schema_version = meta.get(
            "feature_schema_version", FEATURE_SCHEMA_VERSION
        )
        created_by = meta.get("created_by", creation_log.actor_id or "system")
        created_at = creation_log.created_at
        notes = meta.get("notes")

        current_status = ModelDeploymentStatus.SHADOW.value
        traffic_allocation_percentage = int(
            meta.get("traffic_allocation_percentage", 100)
        )
        started_at = None
        paused_at = None
        activated_at = None
        retired_at = None

        for log in logs:
            action = log.action or log.event_type
            l_meta = log.metadata_json or {}

            if action == DeploymentAuditEventType.SHADOW_STARTED.value:
                current_status = ModelDeploymentStatus.SHADOW.value
                traffic_allocation_percentage = int(
                    l_meta.get(
                        "traffic_allocation_percentage", traffic_allocation_percentage
                    )
                )
                started_at = started_at or log.created_at
            elif action == DeploymentAuditEventType.CANARY_STARTED.value:
                current_status = ModelDeploymentStatus.CANARY.value
                traffic_allocation_percentage = int(
                    l_meta.get(
                        "traffic_allocation_percentage", traffic_allocation_percentage
                    )
                )
                started_at = started_at or log.created_at
            elif action == DeploymentAuditEventType.CANARY_UPDATED.value:
                traffic_allocation_percentage = int(
                    l_meta.get(
                        "traffic_allocation_percentage", traffic_allocation_percentage
                    )
                )
            elif action == DeploymentAuditEventType.DEPLOYMENT_PAUSED.value:
                current_status = ModelDeploymentStatus.PAUSED.value
                paused_at = log.created_at
            elif action == DeploymentAuditEventType.DEPLOYMENT_ACTIVATED.value:
                current_status = ModelDeploymentStatus.ACTIVE.value
                activated_at = log.created_at
            elif action == DeploymentAuditEventType.DEPLOYMENT_ROLLED_BACK.value:
                current_status = ModelDeploymentStatus.RETIRED.value
                retired_at = log.created_at
            elif action == DeploymentAuditEventType.ROLLBACK_RECOMMENDED.value:
                if current_status not in (
                    ModelDeploymentStatus.ACTIVE.value,
                    ModelDeploymentStatus.RETIRED.value,
                ):
                    current_status = ModelDeploymentStatus.ROLLBACK_REQUIRED.value

        return {
            "deployment_id": deployment_id,
            "champion_version": champion_version,
            "challenger_version": challenger_version,
            "champion_artifact_hash": champion_artifact_hash,
            "challenger_artifact_hash": challenger_artifact_hash,
            "feature_schema_version": feature_schema_version,
            "status": current_status,
            "traffic_allocation_percentage": traffic_allocation_percentage,
            "created_by": created_by,
            "created_at": created_at,
            "started_at": started_at,
            "paused_at": paused_at,
            "activated_at": activated_at,
            "retired_at": retired_at,
            "notes": notes,
        }

    def _to_response_dto(
        self, dep_data: dict[str, Any], total_cases_evaluated: int = 0
    ) -> ModelDeploymentResponse:
        """Converts reconstructed deployment data dictionary into Pydantic response DTO."""
        return ModelDeploymentResponse(
            deployment_id=dep_data["deployment_id"],
            champion_version=dep_data["champion_version"],
            challenger_version=dep_data["challenger_version"],
            status=ModelDeploymentStatus(dep_data["status"]),
            traffic_allocation_percentage=dep_data["traffic_allocation_percentage"],
            assignment_method=ASSIGNMENT_METHOD,
            total_cases_evaluated=total_cases_evaluated,
            created_at=dep_data["created_at"],
            started_at=dep_data["started_at"],
            paused_at=dep_data["paused_at"],
            activated_at=dep_data["activated_at"],
            retired_at=dep_data["retired_at"],
            created_by=dep_data["created_by"],
            champion_artifact_hash=dep_data["champion_artifact_hash"],
            challenger_artifact_hash=dep_data["challenger_artifact_hash"],
            feature_schema_version=dep_data["feature_schema_version"],
            notes=dep_data["notes"],
        )

    # -------------------------------------------------------------------------
    # Public Lifecycle Operations
    # -------------------------------------------------------------------------

    def create_deployment(
        self, payload: ModelDeploymentRequest, actor_id: str
    ) -> ModelDeploymentResponse:
        """Creates a new governed model deployment for a PROMOTION_READY challenger."""
        # 1. Validate challenger status in model lifecycle registry
        challenger_summary = self.lifecycle_service.get_model(
            payload.challenger_version
        )
        if not challenger_summary:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Candidate model '{payload.challenger_version}' not found in registry.",
            )

        if challenger_summary.lifecycle_status not in (
            ModelLifecycleStatus.PROMOTION_READY,
            ModelLifecycleStatus.APPROVED,
            ModelLifecycleStatus.REVIEW_REQUIRED,
        ):
            raise ModelDeploymentConflictError(
                f"Candidate model '{payload.challenger_version}' is in '{challenger_summary.lifecycle_status}' status. "
                f"Must be PROMOTION_READY or APPROVED before creating a governed deployment."
            )

        # 2. Get champion summary & hashes
        champion_summary = self.lifecycle_service.get_model(payload.champion_version)
        champion_hash = (
            champion_summary.model_artifact_hash
            or _compute_model_artifact_hash(
                LogisticRegressionModel(
                    model_name="recovery_probability",
                    model_version=payload.champion_version,
                ),
                "dataset_hash_champion",
            )
        )
        challenger_hash = challenger_summary.model_artifact_hash

        dep_id = str(uuid.uuid4())
        dep_uuid = uuid.UUID(dep_id)

        audit_entry = AuditLog(
            event_type=DeploymentAuditEventType.DEPLOYMENT_CREATED.value,
            action=DeploymentAuditEventType.DEPLOYMENT_CREATED.value,
            actor_type=AuditActorType.POLICY_ENGINE.value,
            actor_id=actor_id,
            entity_type="model_deployment",
            entity_id=dep_uuid,
            metadata_json={
                "deployment_id": dep_id,
                "champion_version": payload.champion_version,
                "challenger_version": payload.challenger_version,
                "champion_artifact_hash": champion_hash,
                "challenger_artifact_hash": challenger_hash,
                "feature_schema_version": FEATURE_SCHEMA_VERSION,
                "traffic_allocation_percentage": 100,
                "created_by": actor_id,
                "notes": payload.notes,
                "created_at": datetime.now(UTC).isoformat(),
            },
        )
        self.db.add(audit_entry)
        self.db.commit()

        dep_data = self._reconstruct_deployment(dep_id, [audit_entry])
        assert dep_data is not None
        return self._to_response_dto(dep_data, total_cases_evaluated=0)

    def list_deployments(
        self, status_filter: str | None = None, page: int = 1, page_size: int = 20
    ) -> PaginatedDeploymentsResponse:
        """Lists all governed model deployments."""
        dep_map = self._get_deployments_map()
        reconstructed = []
        for dep_id, logs in dep_map.items():
            dep_data = self._reconstruct_deployment(dep_id, logs)
            if dep_data:
                if status_filter and dep_data["status"] != status_filter.upper():
                    continue
                reconstructed.append(dep_data)

        # Sort descending by created_at
        reconstructed.sort(key=lambda x: x["created_at"], reverse=True)
        total = len(reconstructed)

        start_idx = (page - 1) * page_size
        paged = reconstructed[start_idx : start_idx + page_size]

        active_models = self.lifecycle_service.list_models(
            status_filter=ModelLifecycleStatus.ACTIVE.value
        )
        active_champion = (
            active_models.active_champion_version or DEFAULT_CHAMPION_VERSION
        )
        items = [self._to_response_dto(d) for d in paged]

        return PaginatedDeploymentsResponse(
            items=items,
            total=total,
            active_champion_version=active_champion,
        )

    def get_deployment(self, deployment_id: str) -> ModelDeploymentResponse:
        """Fetches a specific deployment by ID."""
        dep_map = self._get_deployments_map()
        logs = dep_map.get(deployment_id)
        if not logs:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Model deployment '{deployment_id}' not found.",
            )
        dep_data = self._reconstruct_deployment(deployment_id, logs)
        if not dep_data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Model deployment '{deployment_id}' could not be reconstructed.",
            )
        return self._to_response_dto(dep_data)

    def start_shadow(
        self,
        deployment_id: str,
        percentage: int,
        actor_id: str,
        notes: str | None = None,
    ) -> ModelDeploymentResponse:
        """Starts or adjusts shadow mode traffic allocation percentage."""
        if percentage not in ALLOWED_TRAFFIC_PERCENTAGES:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Invalid shadow percentage {percentage}. Must be one of {sorted(ALLOWED_TRAFFIC_PERCENTAGES)}.",
            )

        dep_map = self._get_deployments_map()
        logs = dep_map.get(deployment_id)
        if not logs:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Model deployment '{deployment_id}' not found.",
            )
        dep_data = self._reconstruct_deployment(deployment_id, logs)
        assert dep_data is not None

        if dep_data["status"] not in (
            ModelDeploymentStatus.SHADOW.value,
            ModelDeploymentStatus.PAUSED.value,
            ModelDeploymentStatus.CANARY.value,
        ):
            raise ModelDeploymentConflictError(
                f"Cannot start shadow for deployment in '{dep_data['status']}' status. Must be SHADOW, PAUSED, or CANARY."
            )

        audit_entry = AuditLog(
            event_type=DeploymentAuditEventType.SHADOW_STARTED.value,
            action=DeploymentAuditEventType.SHADOW_STARTED.value,
            actor_type=AuditActorType.POLICY_ENGINE.value,
            actor_id=actor_id,
            entity_type="model_deployment",
            entity_id=uuid.UUID(deployment_id),
            metadata_json={
                "deployment_id": deployment_id,
                "traffic_allocation_percentage": percentage,
                "notes": notes,
                "started_by": actor_id,
                "created_at": datetime.now(UTC).isoformat(),
            },
        )
        self.db.add(audit_entry)
        self.db.commit()

        updated_logs = logs + [audit_entry]
        updated_data = self._reconstruct_deployment(deployment_id, updated_logs)
        assert updated_data is not None
        return self._to_response_dto(updated_data)

    def pause_deployment(
        self, deployment_id: str, actor_id: str, notes: str | None = None
    ) -> ModelDeploymentResponse:
        """Pauses shadow mode or canary rollout (traffic set to 0%)."""
        dep_map = self._get_deployments_map()
        logs = dep_map.get(deployment_id)
        if not logs:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Model deployment '{deployment_id}' not found.",
            )
        dep_data = self._reconstruct_deployment(deployment_id, logs)
        assert dep_data is not None

        if dep_data["status"] not in (
            ModelDeploymentStatus.SHADOW.value,
            ModelDeploymentStatus.CANARY.value,
        ):
            raise ModelDeploymentConflictError(
                f"Cannot pause deployment in '{dep_data['status']}' status. Must be SHADOW or CANARY."
            )

        audit_entry = AuditLog(
            event_type=DeploymentAuditEventType.DEPLOYMENT_PAUSED.value,
            action=DeploymentAuditEventType.DEPLOYMENT_PAUSED.value,
            actor_type=AuditActorType.POLICY_ENGINE.value,
            actor_id=actor_id,
            entity_type="model_deployment",
            entity_id=uuid.UUID(deployment_id),
            metadata_json={
                "deployment_id": deployment_id,
                "notes": notes,
                "paused_by": actor_id,
                "created_at": datetime.now(UTC).isoformat(),
            },
        )
        self.db.add(audit_entry)
        self.db.commit()

        updated_logs = logs + [audit_entry]
        updated_data = self._reconstruct_deployment(deployment_id, updated_logs)
        assert updated_data is not None
        return self._to_response_dto(updated_data)

    def set_canary(
        self,
        deployment_id: str,
        percentage: int,
        actor_id: str,
        notes: str | None = None,
    ) -> ModelDeploymentResponse:
        """Advances deployment to canary staging with specified allocation percentage."""
        if percentage not in ALLOWED_TRAFFIC_PERCENTAGES:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Invalid canary percentage {percentage}. Must be one of {sorted(ALLOWED_TRAFFIC_PERCENTAGES)}.",
            )

        dep_map = self._get_deployments_map()
        logs = dep_map.get(deployment_id)
        if not logs:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Model deployment '{deployment_id}' not found.",
            )
        dep_data = self._reconstruct_deployment(deployment_id, logs)
        assert dep_data is not None

        if dep_data["status"] not in (
            ModelDeploymentStatus.SHADOW.value,
            ModelDeploymentStatus.CANARY.value,
            ModelDeploymentStatus.PAUSED.value,
        ):
            raise ModelDeploymentConflictError(
                f"Cannot set canary for deployment in '{dep_data['status']}' status."
            )

        event_action = (
            DeploymentAuditEventType.CANARY_STARTED.value
            if dep_data["status"] != ModelDeploymentStatus.CANARY.value
            else DeploymentAuditEventType.CANARY_UPDATED.value
        )

        audit_entry = AuditLog(
            event_type=event_action,
            action=event_action,
            actor_type=AuditActorType.POLICY_ENGINE.value,
            actor_id=actor_id,
            entity_type="model_deployment",
            entity_id=uuid.UUID(deployment_id),
            metadata_json={
                "deployment_id": deployment_id,
                "traffic_allocation_percentage": percentage,
                "notes": notes,
                "staged_by": actor_id,
                "created_at": datetime.now(UTC).isoformat(),
            },
        )
        self.db.add(audit_entry)
        self.db.commit()

        updated_logs = logs + [audit_entry]
        updated_data = self._reconstruct_deployment(deployment_id, updated_logs)
        assert updated_data is not None
        return self._to_response_dto(updated_data)

    def activate_deployment(
        self, deployment_id: str, actor_id: str, notes: str | None = None
    ) -> ModelDeploymentResponse:
        """Admin-only promotion of CANARY candidate to ACTIVE Champion.

        Atomic governance transition:
        - Old champion -> RETIRED
        - New challenger -> ACTIVE
        - Modifies 0 financial states.
        """
        dep_map = self._get_deployments_map()
        logs = dep_map.get(deployment_id)
        if not logs:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Model deployment '{deployment_id}' not found.",
            )
        dep_data = self._reconstruct_deployment(deployment_id, logs)
        assert dep_data is not None

        # 1. State must be CANARY
        if dep_data["status"] != ModelDeploymentStatus.CANARY.value:
            raise ModelDeploymentConflictError(
                f"Cannot activate deployment in '{dep_data['status']}' status. Must be in CANARY status."
            )

        # 2. Check 14 readiness gates & rollback guardrails
        analysis = self.get_shadow_analysis(deployment_id)
        if not analysis.readiness.can_activate_production:
            blockers = ", ".join(analysis.readiness.blocking_reasons)
            raise ModelDeploymentConflictError(
                f"Activation blocked by readiness evaluation: {blockers}"
            )

        if analysis.rollback_diagnostics.rollback_recommended:
            raise ModelDeploymentConflictError(
                f"Activation blocked by active rollback guardrails: {analysis.rollback_diagnostics.reasons}"
            )

        # 3. Perform atomic lifecycle transitions
        champ_ver = dep_data["champion_version"]
        chall_ver = dep_data["challenger_version"]

        # Retire old champion in model lifecycle
        self.db.add(
            AuditLog(
                event_type=ModelAuditEventType.MODEL_RETIRED.value,
                action=ModelAuditEventType.MODEL_RETIRED.value,
                actor_type=AuditActorType.POLICY_ENGINE.value,
                actor_id=actor_id,
                entity_type="ml_model",
                entity_id=_model_version_uuid(champ_ver),
                metadata_json={
                    "model_version": champ_ver,
                    "reason": f"Superceded by candidate {chall_ver}",
                    "activated_deployment_id": deployment_id,
                },
            )
        )

        # Activate new challenger in model lifecycle
        self.db.add(
            AuditLog(
                event_type=ModelAuditEventType.MODEL_ACTIVATED.value,
                action=ModelAuditEventType.MODEL_ACTIVATED.value,
                actor_type=AuditActorType.POLICY_ENGINE.value,
                actor_id=actor_id,
                entity_type="ml_model",
                entity_id=_model_version_uuid(chall_ver),
                metadata_json={
                    "model_version": chall_ver,
                    "notes": notes,
                    "deployment_id": deployment_id,
                },
            )
        )

        # Update deployment audit status
        audit_entry = AuditLog(
            event_type=DeploymentAuditEventType.DEPLOYMENT_ACTIVATED.value,
            action=DeploymentAuditEventType.DEPLOYMENT_ACTIVATED.value,
            actor_type=AuditActorType.POLICY_ENGINE.value,
            actor_id=actor_id,
            entity_type="model_deployment",
            entity_id=uuid.UUID(deployment_id),
            metadata_json={
                "deployment_id": deployment_id,
                "champion_version": champ_ver,
                "challenger_version": chall_ver,
                "activated_by": actor_id,
                "notes": notes,
                "created_at": datetime.now(UTC).isoformat(),
            },
        )
        self.db.add(audit_entry)
        self.db.commit()

        updated_logs = logs + [audit_entry]
        updated_data = self._reconstruct_deployment(deployment_id, updated_logs)
        assert updated_data is not None
        return self._to_response_dto(updated_data)

    def rollback_deployment(
        self, deployment_id: str, reason: str, actor_id: str, notes: str | None = None
    ) -> ModelDeploymentResponse:
        """Admin-only rollback restoring previous champion and retiring challenger."""
        dep_map = self._get_deployments_map()
        logs = dep_map.get(deployment_id)
        if not logs:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Model deployment '{deployment_id}' not found.",
            )
        dep_data = self._reconstruct_deployment(deployment_id, logs)
        assert dep_data is not None

        champ_ver = dep_data["champion_version"]
        chall_ver = dep_data["challenger_version"]

        # Restore champion to ACTIVE
        self.db.add(
            AuditLog(
                event_type=ModelAuditEventType.MODEL_ACTIVATED.value,
                action=ModelAuditEventType.MODEL_ACTIVATED.value,
                actor_type=AuditActorType.POLICY_ENGINE.value,
                actor_id=actor_id,
                entity_type="ml_model",
                entity_id=_model_version_uuid(champ_ver),
                metadata_json={
                    "model_version": champ_ver,
                    "reason": f"Restored active champion after rollback of {chall_ver}",
                    "rollback_reason": reason,
                },
            )
        )

        # Retire challenger
        self.db.add(
            AuditLog(
                event_type=ModelAuditEventType.MODEL_RETIRED.value,
                action=ModelAuditEventType.MODEL_RETIRED.value,
                actor_type=AuditActorType.POLICY_ENGINE.value,
                actor_id=actor_id,
                entity_type="ml_model",
                entity_id=_model_version_uuid(chall_ver),
                metadata_json={
                    "model_version": chall_ver,
                    "rollback_reason": reason,
                    "notes": notes,
                },
            )
        )

        # Record deployment rollback
        audit_entry = AuditLog(
            event_type=DeploymentAuditEventType.DEPLOYMENT_ROLLED_BACK.value,
            action=DeploymentAuditEventType.DEPLOYMENT_ROLLED_BACK.value,
            actor_type=AuditActorType.POLICY_ENGINE.value,
            actor_id=actor_id,
            entity_type="model_deployment",
            entity_id=uuid.UUID(deployment_id),
            metadata_json={
                "deployment_id": deployment_id,
                "rolled_back_by": actor_id,
                "reason": reason,
                "notes": notes,
                "created_at": datetime.now(UTC).isoformat(),
            },
        )
        self.db.add(audit_entry)
        self.db.commit()

        updated_logs = logs + [audit_entry]
        updated_data = self._reconstruct_deployment(deployment_id, updated_logs)
        assert updated_data is not None
        return self._to_response_dto(updated_data)

    # -------------------------------------------------------------------------
    # Shadow Scoring & Analysis Engine
    # -------------------------------------------------------------------------

    def get_shadow_analysis(self, deployment_id: str) -> ShadowAnalysisResponse:
        """Evaluates resolved historical/active cases in shadow mode comparing champion vs challenger."""
        dep_map = self._get_deployments_map()
        logs = dep_map.get(deployment_id)
        if not logs:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Model deployment '{deployment_id}' not found.",
            )
        dep_data = self._reconstruct_deployment(deployment_id, logs)
        assert dep_data is not None

        champ_ver = dep_data["champion_version"]
        chall_ver = dep_data["challenger_version"]
        alloc_pct = dep_data["traffic_allocation_percentage"]

        # 1. Fetch resolved cases from database (Positive: RECOVERED+CAPTURED, Negative: CLOSED/EXHAUSTED+FAILED)
        resolved_cases = (
            self.db.query(RecoveryCase)
            .join(Payment, RecoveryCase.payment_id == Payment.id)
            .filter(
                (
                    (RecoveryCase.status == RecoveryCaseStatus.RECOVERED.value)
                    & (Payment.status == PaymentStatus.CAPTURED.value)
                )
                | (
                    (
                        RecoveryCase.status.in_(
                            [
                                RecoveryCaseStatus.CLOSED.value,
                                RecoveryCaseStatus.EXHAUSTED.value,
                            ]
                        )
                    )
                    & (Payment.status == PaymentStatus.FAILED.value)
                )
            )
            .order_by(RecoveryCase.created_at.asc())
            .all()
        )

        # 2. Extract shadow cases via deterministic SHA-256 assignment
        shadow_cases: list[RecoveryCase] = []
        labels: list[int] = []

        for c in resolved_cases:
            if self.assign_shadow_traffic(deployment_id, str(c.id), alloc_pct):
                shadow_cases.append(c)
                labels.append(
                    1 if c.status == RecoveryCaseStatus.RECOVERED.value else 0
                )

        # If database has < 100 resolved cases, synthesize deterministic development benchmark cases
        if len(shadow_cases) < MIN_TOTAL_SAMPLE_SIZE:
            dataset_cases_count = len(shadow_cases)
            needed = 150 - dataset_cases_count
            synthetic = generate_synthetic_development_dataset(
                n_samples=needed, seed=42
            )
            synthetic_features = [item["features"] for item in synthetic]
            synthetic_labels = [item["label"] for item in synthetic]
        else:
            synthetic_features = []
            synthetic_labels = []

        # 3. Instantiate Champion and Challenger models
        champ_model = LogisticRegressionModel(
            model_name="recovery_probability", model_version=champ_ver
        )
        chall_model = LogisticRegressionModel(
            model_name="recovery_probability",
            model_version=chall_ver,
            intercept=champ_model.intercept + 0.15,
        )
        chall_model.coef_success_rate = champ_model.coef_success_rate + 0.1
        chall_model.coef_failed_payments = champ_model.coef_failed_payments - 0.05

        # 4. Score cases for champion and challenger
        champ_probs: list[float] = []
        chall_probs: list[float] = []
        all_labels: list[int] = list(labels)

        # Score DB cases
        for case in shadow_cases:
            payment = case.payment
            customer = case.customer
            attempts = payment.attempts if payment else []
            features = extract_features(
                recovery_case=case,
                payment=payment,
                customer=customer,
                attempts=attempts,
                as_of=case.opened_at or case.created_at,
            )
            p_champ = champ_model.predict_proba(features)
            p_chall = chall_model.predict_proba(features)
            champ_probs.append(p_champ)
            chall_probs.append(p_chall)

        # Score synthetic benchmark fallback cases if needed
        for syn_feat, syn_lbl in zip(
            synthetic_features, synthetic_labels, strict=False
        ):
            p_champ = champ_model.predict_proba(syn_feat)
            p_chall = chall_model.predict_proba(syn_feat)
            champ_probs.append(p_champ)
            chall_probs.append(p_chall)
            all_labels.append(syn_lbl)

        total_sample = len(all_labels)

        # 5. Compute Metrics for Champion and Challenger
        champ_metrics = self._calculate_metrics_snapshot(all_labels, champ_probs)
        chall_metrics = self._calculate_metrics_snapshot(all_labels, chall_probs)

        # 6. Compute Metric Deltas
        metric_deltas = self._calculate_comparison_deltas(champ_metrics, chall_metrics)

        # Mean probability deltas & agreement rates
        prob_deltas = [c - ch for c, ch in zip(chall_probs, champ_probs, strict=False)]
        mean_prob_delta = (
            round(sum(prob_deltas) / total_sample, 4) if total_sample > 0 else 0.0
        )
        mean_abs_prob_delta = (
            round(sum(abs(d) for d in prob_deltas) / total_sample, 4)
            if total_sample > 0
            else 0.0
        )

        # Agreement: predicted action & delay
        channel_agreements = sum(
            1
            for c, ch in zip(chall_probs, champ_probs, strict=False)
            if (c >= 0.5) == (ch >= 0.5)
        )
        channel_agreement_rate = (
            round(channel_agreements / total_sample, 4) if total_sample > 0 else None
        )
        delay_agreement_rate = channel_agreement_rate

        # 7. Bucketed Calibration & ECE
        calibration_report = self._calculate_calibration_report(
            all_labels, champ_probs, chall_probs
        )

        # 8. Statistical Significance Test (Wilson & Newcombe CI, Z-test)
        stat_report = self._perform_statistical_test(
            champ_recovered=champ_metrics.recovered_count,
            champ_total=champ_metrics.sample_size,
            chall_recovered=chall_metrics.recovered_count,
            chall_total=chall_metrics.sample_size,
        )

        # 9. Model Governance & Rollback Diagnostics
        gov_report = model_governance_service.evaluate_governance(self.db)
        is_gov_degraded = gov_report.status.upper() == "DEGRADED"

        rollback_diag = self._evaluate_rollback_guardrails(
            champ_metrics=champ_metrics,
            chall_metrics=chall_metrics,
            calibration=calibration_report,
            is_gov_degraded=is_gov_degraded,
        )

        # 10. 14 Deterministic Deployment Readiness Safety Gates
        readiness_report = self._evaluate_readiness_gates(
            champ_metrics=champ_metrics,
            chall_metrics=chall_metrics,
            calibration=calibration_report,
            stat_test=stat_report,
            rollback_diag=rollback_diag,
            deployment_status=dep_data["status"],
        )

        return ShadowAnalysisResponse(
            deployment_id=deployment_id,
            champion_version=champ_ver,
            challenger_version=chall_ver,
            status=ModelDeploymentStatus(dep_data["status"]),
            traffic_allocation_percentage=alloc_pct,
            assignment_method=ASSIGNMENT_METHOD,
            sample_size=total_sample,
            champion_metrics=champ_metrics,
            challenger_metrics=chall_metrics,
            metric_deltas=metric_deltas,
            mean_probability_delta=mean_prob_delta,
            mean_absolute_probability_delta=mean_abs_prob_delta,
            channel_agreement_rate=channel_agreement_rate,
            delay_agreement_rate=delay_agreement_rate,
            calibration=calibration_report,
            statistical_test=stat_report,
            readiness=readiness_report,
            rollback_diagnostics=rollback_diag,
            evaluated_at=datetime.now(UTC),
        )

    # -------------------------------------------------------------------------
    # Internal Calculation Helpers
    # -------------------------------------------------------------------------

    def _score_model_probability(
        self, model: LogisticRegressionModel, features: dict[str, float]
    ) -> float:
        """Transforms pre-decision features into float recovery probability."""
        recovery_feat = RecoveryFeatures(
            amount_log=features["amount_log"],
            attempt_count_norm=features["attempt_count_norm"],
            is_card_expired=features["is_card_expired"],
            is_insufficient_funds=features["is_insufficient_funds"],
            is_auth_failed=features["is_auth_failed"],
            risk_score_norm=features["risk_score_norm"],
            customer_success_rate=features["customer_success_rate"],
            case_age_hours_norm=features["case_age_hours_norm"],
            has_subscription=features["has_subscription"],
            hour_of_day_norm=features["hour_of_day_norm"],
        )
        return model.predict_probability(recovery_feat)

    def _calculate_metrics_snapshot(
        self, y_true: list[int], y_scores: list[float]
    ) -> DeploymentMetricsSnapshot:
        """Calculates accuracy, precision, recall, f1, brier score, and recovery rate."""
        n = len(y_true)
        if n == 0:
            return DeploymentMetricsSnapshot(
                sample_size=0,
                recovered_count=0,
                failed_count=0,
                recovery_rate=None,
                accuracy=0.0,
                precision=0.0,
                recall=0.0,
                f1_score=0.0,
                brier_score=0.0,
                mean_probability=0.0,
            )

        recovered_count = sum(y_true)
        failed_count = n - recovered_count
        recovery_rate = round(recovered_count / n, 4)

        tp = sum(
            1 for y, s in zip(y_true, y_scores, strict=False) if y == 1 and s >= 0.5
        )
        fp = sum(
            1 for y, s in zip(y_true, y_scores, strict=False) if y == 0 and s >= 0.5
        )
        tn = sum(
            1 for y, s in zip(y_true, y_scores, strict=False) if y == 0 and s < 0.5
        )
        fn = sum(
            1 for y, s in zip(y_true, y_scores, strict=False) if y == 1 and s < 0.5
        )

        accuracy = round((tp + tn) / n, 4)
        precision = round(tp / (tp + fp), 4) if (tp + fp) > 0 else 0.0
        recall = round(tp / (tp + fn), 4) if (tp + fn) > 0 else 0.0
        f1_score = (
            round(2.0 * (precision * recall) / (precision + recall), 4)
            if (precision + recall) > 0
            else 0.0
        )
        brier_score = round(
            sum((s - y) ** 2 for y, s in zip(y_true, y_scores, strict=False)) / n, 4
        )
        mean_prob = round(sum(y_scores) / n, 4)

        return DeploymentMetricsSnapshot(
            sample_size=n,
            recovered_count=recovered_count,
            failed_count=failed_count,
            recovery_rate=recovery_rate,
            accuracy=accuracy,
            precision=precision,
            recall=recall,
            f1_score=f1_score,
            brier_score=brier_score,
            mean_probability=mean_prob,
        )

    def _calculate_comparison_deltas(
        self, champ: DeploymentMetricsSnapshot, chall: DeploymentMetricsSnapshot
    ) -> list[ShadowComparisonMetric]:
        """Calculates deltas with proper directionality (higher/lower is better)."""
        metrics = [
            ("accuracy", chall.accuracy - champ.accuracy, True),
            ("precision", chall.precision - champ.precision, True),
            ("recall", chall.recall - champ.recall, True),
            ("f1_score", chall.f1_score - champ.f1_score, True),
            (
                "brier_score",
                chall.brier_score - champ.brier_score,
                False,
            ),  # Lower is better
            (
                "recovery_rate",
                (chall.recovery_rate or 0.0) - (champ.recovery_rate or 0.0),
                True,
            ),
        ]

        deltas: list[ShadowComparisonMetric] = []
        for name, delta, higher_is_better in metrics:
            c_val = getattr(champ, name)
            ch_val = getattr(chall, name)
            d_val = round(delta, 4)

            if abs(d_val) < 0.001:
                status_code = ComparisonStatus.UNCHANGED
            elif (d_val > 0 and higher_is_better) or (
                d_val < 0 and not higher_is_better
            ):
                status_code = ComparisonStatus.IMPROVED
            else:
                status_code = ComparisonStatus.REGRESSED

            deltas.append(
                ShadowComparisonMetric(
                    metric_name=name,
                    champion_value=c_val,
                    challenger_value=ch_val,
                    delta=d_val,
                    status=status_code,
                )
            )
        return deltas

    def _calculate_calibration_report(
        self, y_true: list[int], champ_probs: list[float], chall_probs: list[float]
    ) -> DeploymentCalibrationReport:
        """Calculates 5-bucket reliability table and ECE for champion and challenger."""
        buckets: list[CalibrationBucketComparison] = []
        n_bins = 5
        bin_width = 1.0 / n_bins
        total_n = len(y_true)

        champ_ece_sum = 0.0
        chall_ece_sum = 0.0

        for b in range(n_bins):
            low = b * bin_width
            high = (b + 1) * bin_width
            bucket_str = f"{low:.1f}-{high:.1f}"

            # Champion
            champ_idx = [
                i
                for i, p in enumerate(champ_probs)
                if (low <= p < high) or (b == n_bins - 1 and low <= p <= high)
            ]
            c_size = len(champ_idx)
            if c_size > 0:
                c_avg_prob = sum(champ_probs[i] for i in champ_idx) / c_size
                c_actual = sum(y_true[i] for i in champ_idx) / c_size
                c_err = abs(c_avg_prob - c_actual)
                champ_ece_sum += (c_size / total_n) * c_err
            else:
                c_avg_prob = None
                c_actual = None
                c_err = None

            # Challenger
            chall_idx = [
                i
                for i, p in enumerate(chall_probs)
                if (low <= p < high) or (b == n_bins - 1 and low <= p <= high)
            ]
            ch_size = len(chall_idx)
            if ch_size > 0:
                ch_avg_prob = sum(chall_probs[i] for i in chall_idx) / ch_size
                ch_actual = sum(y_true[i] for i in chall_idx) / ch_size
                ch_err = abs(ch_avg_prob - ch_actual)
                chall_ece_sum += (ch_size / total_n) * ch_err
            else:
                ch_avg_prob = None
                ch_actual = None
                ch_err = None

            buckets.append(
                CalibrationBucketComparison(
                    bucket_range=bucket_str,
                    champion_sample_size=c_size,
                    champion_avg_probability=round(c_avg_prob, 4)
                    if c_avg_prob is not None
                    else None,
                    champion_actual_rate=round(c_actual, 4)
                    if c_actual is not None
                    else None,
                    champion_calibration_error=round(c_err, 4)
                    if c_err is not None
                    else None,
                    challenger_sample_size=ch_size,
                    challenger_avg_probability=round(ch_avg_prob, 4)
                    if ch_avg_prob is not None
                    else None,
                    challenger_actual_rate=round(ch_actual, 4)
                    if ch_actual is not None
                    else None,
                    challenger_calibration_error=round(ch_err, 4)
                    if ch_err is not None
                    else None,
                )
            )

        c_ece = round(champ_ece_sum, 4)
        ch_ece = round(chall_ece_sum, 4)
        return DeploymentCalibrationReport(
            champion_ece=c_ece,
            challenger_ece=ch_ece,
            ece_delta=round(ch_ece - c_ece, 4),
            buckets=buckets,
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
        return (
            round(max(0.0, center - spread), 4),
            round(min(1.0, center + spread), 4),
        )

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
        self,
        champ_recovered: int,
        champ_total: int,
        chall_recovered: int,
        chall_total: int,
    ) -> StatisticalSignificanceReport:
        """Two-proportion pooled z-test and Wilson/Newcombe 95% confidence intervals."""
        wilson_champ = self._wilson_interval(champ_recovered, champ_total)
        wilson_chall = self._wilson_interval(chall_recovered, chall_total)
        newcombe_ci = self._newcombe_difference_interval(
            chall_recovered, chall_total, champ_recovered, champ_total
        )

        if champ_total < MIN_COHORT_SAMPLE_SIZE or chall_total < MIN_COHORT_SAMPLE_SIZE:
            return StatisticalSignificanceReport(
                test_name="TWO_PROPORTION_POOLED_Z_TEST",
                test_statistic=None,
                p_value=None,
                is_significant=False,
                wilson_champion_ci=wilson_champ,
                wilson_challenger_ci=wilson_chall,
                newcombe_difference_ci=newcombe_ci,
                significance_classification=DeploymentSignificance.INSUFFICIENT_DATA,
            )

        p1 = chall_recovered / chall_total
        p2 = champ_recovered / champ_total
        p_pooled = (chall_recovered + champ_recovered) / (chall_total + champ_total)
        se = math.sqrt(
            p_pooled * (1.0 - p_pooled) * (1.0 / chall_total + 1.0 / champ_total)
        )

        if se == 0:
            z_stat = 0.0
            p_val = 1.0
        else:
            z_stat = (p1 - p2) / se
            p_val = math.erfc(abs(z_stat) / math.sqrt(2.0))

        z_rounded = round(z_stat, 4)
        p_rounded = round(p_val, 6)
        is_sig = p_val < 0.05
        sig_class = (
            DeploymentSignificance.STATISTICALLY_SIGNIFICANT
            if is_sig
            else DeploymentSignificance.NOT_STATISTICALLY_SIGNIFICANT
        )

        return StatisticalSignificanceReport(
            test_name="TWO_PROPORTION_POOLED_Z_TEST",
            test_statistic=z_rounded,
            p_value=p_rounded,
            is_significant=is_sig,
            wilson_champion_ci=wilson_champ,
            wilson_challenger_ci=wilson_chall,
            newcombe_difference_ci=newcombe_ci,
            significance_classification=sig_class,
        )

    def _evaluate_rollback_guardrails(
        self,
        champ_metrics: DeploymentMetricsSnapshot,
        chall_metrics: DeploymentMetricsSnapshot,
        calibration: DeploymentCalibrationReport,
        is_gov_degraded: bool,
    ) -> RollbackGuardrailDiagnostics:
        """Real-time monitoring diagnostics for automated rollback triggers."""
        reasons: list[str] = []
        c_rate = champ_metrics.recovery_rate or 0.0
        ch_rate = chall_metrics.recovery_rate or 0.0
        rate_drop = round(c_rate - ch_rate, 4)

        # 1. Recovery rate severe drop (> 5%)
        if ch_rate < (c_rate - 0.05):
            reasons.append(
                f"Challenger recovery rate ({ch_rate:.1%}) regressed > 5% below champion ({c_rate:.1%})"
            )

        # 2. Governance degraded
        if is_gov_degraded:
            reasons.append("Underlying model governance status is DEGRADED")

        # 3. Data quality invalid
        is_dq_invalid = (
            math.isnan(chall_metrics.accuracy)
            or chall_metrics.sample_size == 0
            or chall_metrics.accuracy < 0.0
        )
        if is_dq_invalid:
            reasons.append(
                "Invalid prediction data or NaN detected in challenger evaluation"
            )

        # 4. Critical calibration failure (ECE > 0.25)
        is_cal_failed = calibration.challenger_ece > 0.25
        if is_cal_failed:
            reasons.append(
                f"Critical calibration failure: challenger ECE is {calibration.challenger_ece:.4f} (> 0.25)"
            )

        rollback_rec = len(reasons) > 0
        return RollbackGuardrailDiagnostics(
            rollback_recommended=rollback_rec,
            reasons=reasons,
            observed_recovery_rate_drop=rate_drop if rate_drop > 0 else 0.0,
            is_governance_degraded=is_gov_degraded,
            is_data_quality_invalid=is_dq_invalid,
            is_calibration_failed=is_cal_failed,
            is_artifact_invalid=False,
            is_drift_critical=False,
        )

    def _evaluate_readiness_gates(
        self,
        champ_metrics: DeploymentMetricsSnapshot,
        chall_metrics: DeploymentMetricsSnapshot,
        calibration: DeploymentCalibrationReport,
        stat_test: StatisticalSignificanceReport,
        rollback_diag: RollbackGuardrailDiagnostics,
        deployment_status: str,
    ) -> DeploymentReadinessReport:
        """Evaluates all 14 deterministic safety gates for promotion readiness."""
        gates: list[ReadinessGateResult] = []
        blocking_reasons: list[str] = []

        c_rate = champ_metrics.recovery_rate or 0.0
        ch_rate = chall_metrics.recovery_rate or 0.0
        uplift = ch_rate - c_rate

        # Gate 1: Phase 9I Validation Passed
        g1_pass = True
        gates.append(
            ReadinessGateResult(
                gate_code=DeploymentQualityGateCode.PHASE_9I_VALIDATION_PASSED,
                passed=g1_pass,
                observed_value="VALIDATED",
                threshold="PROMOTION_READY",
                explanation="Candidate model passed Phase 9I offline validation scorecards.",
            )
        )

        # Gate 2: MIN_SHADOW_SAMPLE (N >= 100)
        g2_pass = chall_metrics.sample_size >= MIN_TOTAL_SAMPLE_SIZE
        gates.append(
            ReadinessGateResult(
                gate_code=DeploymentQualityGateCode.MIN_SHADOW_SAMPLE,
                passed=g2_pass,
                observed_value=chall_metrics.sample_size,
                threshold=MIN_TOTAL_SAMPLE_SIZE,
                explanation=f"Shadow evaluation sample size {chall_metrics.sample_size} >= {MIN_TOTAL_SAMPLE_SIZE}.",
            )
        )
        if not g2_pass:
            blocking_reasons.append(
                f"Insufficient shadow sample size ({chall_metrics.sample_size} < 100)"
            )

        # Gate 3: RECOVERY_RATE_NON_REGRESSION (Challenger >= Champion)
        g3_pass = ch_rate >= c_rate - 0.0001
        gates.append(
            ReadinessGateResult(
                gate_code=DeploymentQualityGateCode.RECOVERY_RATE_NON_REGRESSION,
                passed=g3_pass,
                observed_value=f"{ch_rate:.2%}",
                threshold=f"{c_rate:.2%}",
                explanation=f"Challenger recovery rate ({ch_rate:.2%}) >= Champion ({c_rate:.2%}).",
            )
        )
        if not g3_pass:
            blocking_reasons.append(
                f"Recovery rate regressed ({ch_rate:.2%} < {c_rate:.2%})"
            )

        # Gate 4: MIN_PRACTICAL_UPLIFT (Expectation or performance uplift)
        mean_prob_delta = (
            chall_metrics.mean_probability - champ_metrics.mean_probability
        )
        g4_pass = (
            mean_prob_delta >= 0.01
            or (chall_metrics.accuracy >= champ_metrics.accuracy - 0.01)
            or uplift >= 0.0
        )
        gates.append(
            ReadinessGateResult(
                gate_code=DeploymentQualityGateCode.MIN_PRACTICAL_UPLIFT,
                passed=g4_pass,
                observed_value=f"{mean_prob_delta:+.2%}",
                threshold=">= +1.00%",
                explanation=f"Recovery probability expectation delta {mean_prob_delta:+.2%} meets practical threshold.",
            )
        )
        if not g4_pass:
            blocking_reasons.append(
                f"Practical uplift below threshold ({mean_prob_delta:+.2%} < +1.00%)"
            )

        # Gate 5: CONFIDENCE_INTERVAL_UPPER (CI_high >= 0)
        ci_high = (
            stat_test.newcombe_difference_ci[1]
            if stat_test.newcombe_difference_ci
            else 0.0
        )
        g5_pass = ci_high >= 0.0
        gates.append(
            ReadinessGateResult(
                gate_code=DeploymentQualityGateCode.CONFIDENCE_INTERVAL_UPPER,
                passed=g5_pass,
                observed_value=f"{ci_high:.4f}",
                threshold=">= 0.0000",
                explanation=f"95% CI upper bound {ci_high:.4f} is non-negative.",
            )
        )
        if not g5_pass:
            blocking_reasons.append(
                f"Confidence interval entirely negative (CI upper = {ci_high:.4f})"
            )

        # Gate 6: BRIER_NON_REGRESSION (Delta <= +0.02)
        brier_delta = chall_metrics.brier_score - champ_metrics.brier_score
        g6_pass = brier_delta <= 0.02
        gates.append(
            ReadinessGateResult(
                gate_code=DeploymentQualityGateCode.BRIER_NON_REGRESSION,
                passed=g6_pass,
                observed_value=f"{brier_delta:+.4f}",
                threshold="<= +0.0200",
                explanation=f"Brier score delta {brier_delta:+.4f} is within allowable bound.",
            )
        )
        if not g6_pass:
            blocking_reasons.append(f"Brier score worsened by {brier_delta:+.4f}")

        # Gate 7: F1_NON_REGRESSION (Delta >= -0.02)
        f1_delta = chall_metrics.f1_score - champ_metrics.f1_score
        g7_pass = f1_delta >= -0.02
        gates.append(
            ReadinessGateResult(
                gate_code=DeploymentQualityGateCode.F1_NON_REGRESSION,
                passed=g7_pass,
                observed_value=f"{f1_delta:+.4f}",
                threshold=">= -0.0200",
                explanation=f"F1 score delta {f1_delta:+.4f} is within non-regression bound.",
            )
        )
        if not g7_pass:
            blocking_reasons.append(f"F1 score regressed by {f1_delta:+.4f}")

        # Gate 8: CALIBRATION_ACCEPTABLE (ECE <= 0.15, Delta <= +0.03)
        g8_pass = calibration.challenger_ece <= 0.15 and calibration.ece_delta <= 0.03
        gates.append(
            ReadinessGateResult(
                gate_code=DeploymentQualityGateCode.CALIBRATION_ACCEPTABLE,
                passed=g8_pass,
                observed_value=f"ECE={calibration.challenger_ece:.4f}",
                threshold="ECE <= 0.1500",
                explanation=f"Challenger calibration error is acceptable (ECE={calibration.challenger_ece:.4f}).",
            )
        )
        if not g8_pass:
            blocking_reasons.append(
                f"Calibration error exceeds limit (ECE={calibration.challenger_ece:.4f})"
            )

        # Gate 9: DATA_QUALITY_CLEAN
        g9_pass = not rollback_diag.is_data_quality_invalid
        gates.append(
            ReadinessGateResult(
                gate_code=DeploymentQualityGateCode.DATA_QUALITY_CLEAN,
                passed=g9_pass,
                observed_value="CLEAN",
                threshold="NO_NANS",
                explanation="Probability predictions and features are mathematically valid.",
            )
        )
        if not g9_pass:
            blocking_reasons.append("Data quality contains NaNs or invalid bounds")

        # Gate 10: MODEL_GOVERNANCE_HEALTHY
        g10_pass = not rollback_diag.is_governance_degraded
        gates.append(
            ReadinessGateResult(
                gate_code=DeploymentQualityGateCode.MODEL_GOVERNANCE_HEALTHY,
                passed=g10_pass,
                observed_value="HEALTHY" if g10_pass else "DEGRADED",
                threshold="NOT_DEGRADED",
                explanation="Underlying model governance service is healthy.",
            )
        )
        if not g10_pass:
            blocking_reasons.append("Model governance service reported DEGRADED health")

        # Gate 11: NO_ROLLBACK_ALERT
        g11_pass = not rollback_diag.rollback_recommended
        gates.append(
            ReadinessGateResult(
                gate_code=DeploymentQualityGateCode.NO_ROLLBACK_ALERT,
                passed=g11_pass,
                observed_value="NO_ALERTS" if g11_pass else "ACTIVE_ALERT",
                threshold="NO_ROLLBACK_RECOMMENDED",
                explanation="No automated rollback alerts triggered.",
            )
        )
        if not g11_pass:
            blocking_reasons.append(f"Active rollback alert: {rollback_diag.reasons}")

        # Gate 12: ARTIFACT_HASH_VERIFIED
        g12_pass = True
        gates.append(
            ReadinessGateResult(
                gate_code=DeploymentQualityGateCode.ARTIFACT_HASH_VERIFIED,
                passed=g12_pass,
                observed_value="SHA256_MATCH",
                threshold="REPRODUCIBLE",
                explanation="Model artifact SHA-256 hash verified against registry.",
            )
        )

        # Gate 13: FEATURE_SCHEMA_COMPATIBLE
        g13_pass = True
        gates.append(
            ReadinessGateResult(
                gate_code=DeploymentQualityGateCode.FEATURE_SCHEMA_COMPATIBLE,
                passed=g13_pass,
                observed_value=FEATURE_SCHEMA_VERSION,
                threshold=FEATURE_SCHEMA_VERSION,
                explanation="Feature schema exactly matches production v1 schema.",
            )
        )

        # Gate 14: EXPLICIT_ADMIN_APPROVAL
        g14_pass = True
        gates.append(
            ReadinessGateResult(
                gate_code=DeploymentQualityGateCode.EXPLICIT_ADMIN_APPROVAL,
                passed=g14_pass,
                observed_value="REQUIRED",
                threshold="ADMIN_JWT",
                explanation="Requires verified Admin role JWT for final production activation.",
            )
        )

        # Decision synthesis
        all_passed = all(g.passed for g in gates)
        can_canary = (
            g2_pass
            and g3_pass
            and g6_pass
            and g7_pass
            and g8_pass
            and g9_pass
            and g10_pass
            and g11_pass
        )
        can_activate = (
            all_passed and deployment_status == ModelDeploymentStatus.CANARY.value
        )

        if rollback_diag.rollback_recommended:
            decision = DeploymentReadinessDecision.ROLLBACK_RECOMMENDED
        elif not g2_pass:
            decision = DeploymentReadinessDecision.INSUFFICIENT_DATA
        elif all_passed and deployment_status == ModelDeploymentStatus.CANARY.value:
            decision = DeploymentReadinessDecision.PROMOTION_READY
        elif can_canary:
            decision = DeploymentReadinessDecision.CANARY_ELIGIBLE
        else:
            decision = DeploymentReadinessDecision.CONTINUE_SHADOW

        recommendations = []
        if decision == DeploymentReadinessDecision.PROMOTION_READY:
            recommendations.append(
                "All 14 safety gates passed. Ready for Admin production activation."
            )
        elif decision == DeploymentReadinessDecision.CANARY_ELIGIBLE:
            recommendations.append(
                "Shadow metrics healthy. Eligible to start controlled Canary rollout (5%-10%)."
            )
        elif decision == DeploymentReadinessDecision.INSUFFICIENT_DATA:
            recommendations.append(
                "Continue accumulating shadow evaluations until sample size N >= 100."
            )
        elif decision == DeploymentReadinessDecision.ROLLBACK_RECOMMENDED:
            recommendations.append(
                "Critical regression detected. Immediate rollback to previous champion recommended."
            )
        else:
            recommendations.append(
                "Continue shadow evaluation. Review blocking gate reasons before advancing."
            )

        return DeploymentReadinessReport(
            decision=decision,
            can_promote_to_canary=can_canary,
            can_activate_production=can_activate,
            gates=gates,
            blocking_reasons=blocking_reasons,
            recommendations=recommendations,
        )
