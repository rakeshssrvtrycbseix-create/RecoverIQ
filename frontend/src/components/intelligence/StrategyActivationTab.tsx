"use client";

import React, { useCallback, useEffect, useState } from "react";
import {
  PaginatedActivationsResponse,
  PaginatedRecommendationsResponse,
  StrategyActivationResponse,
  activateStrategyRollout,
  createStrategyActivation,
  fetchStrategyActivations,
  fetchStrategyRecommendations,
  formatINR,
  pauseStrategyActivation,
  rollbackStrategyActivation,
  startCanaryRollout
} from "../../lib/api";
import { formatDelta, formatPct, getActivationStatusBadge, getRolloutHealthBadge } from "./intelligenceBadges";

interface StrategyActivationTabProps {
  recData?: PaginatedRecommendationsResponse | null;
  userRole?: string;
}

export default function StrategyActivationTab({
  recData,
  userRole = "ADMIN",
}: StrategyActivationTabProps) {
  const [internalRecData, setInternalRecData] = useState<PaginatedRecommendationsResponse | null>(null);
  const activeRecData = recData || internalRecData;
  const [error, setError] = useState<string | null>(null);

    const [actData, setActData] = useState<PaginatedActivationsResponse | null>(null);
    const [selectedAct, setSelectedAct] = useState<StrategyActivationResponse | null>(null);
    const [canaryModalOpen, setCanaryModalOpen] = useState(false);
    const [canaryPct, setCanaryPct] = useState<number>(5);
    const [actNotes, setActNotes] = useState<string>("");
    const [actActionLoading, setActActionLoading] = useState(false);
    const [actSuccessMsg, setActSuccessMsg] = useState<string | null>(null);
    const [inspectActModalOpen, setInspectActModalOpen] = useState(false);
  

    const handleCreateActivation = async (recommendationId: string) => {
      setActActionLoading(true);
      setError(null);
      try {
        const created = await createStrategyActivation(recommendationId, null, "Initiated from recommendation");
        setSelectedAct(created);
        setActSuccessMsg("Controlled strategy activation created in APPROVED status. Ready for canary staging.");
        await loadActData();
      } catch (err) {
        setError(err instanceof Error ? err.message : "Failed to create activation");
      } finally {
        setActActionLoading(false);
      }
    };
  
    const handleStartCanary = async (activationId: string, pct: number) => {
      setActActionLoading(true);
      setError(null);
      try {
        const updated = await startCanaryRollout(activationId, pct, actNotes || undefined);
        setSelectedAct(updated);
        setCanaryModalOpen(false);
        setActSuccessMsg(`Canary experiment successfully updated to ${pct}% traffic allocation. (Zero financial mutations)`);
        await loadActData();
      } catch (err) {
        setError(err instanceof Error ? err.message : "Failed to start canary");
      } finally {
        setActActionLoading(false);
      }
    };
  
    const handlePauseActivation = async (activationId: string) => {
      setActActionLoading(true);
      setError(null);
      try {
        const updated = await pauseStrategyActivation(activationId, "Operator paused rollout");
        setSelectedAct(updated);
        setActSuccessMsg("Strategy activation PAUSED (Traffic allocation set to 0%).");
        await loadActData();
      } catch (err) {
        setError(err instanceof Error ? err.message : "Failed to pause activation");
      } finally {
        setActActionLoading(false);
      }
    };
  
    const handleRollbackActivation = async (activationId: string) => {
      setActActionLoading(true);
      setError(null);
      try {
        const updated = await rollbackStrategyActivation(activationId, "Operator rolled back activation");
        setSelectedAct(updated);
        setActSuccessMsg("Strategy activation successfully ROLLED BACK.");
        await loadActData();
      } catch (err) {
        setError(err instanceof Error ? err.message : "Failed to rollback activation");
      } finally {
        setActActionLoading(false);
      }
    };
  
    const handleActivateRollout = async (activationId: string) => {
      setActActionLoading(true);
      setError(null);
      try {
        const updated = await activateStrategyRollout(activationId, "Admin promoted activation to 100% full rollout");
        setSelectedAct(updated);
        setActSuccessMsg("Strategy activation successfully PROMOTED to 100% full production rollout (ACTIVE).");
        await loadActData();
      } catch (err) {
        setError(err instanceof Error ? err.message : "Failed to promote activation");
      } finally {
        setActActionLoading(false);
      }
    };
  
    const handleInspectActivation = (act: StrategyActivationResponse) => {
      setSelectedAct(act);
      setInspectActModalOpen(true);
    };
  

  const loadActData = useCallback(async () => {
    try {
      const res = await fetchStrategyActivations();
      setActData(res);
      if (res && res.items && res.items.length > 0 && !selectedAct) {
        setSelectedAct(res.items[0]);
      }
      if (!recData) {
        const rRes = await fetchStrategyRecommendations().catch(() => null);
        setInternalRecData(rRes);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load Strategy Activations");
    }
  }, [selectedAct, recData]);

    useEffect(() => {
    let ignore = false;
    async function execute() {
      if (!ignore) {
        await loadActData();
      }
    }
    void execute();
    return () => {
      ignore = true;
    };
  }, [loadActData]);

  return (
    <>
      {error && (
        <div className="rounded-xl border border-rose-800/40 bg-rose-950/40 p-4 text-xs text-rose-300">
          {error}
        </div>
      )}

      {actSuccessMsg && (
        <div className="rounded-xl border border-emerald-800/60 bg-emerald-950/40 p-4 text-xs text-emerald-300 flex items-center justify-between shadow-lg">
          <span>{actSuccessMsg}</span>
          <button onClick={() => setActSuccessMsg(null)} className="text-emerald-400 hover:text-white font-bold ml-4">✕</button>
        </div>
      )}
              {/* =========================================================================
                 TAB 1: CONTROLLED STRATEGY ACTIVATION & CANARY ROLLOUT (Phase 9F)
                 ========================================================================= */}
              <div className="space-y-8">
                {/* Mandatory Observational & Governance Disclaimer Banner */}
                <div className="rounded-2xl border border-indigo-800/60 bg-indigo-950/20 p-4 flex items-start gap-3">
                  <span className="rounded bg-indigo-900/80 px-2 py-0.5 text-[10px] font-bold uppercase tracking-wider text-indigo-200 border border-indigo-700/60 shrink-0">
                    CANARY GOVERNANCE
                  </span>
                  <div className="text-xs text-indigo-200/90 leading-relaxed space-y-1">
                    <p className="font-semibold">
                      OBSERVATIONAL / CONTROLLED CANARY EXPERIMENT (PHASE 9F)
                    </p>
                    <p className="text-[11px] text-indigo-300/80">
                      Controlled canary experiments partition traffic deterministically using hash-based bucketing to measure empirical uplift against the control baseline. Strategy eligibility is evaluated deterministically by the authoritative Policy Engine. Starting a canary does NOT trigger autonomous fund movements or execute gateway payments.
                    </p>
                  </div>
                </div>
    
    
                {/* Rollback Safety Recommendation Alert Banner */}
                {actData?.active_activation?.health.status === "ROLLBACK_RECOMMENDED" && (
                  <div className="rounded-2xl border border-rose-800/80 bg-rose-950/40 p-4 flex items-start gap-3 animate-pulse">
                    <span className="rounded bg-rose-900/90 px-2.5 py-1 text-[10px] font-black uppercase tracking-wider text-rose-200 border border-rose-700/80 shrink-0">
                      ROLLBACK RECOMMENDED
                    </span>
                    <div className="text-xs text-rose-200 leading-relaxed space-y-1">
                      <p className="font-bold text-rose-300">
                        Safety Gate Alert: Treatment Performance Underperforming Baseline
                      </p>
                      <p className="text-[11px] text-rose-300/90">
                        Treatment cohort recovery rate has underperformed the control baseline by &ge; 5.0 percentage points. Operators are advised to review the empirical telemetry and pause or rollback this rollout.
                      </p>
                    </div>
                  </div>
                )}
    
                {/* Active Canary / Active Rollout Card */}
                {actData?.active_activation ? (
                  <div className="rounded-3xl border border-purple-500/40 bg-gradient-to-b from-purple-950/30 via-slate-900/80 to-slate-950 p-6 sm:p-8 space-y-8 shadow-2xl shadow-purple-950/30">
                    <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between border-b border-purple-900/40 pb-6">
                      <div>
                        <div className="flex items-center gap-3 flex-wrap">
                          <span className="rounded-full bg-purple-900/80 border border-purple-700/60 px-3 py-1 text-[11px] font-bold uppercase tracking-wider text-purple-200">
                            Active Phased Rollout
                          </span>
                          <span className="text-xs font-mono text-slate-400">
                            ID: {actData.active_activation.activation_id}
                          </span>
                          <span
                            className={`rounded-full border px-2.5 py-0.5 text-xs font-mono font-bold uppercase tracking-wider ${getActivationStatusBadge(
                              actData.active_activation.status
                            )}`}
                          >
                            {actData.active_activation.status} ({actData.active_activation.rollout_percentage}%)
                          </span>
                          <span
                            className={`rounded-full border px-2.5 py-0.5 text-xs font-mono font-bold uppercase tracking-wider ${getRolloutHealthBadge(
                              actData.active_activation.health.status
                            )}`}
                          >
                            Health: {actData.active_activation.health.status}
                          </span>
                        </div>
                        <h2 className="text-2xl font-black text-white mt-2">
                          Controlled Strategy Canary: {actData.active_activation.strategy_type}
                        </h2>
                        <p className="text-xs text-slate-400 mt-1">
                          Governed by ML Model {actData.active_activation.model_version} • Rules {actData.active_activation.governance_version} • Effective From: {new Date(actData.active_activation.effective_from).toLocaleDateString()} • Expires: {new Date(actData.active_activation.expires_at).toLocaleDateString()}
                        </p>
                      </div>
    
                      {/* Actions Header */}
                      <div className="flex items-center gap-2 flex-wrap">
                        {userRole !== "viewer" && (
                          <>
                            <button
                              onClick={() => {
                                setSelectedAct(actData.active_activation);
                                setCanaryPct(actData.active_activation?.rollout_percentage === 0 ? 5 : actData.active_activation?.rollout_percentage || 5);
                                setCanaryModalOpen(true);
                              }}
                              disabled={actActionLoading || actData.active_activation.status === "ROLLED_BACK"}
                              className="rounded-xl bg-purple-600 px-4 py-2 text-xs font-bold uppercase tracking-wider text-white hover:bg-purple-500 shadow-md shadow-purple-600/30 transition disabled:opacity-50"
                            >
                              Adjust Canary Stage
                            </button>
                            {actData.active_activation.status !== "PAUSED" ? (
                              <button
                                onClick={() => handlePauseActivation(actData.active_activation!.activation_id)}
                                disabled={actActionLoading}
                                className="rounded-xl border border-amber-800/80 bg-amber-950/40 px-3.5 py-2 text-xs font-bold uppercase tracking-wider text-amber-300 hover:bg-amber-900/50 transition disabled:opacity-50"
                              >
                                Pause
                              </button>
                            ) : (
                              <button
                                onClick={() => {
                                  setSelectedAct(actData.active_activation);
                                  setCanaryPct(5);
                                  setCanaryModalOpen(true);
                                }}
                                disabled={actActionLoading}
                                className="rounded-xl border border-purple-800/80 bg-purple-950/40 px-3.5 py-2 text-xs font-bold uppercase tracking-wider text-purple-300 hover:bg-purple-900/50 transition disabled:opacity-50"
                              >
                                Resume Canary
                              </button>
                            )}
                            <button
                              onClick={() => handleRollbackActivation(actData.active_activation!.activation_id)}
                              disabled={actActionLoading}
                              className="rounded-xl border border-rose-800/80 bg-rose-950/40 px-3.5 py-2 text-xs font-bold uppercase tracking-wider text-rose-300 hover:bg-rose-900/50 transition disabled:opacity-50"
                            >
                              Rollback
                            </button>
                            {userRole === "admin" && actData.active_activation.status === "CANARY" && (
                              <button
                                onClick={() => handleActivateRollout(actData.active_activation!.activation_id)}
                                disabled={actActionLoading}
                                className="rounded-xl bg-emerald-600 px-4 py-2 text-xs font-bold uppercase tracking-wider text-white hover:bg-emerald-500 shadow-md shadow-emerald-600/30 transition disabled:opacity-50"
                              >
                                Promote to Active (100%)
                              </button>
                            )}
                          </>
                        )}
                      </div>
                    </div>
    
                    {/* Phased Rollout Progress Tracker */}
                    <div className="space-y-3">
                      <div className="flex items-center justify-between text-xs font-mono">
                        <span className="text-slate-400 font-bold uppercase tracking-wider">Canary Staging Progress</span>
                        <span className="text-purple-300 font-bold">{actData.active_activation.rollout_percentage}% Traffic Allocation</span>
                      </div>
                      <div className="grid grid-cols-6 gap-2">
                        {[
                          { label: "Approved (0%)", pct: 0 },
                          { label: "Canary 5%", pct: 5 },
                          { label: "Canary 10%", pct: 10 },
                          { label: "Canary 25%", pct: 25 },
                          { label: "Canary 50%", pct: 50 },
                          { label: "Active (100%)", pct: 100 },
                        ].map((step) => {
                          const isCurrent = actData.active_activation!.rollout_percentage === step.pct;
                          const isPassed = actData.active_activation!.rollout_percentage >= step.pct;
                          return (
                            <div
                              key={step.pct}
                              className={`rounded-xl border p-2.5 text-center transition ${
                                isCurrent
                                  ? "border-purple-500 bg-purple-950/60 shadow-lg shadow-purple-950/50 ring-1 ring-purple-500"
                                  : isPassed
                                  ? "border-emerald-700/60 bg-emerald-950/30 text-emerald-300"
                                  : "border-slate-800 bg-slate-900/40 text-slate-500"
                              }`}
                            >
                              <div className={`text-[10px] font-bold uppercase tracking-wider ${isCurrent ? "text-purple-200" : isPassed ? "text-emerald-300" : "text-slate-500"}`}>
                                {step.label}
                              </div>
                              <div className="text-[9px] font-mono mt-0.5">
                                {isCurrent ? "ACTIVE STAGE" : isPassed ? "COMPLETED" : "PENDING"}
                              </div>
                            </div>
                          );
                        })}
                      </div>
                    </div>
    
                    {/* Experiment Telemetry: Control vs Treatment Cohorts */}
                    {actData.active_activation.comparison && (
                      <div className="space-y-6">
                        <div className="flex items-center justify-between">
                          <h3 className="text-sm font-bold uppercase tracking-wider text-slate-200">
                            Empirical Experiment Telemetry (Control vs Treatment)
                          </h3>
                          <span className="text-xs font-mono text-slate-400">
                            Reliability: <strong className="text-white">{actData.active_activation.comparison.reliability}</strong>
                          </span>
                        </div>
    
                        <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
                          {/* Control Cohort Card */}
                          <div className="rounded-2xl border border-slate-800 bg-slate-950/70 p-5 space-y-4">
                            <div className="flex items-center justify-between border-b border-slate-800/80 pb-3">
                              <div>
                                <span className="text-[11px] font-bold text-slate-300 uppercase">
                                  Control Baseline Cohort
                                </span>
                                <span className="text-[10px] text-slate-400 block font-mono">Standard Strategy Allocation</span>
                              </div>
                              <span className="rounded-full bg-slate-800 px-2.5 py-0.5 text-xs font-mono text-slate-300">
                                {actData.active_activation.comparison.control_metrics.sample_size} cases
                              </span>
                            </div>
    
                            <div className="grid grid-cols-2 gap-4 text-xs font-mono">
                              <div>
                                <span className="text-[10px] text-slate-400 block">Recovery Rate</span>
                                <span className="text-lg font-bold text-slate-200">
                                  {formatPct(actData.active_activation.comparison.control_metrics.recovery_rate)}
                                </span>
                                <span className="text-[10px] text-slate-500 block">
                                  {actData.active_activation.comparison.control_metrics.recovered_count} / {actData.active_activation.comparison.control_metrics.sample_size} recovered
                                </span>
                              </div>
                              <div>
                                <span className="text-[10px] text-slate-400 block">Financial Yield</span>
                                <span className="text-lg font-bold text-slate-200">
                                  {formatPct(actData.active_activation.comparison.control_metrics.financial_yield)}
                                </span>
                                <span className="text-[10px] text-slate-500 block">
                                  {formatINR(actData.active_activation.comparison.control_metrics.amount_recovered_paise)} / {formatINR(actData.active_activation.comparison.control_metrics.amount_at_risk_paise)}
                                </span>
                              </div>
                              <div>
                                <span className="text-[10px] text-slate-400 block">Expected Recovery Value</span>
                                <span className="text-sm font-bold text-purple-300">
                                  {formatINR(actData.active_activation.comparison.control_metrics.expected_recovery_value_paise || 0)}
                                </span>
                              </div>
                              <div>
                                <span className="text-[10px] text-slate-400 block">MTTR (Mean / Median)</span>
                                <span className="text-xs font-bold text-slate-300">
                                  {actData.active_activation.comparison.control_metrics.mean_time_to_recovery_hours ? `${actData.active_activation.comparison.control_metrics.mean_time_to_recovery_hours}h` : "—"} / {actData.active_activation.comparison.control_metrics.median_time_to_recovery_hours ? `${actData.active_activation.comparison.control_metrics.median_time_to_recovery_hours}h` : "—"}
                                </span>
                              </div>
                            </div>
                          </div>
    
                          {/* Treatment Cohort Card */}
                          <div className="rounded-2xl border border-purple-500/40 bg-purple-950/20 p-5 space-y-4">
                            <div className="flex items-center justify-between border-b border-purple-900/40 pb-3">
                              <div>
                                <span className="text-[11px] font-bold text-purple-300 uppercase">
                                  Treatment Canary Cohort
                                </span>
                                <span className="text-[10px] text-purple-400/80 block font-mono">
                                  Strategy: {actData.active_activation.strategy_type} ({actData.active_activation.rollout_percentage}%)
                                </span>
                              </div>
                              <span className="rounded-full bg-purple-900/80 border border-purple-700/60 px-2.5 py-0.5 text-xs font-mono text-purple-200">
                                {actData.active_activation.comparison.treatment_metrics.sample_size} cases
                              </span>
                            </div>
    
                            <div className="grid grid-cols-2 gap-4 text-xs font-mono">
                              <div>
                                <span className="text-[10px] text-purple-400/80 block">Recovery Rate</span>
                                <span className="text-lg font-bold text-emerald-400">
                                  {formatPct(actData.active_activation.comparison.treatment_metrics.recovery_rate)}
                                </span>
                                <span className="text-[10px] text-purple-400/60 block">
                                  {actData.active_activation.comparison.treatment_metrics.recovered_count} / {actData.active_activation.comparison.treatment_metrics.sample_size} recovered
                                </span>
                              </div>
                              <div>
                                <span className="text-[10px] text-purple-400/80 block">Financial Yield</span>
                                <span className="text-lg font-bold text-emerald-300">
                                  {formatPct(actData.active_activation.comparison.treatment_metrics.financial_yield)}
                                </span>
                                <span className="text-[10px] text-purple-400/60 block">
                                  {formatINR(actData.active_activation.comparison.treatment_metrics.amount_recovered_paise)} / {formatINR(actData.active_activation.comparison.treatment_metrics.amount_at_risk_paise)}
                                </span>
                              </div>
                              <div>
                                <span className="text-[10px] text-purple-400/80 block">Expected Recovery Value</span>
                                <span className="text-sm font-bold text-purple-200">
                                  {formatINR(actData.active_activation.comparison.treatment_metrics.expected_recovery_value_paise || 0)}
                                </span>
                              </div>
                              <div>
                                <span className="text-[10px] text-purple-400/80 block">MTTR (Mean / Median)</span>
                                <span className="text-xs font-bold text-purple-300">
                                  {actData.active_activation.comparison.treatment_metrics.mean_time_to_recovery_hours ? `${actData.active_activation.comparison.treatment_metrics.mean_time_to_recovery_hours}h` : "—"} / {actData.active_activation.comparison.treatment_metrics.median_time_to_recovery_hours ? `${actData.active_activation.comparison.treatment_metrics.median_time_to_recovery_hours}h` : "—"}
                                </span>
                              </div>
                            </div>
                          </div>
                        </div>
    
                        {/* Comparative Uplift & Statistical Confidence Panel */}
                        <div className="rounded-2xl border border-slate-800 bg-slate-950 p-5 space-y-4">
                          <div className="flex items-center justify-between border-b border-slate-800 pb-3">
                            <span className="text-xs font-bold uppercase tracking-wider text-indigo-400">
                              Comparative Uplift & Statistical Significance
                            </span>
                            {actData.active_activation.comparison.confidence_interval.is_significant ? (
                              <span className="rounded-full bg-emerald-950/80 border border-emerald-700/60 px-2.5 py-0.5 text-[10px] font-bold uppercase text-emerald-300">
                                Statistically Significant (p &lt; 0.05)
                              </span>
                            ) : (
                              <span className="rounded-full bg-slate-900 border border-slate-800 px-2.5 py-0.5 text-[10px] font-mono text-slate-400">
                                Inconclusive (Accumulating Data)
                              </span>
                            )}
                          </div>
    
                          <div className="grid grid-cols-2 gap-4 sm:grid-cols-4 text-xs font-mono">
                            <div>
                              <span className="text-[10px] text-slate-400 block">Absolute Uplift</span>
                              <span className={`text-base font-black ${
                                (actData.active_activation.comparison.uplift.absolute_uplift || 0) >= 0 ? "text-emerald-400" : "text-rose-400"
                              }`}>
                                {formatDelta(actData.active_activation.comparison.uplift.absolute_uplift)}
                              </span>
                            </div>
                            <div>
                              <span className="text-[10px] text-slate-400 block">Relative Uplift</span>
                              <span className={`text-base font-black ${
                                (actData.active_activation.comparison.uplift.relative_uplift_pct || 0) >= 0 ? "text-emerald-400" : "text-rose-400"
                              }`}>
                                {actData.active_activation.comparison.uplift.relative_uplift_pct !== null ? `${actData.active_activation.comparison.uplift.relative_uplift_pct > 0 ? "+" : ""}${actData.active_activation.comparison.uplift.relative_uplift_pct}%` : "—"}
                              </span>
                            </div>
                            <div>
                              <span className="text-[10px] text-slate-400 block">Incremental ERV</span>
                              <span className="text-base font-black text-purple-300">
                                {actData.active_activation.comparison.uplift.incremental_expected_recovery_value_paise !== null ? formatINR(actData.active_activation.comparison.uplift.incremental_expected_recovery_value_paise) : "—"}
                              </span>
                            </div>
                            <div>
                              <span className="text-[10px] text-slate-400 block">95% Confidence Interval</span>
                              <span className="text-xs font-bold text-slate-300 block mt-1">
                                {actData.active_activation.comparison.confidence_interval.lower_bound !== null && actData.active_activation.comparison.confidence_interval.upper_bound !== null
                                  ? `[${formatDelta(actData.active_activation.comparison.confidence_interval.lower_bound)}, ${formatDelta(actData.active_activation.comparison.confidence_interval.upper_bound)}]`
                                  : "—"}
                              </span>
                            </div>
                          </div>
                        </div>
    
                        {/* Rollout Safety Diagnostics */}
                        <div className="rounded-2xl border border-slate-800 bg-slate-950 p-4 space-y-2">
                          <span className="text-[11px] font-bold text-slate-300 uppercase tracking-wider block">
                            Automated Rollout Diagnostics
                          </span>
                          <ul className="space-y-1 text-xs text-slate-400 list-disc list-inside">
                            {actData.active_activation.health.diagnostics.map((diag, idx) => (
                              <li key={idx}>{diag}</li>
                            ))}
                          </ul>
                        </div>
                      </div>
                    )}
                  </div>
                ) : (
                  <div className="rounded-3xl border border-slate-800 bg-slate-900/40 p-8 text-center space-y-4">
                    <div className="mx-auto flex h-12 w-12 items-center justify-center rounded-2xl bg-purple-950/60 border border-purple-800/40 text-purple-400">
                      <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M13 10V3L4 14h7v7l9-11h-7z" />
                      </svg>
                    </div>
                    <div>
                      <h3 className="text-lg font-bold text-white">No Active Strategy Canary Rollout</h3>
                      <p className="text-xs text-slate-400 max-w-md mx-auto mt-1">
                        There is currently no active canary experiment running. You can initiate a controlled rollout from an approved recommendation in the Recommendations tab.
                      </p>
                    </div>
                    {activeRecData?.active_recommendation && activeRecData.active_recommendation.status === "APPROVED" && userRole !== "viewer" && (
                      <button
                        onClick={() => handleCreateActivation(activeRecData.active_recommendation!.recommendation_id)}
                        disabled={actActionLoading}
                        className="rounded-xl bg-purple-600 px-6 py-2.5 text-xs font-bold uppercase tracking-wider text-white hover:bg-purple-500 shadow-lg shadow-purple-600/30 transition disabled:opacity-50"
                      >
                        Launch Canary for Approved Recommendation ({activeRecData.active_recommendation.strategy_type})
                      </button>
                    )}
                  </div>
                )}
    
                {/* Historical Controlled Activations Table */}
                <div className="rounded-3xl border border-slate-800 bg-slate-900/60 p-6 space-y-4">
                  <div className="flex items-center justify-between border-b border-slate-800/80 pb-4">
                    <div>
                      <h3 className="text-lg font-black text-white">Controlled Activations History</h3>
                      <p className="text-xs text-slate-400">Versioned record of all canary and production strategy rollouts.</p>
                    </div>
                    <span className="text-xs font-mono text-slate-400">{actData?.total || 0} Activations</span>
                  </div>
    
                  <div className="overflow-x-auto">
                    <table className="w-full text-left text-xs font-mono">
                      <thead>
                        <tr className="border-b border-slate-800 text-slate-400 font-bold uppercase text-[10px]">
                          <th className="pb-3">Activation ID</th>
                          <th className="pb-3">Strategy</th>
                          <th className="pb-3">Status</th>
                          <th className="pb-3">Rollout %</th>
                          <th className="pb-3">Health</th>
                          <th className="pb-3">Created</th>
                          <th className="pb-3 text-right">Actions</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-slate-800/60">
                        {actData && actData.items.length > 0 ? (
                          actData.items.map((act) => (
                            <tr key={act.activation_id} className="hover:bg-slate-800/30 transition">
                              <td className="py-3 font-bold text-indigo-400">{act.activation_id}</td>
                              <td className="py-3 text-slate-200 font-sans font-semibold">{act.strategy_type}</td>
                              <td className="py-3">
                                <span className={`rounded-full border px-2 py-0.5 text-[10px] font-bold uppercase ${getActivationStatusBadge(act.status)}`}>
                                  {act.status}
                                </span>
                              </td>
                              <td className="py-3 text-purple-300 font-bold">{act.rollout_percentage}%</td>
                              <td className="py-3">
                                <span className={`rounded px-1.5 py-0.5 text-[10px] font-bold uppercase border ${getRolloutHealthBadge(act.health.status)}`}>
                                  {act.health.status}
                                </span>
                              </td>
                              <td className="py-3 text-slate-400">{new Date(act.created_at).toLocaleDateString()}</td>
                              <td className="py-3 text-right">
                                <button
                                  onClick={() => handleInspectActivation(act)}
                                  className="rounded-lg border border-slate-700 bg-slate-800 px-3 py-1 text-[11px] font-sans font-semibold text-slate-300 hover:bg-slate-700 hover:text-white transition"
                                >
                                  Inspect
                                </button>
                              </td>
                            </tr>
                          ))
                        ) : (
                          <tr>
                            <td colSpan={7} className="py-6 text-center text-slate-500 font-sans">
                              No strategy activation records found.
                            </td>
                          </tr>
                        )}
                      </tbody>
                    </table>
                  </div>
                </div>
              </div>


            {canaryModalOpen && selectedAct && (
              <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/80 backdrop-blur-sm p-4 overflow-y-auto">
                <div className="relative w-full max-w-lg rounded-3xl border border-purple-500/50 bg-slate-900 p-6 sm:p-8 shadow-2xl shadow-purple-950/50 space-y-6 animate-in fade-in zoom-in duration-200">
                  <div className="flex items-start justify-between border-b border-slate-800 pb-4">
                    <div>
                      <span className="rounded-full bg-purple-900/80 border border-purple-700/60 px-2.5 py-0.5 text-[10px] font-bold uppercase text-purple-200">
                        Phased Canary Staging
                      </span>
                      <h3 className="text-xl font-black text-white mt-1">
                        Adjust Traffic: {selectedAct.strategy_type}
                      </h3>
                      <p className="text-xs text-slate-400">
                        ID: {selectedAct.activation_id} • Current: {selectedAct.rollout_percentage}%
                      </p>
                    </div>
                    <button
                      onClick={() => setCanaryModalOpen(false)}
                      className="rounded-xl border border-slate-800 bg-slate-950 p-2 text-slate-400 hover:text-white"
                    >
                      <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M6 18L18 6M6 6l12 12" />
                      </svg>
                    </button>
                  </div>
    
                  <div className="space-y-4">
                    <label className="block text-xs font-bold uppercase tracking-wider text-slate-300">
                      Select Canary Rollout Stage
                    </label>
                    <div className="grid grid-cols-2 gap-3">
                      {[
                        { pct: 5, label: "5% Pilot", desc: "Initial verification cohort" },
                        { pct: 10, label: "10% Canary", desc: "Statistical sampling" },
                        { pct: 25, label: "25% Phased", desc: "Scaled confidence verification" },
                        { pct: 50, label: "50% A/B Test", desc: "Balanced cohort experiment" },
                      ].map((stage) => (
                        <button
                          key={stage.pct}
                          type="button"
                          onClick={() => setCanaryPct(stage.pct)}
                          className={`rounded-2xl border p-3.5 text-left transition ${
                            canaryPct === stage.pct
                              ? "border-purple-500 bg-purple-950/60 shadow-md shadow-purple-950/50 ring-1 ring-purple-500"
                              : "border-slate-800 bg-slate-950/60 hover:border-slate-700"
                          }`}
                        >
                          <div className="flex items-center justify-between">
                            <span className={`text-sm font-bold font-mono ${canaryPct === stage.pct ? "text-purple-200" : "text-white"}`}>
                              {stage.label}
                            </span>
                            <span className={`text-xs font-mono font-bold ${canaryPct === stage.pct ? "text-purple-300" : "text-slate-400"}`}>
                              {stage.pct}%
                            </span>
                          </div>
                          <span className="text-[10px] text-slate-400 block mt-1">{stage.desc}</span>
                        </button>
                      ))}
                    </div>
    
                    <div className="space-y-2">
                      <label className="block text-xs font-bold uppercase tracking-wider text-slate-300">
                        Operator Audit Notes
                      </label>
                      <textarea
                        value={actNotes}
                        onChange={(e) => setActNotes(e.target.value)}
                        placeholder="Enter audit rationale for canary percentage adjustment..."
                        rows={2}
                        className="w-full rounded-xl border border-slate-800 bg-slate-950 px-4 py-2.5 text-xs text-slate-200 focus:border-purple-500 focus:outline-none"
                      />
                    </div>
    
                    <div className="rounded-xl border border-slate-800 bg-slate-950 p-3 text-[11px] text-slate-400">
                      <strong className="text-slate-300">Deterministic Assignment:</strong> Cases are allocated to canary based on deterministic SHA-256 hash buckets. PolicyEngine guardrails remain active on all actions.
                    </div>
                  </div>
    
                  <div className="flex items-center justify-end gap-3 border-t border-slate-800 pt-4">
                    <button
                      type="button"
                      onClick={() => setCanaryModalOpen(false)}
                      className="rounded-xl border border-slate-800 bg-slate-950 px-4 py-2 text-xs font-bold uppercase tracking-wider text-slate-400 hover:text-white"
                    >
                      Cancel
                    </button>
                    <button
                      type="button"
                      onClick={() => handleStartCanary(selectedAct.activation_id, canaryPct)}
                      disabled={actActionLoading}
                      className="rounded-xl bg-purple-600 px-6 py-2 text-xs font-bold uppercase tracking-wider text-white hover:bg-purple-500 shadow-md shadow-purple-600/30 transition disabled:opacity-50"
                    >
                      {actActionLoading ? "Updating..." : `Set Canary to ${canaryPct}%`}
                    </button>
                  </div>
                </div>
              </div>
            )}
    
            {/* Inspect Activation Modal */}
            {inspectActModalOpen && selectedAct && (
              <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/80 backdrop-blur-sm p-4 overflow-y-auto">
                <div className="relative w-full max-w-2xl rounded-3xl border border-slate-800 bg-slate-900 p-6 sm:p-8 shadow-2xl space-y-6 animate-in fade-in zoom-in duration-200 max-h-[90vh] overflow-y-auto">
                  <div className="flex items-start justify-between border-b border-slate-800 pb-4">
                    <div>
                      <div className="flex items-center gap-2">
                        <span className="text-xs font-mono font-bold text-indigo-400">{selectedAct.activation_id}</span>
                        <span className={`rounded-full border px-2 py-0.5 text-[10px] font-bold uppercase ${getActivationStatusBadge(selectedAct.status)}`}>
                          {selectedAct.status} ({selectedAct.rollout_percentage}%)
                        </span>
                        <span className={`rounded px-1.5 py-0.5 text-[10px] font-bold uppercase border ${getRolloutHealthBadge(selectedAct.health.status)}`}>
                          {selectedAct.health.status}
                        </span>
                      </div>
                      <h3 className="text-xl font-black text-white mt-1">
                        Activation Strategy: {selectedAct.strategy_type}
                      </h3>
                      <p className="text-xs text-slate-400">
                        Governing Model: {selectedAct.model_version} • Recommendation ID: {selectedAct.recommendation_id}
                      </p>
                    </div>
                    <button
                      onClick={() => setInspectActModalOpen(false)}
                      className="rounded-xl border border-slate-800 bg-slate-950 p-2 text-slate-400 hover:text-white"
                    >
                      <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M6 18L18 6M6 6l12 12" />
                      </svg>
                    </button>
                  </div>
    
                  {selectedAct.comparison && (
                    <div className="space-y-4">
                      <div className="grid grid-cols-2 gap-4">
                        <div className="rounded-2xl border border-slate-800 bg-slate-950 p-4 space-y-2">
                          <span className="text-[10px] font-bold text-slate-400 uppercase font-mono">Control Cohort</span>
                          <div className="text-xs font-mono space-y-1">
                            <div>Rate: <strong className="text-slate-200">{formatPct(selectedAct.comparison.control_metrics.recovery_rate)}</strong></div>
                            <div>Cases: {selectedAct.comparison.control_metrics.recovered_count}/{selectedAct.comparison.control_metrics.sample_size}</div>
                            <div>ERV: <strong className="text-purple-300">{formatINR(selectedAct.comparison.control_metrics.expected_recovery_value_paise || 0)}</strong></div>
                          </div>
                        </div>
                        <div className="rounded-2xl border border-purple-500/40 bg-purple-950/20 p-4 space-y-2">
                          <span className="text-[10px] font-bold text-purple-300 uppercase font-mono">Treatment Cohort ({selectedAct.rollout_percentage}%)</span>
                          <div className="text-xs font-mono space-y-1">
                            <div>Rate: <strong className="text-emerald-400">{formatPct(selectedAct.comparison.treatment_metrics.recovery_rate)}</strong></div>
                            <div>Cases: {selectedAct.comparison.treatment_metrics.recovered_count}/{selectedAct.comparison.treatment_metrics.sample_size}</div>
                            <div>ERV: <strong className="text-purple-200">{formatINR(selectedAct.comparison.treatment_metrics.expected_recovery_value_paise || 0)}</strong></div>
                          </div>
                        </div>
                      </div>
    
                      <div className="rounded-2xl border border-slate-800 bg-slate-950 p-4 space-y-2">
                        <span className="text-[10px] font-bold text-slate-400 uppercase font-mono block">Uplift & Confidence</span>
                        <div className="grid grid-cols-3 gap-2 text-xs font-mono">
                          <div>
                            <span className="text-[9px] text-slate-400 block">Absolute Uplift</span>
                            <strong className={(selectedAct.comparison.uplift.absolute_uplift || 0) >= 0 ? "text-emerald-400" : "text-rose-400"}>
                              {formatDelta(selectedAct.comparison.uplift.absolute_uplift)}
                            </strong>
                          </div>
                          <div>
                            <span className="text-[9px] text-slate-400 block">Relative Uplift</span>
                            <strong className={(selectedAct.comparison.uplift.relative_uplift_pct || 0) >= 0 ? "text-emerald-400" : "text-rose-400"}>
                              {selectedAct.comparison.uplift.relative_uplift_pct !== null ? `${selectedAct.comparison.uplift.relative_uplift_pct > 0 ? "+" : ""}${selectedAct.comparison.uplift.relative_uplift_pct}%` : "—"}
                            </strong>
                          </div>
                          <div>
                            <span className="text-[9px] text-slate-400 block">Reliability</span>
                            <strong className="text-white">{selectedAct.comparison.reliability}</strong>
                          </div>
                        </div>
                      </div>
    
                      <div className="rounded-2xl border border-slate-800 bg-slate-950 p-4 space-y-1 text-xs">
                        <span className="text-[10px] font-bold text-slate-400 uppercase font-mono block">Safety Diagnostics</span>
                        <ul className="list-disc list-inside text-slate-300 text-[11px] space-y-0.5">
                          {selectedAct.health.diagnostics.map((d, i) => (
                            <li key={i}>{d}</li>
                          ))}
                        </ul>
                      </div>
                    </div>
                  )}
    
                  <div className="flex justify-end border-t border-slate-800 pt-4">
                    <button
                      type="button"
                      onClick={() => setInspectActModalOpen(false)}
                      className="rounded-xl bg-slate-800 px-5 py-2 text-xs font-bold uppercase tracking-wider text-white hover:bg-slate-700 transition"
                    >
                      Close
                    </button>
                  </div>
                </div>
              </div>
            )}
    
            {/* Modal: Production Promotion Confirmation (Phase 9G Admin) */}


    </>
  );
}
