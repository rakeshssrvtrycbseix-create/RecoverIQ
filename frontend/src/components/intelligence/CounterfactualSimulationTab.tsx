"use client";

import React, { useCallback, useEffect, useState } from "react";
import {
  CounterfactualSimulationResponse,
  SimulationRequest,
  fetchCounterfactualSimulation,
  formatINR
} from "../../lib/api";
import { formatDelta, formatPct, getAssessmentBadge, getReliabilityBadge } from "./intelligenceBadges";

export default function CounterfactualSimulationTab() {
  const [error, setError] = useState<string | null>(null);

    const [simData, setSimData] = useState<CounterfactualSimulationResponse | null>(null);
    const [simLoading, setSimLoading] = useState(false);
    const [currentAction, setCurrentAction] = useState("RETRY_PAYMENT");
    const [currentDelay, setCurrentDelay] = useState(12);
    const [altAction, setAltAction] = useState("SEND_PAYMENT_LINK");
    const [altDelay, setAltDelay] = useState(4);
    const [riskTier, setRiskTier] = useState<string>("");
    const [failureReason, setFailureReason] = useState<string>("");
    const [attemptNumber, setAttemptNumber] = useState<string>("");
    const [amountBand, setAmountBand] = useState<string>("");
    const [hypotheticalAmountRupees, setHypotheticalAmountRupees] = useState<number>(10000);
  

    const runSimulation = useCallback(async (customPayload?: SimulationRequest) => {
      setSimLoading(true);
      try {
        const payload: SimulationRequest = customPayload || {
          current_action_type: currentAction,
          current_delay_hours: currentDelay,
          alternative_action_type: altAction,
          alternative_delay_hours: altDelay,
          risk_tier: riskTier || null,
          failure_reason: failureReason || null,
          attempt_number: attemptNumber ? parseInt(attemptNumber, 10) : null,
          amount_band: amountBand || null,
          amount_at_risk_paise: hypotheticalAmountRupees ? hypotheticalAmountRupees * 100 : null,
        };
        const res = await fetchCounterfactualSimulation(payload);
        setSimData(res);
      } catch (err) {
        setError(
          err instanceof Error ? err.message : "Counterfactual simulation failed"
        );
      } finally {
        setSimLoading(false);
      }
    }, [
      altAction,
      altDelay,
      amountBand,
      attemptNumber,
      currentAction,
      currentDelay,
      failureReason,
      hypotheticalAmountRupees,
      riskTier,
    ]);
  

    useEffect(() => {
    let ignore = false;
    async function execute() {
      if (!ignore) {
        await runSimulation();
      }
    }
    void execute();
    return () => {
      ignore = true;
    };
  }, [runSimulation]);

  return (
    <>
      {error && (
        <div className="rounded-xl border border-rose-800/40 bg-rose-950/40 p-4 text-xs text-rose-300">
          {error}
        </div>
      )}
    
              {/* =========================================================================
                 TAB 1: STRATEGY SIMULATION (Phase 9D)
                 ========================================================================= */}
              <div className="space-y-8">
                {/* Mandatory Observational Notice */}
                <div className="rounded-2xl border border-amber-800/60 bg-amber-950/20 p-4 flex items-start gap-3">
                  <span className="rounded bg-amber-900/80 px-2 py-0.5 text-[10px] font-bold uppercase tracking-wider text-amber-200 border border-amber-700/60 shrink-0">
                    NOTICE
                  </span>
                  <p className="text-xs text-amber-200/90 leading-relaxed">
                    OBSERVATIONAL SIMULATION — This analysis is based on historical outcomes. It does not establish causal effects or guarantee future recovery. No financial action will be executed.
                  </p>
                </div>
    
                {/* Simulation Parameter Controls */}
                <div className="rounded-2xl border border-slate-800 bg-slate-900/50 p-6 space-y-6">
                  <h3 className="text-sm font-bold text-white uppercase tracking-wider text-indigo-400">
                    Counterfactual What-If Configuration
                  </h3>
    
                  {/* Segment Context Filters */}
                  <div className="grid grid-cols-2 gap-4 sm:grid-cols-5">
                    <div>
                      <label className="block text-[11px] font-semibold text-slate-400 uppercase">
                        Risk Tier
                      </label>
                      <select
                        value={riskTier}
                        onChange={(e) => setRiskTier(e.target.value)}
                        className="mt-1 w-full rounded-xl border border-slate-800 bg-slate-950 px-3 py-2 text-xs text-slate-200 focus:border-indigo-500 focus:outline-none"
                      >
                        <option value="">All Tiers</option>
                        <option value="LOW">LOW</option>
                        <option value="STANDARD">STANDARD</option>
                        <option value="HIGH">HIGH</option>
                        <option value="BLOCKED">BLOCKED</option>
                      </select>
                    </div>
    
                    <div>
                      <label className="block text-[11px] font-semibold text-slate-400 uppercase">
                        Failure Reason
                      </label>
                      <select
                        value={failureReason}
                        onChange={(e) => setFailureReason(e.target.value)}
                        className="mt-1 w-full rounded-xl border border-slate-800 bg-slate-950 px-3 py-2 text-xs text-slate-200 focus:border-indigo-500 focus:outline-none"
                      >
                        <option value="">All Reasons</option>
                        <option value="insufficient_funds">insufficient_funds</option>
                        <option value="transient_network_error">transient_network_error</option>
                        <option value="card_inactive">card_inactive</option>
                        <option value="generic_decline">generic_decline</option>
                      </select>
                    </div>
    
                    <div>
                      <label className="block text-[11px] font-semibold text-slate-400 uppercase">
                        Attempt Number
                      </label>
                      <select
                        value={attemptNumber}
                        onChange={(e) => setAttemptNumber(e.target.value)}
                        className="mt-1 w-full rounded-xl border border-slate-800 bg-slate-950 px-3 py-2 text-xs text-slate-200 focus:border-indigo-500 focus:outline-none"
                      >
                        <option value="">All Attempts</option>
                        <option value="1">Attempt 1</option>
                        <option value="2">Attempt 2</option>
                        <option value="3">Attempt 3</option>
                        <option value="4">Attempt 4+</option>
                      </select>
                    </div>
    
                    <div>
                      <label className="block text-[11px] font-semibold text-slate-400 uppercase">
                        Amount Band
                      </label>
                      <select
                        value={amountBand}
                        onChange={(e) => setAmountBand(e.target.value)}
                        className="mt-1 w-full rounded-xl border border-slate-800 bg-slate-950 px-3 py-2 text-xs text-slate-200 focus:border-indigo-500 focus:outline-none"
                      >
                        <option value="">All Bands</option>
                        <option value="< ₹1,000">&lt; ₹1,000</option>
                        <option value="₹1,000–₹5,000">₹1,000–₹5,000</option>
                        <option value="₹5,000–₹10,000">₹5,000–₹10,000</option>
                        <option value="₹10,000–₹50,000">₹10,000–₹50,000</option>
                        <option value="> ₹50,000">&gt; ₹50,000</option>
                      </select>
                    </div>
    
                    <div>
                      <label className="block text-[11px] font-semibold text-slate-400 uppercase">
                        Principal at Risk (₹)
                      </label>
                      <input
                        type="number"
                        value={hypotheticalAmountRupees}
                        onChange={(e) => setHypotheticalAmountRupees(Number(e.target.value))}
                        className="mt-1 w-full rounded-xl border border-slate-800 bg-slate-950 px-3 py-2 text-xs text-slate-200 focus:border-indigo-500 focus:outline-none font-mono"
                        placeholder="10000"
                      />
                    </div>
                  </div>
    
                  {/* Strategy Selectors */}
                  <div className="grid grid-cols-1 gap-6 pt-4 border-t border-slate-800 sm:grid-cols-2">
                    {/* Baseline Strategy */}
                    <div className="rounded-xl border border-slate-800 bg-slate-950/60 p-4 space-y-3">
                      <span className="text-xs font-bold text-slate-300 uppercase">
                        Current / Baseline Strategy
                      </span>
                      <div className="grid grid-cols-2 gap-3">
                        <div>
                          <label className="block text-[10px] text-slate-400 uppercase">Action</label>
                          <select
                            value={currentAction}
                            onChange={(e) => setCurrentAction(e.target.value)}
                            className="mt-1 w-full rounded-lg border border-slate-800 bg-slate-900 px-3 py-1.5 text-xs text-slate-200"
                          >
                            <option value="RETRY_PAYMENT">RETRY_PAYMENT</option>
                            <option value="SEND_PAYMENT_LINK">SEND_PAYMENT_LINK</option>
                            <option value="SEND_NOTIFICATION">SEND_NOTIFICATION</option>
                            <option value="ESCALATE_HUMAN">ESCALATE_HUMAN</option>
                            <option value="HALT_SUBSCRIPTION">HALT_SUBSCRIPTION</option>
                          </select>
                        </div>
                        <div>
                          <label className="block text-[10px] text-slate-400 uppercase">Delay</label>
                          <select
                            value={currentDelay}
                            onChange={(e) => setCurrentDelay(Number(e.target.value))}
                            className="mt-1 w-full rounded-lg border border-slate-800 bg-slate-900 px-3 py-1.5 text-xs text-slate-200"
                          >
                            <option value={2}>2 Hours</option>
                            <option value={4}>4 Hours</option>
                            <option value={12}>12 Hours</option>
                            <option value={24}>24 Hours</option>
                            <option value={48}>48 Hours</option>
                          </select>
                        </div>
                      </div>
                    </div>
    
                    {/* Alternative Strategy */}
                    <div className="rounded-xl border border-indigo-900/60 bg-indigo-950/20 p-4 space-y-3">
                      <span className="text-xs font-bold text-indigo-300 uppercase">
                        Counterfactual / Alternative Strategy
                      </span>
                      <div className="grid grid-cols-2 gap-3">
                        <div>
                          <label className="block text-[10px] text-indigo-300/80 uppercase">Action</label>
                          <select
                            value={altAction}
                            onChange={(e) => setAltAction(e.target.value)}
                            className="mt-1 w-full rounded-lg border border-indigo-800/60 bg-slate-900 px-3 py-1.5 text-xs text-slate-200"
                          >
                            <option value="SEND_PAYMENT_LINK">SEND_PAYMENT_LINK</option>
                            <option value="RETRY_PAYMENT">RETRY_PAYMENT</option>
                            <option value="SEND_NOTIFICATION">SEND_NOTIFICATION</option>
                            <option value="ESCALATE_HUMAN">ESCALATE_HUMAN</option>
                            <option value="HALT_SUBSCRIPTION">HALT_SUBSCRIPTION</option>
                          </select>
                        </div>
                        <div>
                          <label className="block text-[10px] text-indigo-300/80 uppercase">Delay</label>
                          <select
                            value={altDelay}
                            onChange={(e) => setAltDelay(Number(e.target.value))}
                            className="mt-1 w-full rounded-lg border border-indigo-800/60 bg-slate-900 px-3 py-1.5 text-xs text-slate-200"
                          >
                            <option value={2}>2 Hours</option>
                            <option value={4}>4 Hours</option>
                            <option value={12}>12 Hours</option>
                            <option value={24}>24 Hours</option>
                            <option value={48}>48 Hours</option>
                          </select>
                        </div>
                      </div>
                    </div>
                  </div>
    
                  <div className="flex justify-end">
                    <button
                      onClick={() => runSimulation()}
                      disabled={simLoading}
                      className="flex items-center gap-2 rounded-xl bg-indigo-600 px-6 py-2.5 text-xs font-bold uppercase tracking-wider text-white shadow-lg shadow-indigo-600/30 hover:bg-indigo-500 disabled:opacity-50"
                    >
                      {simLoading && (
                        <div className="h-3.5 w-3.5 animate-spin rounded-full border-2 border-white border-t-transparent" />
                      )}
                      <span>Run Counterfactual Simulation</span>
                    </button>
                  </div>
                </div>
    
                {/* Simulation Results Display */}
                {simData && (
                  <div className="space-y-6">
                    {/* Comparable Population Header */}
                    <div className="rounded-2xl border border-slate-800 bg-slate-900/30 p-4 flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between text-xs text-slate-400">
                      <div className="flex items-center gap-2">
                        <span className="font-bold text-slate-300">Reference Population:</span>
                        <span className="text-slate-200 font-mono">
                          {simData.population.filter_summary}
                        </span>
                        <span className="rounded bg-slate-800 px-2 py-0.5 text-[10px] font-mono uppercase text-slate-300">
                          {simData.population.segmentation_level_used}
                        </span>
                      </div>
                      <span className="font-mono text-slate-400">
                        {simData.population.total_cases_analyzed} Total Cases Evaluated
                      </span>
                    </div>
    
                    {/* Side-by-Side Strategy Comparison */}
                    <div className="grid grid-cols-1 gap-6 md:grid-cols-2">
                      {/* Current Strategy Card */}
                      <div className="rounded-2xl border border-slate-800 bg-slate-900/60 p-6 space-y-4">
                        <div className="flex items-center justify-between border-b border-slate-800 pb-3">
                          <div>
                            <span className="text-[10px] font-bold uppercase tracking-wider text-slate-400">
                              Current Strategy
                            </span>
                            <h4 className="text-base font-black text-white">
                              {simData.current_strategy.action_type} ({simData.current_strategy.delay_hours}h)
                            </h4>
                          </div>
                          <span
                            className={`rounded px-2 py-0.5 text-[10px] font-bold uppercase border ${getReliabilityBadge(
                              simData.current_strategy.reliability
                            )}`}
                          >
                            {simData.current_strategy.reliability}
                          </span>
                        </div>
    
                        <div className="grid grid-cols-2 gap-4 font-mono">
                          <div>
                            <span className="text-[10px] text-slate-400 block">Sample Size</span>
                            <span className="text-xl font-bold text-slate-200">
                              {simData.current_strategy.sample_size}
                            </span>
                          </div>
                          <div>
                            <span className="text-[10px] text-slate-400 block">Recovery Rate</span>
                            <span className="text-xl font-bold text-emerald-400">
                              {formatPct(simData.current_strategy.recovery_rate)}
                            </span>
                          </div>
                          <div>
                            <span className="text-[10px] text-slate-400 block">Financial Yield</span>
                            <span className="text-lg font-bold text-cyan-300">
                              {formatPct(simData.current_strategy.financial_yield)}
                            </span>
                          </div>
                          <div>
                            <span className="text-[10px] text-slate-400 block">Expected Value (ERV)</span>
                            <span className="text-lg font-bold text-purple-300">
                              {simData.current_strategy.expected_recovery_value_paise !== null
                                ? formatINR(simData.current_strategy.expected_recovery_value_paise)
                                : "—"}
                            </span>
                          </div>
                        </div>
                      </div>
    
                      {/* Alternative Strategy Card */}
                      <div className="rounded-2xl border border-indigo-800/80 bg-indigo-950/20 p-6 space-y-4">
                        <div className="flex items-center justify-between border-b border-indigo-900/60 pb-3">
                          <div>
                            <span className="text-[10px] font-bold uppercase tracking-wider text-indigo-400">
                              Alternative Strategy
                            </span>
                            <h4 className="text-base font-black text-indigo-200">
                              {simData.alternative_strategy.action_type} ({simData.alternative_strategy.delay_hours}h)
                            </h4>
                          </div>
                          <span
                            className={`rounded px-2 py-0.5 text-[10px] font-bold uppercase border ${getReliabilityBadge(
                              simData.alternative_strategy.reliability
                            )}`}
                          >
                            {simData.alternative_strategy.reliability}
                          </span>
                        </div>
    
                        <div className="grid grid-cols-2 gap-4 font-mono">
                          <div>
                            <span className="text-[10px] text-slate-400 block">Sample Size</span>
                            <span className="text-xl font-bold text-slate-200">
                              {simData.alternative_strategy.sample_size}
                            </span>
                          </div>
                          <div>
                            <span className="text-[10px] text-slate-400 block">Recovery Rate</span>
                            <span className="text-xl font-bold text-emerald-400">
                              {formatPct(simData.alternative_strategy.recovery_rate)}
                            </span>
                          </div>
                          <div>
                            <span className="text-[10px] text-slate-400 block">Financial Yield</span>
                            <span className="text-lg font-bold text-cyan-300">
                              {formatPct(simData.alternative_strategy.financial_yield)}
                            </span>
                          </div>
                          <div>
                            <span className="text-[10px] text-slate-400 block">Expected Value (ERV)</span>
                            <span className="text-lg font-bold text-purple-300">
                              {simData.alternative_strategy.expected_recovery_value_paise !== null
                                ? formatINR(simData.alternative_strategy.expected_recovery_value_paise)
                                : "—"}
                            </span>
                          </div>
                        </div>
                      </div>
                    </div>
    
                    {/* Strategy Differential & Uplift Assessment */}
                    <div className="rounded-2xl border border-slate-800 bg-slate-900/40 p-6 space-y-4">
                      <div className="flex items-center justify-between">
                        <h3 className="text-sm font-bold text-white uppercase tracking-wider">
                          Estimated Strategy Uplift
                        </h3>
                        <span
                          className={`rounded-full border px-2.5 py-0.5 text-xs font-mono font-bold uppercase tracking-wider ${getAssessmentBadge(
                            simData.estimated_uplift.confidence_assessment
                          )}`}
                        >
                          {simData.estimated_uplift.confidence_assessment.replace(/_/g, " ")}
                        </span>
                      </div>
    
                      <div className="grid grid-cols-2 gap-4 sm:grid-cols-4 font-mono">
                        <div className="rounded-xl bg-slate-950/60 border border-slate-800 p-3">
                          <span className="text-[10px] text-slate-400 block">Rate Delta (Δ)</span>
                          <span
                            className={`text-xl font-black ${
                              (simData.estimated_uplift.recovery_rate_delta || 0) >= 0
                                ? "text-emerald-400"
                                : "text-rose-400"
                            }`}
                          >
                            {formatDelta(simData.estimated_uplift.recovery_rate_delta)}
                          </span>
                        </div>
    
                        <div className="rounded-xl bg-slate-950/60 border border-slate-800 p-3">
                          <span className="text-[10px] text-slate-400 block">Relative Uplift %</span>
                          <span
                            className={`text-xl font-black ${
                              (simData.estimated_uplift.relative_uplift_pct || 0) >= 0
                                ? "text-cyan-300"
                                : "text-rose-400"
                            }`}
                          >
                            {simData.estimated_uplift.relative_uplift_pct !== null
                              ? `${simData.estimated_uplift.relative_uplift_pct > 0 ? "+" : ""}${simData.estimated_uplift.relative_uplift_pct.toFixed(1)}%`
                              : "—"}
                          </span>
                        </div>
    
                        <div className="rounded-xl bg-slate-950/60 border border-slate-800 p-3">
                          <span className="text-[10px] text-slate-400 block">Yield Delta (Δ)</span>
                          <span className="text-xl font-black text-indigo-300">
                            {formatDelta(simData.estimated_uplift.financial_yield_delta)}
                          </span>
                        </div>
    
                        <div className="rounded-xl bg-slate-950/60 border border-slate-800 p-3">
                          <span className="text-[10px] text-slate-400 block">Incremental ERV</span>
                          <span
                            className={`text-xl font-black ${
                              (simData.estimated_uplift.estimated_incremental_erv_paise || 0) >= 0
                                ? "text-emerald-300"
                                : "text-rose-400"
                            }`}
                          >
                            {simData.estimated_uplift.estimated_incremental_erv_paise !== null
                              ? formatINR(simData.estimated_uplift.estimated_incremental_erv_paise)
                              : "—"}
                          </span>
                        </div>
                      </div>
                    </div>
    
                    {/* Diagnostics List */}
                    {simData.diagnostics.length > 0 && (
                      <div className="rounded-2xl border border-slate-800 bg-slate-900/30 p-4 space-y-2">
                        <span className="text-xs font-bold text-slate-400 uppercase">
                          Simulation Diagnostics
                        </span>
                        <div className="grid grid-cols-1 gap-2 sm:grid-cols-2">
                          {simData.diagnostics.map((d, idx) => (
                            <div
                              key={idx}
                              className="flex items-start gap-2 rounded-xl bg-slate-950/60 border border-slate-800 p-3 text-xs"
                            >
                              <span className="rounded px-1.5 py-0.5 font-mono text-[9px] font-bold uppercase bg-slate-900 text-slate-300">
                                {d.code}
                              </span>
                              <p className="flex-1 text-slate-300 text-[11px] leading-relaxed">
                                {d.message}
                              </p>
                            </div>
                          ))}
                        </div>
                      </div>
                    )}
                  </div>
                )}
              </div>


    </>
  );
}
