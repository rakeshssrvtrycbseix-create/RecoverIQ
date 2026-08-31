"""REST API Router for Phase 10J: AI/ML Governance, Model Risk Management,

Explainability, Drift Detection & Responsible AI Control Plane.
"""

import logging
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.rate_limiter import rate_limit_mutations, rate_limit_reads
from app.core.security import (
    AuthenticatedUser,
    require_admin,
    require_operator,
    require_viewer,
)
from app.models.enums import (
    EvaluationType,
    GovernanceStage,
    ModelTier,
    OperationalStatus,
)
from app.schemas.ml_governance import (
    CalibrationMetric,
    ComplianceCardGenerateRequest,
    DriftAnalysis,
    DriftAnalysisRequest,
    EvaluationRequest,
    EvaluationRunRequest,
    ExplainabilityGenerateRequest,
    ExplainabilityRecord,
    ExplainabilityReport,
    ExplanationRequest,
    FairnessAudit,
    FairnessAuditRequest,
    FairnessMetric,
    FinancialPathForensics,
    KillSwitchToggleRequest,
    MLGovernanceReport,
    MLGovernanceSummary,
    MLIncident,
    MLIncidentActionRequest,
    MLReadinessGate,
    ModelComplianceCard,
    ModelDriftSummary,
    ModelEvaluation,
    ModelInventoryItem,
    ModelKillSwitch,
    ModelLineage,
    ModelLineageGraph,
    ModelPerformanceMetrics,
    ModelPromotionEvaluation,
    ModelRegistryEntry,
    ModelRiskAssessment,
    ModelRollbackReadiness,
    ModelVersion,
    PromotionApprovalActionRequest,
    PromotionApprovalRequest,
    PromotionEvaluationRequest,
    PromotionRequest,
    ShadowComparison,
    ShadowComparisonRequest,
)
from app.services.ml_governance_service import MLGovernanceService

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/recovery/intelligence/ml-governance",
    tags=["ml-model-governance"],
)


# =============================================================================
# Core Phase 10J Governance Endpoints (Part 18 Specification)
# =============================================================================


@router.get(
    "",
    response_model=MLGovernanceSummary,
    summary="Get ML Governance Control Plane Summary",
    dependencies=[Depends(rate_limit_reads)],
)
@router.get(
    "/summary",
    response_model=MLGovernanceSummary,
    summary="Get ML Governance Control Plane Summary (Alias)",
    dependencies=[Depends(rate_limit_reads)],
)
def get_ml_governance_summary(
    current_user: Annotated[AuthenticatedUser, Depends(require_viewer)],
    db: Annotated[Session, Depends(get_db)],
) -> MLGovernanceSummary:
    """Retrieve high-level executive posture of AI/ML Governance Control Plane."""
    service = MLGovernanceService(db)
    return service.get_summary()


@router.get(
    "/models",
    response_model=list[ModelRegistryEntry],
    summary="List Registered ML Models",
    dependencies=[Depends(rate_limit_reads)],
)
def list_models(
    current_user: Annotated[AuthenticatedUser, Depends(require_viewer)],
    db: Annotated[Session, Depends(get_db)],
) -> list[ModelRegistryEntry]:
    """List all canonical ML models in the deterministic registry."""
    service = MLGovernanceService(db)
    return service.list_models()


@router.get(
    "/models/{model_id}",
    response_model=ModelRegistryEntry,
    summary="Get Model Details",
    dependencies=[Depends(rate_limit_reads)],
)
def get_model(
    model_id: str,
    current_user: Annotated[AuthenticatedUser, Depends(require_viewer)],
    db: Annotated[Session, Depends(get_db)],
) -> ModelRegistryEntry:
    """Retrieve catalog metadata for a specific ML model."""
    service = MLGovernanceService(db)
    return service.get_model(model_id)


@router.get(
    "/models/{model_id}/versions",
    response_model=list[ModelVersion],
    summary="List Model Versions",
    dependencies=[Depends(rate_limit_reads)],
)
def get_model_versions(
    model_id: str,
    current_user: Annotated[AuthenticatedUser, Depends(require_viewer)],
    db: Annotated[Session, Depends(get_db)],
) -> list[ModelVersion]:
    """List immutable version artifact provenance records for a model."""
    service = MLGovernanceService(db)
    return service.get_model_versions(model_id)


