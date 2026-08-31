import logging
import uuid
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import (
    AuthenticatedUser,
    require_admin,
    require_operator,
    require_viewer,
)
from app.schemas.activation import (
    ActivationActionRequest,
    CreateActivationRequest,
    PaginatedActivationsResponse,
    StartCanaryRequest,
    StrategyActivationResponse,
)
from app.schemas.continuous_learning import (
    ContinuousLearningReadiness,
    ContinuousLearningSummary,
    ManualTrainingTriggerRequest,
    ModelLineageResponse,
    PaginatedDatasetsResponse,
    PaginatedTrainingRunsResponse,
    TrainingRun,
)
from app.schemas.control_plane import (
    CaseDecisionTrace,
    ControlPlaneSummaryResponse,
    GovernanceCenterResponse,
    IncidentsResponse,
    UnifiedIntelligenceHealth,
    UnifiedLineageResponse,
)
from app.schemas.evaluation import IntelligenceEvaluationResponse
from app.schemas.experimentation import (
    ExperimentActionRequest,
    ExperimentAnalysisResponse,
    ExperimentRequest,
    ExperimentResponse,
    PaginatedExperimentsResponse,
)
from app.schemas.governance import ModelGovernanceResponse
from app.schemas.model_deployment import (
    CanaryRolloutRequest,
    DeploymentReadinessReport,
    ModelActivationRequest,
    ModelDeploymentRequest,
    ModelDeploymentResponse,
    ModelRollbackRequest,
    PaginatedDeploymentsResponse,
    ShadowAnalysisResponse,
    ShadowStartRequest,
)
from app.schemas.model_lifecycle import (
    ModelApprovalRequest,
    ModelRejectionRequest,
    ModelScorecardResponse,
    ModelSummaryResponse,
    ModelTrainingRequest,
    PaginatedModelsResponse,
)
from app.schemas.optimization import StrategyOptimizationResponse
from app.schemas.production import (
    ProductionMonitoringResponse,
    PromoteProductionRequest,
    PromotionReadinessResponse,
)
from app.schemas.recommendation import (
    PaginatedRecommendationsResponse,
    RecommendationReviewRequest,
    StrategyRecommendationResponse,
)
from app.schemas.recovery import (
    HumanReviewActionRequest,
    HumanReviewActionResponse,
    PaginatedAuditLogsResponse,
    PaginatedHumanReviewResponse,
    PaginatedRecoveryCasesResponse,
    RecoveryCaseDetailResponse,
    RecoveryMetricsResponse,
)
from app.schemas.simulation import (
    CounterfactualSimulationResponse,
    SimulationRequest,
)
from app.services.continuous_learning_service import (
    ContinuousLearningService,
)
from app.services.counterfactual_simulation_service import (
    counterfactual_simulation_service,
)
from app.services.experimentation_service import (
    experimentation_service,
)
from app.services.intelligence_control_plane_service import (
    IntelligenceControlPlaneService,
)
from app.services.intelligence_evaluation_service import (
    intelligence_evaluation_service,
)
from app.services.metrics_service import (
    CaseNotFoundError,
    ReviewNotEligibleError,
    recovery_metrics_service,
)
from app.services.model_deployment_service import (
    ModelDeploymentService,
)
from app.services.model_governance_service import (
    model_governance_service,
)
from app.services.model_lifecycle_service import (
    ModelLifecycleConflictError,
    ModelLifecycleService,
)
from app.services.production_monitoring_service import (
    production_monitoring_service,
)
from app.services.production_promotion_service import (
    PromotionBlockedError,
    production_promotion_service,
)
from app.services.strategy_activation_service import (
    ActivationNotFoundError,
    InvalidActivationStateError,
    InvalidRolloutPercentageError,
    ModelDegradedError,
    RecommendationNotEligibleError,
    strategy_activation_service,
)
from app.services.strategy_governance_service import (
    InvalidRecommendationStateError,
    RecommendationNotFoundError,
    strategy_governance_service,
)
from app.services.strategy_optimization_service import (
    strategy_optimization_service,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/recovery", tags=["recovery"])


@router.get(
    "/metrics",
    response_model=RecoveryMetricsResponse,
    summary="Get aggregated recovery KPIs, financial statistics, and worker telemetry",
)
def get_recovery_metrics(
    current_user: Annotated[AuthenticatedUser, Depends(require_viewer)],
    db: Session = Depends(get_db),
) -> Any:
    """Return top-level dashboard metrics (cases, amounts in paise, policy rates, worker status)."""
    return recovery_metrics_service.get_dashboard_metrics(db=db)


@router.get(
    "/intelligence/evaluation",
    response_model=IntelligenceEvaluationResponse,
    summary="Get comprehensive recovery intelligence and ML model evaluation report",
)
def get_intelligence_evaluation(
    current_user: Annotated[AuthenticatedUser, Depends(require_viewer)],
    db: Session = Depends(get_db),
) -> Any:
    """
    Return comprehensive, read-only intelligence evaluation metrics (confusion matrix,
    Brier calibration, action attribution, risk-tier segmentation, and MTTR).
    """
    return intelligence_evaluation_service.evaluate(db=db)


@router.get(
    "/intelligence/governance",
    response_model=ModelGovernanceResponse,
    summary="Get model governance, drift monitoring, and intelligence health report",
)
def get_model_governance(
    current_user: Annotated[AuthenticatedUser, Depends(require_viewer)],
    db: Session = Depends(get_db),
) -> Any:
    """
    Return comprehensive, read-only model governance health evaluation, rolling performance
    windows, feature/prediction/outcome drift (PSI), and data quality metrics.
    """
    return model_governance_service.evaluate_governance(db=db)


@router.get(
    "/intelligence/optimization",
    response_model=StrategyOptimizationResponse,
    summary="Get intelligent recovery strategy optimization and Expected Recovery Value report",
)
def get_strategy_optimization(
    current_user: Annotated[AuthenticatedUser, Depends(require_viewer)],
    db: Session = Depends(get_db),
) -> Any:
    """
    Return comprehensive, read-only strategy optimization recommendations, champion recovery action,
    optimal retry delay cadences, segment recommendations, and Expected Recovery Value (ERV).
    """
    return strategy_optimization_service.optimize(db=db)


@router.post(
    "/intelligence/simulation",
    response_model=CounterfactualSimulationResponse,
    summary="Execute counterfactual what-if recovery strategy simulation against comparable populations",
)
def run_counterfactual_simulation(
    payload: SimulationRequest,
    current_user: Annotated[AuthenticatedUser, Depends(require_viewer)],
    db: Session = Depends(get_db),
) -> Any:
    """
    Execute read-only counterfactual strategy simulation comparing baseline vs alternative strategies.
    Zero financial mutations. Zero external calls.
    """
    return counterfactual_simulation_service.simulate(db=db, req=payload)


@router.get(
    "/intelligence/recommendations",
    response_model=PaginatedRecommendationsResponse,
    summary="List governed strategy recommendations with evidence trails and active proposals",
)
def list_strategy_recommendations(
    current_user: Annotated[AuthenticatedUser, Depends(require_viewer)],
    db: Session = Depends(get_db),
) -> Any:
    """List historical versioned recommendations and sync active evidence-backed recommendations."""
    return strategy_governance_service.list_recommendations(db=db)


@router.get(
    "/intelligence/recommendations/{recommendation_id}",
    response_model=StrategyRecommendationResponse,
    summary="Get detailed evidence trail and lifecycle state of a specific strategy recommendation",
)
def get_strategy_recommendation_detail(
    recommendation_id: str,
    current_user: Annotated[AuthenticatedUser, Depends(require_viewer)],
    db: Session = Depends(get_db),
) -> Any:
    """Fetch complete immutable evidence bundle for a single strategy recommendation."""
    try:
        return strategy_governance_service.get_recommendation_detail(
            db=db, recommendation_id=recommendation_id
        )
    except RecommendationNotFoundError as err:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(err),
        ) from err


