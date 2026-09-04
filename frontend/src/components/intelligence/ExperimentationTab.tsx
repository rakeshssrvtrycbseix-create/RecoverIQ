"use client";

import React, { useCallback, useEffect, useState } from "react";
import {
  ExperimentAnalysisResponse,
  ExperimentRequest,
  ExperimentResponse,
  PaginatedExperimentsResponse,
  completeExperiment,
  createExperiment,
  fetchExperimentAnalysis,
  fetchExperiments,
  formatINR,
  pauseExperiment,
  startExperiment
} from "../../lib/api";
import { formatDelta, formatPct, getBalanceBadge, getDecisionBadge, getEvidenceBadge, getExperimentStatusBadge } from "./intelligenceBadges";

interface ExperimentationTabProps {
  userRole?: string;
}

export default function ExperimentationTab({ userRole = "ADMIN" }: ExperimentationTabProps) {
  const [error, setError] = useState<string | null>(null);

  const [expSuccessMsg, setExpSuccessMsg] = useState<string | null>(null);
    const [expData, setExpData] = useState<PaginatedExperimentsResponse | null>(null);
  
    const [selectedExp, setSelectedExp] = useState<ExperimentResponse | null>(null);
    const [analysisData, setAnalysisData] = useState<ExperimentAnalysisResponse | null>(null);
    const [analysisLoading, setAnalysisLoading] = useState(false);
    const [createExpModalOpen, setCreateExpModalOpen] = useState(false);
    const [createExpName, setCreateExpName] = useState("");
    const [createExpDesc, setCreateExpDesc] = useState("");
    const [createExpTreatment, setCreateExpTreatment] = useState("SEND_PAYMENT_LINK");
    const [createExpControl, setCreateExpControl] = useState("RETRY_PAYMENT");
    const [createExpAlloc, setCreateExpAlloc] = useState<number>(50);
    const [createExpRiskTier, setCreateExpRiskTier] = useState<string>("");
    const [createExpFailureReason, setCreateExpFailureReason] = useState<string>("");
    const [createExpNotes, setCreateExpNotes] = useState<string>("");
    const [expActionLoading, setExpActionLoading] = useState(false);
    const [expStatusFilter, setExpStatusFilter] = useState<string>("ALL");
  

    const loadAnalysis = async (experimentId: string) => {
      setAnalysisLoading(true);
      try {
        const res = await fetchExperimentAnalysis(experimentId);
        setAnalysisData(res);
      } catch (err) {
        console.error("Failed to load experiment analysis:", err);
      } finally {
        setAnalysisLoading(false);
      }
    };
  
    const handleSelectExperiment = (exp: ExperimentResponse) => {
      setSelectedExp(exp);
      loadAnalysis(exp.experiment_id);
    };
  
    const handleCreateExperiment = async (e: React.FormEvent) => {
      e.preventDefault();
      if (!createExpName.trim()) return;
      setExpActionLoading(true);
      setError(null);
      try {
        const payload: ExperimentRequest = {
          name: createExpName.trim(),
          description: createExpDesc.trim() || null,
          treatment_strategy: createExpTreatment,
          control_strategy: createExpControl,
          allocation_percentage: createExpAlloc,
          population_definition: {
            risk_tier: createExpRiskTier || null,
            failure_reason: createExpFailureReason || null,
          },
          notes: createExpNotes.trim() || null,
        };
        const created = await createExperiment(payload);
        setCreateExpModalOpen(false);
        setExpSuccessMsg(`Experiment "${created.name}" created in DRAFT status. (Zero financial mutations)`);
        setCreateExpName("");
        setCreateExpDesc("");
        setCreateExpNotes("");
        await loadExpData();
        setSelectedExp(created);
        await loadAnalysis(created.experiment_id);
      } catch (err) {
        setError(err instanceof Error ? err.message : "Failed to create experiment");
      } finally {
        setExpActionLoading(false);
      }
    };
  
    const handleStartExperiment = async (expId: string) => {
      setExpActionLoading(true);
      setError(null);
      try {
        const updated = await startExperiment(expId, "Started by operator");
        setSelectedExp(updated);
        await loadExpData();
        await loadAnalysis(expId);
      } catch (err) {
        setError(err instanceof Error ? err.message : "Failed to start experiment");
      } finally {
        setExpActionLoading(false);
      }
    };
  
    const handlePauseExperiment = async (expId: string) => {
      setExpActionLoading(true);
      setError(null);
      try {
        const updated = await pauseExperiment(expId, "Paused by operator");
        setSelectedExp(updated);
        await loadExpData();
        await loadAnalysis(expId);
      } catch (err) {
        setError(err instanceof Error ? err.message : "Failed to pause experiment");
      } finally {
        setExpActionLoading(false);
      }
    };
  
    const handleCompleteExperiment = async (expId: string) => {
      setExpActionLoading(true);
      setError(null);
      try {
        const updated = await completeExperiment(expId, "Completed by operator");
        setSelectedExp(updated);
        await loadExpData();
        await loadAnalysis(expId);
      } catch (err) {
        setError(err instanceof Error ? err.message : "Failed to complete experiment");
      } finally {
        setExpActionLoading(false);
      }
    };

  const loadExpData = useCallback(async () => {
    try {
      const res = await fetchExperiments();
      setExpData(res);
      if (res && res.items && res.items.length > 0 && !selectedExp) {
        setSelectedExp(res.items[0]);
        loadAnalysis(res.items[0].experiment_id);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load Experiments");
    }
  }, [selectedExp]);

    useEffect(() => {
    let ignore = false;
    async function execute() {
      if (!ignore) {
        await loadExpData();
      }
    }
    void execute();
    return () => {
      ignore = true;
    };
  }, [loadExpData]);

  return (
    <>
      {error && (
        <div className="rounded-xl border border-rose-800/40 bg-rose-950/40 p-4 text-xs text-rose-300">
          {error}
        </div>
      )}

      {expSuccessMsg && (
        <div className="rounded-xl border border-emerald-800/60 bg-emerald-950/40 p-4 text-xs text-emerald-300 flex items-center justify-between shadow-lg">
          <span>{expSuccessMsg}</span>
          <button onClick={() => setExpSuccessMsg(null)} className="text-emerald-400 hover:text-white font-bold ml-4">✕</button>
        </div>
      )}
              {/* =========================================================================
                 TAB 1: CAUSAL EXPERIMENTATION & STATISTICAL DECISION INTELLIGENCE (Phase 9H)
                 ========================================================================= */}
              <div className="space-y-8">
                {/* Mandatory Observational & Governance Disclaimer Banner */}
                <div className="rounded-2xl border border-purple-800/60 bg-purple-950/20 p-4 flex items-start gap-3">
                  <span className="rounded bg-purple-900/80 px-2 py-0.5 text-[10px] font-bold uppercase tracking-wider text-purple-200 border border-purple-700/60 shrink-0">
                    PHASE 9H EXPERIMENTATION
                  </span>
                  <div className="text-xs text-purple-200/90 leading-relaxed space-y-1">
                    <p className="font-semibold">
                      CAUSAL EXPERIMENTATION & STATISTICAL DECISION INTELLIGENCE
                    </p>
                    <p className="text-[11px] text-purple-300/80">
                      Evaluates whether observed recovery improvements are attributable to candidate strategies rather than random variation or population imbalance. Uses deterministic SHA-256 cohort assignment, Wilson/Newcombe 95% confidence intervals, two-proportion pooled z-tests, and multidimensional covariate balance diagnostics. The authoritative PolicyEngine remains intact; experiments execute zero financial mutations.
                    </p>
                  </div>
                </div>
    
    
                {/* Quick Metrics Bar & Action Header */}
                <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
                  <div className="flex flex-wrap items-center gap-3">
                    <div className="rounded-xl border border-slate-800 bg-slate-900/80 px-4 py-2 text-xs font-mono">
                      <span className="text-[10px] text-slate-500 uppercase block font-bold">Total Experiments</span>
                      <strong className="text-white text-sm">{expData?.total || 0}</strong>
                    </div>
                    <div className="rounded-xl border border-slate-800 bg-slate-900/80 px-4 py-2 text-xs font-mono">
                      <span className="text-[10px] text-slate-500 uppercase block font-bold">Active Running</span>
                      <strong className="text-emerald-400 text-sm">{expData?.active_count || 0}</strong>
                    </div>
                    <div className="rounded-xl border border-slate-800 bg-slate-900/80 px-4 py-2 text-xs font-mono">
                      <span className="text-[10px] text-slate-500 uppercase block font-bold">Assignment Engine</span>
                      <strong className="text-purple-300 text-sm">SHA256 DETERMINISTIC</strong>
                    </div>
                  </div>
    
                  <div className="flex items-center gap-3">
                    <select
                      value={expStatusFilter}
                      onChange={(e) => {
                        setExpStatusFilter(e.target.value);
                        fetchExperiments(e.target.value).then((res) => setExpData(res));
                      }}
                      className="rounded-xl border border-slate-800 bg-slate-900 px-3 py-2 text-xs font-semibold text-slate-300 focus:border-purple-500 focus:outline-none"
                    >
                      <option value="ALL">All Statuses</option>
                      <option value="RUNNING">RUNNING</option>
                      <option value="DRAFT">DRAFT</option>
                      <option value="PAUSED">PAUSED</option>
                      <option value="COMPLETED">COMPLETED</option>
                    </select>
    
                    {(userRole === "operator" || userRole === "admin") && (
                      <button
                        onClick={() => setCreateExpModalOpen(true)}
                        className="flex items-center gap-2 rounded-xl bg-purple-600 px-4 py-2 text-xs font-bold uppercase tracking-wider text-white hover:bg-purple-500 shadow-lg shadow-purple-600/30 transition"
                      >
                        <span>+ New Experiment</span>
                      </button>
                    )}
                  </div>
                </div>
    
                {/* Experiment Selection Carousel / Cards */}
                {expData && expData.items.length > 0 && (
                  <div className="space-y-3">
                    <span className="text-xs font-bold uppercase tracking-wider text-slate-400">
                      Select Experiment to Evaluate
                    </span>
                    <div className="flex gap-3 overflow-x-auto pb-2">
                      {expData.items.map((exp) => {
                        const isSelected = selectedExp?.experiment_id === exp.experiment_id;
                        return (
                          <button
                            key={exp.experiment_id}
                            onClick={() => handleSelectExperiment(exp)}
                            className={`shrink-0 rounded-2xl border p-4 text-left transition w-72 ${
                              isSelected
                                ? "border-purple-500 bg-purple-950/40 shadow-lg shadow-purple-950/40 ring-1 ring-purple-500"
                                : "border-slate-800 bg-slate-900/60 hover:bg-slate-900 text-slate-400"
                            }`}
                          >
                            <div className="flex items-center justify-between gap-2 mb-2">
                              <span className="text-xs font-bold text-slate-200 truncate">{exp.name}</span>
                              <span
                                className={`rounded-full border px-2 py-0.5 text-[9px] font-mono font-bold uppercase ${getExperimentStatusBadge(
                                  exp.status
                                )}`}
                              >
                                {exp.status}
                              </span>
                            </div>
                            <div className="text-[10px] font-mono text-slate-400 space-y-0.5">
                              <div>Treatment: <span className="text-purple-300">{exp.treatment_strategy}</span></div>
                              <div>Control: <span className="text-slate-300">{exp.control_strategy}</span></div>
                              <div>Split: <span className="text-white">{exp.allocation_percentage}% / {100 - exp.allocation_percentage}%</span></div>
                            </div>
                          </button>
                        );
                      })}
                    </div>
                  </div>
                )}
    
                {/* Analysis Loading / Empty State */}
                {analysisLoading ? (
                  <div className="flex h-64 items-center justify-center space-x-2">
                    <div className="h-4 w-4 animate-spin rounded-full border-2 border-purple-500 border-t-transparent" />
                    <span className="text-xs text-slate-400">
                      Computing causal uplift, statistical significance & balance diagnostics...
                    </span>
                  </div>
                ) : !selectedExp || !analysisData ? (
                  <div className="rounded-2xl border border-slate-800 bg-slate-900/40 p-12 text-center text-slate-400 text-xs">
                    No experiment selected or available. Click &quot;+ New Experiment&quot; to create a causal evaluation.
                  </div>
                ) : (
                  <div className="space-y-8">
                    {/* Active Experiment Header & Lifecycle Actions */}
                    <div className="rounded-3xl border border-slate-800 bg-slate-900/70 p-6 space-y-6">
                      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between border-b border-slate-800/80 pb-6">
                        <div>
                          <div className="flex items-center gap-3">
                            <h2 className="text-lg font-black tracking-tight text-white">{analysisData.name}</h2>
                            <span
                              className={`rounded-full border px-3 py-0.5 text-xs font-mono font-bold uppercase ${getExperimentStatusBadge(
                                analysisData.status
                              )}`}
                            >
                              {analysisData.status}
                            </span>
                            <span
                              className={`rounded-full border px-3 py-0.5 text-xs font-mono font-bold uppercase ${getEvidenceBadge(
                                analysisData.decision.evidence_level
                              )}`}
                            >
                              {analysisData.decision.evidence_level}
                            </span>
                          </div>
                          <p className="text-xs text-slate-400 font-mono mt-1">
                            ID: {analysisData.experiment_id} • Runtime: {analysisData.runtime_hours ?? 0}h • Evaluated: {new Date(analysisData.last_evaluated).toLocaleTimeString()}
                          </p>
                        </div>
    
                        {/* Operator Lifecycle Controls */}
                        {(userRole === "operator" || userRole === "admin") && (
                          <div className="flex items-center gap-2">
                            {analysisData.status === "DRAFT" && (
                              <button
                                onClick={() => handleStartExperiment(analysisData.experiment_id)}
                                disabled={expActionLoading}
                                className="rounded-xl bg-emerald-600 px-4 py-2 text-xs font-bold uppercase tracking-wider text-white hover:bg-emerald-500 transition disabled:opacity-50"
                              >
                                ▶ Start Experiment
                              </button>
                            )}
                            {analysisData.status === "RUNNING" && (
                              <>
                                <button
                                  onClick={() => handlePauseExperiment(analysisData.experiment_id)}
                                  disabled={expActionLoading}
                                  className="rounded-xl bg-amber-600 px-4 py-2 text-xs font-bold uppercase tracking-wider text-white hover:bg-amber-500 transition disabled:opacity-50"
                                >
                                  ⏸ Pause
                                </button>
                                <button
                                  onClick={() => handleCompleteExperiment(analysisData.experiment_id)}
                                  disabled={expActionLoading}
                                  className="rounded-xl bg-purple-600 px-4 py-2 text-xs font-bold uppercase tracking-wider text-white hover:bg-purple-500 transition disabled:opacity-50"
                                >
                                  ✓ Complete
                                </button>
                              </>
                            )}
                            {analysisData.status === "PAUSED" && (
                              <>
                                <button
                                  onClick={() => handleStartExperiment(analysisData.experiment_id)}
                                  disabled={expActionLoading}
                                  className="rounded-xl bg-emerald-600 px-4 py-2 text-xs font-bold uppercase tracking-wider text-white hover:bg-emerald-500 transition disabled:opacity-50"
                                >
                                  ▶ Resume
                                </button>
                                <button
                                  onClick={() => handleCompleteExperiment(analysisData.experiment_id)}
                                  disabled={expActionLoading}
                                  className="rounded-xl bg-purple-600 px-4 py-2 text-xs font-bold uppercase tracking-wider text-white hover:bg-purple-500 transition disabled:opacity-50"
                                >
                                  ✓ Complete
                                </button>
                              </>
                            )}
                          </div>
                        )}
                      </div>
    
                      {/* Decision & Guardrails Alert Banner */}
                      <div
                        className={`rounded-2xl border p-5 flex items-start gap-4 ${
                          analysisData.decision.decision === "PROMOTE_TO_REVIEW"
                            ? "border-emerald-700/60 bg-emerald-950/30 text-emerald-200"
                            : analysisData.decision.decision === "STOP_RECOMMENDED"
                            ? "border-rose-700/60 bg-rose-950/40 text-rose-200 animate-pulse"
                            : analysisData.decision.decision === "CONTINUE"
                            ? "border-indigo-700/60 bg-indigo-950/30 text-indigo-200"
                            : "border-amber-700/60 bg-amber-950/30 text-amber-200"
                        }`}
                      >
                        <span
                          className={`rounded-full border px-3 py-1 text-xs font-mono font-bold uppercase tracking-wider shrink-0 ${getDecisionBadge(
                            analysisData.decision.decision
                          )}`}
                        >
                          {analysisData.decision.decision.replace("_", " ")}
                        </span>
                        <div className="space-y-1 text-xs">
                          <p className="font-bold">
                            {analysisData.decision.decision === "PROMOTE_TO_REVIEW"
                              ? "Statistically Significant Empirical Evidence — Eligible for Governance Review"
                              : analysisData.decision.decision === "STOP_RECOMMENDED"
                              ? "Automated Safety Guardrails Triggered — Experiment Cessation Recommended"
                              : analysisData.decision.decision === "CONTINUE"
                              ? "Experiment Active — Continuing Observation Collection"
                              : "Insufficient Sample Size (N < 100 observations)"}
                          </p>
                          <ul className="text-[11px] opacity-90 list-disc list-inside space-y-0.5">
                            {analysisData.decision.diagnostics.map((diag, idx) => (
                              <li key={idx}>{diag}</li>
                            ))}
                          </ul>
                        </div>
                      </div>
    
                      {/* Causal Effect & Statistical Hypothesis Testing Grid */}
                      <div className="grid grid-cols-1 gap-6 lg:grid-cols-4 font-mono text-xs">
                        {/* ATE Card */}
                        <div className="rounded-2xl border border-slate-800 bg-slate-950/80 p-4 space-y-2">
                          <span className="text-[10px] text-slate-500 uppercase block font-bold">
                            Absolute Treatment Effect (ATE)
                          </span>
                          <div className="text-2xl font-black text-white">
                            {formatDelta(analysisData.causal_effect.absolute_treatment_effect)}
                          </div>
                          <span className="text-[10px] text-slate-400 block">
                            Rel Uplift: <strong className="text-emerald-400">{analysisData.causal_effect.relative_uplift_pct ? `${analysisData.causal_effect.relative_uplift_pct > 0 ? "+" : ""}${analysisData.causal_effect.relative_uplift_pct}%` : "—"}</strong>
                          </span>
                        </div>
    
                        {/* 95% Confidence Interval */}
                        <div className="rounded-2xl border border-slate-800 bg-slate-950/80 p-4 space-y-2">
                          <span className="text-[10px] text-slate-500 uppercase block font-bold">
                            95% Confidence Interval (Wilson/Newcombe)
                          </span>
                          <div className="text-lg font-black text-purple-300">
                            {analysisData.statistical_test.confidence_interval_low !== null && analysisData.statistical_test.confidence_interval_high !== null
                              ? `[${(analysisData.statistical_test.confidence_interval_low * 100).toFixed(1)}%, ${(analysisData.statistical_test.confidence_interval_high * 100).toFixed(1)}%]`
                              : "—"}
                          </div>
                          <span className="text-[10px] text-slate-400 block">
                            Zero included: <strong className="text-slate-300">{analysisData.statistical_test.confidence_interval_low !== null && analysisData.statistical_test.confidence_interval_low <= 0 && (analysisData.statistical_test.confidence_interval_high ?? 0) >= 0 ? "YES" : "NO"}</strong>
                          </span>
                        </div>
    
                        {/* Z-Test & P-Value */}
                        <div className="rounded-2xl border border-slate-800 bg-slate-950/80 p-4 space-y-2">
                          <span className="text-[10px] text-slate-500 uppercase block font-bold">
                            Two-Proportion Pooled Z-Test
                          </span>
                          <div className="text-lg font-black text-slate-200">
                            z = {analysisData.statistical_test.test_statistic !== null ? analysisData.statistical_test.test_statistic.toFixed(3) : "—"}
                          </div>
                          <span className="text-[10px] text-slate-400 block">
                            p-value: <strong className="text-emerald-400">{analysisData.statistical_test.p_value !== null ? (analysisData.statistical_test.p_value < 0.001 ? "< 0.001" : analysisData.statistical_test.p_value.toFixed(4)) : "—"}</strong> (α = 0.05)
                          </span>
                        </div>
    
                        {/* Incremental Financial Yield */}
                        <div className="rounded-2xl border border-slate-800 bg-slate-950/80 p-4 space-y-2">
                          <span className="text-[10px] text-slate-500 uppercase block font-bold">
                            Incremental ERV Impact
                          </span>
                          <div className="text-lg font-black text-emerald-400">
                            {analysisData.causal_effect.incremental_erv_paise !== null ? formatINR(analysisData.causal_effect.incremental_erv_paise) : "—"}
                          </div>
                          <span className="text-[10px] text-slate-400 block">
                            Est. Recovered Cases: <strong className="text-white">+{analysisData.causal_effect.incremental_recovered_cases_estimate ?? 0}</strong>
                          </span>
                        </div>
                      </div>
    
                      {/* Side-by-side Cohort Comparison (Control vs Treatment) */}
                      <div className="space-y-4">
                        <h3 className="text-xs font-bold uppercase tracking-wider text-slate-300">
                          Cohort Comparison Telemetry
                        </h3>
                        <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
                          {/* Control Cohort Card */}
                          <div className="rounded-2xl border border-slate-800 bg-slate-950/90 p-5 space-y-4">
                            <div className="flex items-center justify-between border-b border-slate-800 pb-3">
                              <div>
                                <span className="text-xs font-bold text-slate-200 uppercase">Control Cohort</span>
                                <span className="text-[10px] text-slate-400 block font-mono">Strategy: {analysisData.control_strategy}</span>
                              </div>
                              <span className="rounded-full bg-slate-800 px-3 py-0.5 text-xs font-mono text-slate-300">
                                {analysisData.control_cohort.sample_size} cases
                              </span>
                            </div>
    
                            <div className="grid grid-cols-2 gap-4 text-xs font-mono">
                              <div>
                                <span className="text-[10px] text-slate-500 block">Recovery Rate</span>
                                <span className="text-xl font-bold text-slate-200">{formatPct(analysisData.control_cohort.recovery_rate)}</span>
                                <span className="text-[10px] text-slate-500 block">
                                  {analysisData.control_cohort.recovered_count}/{analysisData.control_cohort.sample_size} recovered
                                </span>
                              </div>
                              <div>
                                <span className="text-[10px] text-slate-500 block">Financial Yield</span>
                                <span className="text-xl font-bold text-slate-200">{formatPct(analysisData.control_cohort.financial_yield)}</span>
                                <span className="text-[10px] text-slate-500 block">
                                  {formatINR(analysisData.control_cohort.amount_recovered_paise)}
                                </span>
                              </div>
                              <div>
                                <span className="text-[10px] text-slate-500 block">Expected Recovery Value</span>
                                <span className="text-sm font-bold text-purple-300">{formatINR(analysisData.control_cohort.expected_recovery_value_paise)}</span>
                              </div>
                              <div>
                                <span className="text-[10px] text-slate-500 block">MTTR / Avg Attempts</span>
                                <span className="text-xs font-bold text-slate-300">
                                  {analysisData.control_cohort.mttr_hours ? `${analysisData.control_cohort.mttr_hours}h` : "—"} / {analysisData.control_cohort.average_attempts ?? "—"} att
                                </span>
                              </div>
                            </div>
                          </div>
    
                          {/* Treatment Cohort Card */}
                          <div className="rounded-2xl border border-purple-800/60 bg-purple-950/20 p-5 space-y-4">
                            <div className="flex items-center justify-between border-b border-purple-800/40 pb-3">
                              <div>
                                <span className="text-xs font-bold text-purple-200 uppercase">Treatment Cohort</span>
                                <span className="text-[10px] text-purple-400 block font-mono">Strategy: {analysisData.treatment_strategy}</span>
                              </div>
                              <span className="rounded-full bg-purple-900/60 border border-purple-700/60 px-3 py-0.5 text-xs font-mono text-purple-200">
                                {analysisData.treatment_cohort.sample_size} cases
                              </span>
                            </div>
    
                            <div className="grid grid-cols-2 gap-4 text-xs font-mono">
                              <div>
                                <span className="text-[10px] text-purple-400 block">Recovery Rate</span>
                                <span className="text-xl font-bold text-emerald-400">{formatPct(analysisData.treatment_cohort.recovery_rate)}</span>
                                <span className="text-[10px] text-purple-400 block">
                                  {analysisData.treatment_cohort.recovered_count}/{analysisData.treatment_cohort.sample_size} recovered
                                </span>
                              </div>
                              <div>
                                <span className="text-[10px] text-purple-400 block">Financial Yield</span>
                                <span className="text-xl font-bold text-emerald-400">{formatPct(analysisData.treatment_cohort.financial_yield)}</span>
                                <span className="text-[10px] text-purple-400 block">
                                  {formatINR(analysisData.treatment_cohort.amount_recovered_paise)}
                                </span>
                              </div>
                              <div>
                                <span className="text-[10px] text-purple-400 block">Expected Recovery Value</span>
                                <span className="text-sm font-bold text-emerald-300">{formatINR(analysisData.treatment_cohort.expected_recovery_value_paise)}</span>
                              </div>
                              <div>
                                <span className="text-[10px] text-purple-400 block">MTTR / Avg Attempts</span>
                                <span className="text-xs font-bold text-slate-200">
                                  {analysisData.treatment_cohort.mttr_hours ? `${analysisData.treatment_cohort.mttr_hours}h` : "—"} / {analysisData.treatment_cohort.average_attempts ?? "—"} att
                                </span>
                              </div>
                            </div>
                          </div>
                        </div>
                      </div>
    
                      {/* Randomization Covariate Balance Diagnostics */}
                      <div className="space-y-4">
                        <div className="flex items-center justify-between">
                          <h3 className="text-xs font-bold uppercase tracking-wider text-slate-300">
                            Randomization Balance Diagnostics
                          </h3>
                          <span
                            className={`rounded-full border px-2.5 py-0.5 text-[10px] font-mono font-bold uppercase ${getBalanceBadge(
                              analysisData.balance_diagnostics.overall_status
                            )}`}
                          >
                            {analysisData.balance_diagnostics.overall_status.replace("_", " ")}
                          </span>
                        </div>
    
                        <div className="overflow-x-auto rounded-2xl border border-slate-800 bg-slate-950">
                          <table className="w-full text-left text-xs font-mono">
                            <thead className="border-b border-slate-800 bg-slate-900/70 text-[10px] font-bold uppercase tracking-wider text-slate-400">
                              <tr>
                                <th className="px-4 py-3">Covariate Feature</th>
                                <th className="px-4 py-3">Control Distribution</th>
                                <th className="px-4 py-3">Treatment Distribution</th>
                                <th className="px-4 py-3 text-right">Max Delta</th>
                                <th className="px-4 py-3 text-right">Balance Status</th>
                              </tr>
                            </thead>
                            <tbody className="divide-y divide-slate-800/60">
                              {analysisData.balance_diagnostics.features.map((feat) => (
                                <tr key={feat.feature_name} className="hover:bg-slate-900/30">
                                  <td className="px-4 py-3 font-bold text-slate-200 uppercase">{feat.feature_name.replace("_", " ")}</td>
                                  <td className="px-4 py-3 text-slate-400">
                                    {Object.entries(feat.control_distribution).map(([k, v]) => `${k}: ${(v * 100).toFixed(1)}%`).join(", ")}
                                  </td>
                                  <td className="px-4 py-3 text-slate-400">
                                    {Object.entries(feat.treatment_distribution).map(([k, v]) => `${k}: ${(v * 100).toFixed(1)}%`).join(", ")}
                                  </td>
                                  <td className="px-4 py-3 text-right font-bold text-slate-300">
                                    {(feat.max_absolute_difference * 100).toFixed(1)}%
                                  </td>
                                  <td className="px-4 py-3 text-right">
                                    <span
                                      className={`rounded-full border px-2 py-0.5 text-[9px] font-bold uppercase ${getBalanceBadge(
                                        feat.status
                                      )}`}
                                    >
                                      {feat.status}
                                    </span>
                                  </td>
                                </tr>
                              ))}
                            </tbody>
                          </table>
                        </div>
                      </div>
    
                      {/* Overlap & Telemetry Quality Diagnostics */}
                      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2 text-xs font-mono">
                        {/* Telemetry Data Quality */}
                        <div className="rounded-2xl border border-slate-800 bg-slate-950 p-4 space-y-3">
                          <div className="flex items-center justify-between border-b border-slate-800 pb-2">
                            <span className="text-[10px] font-bold text-slate-400 uppercase">Telemetry Quality</span>
                            <span className="rounded-full bg-emerald-950/80 border border-emerald-700/60 px-2 py-0.5 text-[9px] text-emerald-300 uppercase">
                              {analysisData.data_quality.data_quality_status}
                            </span>
                          </div>
                          <div className="space-y-1 text-slate-400">
                            <div>Missing Outcomes: <strong className="text-white">{analysisData.data_quality.missing_outcomes}</strong></div>
                            <div>Missing ML Predictions: <strong className="text-white">{analysisData.data_quality.missing_predictions}</strong></div>
                          </div>
                        </div>
    
                        {/* Population Overlap */}
                        <div className="rounded-2xl border border-slate-800 bg-slate-950 p-4 space-y-3">
                          <div className="flex items-center justify-between border-b border-slate-800 pb-2">
                            <span className="text-[10px] font-bold text-slate-400 uppercase">Population Interference</span>
                            <span className={`rounded-full border px-2 py-0.5 text-[9px] uppercase ${analysisData.overlap_diagnostics.has_overlap ? "bg-rose-950 border-rose-700 text-rose-300 font-bold" : "bg-emerald-950 border-emerald-700 text-emerald-300"}`}>
                              {analysisData.overlap_diagnostics.has_overlap ? "INTERFERENCE DETECTED" : "ISOLATED"}
                            </span>
                          </div>
                          <div className="text-[11px] text-slate-400">
                            {analysisData.overlap_diagnostics.diagnostics.join(" ")}
                          </div>
                        </div>
                      </div>
                    </div>
                  </div>
                )}
              </div>


            {createExpModalOpen && (
              <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-sm p-4">
                <div className="w-full max-w-lg rounded-3xl border border-slate-800 bg-slate-900 p-6 sm:p-8 space-y-6 shadow-2xl">
                  <div className="flex items-start justify-between border-b border-slate-800 pb-4">
                    <div>
                      <span className="rounded bg-purple-950 px-2 py-0.5 text-[10px] font-bold uppercase tracking-wider text-purple-300 border border-purple-700/60">
                        CAUSAL EXPERIMENTATION (PHASE 9H)
                      </span>
                      <h3 className="text-xl font-black text-white mt-1">
                        Create New Causal Experiment
                      </h3>
                      <p className="text-xs text-slate-400">
                        Define treatment vs control strategies and traffic allocation split.
                      </p>
                    </div>
                    <button
                      type="button"
                      onClick={() => setCreateExpModalOpen(false)}
                      className="rounded-xl border border-slate-800 p-2 text-slate-400 hover:text-white"
                    >
                      ✕
                    </button>
                  </div>
    
                  <form onSubmit={handleCreateExperiment} className="space-y-4">
                    <div>
                      <label className="text-xs font-bold text-slate-300 block mb-1">
                        Experiment Name *
                      </label>
                      <input
                        type="text"
                        required
                        value={createExpName}
                        onChange={(e) => setCreateExpName(e.target.value)}
                        placeholder="e.g., Payment Link vs Smart Retry Q3"
                        className="w-full rounded-xl border border-slate-800 bg-slate-950 px-3 py-2 text-xs text-slate-200 placeholder-slate-600 focus:border-purple-500 focus:outline-none"
                      />
                    </div>
    
                    <div>
                      <label className="text-xs font-bold text-slate-300 block mb-1">
                        Description
                      </label>
                      <input
                        type="text"
                        value={createExpDesc}
                        onChange={(e) => setCreateExpDesc(e.target.value)}
                        placeholder="e.g., Empirical evaluation of payment link efficacy on high-risk cases."
                        className="w-full rounded-xl border border-slate-800 bg-slate-950 px-3 py-2 text-xs text-slate-200 placeholder-slate-600 focus:border-purple-500 focus:outline-none"
                      />
                    </div>
    
                    <div className="grid grid-cols-2 gap-4">
                      <div>
                        <label className="text-xs font-bold text-slate-300 block mb-1">
                          Treatment Strategy *
                        </label>
                        <select
                          value={createExpTreatment}
                          onChange={(e) => setCreateExpTreatment(e.target.value)}
                          className="w-full rounded-xl border border-slate-800 bg-slate-950 px-3 py-2 text-xs text-slate-200 focus:border-purple-500 focus:outline-none"
                        >
                          <option value="SEND_PAYMENT_LINK">SEND_PAYMENT_LINK</option>
                          <option value="RETRY_PAYMENT">RETRY_PAYMENT</option>
                          <option value="REQUEST_CUSTOMER_UPDATE">REQUEST_CUSTOMER_UPDATE</option>
                          <option value="ESCALATE_TO_SUPPORT">ESCALATE_TO_SUPPORT</option>
                        </select>
                      </div>
    
                      <div>
                        <label className="text-xs font-bold text-slate-300 block mb-1">
                          Control Strategy *
                        </label>
                        <select
                          value={createExpControl}
                          onChange={(e) => setCreateExpControl(e.target.value)}
                          className="w-full rounded-xl border border-slate-800 bg-slate-950 px-3 py-2 text-xs text-slate-200 focus:border-purple-500 focus:outline-none"
                        >
                          <option value="RETRY_PAYMENT">RETRY_PAYMENT</option>
                          <option value="SEND_PAYMENT_LINK">SEND_PAYMENT_LINK</option>
                          <option value="REQUEST_CUSTOMER_UPDATE">REQUEST_CUSTOMER_UPDATE</option>
                          <option value="ESCALATE_TO_SUPPORT">ESCALATE_TO_SUPPORT</option>
                        </select>
                      </div>
                    </div>
    
                    <div className="grid grid-cols-3 gap-3">
                      <div>
                        <label className="text-xs font-bold text-slate-300 block mb-1">
                          Allocation Split *
                        </label>
                        <select
                          value={createExpAlloc}
                          onChange={(e) => setCreateExpAlloc(parseInt(e.target.value, 10))}
                          className="w-full rounded-xl border border-slate-800 bg-slate-950 px-3 py-2 text-xs text-slate-200 focus:border-purple-500 focus:outline-none"
                        >
                          <option value={50}>50% / 50%</option>
                          <option value={60}>60% / 40%</option>
                          <option value={70}>70% / 30%</option>
                          <option value={80}>80% / 20%</option>
                          <option value={90}>90% / 10%</option>
                        </select>
                      </div>
    
                      <div>
                        <label className="text-xs font-bold text-slate-300 block mb-1">
                          Risk Tier Filter
                        </label>
                        <select
                          value={createExpRiskTier}
                          onChange={(e) => setCreateExpRiskTier(e.target.value)}
                          className="w-full rounded-xl border border-slate-800 bg-slate-950 px-3 py-2 text-xs text-slate-200 focus:border-purple-500 focus:outline-none"
                        >
                          <option value="">All Tiers</option>
                          <option value="LOW">LOW</option>
                          <option value="STANDARD">STANDARD</option>
                          <option value="HIGH">HIGH</option>
                          <option value="CRITICAL">CRITICAL</option>
                        </select>
                      </div>
    
                      <div>
                        <label className="text-xs font-bold text-slate-300 block mb-1">
                          Failure Reason
                        </label>
                        <select
                          value={createExpFailureReason}
                          onChange={(e) => setCreateExpFailureReason(e.target.value)}
                          className="w-full rounded-xl border border-slate-800 bg-slate-950 px-3 py-2 text-xs text-slate-200 focus:border-purple-500 focus:outline-none"
                        >
                          <option value="">All Reasons</option>
                          <option value="INSUFFICIENT_FUNDS">INSUFFICIENT_FUNDS</option>
                          <option value="CARD_EXPIRED">CARD_EXPIRED</option>
                          <option value="NETWORK_ERROR">NETWORK_ERROR</option>
                          <option value="AUTHENTICATION_FAILED">AUTHENTICATION_FAILED</option>
                        </select>
                      </div>
                    </div>
    
                    <div>
                      <label className="text-xs font-bold text-slate-300 block mb-1">
                        Notes / Hypothesis
                      </label>
                      <textarea
                        value={createExpNotes}
                        onChange={(e) => setCreateExpNotes(e.target.value)}
                        placeholder="e.g., Testing if payment links reduce MTTR for customer-actionable failures."
                        rows={2}
                        className="w-full rounded-xl border border-slate-800 bg-slate-950 px-3 py-2 text-xs text-slate-200 placeholder-slate-600 focus:border-purple-500 focus:outline-none"
                      />
                    </div>
    
                    <div className="rounded-xl border border-purple-800/40 bg-purple-950/20 p-3 text-[11px] text-purple-200/90 leading-relaxed font-mono">
                      ✓ Deterministic SHA-256 assignment. Zero financial mutations. State machine starts in DRAFT status.
                    </div>
    
                    <div className="flex items-center justify-end gap-3 border-t border-slate-800 pt-4">
                      <button
                        type="button"
                        onClick={() => setCreateExpModalOpen(false)}
                        className="rounded-xl border border-slate-800 bg-slate-950 px-4 py-2 text-xs font-bold uppercase tracking-wider text-slate-400 hover:text-white transition"
                      >
                        Cancel
                      </button>
                      <button
                        type="submit"
                        disabled={expActionLoading}
                        className="rounded-xl bg-purple-600 px-6 py-2 text-xs font-bold uppercase tracking-wider text-white hover:bg-purple-500 shadow-lg shadow-purple-600/30 transition disabled:opacity-50"
                      >
                        {expActionLoading ? "Creating..." : "Create Experiment (DRAFT)"}
                      </button>
                    </div>
                  </form>
                </div>
              </div>
            )}
    
            {/* Phase 9I: Train Candidate Model Modal */}


    </>
  );
}