@router.get(
    "/models/{model_id}/lineage",
    response_model=ModelLineageGraph,
    summary="Get Model Lineage Graph",
    dependencies=[Depends(rate_limit_reads)],
)
def get_model_lineage(
    model_id: str,
    current_user: Annotated[AuthenticatedUser, Depends(require_viewer)],
    db: Annotated[Session, Depends(get_db)],
    version: str = Query(default="v1.0", description="Model version tag"),
) -> ModelLineageGraph:
    """Retrieve full cryptographic provenance lineage graph for a specific model."""
    service = MLGovernanceService(db)
    return service.get_model_lineage(model_id, version)


@router.get(
    "/models/{model_id}/performance",
    response_model=ModelPerformanceMetrics,
    summary="Get Model Performance Metrics",
    dependencies=[Depends(rate_limit_reads)],
)
def get_model_performance(
    model_id: str,
    current_user: Annotated[AuthenticatedUser, Depends(require_viewer)],
    db: Annotated[Session, Depends(get_db)],
    version: str = Query(default="v1.0", description="Model version tag"),
) -> ModelPerformanceMetrics:
    """Retrieve deterministic validation and live performance metrics."""
    service = MLGovernanceService(db)
    return service.get_performance_metrics(model_id, version)


@router.get(
    "/models/{model_id}/drift",
    response_model=ModelDriftSummary,
    summary="Get Model Drift Surveillance Summary",
    dependencies=[Depends(rate_limit_reads)],
)
def get_model_drift(
    model_id: str,
    current_user: Annotated[AuthenticatedUser, Depends(require_viewer)],
    db: Annotated[Session, Depends(get_db)],
) -> ModelDriftSummary:
    """Retrieve statistical drift metrics (PSI, KS, JS) across all monitored features."""
    service = MLGovernanceService(db)
    return service.calculate_drift(model_id)


@router.get(
    "/models/{model_id}/prediction-drift",
    response_model=dict[str, Any],
    summary="Get Prediction Distribution Drift",
    dependencies=[Depends(rate_limit_reads)],
)
def get_prediction_drift(
    model_id: str,
    current_user: Annotated[AuthenticatedUser, Depends(require_viewer)],
    db: Annotated[Session, Depends(get_db)],
) -> dict[str, Any]:
    """Retrieve prediction probability output distribution drift."""
    service = MLGovernanceService(db)
    return service.calculate_prediction_drift(model_id)


@router.get(
    "/models/{model_id}/concept-drift",
    response_model=dict[str, Any],
    summary="Get Concept Drift Surveillance",
    dependencies=[Depends(rate_limit_reads)],
)
def get_concept_drift(
    model_id: str,
    current_user: Annotated[AuthenticatedUser, Depends(require_viewer)],
    db: Annotated[Session, Depends(get_db)],
) -> dict[str, Any]:
    """Retrieve concept drift metrics tracking input-to-outcome relationship stability."""
    service = MLGovernanceService(db)
    return service.calculate_concept_drift(model_id)


@router.get(
    "/models/{model_id}/explainability",
    response_model=ExplainabilityRecord,
    summary="Get Model Explainability Record",
    dependencies=[Depends(rate_limit_reads)],
)
def get_model_explainability(
    model_id: str,
    current_user: Annotated[AuthenticatedUser, Depends(require_viewer)],
    db: Annotated[Session, Depends(get_db)],
    prediction_ref: str | None = Query(
        default=None, description="Optional prediction reference ID"
    ),
) -> ExplainabilityRecord:
    """Retrieve sanitized SHAP prediction attribution record (Strictly Zero Customer PII)."""
    service = MLGovernanceService(db)
    return service.get_model_explainability(model_id, prediction_ref)


@router.get(
    "/models/{model_id}/fairness",
    response_model=list[FairnessMetric],
    summary="Get Fairness & Responsible AI Metrics",
    dependencies=[Depends(rate_limit_reads)],
)
def get_model_fairness(
    model_id: str,
    current_user: Annotated[AuthenticatedUser, Depends(require_viewer)],
    db: Annotated[Session, Depends(get_db)],
) -> list[FairnessMetric]:
    """Retrieve responsible AI fairness evaluations across synthetic group cohorts."""
    service = MLGovernanceService(db)
    return service.calculate_fairness(model_id)