@router.post(
    "/intelligence/recommendations/{recommendation_id}/approve",
    response_model=StrategyRecommendationResponse,
    summary="Operator approves a governed strategy recommendation (Endorsement only, 0 financial actions)",
)
def approve_strategy_recommendation(
    recommendation_id: str,
    payload: RecommendationReviewRequest,
    current_user: Annotated[AuthenticatedUser, Depends(require_operator)],
    db: Session = Depends(get_db),
) -> Any:
    """
    Approve a recommendation in REVIEW_REQUIRED state.
    Transition status to APPROVED and record immutable operator audit entry.
    Zero autonomous financial execution.
    """
    try:
        return strategy_governance_service.approve_recommendation(
            db=db,
            recommendation_id=recommendation_id,
            current_user=current_user,
            notes=payload.notes,
        )
    except RecommendationNotFoundError as err:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(err),
        ) from err
    except InvalidRecommendationStateError as err:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(err),
        ) from err


@router.post(
    "/intelligence/recommendations/{recommendation_id}/reject",
    response_model=StrategyRecommendationResponse,
    summary="Operator rejects a governed strategy recommendation",
)
def reject_strategy_recommendation(
    recommendation_id: str,
    payload: RecommendationReviewRequest,
    current_user: Annotated[AuthenticatedUser, Depends(require_operator)],
    db: Session = Depends(get_db),
) -> Any:
    """
    Reject a recommendation in REVIEW_REQUIRED state.
    Transition status to REJECTED and record immutable operator audit entry.
    """
    try:
        return strategy_governance_service.reject_recommendation(
            db=db,
            recommendation_id=recommendation_id,
            current_user=current_user,
            notes=payload.notes,
        )
    except RecommendationNotFoundError as err:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(err),
        ) from err
    except InvalidRecommendationStateError as err:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(err),
        ) from err


@router.get(
    "/intelligence/activations",
    response_model=PaginatedActivationsResponse,
    summary="List controlled strategy activations and current canary experiments",
)
def list_strategy_activations(
    current_user: Annotated[AuthenticatedUser, Depends(require_viewer)],
    db: Session = Depends(get_db),
) -> Any:
    """List all versioned strategy activations and active canary rollouts."""
    return strategy_activation_service.list_activations(db=db)


@router.get(
    "/intelligence/activations/{activation_id}",
    response_model=StrategyActivationResponse,
    summary="Get detailed metrics and health of a specific strategy activation",
)
def get_strategy_activation_detail(
    activation_id: str,
    current_user: Annotated[AuthenticatedUser, Depends(require_viewer)],
    db: Session = Depends(get_db),
) -> Any:
    """Fetch complete telemetry comparison and rollout health for an activation."""
    try:
        return strategy_activation_service.get_activation_detail(
            db=db, activation_id=activation_id
        )
    except ActivationNotFoundError as err:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(err),
        ) from err


