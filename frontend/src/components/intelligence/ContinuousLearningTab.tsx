"use client";

import React, { useCallback, useEffect, useState } from "react";
import {
  ContinuousLearningReadiness,
  ContinuousLearningSummary,
  ModelLineageResponse,
  PaginatedDatasetsResponse,
  PaginatedTrainingRunsResponse,
  fetchContinuousLearningDatasets,
  fetchContinuousLearningReadiness,
  fetchContinuousLearningSummary,
  fetchContinuousLearningTrainingRuns,
  fetchModelLineage,
  triggerManualTraining
} from "../../lib/api";
import { formatNum, formatPct, getDeploymentStatusBadge, getEligibilityDecisionBadge, getEvolutionDecisionBadge } from "./intelligenceBadges";

interface ContinuousLearningTabProps {
  userRole?: string;
}

export default function ContinuousLearningTab({ userRole = "ADMIN" }: ContinuousLearningTabProps) {
  const [error, setError] = useState<string | null>(null);

    const [continuousLearningSummary, setContinuousLearningSummary] = useState<ContinuousLearningSummary | null>(null);
    const [datasetsData, setDatasetsData] = useState<PaginatedDatasetsResponse | null>(null);
    const [trainingRunsData, setTrainingRunsData] = useState<PaginatedTrainingRunsResponse | null>(null);
    const [lineageData, setLineageData] = useState<ModelLineageResponse | null>(null);
    const [learningReadinessData, setLearningReadinessData] = useState<ContinuousLearningReadiness | null>(null);
    const [manualTrainingModalOpen, setManualTrainingModalOpen] = useState(false);
    const [manualTrainingLr, setManualTrainingLr] = useState<number>(0.05);
    const [manualTrainingEpochs, setManualTrainingEpochs] = useState<number>(50);
    const [manualTrainingNotes, setManualTrainingNotes] = useState<string>("");
    const [manualTrainingLoading, setManualTrainingLoading] = useState(false);
  

    const handleTriggerOfflineTraining = async () => {
      setManualTrainingLoading(true);
      setError(null);
      try {
        await triggerManualTraining({
          learning_rate: manualTrainingLr,
          epochs: manualTrainingEpochs,
          notes: manualTrainingNotes || undefined,
        });
        setManualTrainingModalOpen(false);
        await loadContinuousLearningData();
      } catch (err) {
        setError(err instanceof Error ? err.message : "Failed to trigger offline training run");
      } finally {
        setManualTrainingLoading(false);
      }
    };
  
  
  

  const loadContinuousLearningData = useCallback(async () => {
    try {
      const [sumRes, dsRes, runsRes, linRes, readRes] = await Promise.all([
        fetchContinuousLearningSummary().catch(() => null),
        fetchContinuousLearningDatasets().catch(() => null),
        fetchContinuousLearningTrainingRuns().catch(() => null),
        fetchModelLineage().catch(() => null),
        fetchContinuousLearningReadiness().catch(() => null),
      ]);
      setContinuousLearningSummary(sumRes);
      setDatasetsData(dsRes);
      setTrainingRunsData(runsRes);
      setLineageData(linRes);
      setLearningReadinessData(readRes);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load Continuous Learning data");
    }
  }, []);

    useEffect(() => {
    let ignore = false;
    async function execute() {
      if (!ignore) {
        await loadContinuousLearningData();
      }
    }
    void execute();
    return () => {
      ignore = true;
    };
  }, [loadContinuousLearningData]);

  return (
    <>
      {error && (
        <div className="rounded-xl border border-rose-800/40 bg-rose-950/40 p-4 text-xs text-rose-300">
          {error}
        </div>
      )}
    
              {/* =========================================================================
                 TAB 11: CONTINUOUS LEARNING, RETRAINING MONITOR & PROVENANCE (Phase 9K)
                 ========================================================================= */}
              <div className="space-y-8">
                {/* Mandatory Governance & Zero Financial Mutation Banner */}
                <div className="rounded-2xl border border-emerald-800/60 bg-emerald-950/20 p-4 flex items-start gap-3">
                  <span className="rounded bg-emerald-900/80 px-2 py-0.5 text-[10px] font-bold uppercase tracking-wider text-emerald-200 border border-emerald-700/60 shrink-0">
                    PHASE 9K CONTINUOUS LEARNING
                  </span>
                  <div className="text-xs text-emerald-200/90 leading-relaxed space-y-1">
                    <p className="font-semibold">
                      GOVERNED CONTINUOUS LEARNING, RETRAINING MONITOR & PROVENANCE DAG
                    </p>
                    <p className="text-[11px] text-emerald-300/80">
                      Continuous learning layer evaluates new resolved recovery cases, model drift, and calibration degradation to determine retraining eligibility. Training is strictly executed offline and logged to the immutable audit ledger. Retraining NEVER automatically deploys models, NEVER bypasses PolicyEngine, and NEVER directly executes financial recovery actions.
                    </p>
                  </div>
                </div>
    
                {/* Quick Metrics Bar & Action Header */}
                <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
                  <div className="flex flex-wrap items-center gap-3">
                    <div className="rounded-xl border border-slate-800 bg-slate-900/80 px-4 py-2 text-xs font-mono">
                      <span className="text-[10px] text-slate-500 uppercase block font-bold">Active Champion</span>
                      <strong className="text-emerald-400 text-sm">{continuousLearningSummary?.active_champion_version || "v1.0"}</strong>
                    </div>
    
                    <div className="rounded-xl border border-slate-800 bg-slate-900/80 px-4 py-2 text-xs font-mono">
                      <span className="text-[10px] text-slate-500 uppercase block font-bold">Latest Dataset Version</span>
                      <strong className="text-cyan-400 text-sm">{continuousLearningSummary?.latest_dataset_version || "dataset-v2.25"}</strong>
                    </div>
    
                    <div className="rounded-xl border border-slate-800 bg-slate-900/80 px-4 py-2 text-xs font-mono">
                      <span className="text-[10px] text-slate-500 uppercase block font-bold">Total Dataset Samples</span>
                      <strong className="text-white text-sm">{continuousLearningSummary?.total_dataset_samples || 0}</strong>
                    </div>
    
                    <div className="rounded-xl border border-slate-800 bg-slate-900/80 px-4 py-2 text-xs font-mono">
                      <span className="text-[10px] text-slate-500 uppercase block font-bold">New Cases Since Training</span>
                      <strong className="text-amber-400 text-sm">{continuousLearningSummary?.new_resolved_cases_since_last_training || 0}</strong>
                    </div>
    
                    <div className="rounded-xl border border-slate-800 bg-slate-900/80 px-4 py-2 text-xs font-mono">
                      <span className="text-[10px] text-slate-500 uppercase block font-bold">Evolution Decision</span>
                      <span className={`inline-block rounded px-2 py-0.5 text-[11px] font-bold uppercase border mt-0.5 ${getEvolutionDecisionBadge(continuousLearningSummary?.evolution_decision || "NO_ACTION")}`}>
                        {(continuousLearningSummary?.evolution_decision || "NO_ACTION").replace(/_/g, " ")}
                      </span>
                    </div>
                  </div>
    
                  {/* Action Trigger Button */}
                  <div>
                    <button
                      onClick={() => setManualTrainingModalOpen(true)}
                      disabled={userRole === "VIEWER"}
                      className="flex items-center gap-2 rounded-xl bg-emerald-600 px-4 py-2 text-xs font-bold uppercase tracking-wider text-white hover:bg-emerald-500 shadow-lg shadow-emerald-600/30 transition disabled:opacity-40"
                      title={userRole === "VIEWER" ? "Viewer role cannot trigger training runs" : "Trigger offline candidate retraining"}
                    >
                      <span>⚡ Trigger Offline Retraining</span>
                    </button>
                  </div>
                </div>
    
                {/* Retraining Monitor: 4 Diagnostic Trigger Cards */}
                <div className="space-y-4">
                  <div className="flex items-center justify-between">
                    <div>
                      <h2 className="text-sm font-bold uppercase tracking-wider text-slate-300">
                        Automated Retraining Monitor & Trigger Signals
                      </h2>
                      <p className="text-xs text-slate-400 mt-0.5">
                        Continuous multi-signal surveillance monitoring dataset expansion, prediction drift, and calibration health.
                      </p>
                    </div>
                    {continuousLearningSummary?.retraining_eligibility && (
                      <span className={`rounded-full border px-3 py-1 text-xs font-bold uppercase tracking-wider ${getEligibilityDecisionBadge(continuousLearningSummary.retraining_eligibility.decision)}`}>
                        {continuousLearningSummary.retraining_eligibility.decision.replace(/_/g, " ")}
                      </span>
                    )}
                  </div>
    
                  <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
                    {/* Trigger 1: New Cases */}
                    {(() => {
                      const tr = continuousLearningSummary?.retraining_eligibility?.triggers?.find((t) => t.trigger_type === "NEW_RESOLVED_CASES");
                      const newCases = continuousLearningSummary?.new_resolved_cases_since_last_training || 0;
                      const threshold = 100;
                      const pct = Math.min(100, Math.round((newCases / threshold) * 100));
                      return (
                        <div className="rounded-2xl border border-slate-800 bg-slate-900/60 p-5 space-y-3">
                          <div className="flex items-center justify-between">
                            <span className="text-[10px] font-bold uppercase tracking-wider text-slate-400">
                              Data Accumulation
                            </span>
                            <span className={`rounded px-1.5 py-0.5 text-[10px] font-bold uppercase border ${tr?.triggered ? "bg-emerald-950/80 border-emerald-700 text-emerald-300" : "bg-slate-950 border-slate-800 text-slate-500"}`}>
                              {tr?.triggered ? "TRIGGERED" : "MONITORING"}
                            </span>
                          </div>
                          <div>
                            <div className="text-2xl font-black text-white font-mono">
                              {newCases} <span className="text-xs font-normal text-slate-400 font-sans">/ {threshold} cases</span>
                            </div>
                            <p className="text-[11px] text-slate-400 mt-1">
                              Threshold: $\ge 100$ new resolved recovery cases since last training run.
                            </p>
                          </div>
                          <div className="w-full bg-slate-950 rounded-full h-2 overflow-hidden border border-slate-800">
                            <div
                              className={`h-full transition-all duration-500 ${tr?.triggered ? "bg-emerald-500" : "bg-indigo-500"}`}
                              style={{ width: `${pct}%` }}
                            />
                          </div>
                        </div>
                      );
                    })()}
    
                    {/* Trigger 2: Prediction Drift (PSI) */}
                    {(() => {
                      const tr = continuousLearningSummary?.retraining_eligibility?.triggers?.find((t) => t.trigger_type === "MODEL_DRIFT");
                      const psi = tr?.observed_value !== undefined && tr?.observed_value !== null ? Number(tr.observed_value) : 0.05;
                      return (
                        <div className="rounded-2xl border border-slate-800 bg-slate-900/60 p-5 space-y-3">
                          <div className="flex items-center justify-between">
                            <span className="text-[10px] font-bold uppercase tracking-wider text-slate-400">
                              Population Drift (PSI)
                            </span>
                            <span className={`rounded px-1.5 py-0.5 text-[10px] font-bold uppercase border ${tr?.triggered ? "bg-rose-950/80 border-rose-700 text-rose-300" : "bg-slate-950 border-slate-800 text-slate-500"}`}>
                              {tr?.triggered ? "DRIFT DETECTED" : "STABLE"}
                            </span>
                          </div>
                          <div>
                            <div className="text-2xl font-black text-white font-mono">
                              {psi.toFixed(3)} <span className="text-xs font-normal text-slate-400 font-sans">PSI (threshold &gt; 0.20)</span>
                            </div>
                            <p className="text-[11px] text-slate-400 mt-1">
                              Population Stability Index comparing 7-day prediction distribution to training baseline.
                            </p>
                          </div>
                          <div className="text-[11px] font-mono text-slate-400">
                            Severity: <strong className={tr?.triggered ? "text-rose-400" : "text-emerald-400"}>{tr?.severity || "LOW"}</strong>
                          </div>
                        </div>
                      );
                    })()}
    
                    {/* Trigger 3: Performance Degradation */}
                    {(() => {
                      const tr = continuousLearningSummary?.retraining_eligibility?.triggers?.find((t) => t.trigger_type === "PERFORMANCE_DEGRADATION");
                      const drop = tr?.observed_value !== undefined && tr?.observed_value !== null ? Number(tr.observed_value) : 0.0;
                      return (
                        <div className="rounded-2xl border border-slate-800 bg-slate-900/60 p-5 space-y-3">
                          <div className="flex items-center justify-between">
                            <span className="text-[10px] font-bold uppercase tracking-wider text-slate-400">
                              Accuracy Stability
                            </span>
                            <span className={`rounded px-1.5 py-0.5 text-[10px] font-bold uppercase border ${tr?.triggered ? "bg-rose-950/80 border-rose-700 text-rose-300" : "bg-slate-950 border-slate-800 text-slate-500"}`}>
                              {tr?.triggered ? "DEGRADATION" : "OPTIMAL"}
                            </span>
                          </div>
                          <div>
                            <div className="text-2xl font-black text-white font-mono">
                              {drop >= 0 ? `-${(drop * 100).toFixed(1)}%` : `+${(Math.abs(drop) * 100).toFixed(1)}%`} <span className="text-xs font-normal text-slate-400 font-sans">Accuracy $\Delta$</span>
                            </div>
                            <p className="text-[11px] text-slate-400 mt-1">
                              Triggered if rolling 14-day recovery accuracy drops $\ge 5\%$ against validation baseline.
                            </p>
                          </div>
                          <div className="text-[11px] font-mono text-slate-400">
                            Severity: <strong className={tr?.triggered ? "text-rose-400" : "text-emerald-400"}>{tr?.severity || "LOW"}</strong>
                          </div>
                        </div>
                      );
                    })()}
    
                    {/* Trigger 4: Calibration Degradation */}
                    {(() => {
                      const tr = continuousLearningSummary?.retraining_eligibility?.triggers?.find((t) => t.trigger_type === "CALIBRATION_DEGRADATION");
                      const ece = tr?.observed_value !== undefined && tr?.observed_value !== null ? Number(tr.observed_value) : 0.038;
                      return (
                        <div className="rounded-2xl border border-slate-800 bg-slate-900/60 p-5 space-y-3">
                          <div className="flex items-center justify-between">
                            <span className="text-[10px] font-bold uppercase tracking-wider text-slate-400">
                              Expected Calibration (ECE)
                            </span>
                            <span className={`rounded px-1.5 py-0.5 text-[10px] font-bold uppercase border ${tr?.triggered ? "bg-amber-950/80 border-amber-700 text-amber-300" : "bg-slate-950 border-slate-800 text-slate-500"}`}>
                              {tr?.triggered ? "MISCALIBRATED" : "CALIBRATED"}
                            </span>
                          </div>
                          <div>
                            <div className="text-2xl font-black text-white font-mono">
                              {ece.toFixed(3)} <span className="text-xs font-normal text-slate-400 font-sans">ECE (threshold $\le 0.15$)</span>
                            </div>
                            <p className="text-[11px] text-slate-400 mt-1">
                              Reliability calibration error across 5 probability bins ($[0-0.2], \dots, [0.8-1.0]$).
                            </p>
                          </div>
                          <div className="text-[11px] font-mono text-slate-400">
                            Severity: <strong className={tr?.triggered ? "text-amber-400" : "text-emerald-400"}>{tr?.severity || "LOW"}</strong>
                          </div>
                        </div>
                      );
                    })()}
                  </div>
    
                  {/* Retraining Eligibility Diagnostic Card */}
                  {continuousLearningSummary?.retraining_eligibility && (
                    <div className="rounded-2xl border border-slate-800 bg-slate-900/40 p-4 flex flex-col sm:flex-row sm:items-center justify-between gap-4">
                      <div className="space-y-1">
                        <span className="text-[10px] font-bold uppercase tracking-wider text-slate-500">
                          Authoritative Retraining Eligibility Assessment
                        </span>
                        <p className="text-xs font-mono text-slate-200">
                          {continuousLearningSummary.retraining_eligibility.primary_reason}
                        </p>
                      </div>
                      <div className="text-[11px] font-mono text-slate-400 shrink-0">
                        Evaluated: {new Date(continuousLearningSummary.retraining_eligibility.evaluated_at).toLocaleString()}
                      </div>
                    </div>
                  )}
                </div>
    
                {/* Model Lineage Provenance DAG Section */}
                <div className="space-y-4">
                  <div className="border-b border-slate-800/80 pb-3">
                    <h2 className="text-sm font-bold uppercase tracking-wider text-slate-300">
                      Model Lineage & Provenance Progression DAG
                    </h2>
                    <p className="text-xs text-slate-400 mt-0.5">
                      Auditable lineage graph connecting Dataset Versions $\to$ Offline Training Runs $\to$ Model Artifacts $\to$ Safety Gates $\to$ Champion Deployment.
                    </p>
                  </div>
    
                  {lineageData && lineageData.lineage.length > 0 ? (
                    <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
                      {lineageData.lineage.map((node) => (
                        <div
                          key={node.model_version}
                          className="rounded-2xl border border-slate-800 bg-slate-900/70 p-5 space-y-4 relative overflow-hidden"
                        >
                          <div className="flex items-center justify-between border-b border-slate-800/60 pb-3">
                            <div>
                              <div className="flex items-center gap-2">
                                <span className="text-base font-bold text-white font-mono">{node.model_version}</span>
                                {node.model_version === lineageData.active_champion_version && (
                                  <span className="rounded bg-emerald-950 border border-emerald-700 px-1.5 py-0.2 text-[9px] font-bold text-emerald-300 uppercase">
                                    ACTIVE CHAMPION
                                  </span>
                                )}
                              </div>
                              <span className="text-[10px] text-slate-500 font-mono">Parent: {node.parent_model_version || "ROOT"}</span>
                            </div>
                            <span className={`rounded px-2 py-0.5 text-[10px] font-bold uppercase border ${getDeploymentStatusBadge(node.deployment_status)}`}>
                              {node.deployment_status}
                            </span>
                          </div>
    
                          <div className="space-y-2 text-xs font-mono">
                            <div className="flex justify-between">
                              <span className="text-slate-500">Dataset Version:</span>
                              <span className="text-cyan-400 font-bold">{node.dataset_version}</span>
                            </div>
                            <div className="flex justify-between">
                              <span className="text-slate-500">Training Run:</span>
                              <span className="text-slate-300">{node.training_run_id}</span>
                            </div>
                            <div className="flex justify-between">
                              <span className="text-slate-500">Validation:</span>
                              <span className="text-emerald-400">{node.validation_status}</span>
                            </div>
                            <div className="flex justify-between">
                              <span className="text-slate-500">Governance:</span>
                              <span className="text-indigo-300">{node.governance_status}</span>
                            </div>
                            <div className="flex justify-between pt-1 border-t border-slate-800/40">
                              <span className="text-slate-500">Artifact Hash:</span>
                              <span className="text-slate-400 text-[10px]">{node.artifact_checksum.slice(0, 16)}...</span>
                            </div>
                          </div>
                        </div>
                      ))}
                    </div>
                  ) : (
                    <div className="rounded-2xl border border-slate-800 bg-slate-900/40 p-8 text-center text-xs text-slate-500">
                      No lineage nodes recorded yet. Initial baseline will populate upon first offline training cycle.
                    </div>
                  )}
                </div>
    
                {/* 14 Continuous Learning Quality Gates Grid */}
                <div className="space-y-4">
                  <div className="flex items-center justify-between border-b border-slate-800/80 pb-3">
                    <div>
                      <h2 className="text-sm font-bold uppercase tracking-wider text-slate-300">
                        14 Continuous Learning Safety & Quality Gates
                      </h2>
                      <p className="text-xs text-slate-400 mt-0.5">
                        Deterministic quality checks verifying data sufficiency, schema integrity, checksum reproducibility, non-regression, and deployment separation.
                      </p>
                    </div>
                    {learningReadinessData && (
                      <span className={`rounded-full border px-3 py-1 text-xs font-bold uppercase tracking-wider ${learningReadinessData.can_retrain ? "bg-emerald-950/80 border-emerald-700 text-emerald-300" : "bg-amber-950/80 border-amber-700 text-amber-300"}`}>
                        {learningReadinessData.decision.replace(/_/g, " ")} ({learningReadinessData.gates.filter((g) => g.passed).length}/14 PASSED)
                      </span>
                    )}
                  </div>
    
                  {learningReadinessData ? (
                    <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3">
                      {learningReadinessData.gates.map((g) => (
                        <div
                          key={g.gate_code}
                          className={`rounded-xl border p-4 space-y-2 ${g.passed ? "border-emerald-800/40 bg-emerald-950/10" : "border-rose-800/40 bg-rose-950/10"}`}
                        >
                          <div className="flex items-center justify-between">
                            <span className="text-[11px] font-bold font-mono text-white">
                              {g.gate_code}
                            </span>
                            <span className={`rounded px-1.5 py-0.5 text-[9px] font-bold uppercase border ${g.passed ? "bg-emerald-950 border-emerald-700 text-emerald-300" : "bg-rose-950 border-rose-700 text-rose-300"}`}>
                              {g.passed ? "✓ PASS" : "✕ FAIL"}
                            </span>
                          </div>
                          <div className="text-xs text-slate-300 leading-relaxed font-sans">
                            {g.explanation}
                          </div>
                          <div className="flex items-center justify-between text-[10px] font-mono text-slate-500 pt-1 border-t border-slate-800/40">
                            <span>Threshold: {String(g.threshold)}</span>
                            <span>Observed: <strong className="text-slate-300">{String(g.observed_value)}</strong></span>
                          </div>
                        </div>
                      ))}
                    </div>
                  ) : (
                    <div className="rounded-2xl border border-slate-800 bg-slate-900/40 p-8 text-center text-xs text-slate-500">
                      Loading 14 Continuous Learning safety gates...
                    </div>
                  )}
                </div>
    
                {/* Dataset Version Registry Table */}
                <div className="space-y-4">
                  <div className="border-b border-slate-800/80 pb-3">
                    <h2 className="text-sm font-bold uppercase tracking-wider text-slate-300">
                      Immutable Dataset Version Registry
                    </h2>
                    <p className="text-xs text-slate-400 mt-0.5">
                      Point-in-time snapshot registry of resolved recovery datasets with deterministic SHA-256 integrity hashes.
                    </p>
                  </div>
    
                  <div className="overflow-x-auto rounded-2xl border border-slate-800 bg-slate-900/60">
                    <table className="w-full text-left text-xs">
                      <thead className="border-b border-slate-800 bg-slate-950/60 text-[10px] font-bold uppercase tracking-wider text-slate-400">
                        <tr>
                          <th className="px-4 py-3">Dataset Version</th>
                          <th className="px-4 py-3">Total Samples</th>
                          <th className="px-4 py-3">Positive / Negative</th>
                          <th className="px-4 py-3">Class Balance</th>
                          <th className="px-4 py-3">Schema</th>
                          <th className="px-4 py-3">SHA-256 Checksum</th>
                          <th className="px-4 py-3">Created</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-slate-800/60 font-mono">
                        {datasetsData && datasetsData.items.length > 0 ? (
                          datasetsData.items.map((ds) => (
                            <tr key={ds.dataset_id} className="hover:bg-slate-800/30">
                              <td className="px-4 py-3 font-bold text-cyan-300">{ds.dataset_version}</td>
                              <td className="px-4 py-3 text-white">{ds.sample_count}</td>
                              <td className="px-4 py-3 text-slate-300">{ds.positive_count} pos / {ds.negative_count} neg</td>
                              <td className="px-4 py-3 text-emerald-400">{(ds.class_balance * 100).toFixed(1)}%</td>
                              <td className="px-4 py-3 text-slate-400">{ds.feature_schema_version}</td>
                              <td className="px-4 py-3 text-[10px] text-slate-500">{ds.sha256_checksum.slice(0, 16)}...</td>
                              <td className="px-4 py-3 text-slate-400 font-sans">{new Date(ds.created_at).toLocaleDateString()}</td>
                            </tr>
                          ))
                        ) : (
                          <tr>
                            <td colSpan={7} className="px-4 py-6 text-center text-slate-500 font-sans">
                              No dataset versions found.
                            </td>
                          </tr>
                        )}
                      </tbody>
                    </table>
                  </div>
                </div>
    
                {/* Offline Training Run Registry Table */}
                <div className="space-y-4">
                  <div className="border-b border-slate-800/80 pb-3">
                    <h2 className="text-sm font-bold uppercase tracking-wider text-slate-300">
                      Offline Training Run Registry & Audit Ledger
                    </h2>
                    <p className="text-xs text-slate-400 mt-0.5">
                      Immutable ledger of offline retraining executions, validation results, and artifact checksums.
                    </p>
                  </div>
    
                  <div className="overflow-x-auto rounded-2xl border border-slate-800 bg-slate-900/60">
                    <table className="w-full text-left text-xs">
                      <thead className="border-b border-slate-800 bg-slate-950/60 text-[10px] font-bold uppercase tracking-wider text-slate-400">
                        <tr>
                          <th className="px-4 py-3">Training Run ID</th>
                          <th className="px-4 py-3">Candidate Model</th>
                          <th className="px-4 py-3">Dataset Version</th>
                          <th className="px-4 py-3">Train / Val Split</th>
                          <th className="px-4 py-3">Validation Metrics</th>
                          <th className="px-4 py-3">Artifact Checksum</th>
                          <th className="px-4 py-3">Status</th>
                          <th className="px-4 py-3">Timestamp</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-slate-800/60 font-mono">
                        {trainingRunsData && trainingRunsData.items.length > 0 ? (
                          trainingRunsData.items.map((run) => (
                            <tr key={run.training_run_id} className="hover:bg-slate-800/30">
                              <td className="px-4 py-3 font-bold text-white text-[11px]">{run.training_run_id}</td>
                              <td className="px-4 py-3 text-cyan-300 font-bold">{run.model_version}</td>
                              <td className="px-4 py-3 text-slate-300">{run.dataset_version}</td>
                              <td className="px-4 py-3 text-slate-400">{run.training_sample_size} / {run.validation_sample_size}</td>
                              <td className="px-4 py-3 text-slate-300 text-[11px]">
                                {run.validation_result ? (
                                  <span>
                                    Acc: <strong className="text-emerald-400">{formatPct((run.validation_result as Record<string, number>).accuracy)}</strong> | F1: <strong className="text-indigo-400">{formatNum((run.validation_result as Record<string, number>).f1_score)}</strong>
                                  </span>
                                ) : "—"}
                              </td>
                              <td className="px-4 py-3 text-[10px] text-slate-500">{run.artifact_checksum.slice(0, 16)}...</td>
                              <td className="px-4 py-3">
                                <span className="rounded bg-emerald-950/80 border border-emerald-700 px-2 py-0.5 text-[10px] font-bold text-emerald-300 uppercase">
                                  {run.status}
                                </span>
                              </td>
                              <td className="px-4 py-3 text-slate-400 font-sans text-[11px]">{new Date(run.started_at).toLocaleString()}</td>
                            </tr>
                          ))
                        ) : (
                          <tr>
                            <td colSpan={8} className="px-4 py-6 text-center text-slate-500 font-sans">
                              No training runs recorded.
                            </td>
                          </tr>
                        )}
                      </tbody>
                    </table>
                  </div>
                </div>
              </div>


            {manualTrainingModalOpen && (
    
              <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/80 backdrop-blur-sm p-4">
                <div className="w-full max-w-lg rounded-2xl border border-emerald-800/80 bg-slate-900 p-6 shadow-2xl space-y-6">
                  <div className="flex items-center justify-between border-b border-slate-800 pb-4">
                    <div>
                      <h3 className="text-base font-bold text-white">
                        Trigger Governed Offline Retraining
                      </h3>
                      <p className="text-xs text-emerald-400 mt-0.5 font-mono">
                        Candidate Generation & Offline Evaluation
                      </p>
                    </div>
                    <button
                      onClick={() => setManualTrainingModalOpen(false)}
                      className="rounded-lg p-1.5 text-slate-400 hover:bg-slate-800 hover:text-white"
                    >
                      ✕
                    </button>
                  </div>
    
                  <form
                    onSubmit={(e) => {
                      e.preventDefault();
                      handleTriggerOfflineTraining();
                    }}
                    className="space-y-4"
                  >
                    <div className="grid grid-cols-2 gap-4">
                      <div>
                        <label className="text-xs font-bold text-slate-300 block mb-1">
                          Learning Rate
                        </label>
                        <input
                          type="number"
                          step="0.01"
                          min="0.001"
                          max="1.0"
                          value={manualTrainingLr}
                          onChange={(e) => setManualTrainingLr(parseFloat(e.target.value))}
                          className="w-full rounded-xl border border-slate-800 bg-slate-950 px-3 py-2 text-xs text-slate-200 focus:border-emerald-500 focus:outline-none"
                        />
                      </div>
    
                      <div>
                        <label className="text-xs font-bold text-slate-300 block mb-1">
                          Epochs
                        </label>
                        <input
                          type="number"
                          min="10"
                          max="500"
                          value={manualTrainingEpochs}
                          onChange={(e) => setManualTrainingEpochs(parseInt(e.target.value, 10))}
                          className="w-full rounded-xl border border-slate-800 bg-slate-950 px-3 py-2 text-xs text-slate-200 focus:border-emerald-500 focus:outline-none"
                        />
                      </div>
                    </div>
    
                    <div>
                      <label className="text-xs font-bold text-slate-300 block mb-1">
                        Retraining Justification & Operator Notes
                      </label>
                      <textarea
                        rows={3}
                        value={manualTrainingNotes}
                        onChange={(e) => setManualTrainingNotes(e.target.value)}
                        placeholder="e.g., Scheduled bi-weekly offline retraining with 100+ new resolved cases."
                        className="w-full rounded-xl border border-slate-800 bg-slate-950 px-3 py-2 text-xs text-slate-200 placeholder-slate-600 focus:border-emerald-500 focus:outline-none"
                      />
                    </div>
    
                    <div className="rounded-xl border border-emerald-800/40 bg-emerald-950/20 p-3 text-[11px] text-emerald-200/90 leading-relaxed font-mono">
                      ⚡ Strictly Governed & Offline: Retraining generates a Candidate model version and evaluates it against 14 safety gates. It will NOT deploy the model or execute financial recovery actions.
                    </div>
    
                    <div className="flex items-center justify-end gap-3 border-t border-slate-800 pt-4">
                      <button
                        type="button"
                        onClick={() => setManualTrainingModalOpen(false)}
                        className="rounded-xl border border-slate-800 bg-slate-950 px-4 py-2 text-xs font-bold uppercase tracking-wider text-slate-400 hover:text-white transition"
                      >
                        Cancel
                      </button>
                      <button
                        type="submit"
                        disabled={manualTrainingLoading}
                        className="rounded-xl bg-emerald-600 px-6 py-2 text-xs font-bold uppercase tracking-wider text-white hover:bg-emerald-500 shadow-lg shadow-emerald-600/30 transition disabled:opacity-50"
                      >
                        {manualTrainingLoading ? "Retraining in progress..." : "Start Retraining Run"}
                      </button>
                    </div>
                  </form>
                </div>
              </div>
            )}
    
            {/* Phase 10A: Admin Emergency Token Revocation Modal */}


    </>
  );
}