@router.get(
    "/models/{model_id}/calibration",
    response_model=CalibrationMetric,
    summary="Get Model Calibration & Reliability Curves",
    dependencies=[Depends(rate_limit_reads)],
)
def get_model_calibration(
    model_id: str,
    current_user: Annotated[AuthenticatedUser, Depends(require_viewer)],
    db: Annotated[Session, Depends(get_db)],
) -> CalibrationMetric:
    """Retrieve probability calibration parameters, ECE, Brier score, and reliability curve bins."""
    service = MLGovernanceService(db)
    return service.calculate_calibration(model_id)


@router.get(
    "/models/{model_id}/risk",
    response_model=ModelRiskAssessment,
    summary="Get 10-Factor Model Risk Assessment",
    dependencies=[Depends(rate_limit_reads)],
)
def get_model_risk(
    model_id: str,
    current_user: Annotated[AuthenticatedUser, Depends(require_viewer)],
    db: Annotated[Session, Depends(get_db)],
) -> ModelRiskAssessment:
    """Retrieve comprehensive 10-factor Model Risk Management scorecard."""
    service = MLGovernanceService(db)
    return service.calculate_model_risk(model_id)


@router.get(
    "/models/{model_id}/readiness",
    response_model=list[MLReadinessGate],
    summary="Get Model Readiness Gates",
    dependencies=[Depends(rate_limit_reads)],
)
def get_model_readiness(
    model_id: str,
    current_user: Annotated[AuthenticatedUser, Depends(require_viewer)],
    db: Annotated[Session, Depends(get_db)],
) -> list[MLReadinessGate]:
    """Retrieve all 22 deterministic ML readiness gates."""
    service = MLGovernanceService(db)
    return service.list_readiness_gates()


@router.get(
    "/models/{model_id}/rollback",
    response_model=ModelRollbackReadiness,
    summary="Get Model Rollback Readiness",
    dependencies=[Depends(rate_limit_reads)],
)
def get_model_rollback(
    model_id: str,
    current_user: Annotated[AuthenticatedUser, Depends(require_viewer)],
    db: Annotated[Session, Depends(get_db)],
) -> ModelRollbackReadiness:
    """Evaluate advisory rollback readiness and switchover validation."""
    service = MLGovernanceService(db)
    return service.evaluate_rollback(model_id)


@router.post(
    "/models/{model_id}/evaluate",
    response_model=ModelEvaluation,
    status_code=status.HTTP_201_CREATED,
    summary="Trigger Model Evaluation",
    dependencies=[Depends(rate_limit_mutations)],
)
def evaluate_model(
    model_id: str,
    request: EvaluationRequest,
    current_user: Annotated[AuthenticatedUser, Depends(require_operator)],
    db: Annotated[Session, Depends(get_db)],
    version: str = Query(default="v1.0", description="Target model version"),
) -> ModelEvaluation:
    """Run automated model evaluation benchmark suite."""
    service = MLGovernanceService(db)
    return service.evaluate_model(model_id, version, request, db=db)


@router.post(
    "/models/{model_id}/explain",
    response_model=ExplainabilityRecord,
    status_code=status.HTTP_201_CREATED,
    summary="Generate Sanitized Model Explanation",
    dependencies=[Depends(rate_limit_mutations)],
)
def explain_model(
    model_id: str,
    request: ExplanationRequest,
    current_user: Annotated[AuthenticatedUser, Depends(require_operator)],
    db: Annotated[Session, Depends(get_db)],
) -> ExplainabilityRecord:
    """Generate on-demand sanitized feature attribution explanation."""
    service = MLGovernanceService(db)
    return service.generate_explanation(model_id, request)


@router.post(
    "/models/{model_id}/promotion-evaluation",
    response_model=ModelPromotionEvaluation,
    status_code=status.HTTP_201_CREATED,
    summary="Evaluate Advisory Model Promotion",
    dependencies=[Depends(rate_limit_mutations)],
)
def evaluate_promotion(
    model_id: str,
    request: PromotionEvaluationRequest,
    current_user: Annotated[AuthenticatedUser, Depends(require_operator)],
    db: Annotated[Session, Depends(get_db)],
) -> ModelPromotionEvaluation:
    """Evaluate advisory promotion gates for a candidate model version."""
    service = MLGovernanceService(db)
    return service.evaluate_promotion(
        model_id=model_id,
        candidate_version=request.candidate_version,
        justification=request.justification,
        db=db,
    )