@router.post(
    "/intelligence/activations/create",
    response_model=StrategyActivationResponse,
    summary="Operator creates a new strategy activation draft from an approved recommendation",
)
def create_strategy_activation(
    payload: CreateActivationRequest,
    current_user: Annotated[AuthenticatedUser, Depends(require_operator)],
    db: Session = Depends(get_db),
) -> Any:
    """Create a strategy activation from an approved, unexpired recommendation."""
    try:
        return strategy_activation_service.create_activation(
            db=db,
            recommendation_id=payload.recommendation_id,
            current_user=current_user,
            target_segment=payload.target_segment,
            notes=payload.notes,
        )
    except RecommendationNotEligibleError as err:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(err),
        ) from err
    except ModelDegradedError as err:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(err),
        ) from err


@router.post(
    "/intelligence/activations/{activation_id}/start-canary",
    response_model=StrategyActivationResponse,
    summary="Operator initiates or updates a canary rollout percentage (5%, 10%, 25%, 50%)",
)
def start_strategy_canary(
    activation_id: str,
    payload: StartCanaryRequest,
    current_user: Annotated[AuthenticatedUser, Depends(require_operator)],
    db: Session = Depends(get_db),
) -> Any:
    """Start or update canary experiment stage. Zero financial mutations."""
    try:
        return strategy_activation_service.start_canary(
            db=db,
            activation_id=activation_id,
            rollout_percentage=payload.rollout_percentage,
            current_user=current_user,
            notes=payload.notes,
        )
    except ActivationNotFoundError as err:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(err),
        ) from err
    except (
        InvalidActivationStateError,
        InvalidRolloutPercentageError,
        ModelDegradedError,
    ) as err:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(err),
        ) from err


@router.post(
    "/intelligence/activations/{activation_id}/pause",
    response_model=StrategyActivationResponse,
    summary="Operator pauses an active canary or full rollout (rollout 0%)",
)
def pause_strategy_activation(
    activation_id: str,
    payload: ActivationActionRequest,
    current_user: Annotated[AuthenticatedUser, Depends(require_operator)],
    db: Session = Depends(get_db),
) -> Any:
    """Pause strategy rollout."""
    try:
        return strategy_activation_service.pause_activation(
            db=db,
            activation_id=activation_id,
            current_user=current_user,
            notes=payload.notes,
        )
    except ActivationNotFoundError as err:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(err),
        ) from err
    except InvalidActivationStateError as err:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(err),
        ) from err


@router.post(
    "/intelligence/activations/{activation_id}/rollback",
    response_model=StrategyActivationResponse,
    summary="Operator terminates and rolls back a strategy rollout",
)
def rollback_strategy_activation(
    activation_id: str,
    payload: ActivationActionRequest,
    current_user: Annotated[AuthenticatedUser, Depends(require_operator)],
    db: Session = Depends(get_db),
) -> Any:
    """Roll back strategy rollout."""
    try:
        return strategy_activation_service.rollback_activation(
            db=db,
            activation_id=activation_id,
            current_user=current_user,
            notes=payload.notes,
        )
    except ActivationNotFoundError as err:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(err),
        ) from err
    except InvalidActivationStateError as err:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(err),
        ) from err


@router.post(
    "/intelligence/activations/{activation_id}/activate",
    response_model=StrategyActivationResponse,
    summary="Admin promotes a canary experiment to 100% full production rollout (ACTIVE)",
)
def activate_strategy_rollout(
    activation_id: str,
    payload: ActivationActionRequest,
    current_user: Annotated[AuthenticatedUser, Depends(require_admin)],
    db: Session = Depends(get_db),
) -> Any:
    """Promote canary to 100% full production rollout. Requires admin role."""
    try:
        return strategy_activation_service.promote_to_active(
            db=db,
            activation_id=activation_id,
            current_user=current_user,
            notes=payload.notes,
        )
    except ActivationNotFoundError as err:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(err),
        ) from err
    except (InvalidActivationStateError, ModelDegradedError) as err:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(err),
        ) from err


@router.get(
    "/intelligence/production",
    response_model=ProductionMonitoringResponse,
    summary="Continuous live monitoring and automated guardrails for production strategy",
)
def get_production_monitoring(
    current_user: Annotated[AuthenticatedUser, Depends(require_viewer)],
    db: Session = Depends(get_db),
) -> Any:
    """Gather real-time continuous performance and safety guardrails for active production strategy."""
    return production_monitoring_service.monitor_production(db=db)


@router.get(
    "/intelligence/activations/{activation_id}/promotion-readiness",
    response_model=PromotionReadinessResponse,
    summary="Check deterministic promotion eligibility against 8 safety gates",
)
def get_promotion_readiness(
    activation_id: str,
    current_user: Annotated[AuthenticatedUser, Depends(require_viewer)],
    db: Session = Depends(get_db),
) -> Any:
    """Evaluate whether an activation meets all 8 promotion safety rules."""
    try:
        return production_promotion_service.evaluate_promotion_readiness(
            db=db, activation_id=activation_id
        )
    except ActivationNotFoundError as err:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(err),
        ) from err


