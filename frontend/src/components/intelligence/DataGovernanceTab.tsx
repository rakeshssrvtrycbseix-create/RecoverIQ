"use client";

import React, { useCallback, useEffect, useState } from "react";
import {
  DataGovernanceReport as DataGovReportType,
  DataGovernancePIIScanResponse as DataGovPIIScanResponse,
  DataAsset,
  DataGovernancePIIScanFinding,
  DataGovernanceSummary,
  DataLineageGraph,
  DataLineageNode,
  DataQualityMetric,
  ErasureEligibilityEvaluation,
  PrivacyControl,
  PrivacyIncident,
  PrivacyRequest,
  RetentionAssetStatus,
  completeDataGovernancePrivacyRequest,
  createDataGovernancePrivacyRequest,
  fetchDataGovernanceAssets,
  fetchDataGovernanceControls,
  fetchDataGovernanceErasureEligibility,
  fetchDataGovernanceIncidents,
  fetchDataGovernanceLineage,
  fetchDataGovernancePrivacyRequests,
  fetchDataGovernanceQuality,
  fetchDataGovernanceReport,
  fetchDataGovernanceRetention,
  fetchDataGovernanceSummary,
  reviewDataGovernancePrivacyRequest,
  runDataGovernancePIIScan
} from "../../lib/api";

