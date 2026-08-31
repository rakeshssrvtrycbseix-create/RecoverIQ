import { ensureValidToken } from "./auth";

const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export interface CasesMetric {
  total: number;
  active: number;
  recovered: number;
  closed: number;
}

export interface FinancialMetric {
  amount_at_risk: number;
  amount_recovered: number;
  recovery_rate_pct: number;
  currency: string;
}

export interface ActionsMetric {
  scheduled: number;
  executing: number;
  completed: number;
  failed: number;
  timed_out: number;
  total: number;
}

export interface PolicyMetric {
  allowed: number;
  blocked: number;
  human_review: number;
  total: number;
  clearance_rate_pct: number;
}

export interface WorkerTelemetrySummary {
  status: string;
  queue_depth: number;
  actions_claimed: number;
  actions_completed: number;
  actions_failed: number;
  reconciliation_runs: number;
  last_poll_at: string | null;
  last_reconciliation_at: string | null;
}

export interface BreakdownItem {
  category: string;
  count: number;
  percentage: number;
}

export interface RecentAuditActivityItem {
  id: number;
  event_type: string;
  actor_type: string;
  actor_id: string;
  case_id: string | null;
  action: string;
  created_at: string;
}

export interface RecoveryMetricsResponse {
  cases: CasesMetric;
  financial: FinancialMetric;
  actions: ActionsMetric;
  policy: PolicyMetric;
  worker: WorkerTelemetrySummary;
  failure_reasons: BreakdownItem[];
  action_types: BreakdownItem[];
  recent_activity: RecentAuditActivityItem[];
}

export interface RecoveryCaseListItem {
  id: string;
  payment_id: string;
  customer_id: string;
  status: string;
  recovery_stage: string;
  amount_at_risk: number;
  recovered_amount: number;
  total_attempts_count: number;
  max_allowed_attempts: number;
  latest_failure_reason: string | null;
  opened_at: string;
  next_action_due_at: string | null;
  resolved_at: string | null;
  closed_reason: string | null;
  ai_proposed_action: string | null;
  ai_confidence_score: number | null;
  latest_policy_result: string | null;
  latest_action_status: string | null;
  created_at: string;
  updated_at: string;
}

export interface PaginatedRecoveryCasesResponse {
  items: RecoveryCaseListItem[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

export interface PaymentSummary {
  id: string;
  razorpay_order_id: string | null;
  razorpay_invoice_id: string | null;
  amount: number;
  currency: string;
  status: string;
  due_date: string | null;
  captured_at: string | null;
  created_at: string;
}

export interface CustomerSummary {
  id: string;
  external_customer_id: string;
  risk_tier: string;
  total_payments_count: number;
  failed_payments_count: number;
  recovered_payments_count: number;
}

export interface MLPredictionSummary {
  id: string;
  model_name: string;
  model_version: string;
  recovery_probability: number;
  risk_score: number;
  confidence: number;
  priority: string;
  predicted_channel: string | null;
  predicted_delay_hours: number | null;
  predicted_at: string;
}

export interface AgentDecisionSummary {
  id: string;
  proposed_action_type: string;
  confidence_score: number;
  reasoning_summary: string;
  recommended_delay_hours: number;
  agent_name: string;
  agent_version: string;
  decided_at: string;
}

export interface PolicyDecisionSummary {
  id: string;
  agent_decision_id: string | null;
  evaluation_result: string;
  policy_engine_version: string;
  triggered_rule_code: string | null;
  rule_name: string | null;
  decision_reason: string;
  decided_at: string;
}

export interface ActionResultSummary {
  id: string;
  execution_status: string;
  provider_reference_id: string | null;
  provider_status_code: string | null;
  failure_reason: string | null;
  executed_at: string;
}

export interface RecoveryActionSummary {
  id: string;
  policy_decision_id: string;
  action_type: string;
  status: string;
  scheduled_for: string;
  dispatched_at: string | null;
  completed_at: string | null;
  created_at: string;
  results: ActionResultSummary[];
}

export interface AuditLogSummary {
  id: number;
  event_type: string;
  actor_type: string;
  actor_id: string;
  entity_type: string;
  entity_id: string | null;
  action: string;
  previous_state: Record<string, unknown> | null;
  new_state: Record<string, unknown> | null;
  metadata_json: Record<string, unknown>;
  created_at: string;
}

export interface RecoveryCaseDetailResponse {
  case: RecoveryCaseListItem;
  payment: PaymentSummary;
  customer: CustomerSummary;
  predictions: MLPredictionSummary[];
  agent_decisions: AgentDecisionSummary[];
  policy_decisions: PolicyDecisionSummary[];
  actions: RecoveryActionSummary[];
  audit_logs: AuditLogSummary[];
}

export interface HumanReviewQueueItem {
  case_id: string;
  payment_id: string;
  customer_id: string;
  customer_risk_tier: string;
  amount_at_risk: number;
  currency: string;
  case_status: string;
  recovery_stage: string;
  latest_failure_reason: string | null;
  previous_attempts_count: number;
  policy_decision_id: string;
  triggered_rule_code: string | null;
  rule_name: string | null;
  policy_decision_reason: string;
  agent_decision_id: string | null;
  proposed_action_type: string | null;
  ai_confidence_score: number | null;
  ai_reasoning_summary: string | null;
  opened_at: string;
  decided_at: string;
}

export interface PaginatedHumanReviewResponse {
  items: HumanReviewQueueItem[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

export interface HumanReviewActionResponse {
  success: boolean;
  case_id: string;
  action: string;
  scheduled_action_id: string | null;
  message: string;
  timestamp: string;
}

export interface PaginatedAuditLogsResponse {
  items: AuditLogSummary[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

// =========================================================================
// Authenticated API Fetchers
// =========================================================================

async function getAuthHeaders(): Promise<HeadersInit> {
  const token = await ensureValidToken();
  const headers: HeadersInit = {
    "Content-Type": "application/json",
  };
  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }
  return headers;
}

export async function fetchRecoveryMetrics(): Promise<RecoveryMetricsResponse> {
  const headers = await getAuthHeaders();
  const res = await fetch(`${API_BASE_URL}/api/recovery/metrics`, {
    headers,
    cache: "no-store",
  });
  if (!res.ok) {
    throw new Error(`Failed to fetch recovery metrics: ${res.statusText}`);
  }
  return res.json();
}

export async function fetchRecoveryCases(params?: {
  page?: number;
  page_size?: number;
  status?: string;
  recovery_stage?: string;
  search?: string;
}): Promise<PaginatedRecoveryCasesResponse> {
  const headers = await getAuthHeaders();
  const url = new URL(`${API_BASE_URL}/api/recovery/cases`);
  if (params?.page) url.searchParams.set("page", params.page.toString());
  if (params?.page_size)
    url.searchParams.set("page_size", params.page_size.toString());
  if (params?.status) url.searchParams.set("status", params.status);
  if (params?.recovery_stage)
    url.searchParams.set("recovery_stage", params.recovery_stage);
  if (params?.search) url.searchParams.set("search", params.search);

  const res = await fetch(url.toString(), { headers, cache: "no-store" });
  if (!res.ok) {
    throw new Error(`Failed to fetch recovery cases: ${res.statusText}`);
  }
  return res.json();
}

export async function fetchRecoveryCaseDetail(
  caseId: string
): Promise<RecoveryCaseDetailResponse> {
  const headers = await getAuthHeaders();
  const res = await fetch(`${API_BASE_URL}/api/recovery/cases/${caseId}`, {
    headers,
    cache: "no-store",
  });
  if (!res.ok) {
    throw new Error(`Failed to fetch case detail: ${res.statusText}`);
  }
  return res.json();
}

export async function fetchHumanReviewQueue(params?: {
  page?: number;
  page_size?: number;
}): Promise<PaginatedHumanReviewResponse> {
  const headers = await getAuthHeaders();
  const url = new URL(`${API_BASE_URL}/api/recovery/human-review`);
  if (params?.page) url.searchParams.set("page", params.page.toString());
  if (params?.page_size)
    url.searchParams.set("page_size", params.page_size.toString());

  const res = await fetch(url.toString(), { headers, cache: "no-store" });
  if (!res.ok) {
    throw new Error(`Failed to fetch human review queue: ${res.statusText}`);
  }
  return res.json();
}

export async function approveHumanReview(
  caseId: string,
  notes?: string
): Promise<HumanReviewActionResponse> {
  const headers = await getAuthHeaders();
  const res = await fetch(
    `${API_BASE_URL}/api/recovery/human-review/${caseId}/approve`,
    {
      method: "POST",
      headers,
      body: JSON.stringify({ notes }),
    }
  );
  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    throw new Error(errorData.detail || "Approval failed");
  }
  return res.json();
}

export async function dismissHumanReview(
  caseId: string,
  notes?: string
): Promise<HumanReviewActionResponse> {
  const headers = await getAuthHeaders();
  const res = await fetch(
    `${API_BASE_URL}/api/recovery/human-review/${caseId}/dismiss`,
    {
      method: "POST",
      headers,
      body: JSON.stringify({ notes }),
    }
  );
  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    throw new Error(errorData.detail || "Dismissal failed");
  }
  return res.json();
}

export async function fetchAuditLogs(params?: {
  page?: number;
  page_size?: number;
  event_type?: string;
  case_id?: string;
}): Promise<PaginatedAuditLogsResponse> {
  const headers = await getAuthHeaders();
  const url = new URL(`${API_BASE_URL}/api/recovery/audit-logs`);
  if (params?.page) url.searchParams.set("page", params.page.toString());
  if (params?.page_size)
    url.searchParams.set("page_size", params.page_size.toString());
  if (params?.event_type) url.searchParams.set("event_type", params.event_type);
  if (params?.case_id) url.searchParams.set("case_id", params.case_id);

  const res = await fetch(url.toString(), { headers, cache: "no-store" });
  if (!res.ok) {
    throw new Error(`Failed to fetch audit logs: ${res.statusText}`);
  }
  return res.json();
}

export interface ModelMetadata {
  model_name: string;
  model_version: string;
}

export interface ClassificationMetrics {
  sample_size: number;
  threshold: number;
  true_positive: number;
  false_positive: number;
  true_negative: number;
  false_negative: number;
  accuracy: number | null;
  precision: number | null;
  recall: number | null;
  f1_score: number | null;
  brier_score: number | null;
}

export interface CalibrationBucket {
  bucket_min: number;
  bucket_max: number;
  sample_size: number;
  predicted_probability_avg: number | null;
  actual_recovery_rate: number | null;
  calibration_error: number | null;
}

export interface ActionAttributionItem {
  action_type: string;
  sample_size: number;
  recovered_count: number;
  failed_count: number;
  recovery_rate: number | null;
  average_confidence: number | null;
  average_recovery_probability: number | null;
}

export interface ConfidenceOutcomeMetrics {
  sample_size: number;
  average_confidence_recovered: number | null;
  average_confidence_failed: number | null;
  confidence_difference: number | null;
  correlation: number | null;
}

export interface PolicyAlignmentItem {
  policy_outcome: string;
  sample_size: number;
  recovered_count: number;
  failed_count: number;
  recovery_rate: number | null;
}

export interface RiskSegmentItem {
  risk_tier: string;
  sample_size: number;
  recovered_count: number;
  failed_count: number;
  recovery_rate: number | null;
  average_recovery_probability: number | null;
}

export interface FailureReasonSegmentItem {
  failure_reason: string;
  sample_size: number;
  recovered_count: number;
  failed_count: number;
  recovery_rate: number | null;
  average_recovery_probability: number | null;
}

export interface ActionDurationItem {
  action_type: string;
  sample_size: number;
  average_hours: number | null;
  median_hours: number | null;
}

export interface PriorityDurationItem {
  priority: string;
  sample_size: number;
  average_hours: number | null;
  median_hours: number | null;
}

export interface RecoveryDurationMetrics {
  sample_size: number;
  overall_average_hours: number | null;
  overall_median_hours: number | null;
  by_action_type: ActionDurationItem[];
  by_priority: PriorityDurationItem[];
}

export interface IntelligenceEvaluationResponse {
  generated_at: string;
  model: ModelMetadata;
  classification: ClassificationMetrics;
  calibration: CalibrationBucket[];
  action_attribution: ActionAttributionItem[];
  confidence_outcomes: ConfidenceOutcomeMetrics;
  policy_alignment: PolicyAlignmentItem[];
  risk_segments: RiskSegmentItem[];
  failure_reason_segments: FailureReasonSegmentItem[];
  recovery_duration: RecoveryDurationMetrics;
}

export async function fetchIntelligenceEvaluation(): Promise<IntelligenceEvaluationResponse> {
  const headers = await getAuthHeaders();
  const res = await fetch(`${API_BASE_URL}/api/recovery/intelligence/evaluation`, {
    headers,
    cache: "no-store",
  });
  if (!res.ok) {
    throw new Error(`Failed to fetch intelligence evaluation: ${res.statusText}`);
  }
  return res.json();
}

export interface GovernanceFinding {
  code: string;
  severity: string;
  message: string;
  metric_name: string | null;
  baseline_value: number | null;
  recent_value: number | null;
  delta: number | null;
}

export interface PerformanceWindow {
  window_name: string;
  window_days: number | null;
  sample_size: number;
  accuracy: number | null;
  precision: number | null;
  recall: number | null;
  f1_score: number | null;
  brier_score: number | null;
  recovery_rate: number | null;
}

export interface PerformanceComparison {
  baseline_window: string;
  recent_window: string;
  baseline_sample_size: number;
  recent_sample_size: number;
  accuracy_delta: number | null;
  precision_delta: number | null;
  recall_delta: number | null;
  f1_delta: number | null;
  brier_delta: number | null;
  recovery_rate_delta: number | null;
}

export interface FeatureDrift {
  feature_name: string;
  feature_type: string;
  psi: number | null;
  drift_level: string;
  reference_sample_size: number;
  recent_sample_size: number;
  details: Record<string, unknown>;
}

export interface PredictionBucketDrift {
  bucket_min: number;
  bucket_max: number;
  historical_percentage: number | null;
  recent_percentage: number | null;
  delta: number | null;
}

export interface PredictionDistributionDrift {
  psi: number | null;
  drift_level: string;
  buckets: PredictionBucketDrift[];
}

export interface OutcomeDrift {
  historical_recovery_rate: number | null;
  recent_recovery_rate: number | null;
  delta: number | null;
  drift_level: string;
}

export interface CalibrationBucketDrift {
  bucket_min: number;
  bucket_max: number;
  historical_pred_avg: number | null;
  historical_recovery_rate: number | null;
  historical_calibration_error: number | null;
  recent_pred_avg: number | null;
  recent_recovery_rate: number | null;
  recent_calibration_error: number | null;
  calibration_error_delta: number | null;
}

export interface ModelVersionSummary {
  model_name: string;
  model_version: string;
  sample_size: number;
  first_seen: string | null;
  last_seen: string | null;
  accuracy: number | null;
  brier_score: number | null;
  recovery_rate: number | null;
}

export interface ModelVersionComparison {
  baseline_version: string;
  comparison_version: string;
  baseline_sample_size: number;
  comparison_sample_size: number;
  accuracy_delta: number | null;
  f1_delta: number | null;
  brier_delta: number | null;
  evidence_statement: string;
}

export interface DataQualitySummary {
  total_predictions: number;
  valid_predictions: number;
  invalid_predictions: number;
  missing_feature_vectors: number;
  missing_model_versions: number;
  invalid_probability_count: number;
  missing_timestamps: number;
}

export interface ModelGovernanceResponse {
  status: string;
  model_name: string;
  model_version: string;
  sample_size: number;
  minimum_required_sample_size: number;
  first_prediction_at: string | null;
  last_prediction_at: string | null;
  performance_windows: PerformanceWindow[];
  performance_comparison: PerformanceComparison;
  feature_drift: FeatureDrift[];
  prediction_drift: PredictionDistributionDrift;
  outcome_drift: OutcomeDrift;
  calibration_drift: CalibrationBucketDrift[];
  model_versions: ModelVersionSummary[];
  version_comparisons: ModelVersionComparison[];
  data_quality: DataQualitySummary;
  findings: GovernanceFinding[];
  warnings: string[];
  critical_findings: string[];
  generated_at: string;
}

export async function fetchModelGovernance(): Promise<ModelGovernanceResponse> {
  const headers = await getAuthHeaders();
  const res = await fetch(`${API_BASE_URL}/api/recovery/intelligence/governance`, {
    headers,
    cache: "no-store",
  });
  if (!res.ok) {
    throw new Error(`Failed to fetch model governance: ${res.statusText}`);
  }
  return res.json();
}

export interface ExpectedRecoveryValue {
  amount_at_risk: number;
  recovery_probability: number;
  expected_recovery_value: number;
}

export interface StrategyPerformance {
  action_type: string;
  sample_size: number;
  recovered_count: number;
  failed_count: number;
  recovery_rate: number | null;
  average_recovery_probability: number | null;
  average_confidence: number | null;
  amount_at_risk: number;
  amount_recovered: number;
  recovery_amount_rate: number | null;
  reliability: string;
}

export interface DelayPerformance {
  delay_hours: number;
  sample_size: number;
  recovered_count: number;
  recovery_rate: number | null;
  average_recovery_probability: number | null;
  amount_at_risk: number;
  amount_recovered: number;
  reliability: string;
}

export interface SegmentStrategyRecommendation {
  segment_type: string;
  segment_value: string;
  sample_size: number;
  best_action_type: string | null;
  best_delay_hours: number | null;
  recovery_rate: number | null;
  amount_at_risk: number;
  expected_recovery_value: number;
  reliability: string;
  recommendation_reason: string;
}

export interface OptimizationRecommendation {
  action_type: string | null;
  recommended_delay_hours: number | null;
  sample_size: number;
  recovery_probability: number | null;
  recovery_rate: number | null;
  average_confidence: number | null;
  expected_recovery_value: number;
  confidence_level: string;
  recommendation_reason: string;
}

export interface OptimizationFinding {
  code: string;
  severity: string;
  message: string;
}

export interface StrategyOptimizationResponse {
  generated_at: string;
  sample_size: number;
  overall_recommendation: OptimizationRecommendation;
  expected_recovery_value_summary: ExpectedRecoveryValue;
  strategies: StrategyPerformance[];
  delay_analysis: DelayPerformance[];
  segment_recommendations: SegmentStrategyRecommendation[];
  diagnostic_findings: OptimizationFinding[];
}

export async function fetchStrategyOptimization(): Promise<StrategyOptimizationResponse> {
  const headers = await getAuthHeaders();
  const res = await fetch(`${API_BASE_URL}/api/recovery/intelligence/optimization`, {
    headers,
    cache: "no-store",
  });
  if (!res.ok) {
    throw new Error(`Failed to fetch strategy optimization: ${res.statusText}`);
  }
  return res.json();
}

export interface SimulationRequest {
  current_action_type: string;
  current_delay_hours: number;
  alternative_action_type: string;
  alternative_delay_hours: number;
  risk_tier?: string | null;
  failure_reason?: string | null;
  attempt_number?: number | null;
  amount_band?: string | null;
  amount_at_risk_paise?: number | null;
}

export interface StrategyMetrics {
  action_type: string;
  delay_hours: number;
  sample_size: number;
  recovered_count: number;
  failed_count: number;
  recovery_rate: number | null;
  financial_yield: number | null;
  average_recovery_probability: number | null;
  amount_at_risk_paise: number;
  amount_recovered_paise: number;
  expected_recovery_value_paise: number | null;
  reliability: string;
}

export interface EstimatedStrategyUplift {
  recovery_rate_delta: number | null;
  relative_uplift_pct: number | null;
  financial_yield_delta: number | null;
  estimated_incremental_erv_paise: number | null;
  confidence_assessment: string;
}

export interface ComparablePopulationMetadata {
  total_cases_analyzed: number;
  matching_criteria: Record<string, any>;
  segmentation_level_used: string;
  filter_summary: string;
}

export interface SimulationDiagnostic {
  code: string;
  severity: string;
  message: string;
}

export interface CounterfactualSimulationResponse {
  generated_at: string;
  request_parameters: SimulationRequest;
  population: ComparablePopulationMetadata;
  current_strategy: StrategyMetrics;
  alternative_strategy: StrategyMetrics;
  estimated_uplift: EstimatedStrategyUplift;
  diagnostics: SimulationDiagnostic[];
  observational_disclaimer: string;
}

export async function fetchCounterfactualSimulation(
  payload: SimulationRequest
): Promise<CounterfactualSimulationResponse> {
  const headers = await getAuthHeaders();
  const res = await fetch(`${API_BASE_URL}/api/recovery/intelligence/simulation`, {
    method: "POST",
    headers: {
      ...headers,
      "Content-Type": "application/json",
    },
    body: JSON.stringify(payload),
    cache: "no-store",
  });
  if (!res.ok) {
    throw new Error(`Failed to execute counterfactual simulation: ${res.statusText}`);
  }
  return res.json();
}

export interface EvaluationEvidence {
  sample_size: number;
  accuracy: number | null;
  precision: number | null;
  recall: number | null;
  f1_score: number | null;
  brier_score: number | null;
}

export interface GovernanceEvidence {
  model_health: string;
  drift_status: string;
  prediction_psi: number | null;
  data_quality_status: string;
  model_version: string;
}

export interface OptimizationEvidence {
  champion_strategy: string | null;
  champion_recovery_rate: number | null;
  champion_financial_yield: number | null;
  champion_erv_paise: number | null;
  strategy_sample_size: number;
}

export interface SimulationEvidence {
  baseline_strategy: string;
  alternative_strategy: string;
  comparable_population_size: number;
  population_match_type: string;
  baseline_recovery_rate: number | null;
  alternative_recovery_rate: number | null;
  rate_delta: number | null;
  relative_uplift_pct: number | null;
  incremental_erv_paise: number | null;
  simulation_reliability: string;
}

export interface EvidenceBundle {
  evaluation: EvaluationEvidence;
  governance: GovernanceEvidence;
  optimization: OptimizationEvidence;
  simulation: SimulationEvidence;
}

export interface StrategyRecommendationResponse {
  recommendation_id: string;
  strategy_type: string;
  retry_delay_hours: number;
  status: string;
  created_at: string;
  expires_at: string;
  model_version: string;
  sample_size: number;
  reliability: string;
  recommendation_confidence: number;
  confidence_level: string;
  baseline_recovery_rate: number | null;
  alternative_recovery_rate: number | null;
  rate_delta: number | null;
  relative_uplift_pct: number | null;
  baseline_erv_paise: number | null;
  alternative_erv_paise: number | null;
  incremental_erv_paise: number | null;
  governance_status: string;
  reasoning: string;
  diagnostics: string[];
  evidence: EvidenceBundle;
  reviewed_by: string | null;
  reviewed_at: string | null;
  review_notes: string | null;
  observational_disclaimer: string;
}

export interface PaginatedRecommendationsResponse {
  items: StrategyRecommendationResponse[];
  total: number;
  active_recommendation: StrategyRecommendationResponse | null;
}

export async function fetchStrategyRecommendations(): Promise<PaginatedRecommendationsResponse> {
  const headers = await getAuthHeaders();
  const res = await fetch(`${API_BASE_URL}/api/recovery/intelligence/recommendations`, {
    headers,
    cache: "no-store",
  });
  if (!res.ok) {
    throw new Error(`Failed to fetch recommendations: ${res.statusText}`);
  }
  return res.json();
}

export async function fetchStrategyRecommendationDetail(
  id: string
): Promise<StrategyRecommendationResponse> {
  const headers = await getAuthHeaders();
  const res = await fetch(`${API_BASE_URL}/api/recovery/intelligence/recommendations/${id}`, {
    headers,
    cache: "no-store",
  });
  if (!res.ok) {
    throw new Error(`Failed to fetch recommendation detail: ${res.statusText}`);
  }
  return res.json();
}

export async function approveStrategyRecommendation(
  id: string,
  notes?: string
): Promise<StrategyRecommendationResponse> {
  const headers = await getAuthHeaders();
  const res = await fetch(`${API_BASE_URL}/api/recovery/intelligence/recommendations/${id}/approve`, {
    method: "POST",
    headers: {
      ...headers,
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ notes: notes || null }),
    cache: "no-store",
  });
  if (!res.ok) {
    const errorBody = await res.json().catch(() => ({}));
    throw new Error(errorBody.detail || `Failed to approve recommendation: ${res.statusText}`);
  }
  return res.json();
}

export async function rejectStrategyRecommendation(
  id: string,
  notes?: string
): Promise<StrategyRecommendationResponse> {
  const headers = await getAuthHeaders();
  const res = await fetch(`${API_BASE_URL}/api/recovery/intelligence/recommendations/${id}/reject`, {
    method: "POST",
    headers: {
      ...headers,
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ notes: notes || null }),
    cache: "no-store",
  });
  if (!res.ok) {
    const errorBody = await res.json().catch(() => ({}));
    throw new Error(errorBody.detail || `Failed to reject recommendation: ${res.statusText}`);
  }
  return res.json();
}

export function formatINR(paise: number): string {
  const rupees = (paise / 100).toLocaleString("en-IN", {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  });
  return `₹${rupees}`;
}

export interface ActivationExperimentMetrics {
  sample_size: number;
  recovered_count: number;
  failed_count: number;
  recovery_rate: number | null;
  amount_at_risk_paise: number;
  amount_recovered_paise: number;
  financial_yield: number | null;
  expected_recovery_value_paise: number | null;
  mean_time_to_recovery_hours: number | null;
  median_time_to_recovery_hours: number | null;
}

export interface ActivationUpliftMetrics {
  absolute_uplift: number | null;
  relative_uplift_pct: number | null;
  incremental_recovered_amount_paise: number | null;
  incremental_expected_recovery_value_paise: number | null;
}

export interface ActivationConfidenceInterval {
  lower_bound: number | null;
  upper_bound: number | null;
  confidence_level: number;
  is_significant: boolean;
}

export interface ActivationStrategyComparison {
  control_metrics: ActivationExperimentMetrics;
  treatment_metrics: ActivationExperimentMetrics;
  uplift: ActivationUpliftMetrics;
  confidence_interval: ActivationConfidenceInterval;
  reliability: string;
}

export interface ActivationRolloutHealth {
  status: string;
  diagnostics: string[];
  evaluated_at: string;
}

export interface StrategyActivationResponse {
  activation_id: string;
  recommendation_id: string;
  strategy_type: string;
  status: string;
  rollout_percentage: number;
  target_segment: Record<string, any> | null;
  model_version: string;
  governance_version: string;
  effective_from: string;
  expires_at: string;
  approved_by: string | null;
  approved_at: string | null;
  activated_by: string | null;
  activated_at: string | null;
  paused_by: string | null;
  paused_at: string | null;
  rolled_back_by: string | null;
  rolled_back_at: string | null;
  created_at: string;
  updated_at: string;
  comparison: ActivationStrategyComparison | null;
  health: ActivationRolloutHealth;
  notes: string | null;
  observational_disclaimer: string;
}

export interface PaginatedActivationsResponse {
  items: StrategyActivationResponse[];
  total: number;
  active_activation: StrategyActivationResponse | null;
}

export async function fetchStrategyActivations(): Promise<PaginatedActivationsResponse> {
  const headers = await getAuthHeaders();
  const res = await fetch(`${API_BASE_URL}/api/recovery/intelligence/activations`, {
    headers,
    cache: "no-store",
  });
  if (!res.ok) {
    throw new Error(`Failed to fetch activations: ${res.statusText}`);
  }
  return res.json();
}

export async function fetchStrategyActivationDetail(
  id: string
): Promise<StrategyActivationResponse> {
  const headers = await getAuthHeaders();
  const res = await fetch(`${API_BASE_URL}/api/recovery/intelligence/activations/${id}`, {
    headers,
    cache: "no-store",
  });
  if (!res.ok) {
    throw new Error(`Failed to fetch activation detail: ${res.statusText}`);
  }
  return res.json();
}

export async function createStrategyActivation(
  recommendationId: string,
  targetSegment?: Record<string, any> | null,
  notes?: string
): Promise<StrategyActivationResponse> {
  const headers = await getAuthHeaders();
  const res = await fetch(`${API_BASE_URL}/api/recovery/intelligence/activations/create`, {
    method: "POST",
    headers: {
      ...headers,
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      recommendation_id: recommendationId,
      target_segment: targetSegment || null,
      notes: notes || null,
    }),
    cache: "no-store",
  });
  if (!res.ok) {
    const errorBody = await res.json().catch(() => ({}));
    throw new Error(errorBody.detail || `Failed to create activation: ${res.statusText}`);
  }
  return res.json();
}

