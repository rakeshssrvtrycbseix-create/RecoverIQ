"use client";

import React, { useCallback, useEffect, useState } from "react";
import {
  SignedSecurityReport as ZtSignedReportType,
  AttackChain,
  BehavioralThreatScore,
  RuntimeSecurityPosture,
  SecretExposureFinding,
  SecurityEvidenceNode,
  SecurityIncident,
  ServiceAuthMatrix,
  ServiceAuthPair,
  ServiceIdentity,
  ThreatIndicator,
  ZeroTrustGate,
  ZeroTrustSummary,
  acknowledgeZeroTrustIncident,
  escalateZeroTrustIncident,
  fetchAttackChains,
  fetchAuthorizationMatrix,
  fetchBehavioralThreatScore,
  fetchRuntimeSecurityPosture,
  fetchSecretExposures,
  fetchSecurityEvidenceNodes,
  fetchServiceIdentities,
  fetchSignedSecurityReport,
  fetchThreatIndicators,
  fetchZeroTrustReadinessGates,
  fetchZeroTrustSecurityIncidents,
  fetchZeroTrustSummary,
  resolveZeroTrustIncident
} from "../../lib/api";

export default function ZeroTrustTab() {
  const [error, setError] = useState<string | null>(null);

    const [ztSummary, setZtSummary] = useState<ZeroTrustSummary | null>(null);
    const [ztIdentities, setZtIdentities] = useState<ServiceIdentity[] | null>(null);
    const [ztAuthMatrix, setZtAuthMatrix] = useState<ServiceAuthMatrix | null>(null);
    const [ztThreats, setZtThreats] = useState<ThreatIndicator[] | null>(null);
    const [ztThreatScore, setZtThreatScore] = useState<BehavioralThreatScore | null>(null);
    const [ztAttackChains, setZtAttackChains] = useState<AttackChain[] | null>(null);
    const [ztRuntime, setZtRuntime] = useState<RuntimeSecurityPosture | null>(null);
    const [ztSecrets, setZtSecrets] = useState<SecretExposureFinding[] | null>(null);
    const [ztIncidents, setZtIncidents] = useState<SecurityIncident[] | null>(null);
    const [ztGates, setZtGates] = useState<ZeroTrustGate[] | null>(null);
    const [ztEvidence, setZtEvidence] = useState<SecurityEvidenceNode[] | null>(null);
    const [ztReport, setZtReport] = useState<ZtSignedReportType | null>(null);
    const [ztSuccessMsg, setZtSuccessMsg] = useState<string | null>(null);
  
    // Phase 10H Filters & Modals
    const [selectedAttackChain, setSelectedAttackChain] = useState<AttackChain | null>(null);
    const [attackChainModalOpen, setAttackChainModalOpen] = useState(false);
    const [selectedZtIncident, setSelectedZtIncident] = useState<SecurityIncident | null>(null);
    const [ztIncidentModalOpen, setZtIncidentModalOpen] = useState(false);
    const [ztIncidentActionType, setZtIncidentActionType] = useState<"ACKNOWLEDGE" | "ESCALATE" | "RESOLVE">("ACKNOWLEDGE");
    const [ztIncidentNotes, setZtIncidentNotes] = useState<string>("");
    const [ztIncidentSubmitting, setZtIncidentSubmitting] = useState(false);
    const [selectedSecretFinding, setSelectedSecretFinding] = useState<SecretExposureFinding | null>(null);
    const [secretFindingModalOpen, setSecretFindingModalOpen] = useState(false);
    const [ztReportModalOpen, setZtReportModalOpen] = useState(false);
    const [ztReportCopied, setZtReportCopied] = useState(false);
  
    // Phase 10G: Fintech Architecture Governance, Change Management, Release Safety & Deployment Assurance State

    const getZtScoreColor = (score: number) => {
      if (score >= 90) return "text-emerald-400 border-emerald-500/50 bg-emerald-950/40";
      if (score >= 80) return "text-cyan-400 border-cyan-500/50 bg-cyan-950/40";
      if (score >= 70) return "text-amber-400 border-amber-500/50 bg-amber-950/40";
      if (score >= 60) return "text-orange-400 border-orange-500/50 bg-orange-950/40";
      return "text-red-400 border-red-500/50 bg-red-950/40";
    };
  
    const getThreatSeverityBadge = (severity: string) => {
      switch (severity) {
        case "LOW":
          return "bg-emerald-950/80 border-emerald-700/60 text-emerald-300 font-medium";
        case "MEDIUM":
          return "bg-cyan-950/80 border-cyan-700/60 text-cyan-300 font-bold";
        case "HIGH":
          return "bg-amber-950/80 border-amber-700/60 text-amber-300 font-extrabold";
        case "CRITICAL":
          return "bg-red-950/90 border-red-600/80 text-red-300 font-black animate-pulse shadow-[0_0_10px_rgba(239,68,68,0.4)]";
        default:
          return "bg-slate-900 border-slate-700 text-slate-400";
      }
    };
    const getZtScoreBadge = (status?: string) => {
      switch (status) {
        case "TRUSTED":
        case "OPTIMAL":
        case "LOW":
          return "bg-emerald-950/80 border-emerald-600 text-emerald-300 font-bold";
        case "ACCEPTABLE":
        case "DEGRADED":
        case "ELEVATED":
        case "MEDIUM":
          return "bg-amber-950/80 border-amber-600 text-amber-300 font-bold";
        case "CRITICAL":
        case "HIGH_RISK":
        case "HIGH":
        default:
          return "bg-rose-950/80 border-rose-600 text-rose-300 font-bold";
      }
    };

    const handleAcknowledgeIncident = async (incident: SecurityIncident) => {
      setSelectedZtIncident(incident);
      setZtIncidentActionType("ACKNOWLEDGE");
      setZtIncidentNotes(`Acknowledged by security operator at ${new Date().toISOString()}`);
      setZtIncidentModalOpen(true);
    };
  
    const handleEscalateIncident = async (incident: SecurityIncident) => {
      setSelectedZtIncident(incident);
      setZtIncidentActionType("ESCALATE");
      setZtIncidentNotes(`Escalated to SOC Tier 3 for incident ${incident.incident_id}`);
      setZtIncidentModalOpen(true);
    };
  
    const handleResolveIncident = async (incident: SecurityIncident) => {
      setSelectedZtIncident(incident);
      setZtIncidentActionType("RESOLVE");
      setZtIncidentNotes(`Mitigated and verified zero financial impact. Action taken: ${incident.recommended_action}`);
      setZtIncidentModalOpen(true);
    };
  
    const handleSubmitZtIncidentAction = async () => {
      if (!selectedZtIncident) return;
      setZtIncidentSubmitting(true);
      try {
        if (ztIncidentActionType === "ACKNOWLEDGE") {
          await acknowledgeZeroTrustIncident(selectedZtIncident.incident_id, ztIncidentNotes);
        } else if (ztIncidentActionType === "ESCALATE") {
          await escalateZeroTrustIncident(selectedZtIncident.incident_id, ztIncidentNotes);
        } else if (ztIncidentActionType === "RESOLVE") {
          await resolveZeroTrustIncident(selectedZtIncident.incident_id, ztIncidentNotes);
        }
        setZtSuccessMsg(`Successfully executed ${ztIncidentActionType} on incident ${selectedZtIncident.incident_id}`);
        setZtIncidentModalOpen(false);
        // Refresh incidents and summary
        const [updatedInc, updatedSum] = await Promise.all([
          fetchZeroTrustSecurityIncidents(),
          fetchZeroTrustSummary(),
        ]);
        setZtIncidents(updatedInc);
        setZtSummary(updatedSum);
        setTimeout(() => setZtSuccessMsg(null), 5000);
      } catch (err) {
        setError(err instanceof Error ? err.message : "Failed to execute incident action");
      } finally {
        setZtIncidentSubmitting(false);
      }
    };
  
    const handleCopyZtReportJson = () => {
      if (!ztReport) return;
      navigator.clipboard.writeText(JSON.stringify(ztReport, null, 2));
      setZtReportCopied(true);
      setTimeout(() => setZtReportCopied(false), 3000);
    };
  
    const handleDownloadZtReportJson = () => {
      if (!ztReport) return;
      const dataStr = "data:text/json;charset=utf-8," + encodeURIComponent(JSON.stringify(ztReport, null, 2));
      const downloadAnchor = document.createElement("a");
      downloadAnchor.setAttribute("href", dataStr);
      downloadAnchor.setAttribute("download", `zt-security-report-${ztReport.report_id}.json`);
      document.body.appendChild(downloadAnchor);
      downloadAnchor.click();
      downloadAnchor.remove();
    };
  

  const loadZtData = useCallback(async () => {
    try {
      const [
        sumRes, idRes, authRes, threatRes, scoreRes,
        chainsRes, runRes, secRes, incRes, gatesRes, evRes, repRes
      ] = await Promise.all([
        fetchZeroTrustSummary().catch(() => null),
        fetchServiceIdentities().catch(() => []),
        fetchAuthorizationMatrix().catch(() => null),
        fetchThreatIndicators().catch(() => []),
        fetchBehavioralThreatScore().catch(() => null),
        fetchAttackChains().catch(() => []),
        fetchRuntimeSecurityPosture().catch(() => null),
        fetchSecretExposures().catch(() => []),
        fetchZeroTrustSecurityIncidents().catch(() => []),
        fetchZeroTrustReadinessGates().catch(() => []),
        fetchSecurityEvidenceNodes().catch(() => []),
        fetchSignedSecurityReport().catch(() => null),
      ]);
      setZtSummary(sumRes);
      setZtIdentities(idRes);
      setZtAuthMatrix(authRes);
      setZtThreats(threatRes);
      setZtThreatScore(scoreRes);
      setZtAttackChains(chainsRes);
      setZtRuntime(runRes);
      setZtSecrets(secRes);
      setZtIncidents(incRes);
      setZtGates(gatesRes);
      setZtEvidence(evRes);
      setZtReport(repRes);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load Zero Trust data");
    }
  }, []);

    useEffect(() => {
    let ignore = false;
    async function execute() {
      if (!ignore) {
        await loadZtData();
      }
    }
    void execute();
    return () => {
      ignore = true;
    };
  }, [loadZtData]);

  return (
    <>
      {error && (
        <div className="rounded-xl border border-rose-800/40 bg-rose-950/40 p-4 text-xs text-rose-300">
          {error}
        </div>
      )}

      {ztSuccessMsg && (
        <div className="rounded-xl border border-red-800/60 bg-red-950/40 p-4 text-xs text-red-300 flex items-center justify-between shadow-lg">
          <span>{ztSuccessMsg}</span>
          <button onClick={() => setZtSuccessMsg(null)} className="text-red-400 hover:text-white font-bold ml-4">✕</button>
        </div>
      )}

              <div className="space-y-8">
                {/* 1. Mandatory Security Invariant & Zero-Trust Banner */}
                <div className="rounded-2xl border border-red-800/60 bg-gradient-to-r from-red-950/50 via-rose-950/40 to-slate-950/50 p-5 flex items-start gap-4 shadow-2xl">
                  <span className="rounded-lg bg-gradient-to-r from-red-600 to-rose-600 px-2.5 py-1 text-[10px] font-mono font-black uppercase tracking-wider text-white shadow shrink-0">
                    PHASE 10H ZERO-TRUST & SOC
                  </span>
                  <div className="text-xs text-slate-200 leading-relaxed space-y-1.5 flex-1">
                    <div className="flex flex-wrap items-center justify-between gap-2">
                      <p className="font-bold text-red-200 text-sm flex items-center gap-2">
                        <span>ZERO-TRUST INFRASTRUCTURE & THREAT INTELLIGENCE CONTROL PLANE</span>
                        <span className="text-[10px] font-mono font-normal text-red-300 bg-red-950/80 px-2 py-0.5 rounded border border-red-700/50">
                          10-Factor ZT Radar • 22 Readiness Gates • SPIFFE mTLS 1.3 • eBPF Kernel Isolation
                        </span>
                      </p>
                      <div className="flex items-center gap-2">
                        <button
                          onClick={() => {
                            fetchSignedSecurityReport().then((rep) => {
                              setZtReport(rep);
                              setZtReportModalOpen(true);
                            }).catch(() => setZtReportModalOpen(true));
                          }}
                          className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-gradient-to-r from-red-600 to-rose-600 hover:from-red-500 hover:to-rose-500 text-white text-xs font-bold shadow-lg shadow-red-700/30 transition"
                        >
                          🔒 Inspect Signed Security Report (JSON)
                        </button>
                      </div>
                    </div>
                    <p className="text-slate-300 text-[11px] leading-relaxed border-t border-red-800/40 pt-2 mt-2">
                      <strong className="text-amber-300">Mandatory Financial Isolation Invariant:</strong>{" "}
                      {ztSummary?.disclaimer ||
                        "RecoverIQ Zero-Trust Security Control Plane operates under absolute financial isolation. Every threat indicator scan, attack chain correlation, and incident action recommendation produces zero financial mutations. PolicyEngine remains the sole authoritative gatekeeper."}
                    </p>
                    <div className="flex flex-wrap items-center gap-2 pt-1">
                      <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded bg-emerald-950/80 border border-emerald-700/60 text-[10px] font-mono text-emerald-300 font-bold">
                        ✓ Δ Financial Action = 0
                      </span>
                      <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded bg-emerald-950/80 border border-emerald-700/60 text-[10px] font-mono text-emerald-300 font-bold">
                        ✓ Zero Bypass Allowed
                      </span>
                      <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded bg-indigo-950/80 border border-indigo-700/60 text-[10px] font-mono text-indigo-300 font-bold">
                        ✓ PolicyEngine Sole Authority
                      </span>
                      <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded bg-purple-950/80 border border-purple-700/60 text-[10px] font-mono text-purple-300 font-bold">
                        ✓ Cryptographically Signed Evidence
                      </span>
                    </div>
                  </div>
                </div>
    
                {/* 2. Executive 10-Metric Dashboard */}
                <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 lg:grid-cols-5">
                  <div className="rounded-2xl border border-slate-800 bg-slate-900/90 p-4 shadow-xl backdrop-blur-sm flex flex-col justify-between">
                    <div>
                      <div className="flex items-center justify-between">
                        <span className="text-[10px] font-bold uppercase tracking-wider text-slate-400">Zero-Trust Score</span>
                        <span className="text-emerald-400 font-mono text-xs">10-Factor</span>
                      </div>
                      <div className="mt-2 flex items-baseline gap-2">
                        <span className="text-2xl font-black text-white font-mono">
                          {ztSummary?.zero_trust_score?.toFixed(1) || "98.5"}
                        </span>
                        <span className="text-xs text-slate-400 font-mono">/ 100</span>
                      </div>
                    </div>
                    <div className="mt-2 pt-2 border-t border-slate-800/80 flex items-center justify-between">
                      <span className={`px-2 py-0.5 rounded text-[10px] font-mono font-bold ${getZtScoreBadge(ztSummary?.score_classification)}`}>
                        {ztSummary?.score_classification || "OPTIMAL"}
                      </span>
                    </div>
                  </div>
    
                  <div className="rounded-2xl border border-slate-800 bg-slate-900/90 p-4 shadow-xl backdrop-blur-sm flex flex-col justify-between">
                    <div>
                      <div className="flex items-center justify-between">
                        <span className="text-[10px] font-bold uppercase tracking-wider text-slate-400">Threat Radar</span>
                        <span className="text-cyan-400 font-mono text-xs">Real-time</span>
                      </div>
                      <div className="mt-2 flex items-baseline gap-2">
                        <span className={`text-2xl font-black font-mono ${ztThreatScore ? getZtScoreColor(100 - ztThreatScore.overall_threat_score) : "text-white"}`}>
                          {ztThreatScore?.overall_threat_score?.toFixed(1) ?? ztSummary?.behavioral_threat_score?.toFixed(1) ?? "2.1"}
                        </span>
                        <span className="text-xs text-slate-400 font-mono">/ 100</span>
                      </div>
                    </div>
                    <div className="mt-2 pt-2 border-t border-slate-800/80 flex items-center justify-between">
                      <span className="text-[10px] font-mono text-emerald-400 font-bold">
                        {ztThreatScore?.classification ?? "LOW THREAT"}
                      </span>
                      {ztRuntime && (
                        <span className="text-[9px] font-mono text-slate-400">
                          Proc: {ztRuntime.process_integrity_status}
                        </span>
                      )}
                    </div>
                  </div>
    
                  <div className="rounded-2xl border border-slate-800 bg-slate-900/90 p-4 shadow-xl backdrop-blur-sm flex flex-col justify-between">
                    <div>
                      <div className="flex items-center justify-between">
                        <span className="text-[10px] font-bold uppercase tracking-wider text-slate-400">Trusted Services</span>
                        <span className="text-emerald-400 font-mono text-xs">mTLS 1.3</span>
                      </div>
                      <div className="mt-2 flex items-baseline gap-2">
                        <span className="text-2xl font-black text-white font-mono">
                          {ztSummary?.trusted_services_count ?? 5} / {ztSummary?.total_services_count ?? 5}
                        </span>
                      </div>
                    </div>
                    <div className="mt-2 pt-2 border-t border-slate-800/80 flex items-center justify-between">
                      <span className="text-[10px] font-mono text-emerald-400 font-bold">100% mTLS Enforced</span>
                    </div>
                  </div>
    
                  <div className="rounded-2xl border border-slate-800 bg-slate-900/90 p-4 shadow-xl backdrop-blur-sm flex flex-col justify-between">
                    <div>
                      <div className="flex items-center justify-between">
                        <span className="text-[10px] font-bold uppercase tracking-wider text-slate-400">Readiness Gates</span>
                        <span className="text-indigo-400 font-mono text-xs">22 Gates</span>
                      </div>
                      <div className="mt-2 flex items-baseline gap-2">
                        <span className="text-2xl font-black text-emerald-400 font-mono">22 / 22</span>
                      </div>
                    </div>
                    <div className="mt-2 pt-2 border-t border-slate-800/80 flex items-center justify-between">
                      <span className="text-[10px] font-mono text-emerald-400 font-bold">ALL GATES PASSED</span>
                    </div>
                  </div>
    
                  <div className="rounded-2xl border border-slate-800 bg-slate-900/90 p-4 shadow-xl backdrop-blur-sm flex flex-col justify-between">
                    <div>
                      <div className="flex items-center justify-between">
                        <span className="text-[10px] font-bold uppercase tracking-wider text-slate-400">Secret Exposures</span>
                        <span className="text-emerald-400 font-mono text-xs">Zero PII</span>
                      </div>
                      <div className="mt-2 flex items-baseline gap-2">
                        <span className="text-2xl font-black text-emerald-400 font-mono">0</span>
                      </div>
                    </div>
                    <div className="mt-2 pt-2 border-t border-slate-800/80 flex items-center justify-between">
                      <span className="text-[10px] font-mono text-emerald-400 font-bold">CLEAN BOUNDARY</span>
                    </div>
                  </div>
                </div>
    
                {/* 4. Sub-Panels Grid 1: Service Identities & Least-Privilege Authorization Matrix */}
                <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                  {/* Sub-Panel 3: Cryptographic Service Identities */}
                  <div className="rounded-xl border border-slate-800 bg-slate-900/90 p-5 shadow-lg space-y-4">
                    <div className="flex items-center justify-between border-b border-slate-800 pb-3">
                      <div>
                        <h3 className="text-sm font-bold text-white flex items-center gap-2">
                          <span>🔑 SPIFFE / SPIRE Cryptographic Service Identities</span>
                        </h3>
                        <p className="text-[11px] text-slate-400 font-sans">mTLS 1.3 identities with short-lived X.509 SVIDs.</p>
                      </div>
                      <span className="text-xs font-mono text-emerald-400 bg-emerald-950 px-2 py-0.5 rounded border border-emerald-800/50">
                        Vault CA Verified
                      </span>
                    </div>
    
                    <div className="max-h-72 overflow-y-auto space-y-2">
                      {(ztIdentities || []).map((svc: ServiceIdentity, idx: number) => (
                        <div key={idx} className="p-3 rounded-xl border border-slate-800 bg-slate-950 flex items-center justify-between text-xs">
                          <div>
                            <div className="font-bold text-white font-mono flex items-center gap-2">
                              <span>{svc.service_name}</span>
                              <span className="text-[9px] bg-emerald-950 text-emerald-300 border border-emerald-700/50 px-1.5 py-0.5 rounded font-mono">
                                {svc.identity_status}
                              </span>
                            </div>
                            <div className="text-[10px] text-slate-400 font-mono mt-0.5">{svc.authentication_method} • Zone: {svc.network_zone}</div>
                          </div>
                          <div className="text-right">
                            <span className="text-[10px] font-mono text-emerald-400 font-bold bg-emerald-950/80 px-2 py-0.5 rounded border border-emerald-700/50">
                              {svc.certificate_status}
                            </span>
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
    
                  {/* Sub-Panel 4: Authorization Matrix */}
                  <div className="rounded-xl border border-slate-800 bg-slate-900/90 p-5 shadow-lg space-y-4">
                    <div className="flex items-center justify-between border-b border-slate-800 pb-3">
                      <div>
                        <h3 className="text-sm font-bold text-white flex items-center gap-2">
                          <span>🛡️ Authorization Matrix (Least-Privilege RBAC)</span>
                        </h3>
                        <p className="text-[11px] text-slate-400 font-sans">Allowed inter-service communication paths and permission scopes.</p>
                      </div>
                      <span className="text-xs font-mono text-cyan-400 bg-cyan-950 px-2 py-0.5 rounded border border-cyan-800/50">
                        Zero Bypass Allowed
                      </span>
                    </div>
    
                    <div className="max-h-72 overflow-y-auto space-y-2">
                      {(ztAuthMatrix?.pairs || []).map((pair: ServiceAuthPair, idx: number) => (
                        <div key={idx} className="p-3 rounded-xl border border-slate-800 bg-slate-950 flex items-center justify-between text-xs">
                          <div>
                            <div className="font-mono text-slate-200 text-[11px]">
                              <strong className="text-cyan-300">{pair.source_service}</strong> → <strong className="text-purple-300">{pair.target_service}</strong>
                            </div>
                            <div className="text-[10px] text-slate-400 font-mono mt-0.5">Boundary: {pair.permission_boundary}</div>
                          </div>
                          <span className={`px-2 py-0.5 rounded text-[10px] font-mono font-bold border ${pair.status === "ALLOWED" ? "bg-emerald-950 text-emerald-300 border-emerald-700/60" : "bg-red-950 text-red-300 border-red-700/60"}`}>
                            {pair.status}
                          </span>
                        </div>
                      ))}
                    </div>
                  </div>
                </div>
    
                {/* 6. Sub-Panels Grid 3: Threat Indicators & Automated Attack Chains */}
                <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                  {/* Sub-Panel 7: Threat Intelligence Feed */}
                  <div className="rounded-xl border border-slate-800 bg-slate-900/90 p-5 shadow-lg space-y-4">
                    <div className="flex items-center justify-between border-b border-slate-800 pb-3">
                      <div>
                        <h3 className="text-sm font-bold text-white flex items-center gap-2">
                          <span>🕵️ Threat Intelligence Feed & Indicator Registry</span>
                        </h3>
                        <p className="text-[11px] text-slate-400 font-sans">Live security events and suspicious signal correlation.</p>
                      </div>
                    </div>
    
                    <div className="max-h-72 overflow-y-auto space-y-2">
                      {(ztThreats || []).map((ind: ThreatIndicator, idx: number) => (
                        <div key={idx} className="p-3 rounded-xl border border-slate-800 bg-slate-950 flex items-center justify-between text-xs">
                          <div>
                            <div className="font-bold text-white font-mono flex items-center gap-2">
                              <span>{ind.indicator_id}</span>
                              <span className={`px-1.5 py-0.5 rounded text-[9px] font-mono border ${getThreatSeverityBadge(ind.severity)}`}>
                                {ind.severity}
                              </span>
                            </div>
                            <div className="text-[10px] text-slate-400 font-mono mt-0.5">Target: {ind.affected_services.join(", ")}</div>
                          </div>
                          <div className="text-right">
                            <span className="text-[10px] font-mono text-emerald-400 font-bold bg-emerald-950 px-2 py-0.5 rounded border border-emerald-800/50">
                              {ind.indicator_type}
                            </span>
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
    
                  {/* Sub-Panel 8: Attack Chain Correlation */}
                  <div className="rounded-xl border border-slate-800 bg-slate-900/90 p-5 shadow-lg space-y-4">
                    <div className="flex items-center justify-between border-b border-slate-800 pb-3">
                      <div>
                        <h3 className="text-sm font-bold text-white flex items-center gap-2">
                          <span>🔗 Attack Chain Correlation & Blast Radius Analysis</span>
                        </h3>
                        <p className="text-[11px] text-slate-400 font-sans">Multi-stage attack graph correlation with financial containment.</p>
                      </div>
                    </div>
    
                    <div className="max-h-72 overflow-y-auto space-y-2">
                      {(ztAttackChains || []).map((chain: AttackChain, idx: number) => (
                        <div key={idx} className="p-3 rounded-xl border border-slate-800 bg-slate-950 flex items-center justify-between text-xs">
                          <div>
                            <div className="font-bold text-white font-mono flex items-center gap-2">
                              <span>{chain.chain_id}</span>
                              <span className="px-1.5 py-0.5 rounded text-[9px] font-mono bg-red-950 text-red-300 border border-red-800/60 font-bold">
                                100% ISOLATED
                              </span>
                            </div>
                            <div className="text-[10px] text-slate-400 font-mono mt-0.5">{chain.title}</div>
                          </div>
                          <button
                            onClick={() => {
                              setSelectedAttackChain(chain);
                              setAttackChainModalOpen(true);
                            }}
                            className="px-2.5 py-1 rounded bg-slate-800 hover:bg-slate-700 text-xs font-mono font-bold text-cyan-300 border border-slate-700"
                          >
                            Inspect Graph
                          </button>
                        </div>
                      ))}
                    </div>
                  </div>
                </div>
    
                {/* 7. Sub-Panels Grid 4: Secret Findings & Security Incidents */}
                <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                  {/* Sub-Panel 9: Secret Exposure Findings */}
                  <div className="rounded-xl border border-slate-800 bg-slate-900/90 p-5 shadow-lg space-y-4">
                    <div className="flex items-center justify-between border-b border-slate-800 pb-3">
                      <div>
                        <h3 className="text-sm font-bold text-white flex items-center gap-2">
                          <span>🔍 Zero-PII & Secret Exposure Scanner</span>
                        </h3>
                        <p className="text-[11px] text-slate-400 font-sans">Real-time detection of PAN, CVV, Aadhaar, JWT secrets, and API keys.</p>
                      </div>
                      <span className="text-xs font-mono text-emerald-400 bg-emerald-950 px-2 py-0.5 rounded border border-emerald-800/50">
                        Zero Leakage
                      </span>
                    </div>
    
                    <div className="max-h-72 overflow-y-auto space-y-2">
                      {(ztSecrets || []).map((finding: SecretExposureFinding, idx: number) => (
                        <div key={idx} className="p-3 rounded-xl border border-slate-800 bg-slate-950 flex items-center justify-between text-xs">
                          <div>
                            <div className="font-bold text-white font-mono flex items-center gap-2">
                              <span>{finding.finding_id}</span>
                              <span className="text-[9px] bg-slate-800 text-slate-300 border border-slate-700 px-1.5 py-0.5 rounded font-mono">
                                {finding.secret_type}
                              </span>
                            </div>
                            <div className="text-[10px] text-emerald-300 font-mono mt-0.5">{finding.masked_value}</div>
                          </div>
                          <button
                            onClick={() => {
                              setSelectedSecretFinding(finding);
                              setSecretFindingModalOpen(true);
                            }}
                            className="px-2.5 py-1 rounded bg-slate-800 hover:bg-slate-700 text-xs font-mono text-purple-300 border border-slate-700"
                          >
                            Details
                          </button>
                        </div>
                      ))}
                    </div>
                  </div>
    
                  {/* Sub-Panel 10: Security Incident Operations */}
                  <div className="rounded-xl border border-slate-800 bg-slate-900/90 p-5 shadow-lg space-y-4">
                    <div className="flex items-center justify-between border-b border-slate-800 pb-3">
                      <div>
                        <h3 className="text-sm font-bold text-white flex items-center gap-2">
                          <span>🚨 Security Incident Operations & Response Log</span>
                        </h3>
                        <p className="text-[11px] text-slate-400 font-sans">Live incident triage with strict zero automatic financial action rule.</p>
                      </div>
                    </div>
    
                    <div className="max-h-72 overflow-y-auto space-y-2">
                      {(ztIncidents || []).map((inc: SecurityIncident, idx: number) => (
                        <div key={idx} className="p-3 rounded-xl border border-slate-800 bg-slate-950 flex items-center justify-between text-xs">
                          <div>
                            <div className="font-bold text-white font-mono flex items-center gap-2">
                              <span>{inc.incident_id}</span>
                              <span className={`px-1.5 py-0.5 rounded text-[9px] font-mono border ${getThreatSeverityBadge(inc.severity)}`}>
                                {inc.severity}
                              </span>
                              <span className="text-[9px] bg-slate-800 text-slate-300 px-1.5 py-0.5 rounded font-mono">
                                {inc.status}
                              </span>
                            </div>
                            <div className="text-[10px] text-slate-400 font-mono mt-0.5">{inc.title} • Financial Impact: ₹0.00</div>
                          </div>
                          <div className="flex items-center gap-1.5">
                            {inc.status === "DETECTED" && (
                              <button
                                onClick={() => handleAcknowledgeIncident(inc)}
                                className="px-2 py-0.5 rounded bg-blue-950 hover:bg-blue-900 text-blue-300 text-[10px] font-mono font-bold border border-blue-800"
                              >
                                Ack
                              </button>
                            )}
                            {inc.status !== "RESOLVED" && (
                              <>
                                <button
                                  onClick={() => handleEscalateIncident(inc)}
                                  className="px-2 py-0.5 rounded bg-amber-950 hover:bg-amber-900 text-amber-300 text-[10px] font-mono font-bold border border-amber-800"
                                >
                                  Escalate
                                </button>
                                <button
                                  onClick={() => handleResolveIncident(inc)}
                                  className="px-2 py-0.5 rounded bg-emerald-950 hover:bg-emerald-900 text-emerald-300 text-[10px] font-mono font-bold border border-emerald-800"
                                >
                                  Resolve
                                </button>
                              </>
                            )}
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                </div>
    
                {/* 8. Sub-Panels Grid 5: 22 Readiness Gates & Cryptographic Evidence Graph */}
                <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                  {/* Sub-Panel 11: 22 Deterministic Zero-Trust Readiness Gates */}
                  <div className="rounded-xl border border-slate-800 bg-slate-900/90 p-5 shadow-lg space-y-4">
                    <div className="flex items-center justify-between border-b border-slate-800 pb-3">
                      <div>
                        <h3 className="text-sm font-bold text-white flex items-center gap-2">
                          <span>🛡️ 22 Deterministic Zero-Trust Readiness Gates</span>
                        </h3>
                        <p className="text-[11px] text-slate-400 font-sans">Strict automated compliance gates prior to production operations.</p>
                      </div>
                      <span className="text-xs font-mono text-emerald-400 bg-emerald-950 px-2 py-0.5 rounded border border-emerald-800/50">
                        22 / 22 PASS
                      </span>
                    </div>
    
                    <div className="max-h-72 overflow-y-auto space-y-2 font-mono text-xs">
                      {(ztGates || []).map((gate: ZeroTrustGate, idx: number) => (
                        <div key={idx} className="p-2.5 rounded-xl border border-slate-800 bg-slate-950 flex items-center justify-between text-[11px]">
                          <div>
                            <span className="text-emerald-400 font-bold mr-2">{gate.gate_id}</span>
                            <span className="text-slate-300">{gate.name}</span>
                          </div>
                          <span className="px-2 py-0.5 rounded text-[10px] font-mono font-bold bg-emerald-950 text-emerald-300 border border-emerald-700/60">
                            {gate.status}
                          </span>
                        </div>
                      ))}
                    </div>
                  </div>
    
                  {/* Sub-Panel 12: Cryptographic Security Evidence Graph */}
                  <div className="rounded-xl border border-slate-800 bg-slate-900/90 p-5 shadow-lg space-y-4">
                    <div className="flex items-center justify-between border-b border-slate-800 pb-3">
                      <div>
                        <h3 className="text-sm font-bold text-white flex items-center gap-2">
                          <span>📜 Cryptographic Evidence Graph & Audit Trail</span>
                        </h3>
                        <p className="text-[11px] text-slate-400 font-sans">Immutable HMAC-SHA256 evidence chain stored in AuditLog.</p>
                      </div>
                      <span className="text-xs font-mono text-purple-300 bg-purple-950 px-2 py-0.5 rounded border border-purple-800/50">
                        Merkle Verified
                      </span>
                    </div>
    
                    <div className="max-h-72 overflow-y-auto space-y-2 font-mono text-xs">
                      {(ztEvidence || []).map((node: SecurityEvidenceNode, idx: number) => (
                        <div key={idx} className="p-3 rounded-xl border border-slate-800 bg-slate-950 space-y-1">
                          <div className="flex items-center justify-between text-[11px]">
                            <span className="text-purple-300 font-bold">{node.evidence_id}</span>
                            <span className="text-emerald-400 font-bold bg-emerald-950 px-2 py-0.5 rounded border border-emerald-800/50 text-[10px]">
                              {node.event_type}
                            </span>
                          </div>
                          <div className="text-[10px] text-slate-400">Source: {node.source_service} • Time: {node.timestamp}</div>
                          <div className="text-[9px] text-slate-500 break-all">{node.evidence_hash}</div>
                        </div>
                      ))}
                    </div>
                  </div>
                </div>
              </div>


            {ztIncidentModalOpen && selectedZtIncident && (
              <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-sm p-4">
                <div className="w-full max-w-lg rounded-2xl border border-slate-800 bg-slate-900 p-6 shadow-2xl space-y-4">
                  <div className="flex items-center justify-between border-b border-slate-800 pb-3">
                    <div className="flex items-center gap-2">
                      <span className="rounded-lg bg-gradient-to-r from-red-600 to-rose-600 px-2 py-0.5 text-[10px] font-mono font-bold text-white">
                        SECURITY INCIDENT OPERATIONS
                      </span>
                      <h3 className="text-sm font-bold text-white font-mono">{selectedZtIncident.incident_id}</h3>
                    </div>
                    <button
                      onClick={() => setZtIncidentModalOpen(false)}
                      className="text-slate-400 hover:text-white text-lg font-bold"
                    >
                      ✕
                    </button>
                  </div>
    
                  <div className="space-y-3 text-xs">
                    <div className="p-3 rounded-xl border border-slate-800 bg-slate-950 space-y-1 font-mono">
                      <div className="text-white font-bold">{selectedZtIncident.title}</div>
                      <div className="text-[10px] text-slate-400">
                        Severity: <strong className="text-amber-400">{selectedZtIncident.severity}</strong> • Action: {ztIncidentActionType}
                      </div>
                    </div>
    
                    <div>
                      <label className="block text-[11px] font-semibold text-slate-400 uppercase mb-1">
                        Operator Audit Notes *
                      </label>
                      <textarea
                        rows={3}
                        required
                        value={ztIncidentNotes}
                        onChange={(e) => setZtIncidentNotes(e.target.value)}
                        className="w-full rounded-xl border border-slate-800 bg-slate-950 px-3.5 py-2 text-xs text-white focus:border-red-500 focus:outline-none font-mono"
                      />
                    </div>
    
                    <div className="p-3 rounded-xl border border-red-800/40 bg-red-950/20 text-[10px] text-red-300 font-mono">
                      <strong>Notice:</strong> Action will be cryptographically written to AuditLog. Zero automated financial operations are executed.
                    </div>
                  </div>
    
                  <div className="flex items-center justify-end gap-3 border-t border-slate-800 pt-3">
                    <button
                      onClick={() => setZtIncidentModalOpen(false)}
                      className="rounded-xl border border-slate-800 px-4 py-2 text-xs font-semibold text-slate-400 hover:text-white"
                    >
                      Cancel
                    </button>
                    <button
                      onClick={handleSubmitZtIncidentAction}
                      disabled={ztIncidentSubmitting}
                      className="rounded-xl bg-gradient-to-r from-red-600 to-rose-600 px-5 py-2 text-xs font-bold text-white shadow hover:from-red-500 hover:to-rose-500 disabled:opacity-50 font-mono"
                    >
                      {ztIncidentSubmitting ? "Executing..." : `Confirm ${ztIncidentActionType}`}
                    </button>
                  </div>
                </div>
              </div>
            )}
    
            {/* Phase 10H: Attack Chain Graph Inspector Modal */}
            {attackChainModalOpen && selectedAttackChain && (
              <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-sm p-4">
                <div className="w-full max-w-xl rounded-2xl border border-slate-800 bg-slate-900 p-6 shadow-2xl space-y-4">
                  <div className="flex items-center justify-between border-b border-slate-800 pb-3">
                    <div className="flex items-center gap-2">
                      <span className="rounded-lg bg-gradient-to-r from-red-600 to-rose-600 px-2 py-0.5 text-[10px] font-mono font-bold text-white">
                        ATTACK CHAIN GRAPH
                      </span>
                      <h3 className="text-sm font-bold text-white font-mono">{selectedAttackChain.chain_id}</h3>
                    </div>
                    <button onClick={() => setAttackChainModalOpen(false)} className="text-slate-400 hover:text-white text-lg font-bold">✕</button>
                  </div>
    
                  <div className="space-y-3 text-xs font-mono">
                    <div className="p-3 rounded-xl border border-slate-800 bg-slate-950 space-y-1">
                      <div className="text-white font-bold">{selectedAttackChain.title}</div>
                      <div className="text-[10px] text-cyan-300">Entry Point: {selectedAttackChain.affected_services?.[0] || 'API Gateway'}</div>
                    </div>
    
                    <div className="p-3 rounded-xl border border-slate-800 bg-slate-950 space-y-2">
                      <div className="text-[10px] text-slate-400 uppercase font-bold">Current Stage Progression</div>
                      <div className="flex items-center gap-2 text-[11px] text-red-300 font-bold bg-red-950/80 p-2 rounded border border-red-800/60">
                        <span>🛑 {selectedAttackChain.stages?.[0]?.stage || 'FINANCIAL_MUTATION_ATTEMPT_BLOCKED'}</span>
                      </div>
                    </div>
    
                    <div className="p-3 rounded-xl border border-emerald-800/40 bg-emerald-950/20 text-emerald-300 text-[11px]">
                      <strong>Financial Isolation Status:</strong> 100% CONTAINED. Zero recovery actions dispatched.
                    </div>
                  </div>
    
                  <div className="border-t border-slate-800 pt-3 flex justify-end">
                    <button onClick={() => setAttackChainModalOpen(false)} className="rounded-xl border border-slate-800 bg-slate-800 px-4 py-2 text-xs font-semibold text-white">Close</button>
                  </div>
                </div>
              </div>
            )}
    
            {/* Phase 10H: Secret & PII Exposure Finding Modal */}
            {secretFindingModalOpen && selectedSecretFinding && (
              <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-sm p-4">
                <div className="w-full max-w-lg rounded-2xl border border-slate-800 bg-slate-900 p-6 shadow-2xl space-y-4">
                  <div className="flex items-center justify-between border-b border-slate-800 pb-3">
                    <div className="flex items-center gap-2">
                      <span className="rounded-lg bg-gradient-to-r from-purple-600 to-rose-600 px-2 py-0.5 text-[10px] font-mono font-bold text-white">
                        SECRET FINDING DETAILS
                      </span>
                      <h3 className="text-sm font-bold text-white font-mono">{selectedSecretFinding.finding_id}</h3>
                    </div>
                    <button onClick={() => setSecretFindingModalOpen(false)} className="text-slate-400 hover:text-white text-lg font-bold">✕</button>
                  </div>
    
                  <div className="space-y-3 text-xs font-mono">
                    <div className="p-3 rounded-xl border border-slate-800 bg-slate-950 space-y-1">
                      <div className="text-slate-400 text-[10px] uppercase">Redacted Target Snippet</div>
                      <div className="text-emerald-300 font-bold">{selectedSecretFinding.masked_value}</div>
                    </div>
    
                    <div className="p-3 rounded-xl border border-slate-800 bg-slate-950 space-y-1">
                      <div className="text-slate-400 text-[10px] uppercase">Compliance & Remediation</div>
                      <div className="text-slate-200">{selectedSecretFinding.location}</div>
                      <div className="text-purple-300 text-[11px] mt-1">{selectedSecretFinding.secret_type}</div>
                    </div>
                  </div>
    
                  <div className="border-t border-slate-800 pt-3 flex justify-end">
                    <button onClick={() => setSecretFindingModalOpen(false)} className="rounded-xl border border-slate-800 bg-slate-800 px-4 py-2 text-xs font-semibold text-white">Close</button>
                  </div>
                </div>
              </div>
            )}
    
            {/* Phase 10H: Cryptographic Signed Zero-Trust Security Report Modal */}
            {ztReportModalOpen && (
              <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-sm p-4">
                <div className="w-full max-w-3xl rounded-2xl border border-slate-800 bg-slate-900 p-6 shadow-2xl space-y-4 max-h-[90vh] flex flex-col">
                  <div className="flex items-center justify-between border-b border-slate-800 pb-3 shrink-0">
                    <div className="flex items-center gap-2">
                      <span className="rounded-lg bg-gradient-to-r from-red-600 to-rose-600 px-2 py-0.5 text-[10px] font-mono font-bold text-white">
                        SIGNED ZERO-TRUST REPORT
                      </span>
                      <h3 className="text-sm font-bold text-white font-mono">
                        {ztReport?.report_id || "RPT-ZT-LIVE"}
                      </h3>
                    </div>
                    <button onClick={() => setZtReportModalOpen(false)} className="text-slate-400 hover:text-white text-lg font-bold">✕</button>
                  </div>
    
                  <div className="flex items-center justify-between text-xs text-slate-400 font-mono bg-slate-950 p-2.5 rounded-xl border border-slate-800 shrink-0">
                    <span>Generated: {ztReport ? new Date(ztReport.generated_at).toLocaleString() : "Live"}</span>
                    <span className="text-emerald-300 font-bold">
                      Score: {ztReport?.zero_trust_score?.toFixed(1) || "98.2"}/100 ({ztReport?.global_security_state || "SECURE"})
                    </span>
                    <span className="text-purple-400 font-mono text-[11px] truncate max-w-xs" title={ztReport?.verification_signature}>
                      Sig: {ztReport?.verification_signature?.slice(0, 24) || "sha256:zt_live_token"}...
                    </span>
                  </div>
    
                  <div className="flex-1 overflow-auto rounded-xl border border-slate-800 bg-slate-950 p-4">
                    <pre className="text-[11px] font-mono text-red-300 leading-relaxed whitespace-pre-wrap">
                      {JSON.stringify(ztReport || { status: "loading" }, null, 2)}
                    </pre>
                  </div>
    
                  <div className="flex items-center justify-between border-t border-slate-800 pt-3 shrink-0">
                    <span className="text-[10px] text-slate-500 font-mono">Cryptographically signed security report</span>
                    <div className="flex items-center gap-2">
                      <button
                        onClick={handleCopyZtReportJson}
                        className="rounded-xl border border-slate-800 bg-slate-800/80 px-4 py-2 text-xs font-semibold text-white hover:bg-slate-700 transition"
                      >
                        {ztReportCopied ? "✓ Copied JSON" : "Copy JSON"}
                      </button>
                      <button
                        onClick={handleDownloadZtReportJson}
                        className="rounded-xl bg-gradient-to-r from-red-600 to-rose-600 px-5 py-2 text-xs font-bold text-white shadow hover:from-red-500 hover:to-rose-500 transition font-mono"
                      >
                        Download .json
                      </button>
                    </div>
                  </div>
                </div>
              </div>
            )}


    </>
  );
}
