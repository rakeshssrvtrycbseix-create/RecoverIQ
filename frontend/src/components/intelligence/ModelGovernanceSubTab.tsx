"use client";

import React, { useCallback, useEffect, useState } from "react";
import {
  ModelGovernanceResponse,
  fetchModelGovernance
} from "../../lib/api";
import { formatDelta, formatNum, formatPct, getDriftBadge } from "./intelligenceBadges";

export default function ModelGovernanceSubTab() {
  const [error, setError] = useState<string | null>(null);

    const [govData, setGovData] = useState<ModelGovernanceResponse | null>(null);

  const loadGovData = useCallback(async () => {
    try {
      const res = await fetchModelGovernance();
      setGovData(res);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load Model Governance data");
    }
  }, []);

    useEffect(() => {
    let ignore = false;
    async function execute() {
      if (!ignore) {
        await loadGovData();
      }
    }
    void execute();
    return () => {
      ignore = true;
    };
  }, [loadGovData]);

  if (!govData) {
    return (
      <div className="flex items-center justify-center min-h-[300px]">
        <div className="text-slate-400 text-sm font-mono">Loading model governance data...</div>
      </div>
    );
  }

  return (
    <>
      {error && (
        <div className="rounded-xl border border-rose-800/40 bg-rose-950/40 p-4 text-xs text-rose-300">
          {error}
        </div>
      )}

              {/* =========================================================================
                 TAB 3: MODEL GOVERNANCE & DRIFT (Phase 9B)
                 ========================================================================= */}
              <div className="space-y-8">
                <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 lg:grid-cols-6">
                  <div className="rounded-2xl border border-slate-800/80 bg-slate-900/60 p-4">
                    <span className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider">
                      Health Status
                    </span>
                    <p className="mt-1 text-lg font-black text-white">
                      {govData.status.replace("_", " ")}
                    </p>
                    <span className="text-[10px] text-slate-400">
                      {govData.model_name}:{govData.model_version}
                    </span>
                  </div>
    
                  <div className="rounded-2xl border border-slate-800/80 bg-slate-900/60 p-4">
                    <span className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider">
                      Sample Size
                    </span>
                    <p className="mt-1 text-2xl font-black text-indigo-300">
                      {govData.sample_size}
                    </p>
                    <span className="text-[10px] text-slate-400">
                      Min Req: {govData.minimum_required_sample_size}
                    </span>
                  </div>
    
                  <div className="rounded-2xl border border-slate-800/80 bg-slate-900/60 p-4">
                    <span className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider">
                      Accuracy Delta (Δ)
                    </span>
                    <p
                      className={`mt-1 text-2xl font-black ${
                        (govData.performance_comparison.accuracy_delta || 0) < -0.05
                          ? "text-rose-400"
                          : "text-emerald-400"
                      }`}
                    >
                      {formatDelta(govData.performance_comparison.accuracy_delta)}
                    </p>
                    <span className="text-[10px] text-slate-400">Recent vs Baseline</span>
                  </div>
    
                  <div className="rounded-2xl border border-slate-800/80 bg-slate-900/60 p-4">
                    <span className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider">
                      Brier Delta (Δ)
                    </span>
                    <p
                      className={`mt-1 text-2xl font-black ${
                        (govData.performance_comparison.brier_delta || 0) > 0.05
                          ? "text-rose-400"
                          : "text-purple-300"
                      }`}
                    >
                      {formatDelta(govData.performance_comparison.brier_delta, false)}
                    </p>
                    <span className="text-[10px] text-slate-400">Lower = Better</span>
                  </div>
    
                  <div className="rounded-2xl border border-slate-800/80 bg-slate-900/60 p-4">
                    <span className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider">
                      Prediction PSI
                    </span>
                    <p className="mt-1 text-2xl font-black text-cyan-300">
                      {formatNum(govData.prediction_drift.psi, 3)}
                    </p>
                    <span className="text-[10px] text-slate-400">
                      {govData.prediction_drift.drift_level} Drift
                    </span>
                  </div>
    
                  <div className="rounded-2xl border border-slate-800/80 bg-slate-900/60 p-4">
                    <span className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider">
                      Data Quality
                    </span>
                    <p className="mt-1 text-2xl font-black text-emerald-300">
                      {govData.data_quality.invalid_predictions === 0
                        ? "100%"
                        : `${govData.data_quality.valid_predictions}/${govData.data_quality.total_predictions}`}
                    </p>
                    <span className="text-[10px] text-slate-400">
                      {govData.data_quality.invalid_predictions} Anomalies
                    </span>
                  </div>
                </div>
    
                {/* Findings & Warnings */}
                {govData.findings.length > 0 && (
                  <div className="rounded-2xl border border-slate-800 bg-slate-900/40 p-6 space-y-3">
                    <h3 className="text-sm font-bold text-white flex items-center gap-2">
                      <span>Governance Telemetry & Diagnostic Findings</span>
                      <span className="rounded-full bg-slate-800 px-2 py-0.5 text-[10px] text-slate-300">
                        {govData.findings.length}
                      </span>
                    </h3>
                    <div className="grid grid-cols-1 gap-2.5 sm:grid-cols-2">
                      {govData.findings.map((finding, idx) => (
                        <div
                          key={idx}
                          className={`flex items-start gap-3 rounded-xl border p-3.5 text-xs ${
                            finding.severity === "CRITICAL"
                              ? "border-rose-800/60 bg-rose-950/20 text-rose-200"
                              : finding.severity === "WARNING"
                              ? "border-amber-800/60 bg-amber-950/20 text-amber-200"
                              : "border-slate-800 bg-slate-950/40 text-slate-300"
                          }`}
                        >
                          <span className="rounded px-1.5 py-0.5 font-mono text-[10px] font-bold uppercase bg-slate-900">
                            {finding.code}
                          </span>
                          <p className="flex-1 leading-relaxed">{finding.message}</p>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
    
                {/* Performance Windows */}
                <div className="rounded-2xl border border-slate-800 bg-slate-900/40 p-6 space-y-4">
                  <h3 className="text-sm font-bold text-white">
                    Rolling Performance Windows (7d, 30d, 90d, Historical)
                  </h3>
                  <div className="overflow-x-auto">
                    <table className="w-full text-left text-xs text-slate-300">
                      <thead className="border-b border-slate-800 bg-slate-950/50 text-[11px] font-semibold uppercase text-slate-400">
                        <tr>
                          <th className="py-2.5 px-3">Time Window</th>
                          <th className="py-2.5 px-3">Sample Count</th>
                          <th className="py-2.5 px-3">Accuracy</th>
                          <th className="py-2.5 px-3">Precision</th>
                          <th className="py-2.5 px-3">Recall</th>
                          <th className="py-2.5 px-3">F1 Score</th>
                          <th className="py-2.5 px-3">Brier Score</th>
                          <th className="py-2.5 px-3">Recovery Rate</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-slate-800/60 font-mono">
                        {govData.performance_windows.map((win, idx) => (
                          <tr key={idx} className="hover:bg-slate-800/20">
                            <td className="py-2.5 px-3 font-semibold text-slate-200 uppercase">
                              {win.window_name}
                            </td>
                            <td className="py-2.5 px-3">{win.sample_size}</td>
                            <td className="py-2.5 px-3 text-indigo-300 font-bold">
                              {formatPct(win.accuracy)}
                            </td>
                            <td className="py-2.5 px-3">{formatPct(win.precision)}</td>
                            <td className="py-2.5 px-3">{formatPct(win.recall)}</td>
                            <td className="py-2.5 px-3">{formatNum(win.f1_score, 3)}</td>
                            <td className="py-2.5 px-3 text-purple-300">
                              {formatNum(win.brier_score, 4)}
                            </td>
                            <td className="py-2.5 px-3 text-emerald-400">
                              {formatPct(win.recovery_rate)}
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
    
                {/* Feature & Prediction Drift */}
                <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
                  <div className="rounded-2xl border border-slate-800 bg-slate-900/40 p-6 space-y-4">
                    <h3 className="text-sm font-bold text-white flex items-center justify-between">
                      <span>Feature Drift (Population Stability Index)</span>
                      <span className="text-[10px] text-slate-400 font-mono">
                        Threshold: &gt;0.25 Significant
                      </span>
                    </h3>
                    <div className="overflow-x-auto">
                      <table className="w-full text-left text-xs text-slate-300">
                        <thead className="border-b border-slate-800 bg-slate-950/50 text-[11px] font-semibold uppercase text-slate-400">
                          <tr>
                            <th className="py-2.5 px-3">Feature Name</th>
                            <th className="py-2.5 px-3">Type</th>
                            <th className="py-2.5 px-3">PSI</th>
                            <th className="py-2.5 px-3">Drift Level</th>
                          </tr>
                        </thead>
                        <tbody className="divide-y divide-slate-800/60 font-mono">
                          {govData.feature_drift.map((fd, idx) => (
                            <tr key={idx} className="hover:bg-slate-800/20">
                              <td className="py-2 px-3 font-semibold text-slate-200">
                                {fd.feature_name}
                              </td>
                              <td className="py-2 px-3 text-slate-400 capitalize">
                                {fd.feature_type}
                              </td>
                              <td className="py-2 px-3 text-cyan-300">
                                {formatNum(fd.psi, 4)}
                              </td>
                              <td className="py-2 px-3">
                                <span
                                  className={`rounded px-1.5 py-0.5 text-[10px] font-bold uppercase border ${getDriftBadge(
                                    fd.drift_level
                                  )}`}
                                >
                                  {fd.drift_level}
                                </span>
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  </div>
    
                  <div className="rounded-2xl border border-slate-800 bg-slate-900/40 p-6 space-y-4">
                    <h3 className="text-sm font-bold text-white flex items-center justify-between">
                      <span>Prediction Distribution Shift</span>
                      <span className="text-[10px] text-slate-400 font-mono">
                        PSI: {formatNum(govData.prediction_drift.psi, 3)} (
                        {govData.prediction_drift.drift_level})
                      </span>
                    </h3>
                    <div className="overflow-x-auto">
                      <table className="w-full text-left text-xs text-slate-300">
                        <thead className="border-b border-slate-800 bg-slate-950/50 text-[11px] font-semibold uppercase text-slate-400">
                          <tr>
                            <th className="py-2.5 px-3">Probability Range</th>
                            <th className="py-2.5 px-3">Baseline %</th>
                            <th className="py-2.5 px-3">Recent %</th>
                            <th className="py-2.5 px-3">Delta (Δ)</th>
                          </tr>
                        </thead>
                        <tbody className="divide-y divide-slate-800/60 font-mono">
                          {govData.prediction_drift.buckets.map((b, idx) => (
                            <tr key={idx} className="hover:bg-slate-800/20">
                              <td className="py-2 px-3 font-semibold text-slate-200">
                                {b.bucket_min.toFixed(1)} – {b.bucket_max.toFixed(1)}
                              </td>
                              <td className="py-2 px-3 text-slate-400">
                                {formatPct(b.historical_percentage)}
                              </td>
                              <td className="py-2 px-3 text-indigo-300">
                                {formatPct(b.recent_percentage)}
                              </td>
                              <td className="py-2 px-3 font-bold text-slate-200">
                                {formatDelta(b.delta)}
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  </div>
                </div>
              </div>


    </>
  );
}
