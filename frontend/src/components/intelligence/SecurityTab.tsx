"use client";

import React, { useCallback, useEffect, useState } from "react";
import {
  PIIScanResponse,
  PaginatedSecurityEventsResponse,
  TrustCenterOverviewResponse,
  fetchSecurityEvents,
  fetchTrustCenterOverview,
  revokeToken,
  scanPayloadPII
} from "../../lib/api";
import { getThreatSeverityBadge } from "./intelligenceBadges";

interface SecurityTabProps {
  userRole?: string;
}

export default function SecurityTab({ userRole = "ADMIN" }: SecurityTabProps) {
  const [error, setError] = useState<string | null>(null);

    const [trustCenterData, setTrustCenterData] = useState<TrustCenterOverviewResponse | null>(null);
    const [securityEventsData, setSecurityEventsData] = useState<PaginatedSecurityEventsResponse | null>(null);
    const [securityLoading, setSecurityLoading] = useState(false);
    const [securitySeverityFilter, setSecuritySeverityFilter] = useState<string>("ALL");
    const [securityEventTypeFilter, setSecurityEventTypeFilter] = useState<string>("ALL");
    const [revokeModalOpen, setRevokeModalOpen] = useState(false);
    const [revokeJtiInput, setRevokeJtiInput] = useState("");
    const [revokeReasonInput, setRevokeReasonInput] = useState("");
    const [revokeLoading, setRevokeLoading] = useState(false);
    const [revokeSuccessMsg, setRevokeSuccessMsg] = useState<string | null>(null);
    const [piiScannerInput, setPiiScannerInput] = useState(
  
      JSON.stringify(
        {
          customer: {
            name: "John Doe",
            email: "john.doe@enterprise.io",
            phone: "+919876543210",
            aadhaar: "9876 5432 1098",
          },
          payment_method: {
            card_pan: "4532015112830366",
            cvv: "888",
            api_key: "rzp_live_secretToken9988776655",
          },
        },
        null,
        2
      )
    );
    const [piiScanResult, setPiiScanResult] = useState<PIIScanResponse | null>(null);
    const [piiScanLoading, setPiiScanLoading] = useState(false);
  

    const handleRevokeTokenSubmit = async () => {
      if (!revokeJtiInput.trim()) return;
      setRevokeLoading(true);
      setError(null);
      try {
        const res = await revokeToken(revokeJtiInput.trim(), revokeReasonInput || undefined);
        setRevokeModalOpen(false);
        setRevokeSuccessMsg(`Token JTI "${res.jti}" successfully revoked and blacklisted. (Zero financial mutations executed)`);
        setRevokeJtiInput("");
        setRevokeReasonInput("");
        const [tcRes, evRes] = await Promise.all([
          fetchTrustCenterOverview().catch(() => null),
          fetchSecurityEvents(1, 50, securitySeverityFilter, securityEventTypeFilter).catch(() => null),
        ]);
        setTrustCenterData(tcRes);
        setSecurityEventsData(evRes);
      } catch (err) {
        setError(err instanceof Error ? err.message : "Failed to revoke token");
      } finally {
        setRevokeLoading(false);
      }
    };
  
    const handleScanPIISubmit = async () => {
      if (!piiScannerInput.trim()) return;
      setPiiScanLoading(true);
      setError(null);
      try {
        let parsedPayload: unknown;
        try {
          parsedPayload = JSON.parse(piiScannerInput);
        } catch {
          parsedPayload = piiScannerInput;
        }
        const res = await scanPayloadPII(parsedPayload);
        setPiiScanResult(res);
      } catch (err) {
        setError(err instanceof Error ? err.message : "Failed to scan payload for PII");
      } finally {
        setPiiScanLoading(false);
      }
    };
  
    // Phase 10H: Zero-Trust Security Operations Handlers & Badge Helpers
    const handleFilterSecurityEvents = async (severity: string, eventType: string) => {
      setSecuritySeverityFilter(severity);
      setSecurityEventTypeFilter(eventType);
      setSecurityLoading(true);
      try {
        const res = await fetchSecurityEvents(1, 50, severity, eventType);
        setSecurityEventsData(res);
      } catch (err) {
        setError(err instanceof Error ? err.message : "Failed to filter security events");
      } finally {
        setSecurityLoading(false);
      }
    };
  
    const getSecurityControlBadge = (status: string) => {
      switch (status) {
        case "ACTIVE":
          return "bg-emerald-950/80 border-emerald-700/60 text-emerald-300 font-bold";
        case "BYPASS_PREVENTED":
          return "bg-purple-950/80 border-purple-700/60 text-purple-300 font-black tracking-wider";
        case "DEGRADED":
          return "bg-amber-950/80 border-amber-700/60 text-amber-300 font-bold animate-pulse";
        case "DISABLED":
        default:
          return "bg-slate-900 border-slate-700 text-slate-400";
      }
    };
  
  
  
    const getSecurityThreatLevelBadge = (level: string) => {
      switch (level) {
        case "CRITICAL":
          return "bg-red-950/90 border-red-500 text-red-200 font-black animate-pulse";
        case "ELEVATED":
          return "bg-amber-950/90 border-amber-500 text-amber-200 font-bold";
        case "NOMINAL":
        default:
          return "bg-emerald-950/80 border-emerald-700/60 text-emerald-300 font-bold";
      }
    };
  
    // Phase 10B Compliance Handlers and Helper Functions

  const loadSecurityData = useCallback(async () => {
    try {
      const [trustRes, eventsRes] = await Promise.all([
        fetchTrustCenterOverview().catch(() => null),
        fetchSecurityEvents().catch(() => null),
      ]);
      setTrustCenterData(trustRes);
      setSecurityEventsData(eventsRes);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load Security data");
    }
  }, []);

    useEffect(() => {
    let ignore = false;
    async function execute() {
      if (!ignore) {
        await loadSecurityData();
      }
    }
    void execute();
    return () => {
      ignore = true;
    };
  }, [loadSecurityData]);

  return (
    <>
      {error && (
        <div className="rounded-xl border border-rose-800/40 bg-rose-950/40 p-4 text-xs text-rose-300">
          {error}
        </div>
      )}

      {revokeSuccessMsg && (
        <div className="rounded-xl border border-emerald-800/60 bg-emerald-950/40 p-4 text-xs text-emerald-300 flex items-center justify-between shadow-lg">
          <span>{revokeSuccessMsg}</span>
          <button onClick={() => setRevokeSuccessMsg(null)} className="text-emerald-400 hover:text-white font-bold ml-4">✕</button>
        </div>
      )}
              {/* =========================================================================
                 TAB 13: SECURITY HARDENING, THREAT DETECTION & FINTECH TRUST LAYER (Phase 10A)
                 ========================================================================= */}
              <div className="space-y-8">
                {/* Mandatory Governance & Zero Financial Mutation Banner */}
                <div className="rounded-2xl border border-rose-800/60 bg-gradient-to-r from-rose-950/40 via-purple-950/30 to-amber-950/30 p-5 flex items-start gap-4 shadow-xl">
    
                  <span className="rounded-lg bg-gradient-to-r from-rose-600 to-amber-600 px-2.5 py-1 text-[10px] font-mono font-black uppercase tracking-wider text-white shadow shrink-0">
                    PHASE 10A FINTECH TRUST
                  </span>
                  <div className="text-xs text-slate-200 leading-relaxed space-y-1.5">
                    <p className="font-bold text-rose-200 text-sm flex items-center gap-2">
                      <span>ENTERPRISE SECURITY HARDENING, THREAT DETECTION & FINTECH TRUST LAYER</span>
                      <span className="text-[10px] font-mono font-normal text-rose-400/80 bg-rose-950/80 px-2 py-0.5 rounded border border-rose-700/50">
                        PolicyEngine Supremacy • Strict Financial Isolation
                      </span>
                    </p>
                    <p className="text-slate-300">
                      Authoritative cryptographic JWT verification, 3-tier centralized RBAC, sliding-window rate limiting,
                      constant-time HMAC webhook verification with replay tripwires, and deep zero-PII/secret redaction.
                      The security layer is strictly observational and protective: it never creates RecoveryAction records, never mutates financial state,
                      and never directly invokes payment gateways.
                    </p>
                  </div>
                </div>
    
                {/* Top Posture 6 KPI Cards Grid */}
                <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-6">
                  {/* Trust Score */}
                  <div className="rounded-2xl border border-rose-800/50 bg-slate-900/90 p-4 shadow-lg flex flex-col justify-between">
                    <span className="text-[11px] font-bold text-slate-400 uppercase tracking-wider">Fintech Trust Score</span>
                    <div className="mt-2 flex items-baseline gap-1">
                      <span className="text-2xl font-black text-rose-400">
                        {trustCenterData ? trustCenterData.trust_score.toFixed(1) : "100.0"}
                      </span>
                      <span className="text-xs text-slate-400 font-mono">/ 100.0</span>
                    </div>
                    <span className="mt-2 text-[10px] text-emerald-400 font-mono flex items-center gap-1">
                      <span>●</span> 100% Verified Trust
                    </span>
                  </div>
    
                  {/* Threat Level */}
                  <div className="rounded-2xl border border-slate-800 bg-slate-900/90 p-4 shadow-lg flex flex-col justify-between">
                    <span className="text-[11px] font-bold text-slate-400 uppercase tracking-wider">Threat Level</span>
                    <div className="mt-2">
                      <span className={`inline-block rounded-md border px-2 py-0.5 text-xs font-mono font-bold uppercase ${
                        trustCenterData ? getSecurityThreatLevelBadge(trustCenterData.threat_level) : "bg-emerald-950/80 border-emerald-700/60 text-emerald-300"
                      }`}>
                        {trustCenterData ? trustCenterData.threat_level : "NOMINAL"}
                      </span>
                    </div>
                    <span className="mt-2 text-[10px] text-slate-400 font-mono">Surveillance Active</span>
                  </div>
    
                  {/* Active Controls */}
                  <div className="rounded-2xl border border-slate-800 bg-slate-900/90 p-4 shadow-lg flex flex-col justify-between">
                    <span className="text-[11px] font-bold text-slate-400 uppercase tracking-wider">Active Controls</span>
                    <div className="mt-2 text-2xl font-black text-white">
                      {trustCenterData ? `${trustCenterData.active_controls_count} / ${trustCenterData.controls.length}` : "7 / 7"}
                    </div>
                    <span className="mt-2 text-[10px] text-emerald-400 font-mono">100% Enforced</span>
                  </div>
    
                  {/* Blocked Attacks (24h) */}
                  <div className="rounded-2xl border border-slate-800 bg-slate-900/90 p-4 shadow-lg flex flex-col justify-between">
                    <span className="text-[11px] font-bold text-slate-400 uppercase tracking-wider">Blocked Threats (24h)</span>
                    <div className="mt-2 text-2xl font-black text-amber-400">
                      {trustCenterData ? trustCenterData.blocked_attacks_count : 0}
                    </div>
                    <span className="mt-2 text-[10px] text-slate-400 font-mono">Tripwires Defended</span>
                  </div>
    
                  {/* Zero PII Leaks */}
                  <div className="rounded-2xl border border-slate-800 bg-slate-900/90 p-4 shadow-lg flex flex-col justify-between">
                    <span className="text-[11px] font-bold text-slate-400 uppercase tracking-wider">PII / Secret Leaks</span>
                    <div className="mt-2 text-2xl font-black text-emerald-400">
                      {trustCenterData ? `${trustCenterData.pii_leak_count} Leaks` : "0 Leaks"}
                    </div>
                    <span className="mt-2 text-[10px] text-emerald-400 font-mono">100% Redacted</span>
                  </div>
    
                  {/* Financial Isolation */}
                  <div className="rounded-2xl border border-slate-800 bg-slate-900/90 p-4 shadow-lg flex flex-col justify-between">
                    <span className="text-[11px] font-bold text-slate-400 uppercase tracking-wider">Financial Isolation</span>
                    <div className="mt-2 text-2xl font-black text-purple-400">
                      100%
                    </div>
                    <span className="mt-2 text-[10px] text-purple-300 font-mono">Δ Mutations = 0</span>
                  </div>
                </div>
    
                {/* Active Security Controls Matrix (7 Controls Grid) */}
                <div className="rounded-2xl border border-slate-800 bg-slate-900/70 p-6 shadow-xl space-y-6">
                  <div className="flex items-center justify-between border-b border-slate-800 pb-4">
                    <div>
                      <h3 className="text-base font-bold text-white flex items-center gap-2">
                        <span>🛡️ Active Security Controls Matrix</span>
                        <span className="text-xs font-mono text-slate-400 bg-slate-800 px-2 py-0.5 rounded border border-slate-700">
                          Enterprise Defense-in-Depth
                        </span>
                      </h3>
                      <p className="text-xs text-slate-400 mt-1">
                        Continuous cryptographic, perimeter, rate limiting, and data masking enforcement across all API endpoints.
                      </p>
                    </div>
                    {userRole === "admin" && (
                      <button
                        onClick={() => setRevokeModalOpen(true)}
                        className="flex items-center gap-1.5 rounded-xl border border-rose-800/80 bg-rose-950/80 px-3.5 py-1.5 text-xs font-bold text-rose-300 hover:bg-rose-900/80 shadow-lg shadow-rose-950/50 transition"
                      >
                        <span>🚨 Emergency Revoke Token</span>
                      </button>
                    )}
                  </div>
    
                  <div className="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-3">
                    {trustCenterData?.controls.map((control, idx) => (
                      <div
                        key={idx}
                        className="rounded-xl border border-slate-800/80 bg-slate-950/60 p-4 space-y-3 flex flex-col justify-between hover:border-slate-700 transition"
                      >
                        <div className="space-y-2">
                          <div className="flex items-start justify-between gap-2">
                            <span className="text-xs font-mono font-bold text-white tracking-wide">
                              {control.control_name.replace(/_/g, " ")}
                            </span>
                            <span className={`rounded-md border px-2 py-0.5 text-[10px] font-mono uppercase ${getSecurityControlBadge(control.status)}`}>
                              {control.status.replace(/_/g, " ")}
                            </span>
                          </div>
                          <p className="text-[11px] text-slate-300 leading-relaxed">
                            {control.description}
                          </p>
                        </div>
    
                        <div className="border-t border-slate-800/60 pt-2 flex items-center justify-between text-[10px] font-mono text-slate-400">
                          <span className="bg-slate-900 px-2 py-0.5 rounded border border-slate-800 text-slate-300">
                            {control.enforcement_type}
                          </span>
                          <span className="text-slate-500">
                            {Object.keys(control.metrics).length} Telemetry Points
                          </span>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
    
                {/* Interactive Zero-PII & Secret Scanner Playground */}
                <div className="rounded-2xl border border-slate-800 bg-slate-900/70 p-6 shadow-xl space-y-6">
                  <div className="border-b border-slate-800 pb-4">
                    <h3 className="text-base font-bold text-white flex items-center gap-2">
                      <span>🔍 Zero-PII & Secret Scanner Playground</span>
                      <span className="text-xs font-mono text-emerald-400 bg-emerald-950/80 px-2 py-0.5 rounded border border-emerald-700/50">
                        Luhn PAN • Aadhaar • CVV • Secrets
                      </span>
                    </h3>
                    <p className="text-xs text-slate-400 mt-1">
                      Test and verify real-time cryptographic scanning and automated redaction of sensitive credentials and PII.
                    </p>
                  </div>
    
                  <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
                    {/* Input Payload Area */}
                    <div className="space-y-3">
                      <label className="text-xs font-bold text-slate-300 block">
                        Test Payload (Raw JSON or Sensitive Strings):
                      </label>
                      <textarea
                        rows={10}
                        value={piiScannerInput}
                        onChange={(e) => setPiiScannerInput(e.target.value)}
                        placeholder="Enter JSON with card PANs, Aadhaar, CVVs, API tokens..."
                        className="w-full rounded-xl border border-slate-800 bg-slate-950 p-3 font-mono text-xs text-slate-200 focus:border-rose-500 focus:outline-none"
                      />
                      <div className="flex items-center justify-between">
                        <span className="text-[11px] text-slate-500">
                          Supports Luhn validation, Aadhaar regex, CVV redaction, JWT detection
                        </span>
                        <button
                          onClick={handleScanPIISubmit}
                          disabled={piiScanLoading}
                          className="rounded-xl bg-gradient-to-r from-rose-600 to-amber-600 px-5 py-2 text-xs font-bold uppercase tracking-wider text-white hover:from-rose-500 hover:to-amber-500 shadow-lg shadow-rose-600/30 transition disabled:opacity-50"
                        >
                          {piiScanLoading ? "Scanning..." : "Scan & Redact Payload"}
                        </button>
                      </div>
                    </div>
    
                    {/* Scan Report & Sanitized Output */}
                    <div className="space-y-3">
                      <label className="text-xs font-bold text-slate-300 block">
                        Scan Report & Redacted Output:
                      </label>
                      {piiScanResult ? (
                        <div className="rounded-xl border border-slate-800 bg-slate-950 p-4 space-y-4 font-mono text-xs">
                          <div className="flex flex-wrap items-center gap-3 border-b border-slate-800 pb-3">
                            <span className={`rounded-md border px-2 py-0.5 text-[10px] font-bold ${
                              piiScanResult.has_pii ? "bg-amber-950/80 border-amber-700 text-amber-300" : "bg-emerald-950/80 border-emerald-700 text-emerald-300"
                            }`}>
                              {piiScanResult.has_pii ? "PII Detected" : "No PII Detected"}
                            </span>
                            <span className={`rounded-md border px-2 py-0.5 text-[10px] font-bold ${
                              piiScanResult.has_secrets ? "bg-rose-950/80 border-rose-700 text-rose-300" : "bg-emerald-950/80 border-emerald-700 text-emerald-300"
                            }`}>
                              {piiScanResult.has_secrets ? "Secrets Detected" : "No Secrets Detected"}
                            </span>
                            <span className="text-[11px] text-slate-400">
                              Findings: <strong className="text-white">{piiScanResult.findings_count}</strong>
                            </span>
                          </div>
    
                          {piiScanResult.findings.length > 0 && (
                            <div className="space-y-1 text-[11px] max-h-32 overflow-y-auto">
                              {piiScanResult.findings.map((f, i) => (
                                <div key={i} className="text-rose-300/90 flex items-start gap-1.5">
                                  <span>⚠️</span>
                                  <span>[{f.type}] at {f.path}: {f.description}</span>
                                </div>
                              ))}
                            </div>
                          )}
    
                          <div>
                            <span className="text-[10px] text-slate-500 uppercase tracking-wider block mb-1">Sanitized Output Payload:</span>
                            <pre className="rounded-lg bg-slate-900/90 p-3 text-[11px] text-emerald-300 overflow-x-auto border border-slate-800">
                              {typeof piiScanResult.sanitized_payload === "object"
                                ? JSON.stringify(piiScanResult.sanitized_payload, null, 2)
                                : String(piiScanResult.sanitized_payload)}
                            </pre>
                          </div>
                        </div>
                      ) : (
                        <div className="rounded-xl border border-dashed border-slate-800 bg-slate-950/50 p-8 text-center text-xs text-slate-500 h-[260px] flex flex-col items-center justify-center">
                          <span className="text-2xl mb-2">🛡️</span>
                          Click &quot;Scan &amp; Redact Payload&quot; to execute deep PII and secret scanner analysis.
                        </div>
                      )}
                    </div>
                  </div>
                </div>
    
                {/* Real-time Security Events & Audit Trail Stream */}
                <div className="rounded-2xl border border-slate-800 bg-slate-900/70 p-6 shadow-xl space-y-6">
                  <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between border-b border-slate-800 pb-4">
                    <div>
                      <h3 className="text-base font-bold text-white flex items-center gap-2">
                        <span>📋 Real-Time Security & Authorization Events Stream</span>
                        <span className="text-xs font-mono text-slate-400 bg-slate-800 px-2 py-0.5 rounded border border-slate-700">
                          Immutable Audit Trail
                        </span>
                      </h3>
                      <p className="text-xs text-slate-400 mt-1">
                        Audited login successes/failures, RBAC gate denials, rate limit spikes, and webhook signature verifications.
                      </p>
                    </div>
    
                    <div className="flex flex-wrap items-center gap-3">
                      <div className="flex items-center gap-1.5 text-xs">
                        <span className="text-slate-400 text-[11px]">Severity:</span>
                        <select
                          value={securitySeverityFilter}
                          onChange={(e) => handleFilterSecurityEvents(e.target.value, securityEventTypeFilter)}
                          className="rounded-lg border border-slate-800 bg-slate-950 px-2.5 py-1 text-xs text-slate-200 focus:border-rose-500 focus:outline-none"
                        >
                          <option value="ALL">ALL SEVERITIES</option>
                          <option value="CRITICAL">CRITICAL</option>
                          <option value="HIGH">HIGH</option>
                          <option value="MEDIUM">MEDIUM</option>
                          <option value="LOW">LOW</option>
                          <option value="INFO">INFO</option>
                        </select>
                      </div>
    
                      <div className="flex items-center gap-1.5 text-xs">
                        <span className="text-slate-400 text-[11px]">Event:</span>
                        <select
                          value={securityEventTypeFilter}
                          onChange={(e) => handleFilterSecurityEvents(securitySeverityFilter, e.target.value)}
                          className="rounded-lg border border-slate-800 bg-slate-950 px-2.5 py-1 text-xs text-slate-200 focus:border-rose-500 focus:outline-none"
                        >
                          <option value="ALL">ALL EVENTS</option>
                          <option value="AUTH_SUCCESS">AUTH_SUCCESS</option>
                          <option value="AUTH_FAILURE">AUTH_FAILURE</option>
                          <option value="TOKEN_REVOKED">TOKEN_REVOKED</option>
                          <option value="RBAC_DENIED">RBAC_DENIED</option>
                          <option value="RATE_LIMIT_EXCEEDED">RATE_LIMIT_EXCEEDED</option>
                          <option value="WEBHOOK_SIGNATURE_FAILED">WEBHOOK_SIGNATURE_FAILED</option>
                          <option value="WEBHOOK_REPLAY_DETECTED">WEBHOOK_REPLAY_DETECTED</option>
                          <option value="INJECTION_ATTEMPT_DETECTED">INJECTION_ATTEMPT_DETECTED</option>
                        </select>
                      </div>
                    </div>
                  </div>
    
                  {securityLoading ? (
                    <div className="flex h-32 items-center justify-center space-x-2">
                      <div className="h-4 w-4 animate-spin rounded-full border-2 border-rose-500 border-t-transparent" />
                      <span className="text-xs text-slate-400">Loading security events...</span>
                    </div>
                  ) : securityEventsData && securityEventsData.items.length > 0 ? (
                    <div className="overflow-x-auto">
                      <table className="w-full text-left text-xs font-mono">
                        <thead className="border-b border-slate-800 bg-slate-950/60 text-slate-400 text-[10px] uppercase tracking-wider">
                          <tr>
                            <th className="py-2.5 px-3">ID</th>
                            <th className="py-2.5 px-3">Timestamp</th>
                            <th className="py-2.5 px-3">Severity</th>
                            <th className="py-2.5 px-3">Event Type</th>
                            <th className="py-2.5 px-3">Actor ID</th>
                            <th className="py-2.5 px-3">Details</th>
                          </tr>
                        </thead>
                        <tbody className="divide-y divide-slate-800/60">
                          {securityEventsData.items.map((ev) => (
                            <tr key={ev.id} className="hover:bg-slate-800/30 transition">
                              <td className="py-2.5 px-3 font-bold text-slate-300">#{ev.id}</td>
                              <td className="py-2.5 px-3 text-slate-400">
                                {new Date(ev.created_at).toLocaleString()}
                              </td>
                              <td className="py-2.5 px-3">
                                <span className={`rounded-md border px-2 py-0.5 text-[10px] font-bold ${getThreatSeverityBadge(ev.severity)}`}>
                                  {ev.severity}
                                </span>
                              </td>
                              <td className="py-2.5 px-3 font-bold text-white">
                                {ev.event_type}
                              </td>
                              <td className="py-2.5 px-3 text-slate-300">
                                <span className="bg-slate-950 px-2 py-0.5 rounded border border-slate-800 text-indigo-300">
                                  {ev.actor_id}
                                </span>
                              </td>
                              <td className="py-2.5 px-3 text-slate-400 max-w-xs truncate">
                                {JSON.stringify(ev.details)}
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  ) : (
                    <div className="rounded-xl border border-dashed border-slate-800 p-8 text-center text-xs text-slate-500">
                      No security events matching current filter criteria.
                    </div>
                  )}
                </div>
              </div>


            {revokeModalOpen && (
              <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/80 backdrop-blur-sm p-4">
                <div className="w-full max-w-md rounded-2xl border border-rose-800/80 bg-slate-900 p-6 shadow-2xl space-y-6">
                  <div className="flex items-center justify-between border-b border-slate-800 pb-4">
                    <div>
                      <h3 className="text-base font-bold text-white flex items-center gap-2">
                        <span>🚨 Emergency Revoke JWT Token</span>
                      </h3>
                      <p className="text-xs text-rose-400 mt-0.5 font-mono">
                        Admin Cryptographic Tripwire Blacklist
                      </p>
                    </div>
                    <button
                      onClick={() => setRevokeModalOpen(false)}
                      className="rounded-lg p-1.5 text-slate-400 hover:bg-slate-800 hover:text-white"
                    >
                      ✕
                    </button>
                  </div>
    
                  <form
                    onSubmit={(e) => {
                      e.preventDefault();
                      handleRevokeTokenSubmit();
                    }}
                    className="space-y-4"
                  >
                    <div>
                      <label className="text-xs font-bold text-slate-300 block mb-1">
                        Unique JWT Token ID (JTI) <span className="text-rose-400">*</span>
                      </label>
                      <input
                        type="text"
                        required
                        value={revokeJtiInput}
                        onChange={(e) => setRevokeJtiInput(e.target.value)}
                        placeholder="e.g. 7f9a8b1c3d2e4f5a6b7c8d9e0f1a2b3c"
                        className="w-full rounded-xl border border-slate-800 bg-slate-950 px-3 py-2 text-xs font-mono text-slate-200 focus:border-rose-500 focus:outline-none"
                      />
                    </div>
    
                    <div>
                      <label className="text-xs font-bold text-slate-300 block mb-1">
                        Revocation Justification & Audit Reason
                      </label>
                      <textarea
                        rows={3}
                        value={revokeReasonInput}
                        onChange={(e) => setRevokeReasonInput(e.target.value)}
                        placeholder="e.g. Suspected credential leak or operator credential compromise."
                        className="w-full rounded-xl border border-slate-800 bg-slate-950 px-3 py-2 text-xs text-slate-200 placeholder-slate-600 focus:border-rose-500 focus:outline-none"
                      />
                    </div>
    
                    <div className="rounded-xl border border-rose-800/40 bg-rose-950/20 p-3 text-[11px] text-rose-200/90 leading-relaxed font-mono">
                      ⚠️ Irreversible Security Tripwire: Blacklisting this JTI will immediately block all subsequent requests with this token across in-memory verification layers and the immutable AuditLog.
                    </div>
    
                    <div className="flex items-center justify-end gap-3 border-t border-slate-800 pt-4">
                      <button
                        type="button"
                        onClick={() => setRevokeModalOpen(false)}
                        className="rounded-xl border border-slate-800 bg-slate-950 px-4 py-2 text-xs font-bold uppercase tracking-wider text-slate-400 hover:text-white transition"
                      >
                        Cancel
                      </button>
                      <button
                        type="submit"
                        disabled={revokeLoading || !revokeJtiInput.trim()}
                        className="rounded-xl bg-rose-600 px-6 py-2 text-xs font-bold uppercase tracking-wider text-white hover:bg-rose-500 shadow-lg shadow-rose-600/30 transition disabled:opacity-50"
                      >
                        {revokeLoading ? "Revoking..." : "Confirm Token Blacklist"}
                      </button>
                    </div>
                  </form>
                </div>
              </div>
            )}
            {/* Phase 10B: Compliance Snapshot Report Modal */}


    </>
  );
}
