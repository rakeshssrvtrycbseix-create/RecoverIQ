"use client";

import React, { useCallback, useEffect, useState } from "react";
import {
  PaginatedDeploymentsResponse,
  PaginatedModelsResponse,
  ShadowAnalysisResponse,
  activateModelDeployment,
  createModelDeployment,
  fetchModelDeployments,
  fetchModels,
  fetchShadowAnalysis,
  pauseModelDeployment,
  rollbackModelDeployment,
  setCanaryRollout,
  startShadowMode
} from "../../lib/api";
import { getDeploymentReadinessDecisionBadge, getDeploymentSignificanceBadge, getDeploymentStatusBadge } from "./intelligenceBadges";

interface ModelDeploymentTabProps {
  modelsData?: PaginatedModelsResponse | null;
}

export default function ModelDeploymentTab({ modelsData }: ModelDeploymentTabProps) {
  const [internalModelsData, setInternalModelsData] = useState<PaginatedModelsResponse | null>(null);
  void (modelsData || internalModelsData);
  const [error, setError] = useState<string | null>(null);

    const [deploymentsData, setDeploymentsData] = useState<PaginatedDeploymentsResponse | null>(null);
    const [selectedDeploymentId, setSelectedDeploymentId] = useState<string | null>(null);
    const [selectedShadowAnalysis, setSelectedShadowAnalysis] = useState<ShadowAnalysisResponse | null>(null);
    const [deploymentLoading, setDeploymentLoading] = useState(false);
    const [deploymentStatusFilter, setDeploymentStatusFilter] = useState<string>("ALL");
    const [createDeploymentModalOpen, setCreateDeploymentModalOpen] = useState(false);
    const [createDepChallengerVersion, setCreateDepChallengerVersion] = useState("");
    const [createDepNotes, setCreateDepNotes] = useState("");
    const [shadowModalOpen, setShadowModalOpen] = useState(false);
    const [shadowPercentage, setShadowPercentage] = useState<number>(100);
    const [depCanaryModalOpen, setDepCanaryModalOpen] = useState(false);
    const [depCanaryPercentage, setDepCanaryPercentage] = useState<number>(10);
    const [depActivateModalOpen, setDepActivateModalOpen] = useState(false);
    const [depActivateNotes, setDepActivateNotes] = useState("");
    const [depRollbackModalOpen, setDepRollbackModalOpen] = useState(false);
    const [depRollbackReason, setDepRollbackReason] = useState("");
    const [depRollbackNotes, setDepRollbackNotes] = useState("");
    const [deploymentActionLoading, setDeploymentActionLoading] = useState(false);
    const [deploymentSuccessMsg, setDeploymentSuccessMsg] = useState<string | null>(null);
  

    const loadDeploymentAnalysis = async (deploymentId: string) => {
  
      setDeploymentLoading(true);
      try {
        const analysis = await fetchShadowAnalysis(deploymentId);
        setSelectedShadowAnalysis(analysis);
        setSelectedDeploymentId(deploymentId);
      } catch (err) {
        console.error("Failed to load shadow analysis", err);
      } finally {
        setDeploymentLoading(false);
      }
    };
  
    const handleCreateDeployment = async () => {
      if (!createDepChallengerVersion) return;
      setDeploymentActionLoading(true);
      setError(null);
      try {
        const created = await createModelDeployment({
          challenger_version: createDepChallengerVersion,
          champion_version: "v1.0",
          notes: createDepNotes || undefined,
        });
        setCreateDeploymentModalOpen(false);
        setDeploymentSuccessMsg(`Deployment created for challenger "${created.challenger_version}". Status: SHADOW (0% traffic).`);
        await loadDeploymentsData();
        await loadDeploymentAnalysis(created.deployment_id);
      } catch (err) {
        setError(err instanceof Error ? err.message : "Failed to create model deployment");
      } finally {
        setDeploymentActionLoading(false);
      }
    };
  
    const handleStartShadow = async () => {
      if (!selectedDeploymentId) return;
      setDeploymentActionLoading(true);
      setError(null);
      try {
        const updated = await startShadowMode(selectedDeploymentId, shadowPercentage);
        setShadowModalOpen(false);
        setDeploymentSuccessMsg(`Shadow mode traffic allocation set to ${updated.traffic_allocation_percentage}%.`);
        await loadDeploymentsData();
        await loadDeploymentAnalysis(selectedDeploymentId);
      } catch (err) {
        setError(err instanceof Error ? err.message : "Failed to adjust shadow traffic");
      } finally {
        setDeploymentActionLoading(false);
      }
    };
  
    const handlePauseDeployment = async () => {
      if (!selectedDeploymentId) return;
      setDeploymentActionLoading(true);
      setError(null);
      try {
        const updated = await pauseModelDeployment(selectedDeploymentId);
        setDeploymentSuccessMsg(`Deployment "${updated.deployment_id}" PAUSED.`);
        await loadDeploymentsData();
        await loadDeploymentAnalysis(selectedDeploymentId);
      } catch (err) {
        setError(err instanceof Error ? err.message : "Failed to pause deployment");
      } finally {
        setDeploymentActionLoading(false);
      }
    };
  
    const handleSetCanary = async () => {
      if (!selectedDeploymentId) return;
      setDeploymentActionLoading(true);
      setError(null);
      try {
        const updated = await setCanaryRollout(selectedDeploymentId, depCanaryPercentage);
        setDepCanaryModalOpen(false);
        setDeploymentSuccessMsg(`Canary rollout set to ${updated.traffic_allocation_percentage}%. Candidate in CANARY validation mode.`);
        await loadDeploymentsData();
        await loadDeploymentAnalysis(selectedDeploymentId);
      } catch (err) {
        setError(err instanceof Error ? err.message : "Failed to set canary rollout");
      } finally {
        setDeploymentActionLoading(false);
      }
    };
  
    const handleActivateDeployment = async () => {
      if (!selectedDeploymentId) return;
      setDeploymentActionLoading(true);
      setError(null);
      try {
        const updated = await activateModelDeployment(selectedDeploymentId, depActivateNotes || undefined);
        setDepActivateModalOpen(false);
        setDeploymentSuccessMsg(`Admin activated deployment "${updated.deployment_id}". Model "${updated.challenger_version}" is now the ACTIVE Champion! (Zero financial mutations executed)`);
        await loadDeploymentsData();
        await loadDeploymentAnalysis(selectedDeploymentId);
      } catch (err) {
        setError(err instanceof Error ? err.message : "Failed to activate model deployment");
      } finally {
        setDeploymentActionLoading(false);
      }
    };
  
    const handleRollbackDeployment = async () => {
      if (!selectedDeploymentId || !depRollbackReason) return;
      setDeploymentActionLoading(true);
      setError(null);
      try {
        const updated = await rollbackModelDeployment(selectedDeploymentId, depRollbackReason, depRollbackNotes || undefined);
        setDepRollbackModalOpen(false);
        setDeploymentSuccessMsg(`Admin rolled back deployment "${updated.deployment_id}". Active Champion restored!`);
        await loadDeploymentsData();
        await loadDeploymentAnalysis(selectedDeploymentId);
      } catch (err) {
        setError(err instanceof Error ? err.message : "Failed to rollback model deployment");
      } finally {
        setDeploymentActionLoading(false);
      }
    };

  const loadDeploymentsData = useCallback(async () => {
    try {
      const res = await fetchModelDeployments();
      setDeploymentsData(res);
      if (res && res.items && res.items.length > 0 && !selectedDeploymentId) {
        setSelectedDeploymentId(res.items[0].deployment_id);
        loadDeploymentAnalysis(res.items[0].deployment_id);
      }
      if (!modelsData) {
        const mRes = await fetchModels().catch(() => null);
        setInternalModelsData(mRes);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load Model Deployments");
    }
  }, [selectedDeploymentId, modelsData]);

    useEffect(() => {
    let ignore = false;
    async function execute() {
      if (!ignore) {
        await loadDeploymentsData();
      }
    }
    void execute();
    return () => {
      ignore = true;
    };
  }, [loadDeploymentsData]);

  return (
    <>
      {error && (
        <div className="rounded-xl border border-rose-800/40 bg-rose-950/40 p-4 text-xs text-rose-300">
          {error}
        </div>
      )}

      {deploymentSuccessMsg && (
        <div className="rounded-xl border border-emerald-800/60 bg-emerald-950/40 p-4 text-xs text-emerald-300 flex items-center justify-between shadow-lg">
          <span>{deploymentSuccessMsg}</span>
          <button onClick={() => setDeploymentSuccessMsg(null)} className="text-emerald-400 hover:text-white font-bold ml-4">✕</button>
        </div>
      )}
              {/* =========================================================================
                 TAB 0: GOVERNED MODEL DEPLOYMENT & SHADOW MODE (Phase 9J)
                 ========================================================================= */}
              <div className="space-y-8">
                {/* Mandatory Governance & Zero Financial Mutation Banner */}
                <div className="rounded-2xl border border-cyan-800/60 bg-cyan-950/20 p-4 flex items-start gap-3">
                  <span className="rounded bg-cyan-900/80 px-2 py-0.5 text-[10px] font-bold uppercase tracking-wider text-cyan-200 border border-cyan-700/60 shrink-0">
    
                    PHASE 9J SHADOW VALIDATION
                  </span>
                  <div className="text-xs text-cyan-200/90 leading-relaxed space-y-1">
                    <p className="font-semibold">
                      GOVERNED MODEL DEPLOYMENT, SHADOW MODE & CHAMPION–CHALLENGER PRODUCTION VALIDATION
                    </p>
                    <p className="text-[11px] text-cyan-300/80">
                      Authoritative multi-stage model rollout for RecoverIQ. Challenger models are evaluated against live production traffic in passive shadow mode or controlled canary staging using deterministic SHA-256 case hashing. Validation is strictly gated across 14 deterministic deployment readiness safety gates. Challenger models NEVER execute financial actions independently; the authoritative flow remains: ML Model → Prediction → Decision Intelligence → PolicyEngine → RecoveryAction → Execution.
                    </p>
                  </div>
                </div>
    
                {/* Quick Metrics Bar & Action Header */}
                <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
                  <div className="flex flex-wrap items-center gap-3">
                    <div className="rounded-xl border border-slate-800 bg-slate-900/80 px-4 py-2 text-xs font-mono">
                      <span className="text-[10px] text-slate-500 uppercase block font-bold">Active Champion</span>
                      <strong className="text-emerald-400 text-sm">{deploymentsData?.active_champion_version || "v1.0"}</strong>
                    </div>
    
                    <div className="rounded-xl border border-slate-800 bg-slate-900/80 px-4 py-2 text-xs font-mono">
                      <span className="text-[10px] text-slate-500 uppercase block font-bold">Deployments Count</span>
                      <strong className="text-white text-sm">{deploymentsData?.total || 0}</strong>
                    </div>
    
                    {selectedShadowAnalysis && (
                      <div className="rounded-xl border border-slate-800 bg-slate-900/80 px-4 py-2 text-xs font-mono">
                        <span className="text-[10px] text-slate-500 uppercase block font-bold">Selected Traffic Allocation</span>
                        <strong className="text-cyan-400 text-sm">
                          {selectedShadowAnalysis.traffic_allocation_percentage}% ({selectedShadowAnalysis.status})
                        </strong>
                      </div>
                    )}
    
                    {selectedShadowAnalysis && (
                      <div className="rounded-xl border border-slate-800 bg-slate-900/80 px-4 py-2 text-xs font-mono">
                        <span className="text-[10px] text-slate-500 uppercase block font-bold">Evaluated Cases</span>
                        <strong className="text-purple-400 text-sm">{selectedShadowAnalysis.sample_size}</strong>
                      </div>
                    )}
                  </div>
    
                  <div className="flex items-center gap-3">
                    <button
                      onClick={() => setCreateDeploymentModalOpen(true)}
                      className="flex items-center gap-2 rounded-xl bg-cyan-600 px-4 py-2 text-xs font-bold uppercase tracking-wider text-white hover:bg-cyan-500 shadow-lg shadow-cyan-600/30 transition"
                    >
                      <span>+ New Deployment</span>
                    </button>
                  </div>
                </div>
    
                {/* 2-Column Responsive Layout */}
                <div className="grid grid-cols-1 gap-8 lg:grid-cols-12">
                  {/* Left Column: Deployments List (Col 4) */}
                  <div className="lg:col-span-4 space-y-4">
                    <div className="flex items-center justify-between">
                      <h2 className="text-xs font-bold uppercase tracking-wider text-slate-400">
                        Deployments Registry
                      </h2>
                      <span className="text-[11px] font-mono text-slate-500">
                        {deploymentsData?.items.length || 0} total
                      </span>
                    </div>
    
                    {/* Status Filter Tabs */}
                    <div className="flex flex-wrap gap-1 rounded-xl bg-slate-900 p-1 border border-slate-800 text-[11px]">
                      {["ALL", "SHADOW", "CANARY", "ACTIVE", "PAUSED", "RETIRED"].map((status) => (
                        <button
                          key={status}
                          onClick={() => setDeploymentStatusFilter(status)}
                          className={`rounded-lg px-2.5 py-1 font-semibold transition ${
                            deploymentStatusFilter === status
                              ? "bg-slate-800 text-cyan-300 font-bold"
                              : "text-slate-500 hover:text-slate-300"
                          }`}
                        >
                          {status}
                        </button>
                      ))}
                    </div>
    
                    {/* Deployment Cards List */}
                    <div className="space-y-2.5 max-h-[850px] overflow-y-auto pr-1">
                      {!deploymentsData || deploymentsData.items.length === 0 ? (
                        <div className="rounded-2xl border border-slate-800/80 bg-slate-900/40 p-6 text-center text-xs text-slate-500">
                          No deployments found. Click &quot;+ New Deployment&quot; to launch shadow mode validation.
                        </div>
                      ) : (
                        deploymentsData.items
                          .filter((dep) => deploymentStatusFilter === "ALL" || dep.status === deploymentStatusFilter)
                          .map((dep) => {
                            const isSelected = selectedDeploymentId === dep.deployment_id;
                            return (
                              <div
                                key={dep.deployment_id}
                                onClick={() => loadDeploymentAnalysis(dep.deployment_id)}
                                className={`cursor-pointer rounded-2xl border p-4 transition ${
                                  isSelected
                                    ? "border-cyan-500/80 bg-cyan-950/20 shadow-lg shadow-cyan-950/50"
                                    : "border-slate-800/80 bg-slate-900/40 hover:border-slate-700 hover:bg-slate-900/80"
                                }`}
                              >
                                <div className="flex items-center justify-between mb-2">
                                  <span className="font-mono text-xs font-bold text-white flex items-center gap-1.5">
                                    <span className="text-slate-400 font-normal">Candidate:</span> {dep.challenger_version}
                                  </span>
                                  <span
                                    className={`rounded-full border px-2 py-0.5 text-[10px] font-mono font-bold uppercase tracking-wider ${getDeploymentStatusBadge(
                                      dep.status
                                    )}`}
                                  >
                                    {dep.status}
                                  </span>
                                </div>
    
                                <div className="flex items-center justify-between text-[11px] text-slate-400 font-mono">
                                  <span>Champion: <strong className="text-slate-300">{dep.champion_version}</strong></span>
                                  <span className="text-cyan-400 font-bold">{dep.traffic_allocation_percentage}% traffic</span>
                                </div>
    
                                <div className="mt-2.5 flex items-center justify-between border-t border-slate-800/60 pt-2 text-[10px] text-slate-500">
                                  <span>ID: {dep.deployment_id.slice(0, 8)}...</span>
                                  <span>{new Date(dep.created_at).toLocaleDateString()}</span>
                                </div>
                              </div>
                            );
                          })
                      )}
                    </div>
                  </div>
    
                  {/* Right Column: Detailed Shadow Analysis Dashboard (Col 8) */}
                  <div className="lg:col-span-8 space-y-6">
                    {deploymentLoading ? (
                      <div className="flex h-96 items-center justify-center space-x-2 rounded-2xl border border-slate-800 bg-slate-900/40">
                        <div className="h-5 w-5 animate-spin rounded-full border-2 border-cyan-500 border-t-transparent" />
                        <span className="text-xs text-slate-400">Loading shadow evaluation diagnostics...</span>
                      </div>
                    ) : !selectedShadowAnalysis ? (
                      <div className="flex h-96 flex-col items-center justify-center rounded-2xl border border-slate-800 bg-slate-900/40 p-8 text-center">
                        <p className="text-sm font-semibold text-slate-400">No Deployment Selected</p>
                        <p className="text-xs text-slate-600 mt-1 max-w-sm">
                          Select a deployment from the registry on the left or create a new deployment to view shadow analysis and readiness gates.
                        </p>
                      </div>
                    ) : (
                      <>
                        {/* Selected Deployment Header Card */}
                        <div className="rounded-2xl border border-slate-800/80 bg-slate-900/70 p-6 space-y-6">
                          <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between border-b border-slate-800/80 pb-4">
                            <div>
                              <div className="flex items-center gap-3">
                                <h3 className="text-lg font-black text-white">
                                  {selectedShadowAnalysis.challenger_version}{" "}
                                  <span className="text-xs font-normal text-slate-400">vs</span>{" "}
                                  {selectedShadowAnalysis.champion_version}
                                </h3>
                                <span
                                  className={`rounded-full border px-2.5 py-0.5 text-xs font-mono font-bold uppercase tracking-wider ${getDeploymentStatusBadge(
                                    selectedShadowAnalysis.status
                                  )}`}
                                >
                                  {selectedShadowAnalysis.status}
                                </span>
                                <span
                                  className={`rounded-full border px-2.5 py-0.5 text-xs font-mono font-bold uppercase tracking-wider ${getDeploymentReadinessDecisionBadge(
                                    selectedShadowAnalysis.readiness.decision
                                  )}`}
                                >
                                  {selectedShadowAnalysis.readiness.decision.replace(/_/g, " ")}
                                </span>
                              </div>
                              <p className="text-xs text-slate-400 font-mono mt-1">
                                Deployment ID: {selectedShadowAnalysis.deployment_id} • SHA-256 Partitioning
                              </p>
                            </div>
    
                            {/* Action Buttons */}
                            <div className="flex flex-wrap items-center gap-2">
                              <button
                                onClick={() => {
                                  setShadowPercentage(selectedShadowAnalysis.traffic_allocation_percentage || 100);
                                  setShadowModalOpen(true);
                                }}
                                className="rounded-xl border border-cyan-700/60 bg-cyan-950/40 px-3 py-1.5 text-xs font-bold text-cyan-300 hover:bg-cyan-900/60 transition"
                              >
                                Shadow Traffic %
                              </button>
    
                              <button
                                onClick={() => {
                                  setDepCanaryPercentage(10);
                                  setDepCanaryModalOpen(true);
                                }}
                                className="rounded-xl border border-purple-700/60 bg-purple-950/40 px-3 py-1.5 text-xs font-bold text-purple-300 hover:bg-purple-900/60 transition"
                              >
                                Canary Rollout
                              </button>
    
                              {selectedShadowAnalysis.status !== "PAUSED" && selectedShadowAnalysis.status !== "RETIRED" && (
                                <button
                                  onClick={handlePauseDeployment}
                                  disabled={deploymentActionLoading}
                                  className="rounded-xl border border-amber-700/60 bg-amber-950/40 px-3 py-1.5 text-xs font-bold text-amber-300 hover:bg-amber-900/60 transition disabled:opacity-50"
                                >
                                  Pause
                                </button>
                              )}
    
                              {selectedShadowAnalysis.status === "CANARY" && (
                                <button
                                  onClick={() => setDepActivateModalOpen(true)}
                                  className="rounded-xl bg-emerald-600 px-3 py-1.5 text-xs font-bold text-white hover:bg-emerald-500 shadow-lg shadow-emerald-600/30 transition"
                                >
                                  Activate (Admin)
                                </button>
                              )}
    
                              {(selectedShadowAnalysis.status === "ACTIVE" || selectedShadowAnalysis.status === "CANARY" || selectedShadowAnalysis.status === "ROLLBACK_REQUIRED") && (
                                <button
                                  onClick={() => setDepRollbackModalOpen(true)}
                                  className="rounded-xl bg-rose-600 px-3 py-1.5 text-xs font-bold text-white hover:bg-rose-500 shadow-lg shadow-rose-600/30 transition"
                                >
                                  Rollback (Admin)
                                </button>
                              )}
                            </div>
                          </div>
    
                          {/* Performance & Quality Metrics Comparison Table */}
                          <div>
                            <h4 className="text-xs font-bold uppercase tracking-wider text-slate-400 mb-3">
                              Champion vs Challenger Shadow Performance Scorecard
                            </h4>
                            <div className="overflow-x-auto rounded-xl border border-slate-800">
                              <table className="w-full text-left text-xs font-mono">
                                <thead className="bg-slate-900/90 text-[10px] uppercase tracking-wider text-slate-400 border-b border-slate-800">
                                  <tr>
                                    <th className="px-4 py-2.5">Metric Name</th>
                                    <th className="px-4 py-2.5">Champion ({selectedShadowAnalysis.champion_version})</th>
                                    <th className="px-4 py-2.5">Challenger ({selectedShadowAnalysis.challenger_version})</th>
                                    <th className="px-4 py-2.5">Delta</th>
                                    <th className="px-4 py-2.5">Classification</th>
                                  </tr>
                                </thead>
                                <tbody className="divide-y divide-slate-800/60 bg-slate-950/40">
                                  {selectedShadowAnalysis.metric_deltas.map((m) => (
                                    <tr key={m.metric_name} className="hover:bg-slate-900/50">
                                      <td className="px-4 py-2.5 text-slate-300 font-sans font-medium">{m.metric_name}</td>
                                      <td className="px-4 py-2.5 text-slate-400">
                                        {m.champion_value !== null ? m.champion_value.toFixed(4) : "N/A"}
                                      </td>
                                      <td className="px-4 py-2.5 text-white font-bold">
                                        {m.challenger_value !== null ? m.challenger_value.toFixed(4) : "N/A"}
                                      </td>
                                      <td className="px-4 py-2.5">
                                        <span
                                          className={
                                            m.delta === null
                                              ? "text-slate-500"
                                              : m.delta > 0
                                              ? "text-emerald-400 font-bold"
                                              : m.delta < 0
                                              ? "text-rose-400 font-bold"
                                              : "text-slate-400"
                                          }
                                        >
                                          {m.delta !== null ? (m.delta > 0 ? `+${m.delta.toFixed(4)}` : m.delta.toFixed(4)) : "N/A"}
                                        </span>
                                      </td>
                                      <td className="px-4 py-2.5">
                                        <span
                                          className={`rounded px-2 py-0.5 text-[10px] font-bold ${
                                            m.status === "IMPROVED"
                                              ? "bg-emerald-950/60 border border-emerald-800/40 text-emerald-300"
                                              : m.status === "REGRESSED"
                                              ? "bg-rose-950/60 border border-rose-800/40 text-rose-300"
                                              : "bg-slate-900 border border-slate-800 text-slate-400"
                                          }`}
                                        >
                                          {m.status}
                                        </span>
                                      </td>
                                    </tr>
                                  ))}
                                </tbody>
                              </table>
                            </div>
                          </div>
    
                          {/* Probability Shift & Agreement Rates */}
                          <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
                            <div className="rounded-xl border border-slate-800 bg-slate-900/60 p-3">
                              <span className="text-[10px] text-slate-500 uppercase block font-bold font-mono">Mean Probability Delta</span>
                              <strong className="text-white font-mono text-sm">
                                {selectedShadowAnalysis.mean_probability_delta > 0
                                  ? `+${selectedShadowAnalysis.mean_probability_delta.toFixed(4)}`
                                  : selectedShadowAnalysis.mean_probability_delta.toFixed(4)}
                              </strong>
                            </div>
    
                            <div className="rounded-xl border border-slate-800 bg-slate-900/60 p-3">
                              <span className="text-[10px] text-slate-500 uppercase block font-bold font-mono">Mean Absolute Shift</span>
                              <strong className="text-cyan-400 font-mono text-sm">
                                {selectedShadowAnalysis.mean_absolute_probability_delta.toFixed(4)}
                              </strong>
                            </div>
    
                            <div className="rounded-xl border border-slate-800 bg-slate-900/60 p-3">
                              <span className="text-[10px] text-slate-500 uppercase block font-bold font-mono">Channel Agreement</span>
                              <strong className="text-purple-400 font-mono text-sm">
                                {selectedShadowAnalysis.channel_agreement_rate !== null
                                  ? `${(selectedShadowAnalysis.channel_agreement_rate * 100).toFixed(1)}%`
                                  : "N/A"}
                              </strong>
                            </div>
    
                            <div className="rounded-xl border border-slate-800 bg-slate-900/60 p-3">
                              <span className="text-[10px] text-slate-500 uppercase block font-bold font-mono">Cadence Agreement</span>
                              <strong className="text-indigo-400 font-mono text-sm">
                                {selectedShadowAnalysis.delay_agreement_rate !== null
                                  ? `${(selectedShadowAnalysis.delay_agreement_rate * 100).toFixed(1)}%`
                                  : "N/A"}
                              </strong>
                            </div>
                          </div>
    
                          {/* 5-Bucket Calibration & Reliability Diagram */}
                          <div>
                            <div className="flex items-center justify-between mb-3">
                              <h4 className="text-xs font-bold uppercase tracking-wider text-slate-400">
                                5-Bucket Expected Calibration Error (ECE) & Reliability
                              </h4>
                              <div className="text-xs font-mono text-slate-400 flex items-center gap-3">
                                <span>Champion ECE: <strong className="text-slate-300">{selectedShadowAnalysis.calibration.champion_ece.toFixed(4)}</strong></span>
                                <span>Challenger ECE: <strong className="text-cyan-400">{selectedShadowAnalysis.calibration.challenger_ece.toFixed(4)}</strong></span>
                                <span>ΔECE: <strong className={selectedShadowAnalysis.calibration.ece_delta <= 0 ? "text-emerald-400" : "text-rose-400"}>
                                  {selectedShadowAnalysis.calibration.ece_delta > 0 ? `+${selectedShadowAnalysis.calibration.ece_delta.toFixed(4)}` : selectedShadowAnalysis.calibration.ece_delta.toFixed(4)}
                                </strong></span>
                              </div>
                            </div>
    
                            <div className="overflow-x-auto rounded-xl border border-slate-800">
                              <table className="w-full text-left text-xs font-mono">
                                <thead className="bg-slate-900/90 text-[10px] uppercase tracking-wider text-slate-400 border-b border-slate-800">
                                  <tr>
                                    <th className="px-3 py-2">Predicted Range</th>
                                    <th className="px-3 py-2">Champ Count</th>
                                    <th className="px-3 py-2">Champ Pred</th>
                                    <th className="px-3 py-2">Champ Actual</th>
                                    <th className="px-3 py-2">Champ Error</th>
                                    <th className="px-3 py-2">Chall Count</th>
                                    <th className="px-3 py-2">Chall Pred</th>
                                    <th className="px-3 py-2">Chall Actual</th>
                                    <th className="px-3 py-2">Chall Error</th>
                                  </tr>
                                </thead>
                                <tbody className="divide-y divide-slate-800/60 bg-slate-950/40">
                                  {selectedShadowAnalysis.calibration.buckets.map((b) => (
                                    <tr key={b.bucket_range} className="hover:bg-slate-900/50">
                                      <td className="px-3 py-2 text-white font-bold">{b.bucket_range}</td>
                                      <td className="px-3 py-2 text-slate-400">{b.champion_sample_size}</td>
                                      <td className="px-3 py-2 text-slate-300">{b.champion_avg_probability?.toFixed(3) ?? "—"}</td>
                                      <td className="px-3 py-2 text-slate-300">{b.champion_actual_rate?.toFixed(3) ?? "—"}</td>
                                      <td className="px-3 py-2 text-slate-400">{b.champion_calibration_error?.toFixed(3) ?? "—"}</td>
                                      <td className="px-3 py-2 text-cyan-400">{b.challenger_sample_size}</td>
                                      <td className="px-3 py-2 text-cyan-300">{b.challenger_avg_probability?.toFixed(3) ?? "—"}</td>
                                      <td className="px-3 py-2 text-cyan-300">{b.challenger_actual_rate?.toFixed(3) ?? "—"}</td>
                                      <td className="px-3 py-2 text-cyan-400 font-bold">{b.challenger_calibration_error?.toFixed(3) ?? "—"}</td>
                                    </tr>
                                  ))}
                                </tbody>
                              </table>
                            </div>
                          </div>
    
                          {/* Statistical Hypothesis Testing Card */}
                          <div className="rounded-xl border border-slate-800 bg-slate-950/40 p-4 space-y-3">
                            <div className="flex items-center justify-between">
                              <h4 className="text-xs font-bold uppercase tracking-wider text-slate-400">
                                Statistical Significance (Two-Proportion Pooled Z-Test)
                              </h4>
                              <span
                                className={`rounded-full border px-2.5 py-0.5 text-xs font-mono font-bold uppercase tracking-wider ${getDeploymentSignificanceBadge(
                                  selectedShadowAnalysis.statistical_test.significance_classification
                                )}`}
                              >
                                {selectedShadowAnalysis.statistical_test.significance_classification.replace(/_/g, " ")}
                              </span>
                            </div>
    
                            <div className="grid grid-cols-2 gap-3 sm:grid-cols-4 text-xs font-mono">
                              <div className="rounded-lg bg-slate-900/80 p-2.5 border border-slate-800/80">
                                <span className="text-[10px] text-slate-500 uppercase block">Z-Statistic</span>
                                <strong className="text-white">
                                  {selectedShadowAnalysis.statistical_test.test_statistic !== null
                                    ? selectedShadowAnalysis.statistical_test.test_statistic.toFixed(4)
                                    : "N/A"}
                                </strong>
                              </div>
    
                              <div className="rounded-lg bg-slate-900/80 p-2.5 border border-slate-800/80">
                                <span className="text-[10px] text-slate-500 uppercase block">P-Value (α=0.05)</span>
                                <strong className="text-cyan-400">
                                  {selectedShadowAnalysis.statistical_test.p_value !== null
                                    ? selectedShadowAnalysis.statistical_test.p_value.toFixed(4)
                                    : "N/A"}
                                </strong>
                              </div>
    
                              <div className="rounded-lg bg-slate-900/80 p-2.5 border border-slate-800/80">
                                <span className="text-[10px] text-slate-500 uppercase block">Champion 95% Wilson CI</span>
                                <strong className="text-slate-300">
                                  {selectedShadowAnalysis.statistical_test.wilson_champion_ci
                                    ? `[${selectedShadowAnalysis.statistical_test.wilson_champion_ci[0].toFixed(3)}, ${selectedShadowAnalysis.statistical_test.wilson_champion_ci[1].toFixed(3)}]`
                                    : "N/A"}
                                </strong>
                              </div>
    
                              <div className="rounded-lg bg-slate-900/80 p-2.5 border border-slate-800/80">
                                <span className="text-[10px] text-slate-500 uppercase block">Newcombe 95% Diff CI</span>
                                <strong className="text-purple-300">
                                  {selectedShadowAnalysis.statistical_test.newcombe_difference_ci
                                    ? `[${selectedShadowAnalysis.statistical_test.newcombe_difference_ci[0].toFixed(3)}, ${selectedShadowAnalysis.statistical_test.newcombe_difference_ci[1].toFixed(3)}]`
                                    : "N/A"}
                                </strong>
                              </div>
                            </div>
                          </div>
    
                          {/* 14 Deployment Readiness Safety Gates */}
                          <div>
                            <div className="flex items-center justify-between mb-3">
                              <h4 className="text-xs font-bold uppercase tracking-wider text-slate-400">
                                14 Deterministic Deployment Readiness Safety Gates
                              </h4>
                              <div className="flex items-center gap-2">
                                <span className={`text-[10px] font-mono font-bold px-2 py-0.5 rounded border ${selectedShadowAnalysis.readiness.can_promote_to_canary ? "bg-purple-950 border-purple-800 text-purple-300" : "bg-slate-900 border-slate-800 text-slate-500"}`}>
                                  Canary Eligible: {selectedShadowAnalysis.readiness.can_promote_to_canary ? "YES" : "NO"}
                                </span>
                                <span className={`text-[10px] font-mono font-bold px-2 py-0.5 rounded border ${selectedShadowAnalysis.readiness.can_activate_production ? "bg-emerald-950 border-emerald-800 text-emerald-300" : "bg-slate-900 border-slate-800 text-slate-500"}`}>
                                  Activation Ready: {selectedShadowAnalysis.readiness.can_activate_production ? "YES" : "NO"}
                                </span>
                              </div>
                            </div>
    
                            <div className="grid grid-cols-1 gap-2.5 sm:grid-cols-2">
                              {selectedShadowAnalysis.readiness.gates.map((g) => (
                                <div
                                  key={g.gate_code}
                                  className={`rounded-xl border p-3 text-xs font-mono ${
                                    g.passed
                                      ? "border-emerald-900/50 bg-emerald-950/10"
                                      : "border-rose-900/50 bg-rose-950/10"
                                  }`}
                                >
                                  <div className="flex items-center justify-between mb-1">
                                    <span className="font-bold text-white text-[11px]">{g.gate_code}</span>
                                    <span
                                      className={`rounded px-1.5 py-0.2 text-[9px] font-bold uppercase ${
                                        g.passed
                                          ? "bg-emerald-900/80 text-emerald-200"
                                          : "bg-rose-900/80 text-rose-200"
                                      }`}
                                    >
                                      {g.passed ? "PASSED" : "FAILED"}
                                    </span>
                                  </div>
                                  <p className="text-[11px] text-slate-400 font-sans leading-relaxed mt-1">
                                    {g.explanation}
                                  </p>
                                  <div className="mt-2 text-[10px] text-slate-500 flex items-center justify-between border-t border-slate-800/40 pt-1.5">
                                    <span>Obs: {String(g.observed_value)}</span>
                                    <span>Req: {String(g.threshold)}</span>
                                  </div>
                                </div>
                              ))}
                            </div>
                          </div>
    
                          {/* Real-Time Rollback Guardrails Diagnostics */}
                          <div className={`rounded-xl border p-4 space-y-2 ${selectedShadowAnalysis.rollback_diagnostics.rollback_recommended ? "border-rose-800 bg-rose-950/30" : "border-slate-800 bg-slate-950/40"}`}>
                            <div className="flex items-center justify-between">
                              <h4 className="text-xs font-bold uppercase tracking-wider text-slate-300">
                                Real-Time Rollback Guardrails Diagnostics
                              </h4>
                              <span
                                className={`rounded-full border px-2.5 py-0.5 text-xs font-mono font-bold uppercase tracking-wider ${
                                  selectedShadowAnalysis.rollback_diagnostics.rollback_recommended
                                    ? "bg-rose-950 border-rose-700 text-rose-300 animate-pulse"
                                    : "bg-emerald-950 border-emerald-700 text-emerald-300"
                                }`}
                              >
                                {selectedShadowAnalysis.rollback_diagnostics.rollback_recommended
                                  ? "ROLLBACK RECOMMENDED"
                                  : "GUARDRAILS HEALTHY"}
                              </span>
                            </div>
    
                            {selectedShadowAnalysis.rollback_diagnostics.rollback_recommended ? (
                              <div className="text-xs text-rose-300 space-y-1">
                                <p className="font-bold">Active Rollback Alert Reasons:</p>
                                <ul className="list-disc pl-4 space-y-0.5 text-[11px]">
                                  {selectedShadowAnalysis.rollback_diagnostics.reasons.map((r, idx) => (
                                    <li key={idx}>{r}</li>
                                  ))}
                                </ul>
                              </div>
                            ) : (
                              <p className="text-xs text-slate-400">
                                All automated safety guardrails are within safe operational tolerances (Recovery yield non-regression, zero drift anomalies, zero data quality corruptions, verified artifact hashes).
                              </p>
                            )}
                          </div>
                        </div>
                      </>
                    )}
                  </div>
                </div>
              </div>


            {createDeploymentModalOpen && (
              <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/80 backdrop-blur-sm p-4">
                <div className="w-full max-w-lg rounded-2xl border border-cyan-800/80 bg-slate-900 p-6 shadow-2xl space-y-6">
                  <div className="flex items-center justify-between border-b border-slate-800 pb-4">
                    <div>
                      <h3 className="text-base font-bold text-white">
                        Create Governed Model Deployment
                      </h3>
                      <p className="text-xs text-slate-400 mt-0.5 font-mono">
                        Initialize passive shadow mode validation against Champion v1.0
                      </p>
                    </div>
                    <button
                      onClick={() => setCreateDeploymentModalOpen(false)}
                      className="rounded-lg p-1.5 text-slate-400 hover:bg-slate-800 hover:text-white"
                    >
                      ✕
                    </button>
                  </div>
    
                  <form
                    onSubmit={(e) => {
                      e.preventDefault();
                      handleCreateDeployment();
                    }}
                    className="space-y-4"
                  >
                    <div>
                      <label className="text-xs font-bold text-slate-300 block mb-1">
                        Select Challenger Candidate Model *
                      </label>
                      <select
                        required
                        value={createDepChallengerVersion}
                        onChange={(e) => setCreateDepChallengerVersion(e.target.value)}
                        className="w-full rounded-xl border border-slate-800 bg-slate-950 px-3 py-2 text-xs text-slate-200 focus:border-cyan-500 focus:outline-none font-mono"
                      >
                        <option value="">-- Choose Candidate Model --</option>
                        {modelsData?.items
                          .filter((m) => m.model_version !== "v1.0")
                          .map((m) => (
                            <option key={m.model_version} value={m.model_version}>
                              {m.model_version} ({m.lifecycle_status}) - Created {new Date(m.created_at).toLocaleDateString()}
                            </option>
                          ))}
                      </select>
                    </div>
    
                    <div>
                      <label className="text-xs font-bold text-slate-300 block mb-1">
                        Deployment Notes (Optional)
                      </label>
                      <textarea
                        value={createDepNotes}
                        onChange={(e) => setCreateDepNotes(e.target.value)}
                        placeholder="e.g., Initiating 100% passive shadow mode traffic evaluation for Retrained Model v1.1."
                        rows={3}
                        className="w-full rounded-xl border border-slate-800 bg-slate-950 px-3 py-2 text-xs text-slate-200 placeholder-slate-600 focus:border-cyan-500 focus:outline-none"
                      />
                    </div>
    
                    <div className="rounded-xl border border-cyan-800/40 bg-cyan-950/20 p-3 text-[11px] text-cyan-200/90 leading-relaxed font-mono">
                      ✓ Strict Financial Isolation Guarantee: Challenger models never execute financial transactions. Traffic starts at 0% shadow mode.
                    </div>
    
                    <div className="flex items-center justify-end gap-3 border-t border-slate-800 pt-4">
                      <button
                        type="button"
                        onClick={() => setCreateDeploymentModalOpen(false)}
                        className="rounded-xl border border-slate-800 bg-slate-950 px-4 py-2 text-xs font-bold uppercase tracking-wider text-slate-400 hover:text-white transition"
                      >
                        Cancel
                      </button>
                      <button
                        type="submit"
                        disabled={deploymentActionLoading || !createDepChallengerVersion}
                        className="rounded-xl bg-cyan-600 px-6 py-2 text-xs font-bold uppercase tracking-wider text-white hover:bg-cyan-500 shadow-lg shadow-cyan-600/30 transition disabled:opacity-50"
                      >
                        {deploymentActionLoading ? "Creating..." : "Initialize Deployment"}
                      </button>
                    </div>
                  </form>
                </div>
              </div>
            )}
    
            {/* Phase 9J: Shadow Traffic Allocation Modal */}
            {shadowModalOpen && selectedShadowAnalysis && (
              <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/80 backdrop-blur-sm p-4">
                <div className="w-full max-w-md rounded-2xl border border-cyan-800/80 bg-slate-900 p-6 shadow-2xl space-y-6">
                  <div className="flex items-center justify-between border-b border-slate-800 pb-4">
                    <div>
                      <h3 className="text-base font-bold text-white">
                        Adjust Shadow Traffic Allocation
                      </h3>
                      <p className="text-xs text-cyan-400 mt-0.5 font-mono">
                        Candidate: {selectedShadowAnalysis.challenger_version}
                      </p>
                    </div>
                    <button
                      onClick={() => setShadowModalOpen(false)}
                      className="rounded-lg p-1.5 text-slate-400 hover:bg-slate-800 hover:text-white"
                    >
                      ✕
                    </button>
                  </div>
    
                  <form
                    onSubmit={(e) => {
                      e.preventDefault();
                      handleStartShadow();
                    }}
                    className="space-y-4"
                  >
                    <div>
                      <label className="text-xs font-bold text-slate-300 block mb-2">
                        Select Shadow Traffic Percentage (Deterministic SHA-256):
                      </label>
                      <div className="grid grid-cols-3 gap-2">
                        {[0, 5, 10, 25, 50, 100].map((pct) => (
                          <button
                            key={pct}
                            type="button"
                            onClick={() => setShadowPercentage(pct)}
                            className={`rounded-xl border py-2 text-xs font-mono font-bold transition ${
                              shadowPercentage === pct
                                ? "border-cyan-500 bg-cyan-950 text-cyan-200 shadow-md shadow-cyan-900/50"
                                : "border-slate-800 bg-slate-950 text-slate-400 hover:border-slate-700"
                            }`}
                          >
                            {pct}%
                          </button>
                        ))}
                      </div>
                    </div>
    
                    <div className="rounded-xl border border-cyan-800/40 bg-cyan-950/20 p-3 text-[11px] text-cyan-200/90 leading-relaxed font-mono">
                      ✓ Shadow mode predictions are logged for telemetry and evaluated offline without affecting operational decisions.
                    </div>
    
                    <div className="flex items-center justify-end gap-3 border-t border-slate-800 pt-4">
                      <button
                        type="button"
                        onClick={() => setShadowModalOpen(false)}
                        className="rounded-xl border border-slate-800 bg-slate-950 px-4 py-2 text-xs font-bold uppercase tracking-wider text-slate-400 hover:text-white transition"
                      >
                        Cancel
                      </button>
                      <button
                        type="submit"
                        disabled={deploymentActionLoading}
                        className="rounded-xl bg-cyan-600 px-6 py-2 text-xs font-bold uppercase tracking-wider text-white hover:bg-cyan-500 shadow-lg shadow-cyan-600/30 transition disabled:opacity-50"
                      >
                        {deploymentActionLoading ? "Updating..." : `Set ${shadowPercentage}% Shadow`}
                      </button>
                    </div>
                  </form>
                </div>
              </div>
            )}
    
            {/* Phase 9J: Canary Rollout Modal */}
            {depCanaryModalOpen && selectedShadowAnalysis && (
              <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/80 backdrop-blur-sm p-4">
                <div className="w-full max-w-md rounded-2xl border border-purple-800/80 bg-slate-900 p-6 shadow-2xl space-y-6">
                  <div className="flex items-center justify-between border-b border-slate-800 pb-4">
                    <div>
                      <h3 className="text-base font-bold text-white">
                        Set Governed Canary Rollout
                      </h3>
                      <p className="text-xs text-purple-400 mt-0.5 font-mono">
                        Candidate: {selectedShadowAnalysis.challenger_version}
                      </p>
                    </div>
                    <button
                      onClick={() => setDepCanaryModalOpen(false)}
                      className="rounded-lg p-1.5 text-slate-400 hover:bg-slate-800 hover:text-white"
                    >
                      ✕
                    </button>
                  </div>
    
                  <form
                    onSubmit={(e) => {
                      e.preventDefault();
                      handleSetCanary();
                    }}
                    className="space-y-4"
                  >
                    <div>
                      <label className="text-xs font-bold text-slate-300 block mb-2">
                        Select Canary Traffic Allocation (%):
                      </label>
                      <div className="grid grid-cols-3 gap-2">
                        {[5, 10, 25, 50, 100].map((pct) => (
                          <button
                            key={pct}
                            type="button"
                            onClick={() => setDepCanaryPercentage(pct)}
                            className={`rounded-xl border py-2 text-xs font-mono font-bold transition ${
                              depCanaryPercentage === pct
                                ? "border-purple-500 bg-purple-950 text-purple-200 shadow-md shadow-purple-900/50"
                                : "border-slate-800 bg-slate-950 text-slate-400 hover:border-slate-700"
                            }`}
                          >
                            {pct}%
                          </button>
                        ))}
                      </div>
                    </div>
    
                    <div className="rounded-xl border border-purple-800/40 bg-purple-950/20 p-3 text-[11px] text-purple-200/90 leading-relaxed font-mono">
                      ✓ Canary stage: Model serves live predictions for {depCanaryPercentage}% of partitioned cases through PolicyEngine financial gates.
                    </div>
    
                    <div className="flex items-center justify-end gap-3 border-t border-slate-800 pt-4">
                      <button
                        type="button"
                        onClick={() => setDepCanaryModalOpen(false)}
                        className="rounded-xl border border-slate-800 bg-slate-950 px-4 py-2 text-xs font-bold uppercase tracking-wider text-slate-400 hover:text-white transition"
                      >
                        Cancel
                      </button>
                      <button
                        type="submit"
                        disabled={deploymentActionLoading}
                        className="rounded-xl bg-purple-600 px-6 py-2 text-xs font-bold uppercase tracking-wider text-white hover:bg-purple-500 shadow-lg shadow-purple-600/30 transition disabled:opacity-50"
                      >
                        {deploymentActionLoading ? "Promoting..." : `Start ${depCanaryPercentage}% Canary`}
                      </button>
                    </div>
                  </form>
                </div>
              </div>
            )}
    
            {/* Phase 9J: Admin Production Activation Modal */}
            {depActivateModalOpen && selectedShadowAnalysis && (
              <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/80 backdrop-blur-sm p-4">
                <div className="w-full max-w-md rounded-2xl border border-emerald-800/80 bg-slate-900 p-6 shadow-2xl space-y-6">
                  <div className="flex items-center justify-between border-b border-slate-800 pb-4">
                    <div>
                      <h3 className="text-base font-bold text-white">
                        Promote Challenger to ACTIVE Champion
                      </h3>
                      <p className="text-xs text-emerald-400 mt-0.5 font-mono">
                        Challenger: {selectedShadowAnalysis.challenger_version} → ACTIVE Champion
                      </p>
                    </div>
                    <button
                      onClick={() => setDepActivateModalOpen(false)}
                      className="rounded-lg p-1.5 text-slate-400 hover:bg-slate-800 hover:text-white"
                    >
                      ✕
                    </button>
                  </div>
    
                  <form
                    onSubmit={(e) => {
                      e.preventDefault();
                      handleActivateDeployment();
                    }}
                    className="space-y-4"
                  >
                    <div>
                      <label className="text-xs font-bold text-slate-300 block mb-1">
                        Admin Approval Notes
                      </label>
                      <textarea
                        value={depActivateNotes}
                        onChange={(e) => setDepActivateNotes(e.target.value)}
                        placeholder="e.g., Passed all 14 gates and completed successful canary period. Activated by Admin."
                        rows={3}
                        className="w-full rounded-xl border border-slate-800 bg-slate-950 px-3 py-2 text-xs text-slate-200 placeholder-slate-600 focus:border-emerald-500 focus:outline-none"
                      />
                    </div>
    
                    <div className="rounded-xl border border-emerald-800/40 bg-emerald-950/20 p-3 text-[11px] text-emerald-200/90 leading-relaxed font-mono">
                      ✓ Atomic Transition: Old Champion ({selectedShadowAnalysis.champion_version}) will be RETIRED. Candidate ({selectedShadowAnalysis.challenger_version}) becomes authoritative 100% active Champion. Modifies zero financial states.
                    </div>
    
                    <div className="flex items-center justify-end gap-3 border-t border-slate-800 pt-4">
                      <button
                        type="button"
                        onClick={() => setDepActivateModalOpen(false)}
                        className="rounded-xl border border-slate-800 bg-slate-950 px-4 py-2 text-xs font-bold uppercase tracking-wider text-slate-400 hover:text-white transition"
                      >
                        Cancel
                      </button>
                      <button
                        type="submit"
                        disabled={deploymentActionLoading}
                        className="rounded-xl bg-emerald-600 px-6 py-2 text-xs font-bold uppercase tracking-wider text-white hover:bg-emerald-500 shadow-lg shadow-emerald-600/30 transition disabled:opacity-50"
                      >
                        {deploymentActionLoading ? "Activating..." : "Confirm Production Activation"}
                      </button>
                    </div>
                  </form>
                </div>
              </div>
            )}
    
            {/* Phase 9J: Admin Emergency Rollback Modal */}
            {depRollbackModalOpen && selectedShadowAnalysis && (
              <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/80 backdrop-blur-sm p-4">
                <div className="w-full max-w-md rounded-2xl border border-rose-800/80 bg-slate-900 p-6 shadow-2xl space-y-6">
                  <div className="flex items-center justify-between border-b border-slate-800 pb-4">
                    <div>
                      <h3 className="text-base font-bold text-white">
                        Emergency Rollback Deployment
                      </h3>
                      <p className="text-xs text-rose-400 mt-0.5 font-mono">
                        Restoring Champion: {selectedShadowAnalysis.champion_version}
                      </p>
                    </div>
                    <button
                      onClick={() => setDepRollbackModalOpen(false)}
                      className="rounded-lg p-1.5 text-slate-400 hover:bg-slate-800 hover:text-white"
                    >
                      ✕
                    </button>
                  </div>
    
                  <form
                    onSubmit={(e) => {
                      e.preventDefault();
                      handleRollbackDeployment();
                    }}
                    className="space-y-4"
                  >
                    <div>
                      <label className="text-xs font-bold text-slate-300 block mb-1">
                        Rollback Reason *
                      </label>
                      <textarea
                        required
                        value={depRollbackReason}
                        onChange={(e) => setDepRollbackReason(e.target.value)}
                        placeholder="e.g., Critical drift anomaly detected or recovery rate degradation exceeding guardrail."
                        rows={3}
                        className="w-full rounded-xl border border-slate-800 bg-slate-950 px-3 py-2 text-xs text-slate-200 placeholder-slate-600 focus:border-rose-500 focus:outline-none"
                      />
                    </div>
    
                    <div>
                      <label className="text-xs font-bold text-slate-300 block mb-1">
                        Additional Notes (Optional)
                      </label>
                      <input
                        type="text"
                        value={depRollbackNotes}
                        onChange={(e) => setDepRollbackNotes(e.target.value)}
                        placeholder="e.g., Incident logged to governance ledger."
                        className="w-full rounded-xl border border-slate-800 bg-slate-950 px-3 py-2 text-xs text-slate-200 focus:border-rose-500 focus:outline-none"
                      />
                    </div>
    
                    <div className="rounded-xl border border-rose-800/40 bg-rose-950/20 p-3 text-[11px] text-rose-200/90 leading-relaxed font-mono">
                      ✕ Instant Reversion: Challenger ({selectedShadowAnalysis.challenger_version}) will be RETIRED. Prior Champion ({selectedShadowAnalysis.champion_version}) is immediately restored to 100% active state.
                    </div>
    
                    <div className="flex items-center justify-end gap-3 border-t border-slate-800 pt-4">
                      <button
                        type="button"
                        onClick={() => setDepRollbackModalOpen(false)}
                        className="rounded-xl border border-slate-800 bg-slate-950 px-4 py-2 text-xs font-bold uppercase tracking-wider text-slate-400 hover:text-white transition"
                      >
                        Cancel
                      </button>
                      <button
                        type="submit"
                        disabled={deploymentActionLoading || !depRollbackReason}
                        className="rounded-xl bg-rose-600 px-6 py-2 text-xs font-bold uppercase tracking-wider text-white hover:bg-rose-500 shadow-lg shadow-rose-600/30 transition disabled:opacity-50"
                      >
                        {deploymentActionLoading ? "Rolling back..." : "Confirm Rollback"}
                      </button>
                    </div>
                  </form>
                </div>
              </div>
            )}
    
            {/* Phase 9K: Trigger Offline Candidate Retraining Modal */}


    </>
  );
}