@router.post(
    "/intelligence/activations/{activation_id}/promote",
    response_model=StrategyActivationResponse,
    summary="Admin promotes an activation to full 100% production rollout",
)
def promote_strategy_to_production(
    activation_id: str,
    payload: PromoteProductionRequest,
    current_user: Annotated[AuthenticatedUser, Depends(require_admin)],
    db: Session = Depends(get_db),
) -> Any:
    """Promote an activation to production after validating 8 safety gates. Requires admin role."""
    try:
        return production_promotion_service.promote_to_production(
            db=db,
            activation_id=activation_id,
            current_user=current_user,
            reason=payload.reason,
        )
    except ActivationNotFoundError as err:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(err),
        ) from err
    except PromotionBlockedError as err:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(err),
        ) from err


# =========================================================================
# Phase 9H: Causal Experimentation, Statistical Testing & Decision Intelligence
# =========================================================================


@router.post(
    "/intelligence/experiments",
    response_model=ExperimentResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new causal experiment in DRAFT status",
)
def create_experiment(
    payload: ExperimentRequest,
    current_user: Annotated[AuthenticatedUser, Depends(require_operator)],
    db: Session = Depends(get_db),
) -> Any:
    """Create a new causal experiment with deterministic SHA-256 cohort partitioning."""
    return experimentation_service.create_experiment(
        db=db,
        payload=payload,
        actor_id=current_user.id,
        actor_role=current_user.role,
    )


@router.get(
    "/intelligence/experiments",
    response_model=PaginatedExperimentsResponse,
    summary="List all causal experiments with pagination and filtering",
)
def list_experiments(
    current_user: Annotated[AuthenticatedUser, Depends(require_viewer)],
    db: Session = Depends(get_db),
    status: str | None = Query(default=None, description="Filter by experiment status"),
    page: int = Query(default=1, ge=1, description="Page number (1-indexed)"),
    page_size: int = Query(default=20, ge=1, le=100, description="Items per page"),
) -> Any:
    """Return paginated list of experiments with aggregate metadata."""
    return experimentation_service.list_experiments(
        db=db,
        status_filter=status,
        page=page,
        page_size=page_size,
    )


@router.get(
    "/intelligence/experiments/{experiment_id}",
    response_model=ExperimentResponse,
    summary="Get details of a specific causal experiment",
)
def get_experiment_detail(
    experiment_id: str,
    current_user: Annotated[AuthenticatedUser, Depends(require_viewer)],
    db: Session = Depends(get_db),
) -> Any:
    """Return comprehensive metadata for an experiment."""
    return experimentation_service.get_experiment(
        db=db,
        experiment_id=experiment_id,
    )


@router.get(
    "/intelligence/experiments/{experiment_id}/analysis",
    response_model=ExperimentAnalysisResponse,
    summary="Evaluate causal effects, statistical hypothesis testing, and balance diagnostics",
)
def get_experiment_analysis(
    experiment_id: str,
    current_user: Annotated[AuthenticatedUser, Depends(require_viewer)],
    db: Session = Depends(get_db),
) -> Any:
    """Perform statistical analysis, Wilson/Newcombe CI, z-test, and causal evidence classification."""
    return experimentation_service.analyze_experiment(
        db=db,
        experiment_id=experiment_id,
    )


@router.post(
    "/intelligence/experiments/{experiment_id}/start",
    response_model=ExperimentResponse,
    summary="Start or resume an experiment",
)
def start_experiment(
    experiment_id: str,
    payload: ExperimentActionRequest,
    current_user: Annotated[AuthenticatedUser, Depends(require_operator)],
    db: Session = Depends(get_db),
) -> Any:
    """Transition experiment to RUNNING status."""
    return experimentation_service.start_experiment(
        db=db,
        experiment_id=experiment_id,
        actor_id=current_user.id,
        notes=payload.notes,
    )


@router.post(
    "/intelligence/experiments/{experiment_id}/pause",
    response_model=ExperimentResponse,
    summary="Pause a running experiment",
)
def pause_experiment(
    experiment_id: str,
    payload: ExperimentActionRequest,
    current_user: Annotated[AuthenticatedUser, Depends(require_operator)],
    db: Session = Depends(get_db),
) -> Any:
    """Transition experiment to PAUSED status."""
    return experimentation_service.pause_experiment(
        db=db,
        experiment_id=experiment_id,
        actor_id=current_user.id,
        notes=payload.notes,
    )


@router.post(
    "/intelligence/experiments/{experiment_id}/complete",
    response_model=ExperimentResponse,
    summary="Complete an experiment",
)
def complete_experiment(
    experiment_id: str,
    payload: ExperimentActionRequest,
    current_user: Annotated[AuthenticatedUser, Depends(require_operator)],
    db: Session = Depends(get_db),
) -> Any:
    """Transition experiment to COMPLETED status."""
    return experimentation_service.complete_experiment(
        db=db,
        experiment_id=experiment_id,
        actor_id=current_user.id,
        notes=payload.notes,
    )


@router.get(
    "/cases",
    response_model=PaginatedRecoveryCasesResponse,
    summary="List paginated recovery cases with safe operational projection",
)
def list_recovery_cases(
    current_user: Annotated[AuthenticatedUser, Depends(require_viewer)],
    db: Session = Depends(get_db),
    page: int = Query(default=1, ge=1, description="Page number (1-indexed)"),
    page_size: int = Query(default=20, ge=1, le=100, description="Items per page"),
    status: str | None = Query(default=None, description="Filter by case status"),
    recovery_stage: str | None = Query(
        default=None, description="Filter by recovery stage"
    ),
    search: str | None = Query(
        default=None, description="Search by customer ID or failure reason"
    ),
) -> Any:
    """Return a paginated list of recovery cases with zero PII."""
    return recovery_metrics_service.list_cases(
        db=db,
        page=page,
        page_size=page_size,
        status=status,
        recovery_stage=recovery_stage,
        search=search,
    )


