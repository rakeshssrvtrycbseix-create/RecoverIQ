"use client";

import React, { useCallback, useEffect, useState } from "react";
import {
  CaseDecisionTrace,
  ControlPlaneSummaryResponse,
  GovernanceCenterResponse,
  IncidentsResponse,
  UnifiedLineageResponse,
    fetchControlPlaneIncidents,
  fetchControlPlaneLineage,
  fetchControlPlaneSummary,
  fetchDecisionTrace,
  fetchGovernanceCenter,
  formatINR
} from "../../lib/api";
import {
  getGlobalStateBadge,
  getEligibilityDecisionBadge,
  getSubsystemStatusBadge,
  getIncidentSeverityBadge,
} from "./intelligenceBadges";

interface ControlPlaneTabProps {
  userRole?: string;
  setActiveTab?: (tab: string) => void;
}

export default function ControlPlaneTab({
  userRole = "ADMIN",
  setActiveTab = () => {},
}: ControlPlaneTabProps) {
  const [error, setError] = useState<string | null>(null);

    const [controlPlaneSummary, setControlPlaneSummary] = useState<ControlPlaneSummaryResponse | null>(null);
    const [controlPlaneIncidents, setControlPlaneIncidents] = useState<IncidentsResponse | null>(null);
    const [controlPlaneLineage, setControlPlaneLineage] = useState<UnifiedLineageResponse | null>(null);
    const [governanceCenter, setGovernanceCenter] = useState<GovernanceCenterResponse | null>(null);
    const [decisionTraceCaseId, setDecisionTraceCaseId] = useState<string>("");
  
    const [decisionTraceData, setDecisionTraceData] = useState<CaseDecisionTrace | null>(null);
    const [decisionTraceLoading, setDecisionTraceLoading] = useState(false);
    const [decisionTraceError, setDecisionTraceError] = useState<string | null>(null);
  

    const handleFetchDecisionTrace = async (caseIdToTrace?: string) => {
      const id = caseIdToTrace || decisionTraceCaseId;
      if (!id.trim()) {
        setDecisionTraceError("Please enter a valid Recovery Case UUID.");
        return;
      }
      setDecisionTraceLoading(true);
      setDecisionTraceError(null);
      try {
        const trace = await fetchDecisionTrace(id.trim());
        setDecisionTraceData(trace);
      } catch (err) {
        setDecisionTraceError(err instanceof Error ? err.message : "Failed to load decision trace");
        setDecisionTraceData(null);
      } finally {
        setDecisionTraceLoading(false);
      }
    };
  

  const loadControlPlaneData = useCallback(async () => {
    try {
      const [sumRes, incRes, linRes, govRes] = await Promise.all([
        fetchControlPlaneSummary().catch(() => null),
        fetchControlPlaneIncidents().catch(() => null),
        fetchControlPlaneLineage().catch(() => null),
        fetchGovernanceCenter().catch(() => null),
      ]);
      setControlPlaneSummary(sumRes);
      setControlPlaneIncidents(incRes);
      setControlPlaneLineage(linRes);
      setGovernanceCenter(govRes);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load Control Plane data");
    }
  }, []);

    useEffect(() => {
    let ignore = false;
    async function execute() {
      if (!ignore) {
        await loadControlPlaneData();
      }
    }
    void execute();
    return () => {
      ignore = true;
    };
  }, [loadControlPlaneData]);

  return (
    <>
      {error && (
        <div className="rounded-xl border border-rose-800/40 bg-rose-950/40 p-4 text-xs text-rose-300">
          {error}
        </div>
      )}
    
    
              {/* =========================================================================
                 TAB 12: UNIFIED INTELLIGENCE CONTROL PLANE & AUTONOMOUS GOVERNANCE (Phase 9L)
                 ========================================================================= */}
              <div className="space-y-8">
                {/* Mandatory Governance & Zero Financial Mutation Banner */}
                <div className="rounded-2xl border border-amber-800/60 bg-gradient-to-r from-amber-950/30 via-purple-950/20 to-indigo-950/30 p-5 flex items-start gap-4 shadow-xl">
                  <span className="rounded-lg bg-gradient-to-r from-amber-600 to-indigo-600 px-2.5 py-1 text-[10px] font-mono font-black uppercase tracking-wider text-white shadow shrink-0">
                    PHASE 9L CONTROL PLANE
                  </span>
                  <div className="text-xs text-slate-200 leading-relaxed space-y-1.5">
                    <p className="font-bold text-amber-200 text-sm flex items-center gap-2">
                      <span>UNIFIED INTELLIGENCE CONTROL PLANE & AUTONOMOUS GOVERNANCE</span>
                      <span className="text-[10px] font-mono font-normal text-amber-400/80 bg-amber-950/80 px-2 py-0.5 rounded border border-amber-700/50">
                        PolicyEngine Supremacy • Zero Financial Mutations
                      </span>
                    </p>
                    <p className="text-[11px] text-slate-300/90">
                      {controlPlaneSummary?.governance_disclaimer ||
                        "The Intelligence Control Plane is an observational and governance surveillance layer. The authoritative financial execution pipeline remains: Payment -> RecoveryCase -> ML Prediction -> AgentDecision -> PolicyDecision -> RecoveryAction -> RecoveryWorker -> ActionDispatcher -> RazorpayActionProvider. The control plane NEVER directly modifies payment financial states, executes retries, or bypasses PolicyEngine."}
                    </p>
                  </div>
                </div>
    
                {/* Quick System Status & Global Health Overview Cards */}
                <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-6">
                  {/* 1. Global System State */}
                  <div className="rounded-2xl border border-slate-800 bg-slate-900/90 p-4 flex flex-col justify-between shadow-lg relative overflow-hidden">
                    <div className="flex items-center justify-between">
                      <span className="text-[10px] font-mono font-bold uppercase tracking-wider text-slate-400">Global State</span>
                      <span className="h-2 w-2 rounded-full bg-indigo-500 animate-ping" />
                    </div>
                    <div className="mt-2">
                      <span
                        className={`inline-block rounded-xl border px-3 py-1 text-xs font-mono font-black uppercase tracking-wider ${getGlobalStateBadge(
                          controlPlaneSummary?.global_state
                        )}`}
                      >
                        {controlPlaneSummary?.global_state.replace(/_/g, " ") || "HEALTHY"}
                      </span>
                      <p className="text-[10px] text-slate-500 mt-1">Deterministic state priority</p>
                    </div>
                  </div>
    
                  {/* 2. Unified Health Score */}
                  <div className="rounded-2xl border border-slate-800 bg-slate-900/90 p-4 flex flex-col justify-between shadow-lg">
                    <div className="flex items-center justify-between">
                      <span className="text-[10px] font-mono font-bold uppercase tracking-wider text-slate-400">Health Score</span>
                      <span className="text-[10px] font-mono text-emerald-400 font-bold">8 Dimensions</span>
                    </div>
                    <div className="mt-2">
                      <div className="flex items-baseline gap-1">
                        <strong className="text-2xl font-black text-white">
                          {controlPlaneSummary?.health_score.overall_score.toFixed(1) || "100.0"}
                        </strong>
                        <span className="text-xs text-slate-500">/ 100</span>
                      </div>
                      <div className="w-full bg-slate-800 h-1.5 rounded-full mt-2 overflow-hidden">
                        <div
                          className="bg-gradient-to-r from-emerald-500 to-cyan-400 h-full rounded-full transition-all duration-500"
                          style={{ width: `${Math.min(100, Math.max(0, controlPlaneSummary?.health_score.overall_score || 100))}%` }}
                        />
                      </div>
                    </div>
                  </div>
    
                  {/* 3. Active Champion Model */}
                  <div className="rounded-2xl border border-slate-800 bg-slate-900/90 p-4 flex flex-col justify-between shadow-lg">
                    <span className="text-[10px] font-mono font-bold uppercase tracking-wider text-slate-400">Active Champion</span>
                    <div className="mt-2">
                      <strong className="text-lg font-mono font-black text-cyan-300">
                        {controlPlaneSummary?.active_champion_version || "v1.0"}
                      </strong>
                      <p className="text-[10px] text-slate-500 truncate">Calibrated Logistic Reg</p>
                    </div>
                  </div>
    
                  {/* 4. Active Strategy */}
                  <div className="rounded-2xl border border-slate-800 bg-slate-900/90 p-4 flex flex-col justify-between shadow-lg">
                    <span className="text-[10px] font-mono font-bold uppercase tracking-wider text-slate-400">Active Strategy</span>
                    <div className="mt-2">
                      <strong className="text-sm font-mono font-bold text-amber-300 truncate block">
                        {controlPlaneSummary?.active_strategy_action || "SEND_PAYMENT_LINK"}
                      </strong>
                      <p className="text-[10px] text-slate-500">Optimized ERV cadence</p>
                    </div>
                  </div>
    
                  {/* 5. Production Deployment */}
                  <div className="rounded-2xl border border-slate-800 bg-slate-900/90 p-4 flex flex-col justify-between shadow-lg">
                    <span className="text-[10px] font-mono font-bold uppercase tracking-wider text-slate-400">Deployment Status</span>
                    <div className="mt-2">
                      <span className="inline-block rounded border border-cyan-700/60 bg-cyan-950/80 px-2 py-0.5 text-xs font-mono font-bold text-cyan-300">
                        {controlPlaneSummary?.deployment_status || "ACTIVE"}
                      </span>
                      <p className="text-[10px] text-slate-500 mt-1">Rollback tripwires armed</p>
                    </div>
                  </div>
    
                  {/* 6. Continuous Learning */}
                  <div className="rounded-2xl border border-slate-800 bg-slate-900/90 p-4 flex flex-col justify-between shadow-lg">
                    <span className="text-[10px] font-mono font-bold uppercase tracking-wider text-slate-400">Learning Readiness</span>
                    <div className="mt-2">
                      <span className={`inline-block rounded border px-2 py-0.5 text-xs font-mono font-bold ${getEligibilityDecisionBadge(
                        controlPlaneSummary?.learning_status || "WAITING_FOR_DATA"
                      )}`}>
                        {controlPlaneSummary?.learning_status || "WAITING_FOR_DATA"}
                      </span>
                      <p className="text-[10px] text-slate-500 mt-1">Autonomous surveillance</p>
                    </div>
                  </div>
                </div>
    
                {/* Subsystem Health Breakdown (8 Dimension Score Cards) */}
                <div className="space-y-4">
                  <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between">
                    <div>
                      <h3 className="text-base font-bold text-white flex items-center gap-2">
                        <span>Subsystem Health & Dimension Scores</span>
                        <span className="text-xs font-normal text-slate-400 font-mono">
                          (Formula: Deterministic Weighted Sum = 100%)
                        </span>
                      </h3>
                      <p className="text-xs text-slate-400">
                        Continuous monitoring across model quality, drift, calibration, data integrity, causal uplift, deployment safety, and continuous learning.
                      </p>
                    </div>
                    <div className="mt-2 sm:mt-0 flex items-center gap-2">
                      <span className="text-[11px] font-mono text-slate-400 bg-slate-900 px-2.5 py-1 rounded-lg border border-slate-800">
                        Pending Human Reviews: <strong className="text-amber-400">{controlPlaneSummary?.pending_reviews_count ?? 0}</strong>
                      </span>
                    </div>
                  </div>
    
                  <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
                    {controlPlaneSummary?.subsystems.map((sub, idx) => (
                      <div
                        key={idx}
                        className="rounded-2xl border border-slate-800 bg-slate-900/80 p-4 flex flex-col justify-between space-y-3 hover:border-slate-700 transition"
                      >
                        <div>
                          <div className="flex items-center justify-between">
                            <span className="text-xs font-mono font-bold text-slate-300">
                              {sub.subsystem.replace(/_/g, " ")}
                            </span>
                            <span
                              className={`rounded-full border px-2 py-0.5 text-[10px] font-mono font-bold uppercase ${getSubsystemStatusBadge(
                                sub.status
                              )}`}
                            >
                              {sub.status}
                            </span>
                          </div>
                          <p className="text-xs text-slate-400 mt-2 line-clamp-2">{sub.summary}</p>
                        </div>
    
                        <div className="border-t border-slate-800/80 pt-3">
                          <div className="flex items-center justify-between text-xs font-mono">
                            <span className="text-slate-500">Component Score</span>
                            <strong className="text-emerald-400 font-black">{sub.score.toFixed(1)} / 100</strong>
                          </div>
                          {sub.metrics && (
                            <div className="mt-2 flex flex-wrap gap-1.5">
                              {Object.entries(sub.metrics).slice(0, 2).map(([k, v]) => (
                                <span
                                  key={k}
                                  className="text-[10px] font-mono bg-slate-950/80 border border-slate-800/80 px-2 py-0.5 rounded text-slate-400 truncate max-w-[140px]"
                                >
                                  {k}: <strong className="text-slate-200">{String(v)}</strong>
                                </span>
                              ))}
                            </div>
                          )}
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
    
                {/* Active Multi-Signal Correlated Incidents */}
                <div className="rounded-2xl border border-slate-800 bg-slate-900/80 p-6 space-y-4 shadow-xl">
                  <div className="flex items-center justify-between border-b border-slate-800 pb-3">
                    <div className="flex items-center gap-3">
                      <h3 className="text-base font-bold text-white">Active Correlated Incidents & Alerts</h3>
                      <span className="rounded-full bg-slate-800 px-2.5 py-0.5 text-xs font-mono text-slate-300 font-bold border border-slate-700">
                        {controlPlaneIncidents?.active_count ?? controlPlaneSummary?.active_incidents_count ?? 0} Active
                      </span>
                    </div>
                    <span className="text-[11px] text-slate-500 font-mono">
                      Autonomous Multi-Signal Surveillance
                    </span>
                  </div>
    
                  {controlPlaneIncidents && controlPlaneIncidents.incidents.length > 0 ? (
                    <div className="space-y-3">
                      {controlPlaneIncidents.incidents.map((inc) => (
                        <div
                          key={inc.incident_id}
                          className="rounded-xl border border-slate-800 bg-slate-950/60 p-4 space-y-3 hover:border-slate-700 transition"
                        >
                          <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2">
                            <div className="flex items-center gap-2">
                              <span
                                className={`rounded border px-2 py-0.5 text-[10px] font-mono font-black uppercase ${getIncidentSeverityBadge(
                                  inc.severity
                                )}`}
                              >
                                {inc.severity}
                              </span>
                              <strong className="text-sm text-white font-mono">{inc.incident_id}</strong>
                              <span className="text-xs text-slate-300 font-semibold">— {inc.title}</span>
                            </div>
                            <div className="flex items-center gap-2 text-[10px] font-mono text-slate-500">
                              <span>Detected: {new Date(inc.first_detected).toLocaleTimeString()}</span>
                              {inc.requires_human_review && (
                                <span className="bg-amber-950/80 text-amber-300 border border-amber-700/60 px-1.5 py-0.5 rounded font-bold">
                                  HUMAN REVIEW REQUIRED
                                </span>
                              )}
                            </div>
                          </div>
    
                          <div className="flex flex-wrap gap-2 text-[10px] font-mono">
                            <span className="text-slate-500">Phases:</span>
                            {inc.source_phases.map((p) => (
                              <span key={p} className="bg-slate-900 border border-slate-800 px-2 py-0.5 rounded text-cyan-300">
                                {p}
                              </span>
                            ))}
                            <span className="text-slate-500 ml-2">Codes:</span>
                            {inc.diagnostic_codes.map((c) => (
                              <span key={c} className="bg-slate-900 border border-slate-800 px-2 py-0.5 rounded text-amber-300">
                                {c}
                              </span>
                            ))}
                          </div>
    
                          <div className="rounded-lg bg-slate-900/90 border border-slate-800/80 p-3 text-xs text-slate-300 space-y-1">
                            <p className="text-[10px] font-mono font-bold uppercase tracking-wider text-slate-400">
                              Recommended Operator Action:
                            </p>
                            <p className="text-amber-200/90 font-mono text-[11px]">{inc.recommended_action}</p>
                          </div>
                        </div>
                      ))}
                    </div>
                  ) : (
                    <div className="rounded-xl border border-emerald-800/40 bg-emerald-950/20 p-4 text-xs text-emerald-300 font-mono flex items-center gap-2">
                      <span>✓</span>
                      <span>Zero active critical or correlated incidents detected. All intelligence subsystems operating within nominal safety thresholds.</span>
                    </div>
                  )}
                </div>
    
                {/* Human Governance Center */}
                <div className="rounded-2xl border border-slate-800 bg-slate-900/80 p-6 space-y-6 shadow-xl">
                  <div className="flex items-center justify-between border-b border-slate-800 pb-4">
                    <div>
                      <h3 className="text-base font-bold text-white flex items-center gap-2">
                        <span>Human Governance Action Center</span>
                        <span className="rounded bg-indigo-900/80 border border-indigo-700/60 px-2 py-0.5 text-[10px] font-mono text-indigo-200 uppercase font-bold">
                          Centralized Reviews
                        </span>
                      </h3>
                      <p className="text-xs text-slate-400 mt-1">
                        Unified action queue for pending model approvals, strategy recommendations, canary promotions, and rollback guardrails.
                      </p>
                    </div>
                    <span className="text-[11px] font-mono text-slate-500">
                      Role: <strong className="text-amber-400 uppercase">{userRole}</strong>
                    </span>
                  </div>
    
                  {/* Action Queue Grid */}
                  <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
                    {/* 1. Pending Strategy Recommendations */}
                    <div className="rounded-xl border border-slate-800 bg-slate-950/60 p-4 space-y-3">
                      <div className="flex items-center justify-between">
                        <span className="text-xs font-mono font-bold text-slate-400 uppercase">Strategy Reviews</span>
                        <span className="rounded bg-amber-950 border border-amber-700 px-2 py-0.5 text-xs font-mono font-bold text-amber-300">
                          {governanceCenter?.pending_strategy_recommendations_count ?? 0} Pending
                        </span>
                      </div>
                      <p className="text-xs text-slate-400">
                        Recommendations requiring operator signoff before canary rollout.
                      </p>
                      <button
                        onClick={() => setActiveTab("recommendations")}
                        className="w-full rounded-lg bg-slate-800 hover:bg-slate-700 py-1.5 text-xs font-semibold text-slate-200 transition"
                      >
                        Open Recommendations Tab →
                      </button>
                    </div>
    
                    {/* 2. Pending Model Scorecards */}
                    <div className="rounded-xl border border-slate-800 bg-slate-950/60 p-4 space-y-3">
                      <div className="flex items-center justify-between">
                        <span className="text-xs font-mono font-bold text-slate-400 uppercase">Model Scorecards</span>
                        <span className="rounded bg-indigo-950 border border-indigo-700 px-2 py-0.5 text-xs font-mono font-bold text-indigo-300">
                          {governanceCenter?.pending_model_reviews_count ?? 0} Pending
                        </span>
                      </div>
                      <p className="text-xs text-slate-400">
                        Candidate models trained offline awaiting human quality gate verification.
                      </p>
                      <button
                        onClick={() => setActiveTab("lifecycle")}
                        className="w-full rounded-lg bg-slate-800 hover:bg-slate-700 py-1.5 text-xs font-semibold text-slate-200 transition"
                      >
                        Open Model Lifecycle Tab →
                      </button>
                    </div>
    
                    {/* 3. Pending Deployment Canary Reviews */}
                    <div className="rounded-xl border border-slate-800 bg-slate-950/60 p-4 space-y-3">
                      <div className="flex items-center justify-between">
                        <span className="text-xs font-mono font-bold text-slate-400 uppercase">Deployment Canaries</span>
                        <span className="rounded bg-cyan-950 border border-cyan-700 px-2 py-0.5 text-xs font-mono font-bold text-cyan-300">
                          {governanceCenter?.pending_deployment_reviews_count ?? 0} Active
                        </span>
                      </div>
                      <p className="text-xs text-slate-400">
                        Active shadow & canary deployments undergoing recovery rate evaluation.
                      </p>
                      <button
                        onClick={() => setActiveTab("deployment")}
                        className="w-full rounded-lg bg-slate-800 hover:bg-slate-700 py-1.5 text-xs font-semibold text-slate-200 transition"
                      >
                        Open Model Deployment Tab →
                      </button>
                    </div>
    
                    {/* 4. Emergency Rollback Alerts */}
                    <div className="rounded-xl border border-slate-800 bg-slate-950/60 p-4 space-y-3">
                      <div className="flex items-center justify-between">
                        <span className="text-xs font-mono font-bold text-slate-400 uppercase">Rollback Guardrails</span>
                        <span
                          className={`rounded px-2 py-0.5 text-xs font-mono font-bold ${
                            (governanceCenter?.rollback_alerts?.length ?? 0) > 0
                              ? "bg-rose-950 border border-rose-600 text-rose-300 animate-pulse"
                              : "bg-emerald-950 border border-emerald-700 text-emerald-300"
                          }`}
                        >
                          {governanceCenter?.rollback_alerts?.length ?? 0} Alerts
                        </span>
                      </div>
                      <p className="text-xs text-slate-400">
                        Automated tripwire monitor for negative recovery uplift breaches.
                      </p>
                      <button
                        onClick={() => setActiveTab("deployment")}
                        className="w-full rounded-lg bg-slate-800 hover:bg-slate-700 py-1.5 text-xs font-semibold text-slate-200 transition"
                      >
                        View Deployment Tripwires →
                      </button>
                    </div>
                  </div>
    
                  {/* Synthesized Required Operator Actions Checklist */}
                  {governanceCenter?.required_operator_actions && governanceCenter.required_operator_actions.length > 0 && (
                    <div className="rounded-xl border border-slate-800 bg-slate-950/60 p-4 space-y-2">
                      <span className="text-xs font-mono font-bold uppercase tracking-wider text-slate-400 block">
                        Required Operator Actions Checklist:
                      </span>
                      <ul className="space-y-1.5">
                        {governanceCenter.required_operator_actions.map((act, i) => (
                          <li key={i} className="text-xs text-slate-300 flex items-start gap-2">
                            <span className="text-amber-400 font-bold">•</span>
                            <span>{act}</span>
                          </li>
                        ))}
                      </ul>
                    </div>
                  )}
                </div>
    
                {/* Unified Provenance & Lineage Progression DAG */}
                <div className="rounded-2xl border border-slate-800 bg-slate-900/80 p-6 space-y-4 shadow-xl">
                  <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between border-b border-slate-800 pb-3">
                    <div>
                      <h3 className="text-base font-bold text-white flex items-center gap-2">
                        <span>Unified Intelligence Lineage & Provenance DAG</span>
                        <span className="rounded bg-cyan-900/80 border border-cyan-700/60 px-2 py-0.5 text-[10px] font-mono text-cyan-200 font-bold uppercase">
                          10 Progression Stages
                        </span>
                      </h3>
                      <p className="text-xs text-slate-400 mt-1">
                        End-to-end model & strategy provenance tracking from training dataset snapshots to production outcomes.
                      </p>
                    </div>
                    <div className="mt-2 sm:mt-0 flex items-center gap-2 text-xs font-mono text-slate-400">
                      <span>Champion: <strong className="text-cyan-300">{controlPlaneLineage?.active_champion_model || "v1.0"}</strong></span>
                      <span className="text-slate-600">|</span>
                      <span>Strategy: <strong className="text-amber-300">{controlPlaneLineage?.active_production_strategy || "SEND_PAYMENT_LINK"}</strong></span>
                    </div>
                  </div>
    
                  {/* Visual DAG Progression Flow */}
                  <div className="grid grid-cols-2 gap-3 sm:grid-cols-5 lg:grid-cols-10 pt-2">
                    {(
                      controlPlaneLineage?.nodes || [
                        { stage: "DATASET", identifier: "dataset-v2.25", status: "VALIDATED" },
                        { stage: "TRAINING_RUN", identifier: "train_20260801", status: "COMPLETED" },
                        { stage: "MODEL_ARTIFACT", identifier: "v1.0", status: "ACTIVE" },
                        { stage: "VALIDATION", identifier: "gate_check_pass", status: "PASSED" },
                        { stage: "GOVERNANCE", identifier: "gov_eval_healthy", status: "HEALTHY" },
                        { stage: "EXPERIMENT", identifier: "exp-causal-link", status: "ACTIVE" },
                        { stage: "STRATEGY_RECOMMENDATION", identifier: "rec_approved", status: "APPROVED" },
                        { stage: "CONTROLLED_ROLLOUT", identifier: "rollout_100pct", status: "ACTIVE" },
                        { stage: "PRODUCTION_DEPLOYMENT", identifier: "dep_champion_v1", status: "ACTIVE" },
                        { stage: "PRODUCTION_OUTCOME", identifier: "outcome_eval", status: "EVALUATED" },
                      ]
                    ).map((node, i) => (
                      <div
                        key={i}
                        className="rounded-xl border border-slate-800 bg-slate-950/80 p-3 flex flex-col justify-between space-y-2 hover:border-cyan-500/50 transition relative group"
                      >
                        <div>
                          <div className="flex items-center justify-between">
                            <span className="text-[9px] font-mono text-slate-500 font-bold">#{i + 1}</span>
                            <span className="text-[8px] font-mono px-1.5 py-0.5 rounded bg-slate-900 border border-slate-800 text-cyan-300 font-bold">
                              {node.status}
                            </span>
                          </div>
                          <strong className="text-[10px] font-mono font-bold text-white uppercase block mt-1.5">
                            {node.stage.replace(/_/g, " ")}
                          </strong>
                        </div>
                        <div className="border-t border-slate-800/80 pt-2">
                          <span className="text-[9px] font-mono text-slate-400 block truncate" title={node.identifier}>
                            {node.identifier}
                          </span>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
    
                {/* Decision Trace Explorer (Case-Level Explainability) */}
                <div className="rounded-2xl border border-slate-800 bg-slate-900/80 p-6 space-y-6 shadow-xl">
                  <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between border-b border-slate-800 pb-4 gap-2">
                    <div>
                      <h3 className="text-base font-bold text-white flex items-center gap-2">
                        <span>Decision Trace Explorer</span>
                        <span className="rounded bg-emerald-950 border border-emerald-700/60 px-2 py-0.5 text-[10px] font-mono text-emerald-300 uppercase font-bold">
                          Zero-PII Forensic Lineage
                        </span>
                      </h3>
                      <p className="text-xs text-slate-400 mt-1">
                        Trace any recovery case across all 6 chronological execution stages from failure ingestion to final financial reconciliation.
                      </p>
                    </div>
                  </div>
    
                  {/* Case Input & Quick Trace Actions */}
                  <div className="flex flex-col sm:flex-row items-center gap-3">
                    <input
                      type="text"
                      value={decisionTraceCaseId}
                      onChange={(e) => setDecisionTraceCaseId(e.target.value)}
                      placeholder="Enter Recovery Case UUID (e.g. 550e8400-e29b-41d4-a716-446655440000)..."
                      className="w-full flex-1 rounded-xl border border-slate-800 bg-slate-950 px-4 py-2.5 text-xs text-slate-100 placeholder-slate-500 focus:border-indigo-500 focus:outline-none font-mono"
                    />
                    <button
                      onClick={() => handleFetchDecisionTrace()}
                      disabled={decisionTraceLoading || !decisionTraceCaseId.trim()}
                      className="w-full sm:w-auto rounded-xl bg-gradient-to-r from-indigo-600 to-purple-600 px-5 py-2.5 text-xs font-bold text-white shadow-lg shadow-indigo-600/30 hover:opacity-90 transition disabled:opacity-50"
                    >
                      {decisionTraceLoading ? "Tracing Pipeline..." : "Trace Case Lineage"}
                    </button>
                  </div>
    
                  {decisionTraceError && (
                    <div className="rounded-xl border border-rose-800/60 bg-rose-950/40 p-3 text-xs text-rose-300 font-mono">
                      {decisionTraceError}
                    </div>
                  )}
    
                  {/* Traced Case Lineage Output */}
                  {decisionTraceData && (
                    <div className="space-y-6 pt-2">
                      {/* Case Header Metrics */}
                      <div className="rounded-xl border border-slate-800 bg-slate-950/80 p-4 grid grid-cols-2 gap-4 sm:grid-cols-4 lg:grid-cols-6 text-xs font-mono">
                        <div>
                          <span className="text-[10px] text-slate-500 uppercase block font-bold">Case ID</span>
                          <span className="text-cyan-300 truncate block">{decisionTraceData.case_id}</span>
                        </div>
                        <div>
                          <span className="text-[10px] text-slate-500 uppercase block font-bold">Outcome</span>
                          <span className="text-emerald-400 font-bold">{decisionTraceData.final_recovery_outcome}</span>
                        </div>
                        <div>
                          <span className="text-[10px] text-slate-500 uppercase block font-bold">Amount at Risk</span>
                          <span className="text-slate-200">{formatINR(decisionTraceData.amount_at_risk_paise)}</span>
                        </div>
                        <div>
                          <span className="text-[10px] text-slate-500 uppercase block font-bold">Recovered</span>
                          <span className="text-emerald-300 font-bold">{formatINR(decisionTraceData.recovered_amount_paise)}</span>
                        </div>
                        <div>
                          <span className="text-[10px] text-slate-500 uppercase block font-bold">Model Version</span>
                          <span className="text-purple-300">{decisionTraceData.model_version}</span>
                        </div>
                        <div>
                          <span className="text-[10px] text-slate-500 uppercase block font-bold">Inferred Prob</span>
                          <span className="text-amber-300 font-bold">
                            {(decisionTraceData.prediction_probability * 100).toFixed(1)}%
                          </span>
                        </div>
                      </div>
    
                      {/* 6-Stage Chronological Pipeline Timeline */}
                      <div className="space-y-3">
                        <span className="text-xs font-mono font-bold uppercase tracking-wider text-slate-400 block">
                          Chronological Decision Timeline:
                        </span>
                        <div className="space-y-3">
                          {decisionTraceData.stages.map((st, i) => (
                            <div
                              key={i}
                              className="rounded-xl border border-slate-800 bg-slate-950/60 p-4 space-y-2 hover:border-slate-700 transition"
                            >
                              <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-1">
                                <div className="flex items-center gap-2">
                                  <span className="h-5 w-5 rounded-full bg-slate-900 border border-slate-700 text-slate-300 flex items-center justify-center text-[10px] font-mono font-bold">
                                    {i + 1}
                                  </span>
                                  <strong className="text-xs font-mono font-bold text-white uppercase">
                                    {st.stage_name.replace(/_/g, " ")}
                                  </strong>
                                  <span className="rounded bg-slate-900 border border-slate-800 px-2 py-0.5 text-[9px] font-mono text-cyan-300 font-bold">
                                    {st.status}
                                  </span>
                                </div>
                                <span className="text-[10px] font-mono text-slate-500">
                                  {st.timestamp ? new Date(st.timestamp).toLocaleTimeString() : "Synchronous"}
                                </span>
                              </div>
    
                              <div className="rounded-lg bg-slate-900/60 p-3 text-[11px] font-mono text-slate-300 flex flex-wrap gap-x-6 gap-y-1">
                                {Object.entries(st.details).map(([k, v]) => (
                                  <div key={k} className="flex items-center gap-1.5">
                                    <span className="text-slate-500">{k}:</span>
                                    <span className="text-slate-200 font-semibold">{String(v)}</span>
                                  </div>
                                ))}
                              </div>
                            </div>
                          ))}
                        </div>
                      </div>
    
                      {/* Feature Snapshot (Zero-PII) */}
                      <div className="rounded-xl border border-slate-800 bg-slate-950/60 p-4 space-y-3">
                        <div className="flex items-center justify-between">
                          <span className="text-xs font-mono font-bold uppercase tracking-wider text-slate-400">
                            Inference Feature Snapshot (Strictly Zero-PII)
                          </span>
                          <span className="text-[10px] font-mono text-emerald-400 bg-emerald-950/80 px-2 py-0.5 rounded border border-emerald-700/60">
                            Sanitized Telemetry
                          </span>
                        </div>
                        <div className="grid grid-cols-2 gap-3 sm:grid-cols-4 text-xs font-mono">
                          <div className="rounded bg-slate-900 p-2.5 border border-slate-800/80">
                            <span className="text-[10px] text-slate-500 block">Payment Amount</span>
                            <span className="text-slate-200 font-bold">
                              {formatINR(decisionTraceData.feature_snapshot.payment_amount_paise)}
                            </span>
                          </div>
                          <div className="rounded bg-slate-900 p-2.5 border border-slate-800/80">
                            <span className="text-[10px] text-slate-500 block">Attempt Number</span>
                            <span className="text-slate-200 font-bold">
                              #{decisionTraceData.feature_snapshot.attempt_number}
                            </span>
                          </div>
                          <div className="rounded bg-slate-900 p-2.5 border border-slate-800/80">
                            <span className="text-[10px] text-slate-500 block">Customer Success Rate</span>
                            <span className="text-emerald-300 font-bold">
                              {(decisionTraceData.feature_snapshot.customer_success_rate * 100).toFixed(1)}%
                            </span>
                          </div>
                          <div className="rounded bg-slate-900 p-2.5 border border-slate-800/80">
                            <span className="text-[10px] text-slate-500 block">Error Code</span>
                            <span className="text-rose-300 font-bold">
                              {decisionTraceData.feature_snapshot.error_code}
                            </span>
                          </div>
                        </div>
                      </div>
                    </div>
                  )}
                </div>
              </div>


    </>
  );
}