@router.get(
    "/incidents",
    response_model=list[MLIncident],
    summary="List ML Governance Incidents",
    dependencies=[Depends(rate_limit_reads)],
)
def list_incidents(
    current_user: Annotated[AuthenticatedUser, Depends(require_viewer)],
    db: Annotated[Session, Depends(get_db)],
) -> list[MLIncident]:
    """List all event-sourced ML governance incidents."""
    service = MLGovernanceService(db)
    return service.list_ml_incidents()


@router.get(
    "/incidents/{incident_id}",
    response_model=MLIncident,
    summary="Get ML Incident Detail",
    dependencies=[Depends(rate_limit_reads)],
)
def get_incident(
    incident_id: str,
    current_user: Annotated[AuthenticatedUser, Depends(require_viewer)],
    db: Annotated[Session, Depends(get_db)],
) -> MLIncident:
    """Retrieve details for a specific ML governance incident."""
    service = MLGovernanceService(db)
    return service.get_incident(incident_id)


@router.post(
    "/incidents/{incident_id}/acknowledge",
    response_model=MLIncident,
    summary="Acknowledge ML Incident",
    dependencies=[Depends(rate_limit_mutations)],
)
def acknowledge_incident(
    incident_id: str,
    current_user: Annotated[AuthenticatedUser, Depends(require_operator)],
    db: Annotated[Session, Depends(get_db)],
    notes: str | None = Query(default=None, description="Acknowledgment notes"),
) -> MLIncident:
    """Acknowledge an open ML incident (Operator or Admin)."""
    service = MLGovernanceService(db)
    return service.acknowledge_incident(
        incident_id, notes, actor_id=current_user.id, db=db
    )


@router.post(
    "/incidents/{incident_id}/resolve",
    response_model=MLIncident,
    summary="Resolve ML Incident",
    dependencies=[Depends(rate_limit_mutations)],
)
def resolve_incident(
    incident_id: str,
    current_user: Annotated[AuthenticatedUser, Depends(require_admin)],
    db: Annotated[Session, Depends(get_db)],
    notes: str | None = Query(default=None, description="Resolution justification"),
) -> MLIncident:
    """Resolve an ML governance incident (Admin authorization required)."""
    service = MLGovernanceService(db)
    return service.resolve_incident(incident_id, notes, actor_id=current_user.id, db=db)


@router.get(
    "/forensics",
    response_model=FinancialPathForensics,
    summary="Get Financial Path Observational Forensics",
    dependencies=[Depends(rate_limit_reads)],
)
def get_forensics(
    current_user: Annotated[AuthenticatedUser, Depends(require_viewer)],
    db: Annotated[Session, Depends(get_db)],
    trace_id: str | None = Query(default=None, description="Optional trace ID"),
) -> FinancialPathForensics:
    """Observational trace of 6-stage ML recovery decision pipeline (ΔRecoveryAction = 0)."""
    service = MLGovernanceService(db)
    return service.get_financial_path_forensics(trace_id)


@router.get(
    "/readiness-gates",
    response_model=list[MLReadinessGate],
    summary="List 22 ML Readiness Gates",
    dependencies=[Depends(rate_limit_reads)],
)
def list_all_readiness_gates(
    current_user: Annotated[AuthenticatedUser, Depends(require_viewer)],
    db: Annotated[Session, Depends(get_db)],
) -> list[MLReadinessGate]:
    """Retrieve all 22 deterministic ML readiness gates."""
    service = MLGovernanceService(db)
    return service.list_readiness_gates()


@router.get(
    "/report",
    response_model=MLGovernanceReport,
    summary="Generate Signed ML Governance Report",
    dependencies=[Depends(rate_limit_reads)],
)
def get_governance_report(
    current_user: Annotated[AuthenticatedUser, Depends(require_viewer)],
    db: Annotated[Session, Depends(get_db)],
) -> MLGovernanceReport:
    """Generate cryptographically signed, audit-grade ML Governance Report."""
    service = MLGovernanceService(db)
    return service.generate_governance_report(db=db)


# =============================================================================
# Compatibility / Extended Endpoints for Legacy Tests and Tools
# =============================================================================


