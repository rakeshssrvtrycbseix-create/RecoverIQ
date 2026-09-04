"use client";

import React, { useCallback, useEffect, useState } from "react";
import {
  PaginatedActivationsResponse,
  ProductionMonitoringResponse,
  PromotionReadinessResponse,
  fetchProductionMonitoring,
  fetchPromotionReadiness,
  fetchStrategyActivations,
  formatINR,
  promoteProductionStrategy
} from "../../lib/api";
import { formatDelta, formatNum, formatPct, getDriftBadge, getProductionStatusBadge } from "./intelligenceBadges";

interface ProductionMonitoringTabProps {
  actData?: PaginatedActivationsResponse | null;
  userRole?: string;
}

export default function ProductionMonitoringTab({
  actData,
  userRole = "ADMIN",
}: ProductionMonitoringTabProps) {
  const [internalActData, setInternalActData] = useState<PaginatedActivationsResponse | null>(null);
  void (actData || internalActData);
  const [error, setError] = useState<string | null>(null);

    const [prodData, setProdData] = useState<ProductionMonitoringResponse | null>(null);
    const [readinessData, setReadinessData] = useState<PromotionReadinessResponse | null>(null);
    const [prodPromoteModalOpen, setProdPromoteModalOpen] = useState(false);
    const [prodPromoteReason, setProdPromoteReason] = useState("");
    const [prodActionLoading, setProdActionLoading] = useState(false);
    const [prodSuccessMsg, setProdSuccessMsg] = useState<string | null>(null);
  

    const handlePromoteToProduction = async (activationId: string) => {
      setProdActionLoading(true);
      setError(null);
      try {
        await promoteProductionStrategy(activationId, prodPromoteReason || undefined);
        setProdPromoteModalOpen(false);
        setProdSuccessMsg("Strategy successfully PROMOTED to 100% full PRODUCTION rollout.");
        await loadProdData();
      } catch (err) {
        setError(err instanceof Error ? err.message : "Failed to promote strategy to production");
      } finally {
        setProdActionLoading(false);
      }
    };
  
  
  
  

  const loadProdData = useCallback(async () => {
    try {
      const [pRes, aRes] = await Promise.all([
        fetchProductionMonitoring().catch(() => null),
        !actData ? fetchStrategyActivations().catch(() => null) : Promise.resolve(actData),
      ]);
      setProdData(pRes);
      if (!actData && aRes) {
        setInternalActData(aRes);
      }
      const activeActivationId = aRes?.active_activation?.activation_id;
      if (activeActivationId) {
        const rRes = await fetchPromotionReadiness(activeActivationId).catch(() => null);
        setReadinessData(rRes);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load Production Monitoring");
    }
  }, [actData]);

    useEffect(() => {
    let ignore = false;
    async function execute() {
      if (!ignore) {
        await loadProdData();
      }
    }
    void execute();
    return () => {
      ignore = true;
    };
  }, [loadProdData]);

  return (
    <>
      {error && (
        <div className="rounded-xl border border-rose-800/40 bg-rose-950/40 p-4 text-xs text-rose-300">
          {error}
        </div>
      )}

      {prodSuccessMsg && (
        <div className="rounded-xl border border-emerald-800/60 bg-emerald-950/40 p-4 text-xs text-emerald-300 flex items-center justify-between shadow-lg">
          <span>{prodSuccessMsg}</span>
          <button onClick={() => setProdSuccessMsg(null)} className="text-emerald-400 hover:text-white font-bold ml-4">✕</button>
        </div>
      )}
              {/* =========================================================================
                 TAB 0: PRODUCTION STRATEGY PROMOTION & CONTINUOUS MONITORING (Phase 9G)
                 ========================================================================= */}
    
              <div className="space-y-8">
                {/* Mandatory Observational & Governance Disclaimer Banner */}
                <div className="rounded-2xl border border-indigo-800/60 bg-indigo-950/20 p-4 flex items-start gap-3">
                  <span className="rounded bg-indigo-900/80 px-2 py-0.5 text-[10px] font-bold uppercase tracking-wider text-indigo-200 border border-indigo-700/60 shrink-0">
                    PRODUCTION GOVERNANCE
                  </span>
                  <div className="text-xs text-indigo-200/90 leading-relaxed space-y-1">
                    <p className="font-semibold">
                      PRODUCTION STRATEGY LIFECYCLE & CONTINUOUS MONITORING (PHASE 9G)
                    </p>
                    <p className="text-[11px] text-indigo-300/80">
                      Continuous telemetry tracks empirical recovery rates, model calibration, drift, and financial yields. Strategy promotion requires passing 8 deterministic safety gates evaluated server-side. The authoritative Policy Engine enforces all financial boundaries. Promotion does NOT execute payments or bypass human authority.
                    </p>
                  </div>
                </div>
    
                {/* Rollback Safety Recommendation Alert Banner */}
                {(prodData?.rollback_recommended || prodData?.status === "ROLLBACK_RECOMMENDED") && (
                  <div className="rounded-2xl border border-rose-800/80 bg-rose-950/40 p-4 flex items-start gap-3 animate-pulse">
                    <span className="rounded bg-rose-900/90 px-2.5 py-1 text-[10px] font-black uppercase tracking-wider text-rose-200 border border-rose-700/80 shrink-0">
                      ROLLBACK RECOMMENDED
                    </span>
                    <div className="text-xs text-rose-200 leading-relaxed space-y-1">
                      <p className="font-bold text-rose-300">
                        Critical Safety Alert: Production Performance Regression Detected
                      </p>
                      <p className="text-[11px] text-rose-300/90">
                        Production recovery performance has deteriorated relative to the control baseline by &ge; 5.0 percentage points, or the underlying ML model is degraded. Human operator/admin review is required.
                      </p>
                    </div>
                  </div>
                )}
    
                {/* Active Production Strategy Card */}
                <div className="rounded-3xl border border-slate-800 bg-slate-900/90 p-6 sm:p-8 space-y-6 shadow-2xl">
                  <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between border-b border-slate-800 pb-6">
                    <div>
                      <div className="flex items-center gap-3">
                        <span className="text-xs font-mono font-bold text-indigo-400">
                          {prodData?.strategy_id || "PROD-NONE"}
                        </span>
                        <span className={`rounded-full border px-2.5 py-0.5 text-[10px] font-bold uppercase ${getProductionStatusBadge(prodData?.status || "NO_ACTIVE_STRATEGY")}`}>
                          {prodData?.status || "NO_ACTIVE_STRATEGY"}
                        </span>
                        <span className="rounded-full bg-slate-800 px-2.5 py-0.5 text-[10px] font-mono font-bold text-slate-300 border border-slate-700">
                          Rollout: {prodData?.rollout_percentage || 0}%
                        </span>
                      </div>
                      <h2 className="text-2xl font-black text-white mt-2">
                        {prodData?.strategy_name || "No Active Production Strategy"}
                      </h2>
                      <p className="text-xs text-slate-400">
                        Strategy Version: <strong className="text-slate-300">{prodData?.strategy_version || "strategy-v1.0"}</strong> • Governing Model: <strong className="text-slate-300">{prodData?.model_version || "v1.0"}</strong> • Activation: <span className="font-mono text-indigo-300">{prodData?.activation_id || "—"}</span>
                      </p>
                    </div>
    
                    <div className="text-right text-xs font-mono text-slate-400 space-y-1">
                      <div>Promoted At: <span className="text-slate-200">{prodData?.promoted_at ? new Date(prodData.promoted_at).toLocaleString() : "—"}</span></div>
                      <div>Promoted By: <span className="text-slate-200">{prodData?.promoted_by || "system"}</span></div>
                      <div>Last Evaluated: <span className="text-slate-200">{prodData?.last_evaluated ? new Date(prodData.last_evaluated).toLocaleTimeString() : "—"}</span></div>
                    </div>
                  </div>
    
                  {/* 7 Production KPI Cards */}
                  <div className="grid grid-cols-2 gap-4 sm:grid-cols-4 lg:grid-cols-7">
                    <div className="rounded-2xl border border-slate-800 bg-slate-950/60 p-4">
                      <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider block">Production Rate</span>
                      <span className="text-lg font-black text-emerald-400 font-mono mt-1 block">
                        {formatPct(prodData?.recovery_rate ?? null)}
                      </span>
                      <span className="text-[10px] text-slate-400">Treatment cohort</span>
                    </div>
    
                    <div className="rounded-2xl border border-slate-800 bg-slate-950/60 p-4">
                      <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider block">Control Baseline</span>
                      <span className="text-lg font-black text-slate-300 font-mono mt-1 block">
                        {formatPct(prodData?.control_recovery_rate ?? null)}
                      </span>
                      <span className="text-[10px] text-slate-400">Control cohort</span>
                    </div>
    
                    <div className="rounded-2xl border border-slate-800 bg-slate-950/60 p-4">
                      <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider block">Recovery Uplift</span>
                      <span className={`text-lg font-black font-mono mt-1 block ${(prodData?.absolute_uplift ?? 0) >= 0 ? "text-emerald-400" : "text-rose-400"}`}>
                        {formatDelta(prodData?.absolute_uplift ?? null)}
                      </span>
                      <span className="text-[10px] text-slate-400">
                        {prodData?.relative_uplift_pct !== null && prodData?.relative_uplift_pct !== undefined ? `${prodData.relative_uplift_pct > 0 ? "+" : ""}${prodData.relative_uplift_pct}% rel` : "—"}
                      </span>
                    </div>
    
                    <div className="rounded-2xl border border-purple-800/40 bg-purple-950/20 p-4">
                      <span className="text-[10px] font-bold text-purple-300 uppercase tracking-wider block">Incremental ERV</span>
                      <span className="text-lg font-black text-purple-300 font-mono mt-1 block">
                        {prodData?.incremental_erv_paise ? formatINR(prodData.incremental_erv_paise) : "—"}
                      </span>
                      <span className="text-[10px] text-purple-400/80">Integer paise</span>
                    </div>
    
                    <div className="rounded-2xl border border-slate-800 bg-slate-950/60 p-4">
                      <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider block">Financial Yield</span>
                      <span className="text-lg font-black text-slate-200 font-mono mt-1 block">
                        {formatPct(prodData?.financial_yield ?? null)}
                      </span>
                      <span className="text-[10px] text-slate-400">Recovered / Risk</span>
                    </div>
    
                    <div className="rounded-2xl border border-slate-800 bg-slate-950/60 p-4">
                      <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider block">Mean MTTR</span>
                      <span className="text-lg font-black text-slate-200 font-mono mt-1 block">
                        {prodData?.mttr_hours !== null && prodData?.mttr_hours !== undefined ? `${prodData.mttr_hours} hrs` : "—"}
                      </span>
                      <span className="text-[10px] text-slate-400">Time to resolution</span>
                    </div>
    
                    <div className="rounded-2xl border border-slate-800 bg-slate-950/60 p-4">
                      <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider block">Cohort Sample</span>
                      <span className="text-lg font-black text-white font-mono mt-1 block">
                        {prodData?.sample_size || 0}
                      </span>
                      <span className="text-[10px] text-slate-400">
                        T:{prodData?.treatment_sample_size || 0} • C:{prodData?.control_sample_size || 0}
                      </span>
                    </div>
                  </div>
                </div>
    
                {/* Promotion Readiness Assessment (8 Safety Gates) */}
                <div className="rounded-3xl border border-slate-800 bg-slate-900 p-6 sm:p-8 space-y-6 shadow-2xl">
                  <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between border-b border-slate-800 pb-4">
                    <div>
                      <h3 className="text-lg font-bold text-white">
                        Production Promotion Gate & Readiness Assessment
                      </h3>
                      <p className="text-xs text-slate-400">
                        Deterministic verification of all 8 safety criteria before 100% production promotion.
                      </p>
                    </div>
    
                    {readinessData && (
                      <span className={`rounded-full border px-3 py-1 text-xs font-mono font-bold uppercase tracking-wider ${
                        readinessData.eligible
                          ? "bg-emerald-950/80 border-emerald-700/60 text-emerald-300"
                          : "bg-rose-950/80 border-rose-700/60 text-rose-300"
                      }`}>
                        {readinessData.status.replace("_", " ")}
                      </span>
                    )}
                  </div>
    
                  {readinessData ? (
                    <div className="space-y-6">
                      {/* 8 Checks Grid */}
                      <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-4">
                        {readinessData.checks.map((c) => (
                          <div
                            key={c.rule}
                            className={`rounded-2xl border p-4 transition ${
                              c.passed
                                ? "border-emerald-800/40 bg-emerald-950/10"
                                : "border-rose-800/40 bg-rose-950/20"
                            }`}
                          >
                            <div className="flex items-center justify-between">
                              <span className="text-[10px] font-mono font-bold uppercase tracking-wider text-slate-400">
                                {c.rule}
                              </span>
                              <span className={`text-xs font-bold ${c.passed ? "text-emerald-400" : "text-rose-400"}`}>
                                {c.passed ? "✓ PASS" : "✗ BLOCKED"}
                              </span>
                            </div>
                            <div className="mt-2 text-xs font-mono text-white">
                              Observed: <strong className={c.passed ? "text-emerald-300" : "text-rose-300"}>{String(c.value ?? "N/A")}</strong>
                            </div>
                            <div className="text-[10px] text-slate-400 mt-0.5">
                              Req: {String(c.required ?? "N/A")}
                            </div>
                            <p className="text-[11px] text-slate-400 mt-2 line-clamp-2">{c.message}</p>
                          </div>
                        ))}
                      </div>
    
                      {/* Blockers Summary */}
                      {readinessData.blockers.length > 0 && (
                        <div className="rounded-2xl border border-rose-800/60 bg-rose-950/30 p-4 space-y-2">
                          <span className="text-xs font-bold uppercase tracking-wider text-rose-300 font-mono">
                            Active Promotion Blockers ({readinessData.blockers.length})
                          </span>
                          <div className="flex flex-wrap gap-2">
                            {readinessData.blockers.map((b) => (
                              <span key={b} className="rounded-lg bg-rose-900/60 border border-rose-700/60 px-2.5 py-1 text-[11px] font-mono font-bold text-rose-200">
                                {b}
                              </span>
                            ))}
                          </div>
                        </div>
                      )}
    
                      {/* Promotion Controls */}
                      <div className="flex flex-col sm:flex-row items-center justify-between gap-4 border-t border-slate-800 pt-4">
                        <div className="text-xs text-slate-400">
                          {userRole === "viewer" ? (
                            <span>Viewer session: Read-only promotion readiness view.</span>
                          ) : userRole === "operator" ? (
                            <span>Operator session: Promotion readiness verified. <strong>Admin role</strong> required for full 100% production promotion.</span>
                          ) : (
                            <span>Admin session: Authorized to execute 100% production promotion upon passing all gates.</span>
                          )}
                        </div>
    
                        {userRole === "admin" && (
                          <button
                            type="button"
                            onClick={() => setProdPromoteModalOpen(true)}
                            disabled={!readinessData.eligible || prodActionLoading}
                            className="rounded-xl bg-emerald-600 px-6 py-2.5 text-xs font-bold uppercase tracking-wider text-white hover:bg-emerald-500 shadow-lg shadow-emerald-600/30 transition disabled:opacity-50 disabled:cursor-not-allowed"
                          >
                            {prodActionLoading ? "Promoting..." : "Promote to Production (100%)"}
                          </button>
                        )}
                      </div>
                    </div>
                  ) : (
                    <div className="rounded-2xl border border-slate-800 bg-slate-950/40 p-6 text-center text-xs text-slate-400">
                      No active canary activation currently eligible for promotion evaluation. Start a controlled rollout in the <strong>Controlled Rollout</strong> tab first.
                    </div>
                  )}
                </div>
    
                {/* Continuous Diagnostics & Model Health Panel */}
                <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
                  <div className="rounded-3xl border border-slate-800 bg-slate-900 p-6 space-y-4">
                    <span className="text-xs font-mono font-bold uppercase tracking-wider text-slate-400">
                      Governing Model & Drift Telemetry
                    </span>
                    <div className="grid grid-cols-2 gap-3 text-xs font-mono">
                      <div className="rounded-xl border border-slate-800 bg-slate-950 p-3">
                        <span className="text-[10px] text-slate-400 block">Model Health</span>
                        <strong className="text-white">{prodData?.model_health || "UNKNOWN"}</strong>
                      </div>
                      <div className="rounded-xl border border-slate-800 bg-slate-950 p-3">
                        <span className="text-[10px] text-slate-400 block">Prediction PSI Drift</span>
                        <strong className="text-white">
                          {prodData?.prediction_psi !== null && prodData?.prediction_psi !== undefined ? formatNum(prodData.prediction_psi, 3) : "—"}{" "}
                          <span className={`text-[10px] ml-1 ${getDriftBadge(prodData?.drift_status || "LOW")}`}>
                            ({prodData?.drift_status || "LOW"})
                          </span>
                        </strong>
                      </div>
                    </div>
                  </div>
    
                  <div className="rounded-3xl border border-slate-800 bg-slate-900 p-6 space-y-3">
                    <span className="text-xs font-mono font-bold uppercase tracking-wider text-slate-400">
                      Continuous Safety Diagnostics
                    </span>
                    <ul className="list-disc list-inside text-xs text-slate-300 space-y-1.5 font-mono">
                      {prodData?.diagnostics && prodData.diagnostics.length > 0 ? (
                        prodData.diagnostics.map((d, i) => (
                          <li key={i} className="text-slate-300">{d}</li>
                        ))
                      ) : (
                        <li className="text-slate-500">No active safety alerts.</li>
                      )}
                    </ul>
                  </div>
                </div>
              </div>


            {prodPromoteModalOpen && actData?.active_activation && (
              <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-sm p-4">
                <div className="w-full max-w-lg rounded-3xl border border-slate-800 bg-slate-900 p-6 sm:p-8 space-y-6 shadow-2xl">
                  <div className="flex items-start justify-between border-b border-slate-800 pb-4">
                    <div>
                      <span className="rounded bg-emerald-950 px-2 py-0.5 text-[10px] font-bold uppercase tracking-wider text-emerald-300 border border-emerald-700/60">
                        ADMIN ACTION (PHASE 9G)
                      </span>
                      <h3 className="text-xl font-black text-white mt-1">
                        Promote Strategy to 100% Production
                      </h3>
                      <p className="text-xs text-slate-400">
                        Promote <strong className="text-white">{actData.active_activation.strategy_type}</strong> to full production rollout.
                      </p>
    
                    </div>
                    <button
                      onClick={() => setProdPromoteModalOpen(false)}
                      className="rounded-xl border border-slate-800 bg-slate-950 p-2 text-slate-400 hover:text-white"
                    >
                      <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M6 18L18 6M6 6l12 12" />
                      </svg>
                    </button>
                  </div>
    
                  <div className="space-y-4">
                    <div className="grid grid-cols-2 gap-3 text-xs font-mono">
                      <div className="rounded-xl border border-slate-800 bg-slate-950 p-3">
                        <span className="text-[10px] text-slate-400 block">Observed Uplift</span>
                        <strong className="text-emerald-400">{formatDelta(readinessData?.absolute_uplift ?? null)}</strong>
                      </div>
                      <div className="rounded-xl border border-slate-800 bg-slate-950 p-3">
                        <span className="text-[10px] text-slate-400 block">Sample Size</span>
                        <strong className="text-white">{readinessData?.sample_size || 0} cases</strong>
                      </div>
                      <div className="rounded-xl border border-slate-800 bg-slate-950 p-3">
                        <span className="text-[10px] text-slate-400 block">Incremental ERV</span>
                        <strong className="text-purple-300">
                          {readinessData?.incremental_erv_paise ? formatINR(readinessData.incremental_erv_paise) : "—"}
                        </strong>
                      </div>
                      <div className="rounded-xl border border-slate-800 bg-slate-950 p-3">
                        <span className="text-[10px] text-slate-400 block">Model Health</span>
                        <strong className="text-emerald-300">{readinessData?.model_health || "HEALTHY"}</strong>
                      </div>
                    </div>
    
                    <div>
                      <label className="text-xs font-bold text-slate-300 block mb-1">
                        Promotion Audit Reason
                      </label>
                      <textarea
                        value={prodPromoteReason}
                        onChange={(e) => setProdPromoteReason(e.target.value)}
                        placeholder="e.g., Empirical canary verification completed with statistically significant positive uplift."
                        rows={3}
                        className="w-full rounded-xl border border-slate-800 bg-slate-950 px-3 py-2 text-xs text-slate-200 placeholder-slate-600 focus:border-indigo-500 focus:outline-none"
                      />
                    </div>
    
                    <div className="rounded-xl border border-emerald-800/40 bg-emerald-950/20 p-3 text-[11px] text-emerald-200/90 leading-relaxed">
                      ✓ Promotion updates the governance state to 100% production traffic allocation. Zero RecoveryActions created, zero Payment status mutated, zero gateway calls made.
                    </div>
                  </div>
    
                  <div className="flex items-center justify-end gap-3 border-t border-slate-800 pt-4">
                    <button
                      type="button"
                      onClick={() => setProdPromoteModalOpen(false)}
                      className="rounded-xl border border-slate-800 bg-slate-950 px-4 py-2 text-xs font-bold uppercase tracking-wider text-slate-400 hover:text-white transition"
                    >
                      Cancel
                    </button>
                    <button
                      type="button"
                      onClick={() => handlePromoteToProduction(actData.active_activation!.activation_id)}
                      disabled={prodActionLoading}
                      className="rounded-xl bg-emerald-600 px-6 py-2 text-xs font-bold uppercase tracking-wider text-white hover:bg-emerald-500 shadow-lg shadow-emerald-600/30 transition disabled:opacity-50"
                    >
                      {prodActionLoading ? "Promoting..." : "Confirm 100% Production Promotion"}
                    </button>
                  </div>
                </div>
              </div>
            )}
    
            {/* Modal: Create Causal Experiment (Phase 9H Operator/Admin) */}


    </>
  );
}