export async function startCanaryRollout(
  id: string,
  rolloutPercentage: number,
  notes?: string
): Promise<StrategyActivationResponse> {
  const headers = await getAuthHeaders();
  const res = await fetch(`${API_BASE_URL}/api/recovery/intelligence/activations/${id}/start-canary`, {
    method: "POST",
    headers: {
      ...headers,
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      rollout_percentage: rolloutPercentage,
      notes: notes || null,
    }),
    cache: "no-store",
  });
  if (!res.ok) {
    const errorBody = await res.json().catch(() => ({}));
    throw new Error(errorBody.detail || `Failed to start canary: ${res.statusText}`);
  }
  return res.json();
}

export async function pauseStrategyActivation(
  id: string,
  notes?: string
): Promise<StrategyActivationResponse> {
  const headers = await getAuthHeaders();
  const res = await fetch(`${API_BASE_URL}/api/recovery/intelligence/activations/${id}/pause`, {
    method: "POST",
    headers: {
      ...headers,
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ notes: notes || null }),
    cache: "no-store",
  });
  if (!res.ok) {
    const errorBody = await res.json().catch(() => ({}));
    throw new Error(errorBody.detail || `Failed to pause activation: ${res.statusText}`);
  }
  return res.json();
}

export async function rollbackStrategyActivation(
  id: string,
  notes?: string
): Promise<StrategyActivationResponse> {
  const headers = await getAuthHeaders();
  const res = await fetch(`${API_BASE_URL}/api/recovery/intelligence/activations/${id}/rollback`, {
    method: "POST",
    headers: {
      ...headers,
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ notes: notes || null }),
    cache: "no-store",
  });
  if (!res.ok) {
    const errorBody = await res.json().catch(() => ({}));
    throw new Error(errorBody.detail || `Failed to rollback activation: ${res.statusText}`);
  }
  return res.json();
}

export async function activateStrategyRollout(
  id: string,
  notes?: string
): Promise<StrategyActivationResponse> {
  const headers = await getAuthHeaders();
  const res = await fetch(`${API_BASE_URL}/api/recovery/intelligence/activations/${id}/activate`, {
    method: "POST",
    headers: {
      ...headers,
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ notes: notes || null }),
    cache: "no-store",
  });
  if (!res.ok) {
    const errorBody = await res.json().catch(() => ({}));
    throw new Error(errorBody.detail || `Failed to promote activation: ${res.statusText}`);
  }
  return res.json();
}

// -------------------------------------------------------------
// Phase 9G: Production Strategy Promotion & Continuous Monitoring
// -------------------------------------------------------------

export interface PromotionCheckItem {
  rule: string;
  passed: boolean;
  value?: any;
  required?: any;
  message?: string;
}

export interface PromotionReadinessResponse {
  activation_id: string;
  strategy_type: string;
  strategy_version: string;
  model_version: string;
  eligible: boolean;
  status: string;
  sample_size: number;
  treatment_recovery_rate: number | null;
  control_recovery_rate: number | null;
  absolute_uplift: number | null;
  relative_uplift_pct: number | null;
  incremental_erv_paise: number | null;
  confidence_interval_low: number | null;
  confidence_interval_high: number | null;
  model_health: string;
  data_quality: string;
  rollback_recommended: boolean;
  checks: PromotionCheckItem[];
  blockers: string[];
  evaluated_at: string;
  disclaimer: string;
}

export interface ProductionMonitoringResponse {
  status: string;
  strategy_id: string | null;
  strategy_name: string | null;
  strategy_version: string | null;
  model_version: string | null;
  activation_id: string | null;
  recommendation_id: string | null;
  rollout_percentage: number;
  sample_size: number;
  treatment_sample_size: number;
  control_sample_size: number;
  recovery_rate: number | null;
  control_recovery_rate: number | null;
  absolute_uplift: number | null;
  relative_uplift_pct: number | null;
  incremental_erv_paise: number | null;
  financial_yield: number | null;
  mttr_hours: number | null;
  model_health: string;
  prediction_psi: number | null;
  drift_status: string;
  rollback_recommended: boolean;
  diagnostics: string[];
  promoted_at: string | null;
  promoted_by: string | null;
  last_evaluated: string;
  disclaimer: string;
}

export async function fetchProductionMonitoring(): Promise<ProductionMonitoringResponse> {
  const headers = await getAuthHeaders();
  const res = await fetch(`${API_BASE_URL}/api/recovery/intelligence/production`, {
    headers,
    cache: "no-store",
  });
  if (!res.ok) {
    const errorBody = await res.json().catch(() => ({}));
    throw new Error(errorBody.detail || `Failed to fetch production monitoring: ${res.statusText}`);
  }
  return res.json();
}

export async function fetchPromotionReadiness(
  activationId: string
): Promise<PromotionReadinessResponse> {
  const headers = await getAuthHeaders();
  const res = await fetch(
    `${API_BASE_URL}/api/recovery/intelligence/activations/${activationId}/promotion-readiness`,
    {
      headers,
      cache: "no-store",
    }
  );
  if (!res.ok) {
    const errorBody = await res.json().catch(() => ({}));
    throw new Error(errorBody.detail || `Failed to fetch promotion readiness: ${res.statusText}`);
  }
  return res.json();
}

export async function promoteProductionStrategy(
  activationId: string,
  reason?: string
): Promise<StrategyActivationResponse> {
  const headers = await getAuthHeaders();
  const res = await fetch(
    `${API_BASE_URL}/api/recovery/intelligence/activations/${activationId}/promote`,
    {
      method: "POST",
      headers: {
        ...headers,
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ reason: reason || null }),
      cache: "no-store",
    }
  );
  if (!res.ok) {
    const errorBody = await res.json().catch(() => ({}));
    throw new Error(errorBody.detail || `Failed to promote strategy to production: ${res.statusText}`);
  }
  return res.json();
}

// =========================================================================
// Phase 9H: Causal Experimentation, Statistical Significance & Decision Intelligence
// =========================================================================

export type ExperimentStatus =
  | "DRAFT"
  | "APPROVED"
  | "RUNNING"
  | "PAUSED"
  | "STOPPED"
  | "COMPLETED"
  | "CANCELLED"
  | "ARCHIVED";

export type CohortType = "CONTROL" | "TREATMENT";
export type BalanceStatus = "BALANCED" | "MINOR_IMBALANCE" | "MAJOR_IMBALANCE";
export type CausalEvidenceLevel = "LEVEL_0" | "LEVEL_1" | "LEVEL_2" | "LEVEL_3";
export type ExperimentDecisionType =
  | "CONTINUE"
  | "STOP_RECOMMENDED"
  | "PROMOTE_TO_REVIEW"
  | "INSUFFICIENT_DATA";

export interface PopulationDefinition {
  risk_tier?: string | null;
  failure_reason?: string | null;
  min_amount_paise?: number | null;
  max_amount_paise?: number | null;
  min_attempts?: number | null;
  max_attempts?: number | null;
}

export interface ExperimentRequest {
  name: string;
  description?: string | null;
  treatment_strategy: string;
  control_strategy: string;
  allocation_percentage?: number;
  population_definition?: PopulationDefinition | null;
  model_version?: string | null;
  notes?: string | null;
}

export interface ExperimentActionRequest {
  notes?: string | null;
}

export interface ExperimentCohortMetrics {
  cohort_type: string;
  sample_size: number;
  recovered_count: number;
  failed_count: number;
  recovery_rate: number | null;
  amount_at_risk_paise: number;
  amount_recovered_paise: number;
  financial_yield: number | null;
  expected_recovery_value_paise: number;
  mttr_hours: number | null;
  failure_rate: number | null;
  average_attempts: number | null;
}

export interface CausalEffectEstimate {
  absolute_treatment_effect: number | null;
  relative_uplift_pct: number | null;
  incremental_recovered_cases_estimate: number | null;
  incremental_erv_paise: number | null;
}

export interface StatisticalTestResult {
  test_name: string;
  test_statistic: number | null;
  p_value: number | null;
  alpha: number;
  statistically_significant: boolean;
  confidence_interval_low: number | null;
  confidence_interval_high: number | null;
  confidence_level: number;
}

export interface BalanceFeatureMetric {
  feature_name: string;
  control_distribution: Record<string, number>;
  treatment_distribution: Record<string, number>;
  max_absolute_difference: number;
  status: string;
}

export interface BalanceDiagnostics {
  overall_status: string;
  is_confounded: boolean;
  features: BalanceFeatureMetric[];
  diagnostics: string[];
}

export interface DataQualityReport {
  data_quality_status: string;
  missing_outcomes: number;
  missing_predictions: number;
  diagnostics: string[];
}

export interface OverlapDiagnostics {
  has_overlap: boolean;
  conflicting_experiment_ids: string[];
  diagnostics: string[];
}

export interface StoppingDiagnostics {
  stop_recommended: boolean;
  reasons: string[];
}

export interface ExperimentDecisionResult {
  decision: string;
  evidence_level: string;
  confidence_interval_95: { low: number | null; high: number | null };
  sample_size_valid: boolean;
  balance_valid: boolean;
  significance_valid: boolean;
  diagnostics: string[];
}

export interface ExperimentResponse {
  experiment_id: string;
  name: string;
  description: string | null;
  status: string;
  treatment_strategy: string;
  control_strategy: string;
  allocation_percentage: number;
  population_definition: PopulationDefinition;
  model_version: string;
  created_by: string;
  created_at: string;
  started_at: string | null;
  ended_at: string | null;
  runtime_hours: number | null;
  notes: string | null;
  sample_size?: number;
  disclaimer: string;
}

export interface ExperimentAnalysisResponse {
  experiment_id: string;
  name: string;
  status: string;
  treatment_strategy: string;
  control_strategy: string;
  allocation_percentage: number;
  assignment_method: string;
  sample_size: number;
  control_cohort: ExperimentCohortMetrics;
  treatment_cohort: ExperimentCohortMetrics;
  causal_effect: CausalEffectEstimate;
  statistical_test: StatisticalTestResult;
  balance_diagnostics: BalanceDiagnostics;
  data_quality: DataQualityReport;
  overlap_diagnostics: OverlapDiagnostics;
  stopping_diagnostics: StoppingDiagnostics;
  decision: ExperimentDecisionResult;
  runtime_hours: number | null;
  last_evaluated: string;
  disclaimer: string;
}

export interface PaginatedExperimentsResponse {
  items: ExperimentResponse[];
  total: number;
  active_count: number;
  disclaimer: string;
}

export async function fetchExperiments(
  statusFilter?: string,
  page = 1,
  pageSize = 20
): Promise<PaginatedExperimentsResponse> {
  const headers = await getAuthHeaders();
  const query = new URLSearchParams();
  if (statusFilter && statusFilter !== "ALL") query.set("status", statusFilter);
  query.set("page", page.toString());
  query.set("page_size", pageSize.toString());

  const res = await fetch(`${API_BASE_URL}/api/recovery/intelligence/experiments?${query}`, {
    headers,
    cache: "no-store",
  });
  if (!res.ok) {
    const errorBody = await res.json().catch(() => ({}));
    throw new Error(errorBody.detail || `Failed to fetch experiments: ${res.statusText}`);
  }
  return res.json();
}

export async function fetchExperimentDetail(
  experimentId: string
): Promise<ExperimentResponse> {
  const headers = await getAuthHeaders();
  const res = await fetch(
    `${API_BASE_URL}/api/recovery/intelligence/experiments/${experimentId}`,
    {
      headers,
      cache: "no-store",
    }
  );
  if (!res.ok) {
    const errorBody = await res.json().catch(() => ({}));
    throw new Error(errorBody.detail || `Failed to fetch experiment detail: ${res.statusText}`);
  }
  return res.json();
}

export async function fetchExperimentAnalysis(
  experimentId: string
): Promise<ExperimentAnalysisResponse> {
  const headers = await getAuthHeaders();
  const res = await fetch(
    `${API_BASE_URL}/api/recovery/intelligence/experiments/${experimentId}/analysis`,
    {
      headers,
      cache: "no-store",
    }
  );
  if (!res.ok) {
    const errorBody = await res.json().catch(() => ({}));
    throw new Error(errorBody.detail || `Failed to fetch experiment analysis: ${res.statusText}`);
  }
  return res.json();
}

export async function createExperiment(
  payload: ExperimentRequest
): Promise<ExperimentResponse> {
  const headers = await getAuthHeaders();
  const res = await fetch(`${API_BASE_URL}/api/recovery/intelligence/experiments`, {
    method: "POST",
    headers: {
      ...headers,
      "Content-Type": "application/json",
    },
    body: JSON.stringify(payload),
    cache: "no-store",
  });
  if (!res.ok) {
    const errorBody = await res.json().catch(() => ({}));
    throw new Error(errorBody.detail || `Failed to create experiment: ${res.statusText}`);
  }
  return res.json();
}

export async function startExperiment(
  experimentId: string,
  notes?: string
): Promise<ExperimentResponse> {
  const headers = await getAuthHeaders();
  const res = await fetch(
    `${API_BASE_URL}/api/recovery/intelligence/experiments/${experimentId}/start`,
    {
      method: "POST",
      headers: {
        ...headers,
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ notes: notes || null }),
      cache: "no-store",
    }
  );
  if (!res.ok) {
    const errorBody = await res.json().catch(() => ({}));
    throw new Error(errorBody.detail || `Failed to start experiment: ${res.statusText}`);
  }
  return res.json();
}

export async function pauseExperiment(
  experimentId: string,
  notes?: string
): Promise<ExperimentResponse> {
  const headers = await getAuthHeaders();
  const res = await fetch(
    `${API_BASE_URL}/api/recovery/intelligence/experiments/${experimentId}/pause`,
    {
      method: "POST",
      headers: {
        ...headers,
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ notes: notes || null }),
      cache: "no-store",
    }
  );
  if (!res.ok) {
    const errorBody = await res.json().catch(() => ({}));
    throw new Error(errorBody.detail || `Failed to pause experiment: ${res.statusText}`);
  }
  return res.json();
}

export async function completeExperiment(
  experimentId: string,
  notes?: string
): Promise<ExperimentResponse> {
  const headers = await getAuthHeaders();
  const res = await fetch(
    `${API_BASE_URL}/api/recovery/intelligence/experiments/${experimentId}/complete`,
    {
      method: "POST",
      headers: {
        ...headers,
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ notes: notes || null }),
      cache: "no-store",
    }
  );
  if (!res.ok) {
    const errorBody = await res.json().catch(() => ({}));
    throw new Error(errorBody.detail || `Failed to complete experiment: ${res.statusText}`);
  }
  return res.json();
}


// =============================================================================
// Phase 9I: Governed Model Lifecycle & Champion-Challenger Types
// =============================================================================

export type ModelLifecycleStatus =
  | "DRAFT"
  | "TRAINING"
  | "VALIDATING"
  | "REVIEW_REQUIRED"
  | "APPROVED"
  | "PROMOTION_READY"
  | "ACTIVE"
  | "RETIRED"
  | "REJECTED"
  | "FAILED";

export interface ModelMetricsSnapshot {
  sample_size: number;
  accuracy: number;
  precision: number;
  recall: number;
  f1_score: number;
  brier_score: number;
  calibration_error: number;
  roc_auc: number;
  pr_auc: number;
  log_loss?: number | null;
}

export interface MetricDelta {
  metric_name: string;
  champion_value: number;
  challenger_value: number;
  delta: number;
  status: "IMPROVED" | "REGRESSED" | "UNCHANGED";
}

export interface ModelQualityGateResult {
  gate_code: string;
  passed: boolean;
  observed_value: string | number;
  threshold: string | number;
  explanation: string;
}

export interface ChampionChallengerComparison {
  champion_version: string;
  challenger_version: string;
  metrics_deltas: MetricDelta[];
  overall_status: "IMPROVED" | "REGRESSED" | "UNCHANGED";
}

export interface TrainingDatasetMetadata {
  sample_size: number;
  positive_count: number;
  negative_count: number;
  class_balance: number;
  feature_names: string[];
  feature_schema_version: string;
  dataset_hash: string;
  temporal_range_start?: string | null;
  temporal_range_end?: string | null;
}

export interface TrainingDatasetSplit {
  training_sample_size: number;
  validation_sample_size: number;
  training_dataset_hash: string;
  validation_dataset_hash: string;
  split_ratio: number;
}

export interface ModelScorecardResponse {
  model_name: string;
  challenger_version: string;
  parent_champion_version: string;
  lifecycle_status: ModelLifecycleStatus;
  champion_metrics: ModelMetricsSnapshot;
  challenger_metrics: ModelMetricsSnapshot;
  comparison: ChampionChallengerComparison;
  gates: ModelQualityGateResult[];
  recommendation:
    | "KEEP_CHAMPION"
    | "PROMOTE_CHALLENGER_REVIEW"
    | "INSUFFICIENT_DATA"
    | "REJECT_CHALLENGER";
  confidence: number;
  evidence_level: string;
  dataset_metadata: TrainingDatasetMetadata;
  training_split: TrainingDatasetSplit;
  model_artifact_hash: string;
  created_at: string;
  evaluated_at: string;
}

export interface ModelSummaryResponse {
  model_name: string;
  model_version: string;
  lifecycle_status: ModelLifecycleStatus;
  model_type: string;
  feature_schema_version: string;
  training_sample_size: number;
  validation_sample_size: number;
  training_started_at?: string | null;
  validation_completed_at?: string | null;
  created_at: string;
  approved_at?: string | null;
  activated_at?: string | null;
  retired_at?: string | null;
  training_dataset_hash: string;
  model_artifact_hash: string;
  parent_model_version?: string | null;
  approval_actor?: string | null;
  rejection_reason?: string | null;
  metrics_snapshot?: ModelMetricsSnapshot | null;
  recommendation?: string | null;
}

export interface PaginatedModelsResponse {
  items: ModelSummaryResponse[];
  total: number;
  active_champion_version: string;
  promotion_ready_version?: string | null;
}

export async function fetchModels(statusFilter?: string): Promise<PaginatedModelsResponse> {
  const headers = await getAuthHeaders();
  const url = new URL(`${API_BASE_URL}/api/recovery/intelligence/models`);
  if (statusFilter && statusFilter !== "ALL") {
    url.searchParams.set("status", statusFilter);
  }

  const res = await fetch(url.toString(), {
    headers,
    cache: "no-store",
  });
  if (!res.ok) {
    const errorBody = await res.json().catch(() => ({}));
    throw new Error(errorBody.detail || `Failed to fetch models: ${res.statusText}`);
  }
  return res.json();
}

export async function fetchModelDetail(version: string): Promise<ModelSummaryResponse> {
  const headers = await getAuthHeaders();
  const res = await fetch(
    `${API_BASE_URL}/api/recovery/intelligence/models/${version}`,
    {
      headers,
      cache: "no-store",
    }
  );
  if (!res.ok) {
    const errorBody = await res.json().catch(() => ({}));
    throw new Error(errorBody.detail || `Failed to fetch model details: ${res.statusText}`);
  }
  return res.json();
}

export async function fetchModelScorecard(version: string): Promise<ModelScorecardResponse> {
  const headers = await getAuthHeaders();
  const res = await fetch(
    `${API_BASE_URL}/api/recovery/intelligence/models/${version}/scorecard`,
    {
      headers,
      cache: "no-store",
    }
  );
  if (!res.ok) {
    const errorBody = await res.json().catch(() => ({}));
    throw new Error(errorBody.detail || `Failed to fetch model scorecard: ${res.statusText}`);
  }
  return res.json();
}

export async function trainCandidateModel(payload: {
  model_name: string;
  parent_version?: string;
  learning_rate?: number;
  epochs?: number;
  notes?: string;
}): Promise<ModelScorecardResponse> {
  const headers = await getAuthHeaders();
  const res = await fetch(
    `${API_BASE_URL}/api/recovery/intelligence/models/train`,
    {
      method: "POST",
      headers: {
        ...headers,
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        model_name: payload.model_name,
        parent_version: payload.parent_version || "v1.0",
        learning_rate: payload.learning_rate || 0.05,
        epochs: payload.epochs || 50,
        notes: payload.notes || null,
      }),
      cache: "no-store",
    }
  );
  if (!res.ok) {
    const errorBody = await res.json().catch(() => ({}));
    throw new Error(errorBody.detail || `Failed to train candidate model: ${res.statusText}`);
  }
  return res.json();
}

export async function approveModel(
  version: string,
  notes?: string
): Promise<ModelSummaryResponse> {
  const headers = await getAuthHeaders();
  const res = await fetch(
    `${API_BASE_URL}/api/recovery/intelligence/models/${version}/approve`,
    {
      method: "POST",
      headers: {
        ...headers,
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ notes: notes || null }),
      cache: "no-store",
    }
  );
  if (!res.ok) {
    const errorBody = await res.json().catch(() => ({}));
    throw new Error(errorBody.detail || `Failed to approve model: ${res.statusText}`);
  }
  return res.json();
}

export async function rejectModel(
  version: string,
  reason: string
): Promise<ModelSummaryResponse> {
  const headers = await getAuthHeaders();
  const res = await fetch(
    `${API_BASE_URL}/api/recovery/intelligence/models/${version}/reject`,
    {
      method: "POST",
      headers: {
        ...headers,
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ reason }),
      cache: "no-store",
    }
  );
  if (!res.ok) {
    const errorBody = await res.json().catch(() => ({}));
    throw new Error(errorBody.detail || `Failed to reject model: ${res.statusText}`);
  }
  return res.json();
}


// =============================================================================
// Phase 9J: Governed Model Deployment, Shadow Mode & Champion–Challenger
// =============================================================================

export interface DeploymentMetricsSnapshot {
  sample_size: number;
  recovered_count: number;
  failed_count: number;
  recovery_rate: number | null;
  accuracy: number;
  precision: number;
  recall: number;
  f1_score: number;
  brier_score: number;
  mean_probability: number;
}

export interface ShadowComparisonMetric {
  metric_name: string;
  champion_value: number | null;
  challenger_value: number | null;
  delta: number | null;
  status: "IMPROVED" | "REGRESSED" | "UNCHANGED";
}

export interface CalibrationBucketComparison {
  bucket_range: string;
  champion_sample_size: number;
  champion_avg_probability: number | null;
  champion_actual_rate: number | null;
  champion_calibration_error: number | null;
  challenger_sample_size: number;
  challenger_avg_probability: number | null;
  challenger_actual_rate: number | null;
  challenger_calibration_error: number | null;
}

export interface DeploymentCalibrationReport {
  champion_ece: number;
  challenger_ece: number;
  ece_delta: number;
  buckets: CalibrationBucketComparison[];
}

export interface StatisticalSignificanceReport {
  test_name: string;
  test_statistic: number | null;
  p_value: number | null;
  is_significant: boolean;
  significance_level: number;
  wilson_champion_ci: [number, number] | null;
  wilson_challenger_ci: [number, number] | null;
  newcombe_difference_ci: [number, number] | null;
  significance_classification: string;
}

export interface ReadinessGateResult {
  gate_code: string;
  passed: boolean;
  observed_value: any;
  threshold: any;
  explanation: string;
}

export interface RollbackGuardrailDiagnostics {
  rollback_recommended: boolean;
  reasons: string[];
  observed_recovery_rate_drop: number | null;
  is_governance_degraded: boolean;
  is_data_quality_invalid: boolean;
  is_calibration_failed: boolean;
  is_artifact_invalid: boolean;
  is_drift_critical: boolean;
}

export interface DeploymentReadinessReport {
  decision: string;
  can_promote_to_canary: boolean;
  can_activate_production: boolean;
  gates: ReadinessGateResult[];
  blocking_reasons: string[];
  recommendations: string[];
}

export interface ModelDeploymentResponse {
  deployment_id: string;
  champion_version: string;
  challenger_version: string;
  status: string;
  traffic_allocation_percentage: number;
  assignment_method: string;
  total_cases_evaluated: number;
  created_at: string;
  started_at: string | null;
  paused_at: string | null;
  activated_at: string | null;
  retired_at: string | null;
  created_by: string;
  champion_artifact_hash: string;
  challenger_artifact_hash: string;
  feature_schema_version: string;
  notes: string | null;
}

export interface ShadowAnalysisResponse {
  deployment_id: string;
  champion_version: string;
  challenger_version: string;
  status: string;
  traffic_allocation_percentage: number;
  assignment_method: string;
  sample_size: number;
  champion_metrics: DeploymentMetricsSnapshot;
  challenger_metrics: DeploymentMetricsSnapshot;
  metric_deltas: ShadowComparisonMetric[];
  mean_probability_delta: number;
  mean_absolute_probability_delta: number;
  channel_agreement_rate: number | null;
  delay_agreement_rate: number | null;
  calibration: DeploymentCalibrationReport;
  statistical_test: StatisticalSignificanceReport;
  readiness: DeploymentReadinessReport;
  rollback_diagnostics: RollbackGuardrailDiagnostics;
  evaluated_at: string;
  disclaimer: string;
}

export interface PaginatedDeploymentsResponse {
  items: ModelDeploymentResponse[];
  total: number;
  active_champion_version: string;
}

export async function fetchModelDeployments(
  statusFilter?: string,
  page: number = 1,
  pageSize: number = 20
): Promise<PaginatedDeploymentsResponse> {
  const headers = await getAuthHeaders();
  const url = new URL(`${API_BASE_URL}/api/recovery/intelligence/models/deployments`);
  if (statusFilter && statusFilter !== "ALL") {
    url.searchParams.set("status", statusFilter);
  }
  url.searchParams.set("page", String(page));
  url.searchParams.set("page_size", String(pageSize));

  const res = await fetch(url.toString(), {
    headers,
    cache: "no-store",
  });
  if (!res.ok) {
    const errorBody = await res.json().catch(() => ({}));
    throw new Error(errorBody.detail || `Failed to fetch deployments: ${res.statusText}`);
  }
  return res.json();
}