@router.get(
    "/inventory",
    response_model=list[ModelInventoryItem],
    summary="List Model Inventory Items (Compatibility)",
    dependencies=[Depends(rate_limit_reads)],
)
def list_model_inventory(
    current_user: Annotated[AuthenticatedUser, Depends(require_viewer)],
    db: Annotated[Session, Depends(get_db)],
    tier: ModelTier | None = Query(default=None, description="Filter by model tier"),
    status_filter: OperationalStatus | None = Query(
        default=None, alias="status", description="Filter by operational status"
    ),
    stage: GovernanceStage | None = Query(
        default=None, description="Filter by governance stage"
    ),
) -> list[ModelInventoryItem]:
    """List registered ML model inventory with optional filters."""
    service = MLGovernanceService(db)
    items = service.get_model_inventory()
    if tier:
        items = [m for m in items if m.tier == tier.value]
    if status_filter:
        items = [m for m in items if m.operational_status == status_filter.value]
    if stage:
        items = [m for m in items if m.stage == stage.value]
    return items


@router.get(
    "/lineage/{model_id}",
    response_model=ModelLineage,
    summary="Get Model Lineage Graph (Compatibility)",
    dependencies=[Depends(rate_limit_reads)],
)
def get_legacy_model_lineage(
    model_id: str,
    current_user: Annotated[AuthenticatedUser, Depends(require_viewer)],
    db: Annotated[Session, Depends(get_db)],
) -> ModelLineage:
    """Retrieve legacy model lineage format."""
    service = MLGovernanceService(db)
    graph = service.get_model_lineage(model_id)
    return ModelLineage(
        model_id=graph.model_id,
        version=graph.version,
        nodes=graph.nodes,
        root_hash=graph.root_hash,
    )


@router.get(
    "/evaluations",
    response_model=list[ModelEvaluation],
    summary="List Evaluations (Compatibility)",
    dependencies=[Depends(rate_limit_reads)],
)
def list_evaluations(
    current_user: Annotated[AuthenticatedUser, Depends(require_viewer)],
    db: Annotated[Session, Depends(get_db)],
    model_id: str | None = Query(default=None, description="Filter by model ID"),
    eval_type: EvaluationType | None = Query(
        default=None, description="Filter by evaluation type"
    ),
) -> list[ModelEvaluation]:
    """List evaluations."""
    service = MLGovernanceService(db)
    evals = service.get_evaluations()
    if model_id:
        evals = [e for e in evals if e.model_id == model_id]
    return evals


@router.post(
    "/evaluations/run",
    response_model=ModelEvaluation,
    status_code=status.HTTP_201_CREATED,
    summary="Trigger Evaluation Run (Compatibility)",
    dependencies=[Depends(rate_limit_mutations)],
)
def run_legacy_evaluation(
    request: EvaluationRunRequest,
    current_user: Annotated[AuthenticatedUser, Depends(require_operator)],
    db: Annotated[Session, Depends(get_db)],
) -> ModelEvaluation:
    """Trigger evaluation run."""
    service = MLGovernanceService(db)
    return service.run_evaluation(request, actor_id=current_user.id)


@router.get(
    "/fairness",
    response_model=list[FairnessAudit],
    summary="List Fairness Audits (Compatibility)",
    dependencies=[Depends(rate_limit_reads)],
)
def list_fairness_audits(
    current_user: Annotated[AuthenticatedUser, Depends(require_viewer)],
    db: Annotated[Session, Depends(get_db)],
    model_id: str | None = Query(default=None, description="Filter by model ID"),
) -> list[FairnessAudit]:
    """List fairness audits."""
    service = MLGovernanceService(db)
    audits = service.get_fairness_audits()
    if model_id:
        audits = [a for a in audits if a.model_id == model_id]
    return audits


@router.post(
    "/fairness/audit",
    response_model=FairnessAudit,
    status_code=status.HTTP_201_CREATED,
    summary="Run Fairness Audit (Compatibility)",
    dependencies=[Depends(rate_limit_mutations)],
)
def run_fairness_audit(
    request: FairnessAuditRequest,
    current_user: Annotated[AuthenticatedUser, Depends(require_operator)],
    db: Annotated[Session, Depends(get_db)],
) -> FairnessAudit:
    """Run fairness audit."""
    service = MLGovernanceService(db)
    return service.run_fairness_audit(request, actor_id=current_user.id)


