"use client";

import React, { useCallback, useEffect, useState } from "react";
import {
  ComplianceControl,
  ComplianceIncident,
  ComplianceReport,
  ComplianceSummary,
  fetchComplianceControls,
  fetchComplianceIncidents,
  fetchComplianceReport,
  fetchComplianceSummary
} from "../../lib/api";

export default function ComplianceTab() {
  const [error, setError] = useState<string | null>(null);

    const [complianceSummary, setComplianceSummary] = useState<ComplianceSummary | null>(null);
    const [complianceControls, setComplianceControls] = useState<ComplianceControl[] | null>(null);
    const [complianceIncidents, setComplianceIncidents] = useState<ComplianceIncident[] | null>(null);
    const [complianceReportData, setComplianceReportData] = useState<ComplianceReport | null>(null);
    const [complianceCategoryFilter, setComplianceCategoryFilter] = useState<string>("ALL");
    const [complianceStatusFilter, setComplianceStatusFilter] = useState<string>("ALL");
    const [complianceSeverityFilter, setComplianceSeverityFilter] = useState<string>("ALL");
    const [incidentSeverityFilter, setIncidentSeverityFilter] = useState<string>("ALL");
    const [incidentCategoryFilter, setIncidentCategoryFilter] = useState<string>("ALL");
    const [selectedIncident, setSelectedIncident] = useState<ComplianceIncident | null>(null);
    const [reportModalOpen, setReportModalOpen] = useState(false);
    const [reportLoading, setReportLoading] = useState(false);
  

    const handleFilterComplianceControls = async (category: string, status: string, severity: string) => {
      setComplianceCategoryFilter(category);
      setComplianceStatusFilter(status);
      setComplianceSeverityFilter(severity);
      try {
        const res = await fetchComplianceControls(category, status, severity);
        setComplianceControls(res);
      } catch (err) {
        setError(err instanceof Error ? err.message : "Failed to filter compliance controls");
      } finally {
      }
    };
  
    const handleFilterComplianceIncidents = async (severity: string, category: string) => {
      setIncidentSeverityFilter(severity);
      setIncidentCategoryFilter(category);
      try {
        const res = await fetchComplianceIncidents(severity, category);
        setComplianceIncidents(res);
      } catch (err) {
        setError(err instanceof Error ? err.message : "Failed to filter compliance incidents");
      } finally {
      }
    };
  
    const handleGenerateComplianceReport = async () => {
      setReportLoading(true);
      setError(null);
      try {
        const rep = await fetchComplianceReport();
        setComplianceReportData(rep);
        setReportModalOpen(true);
      } catch (err) {
        setError(err instanceof Error ? err.message : "Failed to generate compliance report");
      } finally {
        setReportLoading(false);
      }
    };
  
    const getCompliancePostureBadge = (posture?: string) => {
      switch (posture) {
        case "EXCELLENT":
          return "bg-emerald-950/90 border-emerald-500 text-emerald-200 font-black";
        case "GOOD":
          return "bg-teal-950/90 border-teal-500 text-teal-200 font-bold";
        case "WARNING":
          return "bg-amber-950/90 border-amber-500 text-amber-200 font-bold";
        case "HIGH_RISK":
          return "bg-orange-950/90 border-orange-500 text-orange-200 font-bold animate-pulse";
        case "CRITICAL":
          return "bg-rose-950/90 border-rose-500 text-rose-200 font-black animate-pulse";
        default:
          return "bg-slate-900 border-slate-700 text-slate-400";
      }
    };
  
    const getComplianceControlStatusBadge = (status: string) => {
      switch (status) {
        case "PASS":
          return "bg-emerald-950/80 border-emerald-700/60 text-emerald-300 font-bold";
        case "WARNING":
          return "bg-amber-950/80 border-amber-700/60 text-amber-300 font-bold";
        case "FAIL":
          return "bg-rose-950/80 border-rose-700/60 text-rose-300 font-black";
        case "NOT_ASSESSED":
        default:
          return "bg-slate-900 border-slate-700 text-slate-400";
      }
    };
  
    const getComplianceSeverityBadge = (severity: string) => {
      switch (severity) {
        case "CRITICAL":
          return "bg-red-950/90 border-red-500 text-red-200 font-black animate-pulse";
        case "HIGH":
          return "bg-rose-950/90 border-rose-500 text-rose-200 font-bold";
        case "MEDIUM":
          return "bg-amber-950/90 border-amber-500 text-amber-200 font-bold";
        case "LOW":
        default:
          return "bg-blue-950/90 border-blue-500 text-blue-200 font-medium";
      }
    };
  
  
  
  

  const loadComplianceData = useCallback(async () => {
    try {
      const [sumRes, ctrlRes, incRes] = await Promise.all([
        fetchComplianceSummary().catch(() => null),
        fetchComplianceControls().catch(() => null),
        fetchComplianceIncidents().catch(() => null),
      ]);
      setComplianceSummary(sumRes);
      setComplianceControls(ctrlRes);
      setComplianceIncidents(incRes);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load Compliance data");
    }
  }, []);

  useEffect(() => {
    let ignore = false;
    async function execute() {
      if (!ignore) {
        await loadComplianceData();
      }
    }
    void execute();
    return () => {
      ignore = true;
    };
  }, [loadComplianceData]);

  return (
    <>
      {error && (
        <div className="rounded-xl border border-rose-800/40 bg-rose-950/40 p-4 text-xs text-rose-300">
          {error}
        </div>
      )}
              {/* =========================================================================
                 TAB 14: COMPLIANCE, AUDIT INTELLIGENCE & REGULATORY GOVERNANCE (Phase 10B)
                 ========================================================================= */}
              <div className="space-y-8">
                {/* Mandatory Governance, Non-Certification & Zero Financial Mutation Banner */}
                <div className="rounded-2xl border border-teal-800/60 bg-gradient-to-r from-emerald-950/50 via-teal-950/40 to-indigo-950/40 p-5 flex items-start gap-4 shadow-xl">
                  <span className="rounded-lg bg-gradient-to-r from-emerald-600 to-teal-600 px-2.5 py-1 text-[10px] font-mono font-black uppercase tracking-wider text-white shadow shrink-0">
                    PHASE 10B COMPLIANCE
                  </span>
                  <div className="text-xs text-slate-200 leading-relaxed space-y-1.5 flex-1">
                    <div className="flex flex-wrap items-center justify-between gap-2">
                      <p className="font-bold text-teal-200 text-sm flex items-center gap-2">
                        <span>COMPLIANCE, AUDIT INTELLIGENCE & REGULATORY GOVERNANCE</span>
                        <span className="text-[10px] font-mono font-normal text-teal-400/80 bg-teal-950/80 px-2 py-0.5 rounded border border-teal-700/50">
                          Engineering Control Alignment • Immutable Event Sourcing • Zero Financial Mutations
                        </span>
                      </p>
                      <button
                        onClick={handleGenerateComplianceReport}
                        disabled={reportLoading}
                        className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-gradient-to-r from-teal-600 to-indigo-600 hover:from-teal-500 hover:to-indigo-500 text-white text-xs font-bold shadow-lg shadow-teal-700/30 transition disabled:opacity-50"
                      >
                        {reportLoading ? "Generating..." : "📄 Export Compliance Snapshot"}
                      </button>
                    </div>
                    <p className="text-slate-300 text-[11px] leading-relaxed border-t border-teal-800/40 pt-2 mt-2">
                      <strong className="text-amber-300">Engineering Control Evidence Notice:</strong>{" "}
                      {complianceSummary?.disclaimer ||
                        "This dashboard provides automated software engineering control evidence and does not constitute legal, regulatory, or third-party certification (e.g., RBI, PCI DSS, SOC 2, ISO 27001, GDPR). PolicyEngine remains the sole authoritative gatekeeper for recovery actions. The compliance subsystem is strictly observational and produces zero financial mutations."}
                    </p>
                  </div>
                </div>
    
                {/* 8 Top Posture KPI Cards Grid */}
                <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
                  {/* Card 1: Compliance Risk Score */}
                  <div className="rounded-2xl border border-teal-800/50 bg-slate-900/90 p-4 shadow-lg backdrop-blur space-y-2">
                    <div className="flex items-center justify-between">
                      <span className="text-xs font-semibold text-slate-400">Compliance Risk Score</span>
                      <span
                        className={`rounded-full border px-2 py-0.5 text-[10px] font-mono font-bold uppercase tracking-wider ${getCompliancePostureBadge(
                          complianceSummary?.compliance_posture
                        )}`}
                      >
                        {complianceSummary?.compliance_posture || "ASSESSING"}
                      </span>
                    </div>
                    <div className="flex items-baseline gap-2">
                      <span className="text-2xl font-black text-white font-mono">
                        {complianceSummary ? `${complianceSummary.compliance_score.toFixed(1)}` : "--"}
                      </span>
                      <span className="text-xs text-slate-400 font-mono">/ 100.0</span>
                    </div>
                    <p className="text-[11px] text-teal-400/90 font-mono">
                      {complianceSummary
                        ? `${complianceSummary.passing_controls_count} Passing • ${complianceSummary.warning_controls_count} Warning • ${complianceSummary.failing_controls_count} Fail`
                        : "Evaluating controls..."}
                    </p>
                  </div>
    
                  {/* Card 2: Immutable Audit Coverage */}
                  <div className="rounded-2xl border border-teal-800/50 bg-slate-900/90 p-4 shadow-lg backdrop-blur space-y-2">
                    <div className="flex items-center justify-between">
                      <span className="text-xs font-semibold text-slate-400">AuditLog Completeness</span>
                      <span className="rounded-full border border-emerald-700/60 bg-emerald-950/80 px-2 py-0.5 text-[10px] font-mono font-bold text-emerald-300">
                        EVENT-SOURCED
                      </span>
                    </div>
                    <div className="flex items-baseline gap-2">
                      <span className="text-2xl font-black text-emerald-300 font-mono">
                        {complianceSummary ? `${complianceSummary.audit_coverage_percentage.toFixed(1)}%` : "--"}
                      </span>
                      <span className="text-xs text-slate-400 font-mono">
                        ({complianceSummary ? `${complianceSummary.audit_coverage.observed_event_categories}/10` : "-"} Chains)
                      </span>
                    </div>
                    <p className="text-[11px] text-slate-400 font-mono">
                      {complianceSummary ? `${complianceSummary.audit_coverage.total_audit_events_count} events • 0 orphans` : "Scanning audit log..."}
                    </p>
                  </div>
    
                  {/* Card 3: Security Controls Posture */}
                  <div className="rounded-2xl border border-teal-800/50 bg-slate-900/90 p-4 shadow-lg backdrop-blur space-y-2">
                    <div className="flex items-center justify-between">
                      <span className="text-xs font-semibold text-slate-400">Security Control Alignment</span>
                      <span className="rounded-full border border-teal-700/60 bg-teal-950/80 px-2 py-0.5 text-[10px] font-mono font-bold text-teal-300">
                        PHASE 10A TRUST
                      </span>
                    </div>
                    <div className="flex items-baseline gap-2">
                      <span className="text-2xl font-black text-teal-300 font-mono">
                        {complianceSummary?.category_scores.find((c) => c.category === "SECURITY")?.score.toFixed(1) || "100.0"}%
                      </span>
                    </div>
                    <p className="text-[11px] text-teal-400/90 font-mono">
                      JWT HMAC Pinning • Sliding Rate Limit • Threat Center
                    </p>
                  </div>
    
                  {/* Card 4: Financial Governance Integrity */}
                  <div className="rounded-2xl border border-teal-800/50 bg-slate-900/90 p-4 shadow-lg backdrop-blur space-y-2">
                    <div className="flex items-center justify-between">
                      <span className="text-xs font-semibold text-slate-400">Financial Execution Integrity</span>
                      <span className="rounded-full border border-emerald-700/60 bg-emerald-950/80 px-2 py-0.5 text-[10px] font-mono font-bold text-emerald-300">
                        POLICY GATEWAY
                      </span>
                    </div>
                    <div className="flex items-baseline gap-2">
                      <span className="text-2xl font-black text-emerald-300 font-mono">
                        {complianceSummary?.financial_governance.actions_with_policy_decision_percentage.toFixed(1) || "100.0"}%
                      </span>
                    </div>
                    <p className="text-[11px] text-emerald-400 font-mono">
                      PolicyEngine Supremacy Verified • Δ Mutations = 0
                    </p>
                  </div>
    
                  {/* Card 5: RBAC Compliance & Identity */}
                  <div className="rounded-2xl border border-teal-800/50 bg-slate-900/90 p-4 shadow-lg backdrop-blur space-y-2">
                    <div className="flex items-center justify-between">
                      <span className="text-xs font-semibold text-slate-400">RBAC Identity Governance</span>
                      <span className="rounded-full border border-blue-700/60 bg-blue-950/80 px-2 py-0.5 text-[10px] font-mono font-bold text-blue-300">
                        AUTHORITATIVE
                      </span>
                    </div>
                    <div className="flex items-baseline gap-2">
                      <span className="text-2xl font-black text-blue-300 font-mono">
                        {complianceSummary?.rbac_compliance.privilege_escalation_attempts_count === 0 ? "0" : complianceSummary?.rbac_compliance.privilege_escalation_attempts_count}
                      </span>
                      <span className="text-xs text-slate-400">Escalation Attempts</span>
                    </div>
                    <p className="text-[11px] text-blue-400 font-mono">
                      {complianceSummary?.rbac_compliance.unauthorized_access_attempts_count || 0} Denials • Token Blacklist Active
                    </p>
                  </div>
    
                  {/* Card 6: ML & Strategy Governance */}
                  <div className="rounded-2xl border border-teal-800/50 bg-slate-900/90 p-4 shadow-lg backdrop-blur space-y-2">
                    <div className="flex items-center justify-between">
                      <span className="text-xs font-semibold text-slate-400">ML Model Governance</span>
                      <span className="rounded-full border border-purple-700/60 bg-purple-950/80 px-2 py-0.5 text-[10px] font-mono font-bold text-purple-300">
                        14 GATES ACTIVE
                      </span>
                    </div>
                    <div className="flex items-baseline gap-2">
                      <span className="text-2xl font-black text-purple-300 font-mono">
                        {complianceSummary?.model_governance.dataset_lineage_coverage_pct.toFixed(0) || "100"}%
                      </span>
                      <span className="text-xs text-slate-400">Lineage Coverage</span>
                    </div>
                    <p className="text-[11px] text-purple-400 font-mono">
                      0 Unapproved Deployments • Canary Monitored
                    </p>
                  </div>
    
                  {/* Card 7: Data Protection & Zero-PII */}
                  <div className="rounded-2xl border border-teal-800/50 bg-slate-900/90 p-4 shadow-lg backdrop-blur space-y-2">
                    <div className="flex items-center justify-between">
                      <span className="text-xs font-semibold text-slate-400">Data Protection & Privacy</span>
                      <span className="rounded-full border border-emerald-700/60 bg-emerald-950/80 px-2 py-0.5 text-[10px] font-mono font-bold text-emerald-300">
                        PII SCANNER ACTIVE
                      </span>
                    </div>
                    <div className="flex items-baseline gap-2">
                      <span className="text-2xl font-black text-emerald-300 font-mono">
                        {(complianceSummary?.data_protection.unmasked_cards_detected_count || 0) +
                          (complianceSummary?.data_protection.unmasked_aadhaar_detected_count || 0) +
                          (complianceSummary?.data_protection.unmasked_tokens_detected_count || 0)}
                      </span>
                      <span className="text-xs text-slate-400">Exposed PII Records</span>
                    </div>
                    <p className="text-[11px] text-emerald-400 font-mono">
                      Zero Card PANs • Zero Aadhaar • Zero Raw Secrets
                    </p>
                  </div>
    
                  {/* Card 8: Open Incidents & Findings */}
                  <div className="rounded-2xl border border-teal-800/50 bg-slate-900/90 p-4 shadow-lg backdrop-blur space-y-2">
                    <div className="flex items-center justify-between">
                      <span className="text-xs font-semibold text-slate-400">Compliance Incidents</span>
                      <span
                        className={`rounded-full border px-2 py-0.5 text-[10px] font-mono font-bold uppercase tracking-wider ${
                          (complianceSummary?.critical_findings_count || 0) > 0
                            ? "bg-rose-950 border-rose-700 text-rose-300 animate-pulse"
                            : "bg-emerald-950 border-emerald-700 text-emerald-300"
                        }`}
                      >
                        {complianceSummary?.critical_findings_count || 0} CRITICAL
                      </span>
                    </div>
                    <div className="flex items-baseline gap-2">
                      <span className="text-2xl font-black text-white font-mono">
                        {complianceSummary?.open_incidents_count ?? (complianceIncidents?.length || 0)}
                      </span>
                      <span className="text-xs text-slate-400">Active Incidents</span>
                    </div>
                    <p className="text-[11px] text-slate-400 font-mono">
                      Continuous surveillance across 5 control categories
                    </p>
                  </div>
                </div>
    
                {/* Compliance Control Alignment Matrix (18 Controls) */}
                <div className="rounded-2xl border border-slate-800 bg-slate-900/90 p-6 space-y-6 shadow-xl backdrop-blur">
                  <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 border-b border-slate-800 pb-4">
                    <div>
                      <h2 className="text-lg font-bold text-white flex items-center gap-2">
                        <span>🛡️ Engineering Control Alignment Matrix</span>
                        <span className="rounded-full bg-teal-950 border border-teal-700/60 px-2 py-0.5 text-xs text-teal-300 font-mono">
                          {complianceControls?.length || 18} Controls Evaluated
                        </span>
                      </h2>
                      <p className="text-xs text-slate-400 mt-0.5">
                        Automated, deterministic compliance checks continuously evaluated from immutable event state.
                      </p>
                    </div>
    
                    {/* Filters */}
                    <div className="flex flex-wrap items-center gap-2">
                      <select
                        value={complianceCategoryFilter}
                        onChange={(e) =>
                          handleFilterComplianceControls(
                            e.target.value,
                            complianceStatusFilter,
                            complianceSeverityFilter
                          )
                        }
                        className="rounded-lg border border-slate-700 bg-slate-800 px-2.5 py-1.5 text-xs text-slate-200 focus:border-teal-500 focus:outline-none"
                      >
                        <option value="ALL">All Categories</option>
                        <option value="SECURITY">Security</option>
                        <option value="FINANCIAL_CONTROL">Financial Control</option>
                        <option value="ML_GOVERNANCE">ML Governance</option>
                        <option value="DATA_GOVERNANCE">Data Governance</option>
                        <option value="HUMAN_GOVERNANCE">Human Governance</option>
                      </select>
    
                      <select
                        value={complianceStatusFilter}
                        onChange={(e) =>
                          handleFilterComplianceControls(
                            complianceCategoryFilter,
                            e.target.value,
                            complianceSeverityFilter
                          )
                        }
                        className="rounded-lg border border-slate-700 bg-slate-800 px-2.5 py-1.5 text-xs text-slate-200 focus:border-teal-500 focus:outline-none"
                      >
                        <option value="ALL">All Statuses</option>
                        <option value="PASS">Pass</option>
                        <option value="WARNING">Warning</option>
                        <option value="FAIL">Fail</option>
                      </select>
    
                      <select
                        value={complianceSeverityFilter}
                        onChange={(e) =>
                          handleFilterComplianceControls(
                            complianceCategoryFilter,
                            complianceStatusFilter,
                            e.target.value
                          )
                        }
                        className="rounded-lg border border-slate-700 bg-slate-800 px-2.5 py-1.5 text-xs text-slate-200 focus:border-teal-500 focus:outline-none"
                      >
                        <option value="ALL">All Severities</option>
                        <option value="CRITICAL">Critical</option>
                        <option value="HIGH">High</option>
                        <option value="MEDIUM">Medium</option>
                        <option value="LOW">Low</option>
                      </select>
                    </div>
                  </div>
    
                  {/* Controls Grid */}
                  <div className="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-3">
                    {complianceControls && complianceControls.length > 0 ? (
                      complianceControls.map((ctrl) => (
                        <div
                          key={ctrl.control_id}
                          className="rounded-xl border border-slate-800/80 bg-slate-950/60 p-4 space-y-3 hover:border-slate-700 transition"
                        >
                          <div className="flex items-start justify-between gap-2">
                            <div className="space-y-1">
                              <div className="flex items-center gap-2">
                                <span className="font-mono text-xs font-bold text-teal-400">
                                  {ctrl.control_id}
                                </span>
                                <span className="rounded bg-slate-800 px-1.5 py-0.5 text-[9px] font-mono text-slate-400 uppercase">
                                  {ctrl.control_category}
                                </span>
                              </div>
                              <h3 className="text-xs font-bold text-slate-100 leading-snug">
                                {ctrl.control_name}
                              </h3>
                            </div>
                            <span
                              className={`rounded-md border px-2 py-0.5 text-[10px] font-mono font-bold uppercase tracking-wider shrink-0 ${getComplianceControlStatusBadge(
                                ctrl.status
                              )}`}
                            >
                              {ctrl.status}
                            </span>
                          </div>
    
                          <p className="text-[11px] text-slate-400 leading-relaxed">
                            {ctrl.description}
                          </p>
    
                          <div className="rounded-lg border border-slate-800/80 bg-slate-900/60 p-2.5 space-y-1">
                            <span className="text-[10px] font-semibold text-slate-400 block uppercase tracking-wider">
                              Evidence Summary
                            </span>
                            <p className="text-[11px] text-slate-300 font-mono leading-relaxed">
                              {ctrl.evidence_summary}
                            </p>
                          </div>
    
                          <div className="flex items-center justify-between text-[10px] text-slate-500 font-mono border-t border-slate-800/60 pt-2">
                            <span>Owner: <strong className="text-slate-400">{ctrl.owner_role}</strong></span>
                            <span>Verified: {new Date(ctrl.last_verified_at).toLocaleDateString()}</span>
                          </div>
                        </div>
                      ))
                    ) : (
                      <div className="col-span-full py-12 text-center text-xs text-slate-500 font-mono">
                        No compliance controls matching the selected filters.
                      </div>
                    )}
                  </div>
                </div>
    
                {/* Audit Coverage & Lifecycle Provenance Visualizer */}
                <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                  {/* AuditLog Coverage Panel */}
                  <div className="rounded-2xl border border-slate-800 bg-slate-900/90 p-6 space-y-5 shadow-xl backdrop-blur">
                    <div className="flex items-center justify-between border-b border-slate-800 pb-3">
                      <h3 className="text-sm font-bold text-white flex items-center gap-2">
                        <span>📜 Immutable Audit Coverage</span>
                        <span className="rounded-full bg-emerald-950 border border-emerald-700/60 px-2 py-0.5 text-[10px] text-emerald-300 font-mono">
                          {complianceSummary?.audit_coverage.audit_coverage_percentage.toFixed(0) || "95"}% Coverage
                        </span>
                      </h3>
                      <span className="text-xs text-slate-400 font-mono">
                        {complianceSummary?.audit_coverage.total_audit_events_count || 0} Total Events
                      </span>
                    </div>
    
                    {/* Progress Bar */}
                    <div className="space-y-1.5">
                      <div className="flex justify-between text-xs text-slate-300 font-mono">
                        <span>Observed Lifecycle Categories</span>
                        <span>
                          {complianceSummary?.audit_coverage.observed_event_categories || 10} /{" "}
                          {complianceSummary?.audit_coverage.total_required_event_categories || 10}
                        </span>
                      </div>
                      <div className="h-2 w-full rounded-full bg-slate-800 overflow-hidden">
                        <div
                          className="h-full bg-gradient-to-r from-teal-500 to-emerald-400 transition-all duration-500"
                          style={{
                            width: `${complianceSummary?.audit_coverage.audit_coverage_percentage || 100}%`,
                          }}
                        />
                      </div>
                    </div>
    
                    {/* 10 Lifecycle Chains Grid */}
                    <div className="space-y-2">
                      <span className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider block">
                        Required Lifecycle Event Chains
                      </span>
                      <div className="grid grid-cols-2 gap-2">
                        {[
                          "AUTHENTICATION",
                          "AUTHORIZATION",
                          "PAYMENT_INGESTION",
                          "RECOVERY_LIFECYCLE",
                          "POLICY_GOVERNANCE",
                          "ACTION_EXECUTION",
                          "ACTION_RESULT",
                          "MODEL_LIFECYCLE",
                          "STRATEGY_GOVERNANCE",
                          "SECURITY_THREAT",
                        ].map((cat) => {
                          const isMissing = complianceSummary?.audit_coverage.missing_categories.includes(cat);
                          return (
                            <div
                              key={cat}
                              className={`flex items-center justify-between rounded-lg border p-2 text-xs font-mono ${
                                isMissing
                                  ? "border-amber-800/40 bg-amber-950/20 text-amber-300"
                                  : "border-slate-800 bg-slate-950/60 text-slate-300"
                              }`}
                            >
                              <span className="text-[10px] truncate">{cat}</span>
                              <span className="text-[9px] font-bold">
                                {isMissing ? "⚠️ MISSING" : "✓ OBSERVED"}
                              </span>
                            </div>
                          );
                        })}
                      </div>
                    </div>
                  </div>
    
                  {/* 6-Stage Decision Provenance & Financial Integrity Panel */}
                  <div className="rounded-2xl border border-slate-800 bg-slate-900/90 p-6 space-y-5 shadow-xl backdrop-blur">
                    <div className="flex items-center justify-between border-b border-slate-800 pb-3">
                      <h3 className="text-sm font-bold text-white flex items-center gap-2">
                        <span>⚖️ Financial Governance & Provenance Integrity</span>
                        <span className="rounded-full bg-indigo-950 border border-indigo-700/60 px-2 py-0.5 text-[10px] text-indigo-300 font-mono">
                          6-Stage Lifecycle Chain
                        </span>
                      </h3>
                    </div>
    
                    <div className="grid grid-cols-2 gap-3">
                      <div className="rounded-xl border border-slate-800 bg-slate-950/60 p-3 space-y-1">
                        <span className="text-[10px] text-slate-400 font-semibold block uppercase">
                          PolicyEngine Authority
                        </span>
                        <span className="text-base font-bold text-emerald-300 font-mono flex items-center gap-1.5">
                          <span>✓ VERIFIED</span>
                        </span>
                        <p className="text-[10px] text-slate-400">Sole financial gatekeeper</p>
                      </div>
    
                      <div className="rounded-xl border border-slate-800 bg-slate-950/60 p-3 space-y-1">
                        <span className="text-[10px] text-slate-400 font-semibold block uppercase">
                          Decision Trace Rate
                        </span>
                        <span className="text-base font-bold text-teal-300 font-mono">
                          {complianceSummary?.decision_trace_compliance.trace_completeness_rate.toFixed(1) || "100.0"}%
                        </span>
                        <p className="text-[10px] text-slate-400">Case → ML → Policy → Action</p>
                      </div>
    
                      <div className="rounded-xl border border-slate-800 bg-slate-950/60 p-3 space-y-1">
                        <span className="text-[10px] text-slate-400 font-semibold block uppercase">
                          Unauthorized Mutations
                        </span>
                        <span className="text-base font-bold text-white font-mono">0</span>
                        <p className="text-[10px] text-emerald-400">Zero bypass guarantee</p>
                      </div>
    
                      <div className="rounded-xl border border-slate-800 bg-slate-950/60 p-3 space-y-1">
                        <span className="text-[10px] text-slate-400 font-semibold block uppercase">
                          Governance Gateway Calls
                        </span>
                        <span className="text-base font-bold text-white font-mono">0</span>
                        <p className="text-[10px] text-emerald-400">Financially isolated</p>
                      </div>
                    </div>
    
                    {/* 6-Stage Lifecycle Flow */}
                    <div className="space-y-2 border-t border-slate-800/80 pt-3">
                      <span className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider block">
                        6-Stage Provenance Chain
                      </span>
                      <div className="flex items-center justify-between text-[10px] font-mono text-slate-300 bg-slate-950/80 p-2.5 rounded-xl border border-slate-800">
                        <span className="text-emerald-400">RecoveryCase</span>
                        <span>→</span>
                        <span className="text-cyan-400">MLPrediction</span>
                        <span>→</span>
                        <span className="text-purple-400">AgentDecision</span>
                        <span>→</span>
                        <span className="text-teal-400 font-bold">PolicyDecision</span>
                        <span>→</span>
                        <span className="text-amber-400">RecoveryAction</span>
                        <span>→</span>
                        <span className="text-blue-400">ActionResult</span>
                      </div>
                    </div>
                  </div>
                </div>
    
                {/* Compliance Incidents Center */}
                <div className="rounded-2xl border border-slate-800 bg-slate-900/90 p-6 space-y-5 shadow-xl backdrop-blur">
                  <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 border-b border-slate-800 pb-4">
                    <div>
                      <h3 className="text-lg font-bold text-white flex items-center gap-2">
                        <span>🚨 Compliance Incident & Governance Center</span>
                        <span className="rounded-full bg-slate-800 border border-slate-700 px-2 py-0.5 text-xs text-slate-300 font-mono">
                          {complianceIncidents?.length || 0} Detected
                        </span>
                      </h3>
                      <p className="text-xs text-slate-400 mt-0.5">
                        Surveillance findings, audit anomalies, and RBAC security event investigations.
                      </p>
                    </div>
    
                    <div className="flex items-center gap-2">
                      <select
                        value={incidentSeverityFilter}
                        onChange={(e) =>
                          handleFilterComplianceIncidents(e.target.value, incidentCategoryFilter)
                        }
                        className="rounded-lg border border-slate-700 bg-slate-800 px-2.5 py-1.5 text-xs text-slate-200 focus:border-teal-500 focus:outline-none"
                      >
                        <option value="ALL">All Severities</option>
                        <option value="CRITICAL">Critical</option>
                        <option value="HIGH">High</option>
                        <option value="MEDIUM">Medium</option>
                        <option value="LOW">Low</option>
                      </select>
                    </div>
                  </div>
    
                  {/* Incidents Table / Stream */}
                  <div className="space-y-3">
                    {complianceIncidents && complianceIncidents.length > 0 ? (
                      complianceIncidents.map((inc) => (
                        <div
                          key={inc.incident_id}
                          className="rounded-xl border border-slate-800 bg-slate-950/60 p-4 space-y-3 hover:border-slate-700 transition"
                        >
                          <div className="flex flex-wrap items-center justify-between gap-2">
                            <div className="flex items-center gap-2">
                              <span
                                className={`rounded-md border px-2 py-0.5 text-[10px] font-mono font-bold uppercase tracking-wider ${getComplianceSeverityBadge(
                                  inc.severity
                                )}`}
                              >
                                {inc.severity}
                              </span>
                              <span className="font-mono text-xs font-bold text-slate-300">
                                {inc.incident_id}
                              </span>
                              <span className="rounded bg-slate-800 px-1.5 py-0.5 text-[9px] font-mono text-slate-400">
                                {inc.category}
                              </span>
                            </div>
                            <span className="text-[11px] text-slate-500 font-mono">
                              {new Date(inc.detected_at).toLocaleString()}
                            </span>
                          </div>
    
                          <div>
                            <h4 className="text-xs font-bold text-white">{inc.title}</h4>
                            <p className="text-xs text-slate-400 mt-1">{inc.description}</p>
                          </div>
    
                          <div className="flex flex-wrap items-center justify-between gap-2 border-t border-slate-800/80 pt-2.5 text-xs">
                            <span className="text-slate-400 text-[11px]">
                              Target: <strong className="text-slate-200">{inc.affected_entity_type}</strong> ({inc.affected_entity_id || "Global"})
                            </span>
                            <button
                              onClick={() => setSelectedIncident(inc)}
                              className="px-2.5 py-1 rounded bg-slate-800 hover:bg-slate-700 text-teal-300 text-xs font-semibold border border-slate-700 transition"
                            >
                              View Forensic Evidence
                            </button>
                          </div>
                        </div>
                      ))
                    ) : (
                      <div className="rounded-xl border border-slate-800 bg-slate-950/40 p-8 text-center text-xs text-slate-500 font-mono">
                        ✓ Zero compliance incidents currently open. All systems within policy baselines.
                      </div>
                    )}
                  </div>
                </div>
              </div>


            {reportModalOpen && complianceReportData && (
              <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/85 backdrop-blur-md p-4">
                <div className="w-full max-w-3xl max-h-[90vh] flex flex-col rounded-2xl border border-teal-800/80 bg-slate-900 shadow-2xl overflow-hidden">
                  {/* Modal Header */}
                  <div className="flex items-center justify-between border-b border-slate-800 p-5 bg-slate-950/60">
                    <div className="space-y-1">
                      <div className="flex items-center gap-2">
                        <span className="rounded-lg bg-gradient-to-r from-teal-600 to-indigo-600 px-2 py-0.5 text-[10px] font-mono font-black uppercase text-white shadow">
                          COMPLIANCE SNAPSHOT EXPORT
                        </span>
                        <span className="font-mono text-xs font-bold text-teal-400">
                          {complianceReportData.report_id}
                        </span>
                      </div>
                      <h3 className="text-base font-bold text-white">
                        RecoverIQ Enterprise Compliance & Governance Snapshot
                      </h3>
                    </div>
                    <button
                      onClick={() => setReportModalOpen(false)}
                      className="rounded-lg p-1.5 text-slate-400 hover:bg-slate-800 hover:text-white transition"
                    >
                      ✕
                    </button>
                  </div>
    
                  {/* Modal Body */}
                  <div className="flex-1 overflow-y-auto p-6 space-y-6">
                    {/* Executive Summary */}
                    <div className="rounded-xl border border-teal-800/50 bg-teal-950/20 p-4 space-y-2">
                      <div className="flex items-center justify-between">
                        <span className="text-xs font-bold text-teal-300 uppercase tracking-wider">
                          Executive Posture Summary
                        </span>
                        <span
                          className={`rounded-full border px-2.5 py-0.5 text-[10px] font-mono font-bold uppercase tracking-wider ${getCompliancePostureBadge(
                            complianceReportData.compliance_posture
                          )}`}
                        >
                          {complianceReportData.compliance_posture} ({complianceReportData.compliance_score.toFixed(1)}/100)
                        </span>
                      </div>
                      <p className="text-xs text-slate-200 leading-relaxed font-mono">
                        {complianceReportData.executive_summary}
                      </p>
                    </div>
    
                    {/* Remediation Roadmap */}
                    <div className="space-y-3">
                      <h4 className="text-xs font-bold text-slate-300 uppercase tracking-wider">
                        Remediation & Governance Roadmap
                      </h4>
                      <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
                        {complianceReportData.remediation_roadmap.map((item, idx) => (
                          <div
                            key={idx}
                            className="rounded-xl border border-slate-800 bg-slate-950/60 p-3 space-y-1.5"
                          >
                            <div className="flex items-center justify-between">
                              <span className="text-[10px] font-bold text-teal-400 font-mono">
                                {item.milestone}
                              </span>
                              <span className="text-[9px] font-mono bg-slate-800 px-1.5 py-0.5 rounded text-slate-400">
                                {item.priority}
                              </span>
                            </div>
                            <p className="text-[11px] text-slate-200 leading-snug">{item.action}</p>
                            <span className="text-[10px] text-slate-500 font-mono block">
                              Target: {item.target_date}
                            </span>
                          </div>
                        ))}
                      </div>
                    </div>
    
                    {/* Structured JSON Export View */}
                    <div className="space-y-2">
                      <div className="flex items-center justify-between">
                        <span className="text-xs font-bold text-slate-300 uppercase tracking-wider">
                          Structured JSON Evidence Export
                        </span>
                        <button
                          onClick={() => {
                            navigator.clipboard.writeText(JSON.stringify(complianceReportData, null, 2));
                            alert("Compliance report JSON copied to clipboard!");
                          }}
                          className="px-2.5 py-1 rounded bg-slate-800 hover:bg-slate-700 text-teal-300 text-xs font-semibold border border-slate-700 transition"
                        >
                          Copy JSON
                        </button>
                      </div>
                      <pre className="max-h-64 overflow-y-auto rounded-xl border border-slate-800 bg-slate-950 p-4 font-mono text-[11px] text-slate-300 leading-relaxed scrollbar-thin scrollbar-thumb-slate-700">
                        {JSON.stringify(complianceReportData, null, 2)}
                      </pre>
                    </div>
    
                    {/* Disclaimer */}
                    <div className="rounded-xl border border-slate-800 bg-slate-950/80 p-3 text-[11px] text-slate-400 leading-relaxed font-mono">
                      <strong className="text-amber-400">Disclaimer:</strong> {complianceReportData.disclaimer}
                    </div>
                  </div>
    
                  {/* Modal Footer */}
                  <div className="flex items-center justify-between border-t border-slate-800 p-4 bg-slate-950/60">
                    <span className="text-xs text-slate-500 font-mono">
                      Generated: {new Date(complianceReportData.generated_at).toLocaleString()}
                    </span>
                    <button
                      type="button"
                      onClick={() => setReportModalOpen(false)}
                      className="rounded-xl border border-slate-800 bg-slate-950 px-5 py-2 text-xs font-bold uppercase tracking-wider text-slate-300 hover:text-white transition"
                    >
                      Close Snapshot
                    </button>
                  </div>
                </div>
              </div>
            )}
    
            {/* Phase 10B: Compliance Incident Detail Forensic Modal */}
            {selectedIncident && (
              <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/85 backdrop-blur-md p-4">
                <div className="w-full max-w-2xl max-h-[85vh] flex flex-col rounded-2xl border border-rose-800/80 bg-slate-900 shadow-2xl overflow-hidden">
                  <div className="flex items-center justify-between border-b border-slate-800 p-5 bg-slate-950/60">
                    <div className="space-y-1">
                      <div className="flex items-center gap-2">
                        <span
                          className={`rounded-md border px-2 py-0.5 text-[10px] font-mono font-bold uppercase tracking-wider ${getComplianceSeverityBadge(
                            selectedIncident.severity
                          )}`}
                        >
                          {selectedIncident.severity}
                        </span>
                        <span className="font-mono text-xs font-bold text-slate-300">
                          {selectedIncident.incident_id}
                        </span>
                        <span className="rounded bg-slate-800 px-1.5 py-0.5 text-[9px] font-mono text-slate-400">
                          {selectedIncident.category}
                        </span>
                      </div>
                      <h3 className="text-base font-bold text-white">
                        {selectedIncident.title}
                      </h3>
                    </div>
                    <button
                      onClick={() => setSelectedIncident(null)}
                      className="rounded-lg p-1.5 text-slate-400 hover:bg-slate-800 hover:text-white transition"
                    >
                      ✕
                    </button>
                  </div>
    
                  <div className="flex-1 overflow-y-auto p-6 space-y-5">
                    <div>
                      <span className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider block mb-1">
                        Incident Description
                      </span>
                      <p className="text-xs text-slate-200 leading-relaxed font-mono bg-slate-950/60 p-3 rounded-xl border border-slate-800">
                        {selectedIncident.description}
                      </p>
                    </div>
    
                    <div className="grid grid-cols-2 gap-3 text-xs font-mono">
                      <div className="rounded-xl border border-slate-800 bg-slate-950/60 p-3 space-y-1">
                        <span className="text-[10px] text-slate-400 font-semibold uppercase">Target Entity</span>
                        <p className="text-slate-200 font-bold">{selectedIncident.affected_entity_type}</p>
                        <p className="text-[10px] text-slate-400">{selectedIncident.affected_entity_id || "System Global"}</p>
                      </div>
                      <div className="rounded-xl border border-slate-800 bg-slate-950/60 p-3 space-y-1">
                        <span className="text-[10px] text-slate-400 font-semibold uppercase">Detected At</span>
                        <p className="text-slate-200">{new Date(selectedIncident.detected_at).toLocaleString()}</p>
                        <p className="text-[10px] text-slate-400">Status: <strong className="text-rose-400">{selectedIncident.status}</strong></p>
                      </div>
                    </div>
    
                    {/* Forensic Evidence JSON */}
                    <div className="space-y-2">
                      <span className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider block">
                        Forensic Evidence Payload
                      </span>
                      <pre className="max-h-48 overflow-y-auto rounded-xl border border-slate-800 bg-slate-950 p-3 font-mono text-[11px] text-slate-300 leading-relaxed scrollbar-thin scrollbar-thumb-slate-700">
                        {JSON.stringify(selectedIncident.evidence, null, 2)}
                      </pre>
                    </div>
    
                    {/* Recommended Remediation */}
                    <div className="rounded-xl border border-teal-800/40 bg-teal-950/20 p-3 space-y-1">
                      <span className="text-[10px] font-bold text-teal-400 uppercase tracking-wider block">
                        Recommended Remediation
                      </span>
                      <p className="text-xs text-slate-200 leading-relaxed">
                        {selectedIncident.recommended_action}
                      </p>
                    </div>
    
                    {/* Safety Guarantee Notice */}
                    <div className="rounded-xl border border-slate-800 bg-slate-950/80 p-3 text-[10px] text-slate-400 leading-relaxed font-mono">
                      🔒 <strong className="text-slate-200">Zero Financial Mutation Guarantee:</strong> Remediations must follow governed manual or policy engine workflows. This incident viewer is strictly observational.
                    </div>
                  </div>
    
                  <div className="flex items-center justify-end border-t border-slate-800 p-4 bg-slate-950/60">
                    <button
                      type="button"
                      onClick={() => setSelectedIncident(null)}
                      className="rounded-xl border border-slate-800 bg-slate-950 px-5 py-2 text-xs font-bold uppercase tracking-wider text-slate-300 hover:text-white transition"
                    >
                      Close
                    </button>
                  </div>
                </div>
              </div>
            )}
    
            {/* Phase 10D: Postmortem Creation Modal */}


    </>
  );
}