export async function fetchModelDeployment(
  deploymentId: string
): Promise<ModelDeploymentResponse> {
  const headers = await getAuthHeaders();
  const res = await fetch(
    `${API_BASE_URL}/api/recovery/intelligence/models/deployments/${deploymentId}`,
    {
      headers,
      cache: "no-store",
    }
  );
  if (!res.ok) {
    const errorBody = await res.json().catch(() => ({}));
    throw new Error(errorBody.detail || `Failed to fetch deployment details: ${res.statusText}`);
  }
  return res.json();
}

export async function fetchShadowAnalysis(
  deploymentId: string
): Promise<ShadowAnalysisResponse> {
  const headers = await getAuthHeaders();
  const res = await fetch(
    `${API_BASE_URL}/api/recovery/intelligence/models/deployments/${deploymentId}/shadow-analysis`,
    {
      headers,
      cache: "no-store",
    }
  );
  if (!res.ok) {
    const errorBody = await res.json().catch(() => ({}));
    throw new Error(errorBody.detail || `Failed to fetch shadow analysis: ${res.statusText}`);
  }
  return res.json();
}

export async function fetchDeploymentReadiness(
  deploymentId: string
): Promise<DeploymentReadinessReport> {
  const headers = await getAuthHeaders();
  const res = await fetch(
    `${API_BASE_URL}/api/recovery/intelligence/models/deployments/${deploymentId}/readiness`,
    {
      headers,
      cache: "no-store",
    }
  );
  if (!res.ok) {
    const errorBody = await res.json().catch(() => ({}));
    throw new Error(errorBody.detail || `Failed to fetch deployment readiness: ${res.statusText}`);
  }
  return res.json();
}

export async function createModelDeployment(payload: {
  challenger_version: string;
  champion_version?: string;
  notes?: string;
}): Promise<ModelDeploymentResponse> {
  const headers = await getAuthHeaders();
  const res = await fetch(
    `${API_BASE_URL}/api/recovery/intelligence/models/deployments`,
    {
      method: "POST",
      headers: {
        ...headers,
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        challenger_version: payload.challenger_version,
        champion_version: payload.champion_version || "v1.0",
        notes: payload.notes || null,
      }),
      cache: "no-store",
    }
  );
  if (!res.ok) {
    const errorBody = await res.json().catch(() => ({}));
    throw new Error(errorBody.detail || `Failed to create deployment: ${res.statusText}`);
  }
  return res.json();
}

export async function startShadowMode(
  deploymentId: string,
  percentage: number,
  notes?: string
): Promise<ModelDeploymentResponse> {
  const headers = await getAuthHeaders();
  const res = await fetch(
    `${API_BASE_URL}/api/recovery/intelligence/models/deployments/${deploymentId}/start-shadow`,
    {
      method: "POST",
      headers: {
        ...headers,
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        shadow_percentage: percentage,
        notes: notes || null,
      }),
      cache: "no-store",
    }
  );
  if (!res.ok) {
    const errorBody = await res.json().catch(() => ({}));
    throw new Error(errorBody.detail || `Failed to start shadow mode: ${res.statusText}`);
  }
  return res.json();
}

export async function pauseModelDeployment(
  deploymentId: string
): Promise<ModelDeploymentResponse> {
  const headers = await getAuthHeaders();
  const res = await fetch(
    `${API_BASE_URL}/api/recovery/intelligence/models/deployments/${deploymentId}/pause`,
    {
      method: "POST",
      headers: {
        ...headers,
        "Content-Type": "application/json",
      },
      cache: "no-store",
    }
  );
  if (!res.ok) {
    const errorBody = await res.json().catch(() => ({}));
    throw new Error(errorBody.detail || `Failed to pause deployment: ${res.statusText}`);
  }
  return res.json();
}

export async function setCanaryRollout(
  deploymentId: string,
  percentage: number,
  notes?: string
): Promise<ModelDeploymentResponse> {
  const headers = await getAuthHeaders();
  const res = await fetch(
    `${API_BASE_URL}/api/recovery/intelligence/models/deployments/${deploymentId}/canary`,
    {
      method: "POST",
      headers: {
        ...headers,
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        canary_percentage: percentage,
        notes: notes || null,
      }),
      cache: "no-store",
    }
  );
  if (!res.ok) {
    const errorBody = await res.json().catch(() => ({}));
    throw new Error(errorBody.detail || `Failed to set canary rollout: ${res.statusText}`);
  }
  return res.json();
}

export async function activateModelDeployment(
  deploymentId: string,
  notes?: string
): Promise<ModelDeploymentResponse> {
  const headers = await getAuthHeaders();
  const res = await fetch(
    `${API_BASE_URL}/api/recovery/intelligence/models/deployments/${deploymentId}/activate`,
    {
      method: "POST",
      headers: {
        ...headers,
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ notes: notes || null }),
      cache: "no-store",
    }
  );
  if (!res.ok) {
    const errorBody = await res.json().catch(() => ({}));
    throw new Error(errorBody.detail || `Failed to activate deployment: ${res.statusText}`);
  }
  return res.json();
}

export async function rollbackModelDeployment(
  deploymentId: string,
  reason: string,
  notes?: string
): Promise<ModelDeploymentResponse> {
  const headers = await getAuthHeaders();
  const res = await fetch(
    `${API_BASE_URL}/api/recovery/intelligence/models/deployments/${deploymentId}/rollback`,
    {
      method: "POST",
      headers: {
        ...headers,
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        reason,
        notes: notes || null,
      }),
      cache: "no-store",
    }
  );
  if (!res.ok) {
    const errorBody = await res.json().catch(() => ({}));
    throw new Error(errorBody.detail || `Failed to rollback deployment: ${res.statusText}`);
  }
  return res.json();
}


// =============================================================================
// Phase 9K: Continuous Learning, Automated Monitoring & Safe Model Evolution
// =============================================================================

export interface DatasetVersion {
  dataset_id: string;
  dataset_version: string;
  sample_count: number;
  feature_schema_version: string;
  label_definition: string;
  first_case_timestamp: string | null;
  last_case_timestamp: string | null;
  source_case_count: number;
  sha256_checksum: string;
  positive_count: number;
  negative_count: number;
  class_balance: number;
  created_at: string;
}

export interface LearningTrigger {
  trigger_type: string;
  triggered: boolean;
  severity: string;
  threshold?: any;
  observed_value?: any;
  evidence: Record<string, any>;
}

export interface LearningDiagnostic {
  category: string;
  code: string;
  message: string;
  severity: string;
  timestamp: string;
}

export interface RetrainingEligibility {
  decision: string;
  is_eligible: boolean;
  primary_trigger: string | null;
  primary_reason: string;
  triggers: LearningTrigger[];
  diagnostics: LearningDiagnostic[];
  evaluated_at: string;
}

export interface TrainingRun {
  training_run_id: string;
  dataset_id: string;
  dataset_version: string;
  model_version: string;
  algorithm: string;
  feature_schema: string;
  training_sample_size: number;
  validation_sample_size: number;
  dataset_checksum: string;
  artifact_checksum: string;
  started_at: string;
  completed_at: string | null;
  status: string;
  validation_result: Record<string, any> | null;
  governance_result: Record<string, any> | null;
  notes: string | null;
}

export interface ModelLineageNode {
  model_version: string;
  parent_model_version: string | null;
  dataset_version: string;
  dataset_checksum: string;
  artifact_checksum: string;
  training_run_id: string;
  validation_status: string;
  governance_status: string;
  deployment_status: string;
  created_at: string;
}

export interface ContinuousLearningSafetyGateResult {
  gate_code: string;
  passed: boolean;
  observed_value: any;
  threshold: any;
  explanation: string;
}

export interface ContinuousLearningReadiness {
  decision: string;
  can_retrain: boolean;
  gates: ContinuousLearningSafetyGateResult[];
  blocking_reasons: string[];
  recommendations: string[];
  evaluated_at: string;
}

export interface ContinuousLearningSummary {
  active_champion_version: string;
  latest_dataset_version: string;
  total_dataset_samples: number;
  new_resolved_cases_since_last_training: number;
  last_training_run_at: string | null;
  retraining_eligibility: RetrainingEligibility;
  evolution_decision: string;
  recent_training_runs_count: number;
  registered_datasets_count: number;
  governance_disclaimer: string;
}

export interface PaginatedDatasetsResponse {
  items: DatasetVersion[];
  total: number;
}

export interface PaginatedTrainingRunsResponse {
  items: TrainingRun[];
  total: number;
}

export interface ModelLineageResponse {
  lineage: ModelLineageNode[];
  active_champion_version: string;
}

export async function fetchContinuousLearningSummary(): Promise<ContinuousLearningSummary> {
  const headers = await getAuthHeaders();
  const res = await fetch(`${API_BASE_URL}/api/recovery/intelligence/continuous-learning`, {
    headers,
    cache: "no-store",
  });
  if (!res.ok) {
    throw new Error(`Failed to fetch continuous learning summary: ${res.statusText}`);
  }
  return res.json();
}

export async function fetchContinuousLearningDatasets(): Promise<PaginatedDatasetsResponse> {
  const headers = await getAuthHeaders();
  const res = await fetch(`${API_BASE_URL}/api/recovery/intelligence/continuous-learning/datasets`, {
    headers,
    cache: "no-store",
  });
  if (!res.ok) {
    throw new Error(`Failed to fetch continuous learning datasets: ${res.statusText}`);
  }
  return res.json();
}

export async function fetchContinuousLearningTrainingRuns(): Promise<PaginatedTrainingRunsResponse> {
  const headers = await getAuthHeaders();
  const res = await fetch(`${API_BASE_URL}/api/recovery/intelligence/continuous-learning/training-runs`, {
    headers,
    cache: "no-store",
  });
  if (!res.ok) {
    throw new Error(`Failed to fetch continuous learning training runs: ${res.statusText}`);
  }
  return res.json();
}

export async function fetchModelLineage(): Promise<ModelLineageResponse> {
  const headers = await getAuthHeaders();
  const res = await fetch(`${API_BASE_URL}/api/recovery/intelligence/continuous-learning/lineage`, {
    headers,
    cache: "no-store",
  });
  if (!res.ok) {
    throw new Error(`Failed to fetch model lineage: ${res.statusText}`);
  }
  return res.json();
}

export async function fetchContinuousLearningReadiness(): Promise<ContinuousLearningReadiness> {
  const headers = await getAuthHeaders();
  const res = await fetch(`${API_BASE_URL}/api/recovery/intelligence/continuous-learning/readiness`, {
    headers,
    cache: "no-store",
  });
  if (!res.ok) {
    throw new Error(`Failed to fetch continuous learning readiness: ${res.statusText}`);
  }
  return res.json();
}

export async function triggerManualTraining(payload?: {
  dataset_version?: string;
  learning_rate?: number;
  epochs?: number;
  notes?: string;
}): Promise<TrainingRun> {
  const headers = await getAuthHeaders();
  const res = await fetch(`${API_BASE_URL}/api/recovery/intelligence/continuous-learning/trigger-training`, {
    method: "POST",
    headers: {
      ...headers,
      "Content-Type": "application/json",
    },
    body: JSON.stringify(payload || {}),
    cache: "no-store",
  });
  if (!res.ok) {
    const errorBody = await res.json().catch(() => ({}));
    throw new Error(errorBody.detail || `Failed to trigger offline training: ${res.statusText}`);
  }
  return res.json();
}

// =============================================================================
// Phase 9L: Intelligence Control Plane & Unified Autonomous Governance
// =============================================================================

export type GlobalSystemState =
  | "EMERGENCY_LOCKDOWN"
  | "ROLLBACK_REQUIRED"
  | "DEGRADED"
  | "HUMAN_REVIEW_REQUIRED"
  | "LEARNING_REQUIRED"
  | "WARNING"
  | "MONITORING"
  | "HEALTHY";

export type SubsystemHealthStatus = "HEALTHY" | "WARNING" | "DEGRADED" | "CRITICAL";

export type ControlPlaneDiagnosticSeverity = "INFO" | "LOW" | "MEDIUM" | "HIGH" | "CRITICAL";

export type IncidentSeverity = "LOW" | "MEDIUM" | "HIGH" | "CRITICAL";

export type IncidentState = "ACTIVE" | "INVESTIGATING" | "MITIGATED" | "RESOLVED";

export type LineageStageType =
  | "DATASET"
  | "TRAINING_RUN"
  | "MODEL_ARTIFACT"
  | "VALIDATION"
  | "GOVERNANCE"
  | "EXPERIMENT"
  | "STRATEGY_RECOMMENDATION"
  | "CONTROLLED_ROLLOUT"
  | "PRODUCTION_DEPLOYMENT"
  | "PRODUCTION_OUTCOME";

export interface SubsystemHealth {
  subsystem: string;
  status: SubsystemHealthStatus;
  score: number;
  summary: string;
  metrics: Record<string, any>;
}

export interface IntelligenceHealthScoreBreakdown {
  overall_score: number;
  model_score: number;
  calibration_score: number;
  drift_score: number;
  data_quality_score: number;
  strategy_score: number;
  experiment_score: number;
  deployment_score: number;
  continuous_learning_score: number;
  weights: Record<string, number>;
  formula_explanation: string;
}

export interface ControlPlaneDiagnostic {
  code: string;
  severity: ControlPlaneDiagnosticSeverity;
  source_phase: string;
  observed_value?: any;
  threshold?: any;
  explanation: string;
  recommended_operator_action: string;
}

export interface IntelligenceIncident {
  incident_id: string;
  severity: IncidentSeverity;
  state: IncidentState;
  source_phases: string[];
  diagnostic_codes: string[];
  title: string;
  first_detected: string;
  last_detected: string;
  evidence: Record<string, any>;
  recommended_action: string;
  requires_human_review: boolean;
}

export interface UnifiedIntelligenceHealth {
  model_health: SubsystemHealth;
  model_version: string;
  calibration_health: SubsystemHealth;
  strategy_health: SubsystemHealth;
  experiment_health: SubsystemHealth;
  deployment_health: SubsystemHealth;
  continuous_learning_health: SubsystemHealth;
  data_quality_health: SubsystemHealth;
  drift_health: SubsystemHealth;
  rollback_health: SubsystemHealth;
  pending_human_reviews: number;
  global_system_state: GlobalSystemState;
  intelligence_health_score: IntelligenceHealthScoreBreakdown;
  diagnostics: ControlPlaneDiagnostic[];
  generated_at: string;
}

export interface UnifiedLineageNode {
  stage: LineageStageType;
  identifier: string;
  status: string;
  metadata: Record<string, any>;
  parent_stage?: string | null;
  parent_identifier?: string | null;
  created_at: string;
}

export interface UnifiedLineageResponse {
  nodes: UnifiedLineageNode[];
  active_champion_model: string;
  active_production_strategy: string;
  active_deployment_id?: string | null;
  generated_at: string;
}

export interface DecisionTraceFeatureSnapshot {
  payment_amount_paise: number;
  currency: string;
  attempt_number: number;
  customer_total_payments: number;
  customer_success_rate: number;
  error_code: string;
  error_reason: string;
}

export interface DecisionTraceStage {
  stage_name: string;
  timestamp?: string | null;
  status: string;
  details: Record<string, any>;
}

export interface CaseDecisionTrace {
  case_id: string;
  payment_id: string;
  case_status: string;
  amount_at_risk_paise: number;
  recovered_amount_paise: number;
  opened_at: string;
  resolved_at?: string | null;
  failure_event: Record<string, any>;
  feature_snapshot: DecisionTraceFeatureSnapshot;
  model_version: string;
  prediction_probability: number;
  prediction_timestamp?: string | null;
  agent_decision?: Record<string, any> | null;
  policy_decision?: Record<string, any> | null;
  selected_strategy?: Record<string, any> | null;
  experiment_assignment?: Record<string, any> | null;
  rollout_assignment?: Record<string, any> | null;
  action_metadata?: Record<string, any> | null;
  final_action_result?: Record<string, any> | null;
  final_recovery_outcome: string;
  stages: DecisionTraceStage[];
  traced_at: string;
  disclaimer: string;
}

export interface GovernanceCenterResponse {
  pending_strategy_recommendations_count: number;
  pending_strategy_recommendations: any[];
  pending_model_reviews_count: number;
  pending_model_reviews: any[];
  pending_deployment_reviews_count: number;
  pending_deployment_reviews: any[];
  rollback_alerts: any[];
  learning_alerts: any[];
  critical_diagnostics: ControlPlaneDiagnostic[];
  recent_audit_events: any[];
  required_operator_actions: string[];
  generated_at: string;
}

export interface ControlPlaneSummaryResponse {
  global_state: GlobalSystemState;
  health_score: IntelligenceHealthScoreBreakdown;
  subsystems: SubsystemHealth[];
  active_incidents_count: number;
  pending_reviews_count: number;
  active_champion_version: string;
  active_strategy_action: string;
  deployment_status: string;
  learning_status: string;
  top_diagnostics: ControlPlaneDiagnostic[];
  governance_disclaimer: string;
  generated_at: string;
}

export interface IncidentsResponse {
  incidents: IntelligenceIncident[];
  total: number;
  active_count: number;
  generated_at: string;
}

export async function fetchControlPlaneSummary(): Promise<ControlPlaneSummaryResponse> {
  const headers = await getAuthHeaders();
  const res = await fetch(`${API_BASE_URL}/api/recovery/intelligence/control-plane`, {
    headers,
    cache: "no-store",
  });
  if (!res.ok) {
    throw new Error(`Failed to fetch control plane summary: ${res.statusText}`);
  }
  return res.json();
}

export async function fetchControlPlaneHealth(): Promise<UnifiedIntelligenceHealth> {
  const headers = await getAuthHeaders();
  const res = await fetch(`${API_BASE_URL}/api/recovery/intelligence/control-plane/health`, {
    headers,
    cache: "no-store",
  });
  if (!res.ok) {
    throw new Error(`Failed to fetch unified intelligence health: ${res.statusText}`);
  }
  return res.json();
}

export async function fetchControlPlaneIncidents(): Promise<IncidentsResponse> {
  const headers = await getAuthHeaders();
  const res = await fetch(`${API_BASE_URL}/api/recovery/intelligence/control-plane/incidents`, {
    headers,
    cache: "no-store",
  });
  if (!res.ok) {
    throw new Error(`Failed to fetch control plane incidents: ${res.statusText}`);
  }
  return res.json();
}

export async function fetchControlPlaneLineage(): Promise<UnifiedLineageResponse> {
  const headers = await getAuthHeaders();
  const res = await fetch(`${API_BASE_URL}/api/recovery/intelligence/control-plane/lineage`, {
    headers,
    cache: "no-store",
  });
  if (!res.ok) {
    throw new Error(`Failed to fetch unified control plane lineage: ${res.statusText}`);
  }
  return res.json();
}

export async function fetchGovernanceCenter(): Promise<GovernanceCenterResponse> {
  const headers = await getAuthHeaders();
  const res = await fetch(`${API_BASE_URL}/api/recovery/intelligence/governance-center`, {
    headers,
    cache: "no-store",
  });
  if (!res.ok) {
    throw new Error(`Failed to fetch governance center: ${res.statusText}`);
  }
  return res.json();
}

export async function fetchDecisionTrace(caseId: string): Promise<CaseDecisionTrace> {
  const headers = await getAuthHeaders();
  const res = await fetch(`${API_BASE_URL}/api/recovery/intelligence/decision-trace/${caseId}`, {
    headers,
    cache: "no-store",
  });
  if (!res.ok) {
    const errorBody = await res.json().catch(() => ({}));
    throw new Error(errorBody.detail || `Failed to fetch decision trace: ${res.statusText}`);
  }
  return res.json();
}

// ============================================================================
// Phase 10A — Security Hardening, Threat Detection & Fintech Trust Layer
// ============================================================================

export interface SecurityControlHealth {
  control_name: string;
  status: "ACTIVE" | "DEGRADED" | "DISABLED" | "BYPASS_PREVENTED";
  description: string;
  enforcement_type: string;
  metrics: Record<string, any>;
}

export interface SecurityEventResponse {
  id: number;
  event_type: string;
  severity: "INFO" | "LOW" | "MEDIUM" | "HIGH" | "CRITICAL";
  actor_id: string;
  actor_type: string;
  details: Record<string, any>;
  created_at: string;
}

export interface PaginatedSecurityEventsResponse {
  items: SecurityEventResponse[];
  total: number;
  page: number;
  page_size: number;
}

export interface TrustCenterOverviewResponse {
  trust_score: number;
  threat_level: "NOMINAL" | "ELEVATED" | "CRITICAL";
  active_controls_count: number;
  controls: SecurityControlHealth[];
  total_security_events_24h: number;
  blocked_attacks_count: number;
  pii_leak_count: number;
  financial_isolation_guaranteed: boolean;
  policy_engine_supremacy: boolean;
  disclaimer: string;
  generated_at: string;
}

export interface TokenRevocationResponse {
  jti: string;
  revoked: boolean;
  revoked_at: string;
  revoked_by: string;
  message: string;
}

export interface PIIScanResponse {
  has_pii: boolean;
  has_secrets: boolean;
  findings_count: number;
  findings: Array<{ type: string; path: string; description: string }>;
  sanitized_payload: any;
  scan_timestamp: string;
}

export async function fetchTrustCenterOverview(): Promise<TrustCenterOverviewResponse> {
  const headers = await getAuthHeaders();
  const res = await fetch(`${API_BASE_URL}/api/recovery/security/trust-center`, {
    headers,
    cache: "no-store",
  });
  if (!res.ok) {
    throw new Error(`Failed to fetch Trust Center overview: ${res.statusText}`);
  }
  return res.json();
}

export async function fetchSecurityEvents(
  page: number = 1,
  limit: number = 50,
  severity: string = "ALL",
  eventType: string = "ALL"
): Promise<PaginatedSecurityEventsResponse> {
  const headers = await getAuthHeaders();
  const params = new URLSearchParams({
    page: page.toString(),
    limit: limit.toString(),
    severity,
    event_type: eventType,
  });
  const res = await fetch(`${API_BASE_URL}/api/recovery/security/events?${params.toString()}`, {
    headers,
    cache: "no-store",
  });
  if (!res.ok) {
    throw new Error(`Failed to fetch security events: ${res.statusText}`);
  }
  return res.json();
}

export async function revokeToken(jti: string, reason?: string): Promise<TokenRevocationResponse> {
  const headers = await getAuthHeaders();
  const res = await fetch(`${API_BASE_URL}/api/recovery/security/revoke-token`, {
    method: "POST",
    headers: {
      ...headers,
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ jti, reason: reason || "Operator manual revocation" }),
    cache: "no-store",
  });
  if (!res.ok) {
    const errorBody = await res.json().catch(() => ({}));
    throw new Error(errorBody.detail || `Failed to revoke token: ${res.statusText}`);
  }
  return res.json();
}

export async function scanPayloadPII(payload: any): Promise<PIIScanResponse> {
  const headers = await getAuthHeaders();
  const res = await fetch(`${API_BASE_URL}/api/recovery/security/scan`, {
    method: "POST",
    headers: {
      ...headers,
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ payload }),
    cache: "no-store",
  });
  if (!res.ok) {
    const errorBody = await res.json().catch(() => ({}));
    throw new Error(errorBody.detail || `Failed to scan payload: ${res.statusText}`);
  }
  return res.json();
}

/* =========================================================================
   PHASE 10B: COMPLIANCE, AUDIT INTELLIGENCE & REGULATORY GOVERNANCE
   ========================================================================= */

export type ComplianceControlCategory =
  | "SECURITY"
  | "FINANCIAL_CONTROL"
  | "ML_GOVERNANCE"
  | "DATA_GOVERNANCE"
  | "HUMAN_GOVERNANCE";

export type ComplianceControlStatus = "PASS" | "WARNING" | "FAIL" | "NOT_ASSESSED";

export type ComplianceSeverity = "LOW" | "MEDIUM" | "HIGH" | "CRITICAL";

export type CompliancePosture = "EXCELLENT" | "GOOD" | "WARNING" | "HIGH_RISK" | "CRITICAL";

export interface ComplianceControl {
  control_id: string;
  control_category: ComplianceControlCategory;
  control_name: string;
  description: string;
  status: ComplianceControlStatus;
  severity: ComplianceSeverity;
  evidence_count: number;
  last_verified_at: string;
  first_detected_at: string;
  owner_role: string;
  remediation_required: boolean;
  evidence_summary: string;
}

export interface ComplianceFinding {
  finding_id: string;
  control_id: string;
  severity: ComplianceSeverity;
  category: ComplianceControlCategory;
  entity_reference: string;
  description: string;
  recommended_remediation: string;
  detected_at: string;
}

export interface ComplianceCategoryScore {
  category: ComplianceControlCategory;
  weight_percentage: number;
  score: number;
  controls_count: number;
  passing_controls_count: number;
  warning_controls_count: number;
  failing_controls_count: number;
}

export interface AuditCoverage {
  total_required_event_categories: number;
  observed_event_categories: number;
  missing_categories: string[];
  audit_coverage_percentage: number;
  lifecycle_chains_status: Record<string, string>;
  total_audit_events_count: number;
  orphaned_records_count: number;
}

export interface DecisionTraceCompliance {
  total_resolved_cases_sampled: number;
  trace_completeness_rate: number;
  complete_traces_count: number;
  partial_traces_count: number;
  broken_traces_count: number;
  untraced_cases_count: number;
  pii_exposed_in_traces: boolean;
}

export interface FinancialGovernanceAudit {
  policy_engine_supremacy_verified: boolean;
  unauthorized_financial_mutations_count: number;
  untracked_actions_count: number;
  gateway_calls_from_governance_count: number;
  actions_with_policy_decision_percentage: number;
  status: ComplianceControlStatus;
}

export interface RBACComplianceAudit {
  privilege_escalation_attempts_count: number;
  unauthorized_access_attempts_count: number;
  revoked_token_rejections_count: number;
  authoritative_identity_enforced: boolean;
  findings: ComplianceFinding[];
  status: ComplianceControlStatus;
}

export interface ModelGovernanceCompliance {
  dataset_lineage_coverage_pct: number;
  active_champion_has_approved_gates: boolean;
  unapproved_deployments_count: number;
  active_canary_monitoring_healthy: boolean;
  strategy_recommendations_governed_pct: number;
  status: ComplianceControlStatus;
}

export interface DataProtectionAudit {
  pii_scanner_active: boolean;
  unmasked_cards_detected_count: number;
  unmasked_aadhaar_detected_count: number;
  unmasked_tokens_detected_count: number;
  unmasked_emails_detected_count: number;
  status: ComplianceControlStatus;
}

export interface ComplianceIncident {
  incident_id: string;
  severity: ComplianceSeverity;
  category: ComplianceControlCategory;
  title: string;
  description: string;
  evidence: Record<string, any>;
  affected_entity_type: string;
  affected_entity_id: string | null;
  detected_at: string;
  status: string;
  recommended_action: string;
}

