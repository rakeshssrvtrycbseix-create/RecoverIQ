"use client";

import React, { useCallback, useEffect, useState } from "react";
import {
  IntelligenceEvaluationResponse,
  fetchIntelligenceEvaluation
} from "../../lib/api";
import { formatNum, formatPct } from "./intelligenceBadges";

export default function IntelligenceEvaluationTab() {
  const [error, setError] = useState<string | null>(null);

    const [evalData, setEvalData] = useState<IntelligenceEvaluationResponse | null>(null);

  const loadEvalData = useCallback(async () => {
    try {
      const res = await fetchIntelligenceEvaluation();
      setEvalData(res);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load Intelligence Evaluation data");
    }
  }, []);

    useEffect(() => {
    let ignore = false;
    async function execute() {
      if (!ignore) {
        await loadEvalData();
      }
    }
    void execute();
    return () => {
      ignore = true;
    };
  }, [loadEvalData]);

  if (!evalData) {
    return (
      <div className="flex items-center justify-center min-h-[300px]">
        <div className="text-slate-400 text-sm font-mono">Loading evaluation data...</div>
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
                 TAB 4: RECOVERY INTELLIGENCE EVALUATION (Phase 9A)
                 ========================================================================= */}
              <div className="space-y-8">
                <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 lg:grid-cols-6">
                  <div className="rounded-2xl border border-slate-800/80 bg-slate-900/60 p-4">
                    <span className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider">
                      Evaluated Cases
                    </span>
                    <p className="mt-1 text-2xl font-black text-white">
                      {evalData.classification.sample_size}
                    </p>
                    <span className="text-[10px] text-slate-400">Resolved Cases</span>
                  </div>
    
                  <div className="rounded-2xl border border-slate-800/80 bg-slate-900/60 p-4">
                    <span className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider">
                      Accuracy
                    </span>
                    <p className="mt-1 text-2xl font-black text-indigo-300">
                      {formatPct(evalData.classification.accuracy)}
                    </p>
                    <span className="text-[10px] text-slate-400">Threshold 0.50</span>
                  </div>
    
                  <div className="rounded-2xl border border-slate-800/80 bg-slate-900/60 p-4">
                    <span className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider">
                      Precision
                    </span>
                    <p className="mt-1 text-2xl font-black text-cyan-300">
                      {formatPct(evalData.classification.precision)}
                    </p>
                    <span className="text-[10px] text-slate-400">TP / (TP + FP)</span>
                  </div>
    
                  <div className="rounded-2xl border border-slate-800/80 bg-slate-900/60 p-4">
                    <span className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider">
                      Recall
                    </span>
                    <p className="mt-1 text-2xl font-black text-emerald-300">
                      {formatPct(evalData.classification.recall)}
                    </p>
                    <span className="text-[10px] text-slate-400">TP / (TP + FN)</span>
                  </div>
    
                  <div className="rounded-2xl border border-slate-800/80 bg-slate-900/60 p-4">
                    <span className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider">
                      F1 Score
                    </span>
                    <p className="mt-1 text-2xl font-black text-amber-300">
                      {formatNum(evalData.classification.f1_score, 3)}
                    </p>
                    <span className="text-[10px] text-slate-400">Harmonic Mean</span>
                  </div>
    
                  <div className="rounded-2xl border border-slate-800/80 bg-slate-900/60 p-4">
                    <span className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider">
                      Brier Score
                    </span>
                    <p className="mt-1 text-2xl font-black text-purple-300">
                      {formatNum(evalData.classification.brier_score, 4)}
                    </p>
                    <span className="text-[10px] text-slate-400">Lower = Better</span>
                  </div>
                </div>
    
                {/* Confusion Matrix */}
                <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
                  <div className="rounded-2xl border border-slate-800 bg-slate-900/40 p-6 space-y-4">
                    <h3 className="text-sm font-bold text-white flex items-center justify-between">
                      <span>Binary Classification Confusion Matrix</span>
                      <span className="text-xs font-mono font-normal text-slate-400">
                        Decision Boundary: 0.50
                      </span>
                    </h3>
    
                    <div className="grid grid-cols-2 gap-3">
                      <div className="rounded-xl border border-emerald-900/60 bg-emerald-950/30 p-4 text-center">
                        <span className="text-[10px] font-bold uppercase tracking-wider text-emerald-400">
                          True Positive (TP)
                        </span>
                        <p className="text-3xl font-black text-emerald-200 mt-1">
                          {evalData.classification.true_positive}
                        </p>
                        <span className="text-[10px] text-slate-400 block mt-1">
                          Predicted Recovered → Recovered
                        </span>
                      </div>
    
                      <div className="rounded-xl border border-rose-900/60 bg-rose-950/30 p-4 text-center">
                        <span className="text-[10px] font-bold uppercase tracking-wider text-rose-400">
                          False Positive (FP)
                        </span>
                        <p className="text-3xl font-black text-rose-200 mt-1">
                          {evalData.classification.false_positive}
                        </p>
                        <span className="text-[10px] text-slate-400 block mt-1">
                          Predicted Recovered → Failed
                        </span>
                      </div>
    
                      <div className="rounded-xl border border-rose-900/60 bg-rose-950/30 p-4 text-center">
                        <span className="text-[10px] font-bold uppercase tracking-wider text-rose-400">
                          False Negative (FN)
                        </span>
                        <p className="text-3xl font-black text-rose-200 mt-1">
                          {evalData.classification.false_negative}
                        </p>
                        <span className="text-[10px] text-slate-400 block mt-1">
                          Predicted Failed → Recovered
                        </span>
                      </div>
    
                      <div className="rounded-xl border border-emerald-900/60 bg-emerald-950/30 p-4 text-center">
                        <span className="text-[10px] font-bold uppercase tracking-wider text-emerald-400">
                          True Negative (TN)
                        </span>
                        <p className="text-3xl font-black text-emerald-200 mt-1">
                          {evalData.classification.true_negative}
                        </p>
                        <span className="text-[10px] text-slate-400 block mt-1">
                          Predicted Failed → Failed
                        </span>
                      </div>
                    </div>
                  </div>
    
                  {/* Confidence Alignment */}
                  <div className="rounded-2xl border border-slate-800 bg-slate-900/40 p-6 space-y-4">
                    <h3 className="text-sm font-bold text-white">
                      AI Recommendation Confidence vs Outcome
                    </h3>
                    <div className="space-y-3 text-xs">
                      <div className="flex items-center justify-between rounded-xl bg-slate-950/60 border border-slate-800 p-3">
                        <span className="text-slate-400">Avg Confidence (Recovered Cases):</span>
                        <span className="font-mono font-bold text-emerald-300 text-sm">
                          {formatNum(evalData.confidence_outcomes.average_confidence_recovered, 3)}
                        </span>
                      </div>
                      <div className="flex items-center justify-between rounded-xl bg-slate-950/60 border border-slate-800 p-3">
                        <span className="text-slate-400">Avg Confidence (Failed Cases):</span>
                        <span className="font-mono font-bold text-rose-300 text-sm">
                          {formatNum(evalData.confidence_outcomes.average_confidence_failed, 3)}
                        </span>
                      </div>
                      <div className="flex items-center justify-between rounded-xl bg-slate-950/60 border border-slate-800 p-3">
                        <span className="text-slate-400">Confidence Separation (Δ):</span>
                        <span className="font-mono font-bold text-indigo-300 text-sm">
                          {formatNum(evalData.confidence_outcomes.confidence_difference, 3)}
                        </span>
                      </div>
                      <div className="flex items-center justify-between rounded-xl bg-slate-950/60 border border-slate-800 p-3">
                        <span className="text-slate-400">Point-Biserial Correlation (ρ):</span>
                        <span className="font-mono font-bold text-cyan-300 text-sm">
                          {formatNum(evalData.confidence_outcomes.correlation, 3)}
                        </span>
                      </div>
                    </div>
                  </div>
                </div>
              </div>


    </>
  );
}