@router.get(
    "/explainability",
    response_model=list[ExplainabilityReport],
    summary="List Explainability Reports (Compatibility)",
    dependencies=[Depends(rate_limit_reads)],
)
def list_explainability_reports(
    current_user: Annotated[AuthenticatedUser, Depends(require_viewer)],
    db: Annotated[Session, Depends(get_db)],
    model_id: str | None = Query(default=None, description="Filter by model ID"),
) -> list[ExplainabilityReport]:
    """List explainability reports."""
    service = MLGovernanceService(db)
    reports = service.get_explainability_reports()
    if model_id:
        reports = [r for r in reports if r.model_id == model_id]
    return reports


@router.post(
    "/explainability/generate",
    response_model=ExplainabilityReport,
    status_code=status.HTTP_201_CREATED,
    summary="Generate Explainability (Compatibility)",
    dependencies=[Depends(rate_limit_mutations)],
)
def generate_explainability(
    request: ExplainabilityGenerateRequest,
    current_user: Annotated[AuthenticatedUser, Depends(require_operator)],
    db: Annotated[Session, Depends(get_db)],
) -> ExplainabilityReport:
    """Generate explainability report."""
    service = MLGovernanceService(db)
    return service.generate_explainability_report(request, actor_id=current_user.id)


@router.get(
    "/drift",
    response_model=list[DriftAnalysis],
    summary="List Drift Analyses (Compatibility)",
    dependencies=[Depends(rate_limit_reads)],
)
def list_drift_analyses(
    current_user: Annotated[AuthenticatedUser, Depends(require_viewer)],
    db: Annotated[Session, Depends(get_db)],
    model_id: str | None = Query(default=None, description="Filter by model ID"),
) -> list[DriftAnalysis]:
    """List drift analyses."""
    service = MLGovernanceService(db)
    analyses = service.get_drift_analyses()
    if model_id:
        analyses = [d for d in analyses if d.model_id == model_id]
    return analyses


@router.post(
    "/drift/analyze",
    response_model=DriftAnalysis,
    status_code=status.HTTP_201_CREATED,
    summary="Run Drift Analysis (Compatibility)",
    dependencies=[Depends(rate_limit_mutations)],
)
def run_drift_analysis(
    request: DriftAnalysisRequest,
    current_user: Annotated[AuthenticatedUser, Depends(require_operator)],
    db: Annotated[Session, Depends(get_db)],
) -> DriftAnalysis:
    """Run drift analysis."""
    service = MLGovernanceService(db)
    return service.run_drift_analysis(request, actor_id=current_user.id)


@router.get(
    "/shadow",
    response_model=list[ShadowComparison],
    summary="List Shadow Comparisons (Compatibility)",
    dependencies=[Depends(rate_limit_reads)],
)
def list_shadow_comparisons(
    current_user: Annotated[AuthenticatedUser, Depends(require_viewer)],
    db: Annotated[Session, Depends(get_db)],
    model_id: str | None = Query(default=None, description="Filter by model ID"),
) -> list[ShadowComparison]:
    """List shadow comparisons."""
    service = MLGovernanceService(db)
    comparisons = service.get_shadow_comparisons()
    if model_id:
        comparisons = [
            c
            for c in comparisons
            if c.champion_model_id == model_id or c.challenger_model_id == model_id
        ]
    return comparisons


@router.post(
    "/shadow/compare",
    response_model=ShadowComparison,
    status_code=status.HTTP_201_CREATED,
    summary="Run Shadow Comparison (Compatibility)",
    dependencies=[Depends(rate_limit_mutations)],
)
def run_shadow_comparison(
    request: ShadowComparisonRequest,
    current_user: Annotated[AuthenticatedUser, Depends(require_operator)],
    db: Annotated[Session, Depends(get_db)],
) -> ShadowComparison:
    """Run shadow comparison."""
    service = MLGovernanceService(db)
    return service.run_shadow_comparison(request, actor_id=current_user.id)


@router.get(
    "/promotions",
    response_model=list[PromotionApprovalRequest],
    summary="List Promotion Requests (Compatibility)",
    dependencies=[Depends(rate_limit_reads)],
)
def list_promotion_requests(
    current_user: Annotated[AuthenticatedUser, Depends(require_viewer)],
    db: Annotated[Session, Depends(get_db)],
) -> list[PromotionApprovalRequest]:
    """List promotion requests."""
    service = MLGovernanceService(db)
    return service.get_promotion_requests()