export interface ComplianceSummary {
  compliance_score: number;
  compliance_posture: CompliancePosture;
  audit_coverage_percentage: number;
  category_scores: ComplianceCategoryScore[];
  total_controls_count: number;
  passing_controls_count: number;
  warning_controls_count: number;
  failing_controls_count: number;
  open_incidents_count: number;
  critical_findings_count: number;
  financial_governance: FinancialGovernanceAudit;
  rbac_compliance: RBACComplianceAudit;
  model_governance: ModelGovernanceCompliance;
  data_protection: DataProtectionAudit;
  audit_coverage: AuditCoverage;
  decision_trace_compliance: DecisionTraceCompliance;
  disclaimer: string;
  generated_at: string;
}

export interface ComplianceReport {
  report_id: string;
  generated_at: string;
  compliance_score: number;
  compliance_posture: CompliancePosture;
  executive_summary: string;
  disclaimer: string;
  category_scores: ComplianceCategoryScore[];
  controls: ComplianceControl[];
  findings: ComplianceFinding[];
  incidents: ComplianceIncident[];
  audit_coverage: AuditCoverage;
  decision_trace_compliance: DecisionTraceCompliance;
  financial_governance: FinancialGovernanceAudit;
  rbac_compliance: RBACComplianceAudit;
  model_governance: ModelGovernanceCompliance;
  data_protection: DataProtectionAudit;
  remediation_roadmap: Array<{
    priority: string;
    milestone: string;
    action: string;
    target_date: string;
  }>;
}

export async function fetchComplianceSummary(): Promise<ComplianceSummary> {
  const headers = await getAuthHeaders();
  const res = await fetch(`${API_BASE_URL}/api/recovery/intelligence/compliance`, {
    headers,
    cache: "no-store",
  });
  if (!res.ok) {
    throw new Error(`Failed to fetch compliance summary: ${res.statusText}`);
  }
  return res.json();
}

export async function fetchComplianceControls(
  category?: string,
  status?: string,
  severity?: string
): Promise<ComplianceControl[]> {
  const headers = await getAuthHeaders();
  const params = new URLSearchParams();
  if (category && category !== "ALL") params.append("category", category);
  if (status && status !== "ALL") params.append("status", status);
  if (severity && severity !== "ALL") params.append("severity", severity);

  const url = `${API_BASE_URL}/api/recovery/intelligence/compliance/controls${
    params.toString() ? `?${params.toString()}` : ""
  }`;
  const res = await fetch(url, {
    headers,
    cache: "no-store",
  });
  if (!res.ok) {
    throw new Error(`Failed to fetch compliance controls: ${res.statusText}`);
  }
  return res.json();
}

export async function fetchComplianceIncidents(
  severity?: string,
  category?: string,
  status?: string
): Promise<ComplianceIncident[]> {
  const headers = await getAuthHeaders();
  const params = new URLSearchParams();
  if (severity && severity !== "ALL") params.append("severity", severity);
  if (category && category !== "ALL") params.append("category", category);
  if (status && status !== "ALL") params.append("status", status);

  const url = `${API_BASE_URL}/api/recovery/intelligence/compliance/incidents${
    params.toString() ? `?${params.toString()}` : ""
  }`;
  const res = await fetch(url, {
    headers,
    cache: "no-store",
  });
  if (!res.ok) {
    throw new Error(`Failed to fetch compliance incidents: ${res.statusText}`);
  }
  return res.json();
}

export async function fetchAuditCoverage(): Promise<AuditCoverage> {
  const headers = await getAuthHeaders();
  const res = await fetch(`${API_BASE_URL}/api/recovery/intelligence/compliance/audit-coverage`, {
    headers,
    cache: "no-store",
  });
  if (!res.ok) {
    throw new Error(`Failed to fetch audit coverage: ${res.statusText}`);
  }
  return res.json();
}

export async function fetchComplianceReport(): Promise<ComplianceReport> {
  const headers = await getAuthHeaders();
  const res = await fetch(`${API_BASE_URL}/api/recovery/intelligence/compliance/report`, {
    headers,
    cache: "no-store",
  });
  if (!res.ok) {
    throw new Error(`Failed to generate compliance report: ${res.statusText}`);
  }
  return res.json();
}

// =============================================================================
// Phase 10C: Operational Resilience, Disaster Recovery & Business Continuity
// =============================================================================

export type ResilienceState =
  | "DISASTER_MODE"
  | "CRITICAL"
  | "SERVICE_IMPACTED"
  | "DEGRADED"
  | "WARNING"
  | "RECOVERY_IN_PROGRESS"
  | "RECOVERY_VERIFIED"
  | "OPERATIONAL";

export type ResilienceSeverity = "INFO" | "LOW" | "MEDIUM" | "HIGH" | "CRITICAL";

export type ServiceHealthStatus = "HEALTHY" | "DEGRADED" | "UNAVAILABLE" | "UNKNOWN";

export type DependencyStatus = "HEALTHY" | "WARNING" | "DEGRADED" | "CRITICAL" | "UNAVAILABLE";

export type RTORPOComplianceStatus = "COMPLIANT" | "AT_RISK" | "BREACHED" | "UNKNOWN";

export type ReadinessStatus = "READY" | "CONDITIONAL" | "BLOCKED" | "UNKNOWN";

export type DisasterScenarioType =
  | "DATABASE_OUTAGE"
  | "REDIS_OUTAGE"
  | "WORKER_FAILURE"
  | "QUEUE_BACKLOG"
  | "WEBHOOK_OUTAGE"
  | "ML_SERVICE_DEGRADATION"
  | "POLICYENGINE_DEGRADATION"
  | "AUDITLOG_FAILURE"
  | "PAYMENT_PROVIDER_UNAVAILABLE"
  | "REGIONAL_OUTAGE"
  | "CASCADING_DEPENDENCY_FAILURE";

export type ResilienceIncidentStatus =
  | "DETECTED"
  | "TRIAGED"
  | "HUMAN_REVIEW"
  | "MITIGATION_RECOMMENDED"
  | "RECOVERY_IN_PROGRESS"
  | "RECOVERY_VERIFIED"
  | "CLOSED";

export interface ResilienceServiceHealth {
  service_name: string;
  status: ServiceHealthStatus;
  latency_ms: number;
  last_success_timestamp: string | null;
  last_failure_timestamp: string | null;
  consecutive_failures: number;
  availability_percentage: number;
  severity: ResilienceSeverity;
  diagnostic_code: string;
}

export interface ResilienceIncident {
  incident_id: string;
  incident_type: string;
  severity: ResilienceSeverity;
  state: ResilienceIncidentStatus;
  detected_at: string;
  acknowledged_at: string | null;
  resolved_at: string | null;
  affected_services: string[];
  root_cause_category: string;
  evidence: Record<string, any>;
  operator: string | null;
  rto_impact_seconds: number | null;
  rpo_impact_seconds: number | null;
  escalation_level: string;
  recommended_action: string;
}

export interface ResilienceReadinessGate {
  gate_code: string;
  gate_name: string;
  status: ReadinessStatus;
  observed_value: string;
  threshold: string;
  severity: ResilienceSeverity;
  evidence: string;
  remediation: string;
}

export interface ResilienceReadiness {
  overall_status: ReadinessStatus;
  gates: ResilienceReadinessGate[];
  ready_count: number;
  conditional_count: number;
  blocked_count: number;
  unknown_count: number;
  readiness_percentage: number;
}

export interface BackupVerification {
  backup_id: string;
  backup_timestamp: string;
  backup_age_seconds: number;
  freshness_status: string;
  integrity_status: string;
  checksum_sha256: string;
  restore_test_status: string;
  restore_test_timestamp: string | null;
  restore_duration_seconds: number | null;
  restore_validation_status: string;
  rpo_impact_assessment: string;
}

export interface RTORPOStatus {
  rto_target_seconds: number;
  rto_observed_seconds: number;
  rto_compliance: RTORPOComplianceStatus;
  rpo_target_seconds: number;
  rpo_observed_seconds: number;
  rpo_compliance: RTORPOComplianceStatus;
  historical_rto_breaches: number;
  historical_rpo_breaches: number;
  last_rto_breach_at: string | null;
  last_rpo_breach_at: string | null;
}

export interface DisasterSimulationRequest {
  scenario_type: DisasterScenarioType;
  severity_override?: ResilienceSeverity;
}

export interface BlastRadiusAnalysis {
  directly_affected_services: string[];
  indirectly_affected_services: string[];
  critical_path_dependencies: string[];
  financial_path_dependencies: string[];
  non_financial_dependencies: string[];
  blast_radius_percentage: number;
}

export interface DisasterSimulationResult {
  scenario_id: string;
  scenario_type: DisasterScenarioType;
  severity: ResilienceSeverity;
  affected_services: string[];
  blast_radius: BlastRadiusAnalysis;
  estimated_rto_seconds: number;
  estimated_rpo_seconds: number;
  recovery_steps: string[];
  financial_isolation_status: string;
  readiness_status: ReadinessStatus;
  recommended_human_actions: string[];
  simulation_type: string;
  disclaimer: string;
}

export interface RecoveryRunbook {
  runbook_id: string;
  scenario: string;
  preconditions: string[];
  ordered_steps: string[];
  verification_steps: string[];
  rollback_steps: string[];
  required_role: string;
  estimated_duration_minutes: number;
  rto_target_seconds: number;
  rpo_target_seconds: number;
}

export interface ResilienceScoreBreakdown {
  availability_score: number;
  dependency_health_score: number;
  recovery_readiness_score: number;
  rto_compliance_score: number;
  rpo_compliance_score: number;
  queue_health_score: number;
  audit_continuity_score: number;
  incident_stability_score: number;
}

export interface ResilienceSummary {
  resilience_score: number;
  global_state: ResilienceState;
  score_breakdown: ResilienceScoreBreakdown;
  services: ResilienceServiceHealth[];
  active_incidents_count: number;
  critical_incidents_count: number;
  dr_readiness_percentage: number;
  rto_compliance: RTORPOComplianceStatus;
  rpo_compliance: RTORPOComplianceStatus;
  service_availability_percentage: number;
  dependency_health_status: DependencyStatus;
  backup_freshness: string;
  last_evaluated_at: string;
  disclaimer: string;
}

export async function fetchResilienceSummary(): Promise<ResilienceSummary> {
  const headers = await getAuthHeaders();
  const res = await fetch(`${API_BASE_URL}/api/recovery/intelligence/resilience`, {
    headers,
    cache: "no-store",
  });
  if (!res.ok) {
    throw new Error(`Failed to fetch resilience summary: ${res.statusText}`);
  }
  return res.json();
}

export async function fetchResilienceServices(): Promise<ResilienceServiceHealth[]> {
  const headers = await getAuthHeaders();
  const res = await fetch(`${API_BASE_URL}/api/recovery/intelligence/resilience/services`, {
    headers,
    cache: "no-store",
  });
  if (!res.ok) {
    throw new Error(`Failed to fetch resilience service health: ${res.statusText}`);
  }
  return res.json();
}

export async function fetchResilienceIncidents(severity?: string): Promise<ResilienceIncident[]> {
  const headers = await getAuthHeaders();
  const params = new URLSearchParams();
  if (severity && severity !== "ALL") params.append("severity", severity);
  const url = `${API_BASE_URL}/api/recovery/intelligence/resilience/incidents${
    params.toString() ? `?${params.toString()}` : ""
  }`;
  const res = await fetch(url, {
    headers,
    cache: "no-store",
  });
  if (!res.ok) {
    throw new Error(`Failed to fetch resilience incidents: ${res.statusText}`);
  }
  return res.json();
}

export async function fetchResilienceReadiness(): Promise<ResilienceReadiness> {
  const headers = await getAuthHeaders();
  const res = await fetch(`${API_BASE_URL}/api/recovery/intelligence/resilience/readiness`, {
    headers,
    cache: "no-store",
  });
  if (!res.ok) {
    throw new Error(`Failed to fetch DR readiness: ${res.statusText}`);
  }
  return res.json();
}

export async function fetchResilienceBackups(): Promise<BackupVerification> {
  const headers = await getAuthHeaders();
  const res = await fetch(`${API_BASE_URL}/api/recovery/intelligence/resilience/backups`, {
    headers,
    cache: "no-store",
  });
  if (!res.ok) {
    throw new Error(`Failed to fetch backup verification: ${res.statusText}`);
  }
  return res.json();
}

export async function fetchResilienceRtoRpo(): Promise<RTORPOStatus> {
  const headers = await getAuthHeaders();
  const res = await fetch(`${API_BASE_URL}/api/recovery/intelligence/resilience/rto-rpo`, {
    headers,
    cache: "no-store",
  });
  if (!res.ok) {
    throw new Error(`Failed to fetch RTO/RPO status: ${res.statusText}`);
  }
  return res.json();
}

export async function fetchResilienceRunbooks(): Promise<RecoveryRunbook[]> {
  const headers = await getAuthHeaders();
  const res = await fetch(`${API_BASE_URL}/api/recovery/intelligence/resilience/runbooks`, {
    headers,
    cache: "no-store",
  });
  if (!res.ok) {
    throw new Error(`Failed to fetch recovery runbooks: ${res.statusText}`);
  }
  return res.json();
}

export async function fetchResilienceSimulations(): Promise<Record<string, any>[]> {
  const headers = await getAuthHeaders();
  const res = await fetch(`${API_BASE_URL}/api/recovery/intelligence/resilience/simulations`, {
    headers,
    cache: "no-store",
  });
  if (!res.ok) {
    throw new Error(`Failed to fetch disaster simulations: ${res.statusText}`);
  }
  return res.json();
}