@router.get(
    "/cases/{case_id}",
    response_model=RecoveryCaseDetailResponse,
    summary="Get comprehensive lifecycle trail for a specific recovery case",
)
def get_recovery_case_detail(
    case_id: uuid.UUID,
    current_user: Annotated[AuthenticatedUser, Depends(require_viewer)],
    db: Session = Depends(get_db),
) -> Any:
    """Return full timeline of predictions, decisions, actions, and audit logs for a case."""
    detail = recovery_metrics_service.get_case_detail(db=db, case_id=case_id)
    if not detail:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"RecoveryCase '{case_id}' not found.",
        )
    return detail


@router.get(
    "/human-review",
    response_model=PaginatedHumanReviewResponse,
    summary="List active cases queued for human operator review",
)
def get_human_review_queue(
    current_user: Annotated[AuthenticatedUser, Depends(require_viewer)],
    db: Session = Depends(get_db),
    page: int = Query(default=1, ge=1, description="Page number (1-indexed)"),
    page_size: int = Query(default=20, ge=1, le=100, description="Items per page"),
) -> Any:
    """Return cases where latest policy decision is HUMAN_REVIEW and action is pending."""
    return recovery_metrics_service.get_human_review_queue(
        db=db, page=page, page_size=page_size
    )


@router.post(
    "/human-review/{case_id}/approve",
    response_model=HumanReviewActionResponse,
    summary="Approve a human-review case and schedule authorized recovery action",
)
def approve_human_review(
    case_id: uuid.UUID,
    payload: HumanReviewActionRequest,
    current_user: Annotated[AuthenticatedUser, Depends(require_operator)],
    db: Session = Depends(get_db),
) -> Any:
    """
    Operator approval of a flagged case, authorizing PolicyEngine and scheduling action.
    The actor identity is strictly derived from the verified authentication credentials.
    """
    try:
        return recovery_metrics_service.approve_human_review(
            db=db,
            case_id=case_id,
            operator_id=current_user.id,
            notes=payload.notes,
        )
    except CaseNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    except ReviewNotEligibleError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
    except Exception as exc:
        logger.error(
            "human_review_approve_endpoint_error",
            extra={"case_id": str(case_id), "error": str(exc)},
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to approve review: {exc}",
        ) from exc


@router.post(
    "/human-review/{case_id}/dismiss",
    response_model=HumanReviewActionResponse,
    summary="Dismiss a human-review case with immutable audit logging",
)
def dismiss_human_review(
    case_id: uuid.UUID,
    payload: HumanReviewActionRequest,
    current_user: Annotated[AuthenticatedUser, Depends(require_operator)],
    db: Session = Depends(get_db),
) -> Any:
    """
    Operator dismissal of a flagged case with audit trail logging.
    The actor identity is strictly derived from the verified authentication credentials.
    """
    try:
        return recovery_metrics_service.dismiss_human_review(
            db=db,
            case_id=case_id,
            operator_id=current_user.id,
            notes=payload.notes,
        )
    except CaseNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    except ReviewNotEligibleError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
    except Exception as exc:
        logger.error(
            "human_review_dismiss_endpoint_error",
            extra={"case_id": str(case_id), "error": str(exc)},
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to dismiss review: {exc}",
        ) from exc


# =============================================================================
# Phase 9I: Governed Model Training & Model Lifecycle Endpoints
# =============================================================================


@router.get(
    "/intelligence/models",
    response_model=PaginatedModelsResponse,
    summary="List all models in the governed model registry",
)
def list_models(
    current_user: Annotated[AuthenticatedUser, Depends(require_viewer)],
    db: Session = Depends(get_db),
    status: str | None = Query(default=None, description="Filter by lifecycle status"),
) -> Any:
    """Return paginated list of registered models."""
    service = ModelLifecycleService(db)
    return service.list_models(status_filter=status)


# =============================================================================
# Phase 9K: Continuous Learning, Automated Monitoring & Safe Model Evolution
# =============================================================================


@router.get(
    "/intelligence/continuous-learning",
    response_model=ContinuousLearningSummary,
    summary="Get continuous learning monitoring telemetry, triggers and summary",
)
def get_continuous_learning_summary(
    current_user: Annotated[AuthenticatedUser, Depends(require_viewer)],
    db: Session = Depends(get_db),
) -> Any:
    """Return top-level continuous learning summary and trigger evaluations."""
    service = ContinuousLearningService(db)
    return service.get_continuous_learning_summary()


@router.get(
    "/intelligence/continuous-learning/datasets",
    response_model=PaginatedDatasetsResponse,
    summary="List all registered training dataset versions",
)
def list_continuous_learning_datasets(
    current_user: Annotated[AuthenticatedUser, Depends(require_viewer)],
    db: Session = Depends(get_db),
) -> Any:
    """Return immutable audit-backed dataset versions."""
    service = ContinuousLearningService(db)
    return service.list_datasets()


