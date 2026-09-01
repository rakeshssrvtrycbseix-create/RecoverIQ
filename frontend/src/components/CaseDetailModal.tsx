"use client";

import React, { useEffect, useState } from "react";
import {
  fetchRecoveryCaseDetail,
  formatINR,
  RecoveryCaseDetailResponse,
} from "../lib/api";

interface CaseDetailModalProps {
  caseId: string;
  onClose: () => void;
}

export default function CaseDetailModal({
  caseId,
  onClose,
}: CaseDetailModalProps) {
  const [detail, setDetail] = useState<RecoveryCaseDetailResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function load() {
      setLoading(true);
      setError(null);
      try {
        const data = await fetchRecoveryCaseDetail(caseId);
        setDetail(data);
      } catch (err) {
        setError(err instanceof Error ? err.message : "Failed to load details");
      } finally {
        setLoading(false);
      }
    }
    load();
  }, [caseId]);

  const getStatusBadge = (status: string) => {
    switch (status) {
      case "RECOVERED":
      case "SUCCESS":
      case "ALLOWED":
        return "bg-emerald-950/60 text-emerald-400 border-emerald-800/40";
      case "HUMAN_REVIEW":
      case "SCHEDULED":
      case "IN_RECOVERY":
        return "bg-amber-950/60 text-amber-400 border-amber-800/40";
      case "EXECUTING":
        return "bg-cyan-950/60 text-cyan-400 border-cyan-800/40";
      case "FAILED":
      case "BLOCKED":
        return "bg-rose-950/60 text-rose-400 border-rose-800/40";
      default:
        return "bg-slate-800 text-slate-300 border-slate-700";
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/80 p-4 backdrop-blur-sm">
      <div className="relative max-h-[90vh] w-full max-w-4xl overflow-y-auto rounded-2xl border border-slate-800 bg-slate-900 shadow-2xl p-6 text-slate-200">
        {/* Modal Close Button */}
        <button
          onClick={onClose}
          className="absolute right-5 top-5 rounded-lg p-1.5 text-slate-400 hover:bg-slate-800 hover:text-white transition-colors"
        >
          <svg
            className="h-5 w-5"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth="2"
              d="M6 18L18 6M6 6l12 12"
            />
          </svg>
        </button>

        {loading ? (
          <div className="flex h-64 items-center justify-center space-x-2">
            <div className="h-4 w-4 animate-spin rounded-full border-2 border-indigo-500 border-t-transparent" />
            <span className="text-sm text-slate-400">
              Loading recovery lifecycle trail...
            </span>
          </div>
        ) : error || !detail ? (
          <div className="p-8 text-center">
            <p className="text-sm text-rose-400">{error || "Case not found"}</p>
            <button
              onClick={onClose}
              className="mt-4 rounded-lg bg-slate-800 px-4 py-2 text-xs font-semibold text-white hover:bg-slate-700"
            >
              Close
            </button>
          </div>
        ) : (
          <div className="space-y-6">
            {/* Header */}
            <div className="border-b border-slate-800 pb-4">
              <div className="flex flex-wrap items-center gap-2">
                <span className="text-xs font-mono text-indigo-400">
                  Case ID: {detail.case.id}
                </span>
                <span
                  className={`rounded-full border px-2.5 py-0.5 text-xs font-semibold ${getStatusBadge(
                    detail.case.status
                  )}`}
                >
                  {detail.case.status}
                </span>
                <span className="rounded-full border border-slate-700 bg-slate-800 px-2.5 py-0.5 text-xs text-slate-300">
                  Stage: {detail.case.recovery_stage}
                </span>
              </div>

              <div className="mt-3 flex flex-wrap items-baseline justify-between gap-4">
                <div>
                  <span className="text-2xl font-bold text-white">
                    {formatINR(detail.case.amount_at_risk)}
                  </span>
                  <span className="ml-2 text-xs text-slate-400">
                    Amount at Risk ({detail.case.total_attempts_count}/
                    {detail.case.max_allowed_attempts} attempts)
                  </span>
                </div>
                {detail.case.recovered_amount > 0 && (
                  <div className="text-right">
                    <span className="text-lg font-bold text-emerald-400">
                      {formatINR(detail.case.recovered_amount)}
                    </span>
                    <span className="block text-xs text-slate-400">
                      Recovered
                    </span>
                  </div>
                )}
              </div>
            </div>

            {/* Context Grids: Customer & Payment */}
            <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
              <div className="rounded-xl border border-slate-800/80 bg-slate-950/40 p-4">
                <span className="text-xs font-semibold uppercase tracking-wider text-slate-400">
                  Customer Profile (Strict Zero-PII)
                </span>
                <div className="mt-3 space-y-1.5 text-xs">
                  <div className="flex justify-between">
                    <span className="text-slate-400">Customer Identifier:</span>
                    <span className="font-mono text-slate-200">
                      {detail.customer.external_customer_id}
                    </span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-slate-400">Risk Tier:</span>
                    <span className="font-semibold text-indigo-400">
                      {detail.customer.risk_tier}
                    </span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-slate-400">Lifetime History:</span>
                    <span className="text-slate-200">
                      {detail.customer.recovered_payments_count} recovered /{" "}
                      {detail.customer.total_payments_count} total
                    </span>
                  </div>
                  <div className="flex justify-between text-emerald-400 text-[11px] font-medium pt-1">
                    <span>PII Protection:</span>
                    <span>100% Redacted / Excluded</span>
                  </div>
                </div>
              </div>

              <div className="rounded-xl border border-slate-800/80 bg-slate-950/40 p-4">
                <span className="text-xs font-semibold uppercase tracking-wider text-slate-400">
                  Payment Order Details
                </span>
                <div className="mt-3 space-y-1.5 text-xs">
                  <div className="flex justify-between">
                    <span className="text-slate-400">Order ID:</span>
                    <span className="font-mono text-slate-200">
                      {detail.payment.razorpay_order_id || "—"}
                    </span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-slate-400">Invoice ID:</span>
                    <span className="font-mono text-slate-200">
                      {detail.payment.razorpay_invoice_id || "—"}
                    </span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-slate-400">Failure Reason:</span>
                    <span className="font-medium text-rose-400">
                      {detail.case.latest_failure_reason || "unknown"}
                    </span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-slate-400">Opened At:</span>
                    <span className="text-slate-200">
                      {new Date(detail.case.opened_at).toLocaleString()}
                    </span>
                  </div>
                </div>
              </div>
            </div>

            {/* ML & AI Recommendations */}
            <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
              {/* ML Prediction */}
              <div className="rounded-xl border border-indigo-950 bg-indigo-950/20 p-4">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-semibold uppercase tracking-wider text-indigo-400">
                    Phase 5 ML Prediction
                  </span>
                  {detail.predictions.length > 0 && (
                    <span className="rounded-full bg-indigo-900/60 px-2 py-0.5 text-[10px] font-bold text-indigo-300">
                      {detail.predictions[0].priority} Priority
                    </span>
                  )}
                </div>

                {detail.predictions.length === 0 ? (
                  <p className="mt-2 text-xs text-slate-400">
                    No ML prediction computed
                  </p>
                ) : (
                  <div className="mt-3 space-y-1.5 text-xs">
                    <div className="flex justify-between">
                      <span className="text-slate-400">Recovery Prob:</span>
                      <span className="font-bold text-indigo-300">
                        {(
                          detail.predictions[0].recovery_probability * 100
                        ).toFixed(1)}
                        %
                      </span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-slate-400">Risk Score:</span>
                      <span className="text-slate-200">
                        {(detail.predictions[0].risk_score * 100).toFixed(1)}%
                      </span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-slate-400">Model:</span>
                      <span className="text-slate-300 font-mono text-[10px]">
                        {detail.predictions[0].model_name} (
                        {detail.predictions[0].model_version})
                      </span>
                    </div>
                  </div>
                )}
              </div>

              {/* Advisory AI Recommendation */}
              <div className="rounded-xl border border-cyan-950 bg-cyan-950/20 p-4">
                <span className="text-xs font-semibold uppercase tracking-wider text-cyan-400">
                  Phase 6B Advisory AI Decision
                </span>
                {detail.agent_decisions.length === 0 ? (
                  <p className="mt-2 text-xs text-slate-400">
                    No AI decision generated
                  </p>
                ) : (
                  <div className="mt-3 space-y-1.5 text-xs">
                    <div className="flex justify-between">
                      <span className="text-slate-400">Proposed Action:</span>
                      <span className="font-semibold text-cyan-300">
                        {detail.agent_decisions[0].proposed_action_type}
                      </span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-slate-400">Confidence:</span>
                      <span className="font-bold text-cyan-300">
                        {(
                          detail.agent_decisions[0].confidence_score * 100
                        ).toFixed(1)}
                        %
                      </span>
                    </div>
                    <div className="mt-2 rounded bg-slate-900/80 p-2 text-[11px] text-slate-300 italic border border-slate-800">
                      &quot;{detail.agent_decisions[0].reasoning_summary}&quot;
                    </div>
                  </div>
                )}
              </div>
            </div>

            {/* Authoritative Policy Decision */}
            <div className="rounded-xl border border-slate-800 bg-slate-950/50 p-4">
              <span className="text-xs font-semibold uppercase tracking-wider text-slate-400">
                Phase 6C Deterministic Policy Engine (Authoritative)
              </span>

              {detail.policy_decisions.length === 0 ? (
                <p className="mt-2 text-xs text-slate-400">
                  No policy evaluation recorded
                </p>
              ) : (
                <div className="mt-3 space-y-2 text-xs">
                  {detail.policy_decisions.map((pd) => (
                    <div
                      key={pd.id}
                      className="rounded-lg border border-slate-800/80 bg-slate-900/60 p-3 space-y-1"
                    >
                      <div className="flex items-center justify-between">
                        <span
                          className={`rounded-full border px-2 py-0.5 text-[10px] font-bold ${getStatusBadge(
                            pd.evaluation_result
                          )}`}
                        >
                          {pd.evaluation_result}
                        </span>
                        <span className="text-[10px] text-slate-400">
                          {new Date(pd.decided_at).toLocaleString()}
                        </span>
                      </div>
                      {pd.rule_name && (
                        <span className="block font-medium text-slate-300">
                          Rule: {pd.rule_name}{" "}
                          {pd.triggered_rule_code &&
                            `(${pd.triggered_rule_code})`}
                        </span>
                      )}
                      <p className="text-slate-400">{pd.decision_reason}</p>
                    </div>
                  ))}
                </div>
              )}
            </div>

            {/* Recovery Actions & Executions */}
            <div className="rounded-xl border border-slate-800 bg-slate-950/50 p-4">
              <span className="text-xs font-semibold uppercase tracking-wider text-slate-400">
                Action Scheduling & Execution History
              </span>

              {detail.actions.length === 0 ? (
                <p className="mt-2 text-xs text-slate-400">
                  No recovery actions scheduled yet
                </p>
              ) : (
                <div className="mt-3 space-y-3">
                  {detail.actions.map((act) => (
                    <div
                      key={act.id}
                      className="rounded-lg border border-slate-800 bg-slate-900/80 p-3 space-y-2 text-xs"
                    >
                      <div className="flex items-center justify-between">
                        <span className="font-mono font-medium text-indigo-300">
                          {act.action_type}
                        </span>
                        <span
                          className={`rounded-full border px-2 py-0.5 text-[10px] font-bold ${getStatusBadge(
                            act.status
                          )}`}
                        >
                          {act.status}
                        </span>
                      </div>
                      <div className="grid grid-cols-2 gap-2 text-[11px] text-slate-400">
                        <div>
                          Scheduled for:{" "}
                          <span className="text-slate-200">
                            {new Date(act.scheduled_for).toLocaleString()}
                          </span>
                        </div>
                        {act.dispatched_at && (
                          <div>
                            Dispatched at:{" "}
                            <span className="text-slate-200">
                              {new Date(act.dispatched_at).toLocaleString()}
                            </span>
                          </div>
                        )}
                      </div>

                      {act.results.length > 0 && (
                        <div className="border-t border-slate-800 pt-2 space-y-1">
                          <span className="text-[10px] font-semibold text-slate-400 uppercase">
                            Provider Outcomes
                          </span>
                          {act.results.map((res) => (
                            <div
                              key={res.id}
                              className="flex items-center justify-between text-[11px] bg-slate-950/40 p-1.5 rounded"
                            >
                              <span
                                className={`font-semibold ${
                                  res.execution_status === "SUCCESS"
                                    ? "text-emerald-400"
                                    : res.execution_status === "TIMED_OUT"
                                    ? "text-amber-400"
                                    : "text-rose-400"
                                }`}
                              >
                                {res.execution_status}
                              </span>
                              <span className="font-mono text-[10px] text-slate-400">
                                {res.provider_reference_id}
                              </span>
                            </div>
                          ))}
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              )}
            </div>

            {/* Audit Trail Log */}
            <div className="rounded-xl border border-slate-800 bg-slate-950/50 p-4">
              <span className="text-xs font-semibold uppercase tracking-wider text-slate-400">
                Immutable Audit Trail ({detail.audit_logs.length} events)
              </span>

              <div className="mt-3 max-h-48 overflow-y-auto space-y-2 pr-1">
                {detail.audit_logs.map((log) => (
                  <div
                    key={log.id}
                    className="flex items-start justify-between rounded border border-slate-800/60 bg-slate-900/40 p-2 text-xs"
                  >
                    <div>
                      <span className="font-mono font-semibold text-indigo-300">
                        {log.event_type}
                      </span>
                      <span className="ml-2 text-[10px] text-slate-400">
                        by {log.actor_id} ({log.actor_type})
                      </span>
                    </div>
                    <span className="text-[10px] text-slate-400 whitespace-nowrap">
                      {new Date(log.created_at).toLocaleTimeString()}
                    </span>
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