@router.post(
    "/promotions/request",
    response_model=PromotionApprovalRequest,
    status_code=status.HTTP_201_CREATED,
    summary="Request Promotion (Compatibility)",
    dependencies=[Depends(rate_limit_mutations)],
)
def request_promotion(
    request: PromotionRequest,
    current_user: Annotated[AuthenticatedUser, Depends(require_operator)],
    db: Annotated[Session, Depends(get_db)],
) -> PromotionApprovalRequest:
    """Request promotion."""
    service = MLGovernanceService(db)
    return service.request_promotion(request, actor_id=current_user.id)


@router.post(
    "/promotions/{promotion_id}/review",
    response_model=PromotionApprovalRequest,
    summary="Review Promotion Request (Compatibility)",
    dependencies=[Depends(rate_limit_mutations)],
)
def review_promotion(
    promotion_id: str,
    request: PromotionApprovalActionRequest,
    current_user: Annotated[AuthenticatedUser, Depends(require_admin)],
    db: Annotated[Session, Depends(get_db)],
) -> PromotionApprovalRequest:
    """Review promotion request."""
    service = MLGovernanceService(db)
    return service.review_promotion(promotion_id, request, actor_id=current_user.id)


@router.get(
    "/kill-switch",
    response_model=list[ModelKillSwitch],
    summary="List Kill Switches (Compatibility)",
    dependencies=[Depends(rate_limit_reads)],
)
def list_kill_switches(
    current_user: Annotated[AuthenticatedUser, Depends(require_viewer)],
    db: Annotated[Session, Depends(get_db)],
) -> list[ModelKillSwitch]:
    """List kill switches."""
    service = MLGovernanceService(db)
    return service.get_kill_switches()


@router.post(
    "/kill-switch/toggle",
    response_model=ModelKillSwitch,
    summary="Toggle Kill Switch (Compatibility)",
    dependencies=[Depends(rate_limit_mutations)],
)
def toggle_kill_switch(
    request: KillSwitchToggleRequest,
    current_user: Annotated[AuthenticatedUser, Depends(require_admin)],
    db: Annotated[Session, Depends(get_db)],
) -> ModelKillSwitch:
    """Toggle kill switch."""
    service = MLGovernanceService(db)
    return service.toggle_kill_switch(request, actor_id=current_user.id)


@router.get(
    "/compliance/card",
    response_model=list[ModelComplianceCard],
    summary="List Compliance Cards (Compatibility)",
    dependencies=[Depends(rate_limit_reads)],
)
def list_compliance_cards(
    current_user: Annotated[AuthenticatedUser, Depends(require_viewer)],
    db: Annotated[Session, Depends(get_db)],
    model_id: str | None = Query(default=None, description="Filter by model ID"),
) -> list[ModelComplianceCard]:
    """List compliance cards."""
    service = MLGovernanceService(db)
    cards = service.get_compliance_cards()
    if model_id:
        cards = [c for c in cards if c.model_id == model_id]
    return cards


@router.post(
    "/compliance/card",
    response_model=ModelComplianceCard,
    status_code=status.HTTP_201_CREATED,
    summary="Generate Compliance Card (Compatibility)",
    dependencies=[Depends(rate_limit_mutations)],
)
def generate_compliance_card(
    request: ComplianceCardGenerateRequest,
    current_user: Annotated[AuthenticatedUser, Depends(require_operator)],
    db: Annotated[Session, Depends(get_db)],
) -> ModelComplianceCard:
    """Generate compliance card."""
    service = MLGovernanceService(db)
    return service.generate_compliance_card(request, actor_id=current_user.id)


@router.post(
    "/incidents/{incident_id}/action",
    response_model=MLIncident,
    summary="Action Incident (Compatibility)",
    dependencies=[Depends(rate_limit_mutations)],
)
def action_incident(
    incident_id: str,
    request: MLIncidentActionRequest,
    current_user: Annotated[AuthenticatedUser, Depends(require_operator)],
    db: Annotated[Session, Depends(get_db)],
) -> MLIncident:
    """Action incident."""
    service = MLGovernanceService(db)
    if request.decision == "RESOLVE":
        return service.resolve_incident(
            incident_id, request.notes, actor_id=current_user.id, db=db
        )
    return service.acknowledge_incident(
        incident_id, request.notes, actor_id=current_user.id, db=db
    )