@router.get(
    "/intelligence/continuous-learning/training-runs",
    response_model=PaginatedTrainingRunsResponse,
    summary="List all offline training runs",
)
def list_continuous_learning_training_runs(
    current_user: Annotated[AuthenticatedUser, Depends(require_viewer)],
    db: Session = Depends(get_db),
) -> Any:
    """Return audit trail of recorded offline training runs."""
    service = ContinuousLearningService(db)
    return service.list_training_runs()


@router.get(
    "/intelligence/continuous-learning/lineage",
    response_model=ModelLineageResponse,
    summary="Get end-to-end model evolution lineage tree",
)
def get_continuous_learning_lineage(
    current_user: Annotated[AuthenticatedUser, Depends(require_viewer)],
    db: Session = Depends(get_db),
) -> Any:
    """Return provenance graph mapping datasets to training runs to models to deployments."""
    service = ContinuousLearningService(db)
    return service.get_model_lineage()


@router.get(
    "/intelligence/continuous-learning/readiness",
    response_model=ContinuousLearningReadiness,
    summary="Evaluate 14 continuous learning and model evolution safety gates",
)
def get_continuous_learning_readiness(
    current_user: Annotated[AuthenticatedUser, Depends(require_viewer)],
    db: Session = Depends(get_db),
) -> Any:
    """Evaluate 14 safety gates governing continuous learning retraining and evolution."""
    service = ContinuousLearningService(db)
    return service.evaluate_continuous_learning_readiness()


@router.post(
    "/intelligence/continuous-learning/trigger-training",
    response_model=TrainingRun,
    status_code=status.HTTP_201_CREATED,
    summary="Manually trigger an offline governed model training run",
)
def trigger_offline_training(
    payload: ManualTrainingTriggerRequest,
    current_user: Annotated[AuthenticatedUser, Depends(require_operator)],
    db: Session = Depends(get_db),
) -> Any:
    """Trigger an offline model training run. Strictly offline: 0 financial mutations, 0 automatic activations."""
    service = ContinuousLearningService(db)
    return service.trigger_offline_training(payload=payload, actor_id=current_user.id)


# =============================================================================
# Phase 9J: Governed Model Deployment, Shadow Mode & Champion–Challenger
# =============================================================================


@router.get(
    "/intelligence/models/deployments",
    response_model=PaginatedDeploymentsResponse,
    summary="List all governed model deployments with status filter",
)
def list_model_deployments(
    current_user: Annotated[AuthenticatedUser, Depends(require_viewer)],
    db: Session = Depends(get_db),
    status_filter: str | None = Query(
        default=None, alias="status", description="Filter by deployment status"
    ),
    page: int = Query(default=1, ge=1, description="Page number"),
    page_size: int = Query(default=20, ge=1, le=100, description="Page size"),
) -> Any:
    """Return paginated list of governed model deployments."""
    service = ModelDeploymentService(db)
    return service.list_deployments(
        status_filter=status_filter, page=page, page_size=page_size
    )


@router.get(
    "/intelligence/models/deployments/{deployment_id}",
    response_model=ModelDeploymentResponse,
    summary="Get single model deployment summary and audit status",
)
def get_model_deployment(
    deployment_id: str,
    current_user: Annotated[AuthenticatedUser, Depends(require_viewer)],
    db: Session = Depends(get_db),
) -> Any:
    """Fetch specific governed model deployment details by ID."""
    service = ModelDeploymentService(db)
    return service.get_deployment(deployment_id)


@router.get(
    "/intelligence/models/deployments/{deployment_id}/shadow-analysis",
    response_model=ShadowAnalysisResponse,
    summary="Evaluate shadow mode cases comparing champion vs challenger",
)
def get_shadow_mode_analysis(
    deployment_id: str,
    current_user: Annotated[AuthenticatedUser, Depends(require_viewer)],
    db: Session = Depends(get_db),
) -> Any:
    """
    Perform empirical shadow mode analysis comparing champion vs challenger on resolved cases.
    Evaluates deltas, 5-bucket calibration, statistical significance, and rollback guardrails.
    """
    service = ModelDeploymentService(db)
    return service.get_shadow_analysis(deployment_id)


@router.get(
    "/intelligence/models/deployments/{deployment_id}/readiness",
    response_model=DeploymentReadinessReport,
    summary="Evaluate 14 deterministic deployment readiness safety gates",
)
def get_deployment_readiness(
    deployment_id: str,
    current_user: Annotated[AuthenticatedUser, Depends(require_viewer)],
    db: Session = Depends(get_db),
) -> Any:
    """Evaluate 14 deterministic safety gates for canary promotion or production activation."""
    service = ModelDeploymentService(db)
    analysis = service.get_shadow_analysis(deployment_id)
    return analysis.readiness


@router.post(
    "/intelligence/models/deployments",
    response_model=ModelDeploymentResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new governed model deployment for a PROMOTION_READY candidate",
)
def create_model_deployment(
    payload: ModelDeploymentRequest,
    current_user: Annotated[AuthenticatedUser, Depends(require_operator)],
    db: Session = Depends(get_db),
) -> Any:
    """Create a new model deployment in SHADOW status for a validated challenger."""
    service = ModelDeploymentService(db)
    return service.create_deployment(payload=payload, actor_id=current_user.id)


