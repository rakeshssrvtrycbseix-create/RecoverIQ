"use client";

import React, { useCallback, useEffect, useState } from "react";
import {
  ModelScorecardResponse,
  PaginatedModelsResponse,
  approveModel,
  fetchModelScorecard,
  fetchModels,
  rejectModel,
  trainCandidateModel
} from "../../lib/api";
import { getComparisonDeltaBadge, getModelLifecycleBadge, getModelRecommendationBadge } from "./intelligenceBadges";

interface ModelLifecycleTabProps {
  userRole?: string;
}

export default function ModelLifecycleTab({ userRole = "ADMIN" }: ModelLifecycleTabProps) {
  const [error, setError] = useState<string | null>(null);

    const [modelsData, setModelsData] = useState<PaginatedModelsResponse | null>(null);
  
    const [selectedModelVersion, setSelectedModelVersion] = useState<string | null>("v1.0");
    const [selectedScorecard, setSelectedScorecard] = useState<ModelScorecardResponse | null>(null);
    const [trainModalOpen, setTrainModalOpen] = useState(false);
    const [trainLearningRate, setTrainLearningRate] = useState(0.05);
    const [trainEpochs, setTrainEpochs] = useState(50);
    const [trainNotes, setTrainNotes] = useState("");
    const [modelApproveModalOpen, setModelApproveModalOpen] = useState(false);
    const [modelRejectModalOpen, setModelRejectModalOpen] = useState(false);
    const [modelActionNotes, setModelActionNotes] = useState("");
    const [modelRejectReason, setModelRejectReason] = useState("");
    const [modelActionLoading, setModelActionLoading] = useState(false);
    const [modelSuccessMsg, setModelSuccessMsg] = useState<string | null>(null);
    const [modelStatusFilter, setModelStatusFilter] = useState<string>("ALL");
  

    const loadModelScorecard = async (version: string) => {
      try {
        const sc = await fetchModelScorecard(version);
        setSelectedScorecard(sc);
        setSelectedModelVersion(version);
      } catch (err) {
        console.error("Failed to load model scorecard", err);
      } finally {
      }
    };
  
    const handleTrainCandidate = async () => {
      setModelActionLoading(true);
      setError(null);
      try {
        const sc = await trainCandidateModel({
          model_name: "recovery_probability",
          parent_version: "v1.0",
          learning_rate: trainLearningRate,
          epochs: trainEpochs,
          notes: trainNotes || undefined,
        });
        setSelectedScorecard(sc);
        setSelectedModelVersion(sc.challenger_version);
        setTrainModalOpen(false);
        setModelSuccessMsg(`Candidate model "${sc.challenger_version}" trained and evaluated offline. Status: REVIEW_REQUIRED.`);
        await loadModelsData();
      } catch (err) {
        setError(err instanceof Error ? err.message : "Candidate training failed");
      } finally {
        setModelActionLoading(false);
      }
    };
  
    const handleApproveModel = async () => {
      if (!selectedModelVersion) return;
      setModelActionLoading(true);
      setError(null);
      try {
        const updated = await approveModel(selectedModelVersion, modelActionNotes || undefined);
        setModelApproveModalOpen(false);
        setModelSuccessMsg(`Model "${updated.model_version}" successfully APPROVED -> PROMOTION_READY. Notice: Model will remain standby until explicit rollout deployment.`);
        await loadModelsData();
        await loadModelScorecard(selectedModelVersion);
      } catch (err) {
        setError(err instanceof Error ? err.message : "Model approval failed");
      } finally {
        setModelActionLoading(false);
      }
    };
  
    const handleRejectModel = async () => {
      if (!selectedModelVersion || !modelRejectReason) return;
      setModelActionLoading(true);
      setError(null);
      try {
        const updated = await rejectModel(selectedModelVersion, modelRejectReason);
        setModelRejectModalOpen(false);
        setModelSuccessMsg(`Model "${updated.model_version}" REJECTED.`);
        await loadModelsData();
        await loadModelScorecard(selectedModelVersion);
      } catch (err) {
        setError(err instanceof Error ? err.message : "Model rejection failed");
      } finally {
        setModelActionLoading(false);
      }
    };

  const loadModelsData = useCallback(async () => {
    try {
      const res = await fetchModels();
      setModelsData(res);
      if (res && res.items && res.items.length > 0 && !selectedModelVersion) {
        setSelectedModelVersion(res.items[0].model_version);
        loadModelScorecard(res.items[0].model_version);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load Models");
    }
  }, [selectedModelVersion]);

    useEffect(() => {
    let ignore = false;
    async function execute() {
      if (!ignore) {
        await loadModelsData();
      }
    }
    void execute();
    return () => {
      ignore = true;
    };
  }, [loadModelsData]);

  return (
    <>
      {error && (
        <div className="rounded-xl border border-rose-800/40 bg-rose-950/40 p-4 text-xs text-rose-300">
          {error}
        </div>
      )}

      {modelSuccessMsg && (
        <div className="rounded-xl border border-emerald-800/60 bg-emerald-950/40 p-4 text-xs text-emerald-300 flex items-center justify-between shadow-lg">
          <span>{modelSuccessMsg}</span>
          <button onClick={() => setModelSuccessMsg(null)} className="text-emerald-400 hover:text-white font-bold ml-4">✕</button>
        </div>
      )}
    
              {/* =========================================================================
                 TAB 0: GOVERNED MODEL TRAINING & MODEL LIFECYCLE (Phase 9I)
                 ========================================================================= */}
              <div className="space-y-8">
                {/* Mandatory Governance & Zero-Execution Disclaimer Banner */}
                <div className="rounded-2xl border border-indigo-800/60 bg-indigo-950/20 p-4 flex items-start gap-3">
                  <span className="rounded bg-indigo-900/80 px-2 py-0.5 text-[10px] font-bold uppercase tracking-wider text-indigo-200 border border-indigo-700/60 shrink-0">
                    PHASE 9I MODEL GOVERNANCE
                  </span>
                  <div className="text-xs text-indigo-200/90 leading-relaxed space-y-1">
                    <p className="font-semibold">
                      GOVERNED MODEL TRAINING, CHAMPION–CHALLENGER EVALUATION & MODEL LIFECYCLE
                    </p>
                    <p className="text-[11px] text-indigo-300/80">
                      Offline machine-learning model lifecycle for RecoverIQ. Resolved historical cases are deterministically extracted with pre-decision features to train candidate models offline. Challenger models are validated against the active production champion across 10 deterministic governance quality gates. Approval transitions candidate to PROMOTION_READY status; Phase 9I strictly executes zero automatic model activations or financial mutations.
                    </p>
                  </div>
                </div>
    
                {/* Quick Metrics Bar & Action Header */}
                <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
                  <div className="flex flex-wrap items-center gap-3">
                    <div className="rounded-xl border border-slate-800 bg-slate-900/80 px-4 py-2 text-xs font-mono">
                      <span className="text-[10px] text-slate-500 uppercase block font-bold">Registered Models</span>
                      <strong className="text-white text-sm">{modelsData?.total || 1}</strong>
                    </div>
                    <div className="rounded-xl border border-slate-800 bg-slate-900/80 px-4 py-2 text-xs font-mono">
                      <span className="text-[10px] text-slate-500 uppercase block font-bold">Active Champion</span>
                      <strong className="text-emerald-400 text-sm">{modelsData?.active_champion_version || "v1.0"}</strong>
                    </div>
                    <div className="rounded-xl border border-slate-800 bg-slate-900/80 px-4 py-2 text-xs font-mono">
                      <span className="text-[10px] text-slate-500 uppercase block font-bold">Promotion-Ready Standby</span>
                      <strong className="text-purple-300 text-sm">
                        {modelsData?.promotion_ready_version || "None (Standby)"}
                      </strong>
                    </div>
                    <div className="rounded-xl border border-slate-800 bg-slate-900/80 px-4 py-2 text-xs font-mono">
                      <span className="text-[10px] text-slate-500 uppercase block font-bold">Feature Schema</span>
                      <strong className="text-cyan-300 text-sm">v1 (Zero PII)</strong>
                    </div>
                  </div>
    
                  <div className="flex items-center gap-3">
                    <select
                      value={modelStatusFilter}
                      onChange={(e) => {
                        setModelStatusFilter(e.target.value);
                        fetchModels(e.target.value).then((res) => setModelsData(res));
                      }}
                      className="rounded-xl border border-slate-800 bg-slate-900 px-3 py-2 text-xs font-semibold text-slate-300 focus:border-indigo-500 focus:outline-none"
                    >
                      <option value="ALL">All Lifecycle Statuses</option>
                      <option value="ACTIVE">Active Champion</option>
                      <option value="PROMOTION_READY">Promotion Ready</option>
                      <option value="REVIEW_REQUIRED">Review Required</option>
                      <option value="APPROVED">Approved</option>
                      <option value="REJECTED">Rejected</option>
                      <option value="RETIRED">Retired</option>
                    </select>
    
                    {(userRole === "operator" || userRole === "admin") && (
                      <button
                        onClick={() => setTrainModalOpen(true)}
                        className="flex items-center gap-2 rounded-xl bg-indigo-600 px-4 py-2 text-xs font-bold uppercase tracking-wider text-white hover:bg-indigo-500 shadow-lg shadow-indigo-600/30 transition"
                      >
                        <span>⚡ Train Candidate Model (Offline)</span>
                      </button>
                    )}
                  </div>
                </div>
    
                {/* Scorecard & Champion-Challenger Comparison Section */}
                {selectedScorecard && (
                  <div className="space-y-6">
                    {/* Comparison Overview Header */}
                    <div className="rounded-2xl border border-slate-800 bg-slate-900/60 p-6 space-y-6">
                      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between border-b border-slate-800/80 pb-4">
                        <div>
                          <div className="flex items-center gap-3">
                            <h2 className="text-base font-bold text-white">
                              Champion vs Challenger Validation Scorecard
                            </h2>
                            <span
                              className={`rounded-full border px-2.5 py-0.5 text-xs font-mono font-bold uppercase tracking-wider ${getModelLifecycleBadge(
                                selectedScorecard.lifecycle_status
                              )}`}
                            >
                              {selectedScorecard.lifecycle_status}
                            </span>
                            <span
                              className={`rounded-full border px-2.5 py-0.5 text-xs font-mono font-bold uppercase tracking-wider ${getComparisonDeltaBadge(
                                selectedScorecard.comparison.overall_status
                              )}`}
                            >
                              OVERALL: {selectedScorecard.comparison.overall_status}
                            </span>
                          </div>
                          <p className="text-xs text-slate-400 mt-1">
                            Challenger <span className="font-mono text-white font-bold">{selectedScorecard.challenger_version}</span> evaluated against Active Champion <span className="font-mono text-emerald-400 font-bold">{selectedScorecard.parent_champion_version}</span> on validation partition (N = {selectedScorecard.challenger_metrics.sample_size}).
                          </p>
                        </div>
    
                        {/* Human Review Actions */}
                        {selectedScorecard.lifecycle_status === "REVIEW_REQUIRED" && (userRole === "operator" || userRole === "admin") && (
                          <div className="flex items-center gap-2">
                            <button
                              onClick={() => setModelApproveModalOpen(true)}
                              className="rounded-xl bg-emerald-600 px-4 py-1.5 text-xs font-bold uppercase tracking-wider text-white hover:bg-emerald-500 shadow-lg shadow-emerald-600/30 transition"
                            >
                              ✓ Approve Candidate
                            </button>
                            <button
                              onClick={() => setModelRejectModalOpen(true)}
                              className="rounded-xl bg-rose-600 px-4 py-1.5 text-xs font-bold uppercase tracking-wider text-white hover:bg-rose-500 shadow-lg shadow-rose-600/30 transition"
                            >
                              ✕ Reject Candidate
                            </button>
                          </div>
                        )}
                      </div>
    
                      {/* Side-by-Side Model Comparison Grid */}
                      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                        {/* Champion Model Card */}
                        <div className="rounded-xl border border-slate-800 bg-slate-950/60 p-5 space-y-4">
                          <div className="flex items-center justify-between border-b border-slate-800 pb-3">
                            <div>
                              <span className="text-[10px] text-slate-500 uppercase font-bold tracking-wider">Baseline Champion</span>
                              <h3 className="text-sm font-black text-emerald-400 font-mono">
                                {selectedScorecard.parent_champion_version} (ACTIVE)
                              </h3>
                            </div>
                            <span className="rounded bg-emerald-950/80 px-2 py-0.5 text-[10px] font-bold text-emerald-300 border border-emerald-800/60">
                              PRODUCTION
                            </span>
                          </div>
    
                          <div className="grid grid-cols-2 gap-3 text-xs">
                            <div className="rounded-lg bg-slate-900/60 p-2.5 border border-slate-800/60">
                              <span className="text-[10px] text-slate-500 uppercase block font-semibold">Accuracy</span>
                              <span className="text-sm font-bold font-mono text-white">
                                {(selectedScorecard.champion_metrics.accuracy * 100).toFixed(1)}%
                              </span>
                            </div>
                            <div className="rounded-lg bg-slate-900/60 p-2.5 border border-slate-800/60">
                              <span className="text-[10px] text-slate-500 uppercase block font-semibold">F1 Score</span>
                              <span className="text-sm font-bold font-mono text-white">
                                {(selectedScorecard.champion_metrics.f1_score * 100).toFixed(1)}%
                              </span>
                            </div>
                            <div className="rounded-lg bg-slate-900/60 p-2.5 border border-slate-800/60">
                              <span className="text-[10px] text-slate-500 uppercase block font-semibold">Brier Score</span>
                              <span className="text-sm font-bold font-mono text-slate-300">
                                {selectedScorecard.champion_metrics.brier_score.toFixed(4)}
                              </span>
                            </div>
                            <div className="rounded-lg bg-slate-900/60 p-2.5 border border-slate-800/60">
                              <span className="text-[10px] text-slate-500 uppercase block font-semibold">Calibration Error (ECE)</span>
                              <span className="text-sm font-bold font-mono text-slate-300">
                                {selectedScorecard.champion_metrics.calibration_error.toFixed(4)}
                              </span>
                            </div>
                            <div className="rounded-lg bg-slate-900/60 p-2.5 border border-slate-800/60">
                              <span className="text-[10px] text-slate-500 uppercase block font-semibold">ROC-AUC</span>
                              <span className="text-sm font-bold font-mono text-slate-300">
                                {selectedScorecard.champion_metrics.roc_auc.toFixed(4)}
                              </span>
                            </div>
                            <div className="rounded-lg bg-slate-900/60 p-2.5 border border-slate-800/60">
                              <span className="text-[10px] text-slate-500 uppercase block font-semibold">PR-AUC</span>
                              <span className="text-sm font-bold font-mono text-slate-300">
                                {selectedScorecard.champion_metrics.pr_auc.toFixed(4)}
                              </span>
                            </div>
                          </div>
                        </div>
    
                        {/* Challenger Model Card */}
                        <div className="rounded-xl border border-indigo-800/50 bg-indigo-950/10 p-5 space-y-4">
                          <div className="flex items-center justify-between border-b border-slate-800 pb-3">
                            <div>
                              <span className="text-[10px] text-slate-500 uppercase font-bold tracking-wider">Candidate Challenger</span>
                              <h3 className="text-sm font-black text-indigo-400 font-mono">
                                {selectedScorecard.challenger_version}
                              </h3>
                            </div>
                            <span className={`rounded px-2 py-0.5 text-[10px] font-bold border ${getModelLifecycleBadge(selectedScorecard.lifecycle_status)}`}>
                              {selectedScorecard.lifecycle_status}
                            </span>
                          </div>
    
                          <div className="grid grid-cols-2 gap-3 text-xs">
                            <div className="rounded-lg bg-slate-900/60 p-2.5 border border-slate-800/60">
                              <span className="text-[10px] text-slate-500 uppercase block font-semibold">Accuracy</span>
                              <div className="flex items-center justify-between">
                                <span className="text-sm font-bold font-mono text-white">
                                  {(selectedScorecard.challenger_metrics.accuracy * 100).toFixed(1)}%
                                </span>
                                <span className="text-[10px] font-mono text-emerald-400">
                                  {(selectedScorecard.challenger_metrics.accuracy - selectedScorecard.champion_metrics.accuracy >= 0 ? "+" : "")}
                                  {((selectedScorecard.challenger_metrics.accuracy - selectedScorecard.champion_metrics.accuracy) * 100).toFixed(1)}%
                                </span>
                              </div>
                            </div>
                            <div className="rounded-lg bg-slate-900/60 p-2.5 border border-slate-800/60">
                              <span className="text-[10px] text-slate-500 uppercase block font-semibold">F1 Score</span>
                              <div className="flex items-center justify-between">
                                <span className="text-sm font-bold font-mono text-white">
                                  {(selectedScorecard.challenger_metrics.f1_score * 100).toFixed(1)}%
                                </span>
                                <span className="text-[10px] font-mono text-emerald-400">
                                  {(selectedScorecard.challenger_metrics.f1_score - selectedScorecard.champion_metrics.f1_score >= 0 ? "+" : "")}
                                  {((selectedScorecard.challenger_metrics.f1_score - selectedScorecard.champion_metrics.f1_score) * 100).toFixed(1)}%
                                </span>
                              </div>
                            </div>
                            <div className="rounded-lg bg-slate-900/60 p-2.5 border border-slate-800/60">
                              <span className="text-[10px] text-slate-500 uppercase block font-semibold">Brier Score (MSE)</span>
                              <div className="flex items-center justify-between">
                                <span className="text-sm font-bold font-mono text-slate-300">
                                  {selectedScorecard.challenger_metrics.brier_score.toFixed(4)}
                                </span>
                                <span className="text-[10px] font-mono text-emerald-400">
                                  {(selectedScorecard.challenger_metrics.brier_score - selectedScorecard.champion_metrics.brier_score <= 0 ? "" : "+")}
                                  {(selectedScorecard.challenger_metrics.brier_score - selectedScorecard.champion_metrics.brier_score).toFixed(4)}
                                </span>
                              </div>
                            </div>
                            <div className="rounded-lg bg-slate-900/60 p-2.5 border border-slate-800/60">
                              <span className="text-[10px] text-slate-500 uppercase block font-semibold">Calibration Error (ECE)</span>
                              <div className="flex items-center justify-between">
                                <span className="text-sm font-bold font-mono text-slate-300">
                                  {selectedScorecard.challenger_metrics.calibration_error.toFixed(4)}
                                </span>
                                <span className="text-[10px] font-mono text-emerald-400">
                                  {(selectedScorecard.challenger_metrics.calibration_error - selectedScorecard.champion_metrics.calibration_error <= 0 ? "" : "+")}
                                  {(selectedScorecard.challenger_metrics.calibration_error - selectedScorecard.champion_metrics.calibration_error).toFixed(4)}
                                </span>
                              </div>
                            </div>
                            <div className="rounded-lg bg-slate-900/60 p-2.5 border border-slate-800/60">
                              <span className="text-[10px] text-slate-500 uppercase block font-semibold">ROC-AUC</span>
                              <span className="text-sm font-bold font-mono text-slate-300">
                                {selectedScorecard.challenger_metrics.roc_auc.toFixed(4)}
                              </span>
                            </div>
                            <div className="rounded-lg bg-slate-900/60 p-2.5 border border-slate-800/60">
                              <span className="text-[10px] text-slate-500 uppercase block font-semibold">PR-AUC</span>
                              <span className="text-sm font-bold font-mono text-slate-300">
                                {selectedScorecard.challenger_metrics.pr_auc.toFixed(4)}
                              </span>
                            </div>
                          </div>
                        </div>
                      </div>
    
                      {/* Governance Decision Recommendation Box */}
                      <div className="rounded-xl border border-indigo-800/60 bg-indigo-950/30 p-4 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
                        <div className="space-y-1">
                          <div className="flex items-center gap-2">
                            <span className="text-[10px] uppercase font-bold text-slate-400">Governance Recommendation:</span>
                            <span className={`rounded px-2 py-0.5 text-xs font-bold font-mono border ${getModelRecommendationBadge(selectedScorecard.recommendation)}`}>
                              {selectedScorecard.recommendation}
                            </span>
                          </div>
                          <p className="text-xs text-slate-300">
                            Recommendation confidence: <strong className="text-white">{(selectedScorecard.confidence * 100).toFixed(0)}%</strong> • Causal Rigor: <strong className="text-indigo-300 font-mono">{selectedScorecard.evidence_level}</strong>
                          </p>
                        </div>
    
                        <div className="text-right text-[11px] font-mono text-slate-400 space-y-0.5">
                          <div>Dataset SHA-256: <span className="text-slate-200">{selectedScorecard.dataset_metadata.dataset_hash.slice(0, 16)}...</span></div>
                          <div>Artifact SHA-256: <span className="text-indigo-300">{selectedScorecard.model_artifact_hash.slice(0, 16)}...</span></div>
                        </div>
                      </div>
                    </div>
    
                    {/* 10 Model Quality Gates Grid */}
                    <div className="rounded-2xl border border-slate-800 bg-slate-900/60 p-6 space-y-4">
                      <div className="flex items-center justify-between border-b border-slate-800/80 pb-3">
                        <div>
                          <h3 className="text-sm font-bold text-white">
                            10 Governed Model Quality Gates
                          </h3>
                          <p className="text-xs text-slate-400 mt-0.5">
                            Deterministic pre-promotion validation gates ensuring non-regression, calibration integrity, and zero data leakage.
                          </p>
                        </div>
                        <span className="text-xs font-mono font-bold text-emerald-400">
                          {selectedScorecard.gates.filter((g) => g.passed).length} / {selectedScorecard.gates.length} PASSED
                        </span>
                      </div>
    
                      <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                        {selectedScorecard.gates.map((g) => (
                          <div
                            key={g.gate_code}
                            className={`rounded-xl border p-3.5 space-y-1.5 ${
                              g.passed
                                ? "border-emerald-900/50 bg-emerald-950/10"
                                : "border-rose-900/50 bg-rose-950/20"
                            }`}
                          >
                            <div className="flex items-center justify-between">
                              <span className="font-mono text-xs font-bold text-white">
                                {g.gate_code}
                              </span>
                              <span
                                className={`rounded px-2 py-0.5 text-[10px] font-bold uppercase tracking-wider ${
                                  g.passed
                                    ? "bg-emerald-950 border border-emerald-700/60 text-emerald-300"
                                    : "bg-rose-950 border border-rose-700/60 text-rose-300"
                                }`}
                              >
                                {g.passed ? "✓ PASS" : "✕ FAIL"}
                              </span>
                            </div>
                            <p className="text-xs text-slate-300">{g.explanation}</p>
                            <div className="text-[10px] font-mono text-slate-500 pt-1 flex items-center justify-between">
                              <span>Observed: <strong className="text-slate-300">{String(g.observed_value)}</strong></span>
                              <span>Threshold: <strong className="text-slate-300">{String(g.threshold)}</strong></span>
                            </div>
                          </div>
                        ))}
                      </div>
                    </div>
                  </div>
                )}
    
                {/* Model Registry List Table */}
                <div className="rounded-2xl border border-slate-800 bg-slate-900/60 p-6 space-y-4">
                  <div className="flex items-center justify-between border-b border-slate-800/80 pb-3">
                    <div>
                      <h3 className="text-sm font-bold text-white">
                        Governed Model Registry
                      </h3>
                      <p className="text-xs text-slate-400 mt-0.5">
                        Immutable event-sourced version registry with deterministic artifact hashes.
                      </p>
                    </div>
                    <span className="text-xs font-mono text-slate-400">
                      {modelsData?.total || 0} Models Registered
                    </span>
                  </div>
    
                  <div className="overflow-x-auto">
                    <table className="w-full text-left text-xs">
                      <thead className="border-b border-slate-800 text-[10px] uppercase font-bold text-slate-400">
                        <tr>
                          <th className="pb-2.5 font-bold">Model Version</th>
                          <th className="pb-2.5 font-bold">Status</th>
                          <th className="pb-2.5 font-bold">Architecture</th>
                          <th className="pb-2.5 font-bold">Training Size</th>
                          <th className="pb-2.5 font-bold">Validation Size</th>
                          <th className="pb-2.5 font-bold">Artifact Hash</th>
                          <th className="pb-2.5 font-bold">Created At</th>
                          <th className="pb-2.5 font-bold text-right">Scorecard</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-slate-800/60 font-mono">
                        {modelsData?.items.map((m) => (
                          <tr key={m.model_version} className="hover:bg-slate-900/40 transition">
                            <td className="py-3 font-bold text-white flex items-center gap-2">
                              <span>{m.model_version}</span>
                              {m.model_version === modelsData.active_champion_version && (
                                <span className="rounded bg-emerald-950 px-1.5 py-0.2 text-[9px] text-emerald-400 border border-emerald-800/40">
                                  ACTIVE CHAMPION
                                </span>
                              )}
                            </td>
                            <td className="py-3">
                              <span
                                className={`rounded px-2 py-0.5 text-[10px] font-bold ${getModelLifecycleBadge(
                                  m.lifecycle_status
                                )}`}
                              >
                                {m.lifecycle_status}
                              </span>
                            </td>
                            <td className="py-3 text-slate-300">{m.model_type}</td>
                            <td className="py-3 text-slate-300">{m.training_sample_size} cases</td>
                            <td className="py-3 text-slate-300">{m.validation_sample_size} cases</td>
                            <td className="py-3 text-slate-400">
                              {m.model_artifact_hash ? `${m.model_artifact_hash.slice(0, 10)}...` : "—"}
                            </td>
                            <td className="py-3 text-slate-400">
                              {new Date(m.created_at).toLocaleDateString()}
                            </td>
                            <td className="py-3 text-right">
                              <button
                                onClick={() => loadModelScorecard(m.model_version)}
                                className="rounded-lg border border-slate-800 bg-slate-900 px-3 py-1 text-[11px] font-semibold text-indigo-400 hover:bg-slate-800 hover:text-indigo-300 transition"
                              >
                                View Scorecard
                              </button>
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              </div>


            {trainModalOpen && (
              <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/80 backdrop-blur-sm p-4">
                <div className="w-full max-w-lg rounded-2xl border border-indigo-800/80 bg-slate-900 p-6 shadow-2xl space-y-6">
                  <div className="flex items-center justify-between border-b border-slate-800 pb-4">
                    <div>
                      <h3 className="text-base font-bold text-white">
                        Train Candidate Model (Offline)
                      </h3>
                      <p className="text-xs text-slate-400 mt-0.5">
                        Extract resolved cases, evaluate against Champion v1.0, and run quality gates.
                      </p>
                    </div>
                    <button
                      onClick={() => setTrainModalOpen(false)}
                      className="rounded-lg p-1.5 text-slate-400 hover:bg-slate-800 hover:text-white"
                    >
                      ✕
                    </button>
                  </div>
    
                  <form
                    onSubmit={(e) => {
                      e.preventDefault();
                      handleTrainCandidate();
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
                          value={trainLearningRate}
                          onChange={(e) => setTrainLearningRate(parseFloat(e.target.value))}
                          className="w-full rounded-xl border border-slate-800 bg-slate-950 px-3 py-2 text-xs text-slate-200 focus:border-indigo-500 focus:outline-none"
                        />
                      </div>
    
                      <div>
                        <label className="text-xs font-bold text-slate-300 block mb-1">
                          Training Epochs
                        </label>
                        <input
                          type="number"
                          min="10"
                          max="500"
                          value={trainEpochs}
                          onChange={(e) => setTrainEpochs(parseInt(e.target.value, 10))}
                          className="w-full rounded-xl border border-slate-800 bg-slate-950 px-3 py-2 text-xs text-slate-200 focus:border-indigo-500 focus:outline-none"
                        />
                      </div>
                    </div>
    
                    <div>
                      <label className="text-xs font-bold text-slate-300 block mb-1">
                        Training Notes (Optional)
                      </label>
                      <textarea
                        value={trainNotes}
                        onChange={(e) => setTrainNotes(e.target.value)}
                        placeholder="e.g., Retraining candidate model with updated resolved cases dataset."
                        rows={2}
                        className="w-full rounded-xl border border-slate-800 bg-slate-950 px-3 py-2 text-xs text-slate-200 placeholder-slate-600 focus:border-indigo-500 focus:outline-none"
                      />
                    </div>
    
                    <div className="rounded-xl border border-indigo-800/40 bg-indigo-950/20 p-3 text-[11px] text-indigo-200/90 leading-relaxed font-mono">
                      ✓ Strict zero-leakage guarantee. Zero financial executions. Candidate will enter REVIEW_REQUIRED status.
                    </div>
    
                    <div className="flex items-center justify-end gap-3 border-t border-slate-800 pt-4">
                      <button
                        type="button"
                        onClick={() => setTrainModalOpen(false)}
                        className="rounded-xl border border-slate-800 bg-slate-950 px-4 py-2 text-xs font-bold uppercase tracking-wider text-slate-400 hover:text-white transition"
                      >
                        Cancel
                      </button>
                      <button
                        type="submit"
                        disabled={modelActionLoading}
                        className="rounded-xl bg-indigo-600 px-6 py-2 text-xs font-bold uppercase tracking-wider text-white hover:bg-indigo-500 shadow-lg shadow-indigo-600/30 transition disabled:opacity-50"
                      >
                        {modelActionLoading ? "Training & Validating..." : "Start Offline Training"}
                      </button>
                    </div>
                  </form>
                </div>
              </div>
            )}
    
            {/* Phase 9I: Model Approval Modal */}
            {modelApproveModalOpen && (
              <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/80 backdrop-blur-sm p-4">
                <div className="w-full max-w-md rounded-2xl border border-emerald-800/80 bg-slate-900 p-6 shadow-2xl space-y-6">
                  <div className="flex items-center justify-between border-b border-slate-800 pb-4">
                    <div>
                      <h3 className="text-base font-bold text-white">
                        Approve Candidate Model
                      </h3>
                      <p className="text-xs text-emerald-400 mt-0.5 font-mono">
                        Model: {selectedModelVersion}
                      </p>
                    </div>
                    <button
                      onClick={() => setModelApproveModalOpen(false)}
                      className="rounded-lg p-1.5 text-slate-400 hover:bg-slate-800 hover:text-white"
                    >
                      ✕
                    </button>
                  </div>
    
                  <form
                    onSubmit={(e) => {
                      e.preventDefault();
                      handleApproveModel();
                    }}
                    className="space-y-4"
                  >
                    <div>
                      <label className="text-xs font-bold text-slate-300 block mb-1">
                        Approval Notes
                      </label>
                      <textarea
                        value={modelActionNotes}
                        onChange={(e) => setModelActionNotes(e.target.value)}
                        placeholder="e.g., Verified non-regression across all 10 gates. Approved for promotion readiness."
                        rows={3}
                        className="w-full rounded-xl border border-slate-800 bg-slate-950 px-3 py-2 text-xs text-slate-200 placeholder-slate-600 focus:border-emerald-500 focus:outline-none"
                      />
                    </div>
    
                    <div className="rounded-xl border border-emerald-800/40 bg-emerald-950/20 p-3 text-[11px] text-emerald-200/90 leading-relaxed font-mono">
                      ✓ Model transitions to PROMOTION_READY. Notice: Model will remain standby until explicit rollout deployment.
                    </div>
    
                    <div className="flex items-center justify-end gap-3 border-t border-slate-800 pt-4">
                      <button
                        type="button"
                        onClick={() => setModelApproveModalOpen(false)}
                        className="rounded-xl border border-slate-800 bg-slate-950 px-4 py-2 text-xs font-bold uppercase tracking-wider text-slate-400 hover:text-white transition"
                      >
                        Cancel
                      </button>
                      <button
                        type="submit"
                        disabled={modelActionLoading}
                        className="rounded-xl bg-emerald-600 px-6 py-2 text-xs font-bold uppercase tracking-wider text-white hover:bg-emerald-500 shadow-lg shadow-emerald-600/30 transition disabled:opacity-50"
                      >
                        {modelActionLoading ? "Approving..." : "Confirm Approval"}
                      </button>
                    </div>
                  </form>
                </div>
              </div>
            )}
    
            {/* Phase 9I: Model Rejection Modal */}
            {modelRejectModalOpen && (
              <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/80 backdrop-blur-sm p-4">
                <div className="w-full max-w-md rounded-2xl border border-rose-800/80 bg-slate-900 p-6 shadow-2xl space-y-6">
                  <div className="flex items-center justify-between border-b border-slate-800 pb-4">
                    <div>
                      <h3 className="text-base font-bold text-white">
                        Reject Candidate Model
                      </h3>
                      <p className="text-xs text-rose-400 mt-0.5 font-mono">
                        Model: {selectedModelVersion}
                      </p>
                    </div>
                    <button
                      onClick={() => setModelRejectModalOpen(false)}
                      className="rounded-lg p-1.5 text-slate-400 hover:bg-slate-800 hover:text-white"
                    >
                      ✕
                    </button>
                  </div>
    
                  <form
                    onSubmit={(e) => {
                      e.preventDefault();
                      handleRejectModel();
                    }}
                    className="space-y-4"
                  >
                    <div>
                      <label className="text-xs font-bold text-slate-300 block mb-1">
                        Rejection Reason *
                      </label>
                      <textarea
                        required
                        value={modelRejectReason}
                        onChange={(e) => setModelRejectReason(e.target.value)}
                        placeholder="e.g., F1 regression exceeds 2% threshold or calibration error unacceptable."
                        rows={3}
                        className="w-full rounded-xl border border-slate-800 bg-slate-950 px-3 py-2 text-xs text-slate-200 placeholder-slate-600 focus:border-rose-500 focus:outline-none"
                      />
                    </div>
    
                    <div className="rounded-xl border border-rose-800/40 bg-rose-950/20 p-3 text-[11px] text-rose-200/90 leading-relaxed font-mono">
                      ✕ Candidate model will transition to REJECTED and cannot be promoted.
                    </div>
    
                    <div className="flex items-center justify-end gap-3 border-t border-slate-800 pt-4">
                      <button
                        type="button"
                        onClick={() => setModelRejectModalOpen(false)}
                        className="rounded-xl border border-slate-800 bg-slate-950 px-4 py-2 text-xs font-bold uppercase tracking-wider text-slate-400 hover:text-white transition"
                      >
                        Cancel
                      </button>
                      <button
                        type="submit"
                        disabled={modelActionLoading || !modelRejectReason}
                        className="rounded-xl bg-rose-600 px-6 py-2 text-xs font-bold uppercase tracking-wider text-white hover:bg-rose-500 shadow-lg shadow-rose-600/30 transition disabled:opacity-50"
                      >
                        {modelActionLoading ? "Rejecting..." : "Confirm Rejection"}
                      </button>
                    </div>
                  </form>
                </div>
              </div>
            )}
            {/* =========================================================================
                PHASE 9J MODALS: Deployment, Shadow, Canary, Activate, Rollback
                ========================================================================= */}
    
            {/* Phase 9J: Create Model Deployment Modal */}


    </>
  );
}
