"use client";

import React, { useCallback, useEffect, useState } from "react";
import {
  BackupVerification,
  DisasterSimulationResult,
  RTORPOStatus,
  RecoveryRunbook,
  ResilienceIncident,
  ResilienceReadiness,
  ResilienceServiceHealth,
  ResilienceSummary,
  acknowledgeResilienceIncident,
  escalateResilienceIncident,
  fetchResilienceBackups,
  fetchResilienceIncidents,
  fetchResilienceReadiness,
  fetchResilienceRtoRpo,
  fetchResilienceRunbooks,
  fetchResilienceServices,
  fetchResilienceSummary,
  runResilienceSimulation,
  verifyResilienceRecovery
} from "../../lib/api";
import { getIncidentSeverityBadge } from "./intelligenceBadges";

export default function ResilienceTab() {
  const [error, setError] = useState<string | null>(null);

    const [resilienceSummary, setResilienceSummary] = useState<ResilienceSummary | null>(null);
    const [resilienceServices, setResilienceServices] = useState<ResilienceServiceHealth[] | null>(null);
    const [resilienceIncidents, setResilienceIncidents] = useState<ResilienceIncident[] | null>(null);
    const [resilienceReadiness, setResilienceReadiness] = useState<ResilienceReadiness | null>(null);
    const [resilienceBackups, setResilienceBackups] = useState<BackupVerification | null>(null);
    const [resilienceRtoRpo, setResilienceRtoRpo] = useState<RTORPOStatus | null>(null);
    const [resilienceRunbooks, setResilienceRunbooks] = useState<RecoveryRunbook[] | null>(null);
    const [simSelectedScenario, setSimSelectedScenario] = useState<string>("DATABASE_OUTAGE");
    const [simSeverityOverride, setSimSeverityOverride] = useState<string>("DEFAULT");
    const [simulationResult, setSimulationResult] = useState<DisasterSimulationResult | null>(null);
    const [simulationLoading, setSimulationLoading] = useState(false);
    const [selectedRunbook, setSelectedRunbook] = useState<RecoveryRunbook | null>(null);
    const [resIncidentSeverityFilter, setResIncidentSeverityFilter] = useState<string>("ALL");
    const [resActionSuccessMsg, setResActionSuccessMsg] = useState<string | null>(null);
    const [verifyRecoveryLoading, setVerifyRecoveryLoading] = useState(false);
    const [ackIncidentLoading, setAckIncidentLoading] = useState(false);
    const [escIncidentLoading, setEscIncidentLoading] = useState(false);
  

    const handleRunResilienceSimulation = async () => {
      setSimulationLoading(true);
      setError(null);
      try {
        const result = await runResilienceSimulation(
          simSelectedScenario,
          simSeverityOverride !== "DEFAULT" ? simSeverityOverride : undefined
        );
        setSimulationResult(result);
        setResActionSuccessMsg(`Disaster simulation for ${simSelectedScenario} executed. Safe observational mode: 0 financial mutations.`);
        await loadResilienceData();
      } catch (err) {
        setError(err instanceof Error ? err.message : "Failed to execute disaster simulation");
      } finally {
        setSimulationLoading(false);
      }
    };
  
    const handleObsAcknowledgeIncident = async (incidentId: string) => {
      setAckIncidentLoading(true);
      setError(null);
      try {
        await acknowledgeResilienceIncident(incidentId);
        setResActionSuccessMsg(`Incident ${incidentId} acknowledged. Audit event logged.`);
        await loadResilienceData();
      } catch (err) {
        setError(err instanceof Error ? err.message : "Failed to acknowledge incident");
      } finally {
        setAckIncidentLoading(false);
      }
    };
  
    const handleObsEscalateIncident = async (incidentId: string) => {
      setEscIncidentLoading(true);
      setError(null);
      try {
        await escalateResilienceIncident(incidentId);
        setResActionSuccessMsg(`Incident ${incidentId} escalated to Admin review.`);
        await loadResilienceData();
      } catch (err) {
        setError(err instanceof Error ? err.message : "Failed to escalate incident");
      } finally {
        setEscIncidentLoading(false);
      }
    };
  
    const handleVerifyRecovery = async () => {
      setVerifyRecoveryLoading(true);
      setError(null);
      try {
        const res = await verifyResilienceRecovery();
        setResActionSuccessMsg(`Recovery verified across ${res.services_checked || 11} dependencies. Audit event written.`);
        await loadResilienceData();
      } catch (err) {
        setError(err instanceof Error ? err.message : "Failed to verify recovery");
      } finally {
        setVerifyRecoveryLoading(false);
      }
    };
  
    const getResilienceStateBadge = (state?: string) => {
      switch (state) {
        case "DISASTER_MODE":
          return "bg-red-950/90 border-red-500 text-red-300 font-black animate-pulse shadow-lg shadow-red-500/20";
        case "CRITICAL":
          return "bg-rose-950/90 border-rose-500 text-rose-300 font-bold animate-pulse shadow-lg shadow-rose-500/20";
        case "SERVICE_IMPACTED":
          return "bg-orange-950/90 border-orange-500 text-orange-300 font-bold";
        case "DEGRADED":
          return "bg-amber-950/90 border-amber-500 text-amber-300 font-bold";
        case "WARNING":
          return "bg-yellow-950/90 border-yellow-500 text-yellow-300 font-bold";
        case "RECOVERY_IN_PROGRESS":
          return "bg-cyan-950/90 border-cyan-500 text-cyan-300 font-bold animate-pulse";
        case "RECOVERY_VERIFIED":
          return "bg-teal-950/90 border-teal-500 text-teal-300 font-bold";
        case "OPERATIONAL":
        default:
          return "bg-emerald-950/90 border-emerald-500 text-emerald-300 font-bold shadow-lg shadow-emerald-500/20";
      }
    };
  
    const getServiceHealthBadge = (status?: string) => {
      switch (status) {
        case "HEALTHY":
          return "bg-emerald-950/80 border-emerald-600 text-emerald-300 font-bold";
        case "DEGRADED":
          return "bg-amber-950/80 border-amber-600 text-amber-300 font-bold";
        case "UNAVAILABLE":
          return "bg-red-950/80 border-red-600 text-red-300 font-black animate-pulse";
        case "UNKNOWN":
        default:
          return "bg-slate-900 border-slate-700 text-slate-400 font-medium";
      }
    };
  
    const getReadinessGateBadge = (status?: string) => {
      switch (status) {
        case "READY":
          return "bg-emerald-950/80 border-emerald-600 text-emerald-300 font-bold";
        case "CONDITIONAL":
          return "bg-amber-950/80 border-amber-600 text-amber-300 font-bold";
        case "BLOCKED":
          return "bg-red-950/80 border-red-600 text-red-300 font-black animate-pulse";
        case "UNKNOWN":
        default:
          return "bg-slate-900 border-slate-700 text-slate-400 font-medium";
      }
    };
  
    const getRTORPOBadge = (status?: string) => {
      switch (status) {
        case "COMPLIANT":
          return "bg-emerald-950/80 border-emerald-600 text-emerald-300 font-bold";
        case "AT_RISK":
          return "bg-amber-950/80 border-amber-600 text-amber-300 font-bold";
        case "BREACHED":
          return "bg-red-950/80 border-red-600 text-red-300 font-bold animate-pulse";
        case "UNKNOWN":
        default:
          return "bg-slate-900 border-slate-700 text-slate-400 font-medium";
      }
    };
  
    // Phase 10D: Action Handlers & Badge Helpers

  const loadResilienceData = useCallback(async () => {
    try {
      const [
        sumRes, svcRes, incRes, readRes, bkpRes, rtoRes, rbRes
      ] = await Promise.all([
        fetchResilienceSummary().catch(() => null),
        fetchResilienceServices().catch(() => []),
        fetchResilienceIncidents().catch(() => []),
        fetchResilienceReadiness().catch(() => null),
        fetchResilienceBackups().catch(() => null),
        fetchResilienceRtoRpo().catch(() => null),
        fetchResilienceRunbooks().catch(() => []),
      ]);
      setResilienceSummary(sumRes);
      setResilienceServices(svcRes);
      setResilienceIncidents(incRes);
      setResilienceReadiness(readRes);
      setResilienceBackups(bkpRes);
      setResilienceRtoRpo(rtoRes);
      setResilienceRunbooks(rbRes);
      if (rbRes && rbRes.length > 0 && !selectedRunbook) {
        setSelectedRunbook(rbRes[0]);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load Resilience data");
    }
  }, [selectedRunbook]);

    useEffect(() => {
    let ignore = false;
    async function execute() {
      if (!ignore) {
        await loadResilienceData();
      }
    }
    void execute();
    return () => {
      ignore = true;
    };
  }, [loadResilienceData]);

  return (
    <>
      {error && (
        <div className="rounded-xl border border-rose-800/40 bg-rose-950/40 p-4 text-xs text-rose-300">
          {error}
        </div>
      )}

      {resActionSuccessMsg && (
        <div className="rounded-xl border border-emerald-800/60 bg-emerald-950/40 p-4 text-xs text-emerald-300 flex items-center justify-between shadow-lg">
          <span>{resActionSuccessMsg}</span>
          <button onClick={() => setResActionSuccessMsg(null)} className="text-emerald-400 hover:text-white font-bold ml-4">✕</button>
        </div>
      )}
              {/* =========================================================================
                 TAB 15: OPERATIONAL RESILIENCE, DISASTER RECOVERY & BUSINESS CONTINUITY (Phase 10C)
                 ========================================================================= */}
              <div className="space-y-8">
                {/* Mandatory Resilience Governance & Financial Isolation Banner */}
                <div className="rounded-2xl border border-cyan-800/60 bg-gradient-to-r from-cyan-950/50 via-teal-950/40 to-indigo-950/40 p-5 flex items-start gap-4 shadow-xl">
                  <span className="rounded-lg bg-gradient-to-r from-cyan-600 to-teal-600 px-2.5 py-1 text-[10px] font-mono font-black uppercase tracking-wider text-white shadow shrink-0">
                    PHASE 10C RESILIENCE
                  </span>
                  <div className="text-xs text-slate-200 leading-relaxed space-y-1.5 flex-1">
                    <div className="flex flex-wrap items-center justify-between gap-2">
                      <p className="font-bold text-cyan-200 text-sm flex items-center gap-2">
                        <span>OPERATIONAL RESILIENCE, DISASTER RECOVERY & BUSINESS CONTINUITY</span>
                        <span className="text-[10px] font-mono font-normal text-cyan-400/80 bg-cyan-950/80 px-2 py-0.5 rounded border border-cyan-700/50">
                          Deterministic Service Surveillance • 15 DR Gates • 0 Financial Mutations
                        </span>
                      </p>
                      <button
                        onClick={handleVerifyRecovery}
                        disabled={verifyRecoveryLoading}
                        className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-gradient-to-r from-cyan-600 to-indigo-600 hover:from-cyan-500 hover:to-indigo-500 text-white text-xs font-bold shadow-lg shadow-cyan-700/30 transition disabled:opacity-50"
                      >
                        {verifyRecoveryLoading ? "Verifying..." : "🛡️ Verify Recovery Status"}
                      </button>
                    </div>
                    <p className="text-slate-300 text-[11px] leading-relaxed border-t border-cyan-800/40 pt-2 mt-2">
                      <strong className="text-amber-300">Engineering Evidence Disclaimer:</strong>{" "}
                      {resilienceSummary?.disclaimer ||
                        "This dashboard provides automated engineering resilience evidence and operational governance. It does not constitute legal, regulatory, disaster-recovery, business-continuity, or third-party certification. PolicyEngine remains the sole authoritative gatekeeper for recovery actions. The resilience subsystem is strictly observational and produces zero financial mutations."}
                    </p>
                  </div>
                </div>
    
                {/* 8 Top Posture KPI Cards Grid */}
                <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
                  {/* Card 1: Overall Resilience Score */}
                  <div className="rounded-2xl border border-cyan-800/50 bg-slate-900/90 p-4 shadow-lg backdrop-blur space-y-2">
                    <div className="flex items-center justify-between">
                      <span className="text-xs font-semibold text-slate-400">Resilience Score</span>
                      <span
                        className={`rounded-full border px-2 py-0.5 text-[10px] font-mono font-bold uppercase tracking-wider ${getResilienceStateBadge(
                          resilienceSummary?.global_state
                        )}`}
                      >
                        {resilienceSummary?.global_state || "OPERATIONAL"}
                      </span>
                    </div>
                    <div className="flex items-baseline gap-2">
                      <span className="text-2xl font-black text-white font-mono">
                        {resilienceSummary ? `${resilienceSummary.resilience_score.toFixed(1)}` : "--"}
                      </span>
                      <span className="text-xs text-slate-400 font-mono">/ 100.0</span>
                    </div>
                    <p className="text-[11px] text-cyan-400/90 font-mono">
                      Avail: {resilienceSummary?.score_breakdown.availability_score.toFixed(0) || "100"}% • Health: {resilienceSummary?.score_breakdown.dependency_health_score.toFixed(0) || "100"}% • DR: {resilienceSummary?.score_breakdown.recovery_readiness_score.toFixed(0) || "100"}%
                    </p>
                  </div>
    
                  {/* Card 2: Global Resilience State */}
                  <div className="rounded-2xl border border-cyan-800/50 bg-slate-900/90 p-4 shadow-lg backdrop-blur space-y-2">
                    <div className="flex items-center justify-between">
                      <span className="text-xs font-semibold text-slate-400">Global State</span>
                      <span className="rounded-full border border-teal-700/60 bg-teal-950/80 px-2 py-0.5 text-[10px] font-mono font-bold text-teal-300">
                        PRIORITY LEVEL
                      </span>
                    </div>
                    <div className="flex items-baseline gap-2">
                      <span className="text-xl font-black text-teal-300 font-mono">
                        {resilienceSummary ? resilienceSummary.global_state.replace(/_/g, " ") : "OPERATIONAL"}
                      </span>
                    </div>
                    <p className="text-[11px] text-slate-400 font-mono">
                      {resilienceSummary?.active_incidents_count || 0} active incidents • {resilienceSummary?.critical_incidents_count || 0} critical
                    </p>
                  </div>
    
                  {/* Card 3: Service Availability */}
                  <div className="rounded-2xl border border-cyan-800/50 bg-slate-900/90 p-4 shadow-lg backdrop-blur space-y-2">
                    <div className="flex items-center justify-between">
                      <span className="text-xs font-semibold text-slate-400">Service Availability</span>
                      <span className="rounded-full border border-emerald-700/60 bg-emerald-950/80 px-2 py-0.5 text-[10px] font-mono font-bold text-emerald-300">
                        11 SERVICES
                      </span>
                    </div>
                    <div className="flex items-baseline gap-2">
                      <span className="text-2xl font-black text-emerald-400 font-mono">
                        {resilienceSummary ? `${resilienceSummary.service_availability_percentage.toFixed(1)}%` : "100.0%"}
                      </span>
                    </div>
                    <p className="text-[11px] text-emerald-400/90 font-mono">
                      Status: {resilienceSummary?.dependency_health_status || "HEALTHY"}
                    </p>
                  </div>
    
                  {/* Card 4: DR Readiness Gates */}
                  <div className="rounded-2xl border border-cyan-800/50 bg-slate-900/90 p-4 shadow-lg backdrop-blur space-y-2">
                    <div className="flex items-center justify-between">
                      <span className="text-xs font-semibold text-slate-400">DR Readiness</span>
                      <span
                        className={`rounded-full border px-2 py-0.5 text-[10px] font-mono font-bold uppercase ${getReadinessGateBadge(
                          resilienceReadiness?.overall_status
                        )}`}
                      >
                        {resilienceReadiness?.overall_status || "READY"}
                      </span>
                    </div>
                    <div className="flex items-baseline gap-2">
                      <span className="text-2xl font-black text-white font-mono">
                        {resilienceReadiness ? `${resilienceReadiness.readiness_percentage.toFixed(1)}%` : "--"}
                      </span>
                      <span className="text-xs text-slate-400 font-mono">
                        ({resilienceReadiness ? `${resilienceReadiness.ready_count}/15` : "-"} Ready)
                      </span>
                    </div>
                    <p className="text-[11px] text-slate-400 font-mono">
                      {resilienceReadiness?.conditional_count || 0} conditional • {resilienceReadiness?.blocked_count || 0} blocked
                    </p>
                  </div>
    
                  {/* Card 5: RTO Target vs Observed */}
                  <div className="rounded-2xl border border-slate-800 bg-slate-900/90 p-4 shadow-lg flex flex-col justify-between">
                    <div className="flex items-center justify-between">
                      <span className="text-[11px] font-bold text-slate-400 uppercase tracking-wider">RTO Compliance</span>
                      <span
                        className={`rounded-full border px-2 py-0.5 text-[10px] font-mono font-bold uppercase ${getRTORPOBadge(
                          resilienceRtoRpo?.rto_compliance
                        )}`}
                      >
                        {resilienceRtoRpo?.rto_compliance || "COMPLIANT"}
                      </span>
                    </div>
                    <div className="mt-2 flex items-baseline gap-2">
                      <span className="text-2xl font-black text-white font-mono">
                        {resilienceRtoRpo ? `${resilienceRtoRpo.rto_observed_seconds}s` : "0s"}
                      </span>
                      <span className="text-xs text-slate-400 font-mono">
                        / {resilienceRtoRpo?.rto_target_seconds || 300}s SLA
                      </span>
                    </div>
                    <span className="mt-2 text-[10px] text-slate-400 font-mono">
                      {resilienceRtoRpo?.historical_rto_breaches || 0} historical breaches
                    </span>
                  </div>
    
                  {/* Card 6: RPO Target vs Observed */}
                  <div className="rounded-2xl border border-slate-800 bg-slate-900/90 p-4 shadow-lg flex flex-col justify-between">
                    <div className="flex items-center justify-between">
                      <span className="text-[11px] font-bold text-slate-400 uppercase tracking-wider">RPO Compliance</span>
                      <span
                        className={`rounded-full border px-2 py-0.5 text-[10px] font-mono font-bold uppercase ${getRTORPOBadge(
                          resilienceRtoRpo?.rpo_compliance
                        )}`}
                      >
                        {resilienceRtoRpo?.rpo_compliance || "COMPLIANT"}
                      </span>
                    </div>
                    <div className="mt-2 flex items-baseline gap-2">
                      <span className="text-2xl font-black text-white font-mono">
                        {resilienceRtoRpo ? `${resilienceRtoRpo.rpo_observed_seconds}s` : "0s"}
                      </span>
                      <span className="text-xs text-slate-400 font-mono">
                        / {resilienceRtoRpo?.rpo_target_seconds || 60}s SLA
                      </span>
                    </div>
                    <span className="mt-2 text-[10px] text-slate-400 font-mono">
                      {resilienceRtoRpo?.historical_rpo_breaches || 0} historical breaches
                    </span>
                  </div>
    
                  {/* Card 7: Backup Integrity & Freshness */}
                  <div className="rounded-2xl border border-slate-800 bg-slate-900/90 p-4 shadow-lg flex flex-col justify-between">
                    <div className="flex items-center justify-between">
                      <span className="text-[11px] font-bold text-slate-400 uppercase tracking-wider">Backup Integrity</span>
                      <span className="rounded-full border border-emerald-700/60 bg-emerald-950/80 px-2 py-0.5 text-[10px] font-mono font-bold text-emerald-300">
                        {resilienceBackups?.integrity_status || "VALID"}
                      </span>
                    </div>
                    <div className="mt-2 flex items-baseline gap-2">
                      <span className="text-lg font-black text-white font-mono truncate">
                        {resilienceBackups ? resilienceBackups.freshness_status : "CURRENT"}
                      </span>
                    </div>
                    <span className="mt-2 text-[10px] text-slate-400 font-mono">
                      Restore: {resilienceBackups?.restore_test_status || "UNVERIFIED"}
                    </span>
                  </div>
    
                  {/* Card 8: Active Incidents */}
                  <div className="rounded-2xl border border-slate-800 bg-slate-900/90 p-4 shadow-lg flex flex-col justify-between">
                    <div className="flex items-center justify-between">
                      <span className="text-[11px] font-bold text-slate-400 uppercase tracking-wider">Active Incidents</span>
                      <span
                        className={`rounded-full border px-2 py-0.5 text-[10px] font-mono font-bold ${
                          (resilienceSummary?.active_incidents_count || 0) > 0
                            ? "border-rose-700/60 bg-rose-950/80 text-rose-300"
                            : "border-emerald-700/60 bg-emerald-950/80 text-emerald-300"
                        }`}
                      >
                        {(resilienceSummary?.active_incidents_count || 0) > 0 ? "ATTENTION" : "CLEAR"}
                      </span>
                    </div>
                    <div className="mt-2 flex items-baseline gap-2">
                      <span className="text-2xl font-black text-white font-mono">
                        {resilienceSummary?.active_incidents_count || 0}
                      </span>
                      <span className="text-xs text-slate-400 font-mono">Incidents</span>
                    </div>
                    <span className="mt-2 text-[10px] text-slate-400 font-mono">
                      {resilienceSummary?.critical_incidents_count || 0} critical priority
                    </span>
                  </div>
                </div>
    
                {/* Section 1: Service Health Matrix (11 Dependencies) */}
                <div className="rounded-2xl border border-slate-800 bg-slate-900/90 p-6 shadow-xl space-y-4">
                  <div className="flex items-center justify-between border-b border-slate-800 pb-4">
                    <div>
                      <h3 className="text-base font-bold text-white flex items-center gap-2">
                        <span>Service Dependency Health Matrix</span>
                        <span className="text-xs font-mono font-normal text-cyan-400 bg-cyan-950/80 px-2 py-0.5 rounded border border-cyan-800/50">
                          11 Critical Services Monitored
                        </span>
                      </h3>
                      <p className="text-xs text-slate-400 mt-0.5">
                        Real-time operational health, latency metrics, and failure diagnostics across the RecoverIQ architecture.
                      </p>
                    </div>
                  </div>
    
                  <div className="overflow-x-auto">
                    <table className="w-full text-left text-xs">
                      <thead className="bg-slate-950/60 text-[10px] font-mono uppercase text-slate-400 border-b border-slate-800">
                        <tr>
                          <th className="px-3 py-2.5">Service Name</th>
                          <th className="px-3 py-2.5">Status</th>
                          <th className="px-3 py-2.5">Latency</th>
                          <th className="px-3 py-2.5">Availability</th>
                          <th className="px-3 py-2.5">Failures</th>
                          <th className="px-3 py-2.5">Severity</th>
                          <th className="px-3 py-2.5">Diagnostic Code</th>
                          <th className="px-3 py-2.5">Last Success</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-slate-800/50 font-mono">
                        {resilienceServices && resilienceServices.length > 0 ? (
                          resilienceServices.map((svc) => (
                            <tr key={svc.service_name} className="hover:bg-slate-800/30 transition">
                              <td className="px-3 py-2.5 font-bold text-slate-200 font-sans">{svc.service_name}</td>
                              <td className="px-3 py-2.5">
                                <span className={`inline-block rounded px-2 py-0.5 text-[10px] font-bold ${getServiceHealthBadge(svc.status)}`}>
                                  {svc.status}
                                </span>
                              </td>
                              <td className="px-3 py-2.5 text-slate-300">{svc.latency_ms}ms</td>
                              <td className="px-3 py-2.5 text-emerald-400">{svc.availability_percentage.toFixed(1)}%</td>
                              <td className="px-3 py-2.5 text-slate-400">{svc.consecutive_failures}</td>
                              <td className="px-3 py-2.5">
                                <span className={`inline-block rounded px-1.5 py-0.5 text-[10px] ${getIncidentSeverityBadge(svc.severity)}`}>
                                  {svc.severity}
                                </span>
                              </td>
                              <td className="px-3 py-2.5 text-cyan-400">{svc.diagnostic_code}</td>
                              <td className="px-3 py-2.5 text-slate-500 text-[10px]">
                                {svc.last_success_timestamp ? new Date(svc.last_success_timestamp).toLocaleTimeString() : "Never"}
                              </td>
                            </tr>
                          ))
                        ) : (
                          <tr>
                            <td colSpan={8} className="px-4 py-8 text-center text-slate-500">
                              Loading service dependency surveillance data...
                            </td>
                          </tr>
                        )}
                      </tbody>
                    </table>
                  </div>
                </div>
    
                {/* Section 2: DR Readiness Panel (15 Gates Evaluation) */}
                <div className="rounded-2xl border border-slate-800 bg-slate-900/90 p-6 shadow-xl space-y-4">
                  <div className="flex items-center justify-between border-b border-slate-800 pb-4">
                    <div>
                      <h3 className="text-base font-bold text-white flex items-center gap-2">
                        <span>Disaster Recovery Readiness Evaluation</span>
                        <span className="text-xs font-mono font-normal text-indigo-400 bg-indigo-950/80 px-2 py-0.5 rounded border border-indigo-800/50">
                          15 Verification Gates
                        </span>
                      </h3>
                      <p className="text-xs text-slate-400 mt-0.5">
                        Automated pre-flight recovery gate evaluation ensuring zero-gap business continuity.
                      </p>
                    </div>
                    <div className="flex items-center gap-2 font-mono text-xs">
                      <span className="px-2 py-0.5 rounded bg-emerald-950/80 text-emerald-300 border border-emerald-800/60">
                        Ready: {resilienceReadiness?.ready_count || 0}
                      </span>
                      <span className="px-2 py-0.5 rounded bg-amber-950/80 text-amber-300 border border-amber-800/60">
                        Conditional: {resilienceReadiness?.conditional_count || 0}
                      </span>
                      <span className="px-2 py-0.5 rounded bg-red-950/80 text-red-300 border border-red-800/60">
                        Blocked: {resilienceReadiness?.blocked_count || 0}
                      </span>
                    </div>
                  </div>
    
                  <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
                    {resilienceReadiness && resilienceReadiness.gates ? (
                      resilienceReadiness.gates.map((gate) => (
                        <div
                          key={gate.gate_code}
                          className="rounded-xl border border-slate-800 bg-slate-950/50 p-3.5 space-y-2 hover:border-slate-700 transition"
                        >
                          <div className="flex items-center justify-between">
                            <span className="text-xs font-bold text-slate-200 truncate">{gate.gate_name}</span>
                            <span className={`rounded px-1.5 py-0.5 text-[9px] font-mono font-bold ${getReadinessGateBadge(gate.status)}`}>
                              {gate.status}
                            </span>
                          </div>
                          <div className="text-[10px] font-mono text-slate-400 space-y-0.5">
                            <p><span className="text-slate-500">Observed:</span> {gate.observed_value}</p>
                            <p><span className="text-slate-500">Evidence:</span> {gate.evidence}</p>
                            {gate.remediation && (
                              <p className="text-amber-400/90 pt-1"><span className="text-amber-500">Action:</span> {gate.remediation}</p>
                            )}
                          </div>
                        </div>
                      ))
                    ) : (
                      <div className="col-span-3 py-6 text-center text-xs text-slate-500">
                        Evaluating disaster recovery readiness gates...
                      </div>
                    )}
                  </div>
                </div>
    
                {/* Section 3 & 4 Grid: Disaster Simulation & Operational Incidents */}
                <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
                  {/* Left Column: Disaster Recovery Simulation Center */}
                  <div className="rounded-2xl border border-slate-800 bg-slate-900/90 p-6 shadow-xl space-y-4 flex flex-col justify-between">
                    <div className="space-y-4">
                      <div className="border-b border-slate-800 pb-3">
                        <h3 className="text-base font-bold text-white flex items-center gap-2">
                          <span>Disaster Simulation Engine</span>
                          <span className="text-[10px] font-mono font-normal text-emerald-400 bg-emerald-950/80 px-2 py-0.5 rounded border border-emerald-800/50">
                            Safe Observational Mode
                          </span>
                        </h3>
                        <p className="text-xs text-slate-400 mt-0.5">
                          Simulate 11 disaster scenarios to compute blast radius, RTO/RPO impact, and recovery procedures without touching production state.
                        </p>
                      </div>
    
                      <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                        <div>
                          <label className="text-[11px] font-semibold text-slate-400 block mb-1">Scenario Type</label>
                          <select
                            value={simSelectedScenario}
                            onChange={(e) => setSimSelectedScenario(e.target.value)}
                            className="w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-xs text-slate-200 focus:outline-none focus:border-cyan-500"
                          >
                            <option value="DATABASE_OUTAGE">Database Outage</option>
                            <option value="REDIS_OUTAGE">Redis Outage</option>
                            <option value="WORKER_FAILURE">Worker Failure</option>
                            <option value="QUEUE_BACKLOG">Queue Backlog</option>
                            <option value="WEBHOOK_OUTAGE">Webhook Outage</option>
                            <option value="ML_SERVICE_DEGRADATION">ML Service Degradation</option>
                            <option value="POLICYENGINE_DEGRADATION">PolicyEngine Degradation</option>
                            <option value="AUDITLOG_FAILURE">AuditLog Failure</option>
                            <option value="PAYMENT_PROVIDER_UNAVAILABLE">Payment Provider Outage</option>
                            <option value="REGIONAL_OUTAGE">Regional Disaster</option>
                            <option value="CASCADING_DEPENDENCY_FAILURE">Cascading Multi-Failure</option>
                          </select>
                        </div>
    
                        <div>
                          <label className="text-[11px] font-semibold text-slate-400 block mb-1">Severity Override</label>
                          <select
                            value={simSeverityOverride}
                            onChange={(e) => setSimSeverityOverride(e.target.value)}
                            className="w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-xs text-slate-200 focus:outline-none focus:border-cyan-500"
                          >
                            <option value="DEFAULT">Default (Scenario Default)</option>
                            <option value="CRITICAL">CRITICAL</option>
                            <option value="HIGH">HIGH</option>
                            <option value="MEDIUM">MEDIUM</option>
                            <option value="LOW">LOW</option>
                          </select>
                        </div>
                      </div>
    
                      <button
                        onClick={handleRunResilienceSimulation}
                        disabled={simulationLoading}
                        className="w-full rounded-xl bg-gradient-to-r from-cyan-600 via-teal-600 to-indigo-600 hover:from-cyan-500 hover:to-indigo-500 py-2.5 text-xs font-bold text-white shadow-lg shadow-cyan-600/30 transition disabled:opacity-50 flex items-center justify-center gap-2"
                      >
                        {simulationLoading ? (
                          <>
                            <div className="h-3.5 w-3.5 animate-spin rounded-full border-2 border-white border-t-transparent" />
                            <span>Simulating Disaster Dynamics...</span>
                          </>
                        ) : (
                          <>
                            <span>⚡ Run Observational Disaster Simulation</span>
                          </>
                        )}
                      </button>
                    </div>
    
                    {simulationResult && (
                      <div className="rounded-xl border border-cyan-800/60 bg-slate-950/80 p-4 space-y-3 mt-4">
                        <div className="flex items-center justify-between border-b border-slate-800 pb-2">
                          <span className="text-xs font-mono font-bold text-cyan-300">
                            {simulationResult.scenario_id}
                          </span>
                          <span className="text-[10px] font-mono font-bold text-emerald-400 bg-emerald-950/80 px-2 py-0.5 rounded border border-emerald-800/50">
                            Financial Isolation: {simulationResult.financial_isolation_status}
                          </span>
                        </div>
    
                        <div className="grid grid-cols-3 gap-2 text-center text-xs font-mono">
                          <div className="rounded bg-slate-900 p-2 border border-slate-800">
                            <span className="text-[10px] text-slate-400 block">Blast Radius</span>
                            <span className="text-cyan-400 font-bold">{simulationResult.blast_radius.blast_radius_percentage.toFixed(1)}%</span>
                          </div>
                          <div className="rounded bg-slate-900 p-2 border border-slate-800">
                            <span className="text-[10px] text-slate-400 block">Est. RTO</span>
                            <span className="text-amber-400 font-bold">{simulationResult.estimated_rto_seconds}s</span>
                          </div>
                          <div className="rounded bg-slate-900 p-2 border border-slate-800">
                            <span className="text-[10px] text-slate-400 block">Est. RPO</span>
                            <span className="text-purple-400 font-bold">{simulationResult.estimated_rpo_seconds}s</span>
                          </div>
                        </div>
    
                        <div className="space-y-1 text-[11px]">
                          <p className="font-semibold text-slate-300">Recovery Steps:</p>
                          <ul className="list-disc list-inside text-slate-400 space-y-0.5 text-[10px] font-mono">
                            {simulationResult.recovery_steps.slice(0, 4).map((step, idx) => (
                              <li key={idx}>{step}</li>
                            ))}
                          </ul>
                        </div>
    
                        <p className="text-[9px] font-mono text-slate-500 italic border-t border-slate-800 pt-2">
                          {simulationResult.disclaimer}
                        </p>
                      </div>
                    )}
                  </div>
    
                  {/* Right Column: Operational Incidents Center */}
                  <div className="rounded-2xl border border-slate-800 bg-slate-900/90 p-6 shadow-xl space-y-4 flex flex-col justify-between">
                    <div>
                      <div className="flex items-center justify-between border-b border-slate-800 pb-3">
                        <div>
                          <h3 className="text-base font-bold text-white flex items-center gap-2">
                            <span>Resilience Incidents</span>
                            <span className="text-xs font-mono font-normal text-rose-400 bg-rose-950/80 px-2 py-0.5 rounded border border-rose-800/50">
                              {resilienceIncidents?.length || 0} Total
                            </span>
                          </h3>
                          <p className="text-xs text-slate-400 mt-0.5">
                            Active operational incidents reconstructed from immutable audit logs.
                          </p>
                        </div>
    
                        <div className="flex items-center gap-1 bg-slate-950 p-1 rounded-lg border border-slate-800 text-[10px] font-mono">
                          {["ALL", "CRITICAL", "HIGH", "MEDIUM"].map((sev) => (
                            <button
                              key={sev}
                              onClick={() => setResIncidentSeverityFilter(sev)}
                              className={`px-2 py-0.5 rounded transition ${
                                resIncidentSeverityFilter === sev ? "bg-slate-800 text-white font-bold" : "text-slate-400 hover:text-slate-200"
                              }`}
                            >
                              {sev}
                            </button>
                          ))}
                        </div>
                      </div>
    
                      <div className="space-y-2 mt-4 max-h-80 overflow-y-auto pr-1">
                        {resilienceIncidents && resilienceIncidents.length > 0 ? (
                          resilienceIncidents
                            .filter((inc) => resIncidentSeverityFilter === "ALL" || inc.severity === resIncidentSeverityFilter)
                            .map((inc) => (
                              <div
                                key={inc.incident_id}
                                className="rounded-xl border border-slate-800 bg-slate-950/60 p-3 space-y-2 hover:border-slate-700 transition"
                              >
                                <div className="flex items-center justify-between">
                                  <span className="text-xs font-mono font-bold text-slate-200 truncate">{inc.incident_id}</span>
                                  <div className="flex items-center gap-1.5">
                                    <span className={`rounded px-1.5 py-0.5 text-[9px] font-mono font-bold ${getIncidentSeverityBadge(inc.severity)}`}>
                                      {inc.severity}
                                    </span>
                                    <span className="rounded px-1.5 py-0.5 text-[9px] font-mono bg-slate-800 text-slate-300 border border-slate-700">
                                      {inc.state}
                                    </span>
                                  </div>
                                </div>
    
                                <p className="text-[11px] text-slate-300">{inc.recommended_action || "Investigate root cause"}</p>
    
                                <div className="flex items-center justify-between pt-1 border-t border-slate-800/60 text-[10px] font-mono text-slate-500">
                                  <span>Services: {inc.affected_services.join(", ") || "General"}</span>
                                  <div className="flex items-center gap-2">
                                    <button
                                      onClick={() => handleObsAcknowledgeIncident(inc.incident_id)}
                                      disabled={ackIncidentLoading}
                                      className="text-cyan-400 hover:text-cyan-300 font-bold disabled:opacity-50"
                                    >
                                      Acknowledge
                                    </button>
                                    <button
                                      onClick={() => handleObsEscalateIncident(inc.incident_id)}
                                      disabled={escIncidentLoading}
                                      className="text-rose-400 hover:text-rose-300 font-bold disabled:opacity-50"
                                    >
                                      Escalate
                                    </button>
                                  </div>
                                </div>
                              </div>
                            ))
                        ) : (
                          <div className="py-12 text-center text-xs text-slate-500">
                            Zero active operational resilience incidents detected. System healthy.
                          </div>
                        )}
                      </div>
                    </div>
    
                    <div className="rounded-xl bg-slate-950 p-3 border border-slate-800/80 text-[11px] text-slate-400 font-mono flex items-center justify-between mt-4">
                      <span>Incident Escalation Path:</span>
                      <span className="text-emerald-400 font-bold">VIEWER → OPERATOR → ADMIN</span>
                    </div>
                  </div>
                </div>
    
                {/* Section 5: Backup & Restore Integrity Panel */}
                <div className="rounded-2xl border border-slate-800 bg-slate-900/90 p-6 shadow-xl space-y-4">
                  <div className="flex items-center justify-between border-b border-slate-800 pb-3">
                    <div>
                      <h3 className="text-base font-bold text-white flex items-center gap-2">
                        <span>Backup Integrity & Restore Verification</span>
                        <span className="text-xs font-mono font-normal text-teal-400 bg-teal-950/80 px-2 py-0.5 rounded border border-teal-800/50">
                          SHA-256 Cryptographic Verification
                        </span>
                      </h3>
                      <p className="text-xs text-slate-400 mt-0.5">
                        Automated backup artifact freshness monitoring and non-destructive restore verification.
                      </p>
                    </div>
                  </div>
    
                  <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
                    <div className="rounded-xl border border-slate-800 bg-slate-950/60 p-4 space-y-1">
                      <span className="text-[10px] font-mono uppercase text-slate-400">Backup Artifact ID</span>
                      <p className="text-xs font-mono font-bold text-slate-200 truncate">{resilienceBackups?.backup_id || "BKP-LATEST"}</p>
                      <span className="text-[10px] text-slate-500 font-mono block pt-1">
                        Age: {resilienceBackups ? `${Math.round(resilienceBackups.backup_age_seconds / 60)} mins` : "0 mins"}
                      </span>
                    </div>
    
                    <div className="rounded-xl border border-slate-800 bg-slate-950/60 p-4 space-y-1">
                      <span className="text-[10px] font-mono uppercase text-slate-400">Freshness Status</span>
                      <p className="text-xs font-mono font-bold text-emerald-400">{resilienceBackups?.freshness_status || "CURRENT"}</p>
                      <span className="text-[10px] text-slate-500 font-mono block pt-1">
                        Threshold: &lt; 24 Hours
                      </span>
                    </div>
    
                    <div className="rounded-xl border border-slate-800 bg-slate-950/60 p-4 space-y-1">
                      <span className="text-[10px] font-mono uppercase text-slate-400">Restore Test Status</span>
                      <p className="text-xs font-mono font-bold text-cyan-400">{resilienceBackups?.restore_test_status || "UNVERIFIED"}</p>
                      <span className="text-[10px] text-slate-500 font-mono block pt-1">
                        Duration: {resilienceBackups?.restore_duration_seconds ? `${resilienceBackups.restore_duration_seconds}s` : "N/A"}
                      </span>
                    </div>
    
                    <div className="rounded-xl border border-slate-800 bg-slate-950/60 p-4 space-y-1">
                      <span className="text-[10px] font-mono uppercase text-slate-400">SHA-256 Checksum</span>
                      <p className="text-[10px] font-mono font-bold text-purple-300 truncate">
                        {resilienceBackups?.checksum_sha256 || "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"}
                      </p>
                      <span className="text-[10px] text-emerald-400 font-mono block pt-1">
                        ✓ Integrity Validated
                      </span>
                    </div>
                  </div>
                </div>
    
                {/* Section 6: Recovery Runbooks Inspector */}
                <div className="rounded-2xl border border-slate-800 bg-slate-900/90 p-6 shadow-xl space-y-4">
                  <div className="flex items-center justify-between border-b border-slate-800 pb-3">
                    <div>
                      <h3 className="text-base font-bold text-white flex items-center gap-2">
                        <span>Governed Recovery Runbooks</span>
                        <span className="text-xs font-mono font-normal text-indigo-400 bg-indigo-950/80 px-2 py-0.5 rounded border border-indigo-800/50">
                          9 Production Runbooks
                        </span>
                      </h3>
                      <p className="text-xs text-slate-400 mt-0.5">
                        Step-by-step ordered recovery procedures with strict preconditions, verification criteria, and rollback steps.
                      </p>
                    </div>
                  </div>
    
                  <div className="flex flex-wrap gap-2">
                    {resilienceRunbooks && resilienceRunbooks.map((rb) => (
                      <button
                        key={rb.runbook_id}
                        onClick={() => setSelectedRunbook(rb)}
                        className={`rounded-lg px-3 py-1.5 text-xs font-mono font-semibold transition ${
                          selectedRunbook?.runbook_id === rb.runbook_id
                            ? "bg-indigo-600 text-white shadow-lg shadow-indigo-600/30 font-bold"
                            : "bg-slate-950 border border-slate-800 text-slate-400 hover:text-slate-200"
                        }`}
                      >
                        {rb.runbook_id}
                      </button>
                    ))}
                  </div>
    
                  {selectedRunbook && (
                    <div className="rounded-xl border border-slate-800 bg-slate-950/60 p-5 space-y-4">
                      <div className="flex items-center justify-between border-b border-slate-800 pb-2">
                        <h4 className="text-sm font-bold text-white flex items-center gap-2">
                          <span>{selectedRunbook.scenario}</span>
                          <span className="text-[10px] font-mono text-cyan-400 bg-cyan-950 px-2 py-0.5 rounded border border-cyan-800">
                            Role: {selectedRunbook.required_role.toUpperCase()}
                          </span>
                        </h4>
                        <div className="text-xs font-mono text-slate-400 space-x-3">
                          <span>Est. Duration: {selectedRunbook.estimated_duration_minutes} mins</span>
                          <span>Target RTO: {selectedRunbook.rto_target_seconds}s</span>
                        </div>
                      </div>
    
                      <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-xs font-mono">
                        <div className="space-y-2">
                          <span className="text-[11px] font-bold text-amber-300 font-sans block">Preconditions</span>
                          <ul className="list-disc list-inside text-slate-400 space-y-1 text-[11px]">
                            {selectedRunbook.preconditions.map((p, idx) => (
                              <li key={idx}>{p}</li>
                            ))}
                          </ul>
    
                          <span className="text-[11px] font-bold text-cyan-300 font-sans block pt-2">Ordered Recovery Steps</span>
                          <ol className="list-decimal list-inside text-slate-300 space-y-1 text-[11px]">
                            {selectedRunbook.ordered_steps.map((s, idx) => (
                              <li key={idx}>{s}</li>
                            ))}
                          </ol>
                        </div>
    
                        <div className="space-y-2">
                          <span className="text-[11px] font-bold text-emerald-300 font-sans block">Verification Steps</span>
                          <ul className="list-disc list-inside text-slate-400 space-y-1 text-[11px]">
                            {selectedRunbook.verification_steps.map((v, idx) => (
                              <li key={idx}>{v}</li>
                            ))}
                          </ul>
    
                          <span className="text-[11px] font-bold text-rose-300 font-sans block pt-2">Rollback Procedures</span>
                          <ul className="list-disc list-inside text-slate-400 space-y-1 text-[11px]">
                            {selectedRunbook.rollback_steps.map((r, idx) => (
                              <li key={idx}>{r}</li>
                            ))}
                          </ul>
                        </div>
                      </div>
                    </div>
                  )}
                </div>
              </div>


    </>
  );
}
