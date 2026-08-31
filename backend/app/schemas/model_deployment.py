"""Pydantic schemas for Phase 9J: Governed Model Deployment, Shadow Mode & Champion–Challenger."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from app.models.enums import (
    ComparisonStatus,
    DeploymentQualityGateCode,
    DeploymentReadinessDecision,
    DeploymentSignificance,
    ModelDeploymentStatus,
)


class ModelDeploymentRequest(BaseModel):
    """Payload for creating a new governed model deployment."""

    challenger_version: str = Field(
        ...,
        description="Version string of the candidate model in PROMOTION_READY status.",
        min_length=1,
        max_length=32,
    )
    champion_version: str = Field(
        default="v1.0",
        description="Version string of the currently active production champion.",
        min_length=1,
        max_length=32,
    )
    notes: str | None = Field(
        default=None,
        description="Optional deployment rationale or change ticket notes.",
        max_length=500,
    )


class ShadowStartRequest(BaseModel):
    """Payload for starting or updating shadow mode traffic allocation."""

    shadow_percentage: int = Field(
        default=100,
        description="Deterministic traffic percentage in shadow mode: 0, 5, 10, 25, 50, 100.",
    )
    notes: str | None = Field(
        default=None,
        description="Optional operational notes.",
        max_length=500,
    )


class CanaryRolloutRequest(BaseModel):
    """Payload for advancing candidate model to governed canary staging."""

    canary_percentage: int = Field(
        ...,
        description="Deterministic canary allocation percentage: 0, 5, 10, 25, 50, 100.",
    )
    notes: str | None = Field(
        default=None,
        description="Optional operational canary staging notes.",
        max_length=500,
    )


class ModelActivationRequest(BaseModel):
    """Payload for Admin promotion of canary challenger to Active Champion."""

    notes: str | None = Field(
        default=None,
        description="Admin justification and confirmation notes for production activation.",
        max_length=500,
    )


class ModelRollbackRequest(BaseModel):
    """Payload for Admin rollback of challenger to previous champion."""

    reason: str = Field(
        ...,
        description="Mandatory reason for initiating emergency or governed model rollback.",
        min_length=3,
        max_length=500,
    )
    notes: str | None = Field(
        default=None,
        description="Optional operational rollback notes.",
        max_length=500,
    )


class DeploymentMetricsSnapshot(BaseModel):
    """Point-in-time metrics for champion or challenger on evaluated cases."""

    sample_size: int = Field(..., ge=0)
    recovered_count: int = Field(..., ge=0)
    failed_count: int = Field(..., ge=0)
    recovery_rate: float | None = Field(default=None)
    accuracy: float = Field(..., ge=0.0, le=1.0)
    precision: float = Field(..., ge=0.0, le=1.0)
    recall: float = Field(..., ge=0.0, le=1.0)
    f1_score: float = Field(..., ge=0.0, le=1.0)
    brier_score: float = Field(..., ge=0.0, le=1.0)
    mean_probability: float = Field(..., ge=0.0, le=1.0)


class ShadowComparisonMetric(BaseModel):
    """Direct comparison between champion and challenger on a specific metric."""

    metric_name: str
    champion_value: float | None = None
    challenger_value: float | None = None
    delta: float | None = None
    status: ComparisonStatus


class CalibrationBucketComparison(BaseModel):
    """Calibration comparison within a single probability decile/bucket."""

    bucket_range: str
    champion_sample_size: int
    champion_avg_probability: float | None = None
    champion_actual_rate: float | None = None
    champion_calibration_error: float | None = None
    challenger_sample_size: int
    challenger_avg_probability: float | None = None
    challenger_actual_rate: float | None = None
    challenger_calibration_error: float | None = None


class DeploymentCalibrationReport(BaseModel):
    """Expected Calibration Error (ECE) and bucketed reliability comparison."""

    champion_ece: float = Field(..., ge=0.0)
    challenger_ece: float = Field(..., ge=0.0)
    ece_delta: float
    buckets: list[CalibrationBucketComparison]


class StatisticalSignificanceReport(BaseModel):
    """Two-proportion pooled z-test and Wilson/Newcombe 95% confidence intervals."""

    test_name: str = "TWO_PROPORTION_POOLED_Z_TEST"
    test_statistic: float | None = None
    p_value: float | None = None
    is_significant: bool = False
    significance_level: float = 0.05
    wilson_champion_ci: tuple[float, float] | None = None
    wilson_challenger_ci: tuple[float, float] | None = None
    newcombe_difference_ci: tuple[float, float] | None = None
    significance_classification: DeploymentSignificance = (
        DeploymentSignificance.INSUFFICIENT_DATA
    )


class ReadinessGateResult(BaseModel):
    """Result of an individual deterministic deployment readiness safety gate."""

    gate_code: DeploymentQualityGateCode
    passed: bool
    observed_value: Any
    threshold: Any
    explanation: str


class RollbackGuardrailDiagnostics(BaseModel):
    """Real-time monitoring diagnostics for automatic rollback recommendations."""

    rollback_recommended: bool = False
    reasons: list[str] = Field(default_factory=list)
    observed_recovery_rate_drop: float | None = None
    is_governance_degraded: bool = False
    is_data_quality_invalid: bool = False
    is_calibration_failed: bool = False
    is_artifact_invalid: bool = False
    is_drift_critical: bool = False


class DeploymentReadinessReport(BaseModel):
    """Comprehensive readiness assessment across all 14 safety gates."""

    decision: DeploymentReadinessDecision
    can_promote_to_canary: bool = False
    can_activate_production: bool = False
    gates: list[ReadinessGateResult] = Field(default_factory=list)
    blocking_reasons: list[str] = Field(default_factory=list)
    recommendations: list[str] = Field(default_factory=list)


class ModelDeploymentResponse(BaseModel):
    """High-level summary of a governed model deployment entity."""

    deployment_id: str
    champion_version: str
    challenger_version: str
    status: ModelDeploymentStatus
    traffic_allocation_percentage: int
    assignment_method: str = "SHA256_DETERMINISTIC"
    total_cases_evaluated: int = 0
    created_at: datetime
    started_at: datetime | None = None
    paused_at: datetime | None = None
    activated_at: datetime | None = None
    retired_at: datetime | None = None
    created_by: str
    champion_artifact_hash: str
    challenger_artifact_hash: str
    feature_schema_version: str = "v1"
    notes: str | None = None


class ShadowAnalysisResponse(BaseModel):
    """Complete empirical shadow analysis and champion vs challenger validation."""

    deployment_id: str
    champion_version: str
    challenger_version: str
    status: ModelDeploymentStatus
    traffic_allocation_percentage: int
    assignment_method: str = "SHA256_DETERMINISTIC"
    sample_size: int
    champion_metrics: DeploymentMetricsSnapshot
    challenger_metrics: DeploymentMetricsSnapshot
    metric_deltas: list[ShadowComparisonMetric]
    mean_probability_delta: float
    mean_absolute_probability_delta: float
    channel_agreement_rate: float | None = None
    delay_agreement_rate: float | None = None
    calibration: DeploymentCalibrationReport
    statistical_test: StatisticalSignificanceReport
    readiness: DeploymentReadinessReport
    rollback_diagnostics: RollbackGuardrailDiagnostics
    evaluated_at: datetime
    disclaimer: str = (
        "MODEL DEPLOYMENT & SHADOW MODE EVALUATION ONLY. "
        "Challenger model predictions are strictly observational with zero automated financial mutations. "
        "PolicyEngine remains the authoritative financial gatekeeper."
    )


class PaginatedDeploymentsResponse(BaseModel):
    """Paginated collection of governed model deployments."""

    items: list[ModelDeploymentResponse]
    total: int
    active_champion_version: str
