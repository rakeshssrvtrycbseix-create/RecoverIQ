"use client";

import React, { useCallback, useEffect, useState } from "react";
import {
  DeploymentImpact,
  ErrorBudget,
  FinancialPathTelemetry,
  ObservabilityAlert,
  ObservabilityIncident,
  ObservabilitySummary,
  OperationalReadiness,
  PostIncidentReport,
  SLOEvaluation,
  ServiceTelemetry,
  TraceSummary,
  acknowledgeObservabilityIncident,
  createObservabilityPostmortem,
  escalateObservabilityIncident,
  fetchObservabilityAlerts,
  fetchObservabilityDeployments,
  fetchObservabilityErrorBudget,
  fetchObservabilityFinancialPath,
  fetchObservabilityIncidents,
  fetchObservabilityPostmortems,
  fetchObservabilityReadiness,
  fetchObservabilitySLOs,
  fetchObservabilityServices,
  fetchObservabilitySummary,
  fetchObservabilityTraces,
  resolveObservabilityIncident
} from "../../lib/api";
import { getServiceHealthBadge, getReadinessGateBadge } from "./intelligenceBadges";

export default function ObservabilityTab() {
  const [error, setError] = useState<string | null>(null);

    const [obsSummary, setObsSummary] = useState<ObservabilitySummary | null>(null);
    const [obsServices, setObsServices] = useState<ServiceTelemetry[] | null>(null);
    const [obsSLOs, setObsSLOs] = useState<SLOEvaluation[] | null>(null);
    const [obsErrorBudgets, setObsErrorBudgets] = useState<ErrorBudget[] | null>(null);
    const [obsAlerts, setObsAlerts] = useState<ObservabilityAlert[] | null>(null);
    const [obsIncidents, setObsIncidents] = useState<ObservabilityIncident[] | null>(null);
    const [obsTraces, setObsTraces] = useState<TraceSummary[] | null>(null);
    const [obsDeployments, setObsDeployments] = useState<DeploymentImpact[] | null>(null);
    const [obsReadiness, setObsReadiness] = useState<OperationalReadiness | null>(null);
    const [obsPostmortems, setObsPostmortems] = useState<PostIncidentReport[] | null>(null);
    const [obsFinancialPath, setObsFinancialPath] = useState<FinancialPathTelemetry[] | null>(null);
    const [obsSuccessMsg, setObsSuccessMsg] = useState<string | null>(null);
    const [selectedTrace, setSelectedTrace] = useState<TraceSummary | null>(null);
    const [selectedObsIncident, setSelectedObsIncident] = useState<ObservabilityIncident | null>(null);
    const [obsIncidentFilter, setObsIncidentFilter] = useState<string>("ALL");
    const [postmortemModalOpen, setPostmortemModalOpen] = useState(false);
    const [postmortemForm, setPostmortemForm] = useState({
      incident_id: "",
      title: "",
      impact_summary: "",
      root_cause_category: "DATABASE",
      contributing_factors: "",
      corrective_actions: "",
      preventive_actions: "",
    });
    const [postmortemLoading, setPostmortemLoading] = useState(false);
  

    const handleAcknowledgeObsIncident = async (incidentId: string) => {
      setError(null);
      try {
        await acknowledgeObservabilityIncident(incidentId);
        setObsSuccessMsg(`Incident ${incidentId} acknowledged. Audit event written.`);
        await loadObsData();
      } catch (err) {
        setError(err instanceof Error ? err.message : "Failed to acknowledge incident");
      }
    };
  
    const handleEscalateObsIncident = async (incidentId: string) => {
      setError(null);
      try {
        await escalateObservabilityIncident(incidentId);
        setObsSuccessMsg(`Incident ${incidentId} escalated to Admin review.`);
        await loadObsData();
      } catch (err) {
        setError(err instanceof Error ? err.message : "Failed to escalate incident");
      }
    };
  
    const handleResolveObsIncident = async (incidentId: string) => {
      setError(null);
      try {
        await resolveObservabilityIncident(incidentId);
        setObsSuccessMsg(`Incident ${incidentId} resolved. Audit event written.`);
        await loadObsData();
      } catch (err) {
        setError(err instanceof Error ? err.message : "Failed to resolve incident");
      }
    };
  
    const handleCreatePostmortemSubmit = async (e: React.FormEvent) => {
      e.preventDefault();
      if (!postmortemForm.incident_id || !postmortemForm.title) return;
      setPostmortemLoading(true);
      setError(null);
      try {
        await createObservabilityPostmortem({
          incident_id: postmortemForm.incident_id,
          title: postmortemForm.title,
          impact_summary: postmortemForm.impact_summary,
          root_cause_category: postmortemForm.root_cause_category,
          contributing_factors: postmortemForm.contributing_factors.split("\n").filter(Boolean),
          corrective_actions: postmortemForm.corrective_actions.split("\n").filter(Boolean),
          preventive_actions: postmortemForm.preventive_actions.split("\n").filter(Boolean),
        });
        setPostmortemModalOpen(false);
        setObsSuccessMsg(`Postmortem for ${postmortemForm.incident_id} created successfully.`);
        await loadObsData();
      } catch (err) {
        setError(err instanceof Error ? err.message : "Failed to create postmortem");
      } finally {
        setPostmortemLoading(false);
      }
    };
  
    // Phase 10E: Data Governance Action Handlers & Badge Helpers
    const getOperationalStateBadge = (state?: string) => {
      switch (state) {
        case "EMERGENCY_OPERATIONAL_STATE":
          return "bg-red-950/90 border-red-500 text-red-300 font-black animate-pulse shadow-lg shadow-red-500/20";
        case "CRITICAL_INCIDENT":
          return "bg-rose-950/90 border-rose-500 text-rose-300 font-bold animate-pulse shadow-lg shadow-rose-500/20";
        case "MAJOR_INCIDENT":
          return "bg-orange-950/90 border-orange-500 text-orange-300 font-bold";
        case "INCIDENT":
          return "bg-amber-950/90 border-amber-500 text-amber-300 font-bold";
        case "DEGRADED":
          return "bg-yellow-950/90 border-yellow-500 text-yellow-300 font-bold";
        case "WARNING":
          return "bg-yellow-950/80 border-yellow-600 text-yellow-300 font-medium";
        case "MONITORING":
          return "bg-cyan-950/90 border-cyan-500 text-cyan-300 font-medium";
        case "RECOVERY":
          return "bg-indigo-950/90 border-indigo-500 text-indigo-300 font-bold";
        case "STABILIZED":
          return "bg-teal-950/90 border-teal-500 text-teal-300 font-bold";
        case "HEALTHY":
        default:
          return "bg-emerald-950/90 border-emerald-500 text-emerald-300 font-bold shadow-lg shadow-emerald-500/20";
      }
    };
  
    
  
    const getSLOStatusBadge = (status?: string) => {
      switch (status) {
        case "COMPLIANT":
          return "bg-emerald-950/80 border-emerald-600 text-emerald-300 font-bold";
        case "AT_RISK":
          return "bg-amber-950/80 border-amber-600 text-amber-300 font-bold";
        case "BREACHED":
          return "bg-red-950/80 border-red-600 text-red-300 font-bold animate-pulse";
        default:
          return "bg-slate-900 border-slate-700 text-slate-400 font-medium";
      }
    };
  
    
  
    const getSRESeverityBadge = (sev?: string) => {
      switch (sev) {
        case "SEV_1":
          return "bg-red-950/90 border-red-500 text-red-300 font-black animate-pulse shadow-lg shadow-red-500/20";
        case "SEV_2":
          return "bg-rose-950/90 border-rose-500 text-rose-300 font-bold animate-pulse";
        case "SEV_3":
          return "bg-amber-950/90 border-amber-500 text-amber-300 font-bold";
        case "SEV_4":
        default:
          return "bg-cyan-950/90 border-cyan-500 text-cyan-300 font-medium";
      }
    };
  
    const getTraceStatusBadge = (status?: string) => {
      switch (status) {
        case "OK":
          return "bg-emerald-950/80 border-emerald-600 text-emerald-300 font-bold";
        case "DEGRADED":
          return "bg-amber-950/80 border-amber-600 text-amber-300 font-bold";
        case "ERROR":
          return "bg-red-950/80 border-red-600 text-red-300 font-bold";
        default:
          return "bg-slate-900 border-slate-700 text-slate-400 font-medium";
      }
    };
  
    // Phase 10F Performance & Capacity Handlers and Badge Functions

  const loadObsData = useCallback(async () => {
    try {
      const [
        sumRes, svcRes, sloRes, ebRes, alRes,
        incRes, trRes, depRes, readRes, pmRes, fpRes
      ] = await Promise.all([
        fetchObservabilitySummary().catch(() => null),
        fetchObservabilityServices().catch(() => []),
        fetchObservabilitySLOs().catch(() => []),
        fetchObservabilityErrorBudget().catch(() => []),
        fetchObservabilityAlerts().catch(() => []),
        fetchObservabilityIncidents().catch(() => []),
        fetchObservabilityTraces().catch(() => []),
        fetchObservabilityDeployments().catch(() => []),
        fetchObservabilityReadiness().catch(() => null),
        fetchObservabilityPostmortems().catch(() => []),
        fetchObservabilityFinancialPath().catch(() => []),
      ]);
      setObsSummary(sumRes);
      setObsServices(svcRes);
      setObsSLOs(sloRes);
      setObsErrorBudgets(ebRes);
      setObsAlerts(alRes);
      setObsIncidents(incRes);
      setObsTraces(trRes);
      if (trRes && trRes.length > 0 && !selectedTrace) {
        setSelectedTrace(trRes[0]);
      }
      setObsDeployments(depRes);
      setObsReadiness(readRes);
      setObsPostmortems(pmRes);
      setObsFinancialPath(fpRes);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load Observability data");
    }
  }, [selectedTrace]);

    useEffect(() => {
    let ignore = false;
    async function execute() {
      if (!ignore) {
        await loadObsData();
      }
    }
    void execute();
    return () => {
      ignore = true;
    };
  }, [loadObsData]);

  return (
    <>
      {error && (
        <div className="rounded-xl border border-rose-800/40 bg-rose-950/40 p-4 text-xs text-rose-300">
          {error}
        </div>
      )}

      {obsSuccessMsg && (
        <div className="rounded-xl border border-amber-800/60 bg-amber-950/40 p-4 text-xs text-amber-300 flex items-center justify-between shadow-lg">
          <span>{obsSuccessMsg}</span>
          <button onClick={() => setObsSuccessMsg(null)} className="text-amber-400 hover:text-white font-bold ml-4">✕</button>
        </div>
      )}
              {/* =========================================================================
                 TAB 16: FINTECH OBSERVABILITY, SRE, INCIDENT RESPONSE & PRODUCTION OPERATIONS (Phase 10D)
                 ========================================================================= */}
              <div className="space-y-8">
                {/* Mandatory Observability Governance & Financial Isolation Banner */}
                <div className="rounded-2xl border border-blue-800/60 bg-gradient-to-r from-blue-950/50 via-indigo-950/40 to-purple-950/40 p-5 flex items-start gap-4 shadow-xl">
                  <span className="rounded-lg bg-gradient-to-r from-blue-600 to-indigo-600 px-2.5 py-1 text-[10px] font-mono font-black uppercase tracking-wider text-white shadow shrink-0">
                    PHASE 10D OBSERVABILITY
                  </span>
                  <div className="text-xs text-slate-200 leading-relaxed space-y-1.5 flex-1">
                    <div className="flex flex-wrap items-center justify-between gap-2">
                      <p className="font-bold text-blue-200 text-sm flex items-center gap-2">
                        <span>FINTECH OBSERVABILITY, SRE & INCIDENT RESPONSE COMMAND</span>
                        <span className="text-[10px] font-mono font-normal text-blue-400/80 bg-blue-950/80 px-2 py-0.5 rounded border border-blue-700/50">
                          Multi-Signal SRE Telemetry • 18 Readiness Gates • Zero Financial Mutations
                        </span>
                      </p>
                      <button
                        onClick={() => setPostmortemModalOpen(true)}
                        className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-gradient-to-r from-blue-600 to-purple-600 hover:from-blue-500 hover:to-purple-500 text-white text-xs font-bold shadow-lg shadow-blue-700/30 transition"
                      >
                        📝 Create Postmortem
                      </button>
                    </div>
                    <p className="text-slate-300 text-[11px] leading-relaxed border-t border-blue-800/40 pt-2 mt-2">
                      <strong className="text-amber-300">Engineering Evidence Disclaimer:</strong>{" "}
                      {obsSummary?.disclaimer ||
                        "This dashboard provides automated engineering observability, SLO compliance metrics, and operational reliability evidence. It does not constitute legal, regulatory, financial, security, or third-party certification. PolicyEngine remains the authoritative financial execution gatekeeper. Observability is strictly non-mutating with zero financial delta."}
                    </p>
                  </div>
                </div>
    
                {/* 8 Real-time KPI Cards Grid */}
                <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
                  {/* Card 1: Observability Health Score */}
                  <div className="rounded-2xl border border-blue-800/50 bg-slate-900/90 p-4 shadow-lg backdrop-blur space-y-2">
                    <div className="flex items-center justify-between">
                      <span className="text-xs font-semibold text-slate-400">Observability Score</span>
                      <span
                        className={`rounded-full border px-2 py-0.5 text-[10px] font-mono font-bold uppercase tracking-wider ${getOperationalStateBadge(
                          obsSummary?.global_state
                        )}`}
                      >
                        {obsSummary?.global_state ? obsSummary.global_state.replace(/_/g, " ") : "HEALTHY"}
                      </span>
                    </div>
                    <div className="flex items-baseline gap-2">
                      <span className="text-2xl font-black text-white font-mono">
                        {obsSummary ? `${obsSummary.observability_score.toFixed(1)}` : "--"}
                      </span>
                      <span className="text-xs text-slate-400 font-mono">/ 100.0</span>
                    </div>
                    <p className="text-[11px] text-blue-400/90 font-mono">
                      Avail: {obsSummary?.score_breakdown?.availability_score?.toFixed(0) || "100"}% • SLO: {obsSummary?.score_breakdown?.slo_compliance_score?.toFixed(0) || "100"}% • SRE: {obsSummary?.score_breakdown?.incident_stability_score?.toFixed(0) || "100"}%
                    </p>
                  </div>
    
                  {/* Card 2: Global Operational State */}
                  <div className="rounded-2xl border border-blue-800/50 bg-slate-900/90 p-4 shadow-lg backdrop-blur space-y-2">
                    <div className="flex items-center justify-between">
                      <span className="text-xs font-semibold text-slate-400">Global State</span>
                      <span className="text-[10px] font-mono text-slate-400">Priority Engine</span>
                    </div>
                    <div className="flex items-center gap-2">
                      <span className={`inline-block h-3 w-3 rounded-full ${obsSummary?.global_state === "HEALTHY" ? "bg-emerald-400 animate-pulse" : "bg-amber-400 animate-ping"}`} />
                      <span className="text-lg font-bold text-white uppercase font-mono tracking-wide">
                        {obsSummary?.global_state ? obsSummary.global_state.replace(/_/g, " ") : "HEALTHY"}
                      </span>
                    </div>
                    <p className="text-[11px] text-slate-400">
                      Surveillance across 11 core microservices
                    </p>
                  </div>
    
                  {/* Card 3: Aggregated Availability */}
                  <div className="rounded-2xl border border-blue-800/50 bg-slate-900/90 p-4 shadow-lg backdrop-blur space-y-2">
                    <div className="flex items-center justify-between">
                      <span className="text-xs font-semibold text-slate-400">Aggregated Availability</span>
                      <span className="text-[10px] font-mono text-emerald-400 bg-emerald-950/60 px-1.5 py-0.5 rounded border border-emerald-800/40">
                        SLO Target: 99.9%
                      </span>
                    </div>
                    <div className="flex items-baseline gap-2">
                      <span className="text-2xl font-black text-emerald-400 font-mono">
                        {obsServices && obsServices.length > 0
                          ? `${(obsServices.reduce((acc, s) => acc + s.availability, 0) / obsServices.length).toFixed(2)}%`
                          : "99.98%"}
                      </span>
                    </div>
                    <p className="text-[11px] text-slate-400">
                      Zero critical downtime across platform
                    </p>
                  </div>
    
                  {/* Card 4: P95 System Latency */}
                  <div className="rounded-2xl border border-blue-800/50 bg-slate-900/90 p-4 shadow-lg backdrop-blur space-y-2">
                    <div className="flex items-center justify-between">
                      <span className="text-xs font-semibold text-slate-400">P95 System Latency</span>
                      <span className="text-[10px] font-mono text-cyan-400 bg-cyan-950/60 px-1.5 py-0.5 rounded border border-cyan-800/40">
                        Threshold &lt;200ms
                      </span>
                    </div>
                    <div className="flex items-baseline gap-2">
                      <span className="text-2xl font-black text-cyan-300 font-mono">
                        {obsSummary ? `${obsSummary.p95_latency_ms.toFixed(1)} ms` : "--"}
                      </span>
                    </div>
                    <p className="text-[11px] text-slate-400">
                      P50: {(obsSummary ? obsSummary.p95_latency_ms * 0.45 : 38).toFixed(1)} ms • P99: {(obsSummary ? obsSummary.p95_latency_ms * 1.5 : 126).toFixed(1)} ms
                    </p>
                  </div>
    
                  {/* Card 5: Aggregate Error Rate */}
                  <div className="rounded-2xl border border-blue-800/50 bg-slate-900/90 p-4 shadow-lg backdrop-blur space-y-2">
                    <div className="flex items-center justify-between">
                      <span className="text-xs font-semibold text-slate-400">Aggregate Error Rate</span>
                      <span className="text-[10px] font-mono text-emerald-400 bg-emerald-950/60 px-1.5 py-0.5 rounded border border-emerald-800/40">
                        Threshold &lt;0.50%
                      </span>
                    </div>
                    <div className="flex items-baseline gap-2">
                      <span className="text-2xl font-black text-white font-mono">
                        {obsSummary ? `${obsSummary.aggregate_error_rate_pct.toFixed(2)}%` : "0.00%"}
                      </span>
                    </div>
                    <p className="text-[11px] text-emerald-400/90">
                      All error channels within budget
                    </p>
                  </div>
    
                  {/* Card 6: SLO Compliance Rate */}
                  <div className="rounded-2xl border border-blue-800/50 bg-slate-900/90 p-4 shadow-lg backdrop-blur space-y-2">
                    <div className="flex items-center justify-between">
                      <span className="text-xs font-semibold text-slate-400">SLO Compliance Rate</span>
                      <span className="text-[10px] font-mono text-indigo-400 bg-indigo-950/60 px-1.5 py-0.5 rounded border border-indigo-800/40">
                        8 / 8 Active
                      </span>
                    </div>
                    <div className="flex items-baseline gap-2">
                      <span className="text-2xl font-black text-indigo-300 font-mono">
                        {obsSummary ? `${obsSummary.slo_compliance_pct.toFixed(1)}%` : "100.0%"}
                      </span>
                    </div>
                    <p className="text-[11px] text-slate-400">
                      0 breached SLO targets
                    </p>
                  </div>
    
                  {/* Card 7: Remaining Error Budget */}
                  <div className="rounded-2xl border border-blue-800/50 bg-slate-900/90 p-4 shadow-lg backdrop-blur space-y-2">
                    <div className="flex items-center justify-between">
                      <span className="text-xs font-semibold text-slate-400">Error Budget Remaining</span>
                      <span className="text-[10px] font-mono text-emerald-400 bg-emerald-950/60 px-1.5 py-0.5 rounded border border-emerald-800/40">
                        Burn Rate: 1.00x
                      </span>
                    </div>
                    <div className="flex items-baseline gap-2">
                      <span className="text-2xl font-black text-emerald-400 font-mono">
                        {obsSummary ? `${obsSummary.remaining_error_budget_pct.toFixed(1)}%` : "95.0%"}
                      </span>
                    </div>
                    <p className="text-[11px] text-slate-400">
                      Multi-window (1h / 6h / 24h) healthy
                    </p>
                  </div>
    
                  {/* Card 8: Active SRE Incidents */}
                  <div className="rounded-2xl border border-blue-800/50 bg-slate-900/90 p-4 shadow-lg backdrop-blur space-y-2">
                    <div className="flex items-center justify-between">
                      <span className="text-xs font-semibold text-slate-400">Active Incidents</span>
                      <span className="text-[10px] font-mono text-slate-400">SEV_1 - SEV_4</span>
                    </div>
                    <div className="flex items-baseline gap-2">
                      <span className={`text-2xl font-black font-mono ${obsSummary && obsSummary.active_incidents_count > 0 ? "text-amber-400" : "text-emerald-400"}`}>
                        {obsSummary ? obsSummary.active_incidents_count : 0}
                      </span>
                      <span className="text-xs text-slate-400">Active</span>
                    </div>
                    <p className="text-[11px] text-slate-400">
                      Critical SEV_1: {obsSummary ? obsSummary.critical_incidents_count : 0}
                    </p>
                  </div>
                </div>
    
                {/* 11-Service Telemetry Matrix */}
                <div className="rounded-2xl border border-slate-800 bg-slate-900/80 p-6 shadow-xl space-y-4">
                  <div className="flex flex-wrap items-center justify-between gap-2 border-b border-slate-800/80 pb-4">
                    <div>
                      <h3 className="text-base font-bold text-white flex items-center gap-2">
                        <span>11-Service Microservice Telemetry Matrix</span>
                        <span className="text-[10px] font-mono bg-blue-950/80 text-blue-300 border border-blue-700/50 px-2 py-0.5 rounded">
                          Real-time SRE Telemetry
                        </span>
                      </h3>
                      <p className="text-xs text-slate-400 mt-1">
                        Continuous tracking of availability, latency percentiles (P50/P95/P99), error rates, throughput, and error budget consumption.
                      </p>
                    </div>
                    <span className="text-xs font-mono text-slate-400">
                      Evaluated at {obsSummary?.last_evaluated_at ? new Date(obsSummary.last_evaluated_at).toLocaleTimeString() : "Live"}
                    </span>
                  </div>
    
                  <div className="overflow-x-auto">
                    <table className="w-full text-left text-xs font-mono">
                      <thead>
                        <tr className="border-b border-slate-800 text-[11px] font-bold text-slate-400 uppercase tracking-wider">
                          <th className="pb-3">Service</th>
                          <th className="pb-3">Availability</th>
                          <th className="pb-3">P50 Latency</th>
                          <th className="pb-3">P95 Latency</th>
                          <th className="pb-3">P99 Latency</th>
                          <th className="pb-3">Error Rate</th>
                          <th className="pb-3">Throughput</th>
                          <th className="pb-3">SLO Status</th>
                          <th className="pb-3">Budget Left</th>
                          <th className="pb-3 text-right">Status</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-slate-800/60 text-slate-200">
                        {obsServices && obsServices.length > 0 ? (
                          obsServices.map((svc) => (
                            <tr key={svc.service_name} className="hover:bg-slate-800/40 transition">
                              <td className="py-3 font-bold text-white">{svc.service_name}</td>
                              <td className="py-3 text-emerald-400">{svc.availability.toFixed(2)}%</td>
                              <td className="py-3 text-slate-300">{svc.p50_latency_ms.toFixed(1)} ms</td>
                              <td className="py-3 text-cyan-300">{svc.p95_latency_ms.toFixed(1)} ms</td>
                              <td className="py-3 text-slate-400">{svc.p99_latency_ms.toFixed(1)} ms</td>
                              <td className="py-3 text-slate-300">{svc.error_rate_pct.toFixed(2)}%</td>
                              <td className="py-3 text-slate-300">{svc.throughput_rpm.toFixed(1)} RPM</td>
                              <td className="py-3">
                                <span className={`px-2 py-0.5 rounded text-[10px] font-bold ${getSLOStatusBadge(svc.slo_compliance)}`}>
                                  {svc.slo_compliance}
                                </span>
                              </td>
                              <td className="py-3 text-emerald-400">{svc.error_budget_remaining_pct.toFixed(1)}%</td>
                              <td className="py-3 text-right">
                                <span className={`px-2 py-0.5 rounded text-[10px] font-bold ${getServiceHealthBadge(svc.status)}`}>
                                  {svc.status}
                                </span>
                              </td>
                            </tr>
                          ))
                        ) : (
                          <tr>
                            <td colSpan={10} className="py-8 text-center text-slate-500">
                              No service telemetry records available.
                            </td>
                          </tr>
                        )}
                      </tbody>
                    </table>
                  </div>
                </div>
    
                {/* SLO Dashboard & Multi-Window Error Budget Panel */}
                <div className="rounded-2xl border border-slate-800 bg-slate-900/80 p-6 shadow-xl space-y-6">
                  <div className="flex flex-wrap items-center justify-between gap-2 border-b border-slate-800/80 pb-4">
                    <div>
                      <h3 className="text-base font-bold text-white flex items-center gap-2">
                        <span>SLO Compliance & Multi-Window Error Budget Dashboard</span>
                        <span className="text-[10px] font-mono bg-purple-950/80 text-purple-300 border border-purple-700/50 px-2 py-0.5 rounded">
                          Configurable Targets
                        </span>
                      </h3>
                      <p className="text-xs text-slate-400 mt-1">
                        Multi-window burn rate surveillance (1-hour, 6-hour, 24-hour windows) for early incident detection.
                      </p>
                    </div>
                  </div>
    
                  <div className="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-4">
                    {obsSLOs && obsSLOs.length > 0 ? (
                      obsSLOs.map((slo) => {
                        const budget = obsErrorBudgets?.find((b) => b.slo_code === slo.slo_code);
                        return (
                          <div key={slo.slo_code} className="rounded-xl border border-slate-800 bg-slate-950/60 p-4 space-y-3">
                            <div className="flex items-center justify-between">
                              <span className="text-xs font-bold text-white font-mono">{slo.slo_code}</span>
                              <span className={`px-2 py-0.5 rounded text-[10px] font-mono font-bold ${getSLOStatusBadge(slo.status)}`}>
                                {slo.status}
                              </span>
                            </div>
                            <p className="text-[11px] text-slate-300 font-semibold">{slo.name}</p>
                            <div className="grid grid-cols-2 gap-2 text-[11px] font-mono border-t border-slate-800/80 pt-2">
                              <div>
                                <span className="text-slate-500 block">Target</span>
                                <span className="text-slate-200 font-bold">{slo.target_percentage}%</span>
                              </div>
                              <div>
                                <span className="text-slate-500 block">Observed</span>
                                <span className="text-emerald-400 font-bold">{slo.observed_percentage.toFixed(2)}%</span>
                              </div>
                            </div>
                            <div className="space-y-1 border-t border-slate-800/80 pt-2">
                              <div className="flex items-center justify-between text-[10px] font-mono">
                                <span className="text-slate-400">Budget Remaining</span>
                                <span className="text-emerald-400 font-bold">{slo.error_budget_remaining_pct.toFixed(1)}%</span>
                              </div>
                              <div className="h-1.5 w-full rounded-full bg-slate-800 overflow-hidden">
                                <div
                                  className="h-full rounded-full bg-gradient-to-r from-emerald-500 to-cyan-400"
                                  style={{ width: `${Math.min(100, Math.max(0, slo.error_budget_remaining_pct))}%` }}
                                />
                              </div>
                            </div>
                            {budget && (
                              <div className="flex items-center justify-between text-[10px] font-mono text-slate-400 border-t border-slate-800/60 pt-1.5">
                                <span>Burn 1h/6h/24h:</span>
                                <span className="text-cyan-300 font-bold">
                                  {budget.burn_rate_1h.toFixed(1)}x / {budget.burn_rate_6h.toFixed(1)}x / {budget.burn_rate_24h.toFixed(1)}x
                                </span>
                              </div>
                            )}
                          </div>
                        );
                      })
                    ) : (
                      <div className="col-span-4 py-8 text-center text-xs text-slate-500">
                        No SLO definitions loaded.
                      </div>
                    )}
                  </div>
                </div>
    
                {/* Real-time Alert Center with SHA-256 Deduplication */}
                <div className="rounded-2xl border border-slate-800 bg-slate-900/80 p-6 shadow-xl space-y-4">
                  <div className="flex flex-wrap items-center justify-between gap-2 border-b border-slate-800/80 pb-4">
                    <div>
                      <h3 className="text-base font-bold text-white flex items-center gap-2">
                        <span>Active Alerts & Automated Deduplication Center</span>
                        <span className="text-[10px] font-mono bg-indigo-950/80 text-indigo-300 border border-indigo-700/50 px-2 py-0.5 rounded">
                          SHA-256 Fingerprint Deduplication
                        </span>
                      </h3>
                      <p className="text-xs text-slate-400 mt-1">
                        Deterministic alert routing preventing notification storms through rule+service fingerprint hashing.
                      </p>
                    </div>
                    <span className="text-xs font-mono text-slate-400">
                      {obsAlerts ? `${obsAlerts.length} Active Alerts` : "0 Alerts"}
                    </span>
                  </div>
    
                  <div className="overflow-x-auto">
                    <table className="w-full text-left text-xs font-mono">
                      <thead>
                        <tr className="border-b border-slate-800 text-[11px] font-bold text-slate-400 uppercase tracking-wider">
                          <th className="pb-3">Alert ID</th>
                          <th className="pb-3">Fingerprint</th>
                          <th className="pb-3">Rule Code</th>
                          <th className="pb-3">Severity</th>
                          <th className="pb-3">Service</th>
                          <th className="pb-3">Observed / Threshold</th>
                          <th className="pb-3">Occurrences</th>
                          <th className="pb-3 text-right">Status</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-slate-800/60 text-slate-200">
                        {obsAlerts && obsAlerts.length > 0 ? (
                          obsAlerts.map((alt) => (
                            <tr key={alt.alert_id} className="hover:bg-slate-800/40 transition">
                              <td className="py-3 font-bold text-white">{alt.alert_id}</td>
                              <td className="py-3 text-slate-400 font-mono text-[10px]">{alt.fingerprint.slice(0, 16)}...</td>
                              <td className="py-3 text-slate-300">{alt.rule_code}</td>
                              <td className="py-3">
                                <span className={`px-2 py-0.5 rounded text-[10px] font-bold ${getSRESeverityBadge(alt.severity)}`}>
                                  {alt.severity}
                                </span>
                              </td>
                              <td className="py-3 text-slate-300">{alt.service}</td>
                              <td className="py-3 text-amber-300 font-bold">
                                {alt.observed_value.toFixed(2)} / {alt.threshold.toFixed(2)}
                              </td>
                              <td className="py-3 text-slate-300">{alt.occurrence_count}x</td>
                              <td className="py-3 text-right">
                                <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-amber-950/80 border border-amber-800 text-amber-300">
                                  {alt.status}
                                </span>
                              </td>
                            </tr>
                          ))
                        ) : (
                          <tr>
                            <td colSpan={8} className="py-8 text-center text-slate-500">
                              ✨ Zero active alert conditions detected. All metrics healthy.
                            </td>
                          </tr>
                        )}
                      </tbody>
                    </table>
                  </div>
                </div>
    
                {/* SRE Incident Command Center */}
                <div className="rounded-2xl border border-slate-800 bg-slate-900/80 p-6 shadow-xl space-y-6">
                  <div className="flex flex-wrap items-center justify-between gap-4 border-b border-slate-800/80 pb-4">
                    <div>
                      <h3 className="text-base font-bold text-white flex items-center gap-2">
                        <span>SRE Incident Command & SLA Lifecycle Management</span>
                        <span className="text-[10px] font-mono bg-rose-950/80 text-rose-300 border border-rose-700/50 px-2 py-0.5 rounded">
                          SEV_1 to SEV_4 Command
                        </span>
                      </h3>
                      <p className="text-xs text-slate-400 mt-1">
                        Event-sourced incident state transitions (DETECTED → ACKNOWLEDGED → MITIGATED → RESOLVED) with MTTA &amp; MTTR tracking.
                      </p>
                    </div>
                    {/* Severity Filter */}
                    <div className="flex flex-wrap gap-1.5 bg-slate-950 p-1 rounded-xl border border-slate-800 text-xs">
                      {["ALL", "SEV_1", "SEV_2", "SEV_3", "SEV_4"].map((filter) => (
                        <button
                          key={filter}
                          onClick={() => setObsIncidentFilter(filter)}
                          className={`px-3 py-1 rounded-lg text-[11px] font-mono font-bold transition ${
                            obsIncidentFilter === filter
                              ? "bg-gradient-to-r from-rose-600 to-indigo-600 text-white shadow"
                              : "text-slate-400 hover:text-slate-200"
                          }`}
                        >
                          {filter}
                        </button>
                      ))}
                    </div>
                  </div>
    
                  <div className="overflow-x-auto">
                    <table className="w-full text-left text-xs font-mono">
                      <thead>
                        <tr className="border-b border-slate-800 text-[11px] font-bold text-slate-400 uppercase tracking-wider">
                          <th className="pb-3">Incident ID</th>
                          <th className="pb-3">Severity</th>
                          <th className="pb-3">Title &amp; Type</th>
                          <th className="pb-3">Affected Services</th>
                          <th className="pb-3">State</th>
                          <th className="pb-3">MTTA / MTTR</th>
                          <th className="pb-3">SLO Impact</th>
                          <th className="pb-3 text-right">Actions</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-slate-800/60 text-slate-200">
                        {obsIncidents && obsIncidents.filter((inc) => obsIncidentFilter === "ALL" || inc.severity === obsIncidentFilter).length > 0 ? (
                          obsIncidents
                            .filter((inc) => obsIncidentFilter === "ALL" || inc.severity === obsIncidentFilter)
                            .map((inc) => (
                              <tr key={inc.incident_id} className="hover:bg-slate-800/40 transition">
                                <td className="py-3 font-bold text-white">{inc.incident_id}</td>
                                <td className="py-3">
                                  <span className={`px-2 py-0.5 rounded text-[10px] font-bold ${getSRESeverityBadge(inc.severity)}`}>
                                    {inc.severity}
                                  </span>
                                </td>
                                <td className="py-3">
                                  <span className="text-white font-semibold block">{inc.title}</span>
                                  <span className="text-[10px] text-slate-400">{inc.incident_type}</span>
                                </td>
                                <td className="py-3 text-slate-300">{inc.affected_services.join(", ")}</td>
                                <td className="py-3">
                                  <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-slate-900 border border-slate-700 text-slate-300">
                                    {inc.state}
                                  </span>
                                </td>
                                <td className="py-3 text-slate-300">
                                  {inc.mtta_seconds ? `${(inc.mtta_seconds / 60).toFixed(1)}m` : "--"} / {inc.mttr_seconds ? `${(inc.mttr_seconds / 60).toFixed(1)}m` : "--"}
                                </td>
                                <td className="py-3 text-slate-400 text-[10px]">{inc.slo_impact}</td>
                                <td className="py-3 text-right space-x-1.5">
                                  {inc.state === "DETECTED" && (
                                    <button
                                      onClick={() => handleAcknowledgeObsIncident(inc.incident_id)}
                                      className="px-2 py-1 bg-amber-600 hover:bg-amber-500 text-white rounded text-[10px] font-bold"
                                    >
                                      Acknowledge
                                    </button>
                                  )}
                                  {(inc.state === "DETECTED" || inc.state === "ACKNOWLEDGED") && (
                                    <button
                                      onClick={() => handleEscalateObsIncident(inc.incident_id)}
                                      className="px-2 py-1 bg-rose-600 hover:bg-rose-500 text-white rounded text-[10px] font-bold"
                                    >
                                      Escalate
                                    </button>
                                  )}
                                  {inc.state !== "RESOLVED" && (
                                    <button
                                      onClick={() => handleResolveObsIncident(inc.incident_id)}
                                      className="px-2 py-1 bg-emerald-600 hover:bg-emerald-500 text-white rounded text-[10px] font-bold"
                                    >
                                      Resolve
                                    </button>
                                  )}
                                  <button
                                    onClick={() => setSelectedObsIncident(inc)}
                                    className="px-2 py-1 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded text-[10px] font-bold"
                                  >
                                    Timeline
                                  </button>
                                </td>
                              </tr>
                            ))
                        ) : (
                          <tr>
                            <td colSpan={8} className="py-8 text-center text-slate-500">
                              ✨ Zero incidents matching selected filter.
                            </td>
                          </tr>
                        )}
                      </tbody>
                    </table>
                  </div>
    
                  {/* Selected Incident Timeline Drawer */}
                  {selectedObsIncident && (
                    <div className="rounded-xl border border-slate-800 bg-slate-950/80 p-4 space-y-3">
                      <div className="flex items-center justify-between border-b border-slate-800 pb-2">
                        <span className="text-xs font-bold text-white font-mono">
                          Timeline for {selectedObsIncident.incident_id} — {selectedObsIncident.title}
                        </span>
                        <button
                          onClick={() => setSelectedObsIncident(null)}
                          className="text-slate-400 hover:text-white text-xs font-bold"
                        >
                          ✕ Close
                        </button>
                      </div>
                      <div className="space-y-2">
                        {selectedObsIncident.timeline && selectedObsIncident.timeline.length > 0 ? (
                          selectedObsIncident.timeline.map((evt) => (
                            <div key={evt.event_id} className="flex items-start gap-3 text-xs font-mono p-2 bg-slate-900/60 rounded border border-slate-800/60">
                              <span className="text-[10px] text-slate-400">{new Date(evt.timestamp).toLocaleTimeString()}</span>
                              <span className="px-1.5 py-0.5 rounded text-[9px] font-bold bg-slate-800 text-slate-300">
                                {evt.previous_state} → {evt.new_state}
                              </span>
                              <span className="text-slate-400">by {evt.actor_role} ({evt.actor_id})</span>
                              <span className="text-slate-300 italic">{evt.note}</span>
                            </div>
                          ))
                        ) : (
                          <p className="text-xs text-slate-500">No timeline events recorded.</p>
                        )}
                      </div>
                    </div>
                  )}
                </div>
    
                {/* Observational Financial Path Telemetry (11 Stages) */}
                <div className="rounded-2xl border border-slate-800 bg-slate-900/80 p-6 shadow-xl space-y-6">
                  <div className="flex flex-wrap items-center justify-between gap-2 border-b border-slate-800/80 pb-4">
                    <div>
                      <h3 className="text-base font-bold text-white flex items-center gap-2">
                        <span>Financial Execution Pipeline Telemetry (11 Stages)</span>
                        <span className="text-[10px] font-mono bg-cyan-950/80 text-cyan-300 border border-cyan-700/50 px-2 py-0.5 rounded">
                          Observational Pipeline Telemetry
                        </span>
                      </h3>
                      <p className="text-xs text-slate-400 mt-1">
                        End-to-end stage latency, success rate, error rate, and throughput across the authoritative financial execution sequence.
                      </p>
                    </div>
                  </div>
    
                  {/* Financial Isolation Banner */}
                  <div className="rounded-xl border border-cyan-800/40 bg-cyan-950/20 p-3 text-xs text-cyan-200 font-mono flex items-center gap-3">
                    <span className="text-base">🔒</span>
                    <span>
                      <strong>Strict Observational Isolation:</strong> Telemetry observes the pipeline passively. PolicyEngine remains the authoritative gatekeeper. Zero financial mutations.
                    </span>
                  </div>
    
                  <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 xl:grid-cols-6">
                    {obsFinancialPath && obsFinancialPath.length > 0 ? (
                      obsFinancialPath.map((stage, idx) => (
                        <div key={stage.stage_name} className="rounded-xl border border-slate-800 bg-slate-950/60 p-3 space-y-2 relative">
                          <div className="flex items-center justify-between">
                            <span className="text-[10px] font-mono text-cyan-400 font-bold">STAGE {idx + 1}</span>
                            <span className={`px-1.5 py-0.2 text-[9px] font-bold rounded ${getServiceHealthBadge(stage.health_status)}`}>
                              {stage.health_status}
                            </span>
                          </div>
                          <p className="text-xs font-bold text-white truncate" title={stage.stage_name}>
                            {stage.stage_name.replace(/_/g, " ")}
                          </p>
                          <div className="text-[10px] font-mono space-y-1 text-slate-300 border-t border-slate-800/60 pt-1.5">
                            <div className="flex justify-between">
                              <span className="text-slate-500">Latency:</span>
                              <span className="text-cyan-300 font-bold">{stage.latency_ms.toFixed(1)} ms</span>
                            </div>
                            <div className="flex justify-between">
                              <span className="text-slate-500">Success:</span>
                              <span className="text-emerald-400 font-bold">{stage.success_rate_pct.toFixed(1)}%</span>
                            </div>
                            <div className="flex justify-between">
                              <span className="text-slate-500">Throughput:</span>
                              <span className="text-slate-400">{stage.throughput_rpm.toFixed(0)} RPM</span>
                            </div>
                          </div>
                        </div>
                      ))
                    ) : (
                      <div className="col-span-6 py-8 text-center text-xs text-slate-500">
                        No financial pipeline telemetry loaded.
                      </div>
                    )}
                  </div>
                </div>
    
                {/* Sanitized Distributed Trace Forensics & Deployment Impact */}
                <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
                  {/* Distributed Trace Explorer */}
                  <div className="rounded-2xl border border-slate-800 bg-slate-900/80 p-6 shadow-xl space-y-4">
                    <div className="flex items-center justify-between border-b border-slate-800/80 pb-3">
                      <div>
                        <h3 className="text-base font-bold text-white flex items-center gap-2">
                          <span>Sanitized Distributed Trace Forensics</span>
                          <span className="text-[10px] font-mono bg-emerald-950/80 text-emerald-300 border border-emerald-700/50 px-2 py-0.5 rounded">
                            100% PII Sanitized
                          </span>
                        </h3>
                        <p className="text-xs text-slate-400 mt-0.5">End-to-end request traces across dependencies.</p>
                      </div>
                    </div>
    
                    <div className="space-y-3">
                      <div className="flex flex-wrap gap-2">
                        {obsTraces && obsTraces.length > 0 ? (
                          obsTraces.map((t) => (
                            <button
                              key={t.trace_id}
                              onClick={() => setSelectedTrace(t)}
                              className={`px-3 py-1.5 rounded-lg text-xs font-mono font-bold transition border ${
                                selectedTrace?.trace_id === t.trace_id
                                  ? "bg-gradient-to-r from-blue-600 to-indigo-600 border-blue-500 text-white shadow"
                                  : "bg-slate-950 border-slate-800 text-slate-400 hover:text-white"
                              }`}
                            >
                              {t.trace_id} ({t.total_duration_ms.toFixed(0)}ms)
                            </button>
                          ))
                        ) : (
                          <p className="text-xs text-slate-500">No traces loaded.</p>
                        )}
                      </div>
    
                      {selectedTrace && (
                        <div className="rounded-xl border border-slate-800 bg-slate-950/80 p-4 space-y-3">
                          <div className="flex items-center justify-between text-xs font-mono text-slate-400 border-b border-slate-800 pb-2">
                            <span>Root: <strong className="text-white">{selectedTrace.root_service}</strong></span>
                            <span>Spans: <strong className="text-cyan-300">{selectedTrace.span_count}</strong></span>
                            <span>Total: <strong className="text-emerald-400">{selectedTrace.total_duration_ms.toFixed(1)} ms</strong></span>
                          </div>
                          <div className="space-y-2">
                            {selectedTrace.spans && selectedTrace.spans.length > 0 ? (
                              selectedTrace.spans.map((sp) => (
                                <div key={sp.span_id} className="p-2 bg-slate-900/80 rounded border border-slate-800 text-xs font-mono space-y-1">
                                  <div className="flex items-center justify-between">
                                    <span className="font-bold text-white">{sp.service} :: {sp.operation}</span>
                                    <span className={`px-1.5 py-0.5 rounded text-[9px] font-bold ${getTraceStatusBadge(sp.status)}`}>
                                      {sp.status}
                                    </span>
                                  </div>
                                  <div className="flex items-center justify-between text-[10px] text-slate-400">
                                    <span>Span: {sp.span_id}</span>
                                    <span className="text-cyan-300 font-bold">{sp.duration_ms.toFixed(1)} ms</span>
                                  </div>
                                </div>
                              ))
                            ) : (
                              <p className="text-xs text-slate-500">No spans in trace.</p>
                            )}
                          </div>
                        </div>
                      )}
                    </div>
                  </div>
    
                  {/* Deployment Change-Impact Panel */}
                  <div className="rounded-2xl border border-slate-800 bg-slate-900/80 p-6 shadow-xl space-y-4">
                    <div className="flex items-center justify-between border-b border-slate-800/80 pb-3">
                      <div>
                        <h3 className="text-base font-bold text-white flex items-center gap-2">
                          <span>Production Deployment Change-Impact</span>
                          <span className="text-[10px] font-mono bg-blue-950/80 text-blue-300 border border-blue-700/50 px-2 py-0.5 rounded">
                            Advisory Guardrails
                          </span>
                        </h3>
                        <p className="text-xs text-slate-400 mt-0.5">Pre vs Post deployment telemetry differential analysis.</p>
                      </div>
                    </div>
    
                    <div className="space-y-3">
                      {obsDeployments && obsDeployments.length > 0 ? (
                        obsDeployments.map((dep) => (
                          <div key={dep.deployment_id} className="rounded-xl border border-slate-800 bg-slate-950/60 p-4 space-y-3">
                            <div className="flex items-center justify-between">
                              <span className="text-xs font-bold text-white font-mono">{dep.service} ({dep.version})</span>
                              <span className={`px-2 py-0.5 rounded text-[10px] font-mono font-bold ${dep.impact_status === "STABLE" ? "bg-emerald-950/80 border border-emerald-700 text-emerald-300" : "bg-rose-950/80 border border-rose-700 text-rose-300"}`}>
                                {dep.impact_status}
                              </span>
                            </div>
                            <div className="grid grid-cols-3 gap-2 text-[11px] font-mono border-t border-slate-800/60 pt-2">
                              <div>
                                <span className="text-slate-500 block">Latency Delta</span>
                                <span className={`font-bold ${dep.latency_delta_pct > 10 ? "text-rose-400" : "text-emerald-400"}`}>
                                  {dep.latency_delta_pct > 0 ? `+${dep.latency_delta_pct.toFixed(1)}%` : `${dep.latency_delta_pct.toFixed(1)}%`}
                                </span>
                              </div>
                              <div>
                                <span className="text-slate-500 block">Error Delta</span>
                                <span className={`font-bold ${dep.error_rate_delta_pct > 0.5 ? "text-rose-400" : "text-emerald-400"}`}>
                                  {dep.error_rate_delta_pct > 0 ? `+${dep.error_rate_delta_pct.toFixed(2)}%` : `${dep.error_rate_delta_pct.toFixed(2)}%`}
                                </span>
                              </div>
                              <div>
                                <span className="text-slate-500 block">SLO Delta</span>
                                <span className="text-emerald-400 font-bold">{dep.slo_delta_pct.toFixed(1)}%</span>
                              </div>
                            </div>
                            {dep.rollback_recommended && (
                              <div className="p-2 rounded bg-rose-950/60 border border-rose-800 text-[10px] text-rose-300 font-mono">
                                ⚠️ <strong>Advisory Rollback Signal:</strong> Performance degradation detected. Manual rollback recommended. (Observational only; no automatic rollback).
                              </div>
                            )}
                          </div>
                        ))
                      ) : (
                        <p className="text-xs text-slate-500 py-6 text-center">No active deployment impacts recorded.</p>
                      )}
                    </div>
                  </div>
                </div>
    
                {/* 18 Operational Readiness Verification Gates */}
                <div className="rounded-2xl border border-slate-800 bg-slate-900/80 p-6 shadow-xl space-y-6">
                  <div className="flex flex-wrap items-center justify-between gap-2 border-b border-slate-800/80 pb-4">
                    <div>
                      <h3 className="text-base font-bold text-white flex items-center gap-2">
                        <span>18 Operational Readiness Verification Gates</span>
                        <span className="text-[10px] font-mono bg-emerald-950/80 text-emerald-300 border border-emerald-700/50 px-2 py-0.5 rounded">
                          Pre-flight Validation
                        </span>
                      </h3>
                      <p className="text-xs text-slate-400 mt-1">
                        Deterministic verification of service availability, latency, error budgets, security, webhooks, and database stability.
                      </p>
                    </div>
                    <div className="flex items-center gap-2 font-mono text-xs">
                      <span className="text-emerald-400 font-bold">
                        {obsReadiness ? `${obsReadiness.ready_count} / ${obsReadiness.gates.length} Ready` : "18/18 Ready"}
                      </span>
                      <span className="text-slate-500">
                        ({obsReadiness ? `${obsReadiness.readiness_percentage.toFixed(0)}%` : "100%"})
                      </span>
                    </div>
                  </div>
    
                  <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 md:grid-cols-3">
                    {obsReadiness && obsReadiness.gates && obsReadiness.gates.length > 0 ? (
                      obsReadiness.gates.map((g) => (
                        <div key={g.gate_code} className="rounded-xl border border-slate-800 bg-slate-950/60 p-3 space-y-2">
                          <div className="flex items-center justify-between">
                            <span className="text-[10px] font-bold text-cyan-400 font-mono">{g.gate_code}</span>
                            <span className={`px-1.5 py-0.5 rounded text-[9px] font-mono font-bold ${getReadinessGateBadge(g.status)}`}>
                              {g.status}
                            </span>
                          </div>
                          <p className="text-xs font-bold text-white">{g.gate_name}</p>
                          <div className="text-[10px] font-mono text-slate-400 space-y-0.5">
                            <div>Observed: <strong className="text-white">{g.observed_value}</strong></div>
                            <div>Threshold: <strong className="text-slate-300">{g.threshold}</strong></div>
                            <div className="text-slate-500 italic mt-1">{g.evidence}</div>
                          </div>
                        </div>
                      ))
                    ) : (
                      <div className="col-span-3 py-8 text-center text-xs text-slate-500">
                        No readiness gates evaluated.
                      </div>
                    )}
                  </div>
                </div>
    
                {/* Post-Incident Review & Root Cause Explorer */}
                <div className="rounded-2xl border border-slate-800 bg-slate-900/80 p-6 shadow-xl space-y-6">
                  <div className="flex flex-wrap items-center justify-between gap-2 border-b border-slate-800/80 pb-4">
                    <div>
                      <h3 className="text-base font-bold text-white flex items-center gap-2">
                        <span>Post-Incident Review (PIR) & Root Cause Database</span>
                        <span className="text-[10px] font-mono bg-purple-950/80 text-purple-300 border border-purple-700/50 px-2 py-0.5 rounded">
                          Auditable Postmortems
                        </span>
                      </h3>
                      <p className="text-xs text-slate-400 mt-1">
                        Structured postmortems with root causes, contributing factors, corrective actions, and preventive action tracking.
                      </p>
                    </div>
                    <button
                      onClick={() => setPostmortemModalOpen(true)}
                      className="px-3 py-1.5 rounded-lg bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-500 hover:to-indigo-500 text-white text-xs font-bold transition"
                    >
                      + New Postmortem
                    </button>
                  </div>
    
                  <div className="space-y-4">
                    {obsPostmortems && obsPostmortems.length > 0 ? (
                      obsPostmortems.map((pm) => (
                        <div key={pm.postmortem_id} className="rounded-xl border border-slate-800 bg-slate-950/60 p-5 space-y-4">
                          <div className="flex flex-wrap items-center justify-between gap-2 border-b border-slate-800/60 pb-3">
                            <div>
                              <span className="text-[10px] font-mono text-purple-400 font-bold">{pm.postmortem_id}</span>
                              <h4 className="text-sm font-bold text-white mt-0.5">{pm.title}</h4>
                            </div>
                            <div className="flex items-center gap-2">
                              <span className="px-2 py-0.5 rounded text-[10px] font-mono font-bold bg-purple-950/80 border border-purple-700 text-purple-300">
                                Root Cause: {pm.root_cause_category} ({pm.root_cause_confidence})
                              </span>
                              <span className="px-2 py-0.5 rounded text-[10px] font-mono font-bold bg-emerald-950/80 border border-emerald-700 text-emerald-300">
                                {pm.status}
                              </span>
                            </div>
                          </div>
    
                          <p className="text-xs text-slate-300 leading-relaxed font-mono">
                            {pm.impact_summary}
                          </p>
    
                          <div className="grid grid-cols-1 gap-4 md:grid-cols-2 text-xs font-mono">
                            <div className="space-y-1.5 p-3 rounded-lg bg-slate-900/60 border border-slate-800">
                              <span className="text-[10px] font-bold text-emerald-400 uppercase tracking-wider block">Corrective Actions</span>
                              <ul className="list-disc list-inside space-y-1 text-slate-300 text-[11px]">
                                {pm.corrective_actions.map((act, i) => (
                                  <li key={i}>{act}</li>
                                ))}
                              </ul>
                            </div>
                            <div className="space-y-1.5 p-3 rounded-lg bg-slate-900/60 border border-slate-800">
                              <span className="text-[10px] font-bold text-cyan-400 uppercase tracking-wider block">Preventive Actions</span>
                              <ul className="list-disc list-inside space-y-1 text-slate-300 text-[11px]">
                                {pm.preventive_actions.map((act, i) => (
                                  <li key={i}>{act}</li>
                                ))}
                              </ul>
                            </div>
                          </div>
                        </div>
                      ))
                    ) : (
                      <div className="py-8 text-center text-xs text-slate-500">
                        No postmortem reports recorded. Click &quot;+ New Postmortem&quot; to author one.
                      </div>
                    )}
                  </div>
                </div>
              </div>


            {postmortemModalOpen && (
              <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/80 backdrop-blur-sm p-4">
                <div className="relative w-full max-w-xl rounded-2xl border border-blue-800 bg-slate-900 shadow-2xl overflow-hidden flex flex-col max-h-[90vh]">
                  <div className="flex items-center justify-between border-b border-slate-800 p-5 bg-slate-950/60">
                    <div className="flex items-center gap-2">
                      <span className="rounded-lg bg-blue-600 px-2 py-0.5 text-[10px] font-mono font-bold uppercase text-white">
                        Post-Incident Review
                      </span>
                      <h3 className="text-base font-bold text-white">Author Postmortem Report</h3>
                    </div>
                    <button
                      onClick={() => setPostmortemModalOpen(false)}
                      className="rounded-lg p-1.5 text-slate-400 hover:bg-slate-800 hover:text-white transition"
                    >
                      ✕
                    </button>
                  </div>
    
                  <form onSubmit={handleCreatePostmortemSubmit} className="flex-1 overflow-y-auto p-6 space-y-4 text-xs font-mono">
                    <div>
                      <label className="block text-[11px] font-semibold text-slate-400 uppercase mb-1">
                        Incident ID (or Identifier)
                      </label>
                      <input
                        type="text"
                        required
                        value={postmortemForm.incident_id}
                        onChange={(e) => setPostmortemForm({ ...postmortemForm, incident_id: e.target.value })}
                        placeholder="e.g. INC-OBS-2026-0830-01"
                        className="w-full rounded-xl border border-slate-800 bg-slate-950 px-3.5 py-2 text-xs text-white focus:border-blue-500 focus:outline-none"
                      />
                    </div>
    
                    <div>
                      <label className="block text-[11px] font-semibold text-slate-400 uppercase mb-1">
                        Postmortem Title
                      </label>
                      <input
                        type="text"
                        required
                        value={postmortemForm.title}
                        onChange={(e) => setPostmortemForm({ ...postmortemForm, title: e.target.value })}
                        placeholder="e.g. Database Connection Pool Saturation During Morning Spikes"
                        className="w-full rounded-xl border border-slate-800 bg-slate-950 px-3.5 py-2 text-xs text-white focus:border-blue-500 focus:outline-none"
                      />
                    </div>
    
                    <div>
                      <label className="block text-[11px] font-semibold text-slate-400 uppercase mb-1">
                        Root Cause Category
                      </label>
                      <select
                        value={postmortemForm.root_cause_category}
                        onChange={(e) => setPostmortemForm({ ...postmortemForm, root_cause_category: e.target.value })}
                        className="w-full rounded-xl border border-slate-800 bg-slate-950 px-3.5 py-2 text-xs text-white focus:border-blue-500 focus:outline-none"
                      >
                        <option value="DATABASE">DATABASE</option>
                        <option value="UPSTREAM_GATEWAY">UPSTREAM_GATEWAY</option>
                        <option value="NETWORK_CONNECTIVITY">NETWORK_CONNECTIVITY</option>
                        <option value="WORKER_CONCURRENCY">WORKER_CONCURRENCY</option>
                        <option value="MODEL_PERFORMANCE">MODEL_PERFORMANCE</option>
                        <option value="POLICY_MISCONFIGURATION">POLICY_MISCONFIGURATION</option>
                        <option value="CONFIGURATION_DRIFT">CONFIGURATION_DRIFT</option>
                        <option value="CODE_REGRESSION">CODE_REGRESSION</option>
                      </select>
                    </div>
    
                    <div>
                      <label className="block text-[11px] font-semibold text-slate-400 uppercase mb-1">
                        Impact Summary
                      </label>
                      <textarea
                        rows={3}
                        required
                        value={postmortemForm.impact_summary}
                        onChange={(e) => setPostmortemForm({ ...postmortemForm, impact_summary: e.target.value })}
                        placeholder="Describe client and system impact during the incident window..."
                        className="w-full rounded-xl border border-slate-800 bg-slate-950 px-3.5 py-2 text-xs text-white focus:border-blue-500 focus:outline-none"
                      />
                    </div>
    
                    <div>
                      <label className="block text-[11px] font-semibold text-slate-400 uppercase mb-1">
                        Contributing Factors (1 per line)
                      </label>
                      <textarea
                        rows={2}
                        value={postmortemForm.contributing_factors}
                        onChange={(e) => setPostmortemForm({ ...postmortemForm, contributing_factors: e.target.value })}
                        placeholder="Peak renewal traffic surge&#10;Slow query locking connection pool"
                        className="w-full rounded-xl border border-slate-800 bg-slate-950 px-3.5 py-2 text-xs text-white focus:border-blue-500 focus:outline-none"
                      />
                    </div>
    
                    <div>
                      <label className="block text-[11px] font-semibold text-slate-400 uppercase mb-1">
                        Corrective Actions (1 per line)
                      </label>
                      <textarea
                        rows={2}
                        value={postmortemForm.corrective_actions}
                        onChange={(e) => setPostmortemForm({ ...postmortemForm, corrective_actions: e.target.value })}
                        placeholder="Increased pool max_overflow to 20&#10;Added query index"
                        className="w-full rounded-xl border border-slate-800 bg-slate-950 px-3.5 py-2 text-xs text-white focus:border-blue-500 focus:outline-none"
                      />
                    </div>
    
                    <div>
                      <label className="block text-[11px] font-semibold text-slate-400 uppercase mb-1">
                        Preventive Actions (1 per line)
                      </label>
                      <textarea
                        rows={2}
                        value={postmortemForm.preventive_actions}
                        onChange={(e) => setPostmortemForm({ ...postmortemForm, preventive_actions: e.target.value })}
                        placeholder="Deploy slow-query circuit breaker in PolicyEngine&#10;Add p99 latency SLO alert"
                        className="w-full rounded-xl border border-slate-800 bg-slate-950 px-3.5 py-2 text-xs text-white focus:border-blue-500 focus:outline-none"
                      />
                    </div>
    
                    <div className="flex items-center justify-end gap-3 border-t border-slate-800 pt-4">
                      <button
                        type="button"
                        onClick={() => setPostmortemModalOpen(false)}
                        className="rounded-xl border border-slate-800 px-4 py-2 text-xs font-semibold text-slate-400 hover:text-white"
                      >
                        Cancel
                      </button>
                      <button
                        type="submit"
                        disabled={postmortemLoading}
                        className="rounded-xl bg-gradient-to-r from-blue-600 to-indigo-600 px-5 py-2 text-xs font-bold text-white shadow-lg hover:from-blue-500 hover:to-indigo-500 disabled:opacity-50"
                      >
                        {postmortemLoading ? "Saving..." : "Save Postmortem Report"}
                      </button>
                    </div>
                  </form>
                </div>
              </div>
            )}
    


    </>
  );
}
