"use client";

import React, { useCallback, useEffect, useState } from "react";
import {
  StrategyOptimizationResponse,
  fetchStrategyOptimization,
  formatINR
} from "../../lib/api";
import { formatPct, getReliabilityBadge } from "./intelligenceBadges";

export default function StrategyOptimizationTab() {
  const [error, setError] = useState<string | null>(null);

    const [optData, setOptData] = useState<StrategyOptimizationResponse | null>(null);

  const loadOptData = useCallback(async () => {
    try {
      const res = await fetchStrategyOptimization();
      setOptData(res);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load Strategy Optimization data");
    }
  }, []);

    useEffect(() => {
    let ignore = false;
    async function execute() {
      if (!ignore) {
        await loadOptData();
      }
    }
    void execute();
    return () => {
      ignore = true;
    };
  }, [loadOptData]);

  if (!optData) {
    return (
      <div className="flex items-center justify-center min-h-[300px]">
        <div className="text-slate-400 text-sm font-mono">Loading optimization data...</div>
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
                 TAB 2: STRATEGY OPTIMIZATION (Phase 9C)
                 ========================================================================= */}
              <div className="space-y-8">
                {/* Top Level Optimization KPI Cards */}
                <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
                  <div className="rounded-2xl border border-slate-800/80 bg-slate-900/60 p-4">
                    <span className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider">
                      Evaluated Sample
                    </span>
                    <p className="mt-1 text-2xl font-black text-white">
                      {optData.sample_size}
                    </p>
                    <span className="text-[10px] text-slate-400">Resolved Cases</span>
                  </div>
    
                  <div className="rounded-2xl border border-slate-800/80 bg-slate-900/60 p-4">
                    <span className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider">
                      Champion Action
                    </span>
                    <p className="mt-1 text-lg font-black text-indigo-300">
                      {optData.overall_recommendation.action_type || "INSUFFICIENT DATA"}
                    </p>
                    <span className="text-[10px] text-slate-400">
                      Reliability: {optData.overall_recommendation.confidence_level}
                    </span>
                  </div>
    
                  <div className="rounded-2xl border border-slate-800/80 bg-slate-900/60 p-4">
                    <span className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider">
                      Recommended Delay
                    </span>
                    <p className="mt-1 text-2xl font-black text-cyan-300">
                      {optData.overall_recommendation.recommended_delay_hours} Hours
                    </p>
                    <span className="text-[10px] text-slate-400">Optimal Retry Cadence</span>
                  </div>
    
                  <div className="rounded-2xl border border-slate-800/80 bg-slate-900/60 p-4">
                    <span className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider">
                      Expected Recovery Value (ERV)
                    </span>
                    <p className="mt-1 text-2xl font-black text-emerald-300 font-mono">
                      {formatINR(optData.expected_recovery_value_summary.expected_recovery_value)}
                    </p>
                    <span className="text-[10px] text-slate-400">
                      Total Risk: {formatINR(optData.expected_recovery_value_summary.amount_at_risk)}
                    </span>
                  </div>
                </div>
    
                {/* Observational Recommendation Notice & Findings */}
                <div className="rounded-2xl border border-indigo-900/60 bg-indigo-950/20 p-5 space-y-3">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <span className="rounded-md bg-indigo-900/80 px-2 py-0.5 text-[10px] font-bold uppercase tracking-wider text-indigo-200 border border-indigo-700/60">
                        OBSERVATIONAL RECOMMENDATION
                      </span>
                      <span className="text-xs text-indigo-300 font-medium">
                        {optData.overall_recommendation.recommendation_reason}
                      </span>
                    </div>
                    <span className="text-[10px] text-slate-400 font-mono">
                      Non-Executing Advisory Layer
                    </span>
                  </div>
    
                  {optData.diagnostic_findings.length > 0 && (
                    <div className="grid grid-cols-1 gap-2 sm:grid-cols-2 pt-2 border-t border-indigo-900/40">
                      {optData.diagnostic_findings.map((f, idx) => (
                        <div
                          key={idx}
                          className="flex items-start gap-2.5 rounded-xl bg-slate-950/60 border border-slate-800 p-3 text-xs"
                        >
                          <span className="rounded px-1.5 py-0.5 font-mono text-[9px] font-bold uppercase bg-slate-900 text-slate-300">
                            {f.code}
                          </span>
                          <p className="flex-1 text-slate-300 text-[11px] leading-relaxed">
                            {f.message}
                          </p>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
    
                {/* Strategy Performance Table */}
                <div className="rounded-2xl border border-slate-800 bg-slate-900/40 p-6 space-y-4">
                  <h3 className="text-sm font-bold text-white flex items-center justify-between">
                    <span>Action Strategy Performance & Financial Yield</span>
                    <span className="text-xs text-slate-400 font-mono font-normal">
                      Threshold: ≥30 Cases for Statistical Significance
                    </span>
                  </h3>
                  <div className="overflow-x-auto">
                    <table className="w-full text-left text-xs text-slate-300">
                      <thead className="border-b border-slate-800 bg-slate-950/50 text-[11px] font-semibold uppercase text-slate-400">
                        <tr>
                          <th className="py-2.5 px-3">Action Strategy</th>
                          <th className="py-2.5 px-3">Cases</th>
                          <th className="py-2.5 px-3">Recovery Rate</th>
                          <th className="py-2.5 px-3">Amount at Risk</th>
                          <th className="py-2.5 px-3">Amount Recovered</th>
                          <th className="py-2.5 px-3">Yield Rate</th>
                          <th className="py-2.5 px-3">Avg Prob</th>
                          <th className="py-2.5 px-3">Reliability</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-slate-800/60 font-mono">
                        {optData.strategies.map((s, idx) => (
                          <tr key={idx} className="hover:bg-slate-800/20">
                            <td className="py-2.5 px-3 font-semibold text-slate-200">
                              {s.action_type}
                            </td>
                            <td className="py-2.5 px-3">{s.sample_size}</td>
                            <td className="py-2.5 px-3 font-bold text-emerald-400">
                              {formatPct(s.recovery_rate)}
                            </td>
                            <td className="py-2.5 px-3 text-slate-400">
                              {formatINR(s.amount_at_risk)}
                            </td>
                            <td className="py-2.5 px-3 text-cyan-300">
                              {formatINR(s.amount_recovered)}
                            </td>
                            <td className="py-2.5 px-3 text-indigo-300 font-bold">
                              {formatPct(s.recovery_amount_rate)}
                            </td>
                            <td className="py-2.5 px-3 text-slate-300">
                              {formatPct(s.average_recovery_probability)}
                            </td>
                            <td className="py-2.5 px-3">
                              <span
                                className={`rounded px-1.5 py-0.5 text-[10px] font-bold uppercase border ${getReliabilityBadge(
                                  s.reliability
                                )}`}
                              >
                                {s.reliability}
                              </span>
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
    
                {/* Delay Cadence Analysis */}
                <div className="rounded-2xl border border-slate-800 bg-slate-900/40 p-6 space-y-4">
                  <h3 className="text-sm font-bold text-white">
                    Retry Delay Cadence Optimization (Hours)
                  </h3>
                  <div className="overflow-x-auto">
                    <table className="w-full text-left text-xs text-slate-300">
                      <thead className="border-b border-slate-800 bg-slate-950/50 text-[11px] font-semibold uppercase text-slate-400">
                        <tr>
                          <th className="py-2.5 px-3">Cadence Interval</th>
                          <th className="py-2.5 px-3">Sample Count</th>
                          <th className="py-2.5 px-3">Recovered Count</th>
                          <th className="py-2.5 px-3">Empirical Recovery Rate</th>
                          <th className="py-2.5 px-3">Amount Recovered</th>
                          <th className="py-2.5 px-3">Reliability</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-slate-800/60 font-mono">
                        {optData.delay_analysis.map((d, idx) => (
                          <tr key={idx} className="hover:bg-slate-800/20">
                            <td className="py-2.5 px-3 font-semibold text-cyan-300">
                              {d.delay_hours} Hours
                            </td>
                            <td className="py-2.5 px-3">{d.sample_size}</td>
                            <td className="py-2.5 px-3 text-slate-200">{d.recovered_count}</td>
                            <td className="py-2.5 px-3 font-bold text-emerald-400">
                              {formatPct(d.recovery_rate)}
                            </td>
                            <td className="py-2.5 px-3 text-slate-300">
                              {formatINR(d.amount_recovered)}
                            </td>
                            <td className="py-2.5 px-3">
                              <span
                                className={`rounded px-1.5 py-0.5 text-[10px] font-bold uppercase border ${getReliabilityBadge(
                                  d.reliability
                                )}`}
                              >
                                {d.reliability}
                              </span>
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
    
                {/* Segment Recommendations Table */}
                <div className="rounded-2xl border border-slate-800 bg-slate-900/40 p-6 space-y-4">
                  <h3 className="text-sm font-bold text-white">
                    Segment Strategy Recommendations (Risk, Reason, Cadence, Value)
                  </h3>
                  <div className="overflow-x-auto">
                    <table className="w-full text-left text-xs text-slate-300">
                      <thead className="border-b border-slate-800 bg-slate-950/50 text-[11px] font-semibold uppercase text-slate-400">
                        <tr>
                          <th className="py-2.5 px-3">Segment Type</th>
                          <th className="py-2.5 px-3">Segment Value</th>
                          <th className="py-2.5 px-3">Sample</th>
                          <th className="py-2.5 px-3">Recommended Action</th>
                          <th className="py-2.5 px-3">Optimal Delay</th>
                          <th className="py-2.5 px-3">Recovery Rate</th>
                          <th className="py-2.5 px-3">Expected Value (ERV)</th>
                          <th className="py-2.5 px-3">Reliability</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-slate-800/60 font-mono">
                        {optData.segment_recommendations.map((seg, idx) => (
                          <tr key={idx} className="hover:bg-slate-800/20">
                            <td className="py-2.5 px-3 capitalize text-slate-400">
                              {seg.segment_type.replace("_", " ")}
                            </td>
                            <td className="py-2.5 px-3 font-semibold text-slate-200">
                              {seg.segment_value}
                            </td>
                            <td className="py-2.5 px-3">{seg.sample_size}</td>
                            <td className="py-2.5 px-3 font-bold text-indigo-300">
                              {seg.best_action_type || "—"}
                            </td>
                            <td className="py-2.5 px-3 text-cyan-300">
                              {seg.best_delay_hours ? `${seg.best_delay_hours}h` : "—"}
                            </td>
                            <td className="py-2.5 px-3 text-emerald-400 font-bold">
                              {formatPct(seg.recovery_rate)}
                            </td>
                            <td className="py-2.5 px-3 text-purple-300 font-bold">
                              {formatINR(seg.expected_recovery_value)}
                            </td>
                            <td className="py-2.5 px-3">
                              <span
                                className={`rounded px-1.5 py-0.5 text-[10px] font-bold uppercase border ${getReliabilityBadge(
                                  seg.reliability
                                )}`}
                              >
                                {seg.reliability}
                              </span>
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              </div>


    </>
  );
}