export async function runResilienceSimulation(
  scenarioType: string,
  severityOverride?: string
): Promise<DisasterSimulationResult> {
  const headers = await getAuthHeaders();
  const body: Record<string, any> = { scenario_type: scenarioType };
  if (severityOverride && severityOverride !== "DEFAULT") {
    body.severity_override = severityOverride;
  }
  const res = await fetch(`${API_BASE_URL}/api/recovery/intelligence/resilience/simulate`, {
    method: "POST",
    headers: { ...headers, "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) {
    throw new Error(`Failed to run disaster simulation: ${res.statusText}`);
  }
  return res.json();
}

export async function acknowledgeResilienceIncident(incidentId: string): Promise<ResilienceIncident> {
  const headers = await getAuthHeaders();
  const res = await fetch(
    `${API_BASE_URL}/api/recovery/intelligence/resilience/incidents/${encodeURIComponent(incidentId)}/acknowledge`,
    {
      method: "POST",
      headers,
    }
  );
  if (!res.ok) {
    throw new Error(`Failed to acknowledge incident: ${res.statusText}`);
  }
  return res.json();
}

export async function escalateResilienceIncident(incidentId: string): Promise<ResilienceIncident> {
  const headers = await getAuthHeaders();
  const res = await fetch(
    `${API_BASE_URL}/api/recovery/intelligence/resilience/incidents/${encodeURIComponent(incidentId)}/escalate`,
    {
      method: "POST",
      headers,
    }
  );
  if (!res.ok) {
    throw new Error(`Failed to escalate incident: ${res.statusText}`);
  }
  return res.json();
}

export async function verifyResilienceRecovery(): Promise<Record<string, any>> {
  const headers = await getAuthHeaders();
  const res = await fetch(`${API_BASE_URL}/api/recovery/intelligence/resilience/recovery/verify`, {
    method: "POST",
    headers,
  });
  if (!res.ok) {
    throw new Error(`Failed to verify recovery: ${res.statusText}`);
  }
  return res.json();
}

// =============================================================================
// Phase 10D: Fintech Observability, SRE, Incident Response & Production Operations
// =============================================================================

export interface SLIMetric {
  sli_code: string;
  service: string;
  window: string;
  observed_value: number;
  unit: string;
  threshold: number;
  status: string;
  sample_size: number;
  timestamp: string;
}

export interface SLODefinition {
  slo_code: string;
  name: string;
  service: string;
  target_percentage: number;
  window: string;
  metric_type: string;
  is_engineering_default: boolean;
}

export interface SLOEvaluation {
  slo_code: string;
  name: string;
  service: string;
  target_percentage: number;
  observed_percentage: number;
  status: string;
  error_budget_remaining_pct: number;
  burn_rate: number;
  compliance_delta: number;
}

export interface ErrorBudget {
  slo_code: string;
  name: string;
  allowed_budget: number;
  consumed_budget: number;
  remaining_budget: number;
  consumption_percentage: number;
  burn_rate_1h: number;
  burn_rate_6h: number;
  burn_rate_24h: number;
  status: string;
}

export interface ServiceTelemetry {
  service_name: string;
  availability: number;
  p50_latency_ms: number;
  p95_latency_ms: number;
  p99_latency_ms: number;
  error_rate_pct: number;
  throughput_rpm: number;
  slo_compliance: string;
  error_budget_remaining_pct: number;
  status: string;
}

export interface ObservabilityAlert {
  alert_id: string;
  fingerprint: string;
  rule_code: string;
  severity: string;
  service: string;
  observed_value: number;
  threshold: number;
  first_detected: string;
  last_detected: string;
  occurrence_count: number;
  status: string;
  evidence: Record<string, any>;
}

export interface IncidentTimelineEvent {
  event_id: string;
  timestamp: string;
  previous_state: string;
  new_state: string;
  actor_role: string;
  actor_id: string;
  note: string;
}

export interface ObservabilityIncident {
  incident_id: string;
  severity: string;
  incident_type: string;
  title: string;
  affected_services: string[];
  state: string;
  detected_at: string;
  acknowledged_at: string | null;
  resolved_at: string | null;
  mtta_seconds: number | null;
  mttr_seconds: number | null;
  slo_impact: string;
  error_budget_impact: number;
  root_cause_category: string;
  root_cause_confidence: string;
  timeline: IncidentTimelineEvent[];
  evidence: Record<string, any>;
}

export interface TraceSpan {
  span_id: string;
  trace_id: string;
  parent_span_id: string | null;
  service: string;
  operation: string;
  start_time: string;
  duration_ms: number;
  status: string;
  error_details: string | null;
}

export interface TraceSummary {
  trace_id: string;
  root_service: string;
  total_duration_ms: number;
  span_count: number;
  status: string;
  start_time: string;
  spans: TraceSpan[];
}

export interface DeploymentImpact {
  deployment_id: string;
  service: string;
  version: string;
  impact_status: string;
  latency_delta_pct: number;
  error_rate_delta_pct: number;
  slo_delta_pct: number;
  rollback_recommended: boolean;
  evidence: Record<string, any>;
}

export interface OperationalReadinessGate {
  gate_code: string;
  gate_name: string;
  status: string;
  observed_value: string;
  threshold: string;
  severity: string;
  evidence: string;
  remediation: string;
}

export interface OperationalReadiness {
  overall_status: string;
  gates: OperationalReadinessGate[];
  ready_count: number;
  conditional_count: number;
  blocked_count: number;
  readiness_percentage: number;
}

export interface PostIncidentReport {
  postmortem_id: string;
  incident_id: string;
  title: string;
  timeline: IncidentTimelineEvent[];
  impact_summary: string;
  affected_services: string[];
  root_cause_category: string;
  root_cause_confidence: string;
  contributing_factors: string[];
  detection_gap: string;
  response_gap: string;
  resolution_summary: string;
  slo_impact: string;
  error_budget_impact: number;
  corrective_actions: string[];
  preventive_actions: string[];
  author_id: string;
  approved_by: string | null;
  status: string;
  created_at: string;
}

export interface FinancialPathTelemetry {
  stage_name: string;
  latency_ms: number;
  success_rate_pct: number;
  error_rate_pct: number;
  throughput_rpm: number;
  health_status: string;
}

export interface QueueTelemetry {
  queue_depth: number;
  oldest_job_age_seconds: number;
  jobs_processed_last_hour: number;
  jobs_failed_last_hour: number;
  processing_latency_ms: number;
  health_status: string;
}

export interface WorkerTelemetry {
  active_workers: number;
  utilization_pct: number;
  success_rate_pct: number;
  processing_latency_ms: number;
  last_heartbeat: string;
  health_status: string;
}

export interface WebhookTelemetry {
  webhooks_received: number;
  webhooks_verified: number;
  webhooks_rejected: number;
  webhooks_failed: number;
  processing_latency_ms: number;
  duplicate_rate_pct: number;
  replay_rejection_rate_pct: number;
  health_status: string;
}

export interface MLTelemetry {
  prediction_count: number;
  p95_latency_ms: number;
  error_rate_pct: number;
  drift_status: string;
  calibration_status: string;
  active_model_version: string;
  health_status: string;
}

export interface PolicyEngineTelemetry {
  evaluation_count: number;
  allow_rate_pct: number;
  deny_rate_pct: number;
  error_rate_pct: number;
  p95_latency_ms: number;
  timeout_rate_pct: number;
  health_status: string;
}

export interface DatabaseTelemetry {
  connection_health: string;
  query_p95_latency_ms: number;
  transaction_failure_rate_pct: number;
  slow_query_count: number;
  pool_utilization_pct: number;
  health_status: string;
}

export interface ObservabilityScoreBreakdown {
  availability_score: number;
  latency_score: number;
  error_rate_score: number;
  throughput_score: number;
  slo_compliance_score: number;
  error_budget_score: number;
  dependency_score: number;
  queue_health_score: number;
  worker_health_score: number;
  incident_stability_score: number;
}

export interface ObservabilitySummary {
  observability_score: number;
  global_state: string;
  score_breakdown: ObservabilityScoreBreakdown;
  services: ServiceTelemetry[];
  active_incidents_count: number;
  critical_incidents_count: number;
  slo_compliance_pct: number;
  remaining_error_budget_pct: number;
  p95_latency_ms: number;
  aggregate_error_rate_pct: number;
  operational_readiness_pct: number;
  last_evaluated_at: string;
  disclaimer: string;
}

// ─── Phase 10D Fetcher Functions ─────────────────────────────────────────────

export async function fetchObservabilitySummary(): Promise<ObservabilitySummary> {
  const headers = await getAuthHeaders();
  const res = await fetch(`${API_BASE_URL}/api/recovery/intelligence/observability`, {
    headers,
    cache: "no-store",
  });
  if (!res.ok) {
    throw new Error(`Failed to fetch observability summary: ${res.statusText}`);
  }
  return res.json();
}

export async function fetchObservabilityServices(): Promise<ServiceTelemetry[]> {
  const headers = await getAuthHeaders();
  const res = await fetch(`${API_BASE_URL}/api/recovery/intelligence/observability/services`, {
    headers,
    cache: "no-store",
  });
  if (!res.ok) {
    throw new Error(`Failed to fetch service telemetry: ${res.statusText}`);
  }
  return res.json();
}

export async function fetchObservabilitySLIs(): Promise<SLIMetric[]> {
  const headers = await getAuthHeaders();
  const res = await fetch(`${API_BASE_URL}/api/recovery/intelligence/observability/slis`, {
    headers,
    cache: "no-store",
  });
  if (!res.ok) {
    throw new Error(`Failed to fetch SLIs: ${res.statusText}`);
  }
  return res.json();
}

export async function fetchObservabilitySLOs(): Promise<SLOEvaluation[]> {
  const headers = await getAuthHeaders();
  const res = await fetch(`${API_BASE_URL}/api/recovery/intelligence/observability/slos`, {
    headers,
    cache: "no-store",
  });
  if (!res.ok) {
    throw new Error(`Failed to fetch SLOs: ${res.statusText}`);
  }
  return res.json();
}

export async function fetchObservabilityErrorBudget(): Promise<ErrorBudget[]> {
  const headers = await getAuthHeaders();
  const res = await fetch(`${API_BASE_URL}/api/recovery/intelligence/observability/error-budget`, {
    headers,
    cache: "no-store",
  });
  if (!res.ok) {
    throw new Error(`Failed to fetch error budgets: ${res.statusText}`);
  }
  return res.json();
}

export async function fetchObservabilityAlerts(): Promise<ObservabilityAlert[]> {
  const headers = await getAuthHeaders();
  const res = await fetch(`${API_BASE_URL}/api/recovery/intelligence/observability/alerts`, {
    headers,
    cache: "no-store",
  });
  if (!res.ok) {
    throw new Error(`Failed to fetch alerts: ${res.statusText}`);
  }
  return res.json();
}

export async function fetchObservabilityIncidents(): Promise<ObservabilityIncident[]> {
  const headers = await getAuthHeaders();
  const res = await fetch(`${API_BASE_URL}/api/recovery/intelligence/observability/incidents`, {
    headers,
    cache: "no-store",
  });
  if (!res.ok) {
    throw new Error(`Failed to fetch incidents: ${res.statusText}`);
  }
  return res.json();
}

export async function fetchObservabilityIncidentDetail(incidentId: string): Promise<ObservabilityIncident> {
  const headers = await getAuthHeaders();
  const res = await fetch(
    `${API_BASE_URL}/api/recovery/intelligence/observability/incidents/${encodeURIComponent(incidentId)}`,
    {
      headers,
      cache: "no-store",
    }
  );
  if (!res.ok) {
    throw new Error(`Failed to fetch incident detail: ${res.statusText}`);
  }
  return res.json();
}

export async function fetchObservabilityTraces(): Promise<TraceSummary[]> {
  const headers = await getAuthHeaders();
  const res = await fetch(`${API_BASE_URL}/api/recovery/intelligence/observability/traces`, {
    headers,
    cache: "no-store",
  });
  if (!res.ok) {
    throw new Error(`Failed to fetch traces: ${res.statusText}`);
  }
  return res.json();
}

export async function fetchObservabilityDeployments(): Promise<DeploymentImpact[]> {
  const headers = await getAuthHeaders();
  const res = await fetch(`${API_BASE_URL}/api/recovery/intelligence/observability/deployments`, {
    headers,
    cache: "no-store",
  });
  if (!res.ok) {
    throw new Error(`Failed to fetch deployments: ${res.statusText}`);
  }
  return res.json();
}

export async function fetchObservabilityReadiness(): Promise<OperationalReadiness> {
  const headers = await getAuthHeaders();
  const res = await fetch(`${API_BASE_URL}/api/recovery/intelligence/observability/readiness`, {
    headers,
    cache: "no-store",
  });
  if (!res.ok) {
    throw new Error(`Failed to fetch operational readiness: ${res.statusText}`);
  }
  return res.json();
}

export async function fetchObservabilityPostmortems(): Promise<PostIncidentReport[]> {
  const headers = await getAuthHeaders();
  const res = await fetch(`${API_BASE_URL}/api/recovery/intelligence/observability/postmortems`, {
    headers,
    cache: "no-store",
  });
  if (!res.ok) {
    throw new Error(`Failed to fetch postmortems: ${res.statusText}`);
  }
  return res.json();
}

export async function fetchObservabilityFinancialPath(): Promise<FinancialPathTelemetry[]> {
  const headers = await getAuthHeaders();
  const res = await fetch(`${API_BASE_URL}/api/recovery/intelligence/observability/financial-path`, {
    headers,
    cache: "no-store",
  });
  if (!res.ok) {
    throw new Error(`Failed to fetch financial path telemetry: ${res.statusText}`);
  }
  return res.json();
}

export async function fetchObservabilityQueues(): Promise<QueueTelemetry> {
  const headers = await getAuthHeaders();
  const res = await fetch(`${API_BASE_URL}/api/recovery/intelligence/observability/queues`, {
    headers,
    cache: "no-store",
  });
  if (!res.ok) {
    throw new Error(`Failed to fetch queue telemetry: ${res.statusText}`);
  }
  return res.json();
}

export async function fetchObservabilityWorkers(): Promise<WorkerTelemetry> {
  const headers = await getAuthHeaders();
  const res = await fetch(`${API_BASE_URL}/api/recovery/intelligence/observability/workers`, {
    headers,
    cache: "no-store",
  });
  if (!res.ok) {
    throw new Error(`Failed to fetch worker telemetry: ${res.statusText}`);
  }
  return res.json();
}

export async function fetchObservabilityWebhooks(): Promise<WebhookTelemetry> {
  const headers = await getAuthHeaders();
  const res = await fetch(`${API_BASE_URL}/api/recovery/intelligence/observability/webhooks`, {
    headers,
    cache: "no-store",
  });
  if (!res.ok) {
    throw new Error(`Failed to fetch webhook telemetry: ${res.statusText}`);
  }
  return res.json();
}

export async function fetchObservabilityML(): Promise<MLTelemetry> {
  const headers = await getAuthHeaders();
  const res = await fetch(`${API_BASE_URL}/api/recovery/intelligence/observability/ml`, {
    headers,
    cache: "no-store",
  });
  if (!res.ok) {
    throw new Error(`Failed to fetch ML telemetry: ${res.statusText}`);
  }
  return res.json();
}

export async function fetchObservabilityPolicy(): Promise<PolicyEngineTelemetry> {
  const headers = await getAuthHeaders();
  const res = await fetch(`${API_BASE_URL}/api/recovery/intelligence/observability/policy`, {
    headers,
    cache: "no-store",
  });
  if (!res.ok) {
    throw new Error(`Failed to fetch PolicyEngine telemetry: ${res.statusText}`);
  }
  return res.json();
}

export async function fetchObservabilityDatabase(): Promise<DatabaseTelemetry> {
  const headers = await getAuthHeaders();
  const res = await fetch(`${API_BASE_URL}/api/recovery/intelligence/observability/database`, {
    headers,
    cache: "no-store",
  });
  if (!res.ok) {
    throw new Error(`Failed to fetch database telemetry: ${res.statusText}`);
  }
  return res.json();
}

export async function acknowledgeObservabilityIncident(incidentId: string): Promise<ObservabilityIncident> {
  const headers = await getAuthHeaders();
  const res = await fetch(
    `${API_BASE_URL}/api/recovery/intelligence/observability/incidents/${encodeURIComponent(incidentId)}/acknowledge`,
    {
      method: "POST",
      headers,
    }
  );
  if (!res.ok) {
    throw new Error(`Failed to acknowledge incident: ${res.statusText}`);
  }
  return res.json();
}

export async function escalateObservabilityIncident(incidentId: string): Promise<ObservabilityIncident> {
  const headers = await getAuthHeaders();
  const res = await fetch(
    `${API_BASE_URL}/api/recovery/intelligence/observability/incidents/${encodeURIComponent(incidentId)}/escalate`,
    {
      method: "POST",
      headers,
    }
  );
  if (!res.ok) {
    throw new Error(`Failed to escalate incident: ${res.statusText}`);
  }
  return res.json();
}

export async function resolveObservabilityIncident(incidentId: string): Promise<ObservabilityIncident> {
  const headers = await getAuthHeaders();
  const res = await fetch(
    `${API_BASE_URL}/api/recovery/intelligence/observability/incidents/${encodeURIComponent(incidentId)}/resolve`,
    {
      method: "POST",
      headers,
    }
  );
  if (!res.ok) {
    throw new Error(`Failed to resolve incident: ${res.statusText}`);
  }
  return res.json();
}

export async function createObservabilityPostmortem(data: {
  incident_id: string;
  title: string;
  impact_summary: string;
  root_cause_category: string;
  contributing_factors: string[];
  corrective_actions: string[];
  preventive_actions: string[];
}): Promise<PostIncidentReport> {
  const headers = await getAuthHeaders();
  const res = await fetch(`${API_BASE_URL}/api/recovery/intelligence/observability/postmortems`, {
    method: "POST",
    headers: { ...headers, "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });
  if (!res.ok) {
    throw new Error(`Failed to create postmortem: ${res.statusText}`);
  }
  return res.json();
}

// =========================================================================
// Phase 10E: Data Governance, Privacy Engineering, Data Lineage & Regulatory-Grade Data Controls
// =========================================================================

export type DataClassification =
  | "PUBLIC"
  | "INTERNAL"
  | "CONFIDENTIAL"
  | "SENSITIVE"
  | "RESTRICTED"
  | "FINANCIAL_RESTRICTED";

export type DataDomain =
  | "PAYMENT"
  | "RECOVERY"
  | "CUSTOMER"
  | "ML"
  | "AUDIT"
  | "SECURITY"
  | "OBSERVABILITY"
  | "COMPLIANCE"
  | "EXPERIMENTATION"
  | "DEPLOYMENT"
  | "RESILIENCE";

export type DataOwnerRole =
  | "DATA_OWNER"
  | "DATA_STEWARD"
  | "SECURITY_ADMIN"
  | "COMPLIANCE_OPERATOR"
  | "SYSTEM_ADMIN";

export type ProcessingPurpose =
  | "PAYMENT_PROCESSING"
  | "RECOVERY_ANALYTICS"
  | "MODEL_TRAINING"
  | "MODEL_EVALUATION"
  | "SECURITY_MONITORING"
  | "AUDIT"
  | "COMPLIANCE"
  | "OBSERVABILITY"
  | "DISASTER_RECOVERY";

export type PrivacyControlStatus = "PASS" | "WARNING" | "FAIL" | "NOT_APPLICABLE";

export type RetentionStatus =
  | "WITHIN_POLICY"
  | "EXPIRING_SOON"
  | "OVERDUE"
  | "LEGAL_HOLD"
  | "EXEMPT";

export type LineageNodeType =
  | "SOURCE"
  | "INGESTION"
  | "TRANSFORMATION"
  | "DATASET"
  | "MODEL"
  | "PREDICTION"
  | "DECISION"
  | "OUTPUT"
  | "AUDIT";

export type PrivacyIncidentSeverity = "LOW" | "MEDIUM" | "HIGH" | "CRITICAL";

export type PrivacyRequestType =
  | "ACCESS"
  | "EXPORT"
  | "RECTIFICATION"
  | "ERASURE"
  | "RESTRICTION"
  | "PROCESSING_PURPOSE";

export type PrivacyRequestStatus =
  | "RECEIVED"
  | "UNDER_REVIEW"
  | "APPROVED"
  | "REJECTED"
  | "COMPLETED"
  | "BLOCKED";

export type DataQualityStatus = "HEALTHY" | "DEGRADED" | "CRITICAL";

export type GovernanceScoreClassification =
  | "EXCELLENT"
  | "GOOD"
  | "WARNING"
  | "HIGH_RISK"
  | "CRITICAL";

export interface DataFieldClassification {
  field_name: string;
  asset_name: string;
  classification: DataClassification;
  sensitivity: string;
  pii_category?: string | null;
  financial_sensitivity: boolean;
  masking_requirement: string;
  encryption_requirement: string;
  retention_requirement: string;
}

export interface DataAsset {
  asset_id: string;
  asset_name: string;
  domain: DataDomain;
  classification: DataClassification;
  owner_role: DataOwnerRole;
  processing_purpose: ProcessingPurpose;
  contains_pii: boolean;
  contains_financial_data: boolean;
  contains_credentials: boolean;
  retention_policy: string;
  record_count: number;
  storage_type: string;
  encryption_status: string;
  created_at: string;
  last_scanned_at: string;
  fields: DataFieldClassification[];
}

export interface DataAssetSummary {
  asset_id: string;
  asset_name: string;
  domain: DataDomain;
  classification: DataClassification;
  owner_role: DataOwnerRole;
  processing_purpose: ProcessingPurpose;
  contains_pii: boolean;
  contains_financial_data: boolean;
  contains_credentials: boolean;
  retention_status: RetentionStatus;
  record_count: number;
  last_scanned_at: string;
}

export interface DataLineageNode {
  node_id: string;
  node_type: LineageNodeType;
  name: string;
  domain: DataDomain;
  source_system: string;
  transformation: string;
  schema_version: string;
  checksum: string;
  timestamp: string;
  metadata: Record<string, any>;
}

export interface DataLineageEdge {
  edge_id: string;
  source_node_id: string;
  destination_node_id: string;
  transformation_type: string;
  transformation_hash: string;
  timestamp: string;
}

export interface DataLineageGraph {
  graph_id: string;
  nodes: DataLineageNode[];
  edges: DataLineageEdge[];
  integrity_status: string;
  orphan_nodes_count: number;
  broken_links_count: number;
  coverage_pct: number;
  generated_at: string;
}

export interface RetentionAssetStatus {
  asset_id: string;
  asset_name: string;
  domain: DataDomain;
  policy_id: string;
  retention_duration_days: number;
  oldest_record_at: string;
  expiration_at: string;
  status: RetentionStatus;
  legal_hold: boolean;
  deletion_eligible: boolean;
  reason: string;
}

export interface PrivacyControl {
  control_id: string;
  name: string;
  category: string;
  status: PrivacyControlStatus;
  severity: PrivacyIncidentSeverity;
  observed_value: string;
  threshold: string;
  evidence: string;
  remediation: string;
}

export interface PrivacyIncident {
  incident_id: string;
  severity: PrivacyIncidentSeverity;
  category: string;
  title: string;
  affected_asset: string;
  detection_timestamp: string;
  status: string;
  evidence_hash: string;
  remediation_state: string;
  details: string;
}

export interface PrivacyRequest {
  request_id: string;
  request_type: PrivacyRequestType;
  status: PrivacyRequestStatus;
  subject_pseudonym: string;
  scope: string;
  received_at: string;
  reviewed_at?: string | null;
  completed_at?: string | null;
  actor_id: string;
  actor_role: string;
  erasure_eligible: boolean;
  evidence_reference: string;
  notes?: string | null;
}

export interface DataQualityMetric {
  completeness_pct: number;
  validity_pct: number;
  uniqueness_pct: number;
  consistency_pct: number;
  freshness_seconds: number;
  anomaly_rate_pct: number;
  score: number;
  status: DataQualityStatus;
  details: Record<string, any>;
}

export interface DataGovernancePIIScanFinding {
  field_path: string;
  detected_category: string;
  severity: PrivacyIncidentSeverity;
  masked_value: string;
  evidence_hash: string;
}

export interface DataGovernancePIIScanResponse {
  findings_count: number;
  findings: DataGovernancePIIScanFinding[];
  has_critical_findings: boolean;
  scanned_fields_count: number;
  scan_duration_ms: number;
  disclaimer: string;
}

export interface ErasureEligibilityEvaluation {
  subject_pseudonym: string;
  eligible_for_erasure: boolean;
  legal_hold_active: boolean;
  financial_record_retention_required: boolean;
  audit_retention_required: boolean;
  blocker_reasons: string[];
  advisory_notice: string;
}

export interface DataGovernanceScoreBreakdown {
  privacy_controls_score: number;
  data_quality_score: number;
  data_lineage_score: number;
  retention_score: number;
  access_governance_score: number;
  security_controls_score: number;
  audit_coverage_score: number;
  data_minimization_score: number;
}

export interface DataGovernanceSummary {
  governance_score: number;
  classification: GovernanceScoreClassification;
  score_breakdown: DataGovernanceScoreBreakdown;
  total_assets_count: number;
  sensitive_assets_count: number;
  lineage_coverage_pct: number;
  retention_compliance_pct: number;
  data_quality_score: number;
  data_quality_status: DataQualityStatus;
  active_privacy_incidents_count: number;
  pending_privacy_requests_count: number;
  controls_passed_count: number;
  controls_total_count: number;
  last_scanned_at: string;
  disclaimer: string;
}

export interface DataGovernanceReport {
  report_id: string;
  generated_at: string;
  generated_by: string;
  summary: DataGovernanceSummary;
  assets: DataAssetSummary[];
  controls: PrivacyControl[];
  data_quality: DataQualityMetric;
  retention_statuses: RetentionAssetStatus[];
  incidents: PrivacyIncident[];
  privacy_requests: PrivacyRequest[];
  remediation_roadmap: string[];
  verification_signature: string;
}

// -------------------------------------------------------------------------
// Phase 10E API Fetchers
// -------------------------------------------------------------------------

export async function fetchDataGovernanceSummary(): Promise<DataGovernanceSummary> {
  const headers = await getAuthHeaders();
  const res = await fetch(`${API_BASE_URL}/api/recovery/intelligence/data-governance`, {
    headers,
    cache: "no-store",
  });
  if (!res.ok) {
    throw new Error(`Failed to fetch Data Governance summary: ${res.statusText}`);
  }
  return res.json();
}

export async function fetchDataGovernanceAssets(): Promise<DataAsset[]> {
  const headers = await getAuthHeaders();
  const res = await fetch(`${API_BASE_URL}/api/recovery/intelligence/data-governance/assets`, {
    headers,
    cache: "no-store",
  });
  if (!res.ok) {
    throw new Error(`Failed to fetch Data Governance assets: ${res.statusText}`);
  }
  return res.json();
}

export async function fetchDataGovernanceAssetDetail(assetId: string): Promise<DataAsset> {
  const headers = await getAuthHeaders();
  const res = await fetch(
    `${API_BASE_URL}/api/recovery/intelligence/data-governance/assets/${encodeURIComponent(assetId)}`,
    {
      headers,
      cache: "no-store",
    }
  );
  if (!res.ok) {
    throw new Error(`Failed to fetch Data Governance asset detail: ${res.statusText}`);
  }
  return res.json();
}

export async function fetchDataGovernanceControls(params?: {
  category?: string;
  status?: string;
  severity?: string;
}): Promise<PrivacyControl[]> {
  const headers = await getAuthHeaders();
  const q = new URLSearchParams();
  if (params?.category && params.category !== "ALL") q.append("category", params.category);
  if (params?.status && params.status !== "ALL") q.append("status", params.status);
  if (params?.severity && params.severity !== "ALL") q.append("severity", params.severity);

  const url = `${API_BASE_URL}/api/recovery/intelligence/data-governance/controls${q.toString() ? `?${q.toString()}` : ""}`;
  const res = await fetch(url, { headers, cache: "no-store" });
  if (!res.ok) {
    throw new Error(`Failed to fetch Privacy Controls: ${res.statusText}`);
  }
  return res.json();
}

export async function fetchDataGovernanceQuality(): Promise<DataQualityMetric> {
  const headers = await getAuthHeaders();
  const res = await fetch(`${API_BASE_URL}/api/recovery/intelligence/data-governance/data-quality`, {
    headers,
    cache: "no-store",
  });
  if (!res.ok) {
    throw new Error(`Failed to fetch Data Quality metrics: ${res.statusText}`);
  }
  return res.json();
}

export async function fetchDataGovernanceLineage(): Promise<DataLineageGraph> {
  const headers = await getAuthHeaders();
  const res = await fetch(`${API_BASE_URL}/api/recovery/intelligence/data-governance/lineage`, {
    headers,
    cache: "no-store",
  });
  if (!res.ok) {
    throw new Error(`Failed to fetch Data Lineage graph: ${res.statusText}`);
  }
  return res.json();
}

export async function fetchDataGovernanceLineageNode(assetId: string): Promise<DataLineageNode> {
  const headers = await getAuthHeaders();
  const res = await fetch(
    `${API_BASE_URL}/api/recovery/intelligence/data-governance/lineage/${encodeURIComponent(assetId)}`,
    {
      headers,
      cache: "no-store",
    }
  );
  if (!res.ok) {
    throw new Error(`Failed to fetch Data Lineage node: ${res.statusText}`);
  }
  return res.json();
}

export async function fetchDataGovernanceRetention(): Promise<RetentionAssetStatus[]> {
  const headers = await getAuthHeaders();
  const res = await fetch(`${API_BASE_URL}/api/recovery/intelligence/data-governance/retention`, {
    headers,
    cache: "no-store",
  });
  if (!res.ok) {
    throw new Error(`Failed to fetch Retention statuses: ${res.statusText}`);
  }
  return res.json();
}

export async function fetchDataGovernanceErasureEligibility(
  subjectId: string
): Promise<ErasureEligibilityEvaluation> {
  const headers = await getAuthHeaders();
  const res = await fetch(
    `${API_BASE_URL}/api/recovery/intelligence/data-governance/erasure-eligibility/${encodeURIComponent(subjectId)}`,
    {
      headers,
      cache: "no-store",
    }
  );
  if (!res.ok) {
    throw new Error(`Failed to fetch Erasure eligibility: ${res.statusText}`);
  }
  return res.json();
}

export async function fetchDataGovernanceIncidents(): Promise<PrivacyIncident[]> {
  const headers = await getAuthHeaders();
  const res = await fetch(`${API_BASE_URL}/api/recovery/intelligence/data-governance/incidents`, {
    headers,
    cache: "no-store",
  });
  if (!res.ok) {
    throw new Error(`Failed to fetch Privacy incidents: ${res.statusText}`);
  }
  return res.json();
}

export async function fetchDataGovernancePrivacyRequests(): Promise<PrivacyRequest[]> {
  const headers = await getAuthHeaders();
  const res = await fetch(
    `${API_BASE_URL}/api/recovery/intelligence/data-governance/privacy-requests`,
    {
      headers,
      cache: "no-store",
    }
  );
  if (!res.ok) {
    throw new Error(`Failed to fetch Privacy requests: ${res.statusText}`);
  }
  return res.json();
}

export async function createDataGovernancePrivacyRequest(data: {
  request_type: string;
  subject_id: string;
  scope?: string;
  notes?: string;
}): Promise<PrivacyRequest> {
  const headers = await getAuthHeaders();
  const res = await fetch(
    `${API_BASE_URL}/api/recovery/intelligence/data-governance/privacy-requests`,
    {
      method: "POST",
      headers: { ...headers, "Content-Type": "application/json" },
      body: JSON.stringify(data),
    }
  );
  if (!res.ok) {
    throw new Error(`Failed to create privacy request: ${res.statusText}`);
  }
  return res.json();
}

export async function reviewDataGovernancePrivacyRequest(
  id: string,
  data: { decision: "APPROVE" | "REJECT"; notes: string }
): Promise<PrivacyRequest> {
  const headers = await getAuthHeaders();
  const res = await fetch(
    `${API_BASE_URL}/api/recovery/intelligence/data-governance/privacy-requests/${encodeURIComponent(id)}/review`,
    {
      method: "POST",
      headers: { ...headers, "Content-Type": "application/json" },
      body: JSON.stringify(data),
    }
  );
  if (!res.ok) {
    throw new Error(`Failed to review privacy request: ${res.statusText}`);
  }
  return res.json();
}

export async function completeDataGovernancePrivacyRequest(
  id: string,
  data: { notes: string }
): Promise<PrivacyRequest> {
  const headers = await getAuthHeaders();
  const res = await fetch(
    `${API_BASE_URL}/api/recovery/intelligence/data-governance/privacy-requests/${encodeURIComponent(id)}/complete`,
    {
      method: "POST",
      headers: { ...headers, "Content-Type": "application/json" },
      body: JSON.stringify(data),
    }
  );
  if (!res.ok) {
    throw new Error(`Failed to complete privacy request: ${res.statusText}`);
  }
  return res.json();
}

export async function fetchDataGovernanceReport(): Promise<DataGovernanceReport> {
  const headers = await getAuthHeaders();
  const res = await fetch(`${API_BASE_URL}/api/recovery/intelligence/data-governance/report`, {
    headers,
    cache: "no-store",
  });
  if (!res.ok) {
    throw new Error(`Failed to fetch Data Governance report: ${res.statusText}`);
  }
  return res.json();
}

export async function runDataGovernancePIIScan(payload: any): Promise<DataGovernancePIIScanResponse> {
  const headers = await getAuthHeaders();
  const res = await fetch(`${API_BASE_URL}/api/recovery/intelligence/data-governance/scan`, {
    method: "POST",
    headers: { ...headers, "Content-Type": "application/json" },
    body: JSON.stringify({ payload }),
  });
  if (!res.ok) {
    throw new Error(`Failed to run PII scan: ${res.statusText}`);
  }
  return res.json();
}

// =========================================================================
// Phase 10F: Fintech Performance Engineering, Scalability, Capacity Planning & High-Load Resilience
// =========================================================================

export type PerformanceHealth = "EXCELLENT" | "GOOD" | "WARNING" | "DEGRADED" | "CRITICAL";

export type PerformanceGlobalState =
  | "EMERGENCY_CAPACITY_FAILURE"
  | "PERFORMANCE_CRITICAL"
  | "CAPACITY_EXHAUSTION"
  | "SEVERE_DEGRADATION"
  | "PERFORMANCE_DEGRADED"
  | "HIGH_UTILIZATION"
  | "SCALING_RECOMMENDED"
  | "PERFORMANCE_WARNING"
  | "MONITORING"
  | "HEALTHY";

export type PerformanceSeverity = "LOW" | "MEDIUM" | "HIGH" | "CRITICAL";

export type CapacityState = "SAFE" | "ADEQUATE" | "CONSTRAINED" | "EXHAUSTED" | "CRITICAL";

export type QueueState = "QUEUE_HEALTHY" | "QUEUE_GROWING" | "QUEUE_SATURATED" | "QUEUE_CRITICAL";

export type DatabasePerformanceState = "DB_HEALTHY" | "DB_WARNING" | "DB_DEGRADED" | "DB_SATURATED" | "DB_CRITICAL";

export type CachePerformanceState = "CACHE_HEALTHY" | "CACHE_WARNING" | "CACHE_DEGRADED" | "CACHE_PRESSURED" | "CACHE_CRITICAL";

export type BottleneckType =
  | "API"
  | "DATABASE"
  | "REDIS"
  | "QUEUE"
  | "WORKER"
  | "ML"
  | "WEBHOOK"
  | "CPU"
  | "MEMORY"
  | "NETWORK"
  | "EXTERNAL_PROVIDER"
  | "NONE";

export type ScalingRecommendation =
  | "NO_SCALING_REQUIRED"
  | "MONITOR"
  | "SCALE_SOON"
  | "SCALE_NOW"
  | "EMERGENCY_SCALE";

export type LoadTestScenario =
  | "API_NORMAL"
  | "API_2X"
  | "API_5X"
  | "API_10X"
  | "API_20X"
  | "WEBHOOK_NORMAL"
  | "WEBHOOK_5X"
  | "WEBHOOK_10X"
  | "WEBHOOK_20X"
  | "RECOVERY_NORMAL"
  | "RECOVERY_5X"
  | "RECOVERY_10X"
  | "ML_NORMAL"
  | "ML_5X"
  | "ML_10X"
  | "DATABASE_PRESSURE"
  | "CACHE_PRESSURE"
  | "QUEUE_PRESSURE";

export type LoadTestStatus = "INITIALIZED" | "RUNNING" | "COMPLETED" | "FAILED" | "ABORTED";

export type PerformanceIncidentType =
  | "PERF_LATENCY_CRITICAL"
  | "PERF_THROUGHPUT_COLLAPSE"
  | "PERF_DB_SATURATION"
  | "PERF_QUEUE_EXPLOSION"
  | "PERF_ML_BACKLOG"
  | "PERF_CACHE_PRESSURE"
  | "PERF_WORKER_SATURATION"
  | "PERF_CAPACITY_EXHAUSTION";

export type PerformanceIncidentStatus = "DETECTED" | "INVESTIGATING" | "MITIGATING" | "RESOLVED" | "AUTO_REMEDIATED";

export interface PerformanceScoreBreakdown {
  latency_score: number;
  throughput_score: number;
  database_score: number;
  queue_score: number;
  cache_score: number;
  ml_score: number;
  webhook_score: number;
  cpu_score: number;
  memory_score: number;
  capacity_score: number;
}

export interface PerformanceSummary {
  score: number;
  classification: PerformanceHealth;
  global_state: PerformanceGlobalState;
  current_rpm: number;
  peak_rpm: number;
  safe_rpm: number;
  current_latency_ms: number;
  p95_latency_ms: number;
  p99_latency_ms: number;
  error_rate: number;
  capacity_utilization_pct: number;
  headroom_pct: number;
  active_bottlenecks_count: number;
  scaling_recommendation: ScalingRecommendation;
  active_incidents_count: number;
  score_breakdown: PerformanceScoreBreakdown;
  evaluated_at: string;
  disclaimer: string;
}

export interface PerformanceServiceMetric {
  service_name: string;
  rpm: number;
  throughput_tps: number;
  p50_latency_ms: number;
  p95_latency_ms: number;
  p99_latency_ms: number;
  error_rate_pct: number;
  timeout_rate_pct: number;
  cpu_utilization_pct: number;
  memory_utilization_pct: number;
  queue_depth: number;
  saturation_pct: number;
  concurrency: number;
  capacity_utilization_pct: number;
  remaining_headroom_pct: number;
  status: string;
}

export interface CapacityAssessment {
  current_capacity_rpm: number;
  peak_capacity_rpm: number;
  safe_capacity_rpm: number;
  theoretical_capacity_rpm: number;
  current_utilization_pct: number;
  peak_utilization_pct: number;
  headroom_pct: number;
  capacity_state: CapacityState;
  scaling_recommendation: ScalingRecommendation;
  evaluated_at: string;
}

export interface TrafficProjectionScenario {
  multiplier: string;
  expected_rpm: number;
  expected_latency_ms: number;
  expected_cpu_pct: number;
  expected_memory_pct: number;
  expected_db_load_pct: number;
  expected_queue_depth: number;
  expected_ml_load_pct: number;
  expected_cache_load_pct: number;
  expected_saturation_pct: number;
  projected_state: PerformanceGlobalState;
  scaling_recommendation: ScalingRecommendation;
}

export interface CapacityForecast {
  scenarios: TrafficProjectionScenario[];
  forecast_timestamp: string;
  bottleneck_under_20x: BottleneckType;
  headroom_summary: string;
}

export interface QueuePerformance {
  queue_name: string;
  queue_depth: number;
  arrival_rate_per_sec: number;
  processing_rate_per_sec: number;
  oldest_job_age_sec: number;
  backlog_growth_pct: number;
  worker_utilization_pct: number;
  drain_time_sec: number;
  state: QueueState;
  recommendation: string;
}

export interface DatabasePerformance {
  p50_latency_ms: number;
  p95_latency_ms: number;
  p99_latency_ms: number;
  slow_query_count: number;
  active_connections: number;
  waiting_connections: number;
  pool_utilization_pct: number;
  lock_wait_time_ms: number;
  transaction_duration_ms: number;
  query_throughput_qps: number;
  saturation_pct: number;
  state: DatabasePerformanceState;
  recommendations: string[];
}

export interface CachePerformance {
  hit_ratio_pct: number;
  miss_ratio_pct: number;
  command_latency_ms: number;
  memory_utilization_pct: number;
  eviction_rate_per_sec: number;
  connection_utilization_pct: number;
  cache_efficiency_pct: number;
  state: CachePerformanceState;
  cache_pressure: boolean;
  recommendations: string[];
}

export interface MLPerformance {
  inference_rpm: number;
  throughput_rps: number;
  p50_latency_ms: number;
  p95_latency_ms: number;
  p99_latency_ms: number;
  queue_delay_ms: number;
  model_load_time_ms: number;
  prediction_failure_rate_pct: number;
  cpu_utilization_pct: number;
  memory_utilization_pct: number;
  state: string;
  recommendations: string[];
}

export interface WebhookPerformance {
  ingestion_latency_ms: number;
  processing_latency_ms: number;
  ingestion_throughput_tps: number;
  processing_throughput_tps: number;
  queue_depth: number;
  duplicate_rate_pct: number;
  backlog_age_sec: number;
  drain_time_sec: number;
  burst_scenarios: Record<string, any>;
}

export interface BottleneckFinding {
  bottleneck_id: string;
  subsystem: BottleneckType;
  severity: PerformanceSeverity;
  observed_metric: string;
  threshold: string;
  evidence: string;
  impact: string;
  recommended_action: string;
  is_primary: boolean;
}

export interface PerformanceIncident {
  incident_id: string;
  incident_type: PerformanceIncidentType;
  severity: PerformanceSeverity;
  status: PerformanceIncidentStatus;
  detection_timestamp: string;
  affected_subsystem: string;
  observed_metrics: Record<string, any>;
  threshold: string;
  impact: string;
  probable_cause: string;
  recommended_mitigation: string;
  lifecycle_events: Array<Record<string, any>>;
}

export interface LoadTestRequest {
  scenario: LoadTestScenario;
  duration_seconds?: number;
  target_rpm?: number;
  notes?: string | null;
}

export interface LoadTestRun {
  test_id: string;
  scenario: LoadTestScenario;
  status: LoadTestStatus;
  start_timestamp: string;
  duration_seconds: number;
  target_throughput_rpm: number;
  achieved_throughput_rpm: number;
  p50_latency_ms: number;
  p95_latency_ms: number;
  p99_latency_ms: number;
  error_rate_pct: number;
  timeout_rate_pct: number;
  peak_cpu_pct: number;
  peak_memory_pct: number;
  db_utilization_pct: number;
  queue_utilization_pct: number;
  cache_utilization_pct: number;
  bottleneck: BottleneckType;
  capacity_result: string;
  safety_result: string;
  financial_isolation_verified: boolean;
  initiated_by: string;
}

export interface PerformanceRegression {
  regression_id: string;
  metric_name: string;
  current_value: number;
  baseline_value: number;
  delta_pct: number;
  regression_type: string;
  severity: PerformanceSeverity;
  detected_at: string;
}

export interface PerformanceReadinessGate {
  code: string;
  name: string;
  status: "PASS" | "WARN" | "FAIL" | string;
  observed_value: string;
  threshold: string;
  severity: PerformanceSeverity;
  evidence: string;
  remediation: string;
}

export interface PerformanceReport {
  report_id: string;
  generated_at: string;
  performance_score: number;
  global_state: PerformanceGlobalState;
  summary: PerformanceSummary;
  services: PerformanceServiceMetric[];
  capacity: CapacityAssessment;
  bottlenecks: BottleneckFinding[];
  incidents: PerformanceIncident[];
  gates: PerformanceReadinessGate[];
  verification_signature: string;
}

// -------------------------------------------------------------------------
// Phase 10F Fetchers & Mutations
// -------------------------------------------------------------------------

export async function fetchPerformanceSummary(): Promise<PerformanceSummary> {
  const headers = await getAuthHeaders();
  const res = await fetch(`${API_BASE_URL}/api/recovery/intelligence/performance`, {
    headers,
    cache: "no-store",
  });
  if (!res.ok) {
    throw new Error(`Failed to fetch performance summary: ${res.statusText}`);
  }
  return res.json();
}

export async function fetchPerformanceServices(): Promise<PerformanceServiceMetric[]> {
  const headers = await getAuthHeaders();
  const res = await fetch(`${API_BASE_URL}/api/recovery/intelligence/performance/services`, {
    headers,
    cache: "no-store",
  });
  if (!res.ok) {
    throw new Error(`Failed to fetch performance services: ${res.statusText}`);
  }
  return res.json();
}

export async function fetchCapacityAssessment(): Promise<CapacityAssessment> {
  const headers = await getAuthHeaders();
  const res = await fetch(`${API_BASE_URL}/api/recovery/intelligence/performance/capacity`, {
    headers,
    cache: "no-store",
  });
  if (!res.ok) {
    throw new Error(`Failed to fetch capacity assessment: ${res.statusText}`);
  }
  return res.json();
}

export async function fetchCapacityForecast(): Promise<CapacityForecast> {
  const headers = await getAuthHeaders();
  const res = await fetch(`${API_BASE_URL}/api/recovery/intelligence/performance/capacity/forecast`, {
    headers,
    cache: "no-store",
  });
  if (!res.ok) {
    throw new Error(`Failed to fetch capacity forecast: ${res.statusText}`);
  }
  return res.json();
}

export async function fetchQueuePerformance(): Promise<QueuePerformance[]> {
  const headers = await getAuthHeaders();
  const res = await fetch(`${API_BASE_URL}/api/recovery/intelligence/performance/queues`, {
    headers,
    cache: "no-store",
  });
  if (!res.ok) {
    throw new Error(`Failed to fetch queue performance: ${res.statusText}`);
  }
  return res.json();
}

export async function fetchDatabasePerformance(): Promise<DatabasePerformance> {
  const headers = await getAuthHeaders();
  const res = await fetch(`${API_BASE_URL}/api/recovery/intelligence/performance/database`, {
    headers,
    cache: "no-store",
  });
  if (!res.ok) {
    throw new Error(`Failed to fetch database performance: ${res.statusText}`);
  }
  return res.json();
}

export async function fetchCachePerformance(): Promise<CachePerformance> {
  const headers = await getAuthHeaders();
  const res = await fetch(`${API_BASE_URL}/api/recovery/intelligence/performance/cache`, {
    headers,
    cache: "no-store",
  });
  if (!res.ok) {
    throw new Error(`Failed to fetch cache performance: ${res.statusText}`);
  }
  return res.json();
}

export async function fetchMLPerformance(): Promise<MLPerformance> {
  const headers = await getAuthHeaders();
  const res = await fetch(`${API_BASE_URL}/api/recovery/intelligence/performance/ml`, {
    headers,
    cache: "no-store",
  });
  if (!res.ok) {
    throw new Error(`Failed to fetch ML performance: ${res.statusText}`);
  }
  return res.json();
}

export async function fetchWebhookPerformance(): Promise<WebhookPerformance> {
  const headers = await getAuthHeaders();
  const res = await fetch(`${API_BASE_URL}/api/recovery/intelligence/performance/webhooks`, {
    headers,
    cache: "no-store",
  });
  if (!res.ok) {
    throw new Error(`Failed to fetch webhook performance: ${res.statusText}`);
  }
  return res.json();
}

export async function fetchBottleneckFindings(): Promise<BottleneckFinding[]> {
  const headers = await getAuthHeaders();
  const res = await fetch(`${API_BASE_URL}/api/recovery/intelligence/performance/bottlenecks`, {
    headers,
    cache: "no-store",
  });
  if (!res.ok) {
    throw new Error(`Failed to fetch bottleneck findings: ${res.statusText}`);
  }
  return res.json();
}

export async function fetchPerformanceIncidents(): Promise<PerformanceIncident[]> {
  const headers = await getAuthHeaders();
  const res = await fetch(`${API_BASE_URL}/api/recovery/intelligence/performance/incidents`, {
    headers,
    cache: "no-store",
  });
  if (!res.ok) {
    throw new Error(`Failed to fetch performance incidents: ${res.statusText}`);
  }
  return res.json();
}

export async function fetchPerformanceGates(): Promise<PerformanceReadinessGate[]> {
  const headers = await getAuthHeaders();
  const res = await fetch(`${API_BASE_URL}/api/recovery/intelligence/performance/gates`, {
    headers,
    cache: "no-store",
  });
  if (!res.ok) {
    throw new Error(`Failed to fetch performance gates: ${res.statusText}`);
  }
  return res.json();
}

export async function fetchPerformanceRegressions(): Promise<PerformanceRegression[]> {
  const headers = await getAuthHeaders();
  const res = await fetch(`${API_BASE_URL}/api/recovery/intelligence/performance/regressions`, {
    headers,
    cache: "no-store",
  });
  if (!res.ok) {
    throw new Error(`Failed to fetch performance regressions: ${res.statusText}`);
  }
  return res.json();
}

export async function fetchLoadTestRuns(): Promise<LoadTestRun[]> {
  const headers = await getAuthHeaders();
  const res = await fetch(`${API_BASE_URL}/api/recovery/intelligence/performance/load-tests`, {
    headers,
    cache: "no-store",
  });
  if (!res.ok) {
    throw new Error(`Failed to fetch load test runs: ${res.statusText}`);
  }
  return res.json();
}

export async function executeLoadTestRun(data: LoadTestRequest): Promise<LoadTestRun> {
  const headers = await getAuthHeaders();
  const res = await fetch(`${API_BASE_URL}/api/recovery/intelligence/performance/load-tests`, {
    method: "POST",
    headers: { ...headers, "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });
  if (!res.ok) {
    throw new Error(`Failed to execute synthetic load test: ${res.statusText}`);
  }
  return res.json();
}

export async function fetchPerformanceReport(): Promise<PerformanceReport> {
  const headers = await getAuthHeaders();
  const res = await fetch(`${API_BASE_URL}/api/recovery/intelligence/performance/report`, {
    headers,
    cache: "no-store",
  });
  if (!res.ok) {
    throw new Error(`Failed to fetch performance report: ${res.statusText}`);
  }
  return res.json();
}

// =============================================================================
// Phase 10G: Fintech Architecture Governance, Change Management & Release Safety
// =============================================================================

export type ChangeType =
  | "FEATURE"
  | "BUGFIX"
  | "SECURITY"
  | "DATABASE"
  | "API"
  | "CONFIGURATION"
  | "DEPENDENCY"
  | "ML_MODEL"
  | "INFRASTRUCTURE"
  | "HOTFIX";

export type ChangeRiskLevel = "LOW" | "MEDIUM" | "HIGH" | "CRITICAL";

export type ChangeStatus = "PROPOSED" | "IN_REVIEW" | "APPROVED" | "REJECTED" | "DEPLOYED" | "CANCELLED";

export type ChangeApprovalStatus = "PENDING" | "APPROVED" | "REJECTED" | "CHANGES_REQUESTED";

export type ReleaseStage = "DRAFT" | "TESTING" | "STAGING" | "CANARY" | "PRODUCTION" | "ROLLED_BACK";

export type ReleaseStatus = "PREPARING" | "READY_FOR_REVIEW" | "APPROVED" | "IN_PROGRESS" | "SUCCESSFUL" | "FAILED" | "ABORTED";

export type ReleaseHealth = "EXCELLENT" | "HEALTHY" | "WARNING" | "DEGRADED" | "CRITICAL";

export type ReleaseDecision = "GO" | "NO_GO" | "CONDITIONAL_GO" | "PENDING_REVIEW";

export type DeploymentStrategy = "BLUE_GREEN" | "CANARY" | "ROLLING" | "SHADOW" | "ROLLBACK";

export type ArchitectureRisk = "LOW" | "MEDIUM" | "HIGH" | "CRITICAL";

export type DependencyRisk = "LOW" | "MEDIUM" | "HIGH" | "CRITICAL";

export type CompatibilityStatus = "BACKWARD_COMPATIBLE" | "NON_BREAKING" | "BREAKING" | "UNKNOWN";

export type ArchitectureLayer = "GATEWAY" | "CORE_ENGINE" | "DATA_TIER" | "INTEGRATION" | "OBSERVABILITY" | "GOVERNANCE";

export type ConfigurationDriftStatus = "IN_SYNC" | "DRIFT_DETECTED" | "CRITICAL_DRIFT" | "OVERRIDDEN";

export type FeatureFlagStatus = "CREATED" | "ACTIVE" | "ROLLOUT" | "PAUSED" | "ROLLED_BACK" | "RETIRED";

export type GovernanceDecision = "APPROVE" | "REJECT" | "REQUEST_CHANGES" | "HOLD";

export interface ChangeImpact {
  affected_services: string[];
  is_financial_path: boolean;
  database_impact: boolean;
  breaking_api_impact: boolean;
  authentication_impact: boolean;
  ml_model_impact: boolean;
  configuration_impact: boolean;
  blast_radius_score: number;
}

export interface ChangeRiskAssessment {
  risk_score: number;
  risk_level: ChangeRiskLevel;
  financial_risk_multiplier: number;
  risk_factors: string[];
  mitigation_recommendations: string[];
}

export interface ChangeRequest {
  change_id: string;
  title: string;
  description: string;
  change_type: ChangeType;
  risk_level: ChangeRiskLevel;
  status: ChangeStatus;
  approval_status: ChangeApprovalStatus;
  owner_role: string;
  affected_services: string[];
  is_financial_path: boolean;
  requires_downtime: boolean;
  rollback_procedure: string;
  created_at: string;
  risk_assessment: ChangeRiskAssessment;
}

export interface ChangeRequestCreate {
  title: string;
  description: string;
  change_type: ChangeType;
  affected_services: string[];
  is_financial_path: boolean;
  requires_downtime: boolean;
  rollback_procedure: string;
}

export interface DependencyImpact {
  source_service: string;
  target_service: string;
  dependency_type: string;
  is_financial_path: boolean;
  is_single_point_of_failure: boolean;
  failure_propagation_risk: ArchitectureRisk;
  blast_radius: number;
}

export interface ArchitectureFinding {
  finding_id: string;
  layer: ArchitectureLayer;
  severity: ArchitectureRisk;
  title: string;
  description: string;
  affected_components: string[];
  remediation: string;
  created_at: string;
}

export interface ApiCompatibilityReport {
  total_endpoints: number;
  breaking_changes_count: number;
  non_breaking_changes_count: number;
  compatibility_status: CompatibilityStatus;
  breaking_details: string[];
  evaluated_at: string;
}

export interface DatabaseCompatibilityReport {
  schema_modifications_count: number;
  table_impacts: string[];
  is_migration_required: boolean;
  compatibility_status: CompatibilityStatus;
  breaking_risks: string[];
  evaluated_at: string;
}

export interface ConfigurationDrift {
  key: string;
  category: string;
  expected_value_masked: string;
  observed_value_masked: string;
  status: ConfigurationDriftStatus;
  severity: ArchitectureRisk;
  drift_detected_at: string;
  evidence_hash: string;
}

export interface FeatureFlag {
  flag_id: string;
  name: string;
  description: string;
  status: FeatureFlagStatus;
  rollout_percentage: number;
  environment: string;
  is_financial_path: boolean;
  owner: string;
  created_at: string;
  expiration_date?: string | null;
  is_stale: boolean;
}

export interface FeatureFlagUpdate {
  status?: FeatureFlagStatus;
  rollout_percentage?: number;
  rationale: string;
}

export interface ReleaseReadinessGate {
  code: string;
  name: string;
  status: "PASS" | "WARNING" | "BLOCKED" | "REVIEW_REQUIRED" | string;
  observed_value: string;
  threshold: string;
  evidence: string;
  remediation: string;
}

export interface ReleaseReadinessSummary {
  total_gates: number;
  passed_gates: number;
  warning_gates: number;
  blocked_gates: number;
  review_required_gates: number;
  overall_status: string;
  gates: ReleaseReadinessGate[];
}

export interface DeploymentObservation {
  environment: string;
  strategy: DeploymentStrategy;
  current_version: string;
  target_version: string;
  status: ReleaseStatus;
  observed_at: string;
  health_metrics: Record<string, any>;
}

export interface CanaryEvaluation {
  canary_version: string;
  traffic_percentage: number;
  baseline_p95_ms: number;
  canary_p95_ms: number;
  baseline_error_rate_pct: number;
  canary_error_rate_pct: number;
  decision: ReleaseDecision;
  recommendation_reason: string;
  evaluated_at: string;
}

export interface RollbackReadiness {
  previous_version_available: boolean;
  artifact_digest: string;
  database_reversible: boolean;
  config_reversible: boolean;
  estimated_recovery_time_sec: number;
  readiness_status: string;
  recommendations: string[];
}

export interface ReleaseApproval {
  approval_id: string;
  release_id: string;
  approver_id: string;
  approver_role: string;
  decision: GovernanceDecision;
  comments: string;
  decided_at: string;
}

export interface ReleaseApprovalRequest {
  decision: GovernanceDecision;
  comments: string;
}

export interface ReleaseIncident {
  incident_id: string;
  severity: ArchitectureRisk;
  affected_service: string;
  description: string;
  status: string;
  detected_at: string;
  mitigation: string;
}

export interface ReleaseLineageNode {
  node_id: string;
  stage: string;
  title: string;
  status: string;
  actor: string;
  timestamp: string;
  evidence_hash: string;
  details: Record<string, any>;
}

export interface ReleaseCandidate {
  rc_id: string;
  version: string;
  commit_sha: string;
  stage: ReleaseStage;
  status: ReleaseStatus;
  health: ReleaseHealth;
  decision: ReleaseDecision;
  deployment_strategy: DeploymentStrategy;
  change_requests: string[];
  affected_services: string[];
  risk_score: number;
  readiness_summary: ReleaseReadinessSummary;
  rollback_readiness: RollbackReadiness;
  created_at: string;
}

export interface ReleaseCandidateCreate {
  version: string;
  commit_sha: string;
  deployment_strategy: DeploymentStrategy;
  change_request_ids: string[];
}

export interface ReleaseGovernanceSummary {
  governance_score: number;
  classification: ReleaseHealth;
  global_state: ReleaseDecision;
  open_changes_count: number;
  high_risk_changes_count: number;
  release_candidates_count: number;
  readiness_score: number;
  config_drift_count: number;
  rollback_readiness_status: string;
  active_incidents_count: number;
  approved_releases_count: number;
  evaluated_at: string;
  disclaimer: string;
}

export interface ReleaseGovernanceReport {
  report_id: string;
  generated_at: string;
  governance_score: number;
  classification: ReleaseHealth;
  decision: ReleaseDecision;
  summary: ReleaseGovernanceSummary;
  change_requests: ChangeRequest[];
  readiness_gates: ReleaseReadinessGate[];
  config_drift: ConfigurationDrift[];
  feature_flags: FeatureFlag[];
  canary_evaluation: CanaryEvaluation;
  rollback_readiness: RollbackReadiness;
  incidents: ReleaseIncident[];
  verification_signature: string;
  isolation_verified: boolean;
}

// -----------------------------------------------------------------------------
// Phase 10G API Fetchers
// -----------------------------------------------------------------------------

export async function fetchReleaseGovernanceSummary(): Promise<ReleaseGovernanceSummary> {
  const headers = await getAuthHeaders();
  const res = await fetch(`${API_BASE_URL}/api/recovery/intelligence/release-governance`, {
    headers,
    cache: "no-store",
  });
  if (!res.ok) {
    throw new Error(`Failed to fetch release governance summary: ${res.statusText}`);
  }
  return res.json();
}

export async function fetchChangeRequests(): Promise<ChangeRequest[]> {
  const headers = await getAuthHeaders();
  const res = await fetch(`${API_BASE_URL}/api/recovery/intelligence/release-governance/changes`, {
    headers,
    cache: "no-store",
  });
  if (!res.ok) {
    throw new Error(`Failed to fetch change requests: ${res.statusText}`);
  }
  return res.json();
}

export async function createChangeRequest(data: ChangeRequestCreate): Promise<ChangeRequest> {
  const headers = await getAuthHeaders();
  const res = await fetch(`${API_BASE_URL}/api/recovery/intelligence/release-governance/changes`, {
    method: "POST",
    headers: { ...headers, "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });
  if (!res.ok) {
    throw new Error(`Failed to create change request: ${res.statusText}`);
  }
  return res.json();
}

export async function fetchChangeRequestDetails(changeId: string): Promise<ChangeRequest> {
  const headers = await getAuthHeaders();
  const res = await fetch(`${API_BASE_URL}/api/recovery/intelligence/release-governance/changes/${changeId}`, {
    headers,
    cache: "no-store",
  });
  if (!res.ok) {
    throw new Error(`Failed to fetch change request details: ${res.statusText}`);
  }
  return res.json();
}

export async function fetchChangeRiskAssessment(changeId: string): Promise<ChangeRiskAssessment> {
  const headers = await getAuthHeaders();
  const res = await fetch(`${API_BASE_URL}/api/recovery/intelligence/release-governance/risk/${changeId}`, {
    headers,
    cache: "no-store",
  });
  if (!res.ok) {
    throw new Error(`Failed to fetch change risk assessment: ${res.statusText}`);
  }
  return res.json();
}

export async function fetchDependencyImpacts(): Promise<DependencyImpact[]> {
  const headers = await getAuthHeaders();
  const res = await fetch(`${API_BASE_URL}/api/recovery/intelligence/release-governance/dependencies`, {
    headers,
    cache: "no-store",
  });
  if (!res.ok) {
    throw new Error(`Failed to fetch dependency impacts: ${res.statusText}`);
  }
  return res.json();
}

export async function fetchArchitectureFindings(): Promise<ArchitectureFinding[]> {
  const headers = await getAuthHeaders();
  const res = await fetch(`${API_BASE_URL}/api/recovery/intelligence/release-governance/architecture-findings`, {
    headers,
    cache: "no-store",
  });
  if (!res.ok) {
    throw new Error(`Failed to fetch architecture findings: ${res.statusText}`);
  }
  return res.json();
}

export async function fetchApiCompatibilityReport(): Promise<ApiCompatibilityReport> {
  const headers = await getAuthHeaders();
  const res = await fetch(`${API_BASE_URL}/api/recovery/intelligence/release-governance/api-compatibility`, {
    headers,
    cache: "no-store",
  });
  if (!res.ok) {
    throw new Error(`Failed to fetch api compatibility report: ${res.statusText}`);
  }
  return res.json();
}

export async function fetchDatabaseCompatibilityReport(): Promise<DatabaseCompatibilityReport> {
  const headers = await getAuthHeaders();
  const res = await fetch(`${API_BASE_URL}/api/recovery/intelligence/release-governance/database-compatibility`, {
    headers,
    cache: "no-store",
  });
  if (!res.ok) {
    throw new Error(`Failed to fetch database compatibility report: ${res.statusText}`);
  }
  return res.json();
}

export async function fetchConfigurationDrifts(): Promise<ConfigurationDrift[]> {
  const headers = await getAuthHeaders();
  const res = await fetch(`${API_BASE_URL}/api/recovery/intelligence/release-governance/configuration-drift`, {
    headers,
    cache: "no-store",
  });
  if (!res.ok) {
    throw new Error(`Failed to fetch configuration drifts: ${res.statusText}`);
  }
  return res.json();
}

export async function fetchFeatureFlags(): Promise<FeatureFlag[]> {
  const headers = await getAuthHeaders();
  const res = await fetch(`${API_BASE_URL}/api/recovery/intelligence/release-governance/feature-flags`, {
    headers,
    cache: "no-store",
  });
  if (!res.ok) {
    throw new Error(`Failed to fetch feature flags: ${res.statusText}`);
  }
  return res.json();
}

export async function updateFeatureFlag(flagId: string, data: FeatureFlagUpdate): Promise<FeatureFlag> {
  const headers = await getAuthHeaders();
  const res = await fetch(`${API_BASE_URL}/api/recovery/intelligence/release-governance/feature-flags/${flagId}`, {
    method: "POST",
    headers: { ...headers, "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });
  if (!res.ok) {
    throw new Error(`Failed to update feature flag: ${res.statusText}`);
  }
  return res.json();
}

export async function fetchReleaseCandidates(): Promise<ReleaseCandidate[]> {
  const headers = await getAuthHeaders();
  const res = await fetch(`${API_BASE_URL}/api/recovery/intelligence/release-governance/releases`, {
    headers,
    cache: "no-store",
  });
  if (!res.ok) {
    throw new Error(`Failed to fetch release candidates: ${res.statusText}`);
  }
  return res.json();
}

export async function createReleaseCandidate(data: ReleaseCandidateCreate): Promise<ReleaseCandidate> {
  const headers = await getAuthHeaders();
  const res = await fetch(`${API_BASE_URL}/api/recovery/intelligence/release-governance/releases`, {
    method: "POST",
    headers: { ...headers, "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });
  if (!res.ok) {
    throw new Error(`Failed to create release candidate: ${res.statusText}`);
  }
  return res.json();
}

export async function fetchReleaseCandidateDetails(rcId: string): Promise<ReleaseCandidate> {
  const headers = await getAuthHeaders();
  const res = await fetch(`${API_BASE_URL}/api/recovery/intelligence/release-governance/releases/${rcId}`, {
    headers,
    cache: "no-store",
  });
  if (!res.ok) {
    throw new Error(`Failed to fetch release candidate details: ${res.statusText}`);
  }
  return res.json();
}

export async function fetchReleaseReadinessGates(): Promise<ReleaseReadinessSummary> {
  const headers = await getAuthHeaders();
  const res = await fetch(`${API_BASE_URL}/api/recovery/intelligence/release-governance/readiness`, {
    headers,
    cache: "no-store",
  });
  if (!res.ok) {
    throw new Error(`Failed to fetch release readiness gates: ${res.statusText}`);
  }
  return res.json();
}

export async function fetchCanaryEvaluation(): Promise<CanaryEvaluation> {
  const headers = await getAuthHeaders();
  const res = await fetch(`${API_BASE_URL}/api/recovery/intelligence/release-governance/canary`, {
    headers,
    cache: "no-store",
  });
  if (!res.ok) {
    throw new Error(`Failed to fetch canary evaluation: ${res.statusText}`);
  }
  return res.json();
}

export async function fetchRollbackReadiness(): Promise<RollbackReadiness> {
  const headers = await getAuthHeaders();
  const res = await fetch(`${API_BASE_URL}/api/recovery/intelligence/release-governance/rollback-readiness`, {
    headers,
    cache: "no-store",
  });
  if (!res.ok) {
    throw new Error(`Failed to fetch rollback readiness: ${res.statusText}`);
  }
  return res.json();
}

export async function fetchReleaseLineage(): Promise<ReleaseLineageNode[]> {
  const headers = await getAuthHeaders();
  const res = await fetch(`${API_BASE_URL}/api/recovery/intelligence/release-governance/lineage`, {
    headers,
    cache: "no-store",
  });
  if (!res.ok) {
    throw new Error(`Failed to fetch release lineage: ${res.statusText}`);
  }
  return res.json();
}

export async function fetchReleaseIncidents(): Promise<ReleaseIncident[]> {
  const headers = await getAuthHeaders();
  const res = await fetch(`${API_BASE_URL}/api/recovery/intelligence/release-governance/incidents`, {
    headers,
    cache: "no-store",
  });
  if (!res.ok) {
    throw new Error(`Failed to fetch release incidents: ${res.statusText}`);
  }
  return res.json();
}

export async function approveReleaseCandidate(rcId: string, data: ReleaseApprovalRequest): Promise<ReleaseApproval> {
  const headers = await getAuthHeaders();
  const res = await fetch(`${API_BASE_URL}/api/recovery/intelligence/release-governance/approve/${rcId}`, {
    method: "POST",
    headers: { ...headers, "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });
  if (!res.ok) {
    throw new Error(`Failed to approve release candidate: ${res.statusText}`);
  }
  return res.json();
}

export async function fetchReleaseGovernanceReport(): Promise<ReleaseGovernanceReport> {
  const headers = await getAuthHeaders();
  const res = await fetch(`${API_BASE_URL}/api/recovery/intelligence/release-governance/report`, {
    headers,
    cache: "no-store",
  });
  if (!res.ok) {
    throw new Error(`Failed to fetch release governance report: ${res.statusText}`);
  }
  return res.json();
}

// ---------------------------------------------------------------------------
// Phase 10H: Zero-Trust Infrastructure & Security Operations Interfaces & Fetchers
// ---------------------------------------------------------------------------

export type ZeroTrustScoreClassification = "TRUSTED" | "ACCEPTABLE" | "DEGRADED" | "HIGH_RISK" | "CRITICAL";
export type GlobalSecurityState =
  | "EMERGENCY_SECURITY_LOCKDOWN"
  | "CRITICAL_SECURITY_BREACH"
  | "ACTIVE_ATTACK"
  | "TRUST_BOUNDARY_VIOLATION"
  | "HIGH_SECURITY_RISK"
  | "THREAT_DETECTED"
  | "SECURITY_DEGRADED"
  | "INVESTIGATION_REQUIRED"
  | "MONITORING"
  | "SECURE";
export type ServiceIdentityStatus = "AUTHENTICATED" | "VALIDATED" | "DEGRADED" | "STALE_CREDENTIAL" | "REVOKED" | "UNTRUSTED";
export type AuthMatrixStatus = "ALLOWED" | "DENIED" | "CONDITIONAL" | "REVIEW_REQUIRED";
export type ThreatSeverity = "INFORMATIONAL" | "LOW" | "MEDIUM" | "HIGH" | "CRITICAL";
export type ThreatScoreClassification = "INFORMATIONAL" | "LOW" | "MEDIUM" | "HIGH" | "CRITICAL";
export type SecurityIncidentStatus =
  | "DETECTED"
  | "TRIAGED"
  | "ACKNOWLEDGED"
  | "INVESTIGATING"
  | "CONTAINMENT_RECOMMENDED"
  | "ESCALATED"
  | "RESOLVED"
  | "POST_INCIDENT_REVIEW";
export type ZeroTrustGateStatus = "PASS" | "WARN" | "FAIL" | "BLOCKED";
export type ZeroTrustGateId = string;
export type AttackChainStage =
  | "INITIAL_SIGNAL"
  | "AUTHENTICATION_ANOMALY"
  | "API_ANOMALY"
  | "PRIVILEGE_ESCALATION"
  | "SERVICE_BOUNDARY_VIOLATION"
  | "RUNTIME_ANOMALY"
  | "POTENTIAL_DATA_ACCESS"
  | "THREAT_INCIDENT"
  | "HUMAN_ESCALATION";
export type SecurityResponseType =
  | "MONITOR"
  | "INVESTIGATE"
  | "ESCALATE"
  | "ISOLATE_RECOMMENDED"
  | "CREDENTIAL_ROTATION_RECOMMENDED"
  | "ROLLBACK_RECOMMENDED"
  | "HUMAN_REVIEW_REQUIRED";

export interface ServiceIdentity {
  service_name: string;
  identity_status: ServiceIdentityStatus;
  authentication_method: string;
  authorization_status: string;
  certificate_status: string;
  credential_age_days: number;
  last_verified: string;
  trust_score: number;
  privilege_level: string;
  network_zone: string;
  runtime_status: string;
  configuration_integrity: string;
}

export interface ServiceAuthPair {
  source_service: string;
  target_service: string;
  status: AuthMatrixStatus;
  is_financial_path: boolean;
  requires_mutual_tls: boolean;
  permission_boundary: string;
  last_evaluated: string;
  violation_id?: string | null;
}

export interface ServiceAuthMatrix {
  total_pairs: number;
  allowed_pairs: number;
  denied_pairs: number;
  conditional_pairs: number;
  review_required_pairs: number;
  violations_count: number;
  pairs: ServiceAuthPair[];
}

export interface TrustViolation {
  violation_id: string;
  severity: ThreatSeverity;
  violation_type: string;
  source_service: string;
  target_service: string;
  description: string;
  detected_at: string;
  mitigation_recommendation: SecurityResponseType;
}

export interface ThreatIndicator {
  indicator_id: string;
  fingerprint: string;
  indicator_type: string;
  severity: ThreatSeverity;
  confidence_score: number;
  source_component: string;
  first_seen: string;
  last_seen: string;
  affected_services: string[];
  description: string;
}

export interface BehavioralThreatScore {
  overall_threat_score: number;
  classification: ThreatScoreClassification;
  auth_anomaly_score: number;
  frequency_anomaly_score: number;
  privilege_anomaly_score: number;
  service_anomaly_score: number;
  config_anomaly_score: number;
  runtime_anomaly_score: number;
  evaluated_at: string;
}

export interface AttackChainStageItem {
  stage: AttackChainStage;
  timestamp: string;
  component: string;
  summary: string;
  evidence_hash: string;
}

export interface AttackChain {
  chain_id: string;
  title: string;
  severity: ThreatSeverity;
  confidence_score: number;
  first_seen: string;
  last_seen: string;
  stages: AttackChainStageItem[];
  evidence_hashes: string[];
  affected_services: string[];
  blast_radius_score: number;
  recommended_action: SecurityResponseType;
  human_review_required: boolean;
}

export interface RuntimeSecurityPosture {
  process_integrity_status: string;
  container_workload_posture: string;
  dependency_cve_count_critical: number;
  dependency_cve_count_high: number;
  filesystem_integrity_status: string;
  unexpected_open_ports_count: number;
  unauthorized_process_count: number;
  evaluated_at: string;
}

export interface SecretExposureFinding {
  finding_id: string;
  secret_type: string;
  masked_value: string;
  location: string;
  severity: ThreatSeverity;
  fingerprint: string;
  detected_at: string;
}

export interface SecurityIncident {
  incident_id: string;
  title: string;
  severity: ThreatSeverity;
  status: SecurityIncidentStatus;
  affected_services: string[];
  attack_chain_id?: string | null;
  detected_at: string;
  updated_at: string;
  mtta_seconds: number;
  mttr_seconds: number;
  assigned_operator: string;
  recommended_action: SecurityResponseType;
  human_authorization_required: boolean;
  evidence_fingerprint: string;
  timeline: Record<string, any>[];
}

export interface ZeroTrustGate {
  gate_id: ZeroTrustGateId;
  name: string;
  category: string;
  status: ZeroTrustGateStatus;
  observed_value: string;
  threshold: string;
  severity: ThreatSeverity;
  evidence: string;
  remediation: string;
  evaluated_at: string;
}

export interface SecurityEvidenceNode {
  evidence_id: string;
  evidence_hash: string;
  event_type: string;
  source_service: string;
  timestamp: string;
  sanitized_payload: Record<string, any>;
  signature: string;
}

export interface ZeroTrustSummary {
  zero_trust_score: number;
  score_classification: ZeroTrustScoreClassification;
  global_security_state: GlobalSecurityState;
  behavioral_threat_score: number;
  threat_classification: ThreatScoreClassification;
  trusted_services_count: number;
  total_services_count: number;
  active_threat_indicators_count: number;
  trust_violations_count: number;
  active_attack_chains_count: number;
  critical_incidents_count: number;
  security_readiness_score: number;
  secret_exposures_count: number;
  financial_isolation_verified: boolean;
  automatic_financial_response: string;
  evaluated_at: string;
  disclaimer: string;
}

export interface SignedSecurityReport {
  report_id: string;
  generated_at: string;
  zero_trust_score: number;
  score_classification: ZeroTrustScoreClassification;
  global_security_state: GlobalSecurityState;
  summary: ZeroTrustSummary;
  service_identities: ServiceIdentity[];
  authorization_matrix: ServiceAuthMatrix;
  trust_violations: TrustViolation[];
  threat_indicators: ThreatIndicator[];
  attack_chains: AttackChain[];
  runtime_posture: RuntimeSecurityPosture;
  secret_exposures: SecretExposureFinding[];
  incidents: SecurityIncident[];
  readiness_gates: ZeroTrustGate[];
  verification_signature: string;
  financial_isolation_verified: boolean;
}

export async function fetchZeroTrustSummary(): Promise<ZeroTrustSummary> {
  const headers = await getAuthHeaders();
  const res = await fetch(`${API_BASE_URL}/api/recovery/intelligence/zero-trust/summary`, {
    headers,
    cache: "no-store",
  });
  if (!res.ok) {
    throw new Error(`Failed to fetch Zero-Trust summary: ${res.statusText}`);
  }
  return res.json();
}

export async function fetchServiceIdentities(): Promise<ServiceIdentity[]> {
  const headers = await getAuthHeaders();
  const res = await fetch(`${API_BASE_URL}/api/recovery/intelligence/zero-trust/service-identities`, {
    headers,
    cache: "no-store",
  });
  if (!res.ok) {
    throw new Error(`Failed to fetch service identities: ${res.statusText}`);
  }
  return res.json();
}

export async function fetchAuthorizationMatrix(): Promise<ServiceAuthMatrix> {
  const headers = await getAuthHeaders();
  const res = await fetch(`${API_BASE_URL}/api/recovery/intelligence/zero-trust/authorization-matrix`, {
    headers,
    cache: "no-store",
  });
  if (!res.ok) {
    throw new Error(`Failed to fetch authorization matrix: ${res.statusText}`);
  }
  return res.json();
}

export async function fetchTrustViolations(): Promise<TrustViolation[]> {
  const headers = await getAuthHeaders();
  const res = await fetch(`${API_BASE_URL}/api/recovery/intelligence/zero-trust/trust-violations`, {
    headers,
    cache: "no-store",
  });
  if (!res.ok) {
    throw new Error(`Failed to fetch trust violations: ${res.statusText}`);
  }
  return res.json();
}

export async function fetchThreatIndicators(): Promise<ThreatIndicator[]> {
  const headers = await getAuthHeaders();
  const res = await fetch(`${API_BASE_URL}/api/recovery/intelligence/zero-trust/threat-indicators`, {
    headers,
    cache: "no-store",
  });
  if (!res.ok) {
    throw new Error(`Failed to fetch threat indicators: ${res.statusText}`);
  }
  return res.json();
}

export async function fetchBehavioralThreatScore(): Promise<BehavioralThreatScore> {
  const headers = await getAuthHeaders();
  const res = await fetch(`${API_BASE_URL}/api/recovery/intelligence/zero-trust/threat-score`, {
    headers,
    cache: "no-store",
  });
  if (!res.ok) {
    throw new Error(`Failed to fetch behavioral threat score: ${res.statusText}`);
  }
  return res.json();
}

export async function fetchAttackChains(): Promise<AttackChain[]> {
  const headers = await getAuthHeaders();
  const res = await fetch(`${API_BASE_URL}/api/recovery/intelligence/zero-trust/attack-chains`, {
    headers,
    cache: "no-store",
  });
  if (!res.ok) {
    throw new Error(`Failed to fetch attack chains: ${res.statusText}`);
  }
  return res.json();
}

export async function fetchRuntimeSecurityPosture(): Promise<RuntimeSecurityPosture> {
  const headers = await getAuthHeaders();
  const res = await fetch(`${API_BASE_URL}/api/recovery/intelligence/zero-trust/runtime-security`, {
    headers,
    cache: "no-store",
  });
  if (!res.ok) {
    throw new Error(`Failed to fetch runtime security posture: ${res.statusText}`);
  }
  return res.json();
}

export async function fetchSecretExposures(): Promise<SecretExposureFinding[]> {
  const headers = await getAuthHeaders();
  const res = await fetch(`${API_BASE_URL}/api/recovery/intelligence/zero-trust/secret-exposure`, {
    headers,
    cache: "no-store",
  });
  if (!res.ok) {
    throw new Error(`Failed to fetch secret exposure findings: ${res.statusText}`);
  }
  return res.json();
}

export async function fetchZeroTrustSecurityIncidents(): Promise<SecurityIncident[]> {
  const headers = await getAuthHeaders();
  const res = await fetch(`${API_BASE_URL}/api/recovery/intelligence/zero-trust/security-incidents`, {
    headers,
    cache: "no-store",
  });
  if (!res.ok) {
    throw new Error(`Failed to fetch zero-trust security incidents: ${res.statusText}`);
  }
  return res.json();
}

export async function acknowledgeZeroTrustIncident(incidentId: string, notes?: string): Promise<SecurityIncident> {
  const headers = await getAuthHeaders();
  const query = notes ? `?notes=${encodeURIComponent(notes)}` : "";
  const res = await fetch(`${API_BASE_URL}/api/recovery/intelligence/zero-trust/security-incidents/${incidentId}/acknowledge${query}`, {
    method: "POST",
    headers,
  });
  if (!res.ok) {
    throw new Error(`Failed to acknowledge security incident: ${res.statusText}`);
  }
  return res.json();
}

export async function escalateZeroTrustIncident(incidentId: string, notes?: string): Promise<SecurityIncident> {
  const headers = await getAuthHeaders();
  const query = notes ? `?notes=${encodeURIComponent(notes)}` : "";
  const res = await fetch(`${API_BASE_URL}/api/recovery/intelligence/zero-trust/security-incidents/${incidentId}/escalate${query}`, {
    method: "POST",
    headers,
  });
  if (!res.ok) {
    throw new Error(`Failed to escalate security incident: ${res.statusText}`);
  }
  return res.json();
}

export async function resolveZeroTrustIncident(incidentId: string, notes?: string): Promise<SecurityIncident> {
  const headers = await getAuthHeaders();
  const query = notes ? `?notes=${encodeURIComponent(notes)}` : "";
  const res = await fetch(`${API_BASE_URL}/api/recovery/intelligence/zero-trust/security-incidents/${incidentId}/resolve${query}`, {
    method: "POST",
    headers,
  });
  if (!res.ok) {
    throw new Error(`Failed to resolve security incident: ${res.statusText}`);
  }
  return res.json();
}

export async function fetchZeroTrustReadinessGates(): Promise<ZeroTrustGate[]> {
  const headers = await getAuthHeaders();
  const res = await fetch(`${API_BASE_URL}/api/recovery/intelligence/zero-trust/readiness`, {
    headers,
    cache: "no-store",
  });
  if (!res.ok) {
    throw new Error(`Failed to fetch zero-trust readiness gates: ${res.statusText}`);
  }
  return res.json();
}

export async function fetchSecurityEvidenceNodes(): Promise<SecurityEvidenceNode[]> {
  const headers = await getAuthHeaders();
  const res = await fetch(`${API_BASE_URL}/api/recovery/intelligence/zero-trust/evidence`, {
    headers,
    cache: "no-store",
  });
  if (!res.ok) {
    throw new Error(`Failed to fetch security evidence nodes: ${res.statusText}`);
  }
  return res.json();
}

export async function fetchSignedSecurityReport(): Promise<SignedSecurityReport> {
  const headers = await getAuthHeaders();
  const res = await fetch(`${API_BASE_URL}/api/recovery/intelligence/zero-trust/report`, {
    headers,
    cache: "no-store",
  });
  if (!res.ok) {
    throw new Error(`Failed to fetch signed security report: ${res.statusText}`);
  }
  return res.json();
}


// ============================================================================
// Phase 10I: FinOps, Cost Intelligence, Resource Governance, Unit Economics & Financial Efficiency Types & API
// ============================================================================

export interface FinOpsScoreBreakdown {
  cost_allocation_score: number;
  budget_health_score: number;
  forecast_accuracy_score: number;
  resource_efficiency_score: number;
  unit_economics_score: number;
  cost_anomaly_score: number;
  capacity_efficiency_score: number;
  waste_detection_score: number;
  tagging_governance_score: number;
  optimization_readiness_score: number;
  composite_finops_score: number;
  classification: string;
}

export interface ServiceCostMetric {
  service_name: string;
  monthly_cost_inr: number;
  cost_share_pct: number;
  rpm: number;
  cost_per_1k_requests_inr: number;
  cpu_efficiency_pct: number;
  memory_efficiency_pct: number;
  compute_cost_inr: number;
  database_cost_inr: number;
  cache_cost_inr: number;
  network_cost_inr: number;
  ml_cost_inr: number;
  efficiency_status: string;
}

export interface CostCategoryBreakdown {
  category: string;
  hourly_cost_inr: number;
  daily_cost_inr: number;
  monthly_cost_inr: number;
  cost_share_pct: number;
  trend_pct: number;
  source: string;
}

export interface CostAllocation {
  total_monthly_cost_inr: number;
  total_daily_cost_inr: number;
  total_hourly_cost_inr: number;
  services: ServiceCostMetric[];
  categories: CostCategoryBreakdown[];
  evaluated_at: string;
}

export interface BudgetThreshold {
  threshold_pct: number;
  threshold_amount_inr: number;
  breached: boolean;
  breached_at?: string | null;
}

export interface BudgetStatus {
  period: string;
  budget_amount_inr: number;
  actual_amount_inr: number;
  committed_amount_inr: number;
  forecast_amount_inr: number;
  remaining_amount_inr: number;
  burn_rate_pct: number;
  projected_overrun_inr: number;
  state: string;
  thresholds: BudgetThreshold[];
}

export interface BudgetConfigRequest {
  period: string;
  budget_amount_inr: number;
  alert_thresholds?: number[];
  notes?: string;
}

export interface ForecastScenario {
  scenario_name: string;
  growth_rate_pct: number;
  forecast_7d_inr: number;
  forecast_30d_inr: number;
  forecast_90d_inr: number;
  confidence_score: number;
  budget_variance_pct: number;
  assumptions: string[];
}

export interface CostForecast {
  forecast_id: string;
  generated_at: string;
  baseline_monthly_cost_inr: number;
  forecast_state: string;
  scenarios: ForecastScenario[];
}

export interface ForecastGenerateRequest {
  horizon_days?: number;
  traffic_multiplier?: number;
  include_stress_scenario?: boolean;
}

export interface CostAnomaly {
  anomaly_id: string;
  anomaly_type: string;
  severity: string;
  affected_service: string;
  affected_category: string;
  detected_at: string;
  baseline_cost_inr: number;
  observed_cost_inr: number;
  deviation_pct: number;
  confidence_score: number;
  evidence_hash: string;
  recommended_action: string;
}

export interface ResourceUtilization {
  resource_type: string;
  allocated_units: string;
  utilization_pct: number;
  safe_capacity_pct: number;
  headroom_pct: number;
  efficiency_pct: number;
  waste_pct: number;
  state: string;
}

export interface ResourceEfficiency {
  overall_efficiency_pct: number;
  total_waste_cost_inr: number;
  resources: ResourceUtilization[];
  evaluated_at: string;
}

export interface WasteFinding {
  finding_id: string;
  waste_type: string;
  resource_name: string;
  service_name: string;
  estimated_monthly_savings_inr: number;
  risk_tier: string;
  confidence_score: number;
  recommended_change: string;
  rollback_strategy: string;
  human_approval_required: boolean;
}

export interface CostPerTransaction {
  cost_per_successful_txn_inr: number;
  cost_per_attempted_txn_inr: number;
  monthly_transaction_volume: number;
  total_transaction_infrastructure_cost_inr: number;
}

export interface CostPerRecoveryCase {
  cost_per_case_inr: number;
  cost_per_resolved_case_inr: number;
  monthly_case_volume: number;
  total_case_infrastructure_cost_inr: number;
}

export interface MLInferenceCost {
  cost_per_prediction_inr: number;
  cost_per_training_run_inr: number;
  monthly_prediction_volume: number;
  total_ml_infrastructure_cost_inr: number;
}

export interface DatabaseCost {
  cost_per_100k_queries_inr: number;
  storage_cost_per_gb_inr: number;
  iops_cost_inr: number;
  monthly_database_cost_inr: number;
}

export interface CacheCost {
  cost_per_1m_ops_inr: number;
  hit_rate_pct: number;
  monthly_cache_cost_inr: number;
}

export interface WebhookCost {
  cost_per_1k_webhooks_inr: number;
  monthly_webhook_volume: number;
  total_webhook_infrastructure_cost_inr: number;
}

export interface UnitEconomics {
  cost_per_transaction: CostPerTransaction;
  cost_per_recovery_case: CostPerRecoveryCase;
  ml_inference_cost: MLInferenceCost;
  database_cost: DatabaseCost;
  cache_cost: CacheCost;
  webhook_cost: WebhookCost;
  cost_per_1k_requests_inr: number;
  recovery_intelligence_value_efficiency: number;
  evaluated_at: string;
}

export interface OptimizationImpact {
  performance_impact: string;
  security_impact: string;
  resilience_impact: string;
  rollback_complexity: string;
}

export interface OptimizationRecommendation {
  recommendation_id: string;
  optimization_type: string;
  target_resource: string;
  affected_service: string;
  expected_monthly_savings_inr: number;
  implementation_risk: string;
  confidence_score: number;
  impact: OptimizationImpact;
  status: string;
  created_at: string;
  approved_by?: string | null;
  approved_at?: string | null;
  approval_notes?: string | null;
}

export interface OptimizationApprovalRequest {
  decision: "APPROVE" | "REJECT";
  notes: string;
}

export interface FinOpsIncident {
  incident_id: string;
  title: string;
  incident_type: string;
  severity: string;
  status: string;
  affected_service: string;
  detected_at: string;
  updated_at: string;
  cost_impact_inr: number;
  assigned_operator: string;
  recommended_action: string;
  evidence_fingerprint: string;
  timeline: Array<Record<string, any>>;
}

export interface FinOpsReadinessGate {
  gate_id: string;
  name: string;
  category: string;
  status: "PASS" | "WARN" | "FAIL" | "BLOCKED";
  observed_value: string;
  threshold: string;
  severity: string;
  evidence: string;
  remediation: string;
  evaluated_at: string;
}

export interface FinOpsSummary {
  finops_score: number;
  score_classification: string;
  global_finops_state: string;
  total_monthly_cost_inr: number;
  total_daily_cost_inr: number;
  monthly_budget_inr: number;
  monthly_budget_remaining_inr: number;
  monthly_burn_rate_pct: number;
  cost_growth_rate_pct: number;
  potential_monthly_savings_inr: number;
  active_anomalies_count: number;
  active_incidents_count: number;
  passed_gates_count: number;
  total_gates_count: number;
  financial_isolation_verified: boolean;
  automatic_financial_response: string;
  evaluated_at: string;
  disclaimer: string;
}

export interface FinOpsReport {
  report_id: string;
  generated_at: string;
  finops_score: number;
  score_classification: string;
  global_finops_state: string;
  summary: FinOpsSummary;
  cost_allocation: CostAllocation;
  unit_economics: UnitEconomics;
  budget_status: BudgetStatus[];
  forecast: CostForecast;
  resource_efficiency: ResourceEfficiency;
  waste_findings: WasteFinding[];
  anomalies: CostAnomaly[];
  optimizations: OptimizationRecommendation[];
  incidents: FinOpsIncident[];
  readiness_gates: FinOpsReadinessGate[];
  verification_signature: string;
  financial_isolation_verified: boolean;
}

// ----------------------------------------------------------------------------
// Phase 10I API Fetchers & Mutations
// ----------------------------------------------------------------------------

export async function fetchFinOpsSummary(): Promise<FinOpsSummary> {
  const headers = await getAuthHeaders();
  const res = await fetch(`${API_BASE_URL}/api/recovery/intelligence/finops/summary`, {
    headers,
    cache: "no-store",
  });
  if (!res.ok) {
    throw new Error(`Failed to fetch FinOps summary: ${res.statusText}`);
  }
  return res.json();
}

export async function fetchFinOpsScore(): Promise<FinOpsScoreBreakdown> {
  const headers = await getAuthHeaders();
  const res = await fetch(`${API_BASE_URL}/api/recovery/intelligence/finops/score`, {
    headers,
    cache: "no-store",
  });
  if (!res.ok) {
    throw new Error(`Failed to fetch FinOps score breakdown: ${res.statusText}`);
  }
  return res.json();
}

export async function fetchCostAllocation(): Promise<CostAllocation> {
  const headers = await getAuthHeaders();
  const res = await fetch(`${API_BASE_URL}/api/recovery/intelligence/finops/costs`, {
    headers,
    cache: "no-store",
  });
  if (!res.ok) {
    throw new Error(`Failed to fetch cost allocation: ${res.statusText}`);
  }
  return res.json();
}

export async function fetchServiceCosts(): Promise<ServiceCostMetric[]> {
  const headers = await getAuthHeaders();
  const res = await fetch(`${API_BASE_URL}/api/recovery/intelligence/finops/costs/services`, {
    headers,
    cache: "no-store",
  });
  if (!res.ok) {
    throw new Error(`Failed to fetch service costs: ${res.statusText}`);
  }
  return res.json();
}

export async function fetchCategoryCosts(): Promise<CostCategoryBreakdown[]> {
  const headers = await getAuthHeaders();
  const res = await fetch(`${API_BASE_URL}/api/recovery/intelligence/finops/costs/categories`, {
    headers,
    cache: "no-store",
  });
  if (!res.ok) {
    throw new Error(`Failed to fetch category costs: ${res.statusText}`);
  }
  return res.json();
}

export async function fetchUnitEconomics(): Promise<UnitEconomics> {
  const headers = await getAuthHeaders();
  const res = await fetch(`${API_BASE_URL}/api/recovery/intelligence/finops/unit-economics`, {
    headers,
    cache: "no-store",
  });
  if (!res.ok) {
    throw new Error(`Failed to fetch unit economics: ${res.statusText}`);
  }
  return res.json();
}

export async function fetchResourceEfficiency(): Promise<ResourceEfficiency> {
  const headers = await getAuthHeaders();
  const res = await fetch(`${API_BASE_URL}/api/recovery/intelligence/finops/resources/efficiency`, {
    headers,
    cache: "no-store",
  });
  if (!res.ok) {
    throw new Error(`Failed to fetch resource efficiency: ${res.statusText}`);
  }
  return res.json();
}

export async function fetchBudgetStatuses(): Promise<BudgetStatus[]> {
  const headers = await getAuthHeaders();
  const res = await fetch(`${API_BASE_URL}/api/recovery/intelligence/finops/budgets/status`, {
    headers,
    cache: "no-store",
  });
  if (!res.ok) {
    throw new Error(`Failed to fetch budget statuses: ${res.statusText}`);
  }
  return res.json();
}

export async function configureFinOpsBudget(payload: BudgetConfigRequest): Promise<BudgetStatus> {
  const headers = await getAuthHeaders();
  const res = await fetch(`${API_BASE_URL}/api/recovery/intelligence/finops/budgets/configure`, {
    method: "POST",
    headers,
    body: JSON.stringify(payload),
  });
  if (!res.ok) {
    throw new Error(`Failed to configure budget: ${res.statusText}`);
  }
  return res.json();
}

export async function fetchCostForecasts(): Promise<CostForecast> {
  const headers = await getAuthHeaders();
  const res = await fetch(`${API_BASE_URL}/api/recovery/intelligence/finops/forecasts`, {
    headers,
    cache: "no-store",
  });
  if (!res.ok) {
    throw new Error(`Failed to fetch cost forecasts: ${res.statusText}`);
  }
  return res.json();
}

export async function generateCustomCostForecast(payload: ForecastGenerateRequest): Promise<CostForecast> {
  const headers = await getAuthHeaders();
  const res = await fetch(`${API_BASE_URL}/api/recovery/intelligence/finops/forecasts/generate`, {
    method: "POST",
    headers,
    body: JSON.stringify(payload),
  });
  if (!res.ok) {
    throw new Error(`Failed to generate custom forecast: ${res.statusText}`);
  }
  return res.json();
}

export async function fetchCostAnomalies(): Promise<CostAnomaly[]> {
  const headers = await getAuthHeaders();
  const res = await fetch(`${API_BASE_URL}/api/recovery/intelligence/finops/anomalies`, {
    headers,
    cache: "no-store",
  });
  if (!res.ok) {
    throw new Error(`Failed to fetch cost anomalies: ${res.statusText}`);
  }
  return res.json();
}

export async function fetchResourceWasteFindings(): Promise<WasteFinding[]> {
  const headers = await getAuthHeaders();
  const res = await fetch(`${API_BASE_URL}/api/recovery/intelligence/finops/waste`, {
    headers,
    cache: "no-store",
  });
  if (!res.ok) {
    throw new Error(`Failed to fetch waste findings: ${res.statusText}`);
  }
  return res.json();
}

export async function fetchOptimizationRecommendations(): Promise<OptimizationRecommendation[]> {
  const headers = await getAuthHeaders();
  const res = await fetch(`${API_BASE_URL}/api/recovery/intelligence/finops/optimizations`, {
    headers,
    cache: "no-store",
  });
  if (!res.ok) {
    throw new Error(`Failed to fetch optimization recommendations: ${res.statusText}`);
  }
  return res.json();
}

export async function approveOptimizationRecommendation(
  recommendationId: string,
  payload: OptimizationApprovalRequest
): Promise<OptimizationRecommendation> {
  const headers = await getAuthHeaders();
  const res = await fetch(`${API_BASE_URL}/api/recovery/intelligence/finops/optimizations/${recommendationId}/approve`, {
    method: "POST",
    headers,
    body: JSON.stringify(payload),
  });
  if (!res.ok) {
    throw new Error(`Failed to approve optimization recommendation: ${res.statusText}`);
  }
  return res.json();
}

export async function fetchFinOpsIncidents(): Promise<FinOpsIncident[]> {
  const headers = await getAuthHeaders();
  const res = await fetch(`${API_BASE_URL}/api/recovery/intelligence/finops/incidents`, {
    headers,
    cache: "no-store",
  });
  if (!res.ok) {
    throw new Error(`Failed to fetch FinOps incidents: ${res.statusText}`);
  }
  return res.json();
}

export async function acknowledgeFinOpsIncident(incidentId: string, notes?: string): Promise<FinOpsIncident> {
  const headers = await getAuthHeaders();
  const query = notes ? `?notes=${encodeURIComponent(notes)}` : "";
  const res = await fetch(`${API_BASE_URL}/api/recovery/intelligence/finops/incidents/${incidentId}/acknowledge${query}`, {
    method: "POST",
    headers,
  });
  if (!res.ok) {
    throw new Error(`Failed to acknowledge FinOps incident: ${res.statusText}`);
  }
  return res.json();
}

export async function escalateFinOpsIncident(incidentId: string, notes?: string): Promise<FinOpsIncident> {
  const headers = await getAuthHeaders();
  const query = notes ? `?notes=${encodeURIComponent(notes)}` : "";
  const res = await fetch(`${API_BASE_URL}/api/recovery/intelligence/finops/incidents/${incidentId}/escalate${query}`, {
    method: "POST",
    headers,
  });
  if (!res.ok) {
    throw new Error(`Failed to escalate FinOps incident: ${res.statusText}`);
  }
  return res.json();
}

export async function resolveFinOpsIncident(incidentId: string, notes?: string): Promise<FinOpsIncident> {
  const headers = await getAuthHeaders();
  const query = notes ? `?notes=${encodeURIComponent(notes)}` : "";
  const res = await fetch(`${API_BASE_URL}/api/recovery/intelligence/finops/incidents/${incidentId}/resolve${query}`, {
    method: "POST",
    headers,
  });
  if (!res.ok) {
    throw new Error(`Failed to resolve FinOps incident: ${res.statusText}`);
  }
  return res.json();
}

export async function fetchFinOpsReadinessGates(): Promise<FinOpsReadinessGate[]> {
  const headers = await getAuthHeaders();
  const res = await fetch(`${API_BASE_URL}/api/recovery/intelligence/finops/readiness`, {
    headers,
    cache: "no-store",
  });
  if (!res.ok) {
    throw new Error(`Failed to fetch FinOps readiness gates: ${res.statusText}`);
  }
  return res.json();
}

export async function fetchSignedFinOpsReport(): Promise<FinOpsReport> {
  const headers = await getAuthHeaders();
  const res = await fetch(`${API_BASE_URL}/api/recovery/intelligence/finops/report`, {
    headers,
    cache: "no-store",
  });
  if (!res.ok) {
    throw new Error(`Failed to fetch signed FinOps report: ${res.statusText}`);
  }
  return res.json();
}

// =============================================================================
// Phase 10J: AI/ML Governance, Model Risk Management, Explainability,
// Drift Detection & Responsible AI Control Plane
// =============================================================================

export type MLGlobalState =
  | "HEALTHY"
  | "MONITORING"
  | "DRIFT_WARNING"
  | "CALIBRATION_WARNING"
  | "BIAS_WARNING"
  | "MODEL_PERFORMANCE_FAILURE"
  | "SEVERE_MODEL_DRIFT"
  | "HIGH_MODEL_RISK"
  | "MODEL_GOVERNANCE_CRITICAL"
  | "EMERGENCY_MODEL_RISK";

export type ModelLifecycleState =
  | "EXPLORATION"
  | "DEVELOPMENT"
  | "VALIDATING"
  | "STAGING"
  | "CANARY"
  | "PRODUCTION"
  | "SHADOW"
  | "CHALLENGER"
  | "CHAMPION"
  | "DEPRECATED"
  | "RETIRED"
  | "ROLLBACK";

export type ModelRiskLevel =
  | "LOW"
  | "MODERATE"
  | "MEDIUM"
  | "HIGH"
  | "CRITICAL";

export type ModelHealth =
  | "EXCELLENT"
  | "GOOD"
  | "HEALTHY"
  | "WARNING"
  | "DEGRADED"
  | "CRITICAL";

export type DriftStatus =
  | "STABLE"
  | "MINOR_DRIFT"
  | "MODERATE_DRIFT"
  | "SEVERE_DRIFT"
  | "DRIFT_DETECTED"
  | "CRITICAL_DRIFT";

export type MLIncidentSeverity =
  | "SEV_1"
  | "SEV_2"
  | "SEV_3"
  | "SEV_4"
  | "P1_CRITICAL"
  | "P2_HIGH"
  | "P3_MEDIUM"
  | "P4_LOW";

export type MLIncidentStatus =
  | "DETECTED"
  | "ACKNOWLEDGED"
  | "INVESTIGATING"
  | "MITIGATING"
  | "RESOLVED"
  | "CLOSED";

export type PromotionRecommendation =
  | "PROMOTE_RECOMMENDED"
  | "RECOMMEND_PROMOTION"
  | "PROMOTION_REJECTED"
  | "FURTHER_EVALUATION_REQUIRED"
  | "ROLLBACK_REQUIRED";

export type RollbackReadinessStatus =
  | "READY"
  | "CONFIGURING"
  | "TESTING"
  | "DEGRADED"
  | "BLOCKED";

export type MLGateStatus = "PASS" | "WARN" | "FAIL" | "BLOCKED";

export interface ModelRegistryEntry {
  model_id: string;
  model_name: string;
  model_family: string;
  owner_role: string;
  purpose: string;
  lifecycle_state: ModelLifecycleState;
  risk_level: ModelRiskLevel;
  health: ModelHealth;
  current_version: string;
  deployment_status: string;
  created_at: string;
  updated_at: string;
}

export interface ModelVersion {
  model_id: string;
  version: string;
  lifecycle_state: ModelLifecycleState;
  artifact_hash: string;
  training_dataset_hash: string;
  feature_schema_hash: string;
  code_commit_hash: string;
  framework: string;
  hyperparameters_hash: string;
  training_timestamp: string;
  evaluation_timestamp: string;
}

export interface ModelPerformanceMetrics {
  accuracy: number;
  precision: number;
  recall: number;
  f1: number;
  roc_auc: number;
  pr_auc: number;
  log_loss: number;
  brier_score: number;
  latency_p50_ms: number;
  latency_p95_ms: number;
  latency_p99_ms: number;
  throughput_rps: number;
  sample_count: number;
  evaluation_timestamp: string;
}

export interface ModelEvaluation {
  evaluation_id: string;
  model_id: string;
  version: string;
  evaluation_type: string;
  metrics: ModelPerformanceMetrics;
  baseline_version?: string;
  baseline_metrics?: ModelPerformanceMetrics;
  performance_regression_detected: boolean;
  result: string;
  evidence_hash: string;
  timestamp: string;
}

export interface FeatureDriftMetric {
  feature_name: string;
  baseline_distribution_hash: string;
  current_distribution_hash: string;
  psi_score: number;
  ks_statistic: number;
  js_divergence: number;
  threshold_warning: number;
  threshold_critical: number;
  status: DriftStatus;
}

export interface ModelDriftSummary {
  model_id: string;
  version: string;
  data_drift_score: number;
  feature_drift_score: number;
  prediction_drift_score: number;
  concept_drift_score: number;
  features_monitored_count: number;
  features_drifted_count: number;
  overall_status: DriftStatus;
  sample_size: number;
  confidence_note: string;
  feature_metrics: FeatureDriftMetric[];
  timestamp: string;
}

export interface FeatureContribution {
  feature_name: string;
  contribution_weight: number;
  direction: "POSITIVE" | "NEGATIVE";
  relative_percentage: number;
}

export interface ExplainabilityRecord {
  prediction_reference: string;
  model_id: string;
  model_version: string;
  explanation_method: string;
  top_features: FeatureContribution[];
  contribution_summary: string;
  explanation_status: string;
  sanitized: boolean;
  disclaimer: string;
  evidence_hash: string;
  timestamp: string;
}

export interface FairnessMetric {
  protected_group_hash: string;
  metric_name: string;
  reference_metric: number;
  observed_metric: number;
  disparity: number;
  threshold: number;
  status: string;
  sample_size: number;
  limitation_note: string;
}

export interface CalibrationMetric {
  model_id: string;
  version: string;
  brier_score: number;
  expected_calibration_error: number;
  maximum_calibration_error: number;
  calibration_slope: number;
  calibration_intercept: number;
  status: string;
  sample_size: number;
  bins_data: Array<{
    bin: string;
    mean_predicted: number;
    observed_fraction: number;
    samples: number;
  }>;
}

export interface RiskDimensionScore {
  category: string;
  weight: number;
  raw_score: number;
  weighted_score: number;
  risk_level: ModelRiskLevel;
  finding: string;
}

export interface ModelRiskAssessment {
  model_id: string;
  version: string;
  dimensions: RiskDimensionScore[];
  total_score: number;
  risk_level: ModelRiskLevel;
  remediation_recommendations: string[];
  evidence_hash: string;
  assessed_at: string;
}

export interface ModelPromotionEvaluation {
  model_id: string;
  current_version: string;
  candidate_version: string;
  recommendation: PromotionRecommendation;
  performance_passed: boolean;
  drift_passed: boolean;
  fairness_passed: boolean;
  calibration_passed: boolean;
  explainability_passed: boolean;
  security_passed: boolean;
  lineage_verified: boolean;
  rollback_ready: boolean;
  human_approval_required: boolean;
  findings: string[];
  evidence_hash: string;
  evaluated_at: string;
}

export interface ModelRollbackReadiness {
  model_id: string;
  active_version: string;
  previous_version: string;
  artifact_integrity: boolean;
  rollback_tested: boolean;
  rollback_time_seconds: number;
  data_compatibility: boolean;
  readiness_status: RollbackReadinessStatus;
  authorization_path: string;
}

export interface MLIncident {
  incident_id: string;
  severity: MLIncidentSeverity;
  status: MLIncidentStatus;
  model_id: string;
  affected_version: string;
  trigger: string;
  root_cause_category: string;
  impact: string;
  evidence_hash: string;
  detected_at: string;
  acknowledged_at?: string;
  resolved_at?: string;
  mtta_minutes?: number;
  mttr_minutes?: number;
}

export interface MLReadinessGate {
  gate_code: string;
  category: string;
  title: string;
  status: MLGateStatus;
  observed_value: string;
  threshold: string;
  evidence: string;
  remediation?: string;
}

export interface ModelLineageNode {
  node_id: string;
  node_type: string;
  label: string;
  hash_sha256: string;
  metadata: Record<string, unknown>;
  parent_ids: string[];
}

export interface ModelLineageGraph {
  model_id: string;
  version: string;
  root_hash: string;
  nodes: ModelLineageNode[];
  verified: boolean;
}

export interface FinancialPathForensicsNode {
  stage: string;
  entity_id: string;
  status: string;
  latency_ms: number;
  evidence_hash: string;
  timestamp: string;
}

export interface FinancialPathForensics {
  trace_id: string;
  stages: FinancialPathForensicsNode[];
  total_latency_ms: number;
  financial_isolation_verified: boolean;
  delta_recovery_actions: number;
  delta_payments: number;
  delta_case_financial_state: number;
  action_dispatcher_calls: number;
  razorpay_provider_calls: number;
  policy_engine_supremacy_verified: boolean;
}

export interface MLGovernanceSummary {
  governance_score: number;
  health: ModelHealth;
  global_state: MLGlobalState;
  active_models_count: number;
  production_models_count: number;
  high_risk_models_count: number;
  drift_alerts_count: number;
  fairness_alerts_count: number;
  calibration_alerts_count: number;
  open_incidents_count: number;
  readiness_percentage: number;
  passed_gates_count: number;
  total_gates_count: number;
  financial_isolation_verified: boolean;
  zero_pii_verified: boolean;
  last_evaluated_at: string;
}

export interface MLGovernanceReport {
  report_id: string;
  generated_at: string;
  summary: MLGovernanceSummary;
  model_inventory: ModelRegistryEntry[];
  risk_assessments: ModelRiskAssessment[];
  drift_summary: ModelDriftSummary[];
  fairness_summary: FairnessMetric[];
  calibration_summary: CalibrationMetric[];
  readiness_gates: MLReadinessGate[];
  incidents: MLIncident[];
  forensics: FinancialPathForensics;
  evidence_hash: string;
  signature: string;
}

export interface EvaluationRequest {
  evaluation_type?: string;
  sample_size?: number;
  notes?: string;
}

export interface ExplanationRequest {
  prediction_reference: string;
  feature_vector?: Record<string, number>;
}

export interface PromotionEvaluationRequest {
  candidate_version: string;
  justification: string;
}

// -----------------------------------------------------------------------------
// Phase 10J API Fetchers
// -----------------------------------------------------------------------------

export async function fetchMLGovernanceSummary(): Promise<MLGovernanceSummary> {
  const headers = await getAuthHeaders();
  const res = await fetch(`${API_BASE_URL}/api/recovery/intelligence/ml-governance/summary`, {
    headers,
    cache: "no-store",
  });
  if (!res.ok) {
    throw new Error(`Failed to fetch ML governance summary: ${res.statusText}`);
  }
  return res.json();
}

export async function fetchMLModels(): Promise<ModelRegistryEntry[]> {
  const headers = await getAuthHeaders();
  const res = await fetch(`${API_BASE_URL}/api/recovery/intelligence/ml-governance/models`, {
    headers,
    cache: "no-store",
  });
  if (!res.ok) {
    throw new Error(`Failed to fetch ML models: ${res.statusText}`);
  }
  return res.json();
}

export async function fetchMLModelDetail(modelId: string): Promise<ModelRegistryEntry> {
  const headers = await getAuthHeaders();
  const res = await fetch(`${API_BASE_URL}/api/recovery/intelligence/ml-governance/models/${modelId}`, {
    headers,
    cache: "no-store",
  });
  if (!res.ok) {
    throw new Error(`Failed to fetch model detail: ${res.statusText}`);
  }
  return res.json();
}

export async function fetchMLModelVersions(modelId: string): Promise<ModelVersion[]> {
  const headers = await getAuthHeaders();
  const res = await fetch(`${API_BASE_URL}/api/recovery/intelligence/ml-governance/models/${modelId}/versions`, {
    headers,
    cache: "no-store",
  });
  if (!res.ok) {
    throw new Error(`Failed to fetch model versions: ${res.statusText}`);
  }
  return res.json();
}

export async function fetchMLModelLineage(modelId: string, version?: string): Promise<ModelLineageGraph> {
  const headers = await getAuthHeaders();
  const query = version ? `?version=${encodeURIComponent(version)}` : "";
  const res = await fetch(`${API_BASE_URL}/api/recovery/intelligence/ml-governance/models/${modelId}/lineage${query}`, {
    headers,
    cache: "no-store",
  });
  if (!res.ok) {
    throw new Error(`Failed to fetch model lineage: ${res.statusText}`);
  }
  return res.json();
}

export async function fetchMLModelPerformance(modelId: string, version?: string): Promise<ModelPerformanceMetrics> {
  const headers = await getAuthHeaders();
  const query = version ? `?version=${encodeURIComponent(version)}` : "";
  const res = await fetch(`${API_BASE_URL}/api/recovery/intelligence/ml-governance/models/${modelId}/performance${query}`, {
    headers,
    cache: "no-store",
  });
  if (!res.ok) {
    throw new Error(`Failed to fetch model performance: ${res.statusText}`);
  }
  return res.json();
}

export async function fetchMLModelDrift(modelId: string): Promise<ModelDriftSummary> {
  const headers = await getAuthHeaders();
  const res = await fetch(`${API_BASE_URL}/api/recovery/intelligence/ml-governance/models/${modelId}/drift`, {
    headers,
    cache: "no-store",
  });
  if (!res.ok) {
    throw new Error(`Failed to fetch model drift: ${res.statusText}`);
  }
  return res.json();
}

export async function fetchMLPredictionDrift(modelId: string): Promise<Record<string, unknown>> {
  const headers = await getAuthHeaders();
  const res = await fetch(`${API_BASE_URL}/api/recovery/intelligence/ml-governance/models/${modelId}/prediction-drift`, {
    headers,
    cache: "no-store",
  });
  if (!res.ok) {
    throw new Error(`Failed to fetch prediction drift: ${res.statusText}`);
  }
  return res.json();
}

export async function fetchMLConceptDrift(modelId: string): Promise<Record<string, unknown>> {
  const headers = await getAuthHeaders();
  const res = await fetch(`${API_BASE_URL}/api/recovery/intelligence/ml-governance/models/${modelId}/concept-drift`, {
    headers,
    cache: "no-store",
  });
  if (!res.ok) {
    throw new Error(`Failed to fetch concept drift: ${res.statusText}`);
  }
  return res.json();
}

export async function fetchMLExplainability(modelId: string, predictionRef?: string): Promise<ExplainabilityRecord> {
  const headers = await getAuthHeaders();
  const query = predictionRef ? `?prediction_ref=${encodeURIComponent(predictionRef)}` : "";
  const res = await fetch(`${API_BASE_URL}/api/recovery/intelligence/ml-governance/models/${modelId}/explainability${query}`, {
    headers,
    cache: "no-store",
  });
  if (!res.ok) {
    throw new Error(`Failed to fetch model explainability: ${res.statusText}`);
  }
  return res.json();
}

export async function fetchMLFairness(modelId: string): Promise<FairnessMetric[]> {
  const headers = await getAuthHeaders();
  const res = await fetch(`${API_BASE_URL}/api/recovery/intelligence/ml-governance/models/${modelId}/fairness`, {
    headers,
    cache: "no-store",
  });
  if (!res.ok) {
    throw new Error(`Failed to fetch model fairness: ${res.statusText}`);
  }
  return res.json();
}

export async function fetchMLCalibration(modelId: string): Promise<CalibrationMetric> {
  const headers = await getAuthHeaders();
  const res = await fetch(`${API_BASE_URL}/api/recovery/intelligence/ml-governance/models/${modelId}/calibration`, {
    headers,
    cache: "no-store",
  });
  if (!res.ok) {
    throw new Error(`Failed to fetch model calibration: ${res.statusText}`);
  }
  return res.json();
}

export async function fetchMLModelRisk(modelId: string): Promise<ModelRiskAssessment> {
  const headers = await getAuthHeaders();
  const res = await fetch(`${API_BASE_URL}/api/recovery/intelligence/ml-governance/models/${modelId}/risk`, {
    headers,
    cache: "no-store",
  });
  if (!res.ok) {
    throw new Error(`Failed to fetch model risk: ${res.statusText}`);
  }
  return res.json();
}

export async function fetchMLReadinessGates(): Promise<MLReadinessGate[]> {
  const headers = await getAuthHeaders();
  const res = await fetch(`${API_BASE_URL}/api/recovery/intelligence/ml-governance/readiness-gates`, {
    headers,
    cache: "no-store",
  });
  if (!res.ok) {
    throw new Error(`Failed to fetch ML readiness gates: ${res.statusText}`);
  }
  return res.json();
}

export async function fetchMLRollbackReadiness(modelId: string): Promise<ModelRollbackReadiness> {
  const headers = await getAuthHeaders();
  const res = await fetch(`${API_BASE_URL}/api/recovery/intelligence/ml-governance/models/${modelId}/rollback`, {
    headers,
    cache: "no-store",
  });
  if (!res.ok) {
    throw new Error(`Failed to fetch rollback readiness: ${res.statusText}`);
  }
  return res.json();
}

export async function runMLEvaluation(
  modelId: string,
  payload: EvaluationRequest,
  version?: string
): Promise<ModelEvaluation> {
  const headers = await getAuthHeaders();
  const query = version ? `?version=${encodeURIComponent(version)}` : "";
  const res = await fetch(`${API_BASE_URL}/api/recovery/intelligence/ml-governance/models/${modelId}/evaluate${query}`, {
    method: "POST",
    headers: { ...headers, "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!res.ok) {
    throw new Error(`Failed to run ML evaluation: ${res.statusText}`);
  }
  return res.json();
}

export async function generateMLExplanation(
  modelId: string,
  payload: ExplanationRequest
): Promise<ExplainabilityRecord> {
  const headers = await getAuthHeaders();
  const res = await fetch(`${API_BASE_URL}/api/recovery/intelligence/ml-governance/models/${modelId}/explain`, {
    method: "POST",
    headers: { ...headers, "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!res.ok) {
    throw new Error(`Failed to generate explanation: ${res.statusText}`);
  }
  return res.json();
}

export async function evaluateMLPromotion(
  modelId: string,
  payload: PromotionEvaluationRequest
): Promise<ModelPromotionEvaluation> {
  const headers = await getAuthHeaders();
  const res = await fetch(
    `${API_BASE_URL}/api/recovery/intelligence/ml-governance/models/${modelId}/promotion-evaluation`,
    {
      method: "POST",
      headers: { ...headers, "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    }
  );
  if (!res.ok) {
    throw new Error(`Failed to evaluate promotion: ${res.statusText}`);
  }
  return res.json();
}

export async function fetchMLIncidents(): Promise<MLIncident[]> {
  const headers = await getAuthHeaders();
  const res = await fetch(`${API_BASE_URL}/api/recovery/intelligence/ml-governance/incidents`, {
    headers,
    cache: "no-store",
  });
  if (!res.ok) {
    throw new Error(`Failed to fetch ML incidents: ${res.statusText}`);
  }
  return res.json();
}

export async function fetchMLIncidentDetail(incidentId: string): Promise<MLIncident> {
  const headers = await getAuthHeaders();
  const res = await fetch(`${API_BASE_URL}/api/recovery/intelligence/ml-governance/incidents/${incidentId}`, {
    headers,
    cache: "no-store",
  });
  if (!res.ok) {
    throw new Error(`Failed to fetch incident detail: ${res.statusText}`);
  }
  return res.json();
}

export async function acknowledgeMLIncident(incidentId: string, notes?: string): Promise<MLIncident> {
  const headers = await getAuthHeaders();
  const query = notes ? `?notes=${encodeURIComponent(notes)}` : "";
  const res = await fetch(
    `${API_BASE_URL}/api/recovery/intelligence/ml-governance/incidents/${incidentId}/acknowledge${query}`,
    {
      method: "POST",
      headers,
    }
  );
  if (!res.ok) {
    throw new Error(`Failed to acknowledge ML incident: ${res.statusText}`);
  }
  return res.json();
}

export async function resolveMLIncident(incidentId: string, notes?: string): Promise<MLIncident> {
  const headers = await getAuthHeaders();
  const query = notes ? `?notes=${encodeURIComponent(notes)}` : "";
  const res = await fetch(
    `${API_BASE_URL}/api/recovery/intelligence/ml-governance/incidents/${incidentId}/resolve${query}`,
    {
      method: "POST",
      headers,
    }
  );
  if (!res.ok) {
    throw new Error(`Failed to resolve ML incident: ${res.statusText}`);
  }
  return res.json();
}

export async function fetchMLFinancialPathForensics(traceId?: string): Promise<FinancialPathForensics> {
  const headers = await getAuthHeaders();
  const query = traceId ? `?trace_id=${encodeURIComponent(traceId)}` : "";
  const res = await fetch(`${API_BASE_URL}/api/recovery/intelligence/ml-governance/forensics${query}`, {
    headers,
    cache: "no-store",
  });
  if (!res.ok) {
    throw new Error(`Failed to fetch financial path forensics: ${res.statusText}`);
  }
  return res.json();
}

export async function fetchSignedMLGovernanceReport(): Promise<MLGovernanceReport> {
  const headers = await getAuthHeaders();
  const res = await fetch(`${API_BASE_URL}/api/recovery/intelligence/ml-governance/report`, {
    headers,
    cache: "no-store",
  });
  if (!res.ok) {
    throw new Error(`Failed to fetch signed ML governance report: ${res.statusText}`);
  }
  return res.json();
}

