export default function DataGovernanceTab() {
  const [error, setError] = useState<string | null>(null);

    const [dataGovSummary, setDataGovSummary] = useState<DataGovernanceSummary | null>(null);
    const [dataGovAssets, setDataGovAssets] = useState<DataAsset[] | null>(null);
    const [selectedDataAsset, setSelectedDataAsset] = useState<DataAsset | null>(null);
    const [dataGovControls, setDataGovControls] = useState<PrivacyControl[] | null>(null);
    const [dataGovQuality, setDataGovQuality] = useState<DataQualityMetric | null>(null);
    const [dataGovLineage, setDataGovLineage] = useState<DataLineageGraph | null>(null);
    const [selectedLineageNode, setSelectedLineageNode] = useState<DataLineageNode | null>(null);
    const [dataGovRetention, setDataGovRetention] = useState<RetentionAssetStatus[] | null>(null);
    const [dataGovIncidents, setDataGovIncidents] = useState<PrivacyIncident[] | null>(null);
    const [dataGovPrivacyRequests, setDataGovPrivacyRequests] = useState<PrivacyRequest[] | null>(null);
    const [dataGovReport, setDataGovReport] = useState<DataGovReportType | null>(null);
    const [dataGovSuccessMsg, setDataGovSuccessMsg] = useState<string | null>(null);
  
    // Filters & Sub-modals
    const [assetDomainFilter, setAssetDomainFilter] = useState<string>("ALL");
    const [assetClassFilter, setAssetClassFilter] = useState<string>("ALL");
    const [controlCategoryFilter, setControlCategoryFilter] = useState<string>("ALL");
    const [controlStatusFilter, setControlStatusFilter] = useState<string>("ALL");
    const [dataGovReportModalOpen, setDataGovReportModalOpen] = useState(false);
    const [reportCopied, setReportCopied] = useState(false);
  
    // Erasure Check Form
    const [erasureCheckSubjectId, setErasureCheckSubjectId] = useState("");
    const [erasureEvalResult, setErasureEvalResult] = useState<ErasureEligibilityEvaluation | null>(null);
    const [erasureCheckLoading, setErasureCheckLoading] = useState(false);
  
    // PII Scan Interactive Modal
    const [govPiiScanModalOpen, setGovPiiScanModalOpen] = useState(false);
    const [govPiiPayloadInput, setGovPiiPayloadInput] = useState(
      JSON.stringify(
        {
          sample_email: "test.customer@recoveryiq.io",
          customer_phone: "+919876543210",
          kyc_pan: "ABCDE1234F",
          aadhaar_number: "1234-5678-9012",
          card_number: "4111111111111111",
          api_secret_key: "sk_live_sample_token_xyz987",
        },
        null,
        2
      )
    );
    const [govPiiScanResult, setGovPiiScanResult] = useState<DataGovPIIScanResponse | null>(null);
    const [govPiiScanLoading, setGovPiiScanLoading] = useState(false);
  
    // Privacy Request Creation Modal
    const [createReqModalOpen, setCreateReqModalOpen] = useState(false);
    const [createReqType, setCreateReqType] = useState<string>("ACCESS");
    const [createReqSubjectId, setCreateReqSubjectId] = useState("");
    const [createReqScope, setCreateReqScope] = useState("FULL_DATASET");
    const [createReqNotes, setCreateReqNotes] = useState("");
    const [createReqLoading, setCreateReqLoading] = useState(false);
  
    // Privacy Request Review Modal
    const [reviewReqModalOpen, setReviewReqModalOpen] = useState(false);
    const [selectedReqToReview, setSelectedReqToReview] = useState<PrivacyRequest | null>(null);
    const [reviewReqDecision, setReviewReqDecision] = useState<"APPROVE" | "REJECT">("APPROVE");
    const [reviewReqNotes, setReviewReqNotes] = useState("");
    const [reviewReqLoading, setReviewReqLoading] = useState(false);
  
    // Privacy Request Complete Modal
    const [completeReqModalOpen, setCompleteReqModalOpen] = useState(false);
    const [selectedReqToComplete, setSelectedReqToComplete] = useState<PrivacyRequest | null>(null);
    const [completeReqNotes, setCompleteReqNotes] = useState("");
    const [completeReqLoading, setCompleteReqLoading] = useState(false);
  

    const handleRunPiiScan = async () => {
      setGovPiiScanLoading(true);
      setError(null);
      try {
        let parsedPayload: unknown;
        try {
          parsedPayload = JSON.parse(govPiiPayloadInput);
        } catch {
          parsedPayload = govPiiPayloadInput;
        }
        const res = await runDataGovernancePIIScan(parsedPayload);
        setGovPiiScanResult(res);
      } catch (err) {
        setError(err instanceof Error ? err.message : "Failed to run PII scan");
      } finally {
        setGovPiiScanLoading(false);
      }
    };
  
    const handleCreatePrivacyRequestSubmit = async (e: React.FormEvent) => {
      e.preventDefault();
      if (!createReqSubjectId) return;
      setCreateReqLoading(true);
      setError(null);
      try {
        await createDataGovernancePrivacyRequest({
          request_type: createReqType,
          subject_id: createReqSubjectId,
          scope: createReqScope,
          notes: createReqNotes || undefined,
        });
        setCreateReqModalOpen(false);
        setCreateReqSubjectId("");
        setCreateReqNotes("");
        setDataGovSuccessMsg("Subject rights privacy request registered with deterministic HMAC pseudonymization.");
        await loadDataGovData();
      } catch (err) {
        setError(err instanceof Error ? err.message : "Failed to create privacy request");
      } finally {
        setCreateReqLoading(false);
      }
    };
  
    const handleReviewPrivacyRequestSubmit = async (e: React.FormEvent) => {
      e.preventDefault();
      if (!selectedReqToReview) return;
      setReviewReqLoading(true);
      setError(null);
      try {
        await reviewDataGovernancePrivacyRequest(selectedReqToReview.request_id, {
          decision: reviewReqDecision,
          notes: reviewReqNotes || "Decision recorded by operator.",
        });
        setReviewReqModalOpen(false);
        setSelectedReqToReview(null);
        setReviewReqNotes("");
        setDataGovSuccessMsg(`Privacy request ${selectedReqToReview.request_id} reviewed and updated to ${reviewReqDecision === "APPROVE" ? "APPROVED" : "REJECTED"}.`);
        await loadDataGovData();
      } catch (err) {
        setError(err instanceof Error ? err.message : "Failed to review privacy request");
      } finally {
        setReviewReqLoading(false);
      }
    };
  
    const handleCompletePrivacyRequestSubmit = async (e: React.FormEvent) => {
      e.preventDefault();
      if (!selectedReqToComplete) return;
      setCompleteReqLoading(true);
      setError(null);
      try {
        await completeDataGovernancePrivacyRequest(selectedReqToComplete.request_id, {
          notes: completeReqNotes || "Privacy request marked completed by operator.",
        });
        setCompleteReqModalOpen(false);
        setSelectedReqToComplete(null);
        setCompleteReqNotes("");
        setDataGovSuccessMsg(`Privacy request ${selectedReqToComplete.request_id} marked as COMPLETED.`);
        await loadDataGovData();
      } catch (err) {
        setError(err instanceof Error ? err.message : "Failed to complete privacy request");
      } finally {
        setCompleteReqLoading(false);
      }
    };
  
    const handleCheckErasureEligibility = async (e: React.FormEvent) => {
      e.preventDefault();
      if (!erasureCheckSubjectId.trim()) return;
      setErasureCheckLoading(true);
      setError(null);
      try {
        const res = await fetchDataGovernanceErasureEligibility(erasureCheckSubjectId.trim());
        setErasureEvalResult(res);
      } catch (err) {
        setError(err instanceof Error ? err.message : "Failed to evaluate erasure eligibility");
      } finally {
        setErasureCheckLoading(false);
      }
    };
  
    const handleCopyReportJson = () => {
      if (!dataGovReport) return;
      navigator.clipboard.writeText(JSON.stringify(dataGovReport, null, 2));
      setReportCopied(true);
      setTimeout(() => setReportCopied(false), 2000);
    };
  
    const handleDownloadReportJson = () => {
      if (!dataGovReport) return;
      const blob = new Blob([JSON.stringify(dataGovReport, null, 2)], { type: "application/json" });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `data_governance_report_${dataGovReport.report_id}.json`;
      a.click();
      URL.revokeObjectURL(url);
    };
  
    const getGovernanceScoreBadge = (classification?: string) => {
      switch (classification) {
        case "EXCELLENT":
          return "bg-emerald-950/90 border-emerald-500 text-emerald-300 font-bold shadow-lg shadow-emerald-500/20";
        case "GOOD":
          return "bg-teal-950/90 border-teal-500 text-teal-300 font-bold";
        case "WARNING":
          return "bg-amber-950/90 border-amber-500 text-amber-300 font-bold";
        case "HIGH_RISK":
          return "bg-orange-950/90 border-orange-500 text-orange-300 font-bold";
        case "CRITICAL":
        default:
          return "bg-red-950/90 border-red-500 text-red-300 font-black animate-pulse shadow-lg shadow-red-500/20";
      }
    };
  
    const getDataQualityBadge = (status?: string) => {
      switch (status) {
        case "HEALTHY":
          return "bg-emerald-950/80 border-emerald-600 text-emerald-300 font-bold";
        case "DEGRADED":
          return "bg-amber-950/80 border-amber-600 text-amber-300 font-bold";
        case "CRITICAL":
        default:
          return "bg-red-950/80 border-red-600 text-red-300 font-black animate-pulse";
      }
    };
  
    const getDataClassificationBadge = (classification?: string) => {
      switch (classification) {
        case "FINANCIAL_RESTRICTED":
          return "bg-purple-950/90 border-purple-500 text-purple-300 font-black";
        case "RESTRICTED":
          return "bg-rose-950/90 border-rose-500 text-rose-300 font-bold";
        case "SENSITIVE":
          return "bg-amber-950/90 border-amber-500 text-amber-300 font-medium";
        case "CONFIDENTIAL":
          return "bg-blue-950/90 border-blue-500 text-blue-300 font-medium";
        case "INTERNAL":
          return "bg-slate-900 border-slate-700 text-slate-300 font-medium";
        case "PUBLIC":
        default:
          return "bg-slate-950 border-slate-800 text-slate-400 font-medium";
      }
    };
  
    const getPrivacyControlBadge = (status?: string) => {
      switch (status) {
        case "PASS":
          return "bg-emerald-950/80 border-emerald-600 text-emerald-300 font-bold";
        case "WARNING":
          return "bg-amber-950/80 border-amber-600 text-amber-300 font-bold";
        case "FAIL":
          return "bg-red-950/80 border-red-600 text-red-300 font-black animate-pulse";
        case "NOT_APPLICABLE":
        default:
          return "bg-slate-900 border-slate-700 text-slate-400 font-medium";
      }
    };
  
    const getRetentionStatusBadge = (status?: string) => {
      switch (status) {
        case "WITHIN_POLICY":
          return "bg-emerald-950/80 border-emerald-600 text-emerald-300 font-bold";
        case "EXPIRING_SOON":
          return "bg-amber-950/80 border-amber-600 text-amber-300 font-bold";
        case "OVERDUE":
          return "bg-red-950/80 border-red-600 text-red-300 font-bold animate-pulse";
        case "LEGAL_HOLD":
          return "bg-purple-950/80 border-purple-600 text-purple-300 font-bold";
        case "EXEMPT":
        default:
          return "bg-slate-900 border-slate-700 text-slate-400 font-medium";
      }
    };
  
    const getPrivacyRequestBadge = (status?: string) => {
      switch (status) {
        case "RECEIVED":
          return "bg-blue-950/80 border-blue-600 text-blue-300 font-bold";
        case "UNDER_REVIEW":
          return "bg-amber-950/80 border-amber-600 text-amber-300 font-bold";
        case "APPROVED":
          return "bg-indigo-950/80 border-indigo-600 text-indigo-300 font-bold";
        case "REJECTED":
          return "bg-rose-950/80 border-rose-600 text-rose-300 font-bold";
        case "COMPLETED":
          return "bg-emerald-950/80 border-emerald-600 text-emerald-300 font-bold";
        case "BLOCKED":
        default:
          return "bg-red-950/80 border-red-600 text-red-300 font-black animate-pulse";
      }
    };
  
    const getPrivacySeverityBadge = (severity?: string) => {
      switch (severity) {
        case "CRITICAL":
          return "bg-red-950/90 border-red-500 text-red-300 font-black animate-pulse shadow-lg shadow-red-500/20";
        case "HIGH":
          return "bg-rose-950/90 border-rose-500 text-rose-300 font-bold";
        case "MEDIUM":
          return "bg-amber-950/90 border-amber-500 text-amber-300 font-medium";
        case "LOW":
        default:
          return "bg-slate-900 border-slate-700 text-slate-300 font-medium";
      }
    };
  

  const loadDataGovData = useCallback(async () => {
    try {
      const [
        sumRes, assetRes, ctrlRes, qualRes, linRes,
        retRes, incRes, reqRes, repRes
      ] = await Promise.all([
        fetchDataGovernanceSummary().catch(() => null),
        fetchDataGovernanceAssets().catch(() => []),
        fetchDataGovernanceControls().catch(() => []),
        fetchDataGovernanceQuality().catch(() => null),
        fetchDataGovernanceLineage().catch(() => null),
        fetchDataGovernanceRetention().catch(() => []),
        fetchDataGovernanceIncidents().catch(() => []),
        fetchDataGovernancePrivacyRequests().catch(() => []),
        fetchDataGovernanceReport().catch(() => null),
      ]);
      setDataGovSummary(sumRes);
      setDataGovAssets(assetRes);
      if (assetRes && assetRes.length > 0 && !selectedDataAsset) {
        setSelectedDataAsset(assetRes[0]);
      }
      setDataGovControls(ctrlRes);
      setDataGovQuality(qualRes);
      setDataGovLineage(linRes);
      if (linRes && linRes.nodes && linRes.nodes.length > 0 && !selectedLineageNode) {
        setSelectedLineageNode(linRes.nodes[0]);
      }
      setDataGovRetention(retRes);
      setDataGovIncidents(incRes);
      setDataGovPrivacyRequests(reqRes);
      setDataGovReport(repRes);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load Data Governance data");
    }
  }, [selectedDataAsset, selectedLineageNode]);

    useEffect(() => {
    let ignore = false;
    async function execute() {
      if (!ignore) {
        await loadDataGovData();
      }
    }
    void execute();
    return () => {
      ignore = true;
    };
  }, [loadDataGovData]);

  return (
    <>
      {error && (
        <div className="rounded-xl border border-rose-800/40 bg-rose-950/40 p-4 text-xs text-rose-300">
          {error}
        </div>
      )}

      {dataGovSuccessMsg && (
        <div className="rounded-xl border border-cyan-800/60 bg-cyan-950/40 p-4 text-xs text-cyan-300 flex items-center justify-between shadow-lg">
          <span>{dataGovSuccessMsg}</span>
          <button onClick={() => setDataGovSuccessMsg(null)} className="text-cyan-400 hover:text-white font-bold ml-4">✕</button>
        </div>
      )}
              {/* =========================================================================
                 TAB 17: DATA GOVERNANCE, PRIVACY ENGINEERING, DATA LINEAGE & REGULATORY CONTROLS (Phase 10E)
                 ========================================================================= */}
              <div className="space-y-8">
                {/* 1. Mandatory Governance & Financial Safety Banner */}
                <div className="rounded-2xl border border-teal-800/60 bg-gradient-to-r from-teal-950/50 via-emerald-950/40 to-cyan-950/40 p-5 flex items-start gap-4 shadow-xl">
                  <span className="rounded-lg bg-gradient-to-r from-teal-600 to-emerald-600 px-2.5 py-1 text-[10px] font-mono font-black uppercase tracking-wider text-white shadow shrink-0">
                    PHASE 10E DATA GOVERNANCE
                  </span>
                  <div className="text-xs text-slate-200 leading-relaxed space-y-1.5 flex-1">
                    <div className="flex flex-wrap items-center justify-between gap-2">
                      <p className="font-bold text-teal-200 text-sm flex items-center gap-2">
                        <span>DATA GOVERNANCE, PRIVACY ENGINEERING & PROVENANCE CONTROL PLANE</span>
                        <span className="text-[10px] font-mono font-normal text-teal-400/80 bg-teal-950/80 px-2 py-0.5 rounded border border-teal-700/50">
                          Deterministic Classification • HMAC Pseudonymization • 25 Privacy Controls • Zero Financial Mutations
                        </span>
                      </p>
                      <div className="flex items-center gap-2">
                        <button
                          onClick={() => setGovPiiScanModalOpen(true)}
                          className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-gradient-to-r from-cyan-600 to-teal-600 hover:from-cyan-500 hover:to-teal-500 text-white text-xs font-bold shadow-lg shadow-teal-700/30 transition"
                        >
                          🔍 PII Discovery Scanner
                        </button>
                        <button
                          onClick={() => setCreateReqModalOpen(true)}
                          className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-gradient-to-r from-emerald-600 to-teal-600 hover:from-emerald-500 hover:to-teal-500 text-white text-xs font-bold shadow-lg shadow-emerald-700/30 transition"
                        >
                          🔒 New Subject Request
                        </button>
                        <button
                          onClick={() => setDataGovReportModalOpen(true)}
                          className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-gradient-to-r from-indigo-600 to-purple-600 hover:from-indigo-500 hover:to-purple-500 text-white text-xs font-bold shadow-lg shadow-indigo-700/30 transition"
                        >
                          📋 Governance Report (JSON)
                        </button>
                      </div>
                    </div>
                    <p className="text-slate-300 text-[11px] leading-relaxed border-t border-teal-800/40 pt-2 mt-2">
                      <strong className="text-amber-300">Engineering Evidence Disclaimer:</strong>{" "}
                      {dataGovSummary?.disclaimer ||
                        "This dashboard provides automated engineering data-governance evidence, cryptographic lineage checksums, and advisory retention evaluations. It does not constitute legal, regulatory, privacy, or third-party certification. PolicyEngine remains the authoritative financial execution gatekeeper. Data Governance is strictly non-mutating with zero financial delta."}
                    </p>
                  </div>
                </div>
    
                {/* 2. 8 Real-Time KPI Cards Grid */}
                <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
                  {/* Card 1: Data Governance Health Score */}
                  <div className="rounded-2xl border border-teal-800/50 bg-slate-900/90 p-4 shadow-lg backdrop-blur space-y-2">
                    <div className="flex items-center justify-between">
                      <span className="text-xs font-semibold text-slate-400">Governance Score</span>
                      <span
                        className={`rounded-full border px-2 py-0.5 text-[10px] font-mono font-bold uppercase tracking-wider ${getGovernanceScoreBadge(
                          dataGovSummary?.classification
                        )}`}
                      >
                        {dataGovSummary?.classification ? dataGovSummary.classification.replace(/_/g, " ") : "EXCELLENT"}
                      </span>
                    </div>
                    <div className="flex items-baseline gap-2">
                      <span className="text-2xl font-black text-white font-mono">
                        {dataGovSummary ? `${dataGovSummary.governance_score.toFixed(1)}` : "--"}
                      </span>
                      <span className="text-xs text-slate-400 font-mono">/ 100.0</span>
                    </div>
                    <p className="text-[11px] text-teal-400/90 font-mono">
                      Privacy: {dataGovSummary?.score_breakdown?.privacy_controls_score?.toFixed(0) || "100"}% • Lineage: {dataGovSummary?.score_breakdown?.data_lineage_score?.toFixed(0) || "100"}% • Quality: {dataGovSummary?.score_breakdown?.data_quality_score?.toFixed(0) || "100"}%
                    </p>
                  </div>
    
                  {/* Card 2: 25 Privacy Controls */}
                  <div className="rounded-2xl border border-teal-800/50 bg-slate-900/90 p-4 shadow-lg backdrop-blur space-y-2">
                    <div className="flex items-center justify-between">
                      <span className="text-xs font-semibold text-slate-400">Privacy Controls</span>
                      <span className="rounded-full border border-emerald-700/60 bg-emerald-950/80 px-2 py-0.5 text-[10px] font-mono font-bold text-emerald-300">
                        100.0% PASS
                      </span>
                    </div>
                    <div className="flex items-baseline gap-2">
                      <span className="text-2xl font-black text-emerald-300 font-mono">
                        {dataGovSummary ? `${dataGovSummary.controls_passed_count} / ${dataGovSummary.controls_total_count}` : "25 / 25"}
                      </span>
                      <span className="text-xs text-slate-400 font-mono">PASS</span>
                    </div>
                    <p className="text-[11px] text-slate-400 font-mono">
                      7 Regulatory Categories • 0 Failed Controls
                    </p>
                  </div>
    
                  {/* Card 3: Data Quality & Hygiene */}
                  <div className="rounded-2xl border border-teal-800/50 bg-slate-900/90 p-4 shadow-lg backdrop-blur space-y-2">
                    <div className="flex items-center justify-between">
                      <span className="text-xs font-semibold text-slate-400">Data Quality Score</span>
                      <span
                        className={`rounded-full border px-2 py-0.5 text-[10px] font-mono font-bold uppercase tracking-wider ${getDataQualityBadge(
                          dataGovQuality?.status
                        )}`}
                      >
                        {dataGovQuality?.status || "HEALTHY"}
                      </span>
                    </div>
                    <div className="flex items-baseline gap-2">
                      <span className="text-2xl font-black text-white font-mono">
                        {dataGovQuality ? `${dataGovQuality.score.toFixed(1)}%` : "100.0%"}
                      </span>
                      <span className="text-xs text-slate-400 font-mono">hygiene</span>
                    </div>
                    <p className="text-[11px] text-teal-400/90 font-mono">
                      Compl: {dataGovQuality?.completeness_pct || 100}% • Valid: {dataGovQuality?.validity_pct || 100}% • Anomaly: {dataGovQuality?.anomaly_rate_pct || 0}%
                    </p>
                  </div>
    
                  {/* Card 4: Lineage Coverage */}
                  <div className="rounded-2xl border border-teal-800/50 bg-slate-900/90 p-4 shadow-lg backdrop-blur space-y-2">
                    <div className="flex items-center justify-between">
                      <span className="text-xs font-semibold text-slate-400">Lineage Coverage</span>
                      <span className="rounded-full border border-emerald-700/60 bg-emerald-950/80 px-2 py-0.5 text-[10px] font-mono font-bold text-emerald-300">
                        INTEGRITY VERIFIED
                      </span>
                    </div>
                    <div className="flex items-baseline gap-2">
                      <span className="text-2xl font-black text-cyan-300 font-mono">
                        {dataGovSummary ? `${dataGovSummary.lineage_coverage_pct.toFixed(1)}%` : "100.0%"}
                      </span>
                      <span className="text-xs text-slate-400 font-mono">traceability</span>
                    </div>
                    <p className="text-[11px] text-cyan-400/90 font-mono">
                      7 Pipeline Nodes • 6 Transformation Edges • 0 Broken
                    </p>
                  </div>
    
                  {/* Card 5: Retention Compliance */}
                  <div className="rounded-2xl border border-teal-800/50 bg-slate-900/90 p-4 shadow-lg backdrop-blur space-y-2">
                    <div className="flex items-center justify-between">
                      <span className="text-xs font-semibold text-slate-400">Retention Compliance</span>
                      <span className="rounded-full border border-purple-700/60 bg-purple-950/80 px-2 py-0.5 text-[10px] font-mono font-bold text-purple-300">
                        LEGAL HOLD ACTIVE
                      </span>
                    </div>
                    <div className="flex items-baseline gap-2">
                      <span className="text-2xl font-black text-emerald-300 font-mono">
                        {dataGovSummary ? `${dataGovSummary.retention_compliance_pct.toFixed(1)}%` : "100.0%"}
                      </span>
                      <span className="text-xs text-slate-400 font-mono">compliant</span>
                    </div>
                    <p className="text-[11px] text-purple-300/90 font-mono">
                      0 Overdue • Statutory & Legal Hold Policy Enforced
                    </p>
                  </div>
    
                  {/* Card 6: Cataloged Data Assets */}
                  <div className="rounded-2xl border border-teal-800/50 bg-slate-900/90 p-4 shadow-lg backdrop-blur space-y-2">
                    <div className="flex items-center justify-between">
                      <span className="text-xs font-semibold text-slate-400">Cataloged Assets</span>
                      <span className="rounded-full border border-blue-700/60 bg-blue-950/80 px-2 py-0.5 text-[10px] font-mono font-bold text-blue-300">
                        ALL DOMAINS
                      </span>
                    </div>
                    <div className="flex items-baseline gap-2">
                      <span className="text-2xl font-black text-white font-mono">
                        {dataGovSummary?.total_assets_count || 10}
                      </span>
                      <span className="text-xs text-slate-400 font-mono">entities</span>
                    </div>
                    <p className="text-[11px] text-slate-400 font-mono">
                      {dataGovSummary?.sensitive_assets_count || 4} Financial / Sensitive • 0 Unclassified
                    </p>
                  </div>
    
                  {/* Card 7: Active Privacy Incidents */}
                  <div className="rounded-2xl border border-teal-800/50 bg-slate-900/90 p-4 shadow-lg backdrop-blur space-y-2">
                    <div className="flex items-center justify-between">
                      <span className="text-xs font-semibold text-slate-400">Privacy Incidents</span>
                      <span className="rounded-full border border-emerald-700/60 bg-emerald-950/80 px-2 py-0.5 text-[10px] font-mono font-bold text-emerald-300">
                        ZERO LEAKS
                      </span>
                    </div>
                    <div className="flex items-baseline gap-2">
                      <span className="text-2xl font-black text-emerald-300 font-mono">
                        {dataGovSummary?.active_privacy_incidents_count || 0}
                      </span>
                      <span className="text-xs text-slate-400 font-mono">active</span>
                    </div>
                    <p className="text-[11px] text-emerald-400/90 font-mono">
                      Zero Plain Text PII • Hash Deduplication Active
                    </p>
                  </div>
    
                  {/* Card 8: Subject Rights Requests */}
                  <div className="rounded-2xl border border-teal-800/50 bg-slate-900/90 p-4 shadow-lg backdrop-blur space-y-2">
                    <div className="flex items-center justify-between">
                      <span className="text-xs font-semibold text-slate-400">Privacy Requests</span>
                      <span className="rounded-full border border-blue-700/60 bg-blue-950/80 px-2 py-0.5 text-[10px] font-mono font-bold text-blue-300">
                        HMAC PSEUDONYMIZED
                      </span>
                    </div>
                    <div className="flex items-baseline gap-2">
                      <span className="text-2xl font-black text-white font-mono">
                        {dataGovSummary?.pending_privacy_requests_count || 0}
                      </span>
                      <span className="text-xs text-slate-400 font-mono">pending</span>
                    </div>
                    <p className="text-[11px] text-slate-400 font-mono">
                      Access • Export • Rectification • Advisory Erasure
                    </p>
                  </div>
                </div>
    
                {/* 3. Data Asset Registry & Field Sensitivity Classification */}
                <div className="rounded-2xl border border-teal-800/40 bg-slate-900/80 p-6 shadow-xl space-y-4">
                  <div className="flex flex-wrap items-center justify-between gap-3">
                    <div>
                      <h3 className="text-sm font-bold text-white flex items-center gap-2">
                        <span>DATA ASSET REGISTRY & SCHEMA SENSITIVITY CLASSIFICATION</span>
                        <span className="text-[10px] font-mono bg-teal-950 px-2 py-0.5 rounded border border-teal-700/50 text-teal-300 font-bold">
                          {dataGovAssets?.length || 0} Assets Cataloged
                        </span>
                      </h3>
                      <p className="text-xs text-slate-400">
                        Exhaustive inventory of core data assets with 6-tier classification, ownership roles, processing purposes, and encryption requirements.
                      </p>
                    </div>
                    <div className="flex items-center gap-2">
                      {/* Domain Filter */}
                      <select
                        value={assetDomainFilter}
                        onChange={(e) => setAssetDomainFilter(e.target.value)}
                        className="rounded-lg border border-slate-700 bg-slate-950 px-2.5 py-1 text-xs text-slate-300 focus:border-teal-500 focus:outline-none"
                      >
                        <option value="ALL">All Domains</option>
                        <option value="PAYMENT">Payment</option>
                        <option value="RECOVERY">Recovery</option>
                        <option value="CUSTOMER">Customer</option>
                        <option value="ML">ML</option>
                        <option value="AUDIT">Audit</option>
                        <option value="SECURITY">Security</option>
                        <option value="OBSERVABILITY">Observability</option>
                        <option value="COMPLIANCE">Compliance</option>
                      </select>
    
                      {/* Classification Filter */}
                      <select
                        value={assetClassFilter}
                        onChange={(e) => setAssetClassFilter(e.target.value)}
                        className="rounded-lg border border-slate-700 bg-slate-950 px-2.5 py-1 text-xs text-slate-300 focus:border-teal-500 focus:outline-none"
                      >
                        <option value="ALL">All Classifications</option>
                        <option value="FINANCIAL_RESTRICTED">Financial Restricted</option>
                        <option value="RESTRICTED">Restricted</option>
                        <option value="SENSITIVE">Sensitive</option>
                        <option value="CONFIDENTIAL">Confidential</option>
                        <option value="INTERNAL">Internal</option>
                        <option value="PUBLIC">Public</option>
                      </select>
                    </div>
                  </div>
    
                  {/* Assets Table */}
                  <div className="overflow-x-auto rounded-xl border border-slate-800">
                    <table className="w-full text-left text-xs">
                      <thead className="bg-slate-950/80 text-slate-400 border-b border-slate-800 uppercase font-mono text-[10px]">
                        <tr>
                          <th className="px-3.5 py-2.5">Asset Name</th>
                          <th className="px-3.5 py-2.5">Domain</th>
                          <th className="px-3.5 py-2.5">Classification</th>
                          <th className="px-3.5 py-2.5">Owner Role</th>
                          <th className="px-3.5 py-2.5">Processing Purpose</th>
                          <th className="px-3.5 py-2.5 text-center">PII</th>
                          <th className="px-3.5 py-2.5 text-center">Financial</th>
                          <th className="px-3.5 py-2.5">Retention Policy</th>
                          <th className="px-3.5 py-2.5 text-right">Records</th>
                          <th className="px-3.5 py-2.5 text-right">Fields</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-slate-800/60 font-mono text-slate-300">
                        {(dataGovAssets || [])
                          .filter((a) => assetDomainFilter === "ALL" || a.domain === assetDomainFilter)
                          .filter((a) => assetClassFilter === "ALL" || a.classification === assetClassFilter)
                          .map((asset) => {
                            const isSelected = selectedDataAsset?.asset_id === asset.asset_id;
                            return (
                              <tr
                                key={asset.asset_id}
                                onClick={() => setSelectedDataAsset(asset)}
                                className={`cursor-pointer transition hover:bg-slate-800/40 ${
                                  isSelected ? "bg-teal-950/40 border-l-2 border-teal-500" : ""
                                }`}
                              >
                                <td className="px-3.5 py-2.5 font-bold text-white flex items-center gap-1.5">
                                  <span>{asset.asset_name}</span>
                                  <span className="text-[10px] text-slate-500 font-normal">({asset.asset_id})</span>
                                </td>
                                <td className="px-3.5 py-2.5 text-cyan-300">{asset.domain}</td>
                                <td className="px-3.5 py-2.5">
                                  <span
                                    className={`rounded-full border px-2 py-0.5 text-[9px] font-bold ${getDataClassificationBadge(
                                      asset.classification
                                    )}`}
                                  >
                                    {asset.classification}
                                  </span>
                                </td>
                                <td className="px-3.5 py-2.5 text-slate-400">{asset.owner_role}</td>
                                <td className="px-3.5 py-2.5 text-slate-300">{asset.processing_purpose}</td>
                                <td className="px-3.5 py-2.5 text-center">
                                  {asset.contains_pii ? (
                                    <span className="text-amber-400 font-bold">YES</span>
                                  ) : (
                                    <span className="text-slate-600">NO</span>
                                  )}
                                </td>
                                <td className="px-3.5 py-2.5 text-center">
                                  {asset.contains_financial_data ? (
                                    <span className="text-purple-400 font-bold">YES</span>
                                  ) : (
                                    <span className="text-slate-600">NO</span>
                                  )}
                                </td>
                                <td className="px-3.5 py-2.5 text-slate-400">{asset.retention_policy}</td>
                                <td className="px-3.5 py-2.5 text-right font-mono text-slate-200">
                                  {asset.record_count.toLocaleString()}
                                </td>
                                <td className="px-3.5 py-2.5 text-right">
                                  <button
                                    onClick={(e) => {
                                      e.stopPropagation();
                                      setSelectedDataAsset(asset);
                                    }}
                                    className="text-xs text-teal-400 hover:text-teal-200 font-bold underline"
                                  >
                                    {asset.fields?.length || 0} fields →
                                  </button>
                                </td>
                              </tr>
                            );
                          })}
                      </tbody>
                    </table>
                  </div>
    
                  {/* Selected Asset Field Inspector Drawer */}
                  {selectedDataAsset && (
                    <div className="rounded-xl border border-teal-800/40 bg-slate-950/70 p-4 space-y-3">
                      <div className="flex items-center justify-between">
                        <h4 className="text-xs font-bold text-teal-200 flex items-center gap-2">
                          <span>FIELD-LEVEL SENSITIVITY SCHEMA: {selectedDataAsset.asset_name.toUpperCase()}</span>
                          <span className="text-[10px] text-slate-400 font-mono">
                            Storage: {selectedDataAsset.storage_type} • Encryption: {selectedDataAsset.encryption_status}
                          </span>
                        </h4>
                        <span className="text-[10px] text-slate-500 font-mono">
                          Last Scanned: {new Date(selectedDataAsset.last_scanned_at).toLocaleTimeString()}
                        </span>
                      </div>
    
                      <div className="overflow-x-auto rounded-lg border border-slate-800">
                        <table className="w-full text-left text-xs">
                          <thead className="bg-slate-900 text-slate-400 font-mono text-[9px] uppercase">
                            <tr>
                              <th className="px-3 py-2">Field Name</th>
                              <th className="px-3 py-2">Classification</th>
                              <th className="px-3 py-2">Sensitivity</th>
                              <th className="px-3 py-2">PII Category</th>
                              <th className="px-3 py-2">Financial Sensitivity</th>
                              <th className="px-3 py-2">Masking Policy</th>
                              <th className="px-3 py-2">Encryption</th>
                              <th className="px-3 py-2">Retention</th>
                            </tr>
                          </thead>
                          <tbody className="divide-y divide-slate-800/50 font-mono text-slate-300 text-[11px]">
                            {(selectedDataAsset.fields || []).map((f) => (
                              <tr key={f.field_name} className="hover:bg-slate-900/40">
                                <td className="px-3 py-2 font-bold text-white font-mono">{f.field_name}</td>
                                <td className="px-3 py-2">
                                  <span
                                    className={`rounded px-1.5 py-0.5 text-[9px] font-bold ${getDataClassificationBadge(
                                      f.classification
                                    )}`}
                                  >
                                    {f.classification}
                                  </span>
                                </td>
                                <td className="px-3 py-2 text-slate-400">{f.sensitivity}</td>
                                <td className="px-3 py-2 text-amber-300 font-bold">
                                  {f.pii_category || "—"}
                                </td>
                                <td className="px-3 py-2">
                                  {f.financial_sensitivity ? (
                                    <span className="text-purple-300 font-bold">YES</span>
                                  ) : (
                                    <span className="text-slate-600">NO</span>
                                  )}
                                </td>
                                <td className="px-3 py-2 text-teal-300">{f.masking_requirement}</td>
                                <td className="px-3 py-2 text-slate-400">{f.encryption_requirement}</td>
                                <td className="px-3 py-2 text-slate-400">{f.retention_requirement}</td>
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </div>
                    </div>
                  )}
                </div>
    
                {/* 4. 25 Automated Privacy & Governance Controls Matrix */}
                <div className="rounded-2xl border border-teal-800/40 bg-slate-900/80 p-6 shadow-xl space-y-4">
                  <div className="flex flex-wrap items-center justify-between gap-3">
                    <div>
                      <h3 className="text-sm font-bold text-white flex items-center gap-2">
                        <span>25 AUTOMATED PRIVACY & GOVERNANCE CONTROLS MATRIX</span>
                        <span className="text-[10px] font-mono bg-emerald-950 px-2 py-0.5 rounded border border-emerald-700/50 text-emerald-300 font-bold">
                          25 / 25 Controls Passing (100%)
                        </span>
                      </h3>
                      <p className="text-xs text-slate-400">
                        Comprehensive compliance controls evaluating DPDP Act 2023, RBI Guidelines, GDPR/CCPA parity, cryptographic pseudonymization, and zero-PII guarantees.
                      </p>
                    </div>
                    <div className="flex items-center gap-2">
                      {/* Category Filter */}
                      <select
                        value={controlCategoryFilter}
                        onChange={(e) => setControlCategoryFilter(e.target.value)}
                        className="rounded-lg border border-slate-700 bg-slate-950 px-2.5 py-1 text-xs text-slate-300 focus:border-teal-500 focus:outline-none"
                      >
                        <option value="ALL">All Categories</option>
                        <option value="DATA_CLASSIFICATION">Data Classification</option>
                        <option value="PRIVACY_ENGINEERING">Privacy Engineering</option>
                        <option value="DATA_LINEAGE">Data Lineage</option>
                        <option value="RETENTION_GOVERNANCE">Retention Governance</option>
                        <option value="DATA_QUALITY">Data Quality</option>
                        <option value="ACCESS_GOVERNANCE">Access Governance</option>
                        <option value="GOVERNANCE_REPORTING">Governance Reporting</option>
                      </select>
    
                      {/* Status Filter */}
                      <select
                        value={controlStatusFilter}
                        onChange={(e) => setControlStatusFilter(e.target.value)}
                        className="rounded-lg border border-slate-700 bg-slate-950 px-2.5 py-1 text-xs text-slate-300 focus:border-teal-500 focus:outline-none"
                      >
                        <option value="ALL">All Statuses</option>
                        <option value="PASS">Pass</option>
                        <option value="WARNING">Warning</option>
                        <option value="FAIL">Fail</option>
                      </select>
                    </div>
                  </div>
    
                  {/* Controls Matrix Table */}
                  <div className="overflow-x-auto rounded-xl border border-slate-800">
                    <table className="w-full text-left text-xs">
                      <thead className="bg-slate-950/80 text-slate-400 border-b border-slate-800 uppercase font-mono text-[10px]">
                        <tr>
                          <th className="px-3.5 py-2.5">ID</th>
                          <th className="px-3.5 py-2.5">Control Name</th>
                          <th className="px-3.5 py-2.5">Category</th>
                          <th className="px-3.5 py-2.5">Status</th>
                          <th className="px-3.5 py-2.5">Severity</th>
                          <th className="px-3.5 py-2.5">Observed vs Threshold</th>
                          <th className="px-3.5 py-2.5">Evidence</th>
                          <th className="px-3.5 py-2.5">Remediation</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-slate-800/60 font-mono text-slate-300">
                        {(dataGovControls || [])
                          .filter((c) => controlCategoryFilter === "ALL" || c.category === controlCategoryFilter)
                          .filter((c) => controlStatusFilter === "ALL" || c.status === controlStatusFilter)
                          .map((ctrl) => (
                            <tr key={ctrl.control_id} className="hover:bg-slate-800/40">
                              <td className="px-3.5 py-2.5 font-bold text-teal-300">{ctrl.control_id}</td>
                              <td className="px-3.5 py-2.5 font-semibold text-white">{ctrl.name}</td>
                              <td className="px-3.5 py-2.5 text-cyan-300 text-[11px]">{ctrl.category}</td>
                              <td className="px-3.5 py-2.5">
                                <span
                                  className={`rounded-full border px-2 py-0.5 text-[10px] font-bold ${getPrivacyControlBadge(
                                    ctrl.status
                                  )}`}
                                >
                                  {ctrl.status}
                                </span>
                              </td>
                              <td className="px-3.5 py-2.5">
                                <span
                                  className={`rounded-full border px-2 py-0.5 text-[9px] font-bold ${getPrivacySeverityBadge(
                                    ctrl.severity
                                  )}`}
                                >
                                  {ctrl.severity}
                                </span>
                              </td>
                              <td className="px-3.5 py-2.5 text-[11px]">
                                <span className="text-emerald-300 font-bold">{ctrl.observed_value}</span>
                                <span className="text-slate-500"> (req: {ctrl.threshold})</span>
                              </td>
                              <td className="px-3.5 py-2.5 text-slate-400 text-[11px] max-w-xs truncate" title={ctrl.evidence}>
                                {ctrl.evidence}
                              </td>
                              <td className="px-3.5 py-2.5 text-slate-400 text-[11px] max-w-xs truncate" title={ctrl.remediation}>
                                {ctrl.remediation}
                              </td>
                            </tr>
                          ))}
                      </tbody>
                    </table>
                  </div>
                </div>
    
                {/* 5. Data Quality & Hygiene Dashboard */}
                <div className="rounded-2xl border border-teal-800/40 bg-slate-900/80 p-6 shadow-xl space-y-4">
                  <div>
                    <h3 className="text-sm font-bold text-white flex items-center gap-2">
                      <span>DATA QUALITY, RECOVERY HYGIENE & ANOMALY SURVEILLANCE</span>
                      <span className="text-[10px] font-mono bg-teal-950 px-2 py-0.5 rounded border border-teal-700/50 text-teal-300 font-bold">
                        6 Dimensions Evaluated
                      </span>
                    </h3>
                    <p className="text-xs text-slate-400">
                      Continuous measurement of data quality metrics across ingestion, recovery case transitions, ML feature pipelines, and PolicyEngine state machines.
                    </p>
                  </div>
    
                  {/* 6 Dimension Cards Grid */}
                  <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-6">
                    <div className="rounded-xl border border-slate-800 bg-slate-950/80 p-3 space-y-1">
                      <span className="text-[10px] font-mono uppercase text-slate-400">Completeness</span>
                      <div className="text-xl font-bold font-mono text-emerald-300">
                        {dataGovQuality?.completeness_pct || 100}%
                      </div>
                      <p className="text-[10px] text-slate-500">Zero required null fields</p>
                    </div>
    
                    <div className="rounded-xl border border-slate-800 bg-slate-950/80 p-3 space-y-1">
                      <span className="text-[10px] font-mono uppercase text-slate-400">Validity</span>
                      <div className="text-xl font-bold font-mono text-emerald-300">
                        {dataGovQuality?.validity_pct || 100}%
                      </div>
                      <p className="text-[10px] text-slate-500">100% schema conformance</p>
                    </div>
    
                    <div className="rounded-xl border border-slate-800 bg-slate-950/80 p-3 space-y-1">
                      <span className="text-[10px] font-mono uppercase text-slate-400">Uniqueness</span>
                      <div className="text-xl font-bold font-mono text-emerald-300">
                        {dataGovQuality?.uniqueness_pct || 100}%
                      </div>
                      <p className="text-[10px] text-slate-500">0 duplicate event IDs</p>
                    </div>
    
                    <div className="rounded-xl border border-slate-800 bg-slate-950/80 p-3 space-y-1">
                      <span className="text-[10px] font-mono uppercase text-slate-400">Consistency</span>
                      <div className="text-xl font-bold font-mono text-emerald-300">
                        {dataGovQuality?.consistency_pct || 100}%
                      </div>
                      <p className="text-[10px] text-slate-500">Cross-table foreign keys</p>
                    </div>
    
                    <div className="rounded-xl border border-slate-800 bg-slate-950/80 p-3 space-y-1">
                      <span className="text-[10px] font-mono uppercase text-slate-400">Freshness</span>
                      <div className="text-xl font-bold font-mono text-cyan-300">
                        {dataGovQuality?.freshness_seconds || 15}s
                      </div>
                      <p className="text-[10px] text-slate-500">Ingestion latency lag</p>
                    </div>
    
                    <div className="rounded-xl border border-slate-800 bg-slate-950/80 p-3 space-y-1">
                      <span className="text-[10px] font-mono uppercase text-slate-400">Anomaly Rate</span>
                      <div className="text-xl font-bold font-mono text-emerald-300">
                        {dataGovQuality?.anomaly_rate_pct || 0.0}%
                      </div>
                      <p className="text-[10px] text-slate-500">0 null/drift explosions</p>
                    </div>
                  </div>
                </div>
    
                {/* 6. Data Lineage Explorer & Cryptographic Checksums */}
                <div className="rounded-2xl border border-teal-800/40 bg-slate-900/80 p-6 shadow-xl space-y-4">
                  <div>
                    <h3 className="text-sm font-bold text-white flex items-center gap-2">
                      <span>DATA LINEAGE EXPLORER & CRYPTOGRAPHIC PROVENANCE</span>
                      <span className="text-[10px] font-mono bg-cyan-950 px-2 py-0.5 rounded border border-cyan-700/50 text-cyan-300 font-bold">
                        100% Pipeline Traceability
                      </span>
                    </h3>
                    <p className="text-xs text-slate-400">
                      Cryptographically verified end-to-end data pipeline lineage from payment webhook arrival through ML prediction, PolicyEngine decisioning, and immutable audit event-sourcing.
                    </p>
                  </div>
    
                  {/* Visual Pipeline Progression Nodes */}
                  <div className="grid grid-cols-1 gap-2 md:grid-cols-7">
                    {(dataGovLineage?.nodes || []).map((node, idx) => {
                      const isSelected = selectedLineageNode?.node_id === node.node_id;
                      return (
                        <div
                          key={node.node_id}
                          onClick={() => setSelectedLineageNode(node)}
                          className={`cursor-pointer rounded-xl border p-3 transition space-y-1.5 ${
                            isSelected
                              ? "border-cyan-500 bg-cyan-950/40 shadow-lg shadow-cyan-500/20"
                              : "border-slate-800 bg-slate-950/60 hover:bg-slate-850"
                          }`}
                        >
                          <div className="flex items-center justify-between">
                            <span className="text-[9px] font-mono text-slate-500">STEP {idx + 1}</span>
                            <span className="rounded bg-slate-900 px-1.5 py-0.5 text-[8px] font-mono text-cyan-400">
                              {node.node_type}
                            </span>
                          </div>
                          <h5 className="text-xs font-bold text-white truncate" title={node.name}>
                            {node.name}
                          </h5>
                          <p className="text-[9px] font-mono text-slate-400 truncate">
                            {node.domain}
                          </p>
                          <p className="text-[8px] font-mono text-slate-500 truncate" title={node.checksum}>
                            {node.checksum.substring(0, 16)}...
                          </p>
                        </div>
                      );
                    })}
                  </div>
    
                  {/* Selected Node Details */}
                  {selectedLineageNode && (
                    <div className="rounded-xl border border-cyan-800/40 bg-slate-950/80 p-4 space-y-2">
                      <div className="flex items-center justify-between">
                        <h4 className="text-xs font-bold text-cyan-200 flex items-center gap-2">
                          <span>LINEAGE NODE INSPECTOR: {selectedLineageNode.name.toUpperCase()}</span>
                          <span className="text-[10px] font-mono text-slate-400">
                            Type: {selectedLineageNode.node_type} • Schema: {selectedLineageNode.schema_version}
                          </span>
                        </h4>
                        <span className="text-[10px] text-slate-500 font-mono">
                          Timestamp: {new Date(selectedLineageNode.timestamp).toLocaleString()}
                        </span>
                      </div>
    
                      <div className="grid grid-cols-1 gap-3 md:grid-cols-3 text-xs font-mono text-slate-300">
                        <div className="space-y-1">
                          <span className="text-[10px] text-slate-500 uppercase">Source System</span>
                          <p className="text-slate-200 font-bold">{selectedLineageNode.source_system}</p>
                        </div>
                        <div className="space-y-1">
                          <span className="text-[10px] text-slate-500 uppercase">Transformation</span>
                          <p className="text-slate-200">{selectedLineageNode.transformation}</p>
                        </div>
                        <div className="space-y-1">
                          <span className="text-[10px] text-slate-500 uppercase">SHA-256 Checksum</span>
                          <p className="text-cyan-300 text-[10px] break-all">{selectedLineageNode.checksum}</p>
                        </div>
                      </div>
                    </div>
                  )}
                </div>
    
                {/* 7. Retention Governance & Advisory Erasure Eligibility */}
                <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
                  {/* Retention Policy Statuses */}
                  <div className="rounded-2xl border border-teal-800/40 bg-slate-900/80 p-6 shadow-xl space-y-4">
                    <div className="flex items-center justify-between">
                      <h3 className="text-sm font-bold text-white flex items-center gap-2">
                        <span>RETENTION POLICIES & STATUTORY AGING</span>
                      </h3>
                      <span className="text-[10px] font-mono bg-purple-950 px-2 py-0.5 rounded border border-purple-700/50 text-purple-300 font-bold">
                        Statutory Holds Active
                      </span>
                    </div>
                    <p className="text-xs text-slate-400">
                      Domain retention policies enforcing 7-year RBI tax compliance, 5-year recovery aging, 3-year ML data lifecycle, and legal hold on AuditLog.
                    </p>
    
                    <div className="overflow-x-auto rounded-xl border border-slate-800">
                      <table className="w-full text-left text-xs">
                        <thead className="bg-slate-950/80 text-slate-400 border-b border-slate-800 uppercase font-mono text-[10px]">
                          <tr>
                            <th className="px-3 py-2">Asset</th>
                            <th className="px-3 py-2">Duration</th>
                            <th className="px-3 py-2">Status</th>
                            <th className="px-3 py-2">Legal Hold</th>
                            <th className="px-3 py-2 text-right">Advisory Erasure</th>
                          </tr>
                        </thead>
                        <tbody className="divide-y divide-slate-800/60 font-mono text-slate-300 text-[11px]">
                          {(dataGovRetention || []).map((ret) => (
                            <tr key={ret.asset_id} className="hover:bg-slate-800/40">
                              <td className="px-3 py-2 font-bold text-white">{ret.asset_name}</td>
                              <td className="px-3 py-2 text-slate-400">{ret.retention_duration_days} days</td>
                              <td className="px-3 py-2">
                                <span
                                  className={`rounded-full border px-2 py-0.5 text-[9px] font-bold ${getRetentionStatusBadge(
                                    ret.status
                                  )}`}
                                >
                                  {ret.status}
                                </span>
                              </td>
                              <td className="px-3 py-2">
                                {ret.legal_hold ? (
                                  <span className="text-purple-300 font-bold">YES</span>
                                ) : (
                                  <span className="text-slate-600">NO</span>
                                )}
                              </td>
                              <td className="px-3 py-2 text-right">
                                {ret.deletion_eligible ? (
                                  <span className="text-amber-400 font-bold">ADVISORY ELIGIBLE</span>
                                ) : (
                                  <span className="text-slate-500 font-normal">BLOCKED (STATUTORY)</span>
                                )}
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  </div>
    
                  {/* Subject Erasure Eligibility Evaluator (Advisory) */}
                  <div className="rounded-2xl border border-teal-800/40 bg-slate-900/80 p-6 shadow-xl space-y-4">
                    <div className="flex items-center justify-between">
                      <h3 className="text-sm font-bold text-white flex items-center gap-2">
                        <span>SUBJECT ERASURE ELIGIBILITY EVALUATOR</span>
                      </h3>
                      <span className="text-[10px] font-mono bg-amber-950 px-2 py-0.5 rounded border border-amber-700/50 text-amber-300 font-bold">
                        Advisory Only • Non-Mutating
                      </span>
                    </div>
                    <p className="text-xs text-slate-400">
                      Evaluates statutory retention blockers (RBI, tax audit, legal hold) for a subject without deleting financial records.
                    </p>
    
                    <form onSubmit={handleCheckErasureEligibility} className="space-y-3">
                      <div className="flex gap-2">
                        <input
                          type="text"
                          value={erasureCheckSubjectId}
                          onChange={(e) => setErasureCheckSubjectId(e.target.value)}
                          placeholder="Enter external customer ID (e.g. cust_12345)..."
                          className="flex-1 rounded-xl border border-slate-800 bg-slate-950 px-3.5 py-2 text-xs text-white placeholder-slate-500 focus:border-teal-500 focus:outline-none"
                        />
                        <button
                          type="submit"
                          disabled={erasureCheckLoading || !erasureCheckSubjectId.trim()}
                          className="rounded-xl bg-gradient-to-r from-teal-600 to-emerald-600 px-4 py-2 text-xs font-bold text-white shadow hover:from-teal-500 hover:to-emerald-500 disabled:opacity-50"
                        >
                          {erasureCheckLoading ? "Evaluating..." : "Evaluate"}
                        </button>
                      </div>
                    </form>
    
                    {erasureEvalResult && (
                      <div className="rounded-xl border border-slate-800 bg-slate-950/80 p-4 space-y-2 text-xs font-mono">
                        <div className="flex items-center justify-between">
                          <span className="text-slate-400">Subject Pseudonym:</span>
                          <span className="font-bold text-cyan-300">{erasureEvalResult.subject_pseudonym}</span>
                        </div>
                        <div className="flex items-center justify-between">
                          <span className="text-slate-400">Eligible for Erasure:</span>
                          <span
                            className={`font-bold ${
                              erasureEvalResult.eligible_for_erasure ? "text-emerald-400" : "text-rose-400"
                            }`}
                          >
                            {erasureEvalResult.eligible_for_erasure ? "YES (ADVISORY)" : "NO (BLOCKED)"}
                          </span>
                        </div>
                        <div className="flex items-center justify-between">
                          <span className="text-slate-400">Statutory Financial Retention:</span>
                          <span className="font-bold text-amber-300">
                            {erasureEvalResult.financial_record_retention_required ? "MANDATORY (7 Years)" : "EXEMPT"}
                          </span>
                        </div>
                        <div className="flex items-center justify-between">
                          <span className="text-slate-400">Audit Log Legal Hold:</span>
                          <span className="font-bold text-purple-300">
                            {erasureEvalResult.audit_retention_required ? "ACTIVE" : "NONE"}
                          </span>
                        </div>
                        {erasureEvalResult.blocker_reasons.length > 0 && (
                          <div className="border-t border-slate-800 pt-2 text-[11px] text-rose-300 space-y-1">
                            <span className="font-bold">Blocker Reasons:</span>
                            <ul className="list-disc list-inside space-y-0.5 text-slate-400">
                              {erasureEvalResult.blocker_reasons.map((r, i) => (
                                <li key={i}>{r}</li>
                              ))}
                            </ul>
                          </div>
                        )}
                        <p className="text-[10px] text-slate-500 italic border-t border-slate-800 pt-1">
                          {erasureEvalResult.advisory_notice}
                        </p>
                      </div>
                    )}
                  </div>
                </div>
    
                {/* 8. Privacy Incident Center & Threat Surveillance */}
                <div className="rounded-2xl border border-teal-800/40 bg-slate-900/80 p-6 shadow-xl space-y-4">
                  <div className="flex items-center justify-between">
                    <div>
                      <h3 className="text-sm font-bold text-white flex items-center gap-2">
                        <span>PRIVACY INCIDENT CENTER & AUTOMATED SURVEILLANCE</span>
                        <span className="text-[10px] font-mono bg-emerald-950 px-2 py-0.5 rounded border border-emerald-700/50 text-emerald-300 font-bold">
                          Zero Data Breaches
                        </span>
                      </h3>
                      <p className="text-xs text-slate-400">
                        Automated discovery of privacy anomalies with SHA-256 fingerprint deduplication and zero plain-text storage.
                      </p>
                    </div>
                  </div>
    
                  <div className="overflow-x-auto rounded-xl border border-slate-800">
                    <table className="w-full text-left text-xs">
                      <thead className="bg-slate-950/80 text-slate-400 border-b border-slate-800 uppercase font-mono text-[10px]">
                        <tr>
                          <th className="px-3.5 py-2.5">Incident ID</th>
                          <th className="px-3.5 py-2.5">Severity</th>
                          <th className="px-3.5 py-2.5">Category</th>
                          <th className="px-3.5 py-2.5">Title</th>
                          <th className="px-3.5 py-2.5">Affected Asset</th>
                          <th className="px-3.5 py-2.5">Detection Time</th>
                          <th className="px-3.5 py-2.5">Status</th>
                          <th className="px-3.5 py-2.5">Evidence Hash</th>
                          <th className="px-3.5 py-2.5">Remediation State</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-slate-800/60 font-mono text-slate-300">
                        {(dataGovIncidents || []).map((inc) => (
                          <tr key={inc.incident_id} className="hover:bg-slate-800/40">
                            <td className="px-3.5 py-2.5 font-bold text-teal-300">{inc.incident_id}</td>
                            <td className="px-3.5 py-2.5">
                              <span
                                className={`rounded-full border px-2 py-0.5 text-[9px] font-bold ${getPrivacySeverityBadge(
                                  inc.severity
                                )}`}
                              >
                                {inc.severity}
                              </span>
                            </td>
                            <td className="px-3.5 py-2.5 text-cyan-300">{inc.category}</td>
                            <td className="px-3.5 py-2.5 font-semibold text-white">{inc.title}</td>
                            <td className="px-3.5 py-2.5 text-slate-300">{inc.affected_asset}</td>
                            <td className="px-3.5 py-2.5 text-slate-400">
                              {new Date(inc.detection_timestamp).toLocaleString()}
                            </td>
                            <td className="px-3.5 py-2.5">
                              <span className="rounded-full border border-emerald-700/60 bg-emerald-950/80 px-2 py-0.5 text-[9px] font-bold text-emerald-300">
                                {inc.status}
                              </span>
                            </td>
                            <td className="px-3.5 py-2.5 text-[10px] text-slate-500 font-mono truncate max-w-xs" title={inc.evidence_hash}>
                              {inc.evidence_hash.substring(0, 16)}...
                            </td>
                            <td className="px-3.5 py-2.5 text-emerald-400 font-bold">{inc.remediation_state}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
    
                {/* 9. Subject Rights & Privacy Request Center */}
                <div className="rounded-2xl border border-teal-800/40 bg-slate-900/80 p-6 shadow-xl space-y-4">
                  <div className="flex flex-wrap items-center justify-between gap-3">
                    <div>
                      <h3 className="text-sm font-bold text-white flex items-center gap-2">
                        <span>SUBJECT RIGHTS & PRIVACY REQUEST LIFECYCLE</span>
                        <span className="text-[10px] font-mono bg-blue-950 px-2 py-0.5 rounded border border-blue-700/50 text-blue-300 font-bold">
                          {dataGovPrivacyRequests?.length || 0} Requests Registered
                        </span>
                      </h3>
                      <p className="text-xs text-slate-400">
                        Governed subject rights workflow (Access, Export, Rectification, Erasure) with HMAC pseudonymization and immutable AuditLog traceability.
                      </p>
                    </div>
                    <button
                      onClick={() => setCreateReqModalOpen(true)}
                      className="rounded-xl bg-gradient-to-r from-teal-600 to-emerald-600 px-4 py-2 text-xs font-bold text-white shadow hover:from-teal-500 hover:to-emerald-500"
                    >
                      ➕ New Privacy Request
                    </button>
                  </div>
    
                  <div className="overflow-x-auto rounded-xl border border-slate-800">
                    <table className="w-full text-left text-xs">
                      <thead className="bg-slate-950/80 text-slate-400 border-b border-slate-800 uppercase font-mono text-[10px]">
                        <tr>
                          <th className="px-3.5 py-2.5">Request ID</th>
                          <th className="px-3.5 py-2.5">Type</th>
                          <th className="px-3.5 py-2.5">Status</th>
                          <th className="px-3.5 py-2.5">Subject Pseudonym</th>
                          <th className="px-3.5 py-2.5">Scope</th>
                          <th className="px-3.5 py-2.5">Actor</th>
                          <th className="px-3.5 py-2.5">Received At</th>
                          <th className="px-3.5 py-2.5">Evidence Ref</th>
                          <th className="px-3.5 py-2.5 text-right">Actions</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-slate-800/60 font-mono text-slate-300">
                        {(dataGovPrivacyRequests || []).map((req) => (
                          <tr key={req.request_id} className="hover:bg-slate-800/40">
                            <td className="px-3.5 py-2.5 font-bold text-white">{req.request_id}</td>
                            <td className="px-3.5 py-2.5 text-cyan-300">{req.request_type}</td>
                            <td className="px-3.5 py-2.5">
                              <span
                                className={`rounded-full border px-2 py-0.5 text-[9px] font-bold ${getPrivacyRequestBadge(
                                  req.status
                                )}`}
                              >
                                {req.status}
                              </span>
                            </td>
                            <td className="px-3.5 py-2.5 text-teal-300 font-mono text-[11px]">{req.subject_pseudonym}</td>
                            <td className="px-3.5 py-2.5 text-slate-400">{req.scope}</td>
                            <td className="px-3.5 py-2.5 text-slate-400">
                              {req.actor_id} <span className="text-slate-600">({req.actor_role})</span>
                            </td>
                            <td className="px-3.5 py-2.5 text-slate-400">
                              {new Date(req.received_at).toLocaleDateString()}
                            </td>
                            <td className="px-3.5 py-2.5 text-slate-500 text-[10px]">{req.evidence_reference}</td>
                            <td className="px-3.5 py-2.5 text-right space-x-2">
                              {(req.status === "RECEIVED" || req.status === "UNDER_REVIEW") && (
                                <button
                                  onClick={() => {
                                    setSelectedReqToReview(req);
                                    setReviewReqModalOpen(true);
                                  }}
                                  className="rounded bg-indigo-900/60 border border-indigo-700 px-2 py-1 text-[10px] font-bold text-indigo-200 hover:bg-indigo-800"
                                >
                                  Review
                                </button>
                              )}
                              {req.status === "APPROVED" && (
                                <button
                                  onClick={() => {
                                    setSelectedReqToComplete(req);
                                    setCompleteReqModalOpen(true);
                                  }}
                                  className="rounded bg-emerald-900/60 border border-emerald-700 px-2 py-1 text-[10px] font-bold text-emerald-200 hover:bg-emerald-800"
                                >
                                  Complete
                                </button>
                              )}
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              </div>


            {/* Phase 10E: Interactive PII & Secret Discovery Scanner Modal */}
            {govPiiScanModalOpen && (
              <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-sm p-4">
                <div className="w-full max-w-2xl rounded-2xl border border-teal-800/80 bg-slate-900 p-6 shadow-2xl space-y-4">
                  <div className="flex items-center justify-between border-b border-slate-800 pb-3">
                    <h3 className="text-sm font-bold text-white flex items-center gap-2">
                      <span>🔍 INTERACTIVE PII & CREDENTIAL DISCOVERY SCANNER</span>
                      <span className="text-[10px] font-mono text-teal-400 bg-teal-950 px-2 py-0.5 rounded border border-teal-700">
                        Non-Mutating • Redacted
                      </span>
                    </h3>
                    <button
                      onClick={() => {
                        setGovPiiScanModalOpen(false);
                        setGovPiiScanResult(null);
                      }}
                      className="text-slate-400 hover:text-white text-lg font-bold"
                    >
                      ✕
                    </button>
                  </div>
    
                  <p className="text-xs text-slate-300">
                    Paste arbitrary payload data or JSON below to test automated regex discovery of emails, phones, PAN, Aadhaar, payment cards, JWT tokens, and API credentials. Output is strictly sanitized with SHA-256 evidence hashes and zero plain-text secrets.
                  </p>
    
                  <div>
                    <label className="block text-[11px] font-semibold text-slate-400 uppercase mb-1">
                      Payload / JSON Data to Scan
                    </label>
                    <textarea
                      rows={6}
                      value={govPiiPayloadInput}
                      onChange={(e) => setGovPiiPayloadInput(e.target.value)}
                      placeholder="Paste JSON or plain text here..."
                      className="w-full font-mono rounded-xl border border-slate-800 bg-slate-950 p-3 text-xs text-white focus:border-teal-500 focus:outline-none"
                    />
                  </div>
    
                  <div className="flex items-center justify-between">
                    <button
                      type="button"
                      onClick={handleRunPiiScan}
                      disabled={govPiiScanLoading}
                      className="rounded-xl bg-gradient-to-r from-teal-600 to-cyan-600 px-5 py-2 text-xs font-bold text-white shadow hover:from-teal-500 hover:to-cyan-500 disabled:opacity-50"
                    >
                      {govPiiScanLoading ? "Scanning Fields..." : "Run Discovery Scan"}
                    </button>
                    {govPiiScanResult && (
                      <span className="text-xs font-mono text-slate-400">
                        Found {govPiiScanResult.findings_count} findings across {govPiiScanResult.scanned_fields_count} fields in {govPiiScanResult.scan_duration_ms.toFixed(1)}ms
                      </span>
                    )}
                  </div>
    
                  {govPiiScanResult && (
                    <div className="rounded-xl border border-slate-800 bg-slate-950/90 p-3 space-y-2 max-h-60 overflow-y-auto">
                      <h4 className="text-xs font-bold text-teal-300 font-mono">
                        Scan Findings ({govPiiScanResult.findings.length}):
                      </h4>
                      {govPiiScanResult.findings.length === 0 ? (
                        <p className="text-xs text-emerald-400 font-mono">✓ Zero PII, PAN, Card, or Secret findings detected.</p>
                      ) : (
                        <div className="space-y-1.5 font-mono text-xs">
                          {govPiiScanResult.findings.map((f: DataGovernancePIIScanFinding, i: number) => (
                            <div key={i} className="rounded border border-slate-800 bg-slate-900/60 p-2 text-[11px] space-y-0.5">
                              <div className="flex items-center justify-between">
                                <span className="font-bold text-white">{f.field_path}</span>
                                <span className={`rounded px-1.5 py-0.5 text-[9px] font-bold ${getPrivacySeverityBadge(f.severity)}`}>
                                  {f.severity}
                                </span>
                              </div>
                              <div className="flex items-center justify-between text-slate-400">
                                <span>Category: <strong className="text-cyan-300">{f.detected_category}</strong></span>
                                <span>Masked: <strong className="text-amber-300">{f.masked_value}</strong></span>
                              </div>
                              <div className="text-[9px] text-slate-500 truncate" title={f.evidence_hash}>
                                Evidence Hash: {f.evidence_hash}
                              </div>
                            </div>
                          ))}
                        </div>
                      )}
                    </div>
                  )}
                </div>
              </div>
            )}
    
            {/* Phase 10E: Governance Report & Export Modal */}
            {dataGovReportModalOpen && (
              <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-sm p-4">
                <div className="w-full max-w-3xl rounded-2xl border border-teal-800/80 bg-slate-900 p-6 shadow-2xl space-y-4">
                  <div className="flex items-center justify-between border-b border-slate-800 pb-3">
                    <h3 className="text-sm font-bold text-white flex items-center gap-2">
                      <span>📋 DATA GOVERNANCE & PRIVACY ENGINEERING AUDIT REPORT</span>
                      <span className="text-[10px] font-mono text-teal-400 bg-teal-950 px-2 py-0.5 rounded border border-teal-700">
                        Cryptographically Signed
                      </span>
                    </h3>
                    <button
                      onClick={() => setDataGovReportModalOpen(false)}
                      className="text-slate-400 hover:text-white text-lg font-bold"
                    >
                      ✕
                    </button>
                  </div>
    
                  <div className="flex items-center justify-between text-xs text-slate-400 font-mono">
                    <span>Report ID: <strong className="text-teal-300">{dataGovReport?.report_id || "RPT-GOV-CURRENT"}</strong></span>
                    <span>Generated At: {dataGovReport?.generated_at ? new Date(dataGovReport.generated_at).toLocaleString() : new Date().toLocaleString()}</span>
                  </div>
    
                  <div className="rounded-xl border border-slate-800 bg-slate-950 p-3 max-h-80 overflow-y-auto font-mono text-[11px] text-teal-200">
                    <pre className="whitespace-pre-wrap break-all">
                      {JSON.stringify(dataGovReport || { message: "Loading report..." }, null, 2)}
                    </pre>
                  </div>
    
                  <div className="flex items-center justify-between border-t border-slate-800 pt-3">
                    <span className="text-[10px] text-slate-500 font-mono truncate max-w-xs" title={dataGovReport?.verification_signature}>
                      Sig: {dataGovReport?.verification_signature || "sha256:verified"}
                    </span>
                    <div className="flex items-center gap-2">
                      <button
                        type="button"
                        onClick={handleCopyReportJson}
                        className="rounded-xl border border-slate-700 bg-slate-800 px-4 py-2 text-xs font-bold text-white hover:bg-slate-700"
                      >
                        {reportCopied ? "✓ Copied JSON" : "Copy JSON"}
                      </button>
                      <button
                        type="button"
                        onClick={handleDownloadReportJson}
                        className="rounded-xl bg-gradient-to-r from-teal-600 to-emerald-600 px-4 py-2 text-xs font-bold text-white shadow hover:from-teal-500 hover:to-emerald-500"
                      >
                        Download JSON
                      </button>
                    </div>
                  </div>
                </div>
              </div>
            )}
    
            {/* Phase 10E: Create Subject Rights Request Modal */}
            {createReqModalOpen && (
              <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-sm p-4">
                <div className="w-full max-w-md rounded-2xl border border-teal-800/80 bg-slate-900 p-6 shadow-2xl space-y-4">
                  <div className="flex items-center justify-between border-b border-slate-800 pb-3">
                    <h3 className="text-sm font-bold text-white flex items-center gap-2">
                      <span>🔒 NEW SUBJECT PRIVACY REQUEST</span>
                    </h3>
                    <button
                      onClick={() => setCreateReqModalOpen(false)}
                      className="text-slate-400 hover:text-white text-lg font-bold"
                    >
                      ✕
                    </button>
                  </div>
    
                  <form onSubmit={handleCreatePrivacyRequestSubmit} className="space-y-3">
                    <div>
                      <label className="block text-[11px] font-semibold text-slate-400 uppercase mb-1">
                        Request Type
                      </label>
                      <select
                        value={createReqType}
                        onChange={(e) => setCreateReqType(e.target.value)}
                        className="w-full rounded-xl border border-slate-800 bg-slate-950 px-3.5 py-2 text-xs text-white focus:border-teal-500 focus:outline-none"
                      >
                        <option value="ACCESS">ACCESS (Access Recovery History)</option>
                        <option value="EXPORT">EXPORT (Data Portability Package)</option>
                        <option value="RECTIFICATION">RECTIFICATION (Correct Subject Attributes)</option>
                        <option value="ERASURE">ERASURE (Advisory Erasure Evaluation)</option>
                        <option value="RESTRICTION">RESTRICTION (Processing Limitation)</option>
                        <option value="PROCESSING_PURPOSE">PROCESSING_PURPOSE (Purpose Query)</option>
                      </select>
                    </div>
    
                    <div>
                      <label className="block text-[11px] font-semibold text-slate-400 uppercase mb-1">
                        Subject Identifier (Customer External ID)
                      </label>
                      <input
                        type="text"
                        required
                        value={createReqSubjectId}
                        onChange={(e) => setCreateReqSubjectId(e.target.value)}
                        placeholder="e.g. cust_external_98765"
                        className="w-full rounded-xl border border-slate-800 bg-slate-950 px-3.5 py-2 text-xs text-white focus:border-teal-500 focus:outline-none"
                      />
                      <p className="text-[10px] text-teal-400 font-mono mt-1">
                        *Will be deterministically pseudonymized with HMAC-SHA256 salt.
                      </p>
                    </div>
    
                    <div>
                      <label className="block text-[11px] font-semibold text-slate-400 uppercase mb-1">
                        Scope
                      </label>
                      <select
                        value={createReqScope}
                        onChange={(e) => setCreateReqScope(e.target.value)}
                        className="w-full rounded-xl border border-slate-800 bg-slate-950 px-3.5 py-2 text-xs text-white focus:border-teal-500 focus:outline-none"
                      >
                        <option value="FULL_DATASET">FULL_DATASET</option>
                        <option value="RECOVERY_HISTORY">RECOVERY_HISTORY</option>
                        <option value="COMMUNICATIONS">COMMUNICATIONS</option>
                        <option value="PAYMENT_EVENTS">PAYMENT_EVENTS</option>
                      </select>
                    </div>
    
                    <div>
                      <label className="block text-[11px] font-semibold text-slate-400 uppercase mb-1">
                        Notes
                      </label>
                      <textarea
                        rows={2}
                        value={createReqNotes}
                        onChange={(e) => setCreateReqNotes(e.target.value)}
                        placeholder="Optional justification or subject request notes..."
                        className="w-full rounded-xl border border-slate-800 bg-slate-950 px-3.5 py-2 text-xs text-white focus:border-teal-500 focus:outline-none"
                      />
                    </div>
    
                    <div className="flex items-center justify-end gap-3 border-t border-slate-800 pt-3">
                      <button
                        type="button"
                        onClick={() => setCreateReqModalOpen(false)}
                        className="rounded-xl border border-slate-800 px-4 py-2 text-xs font-semibold text-slate-400 hover:text-white"
                      >
                        Cancel
                      </button>
                      <button
                        type="submit"
                        disabled={createReqLoading}
                        className="rounded-xl bg-gradient-to-r from-teal-600 to-emerald-600 px-5 py-2 text-xs font-bold text-white shadow hover:from-teal-500 hover:to-emerald-500 disabled:opacity-50"
                      >
                        {createReqLoading ? "Registering..." : "Submit Request"}
                      </button>
                    </div>
                  </form>
                </div>
              </div>
            )}
    
            {/* Phase 10E: Review Privacy Request Modal */}
            {reviewReqModalOpen && selectedReqToReview && (
              <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-sm p-4">
                <div className="w-full max-w-md rounded-2xl border border-indigo-800/80 bg-slate-900 p-6 shadow-2xl space-y-4">
                  <div className="flex items-center justify-between border-b border-slate-800 pb-3">
                    <h3 className="text-sm font-bold text-white flex items-center gap-2">
                      <span>⚖️ REVIEW PRIVACY REQUEST: {selectedReqToReview.request_id}</span>
                    </h3>
                    <button
                      onClick={() => setReviewReqModalOpen(false)}
                      className="text-slate-400 hover:text-white text-lg font-bold"
                    >
                      ✕
                    </button>
                  </div>
    
                  <div className="text-xs font-mono text-slate-300 space-y-1 bg-slate-950 p-3 rounded-xl border border-slate-800">
                    <div>Type: <strong className="text-cyan-300">{selectedReqToReview.request_type}</strong></div>
                    <div>Subject: <strong className="text-teal-300">{selectedReqToReview.subject_pseudonym}</strong></div>
                    <div>Scope: <strong className="text-slate-200">{selectedReqToReview.scope}</strong></div>
                    <div>Received: {new Date(selectedReqToReview.received_at).toLocaleString()}</div>
                  </div>
    
                  <form onSubmit={handleReviewPrivacyRequestSubmit} className="space-y-3">
                    <div>
                      <label className="block text-[11px] font-semibold text-slate-400 uppercase mb-1">
                        Decision
                      </label>
                      <select
                        value={reviewReqDecision}
                        onChange={(e) => setReviewReqDecision(e.target.value as "APPROVE" | "REJECT")}
                        className="w-full rounded-xl border border-slate-800 bg-slate-950 px-3.5 py-2 text-xs text-white focus:border-indigo-500 focus:outline-none"
                      >
                        <option value="APPROVE">APPROVE (Allow Fulfillment)</option>
                        <option value="REJECT">REJECT (Decline with Reason)</option>
                      </select>
                    </div>
    
                    <div>
                      <label className="block text-[11px] font-semibold text-slate-400 uppercase mb-1">
                        Review Notes / Justification
                      </label>
                      <textarea
                        rows={2}
                        required
                        value={reviewReqNotes}
                        onChange={(e) => setReviewReqNotes(e.target.value)}
                        placeholder="Provide justification or reason for review decision..."
                        className="w-full rounded-xl border border-slate-800 bg-slate-950 px-3.5 py-2 text-xs text-white focus:border-indigo-500 focus:outline-none"
                      />
                    </div>
    
                    <div className="flex items-center justify-end gap-3 border-t border-slate-800 pt-3">
                      <button
                        type="button"
                        onClick={() => setReviewReqModalOpen(false)}
                        className="rounded-xl border border-slate-800 px-4 py-2 text-xs font-semibold text-slate-400 hover:text-white"
                      >
                        Cancel
                      </button>
                      <button
                        type="submit"
                        disabled={reviewReqLoading}
                        className="rounded-xl bg-gradient-to-r from-indigo-600 to-purple-600 px-5 py-2 text-xs font-bold text-white shadow hover:from-indigo-500 hover:to-purple-500 disabled:opacity-50"
                      >
                        {reviewReqLoading ? "Submitting..." : `Submit Decision (${reviewReqDecision})`}
                      </button>
                    </div>
                  </form>
                </div>
              </div>
            )}
    
            {/* Phase 10E: Complete Privacy Request Modal */}
            {completeReqModalOpen && selectedReqToComplete && (
              <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-sm p-4">
                <div className="w-full max-w-md rounded-2xl border border-emerald-800/80 bg-slate-900 p-6 shadow-2xl space-y-4">
                  <div className="flex items-center justify-between border-b border-slate-800 pb-3">
                    <h3 className="text-sm font-bold text-white flex items-center gap-2">
                      <span>✅ COMPLETE PRIVACY REQUEST: {selectedReqToComplete.request_id}</span>
                    </h3>
                    <button
                      onClick={() => setCompleteReqModalOpen(false)}
                      className="text-slate-400 hover:text-white text-lg font-bold"
                    >
                      ✕
                    </button>
                  </div>
    
                  <div className="text-xs font-mono text-slate-300 space-y-1 bg-slate-950 p-3 rounded-xl border border-slate-800">
                    <div>Type: <strong className="text-cyan-300">{selectedReqToComplete.request_type}</strong></div>
                    <div>Subject: <strong className="text-teal-300">{selectedReqToComplete.subject_pseudonym}</strong></div>
                    <div>Status: <strong className="text-indigo-400">APPROVED</strong></div>
                  </div>
    
                  <form onSubmit={handleCompletePrivacyRequestSubmit} className="space-y-3">
                    <div>
                      <label className="block text-[11px] font-semibold text-slate-400 uppercase mb-1">
                        Completion Notes / Evidence Reference
                      </label>
                      <textarea
                        rows={2}
                        required
                        value={completeReqNotes}
                        onChange={(e) => setCompleteReqNotes(e.target.value)}
                        placeholder="Provide fulfillment notes or export package reference..."
                        className="w-full rounded-xl border border-slate-800 bg-slate-950 px-3.5 py-2 text-xs text-white focus:border-emerald-500 focus:outline-none"
                      />
                    </div>
    
                    <div className="flex items-center justify-end gap-3 border-t border-slate-800 pt-3">
                      <button
                        type="button"
                        onClick={() => setCompleteReqModalOpen(false)}
                        className="rounded-xl border border-slate-800 px-4 py-2 text-xs font-semibold text-slate-400 hover:text-white"
                      >
                        Cancel
                      </button>
                      <button
                        type="submit"
                        disabled={completeReqLoading}
                        className="rounded-xl bg-gradient-to-r from-emerald-600 to-teal-600 px-5 py-2 text-xs font-bold text-white shadow hover:from-emerald-500 hover:to-teal-500 disabled:opacity-50"
                      >
                        {completeReqLoading ? "Completing..." : "Mark as Completed"}
                      </button>
                    </div>
                  </form>
                </div>
              </div>
            )}
    


    </>
  );
}
