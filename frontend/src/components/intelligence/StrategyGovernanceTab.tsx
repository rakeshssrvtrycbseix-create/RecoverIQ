"use client";

import React, { useCallback, useEffect, useState } from "react";
import {
  PaginatedRecommendationsResponse,
  StrategyRecommendationResponse,
  approveStrategyRecommendation,
  fetchStrategyRecommendations,
  formatINR,
  rejectStrategyRecommendation
} from "../../lib/api";
import { formatDelta, formatNum, formatPct, getConfidenceLevelBadge, getRecommendationStatusBadge, getReliabilityBadge, getStatusBadge } from "./intelligenceBadges";

interface StrategyGovernanceTabProps {
  userRole?: string;
}

export default function StrategyGovernanceTab({ userRole = "ADMIN" }: StrategyGovernanceTabProps) {
  const [error, setError] = useState<string | null>(null);

    const [recData, setRecData] = useState<PaginatedRecommendationsResponse | null>(null);
    const [selectedRec, setSelectedRec] = useState<StrategyRecommendationResponse | null>(null);
    const [reviewNotes, setReviewNotes] = useState<string>("");
    const [reviewActionLoading, setReviewActionLoading] = useState(false);
    const [reviewModalOpen, setReviewModalOpen] = useState(false);
    const [reviewSuccessMsg, setReviewSuccessMsg] = useState<string | null>(null);
  

    const handleOpenReview = (rec: StrategyRecommendationResponse) => {
      setSelectedRec(rec);
      setReviewNotes(rec.review_notes || "");
      setReviewSuccessMsg(null);
      setReviewModalOpen(true);
    };
  
    const handleApprove = async () => {
      if (!selectedRec) return;
      setReviewActionLoading(true);
      setError(null);
      try {
        const updated = await approveStrategyRecommendation(selectedRec.recommendation_id, reviewNotes);
        setSelectedRec(updated);
        setReviewSuccessMsg("Strategy recommendation successfully APPROVED. (Zero financial actions dispatched)");
        await loadRecData();
      } catch (err) {
        setError(err instanceof Error ? err.message : "Approval failed");
      } finally {
        setReviewActionLoading(false);
      }
    };
  
    const handleReject = async () => {
      if (!selectedRec) return;
      setReviewActionLoading(true);
      setError(null);
      try {
        const updated = await rejectStrategyRecommendation(selectedRec.recommendation_id, reviewNotes);
        setSelectedRec(updated);
        setReviewSuccessMsg("Strategy recommendation successfully REJECTED.");
        await loadRecData();
      } catch (err) {
        setError(err instanceof Error ? err.message : "Rejection failed");
      } finally {
        setReviewActionLoading(false);
      }
    };
  

  const loadRecData = useCallback(async () => {
    try {
      const res = await fetchStrategyRecommendations();
      setRecData(res);
      if (res && res.items && res.items.length > 0 && !selectedRec) {
        setSelectedRec(res.items[0]);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load Strategy Recommendations");
    }
  }, [selectedRec]);

    useEffect(() => {
    let ignore = false;
    async function execute() {
      if (!ignore) {
        await loadRecData();
      }
    }
    void execute();
    return () => {
      ignore = true;
    };
  }, [loadRecData]);

  return (
    <>
      {error && (
        <div className="rounded-xl border border-rose-800/40 bg-rose-950/40 p-4 text-xs text-rose-300">
          {error}
        </div>
      )}

      {reviewSuccessMsg && (
        <div className="rounded-xl border border-emerald-800/60 bg-emerald-950/40 p-4 text-xs text-emerald-300 flex items-center justify-between shadow-lg">
          <span>{reviewSuccessMsg}</span>
          <button onClick={() => setReviewSuccessMsg(null)} className="text-emerald-400 hover:text-white font-bold ml-4">✕</button>
        </div>
      )}
              {/* =========================================================================
                 TAB 0: GOVERNED STRATEGY RECOMMENDATIONS (Phase 9E)
                 ========================================================================= */}
              <div className="space-y-8">
                {/* Mandatory Observational & Governance Disclaimer Banner */}
                <div className="rounded-2xl border border-amber-800/60 bg-amber-950/20 p-4 flex items-start gap-3">
                  <span className="rounded bg-amber-900/80 px-2 py-0.5 text-[10px] font-bold uppercase tracking-wider text-amber-200 border border-amber-700/60 shrink-0">
                    GOVERNED ADVISORY
                  </span>
                  <div className="text-xs text-amber-200/90 leading-relaxed space-y-1">
                    <p className="font-semibold">
                      OBSERVATIONAL / GOVERNED STRATEGY RECOMMENDATION
                    </p>
                    <p className="text-[11px] text-amber-300/80">
                      Governed strategy recommendations synthesize Phase 9A Evaluation, 9B Governance, 9C Optimization, and 9D Simulation into versioned proposals for human operator review. Approving a recommendation records operator endorsement and updates its lifecycle status. It does NOT create, schedule, dispatch, or execute financial actions.
                    </p>
                  </div>
                </div>
    
    
                {/* Active Proposed Recommendation Card */}
                {recData?.active_recommendation ? (
                  <div className="rounded-3xl border border-indigo-500/40 bg-gradient-to-b from-indigo-950/40 to-slate-900/80 p-6 sm:p-8 space-y-6 shadow-xl shadow-indigo-950/30">
                    <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between border-b border-indigo-900/50 pb-6">
                      <div>
                        <div className="flex items-center gap-3">
                          <span className="rounded-full bg-indigo-900/80 border border-indigo-700/60 px-3 py-1 text-[11px] font-bold uppercase tracking-wider text-indigo-200">
                            Active Governed Proposal
                          </span>
                          <span className="text-xs font-mono text-slate-400">
                            ID: {recData.active_recommendation.recommendation_id}
                          </span>
                          <span
                            className={`rounded-full border px-2.5 py-0.5 text-xs font-mono font-bold uppercase tracking-wider ${getRecommendationStatusBadge(
                              recData.active_recommendation.status
                            )}`}
                          >
                            {recData.active_recommendation.status.replace("_", " ")}
                          </span>
                        </div>
                        <h2 className="text-2xl font-black text-white mt-2">
                          Proposed Recovery Strategy: {recData.active_recommendation.strategy_type}
                        </h2>
                        <p className="text-xs text-slate-300 mt-1">
                          Recommended Retry Cadence: {recData.active_recommendation.retry_delay_hours} Hours after failure
                        </p>
                      </div>
    
                      <div className="flex items-center gap-3">
                        <button
                          onClick={() => handleOpenReview(recData.active_recommendation!)}
                          className="flex items-center gap-2 rounded-xl bg-indigo-600 px-6 py-3 text-xs font-bold uppercase tracking-wider text-white shadow-lg shadow-indigo-600/30 hover:bg-indigo-500 transition"
                        >
                          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                          </svg>
                          <span>Review & Decision</span>
                        </button>
                      </div>
                    </div>
    
                    {/* Proposal Key Statistics */}
                    <div className="grid grid-cols-2 gap-4 sm:grid-cols-4 font-mono">
                      <div className="rounded-2xl border border-slate-800 bg-slate-950/70 p-4">
                        <span className="text-[10px] text-slate-400 block uppercase">Rate Delta (Δ)</span>
                        <span className="text-2xl font-black text-emerald-400">
                          {formatDelta(recData.active_recommendation.rate_delta)}
                        </span>
                        <span className="text-[10px] text-slate-400 block mt-1">
                          Relative: {recData.active_recommendation.relative_uplift_pct !== null ? `+${recData.active_recommendation.relative_uplift_pct.toFixed(1)}%` : "—"}
                        </span>
                      </div>
    
                      <div className="rounded-2xl border border-slate-800 bg-slate-950/70 p-4">
                        <span className="text-[10px] text-slate-400 block uppercase">Incremental ERV</span>
                        <span className="text-2xl font-black text-emerald-300">
                          {recData.active_recommendation.incremental_erv_paise !== null
                            ? formatINR(recData.active_recommendation.incremental_erv_paise)
                            : "—"}
                        </span>
                        <span className="text-[10px] text-slate-400 block mt-1">
                          Alt: {recData.active_recommendation.alternative_erv_paise ? formatINR(recData.active_recommendation.alternative_erv_paise) : "—"}
                        </span>
                      </div>
    
                      <div className="rounded-2xl border border-slate-800 bg-slate-950/70 p-4">
                        <span className="text-[10px] text-slate-400 block uppercase">Confidence Score</span>
                        <span className="text-2xl font-black text-cyan-300">
                          {(recData.active_recommendation.recommendation_confidence * 100).toFixed(0)}%
                        </span>
                        <span
                          className={`inline-block rounded px-1.5 py-0.2 text-[10px] font-bold uppercase border mt-1 ${getConfidenceLevelBadge(
                            recData.active_recommendation.confidence_level
                          )}`}
                        >
                          {recData.active_recommendation.confidence_level}
                        </span>
                      </div>
    
                      <div className="rounded-2xl border border-slate-800 bg-slate-950/70 p-4">
                        <span className="text-[10px] text-slate-400 block uppercase">Evidence Reliability</span>
                        <span
                          className={`inline-block rounded px-2 py-1 text-xs font-bold uppercase border mt-1 ${getReliabilityBadge(
                            recData.active_recommendation.reliability
                          )}`}
                        >
                          {recData.active_recommendation.reliability}
                        </span>
                        <span className="text-[10px] text-slate-400 block mt-1">
                          Sample: {recData.active_recommendation.sample_size} cases
                        </span>
                      </div>
                    </div>
    
                    {/* Reasoning & Expiration */}
                    <div className="rounded-2xl border border-slate-800 bg-slate-950/50 p-4 space-y-2">
                      <div className="flex items-center justify-between text-xs">
                        <span className="font-bold text-slate-300">Governance Reasoning & Evidence Summary:</span>
                        <span className="text-slate-400 font-mono text-[11px]">
                          Expires: {new Date(recData.active_recommendation.expires_at).toLocaleDateString()}
                        </span>
                      </div>
                      <p className="text-xs text-slate-300 leading-relaxed">
                        {recData.active_recommendation.reasoning}
                      </p>
                      {recData.active_recommendation.diagnostics.length > 0 && (
                        <div className="pt-2 flex flex-wrap gap-2">
                          {recData.active_recommendation.diagnostics.map((diag, i) => (
                            <span key={i} className="rounded bg-amber-950/60 border border-amber-800/40 px-2 py-0.5 text-[10px] text-amber-300 font-mono">
                              {diag}
                            </span>
                          ))}
                        </div>
                      )}
                    </div>
                  </div>
                ) : (
                  <div className="rounded-2xl border border-slate-800 bg-slate-900/40 p-8 text-center space-y-3">
                    <div className="w-12 h-12 rounded-full bg-slate-800 flex items-center justify-center mx-auto text-slate-400">
                      <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                      </svg>
                    </div>
                    <h3 className="text-base font-bold text-white">No Active Strategy Recommendation</h3>
                    <p className="text-xs text-slate-400 max-w-md mx-auto">
                      The governance engine requires minimum historical evidence (N ≥ 10), healthy model status, zero data quality anomalies, and strictly positive recovery rate uplift to generate an active strategy recommendation.
                    </p>
                  </div>
                )}
    
                {/* Historical Recommendations Table */}
                <div className="rounded-2xl border border-slate-800 bg-slate-900/40 p-6 space-y-4">
                  <div className="flex items-center justify-between">
                    <h3 className="text-sm font-bold text-white uppercase tracking-wider">
                      Governed Recommendations History
                    </h3>
                    <span className="text-xs text-slate-400 font-mono">
                      {recData?.total || 0} Total Proposals Logged
                    </span>
                  </div>
    
                  <div className="overflow-x-auto">
                    <table className="w-full text-left text-xs">
                      <thead className="border-b border-slate-800 text-[10px] uppercase tracking-wider text-slate-400">
                        <tr>
                          <th className="pb-3 font-semibold">Recommendation ID</th>
                          <th className="pb-3 font-semibold">Proposed Strategy</th>
                          <th className="pb-3 font-semibold">Delay</th>
                          <th className="pb-3 font-semibold">Rate Delta</th>
                          <th className="pb-3 font-semibold">Incremental ERV</th>
                          <th className="pb-3 font-semibold">Confidence</th>
                          <th className="pb-3 font-semibold">Status</th>
                          <th className="pb-3 font-semibold">Created</th>
                          <th className="pb-3 font-semibold">Reviewed By</th>
                          <th className="pb-3 font-semibold text-right">Actions</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-slate-800/60 font-mono">
                        {recData && recData.items.length > 0 ? (
                          recData.items.map((item) => (
                            <tr key={item.recommendation_id} className="hover:bg-slate-800/30 transition">
                              <td className="py-3 font-bold text-indigo-300">
                                {item.recommendation_id}
                              </td>
                              <td className="py-3 font-sans font-medium text-slate-200">
                                {item.strategy_type}
                              </td>
                              <td className="py-3 text-slate-400">
                                {item.retry_delay_hours}h
                              </td>
                              <td className="py-3 font-bold text-emerald-400">
                                {formatDelta(item.rate_delta)}
                              </td>
                              <td className="py-3 text-emerald-300">
                                {item.incremental_erv_paise !== null ? formatINR(item.incremental_erv_paise) : "—"}
                              </td>
                              <td className="py-3">
                                <span className={`rounded px-1.5 py-0.5 text-[10px] font-bold uppercase border ${getConfidenceLevelBadge(item.confidence_level)}`}>
                                  {(item.recommendation_confidence * 100).toFixed(0)}%
                                </span>
                              </td>
                              <td className="py-3">
                                <span className={`rounded-full border px-2 py-0.5 text-[10px] font-bold uppercase ${getRecommendationStatusBadge(item.status)}`}>
                                  {item.status.replace("_", " ")}
                                </span>
                              </td>
                              <td className="py-3 text-slate-400 text-[11px]">
                                {new Date(item.created_at).toLocaleDateString()}
                              </td>
                              <td className="py-3 text-slate-300 text-[11px]">
                                {item.reviewed_by || "—"}
                              </td>
                              <td className="py-3 text-right">
                                <button
                                  onClick={() => handleOpenReview(item)}
                                  className="rounded-lg border border-slate-700 bg-slate-800 px-2.5 py-1 text-[11px] font-sans font-semibold text-slate-200 hover:bg-slate-700"
                                >
                                  View Evidence
                                </button>
                              </td>
                            </tr>
                          ))
                        ) : (
                          <tr>
                            <td colSpan={10} className="py-6 text-center text-slate-500 font-sans">
                              No historical governed recommendations recorded.
                            </td>
                          </tr>
                        )}
                      </tbody>
                    </table>
                  </div>
                </div>
              </div>


            {reviewModalOpen && selectedRec && (
              <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-sm p-4 overflow-y-auto">
                <div className="w-full max-w-4xl rounded-3xl border border-slate-700 bg-slate-900 p-6 sm:p-8 space-y-6 shadow-2xl max-h-[90vh] overflow-y-auto">
                  {/* Modal Header */}
                  <div className="flex items-start justify-between border-b border-slate-800 pb-4">
                    <div>
                      <div className="flex items-center gap-2">
                        <span className="rounded bg-indigo-950 border border-indigo-700 px-2 py-0.5 text-[10px] font-bold uppercase text-indigo-300 font-mono">
                          {selectedRec.recommendation_id}
                        </span>
                        <span
                          className={`rounded-full border px-2 py-0.5 text-[10px] font-bold uppercase ${getRecommendationStatusBadge(
                            selectedRec.status
                          )}`}
                        >
                          {selectedRec.status.replace("_", " ")}
                        </span>
                      </div>
                      <h3 className="text-xl font-black text-white mt-1">
                        Governed Strategy Review: {selectedRec.strategy_type} ({selectedRec.retry_delay_hours}h Delay)
                      </h3>
                      <p className="text-xs text-slate-400">
                        Created: {new Date(selectedRec.created_at).toLocaleString()} • Expires: {new Date(selectedRec.expires_at).toLocaleString()}
                      </p>
                    </div>
                    <button
                      onClick={() => setReviewModalOpen(false)}
                      className="rounded-xl border border-slate-800 bg-slate-950 p-2 text-slate-400 hover:text-white"
                    >
                      <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M6 18L18 6M6 6l12 12" />
                      </svg>
                    </button>
                  </div>
    
                  {/* Notification Banner */}
                  {reviewSuccessMsg && (
                    <div className="rounded-xl border border-emerald-800/60 bg-emerald-950/40 p-4 text-xs text-emerald-300">
                      {reviewSuccessMsg}
                    </div>
                  )}
    
                  {/* Observational Notice inside modal */}
                  <div className="rounded-xl border border-slate-800 bg-slate-950 p-3 text-[11px] text-slate-400 leading-relaxed">
                    <span className="font-bold text-slate-300">Governance Notice:</span> Approving this recommendation records human operator review and endorses the strategy proposal. Approvals do NOT trigger automated dispatch or call external payment gateways.
                  </div>
    
                  {/* Evidence Breakdown Grid */}
                  <div className="space-y-4">
                    <h4 className="text-xs font-bold uppercase tracking-wider text-indigo-400">
                      Synthesized Evidence Trail (Phases 9A–9D)
                    </h4>
    
                    <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
                      {/* Phase 9A Evaluation Evidence */}
                      <div className="rounded-2xl border border-slate-800 bg-slate-950/60 p-4 space-y-3">
                        <div className="flex items-center justify-between border-b border-slate-800/80 pb-2">
                          <span className="text-[11px] font-bold text-white uppercase">
                            1. ML Intelligence (9A)
                          </span>
                          <span className="text-[10px] text-slate-400 font-mono">
                            {selectedRec.evidence.evaluation.sample_size} cases
                          </span>
                        </div>
                        <div className="grid grid-cols-2 gap-2 text-xs font-mono">
                          <div>
                            <span className="text-[10px] text-slate-400 block">Accuracy</span>
                            <span className="text-slate-200 font-bold">{formatPct(selectedRec.evidence.evaluation.accuracy)}</span>
                          </div>
                          <div>
                            <span className="text-[10px] text-slate-400 block">F1-Score</span>
                            <span className="text-slate-200 font-bold">{formatNum(selectedRec.evidence.evaluation.f1_score, 3)}</span>
                          </div>
                          <div>
                            <span className="text-[10px] text-slate-400 block">Brier Score</span>
                            <span className="text-slate-200 font-bold">{formatNum(selectedRec.evidence.evaluation.brier_score, 3)}</span>
                          </div>
                          <div>
                            <span className="text-[10px] text-slate-400 block">Precision / Recall</span>
                            <span className="text-slate-200 font-bold">{formatNum(selectedRec.evidence.evaluation.precision, 2)} / {formatNum(selectedRec.evidence.evaluation.recall, 2)}</span>
                          </div>
                        </div>
                      </div>
    
                      {/* Phase 9B Governance Evidence */}
                      <div className="rounded-2xl border border-slate-800 bg-slate-950/60 p-4 space-y-3">
                        <div className="flex items-center justify-between border-b border-slate-800/80 pb-2">
                          <span className="text-[11px] font-bold text-white uppercase">
                            2. Model Governance (9B)
                          </span>
                          <span className={`rounded px-1.5 py-0.2 text-[10px] font-bold uppercase border ${getStatusBadge(selectedRec.evidence.governance.model_health)}`}>
                            {selectedRec.evidence.governance.model_health}
                          </span>
                        </div>
                        <div className="grid grid-cols-2 gap-2 text-xs font-mono">
                          <div>
                            <span className="text-[10px] text-slate-400 block">Model Version</span>
                            <span className="text-slate-200 font-bold">{selectedRec.evidence.governance.model_version}</span>
                          </div>
                          <div>
                            <span className="text-[10px] text-slate-400 block">Prediction Drift (PSI)</span>
                            <span className="text-slate-200 font-bold">{formatNum(selectedRec.evidence.governance.prediction_psi, 3)} ({selectedRec.evidence.governance.drift_status})</span>
                          </div>
                          <div className="col-span-2">
                            <span className="text-[10px] text-slate-400 block">Data Quality</span>
                            <span className="text-emerald-400 font-bold">{selectedRec.evidence.governance.data_quality_status}</span>
                          </div>
                        </div>
                      </div>
    
                      {/* Phase 9C Optimization Evidence */}
                      <div className="rounded-2xl border border-slate-800 bg-slate-950/60 p-4 space-y-3">
                        <div className="flex items-center justify-between border-b border-slate-800/80 pb-2">
                          <span className="text-[11px] font-bold text-white uppercase">
                            3. Strategy Optimization (9C)
                          </span>
                          <span className="text-[10px] text-indigo-300 font-bold">
                            {selectedRec.evidence.optimization.champion_strategy || "—"}
                          </span>
                        </div>
                        <div className="grid grid-cols-2 gap-2 text-xs font-mono">
                          <div>
                            <span className="text-[10px] text-slate-400 block">Champion Rate</span>
                            <span className="text-emerald-400 font-bold">{formatPct(selectedRec.evidence.optimization.champion_recovery_rate)}</span>
                          </div>
                          <div>
                            <span className="text-[10px] text-slate-400 block">Champion ERV</span>
                            <span className="text-purple-300 font-bold">{selectedRec.evidence.optimization.champion_erv_paise ? formatINR(selectedRec.evidence.optimization.champion_erv_paise) : "—"}</span>
                          </div>
                        </div>
                      </div>
    
                      {/* Phase 9D Simulation Evidence */}
                      <div className="rounded-2xl border border-slate-800 bg-slate-950/60 p-4 space-y-3">
                        <div className="flex items-center justify-between border-b border-slate-800/80 pb-2">
                          <span className="text-[11px] font-bold text-white uppercase">
                            4. Counterfactual Simulation (9D)
                          </span>
                          <span className="text-[10px] text-slate-400 font-mono">
                            {selectedRec.evidence.simulation.comparable_population_size} matched cases
                          </span>
                        </div>
                        <div className="grid grid-cols-2 gap-2 text-xs font-mono">
                          <div>
                            <span className="text-[10px] text-slate-400 block">Simulated Rate Delta</span>
                            <span className="text-emerald-400 font-bold">{formatDelta(selectedRec.evidence.simulation.rate_delta)}</span>
                          </div>
                          <div>
                            <span className="text-[10px] text-slate-400 block">Incremental ERV</span>
                            <span className="text-emerald-300 font-bold">{selectedRec.evidence.simulation.incremental_erv_paise ? formatINR(selectedRec.evidence.simulation.incremental_erv_paise) : "—"}</span>
                          </div>
                        </div>
                      </div>
                    </div>
                  </div>
    
                  {/* Operator Review Controls */}
                  <div className="space-y-4 border-t border-slate-800 pt-4">
                    <label className="block text-xs font-bold uppercase tracking-wider text-slate-300">
                      Operator Decision & Review Notes
                    </label>
                    <textarea
                      value={reviewNotes}
                      onChange={(e) => setReviewNotes(e.target.value)}
                      disabled={selectedRec.status !== "REVIEW_REQUIRED"}
                      placeholder="Enter audit rationale for approval or rejection..."
                      rows={3}
                      className="w-full rounded-xl border border-slate-800 bg-slate-950 px-4 py-3 text-xs text-slate-200 focus:border-indigo-500 focus:outline-none"
                    />
    
                    {userRole === "viewer" ? (
                      <div className="rounded-xl border border-amber-800/60 bg-amber-950/30 p-3 text-xs text-amber-300">
                        Your session is currently authenticated with <strong>Viewer</strong> permissions (Read-Only). An <strong>Operator</strong> or <strong>Admin</strong> session is required to approve or reject recommendations.
                      </div>
                    ) : selectedRec.status === "REVIEW_REQUIRED" ? (
                      <div className="flex items-center justify-end gap-3 pt-2">
                        <button
                          onClick={handleReject}
                          disabled={reviewActionLoading}
                          className="rounded-xl border border-rose-800/80 bg-rose-950/50 px-6 py-2.5 text-xs font-bold uppercase tracking-wider text-rose-300 hover:bg-rose-900/60 disabled:opacity-50 transition"
                        >
                          Reject Strategy
                        </button>
                        <button
                          onClick={handleApprove}
                          disabled={reviewActionLoading}
                          className="rounded-xl bg-emerald-600 px-6 py-2.5 text-xs font-bold uppercase tracking-wider text-white shadow-lg shadow-emerald-600/30 hover:bg-emerald-500 disabled:opacity-50 transition"
                        >
                          {reviewActionLoading ? "Processing..." : "Approve Strategy"}
                        </button>
                      </div>
                    ) : (
                      <div className="rounded-xl border border-slate-800 bg-slate-950 p-3 text-xs text-slate-400 flex items-center justify-between">
                        <span>
                          Decision recorded by <strong>{selectedRec.reviewed_by || "system"}</strong> at{" "}
                          {selectedRec.reviewed_at ? new Date(selectedRec.reviewed_at).toLocaleString() : "—"}.
                        </span>
                        <span className={`rounded px-2 py-0.5 text-[10px] font-bold uppercase ${getRecommendationStatusBadge(selectedRec.status)}`}>
                          {selectedRec.status}
                        </span>
                      </div>
                    )}
                  </div>
                </div>
              </div>
            )}
    
            {/* Canary Staging Adjustment Modal */}


    </>
  );
}