@router.post(
    "/intelligence/models/deployments/{deployment_id}/start-shadow",
    response_model=ModelDeploymentResponse,
    summary="Start or update shadow mode deterministic traffic allocation",
)
def start_shadow_deployment(
    deployment_id: str,
    payload: ShadowStartRequest,
    current_user: Annotated[AuthenticatedUser, Depends(require_operator)],
    db: Session = Depends(get_db),
) -> Any:
    """Adjust shadow mode traffic percentage (0, 5, 10, 25, 50, 100)."""
    service = ModelDeploymentService(db)
    return service.start_shadow(
        deployment_id=deployment_id,
        percentage=payload.shadow_percentage,
        actor_id=current_user.id,
        notes=payload.notes,
    )


@router.post(
    "/intelligence/models/deployments/{deployment_id}/pause",
    response_model=ModelDeploymentResponse,
    summary="Pause model deployment traffic",
)
def pause_model_deployment(
    deployment_id: str,
    current_user: Annotated[AuthenticatedUser, Depends(require_operator)],
    db: Session = Depends(get_db),
) -> Any:
    """Pause active shadow or canary rollout (traffic set to 0%)."""
    service = ModelDeploymentService(db)
    return service.pause_deployment(
        deployment_id=deployment_id,
        actor_id=current_user.id,
    )


@router.post(
    "/intelligence/models/deployments/{deployment_id}/canary",
    response_model=ModelDeploymentResponse,
    summary="Advance deployment to governed canary staging",
)
def canary_model_deployment(
    deployment_id: str,
    payload: CanaryRolloutRequest,
    current_user: Annotated[AuthenticatedUser, Depends(require_operator)],
    db: Session = Depends(get_db),
) -> Any:
    """Advance challenger to canary allocation stage (0, 5, 10, 25, 50, 100)."""
    service = ModelDeploymentService(db)
    return service.set_canary(
        deployment_id=deployment_id,
        percentage=payload.canary_percentage,
        actor_id=current_user.id,
        notes=payload.notes,
    )


@router.post(
    "/intelligence/models/deployments/{deployment_id}/activate",
    response_model=ModelDeploymentResponse,
    summary="Admin activation of CANARY candidate to ACTIVE Champion",
)
def activate_model_deployment(
    deployment_id: str,
    payload: ModelActivationRequest,
    current_user: Annotated[AuthenticatedUser, Depends(require_admin)],
    db: Session = Depends(get_db),
) -> Any:
    """
    Admin-only production activation of challenger.
    Requires deployment to be in CANARY status with all 14 readiness gates passing.
    Atomically retires old champion and activates new challenger.
    Zero financial mutations.
    """
    service = ModelDeploymentService(db)
    return service.activate_deployment(
        deployment_id=deployment_id,
        actor_id=current_user.id,
        notes=payload.notes,
    )


@router.post(
    "/intelligence/models/deployments/{deployment_id}/rollback",
    response_model=ModelDeploymentResponse,
    summary="Admin rollback of challenger restoring previous champion",
)
def rollback_model_deployment(
    deployment_id: str,
    payload: ModelRollbackRequest,
    current_user: Annotated[AuthenticatedUser, Depends(require_admin)],
    db: Session = Depends(get_db),
) -> Any:
    """
    Admin-only rollback.
    Restores previous champion to ACTIVE and retires candidate challenger.
    """
    service = ModelDeploymentService(db)
    return service.rollback_deployment(
        deployment_id=deployment_id,
        reason=payload.reason,
        actor_id=current_user.id,
        notes=payload.notes,
    )


@router.get(
    "/intelligence/models/{version}",
    response_model=ModelSummaryResponse,
    summary="Get details of a specific model version",
)
def get_model_detail(
    version: str,
    current_user: Annotated[AuthenticatedUser, Depends(require_viewer)],
    db: Session = Depends(get_db),
) -> Any:
    """Return summary metadata for a model version."""
    service = ModelLifecycleService(db)
    model = service.get_model(version)
    if not model:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Model version '{version}' not found in registry",
        )
    return model


@router.get(
    "/intelligence/models/{version}/scorecard",
    response_model=ModelScorecardResponse,
    summary="Get champion-challenger evaluation scorecard and quality gates",
)
def get_model_scorecard(
    version: str,
    current_user: Annotated[AuthenticatedUser, Depends(require_viewer)],
    db: Session = Depends(get_db),
) -> Any:
    """Return comprehensive champion-challenger scorecard."""
    service = ModelLifecycleService(db)
    scorecard = service.get_model_scorecard(version)
    if not scorecard:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Evaluation scorecard for model '{version}' not found",
        )
    return scorecard


@router.post(
    "/intelligence/models/train",
    response_model=ModelScorecardResponse,
    summary="Initiate offline candidate model training and validation",
)
def train_candidate_model(
    payload: ModelTrainingRequest,
    current_user: Annotated[AuthenticatedUser, Depends(require_operator)],
    db: Session = Depends(get_db),
) -> Any:
    """
    Train a candidate model on resolved historical data and validate against champion.
    Strictly offline computation. Zero direct financial mutations.
    """
    service = ModelLifecycleService(db)
    return service.train_candidate_pipeline(
        request=payload,
        actor_id=current_user.id,
        actor_role=current_user.role,
    )


@router.post(
    "/intelligence/models/{version}/approve",
    response_model=ModelSummaryResponse,
    summary="Approve candidate model into PROMOTION_READY status",
)
def approve_model_candidate(
    version: str,
    payload: ModelApprovalRequest,
    current_user: Annotated[AuthenticatedUser, Depends(require_operator)],
    db: Session = Depends(get_db),
) -> Any:
    """
    Approve candidate model. Transitions state from REVIEW_REQUIRED to PROMOTION_READY.
    Does NOT automatically activate model for live scoring.
    """
    service = ModelLifecycleService(db)
    try:
        return service.approve_model(
            version=version,
            actor_id=current_user.id,
            actor_role=current_user.role,
            notes=payload.notes,
        )
    except ModelLifecycleConflictError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc


@router.post(
    "/intelligence/models/{version}/reject",
    response_model=ModelSummaryResponse,
    summary="Reject candidate model",
)
def reject_model_candidate(
    version: str,
    payload: ModelRejectionRequest,
    current_user: Annotated[AuthenticatedUser, Depends(require_operator)],
    db: Session = Depends(get_db),
) -> Any:
    """Reject candidate model in REVIEW_REQUIRED status."""
    service = ModelLifecycleService(db)
    try:
        return service.reject_model(
            version=version,
            reason=payload.reason,
            actor_id=current_user.id,
            actor_role=current_user.role,
        )
    except ModelLifecycleConflictError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc


# =============================================================================
# Phase 9L: Intelligence Control Plane & Unified Autonomous Governance
# =============================================================================


@router.get(
    "/intelligence/control-plane",
    response_model=ControlPlaneSummaryResponse,
    summary="Get high-level summary of the unified Intelligence Control Plane",
)
def get_control_plane_summary(
    current_user: Annotated[AuthenticatedUser, Depends(require_viewer)],
    db: Session = Depends(get_db),
) -> Any:
    """Return high-level control plane state, health score, subsystems, and diagnostics."""
    service = IntelligenceControlPlaneService(db)
    return service.get_summary()


@router.get(
    "/intelligence/control-plane/health",
    response_model=UnifiedIntelligenceHealth,
    summary="Get complete unified health evaluation across all 8 intelligence dimensions",
)
def get_control_plane_health(
    current_user: Annotated[AuthenticatedUser, Depends(require_viewer)],
    db: Session = Depends(get_db),
) -> Any:
    """Return detailed health status, component scores, global system state, and diagnostics."""
    service = IntelligenceControlPlaneService(db)
    return service.evaluate_unified_health()


@router.get(
    "/intelligence/control-plane/incidents",
    response_model=IncidentsResponse,
    summary="List active and correlated automated intelligence incidents",
)
def get_control_plane_incidents(
    current_user: Annotated[AuthenticatedUser, Depends(require_viewer)],
    db: Session = Depends(get_db),
) -> Any:
    """Return correlated intelligence incidents detected by multi-signal surveillance rules."""
    service = IntelligenceControlPlaneService(db)
    return service.detect_incidents()


@router.get(
    "/intelligence/control-plane/lineage",
    response_model=UnifiedLineageResponse,
    summary="Get unified end-to-end model and strategy provenance lineage graph",
)
def get_control_plane_lineage(
    current_user: Annotated[AuthenticatedUser, Depends(require_viewer)],
    db: Session = Depends(get_db),
) -> Any:
    """Return complete DAG from dataset through model, validation, governance, rollout, to outcome."""
    service = IntelligenceControlPlaneService(db)
    return service.get_unified_lineage()


@router.get(
    "/intelligence/governance-center",
    response_model=GovernanceCenterResponse,
    summary="Get centralized human governance center queue and action items",
)
def get_governance_center(
    current_user: Annotated[AuthenticatedUser, Depends(require_viewer)],
    db: Session = Depends(get_db),
) -> Any:
    """Return pending strategy recommendations, model scorecards, deployment reviews, and alerts."""
    service = IntelligenceControlPlaneService(db)
    return service.get_governance_center()


@router.get(
    "/intelligence/decision-trace/{case_id}",
    response_model=CaseDecisionTrace,
    summary="Reconstruct complete end-to-end intelligence execution decision trace for a case",
)
def get_decision_trace(
    case_id: str,
    current_user: Annotated[AuthenticatedUser, Depends(require_viewer)],
    db: Session = Depends(get_db),
) -> Any:
    """
    Reconstruct chronological execution trace: failure -> features -> ML -> Agent -> Policy -> Action -> Result -> Outcome.
    Strictly read-only with zero PII or credentials exposed.
    """
    service = IntelligenceControlPlaneService(db)
    return service.get_decision_trace(case_id_str=case_id)


@router.get(
    "/audit-logs",
    response_model=PaginatedAuditLogsResponse,
    summary="List immutable system audit logs with pagination and filters",
)
def list_audit_logs(
    current_user: Annotated[AuthenticatedUser, Depends(require_viewer)],
    db: Session = Depends(get_db),
    page: int = Query(default=1, ge=1, description="Page number (1-indexed)"),
    page_size: int = Query(default=20, ge=1, le=100, description="Items per page"),
    event_type: str | None = Query(default=None, description="Filter by event type"),
    case_id: uuid.UUID | None = Query(
        default=None, description="Filter by recovery case ID"
    ),
) -> Any:
    """Return paginated immutable audit trail."""
    return recovery_metrics_service.list_audit_logs(
        db=db,
        page=page,
        page_size=page_size,
        event_type=event_type,
        case_id=case_id,
    )
