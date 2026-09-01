"use client";

import React, { useCallback, useEffect, useState } from "react";
import CaseDetailModal from "../../components/CaseDetailModal";
import HumanReviewModal from "../../components/HumanReviewModal";
import Navbar from "../../components/Navbar";
import {
  fetchHumanReviewQueue,
  formatINR,
  HumanReviewQueueItem,
  PaginatedHumanReviewResponse,
} from "../../lib/api";
import { getStoredSession, UserSession } from "../../lib/auth";

export default function HumanReviewQueuePage() {
  const [queue, setQueue] = useState<PaginatedHumanReviewResponse | null>(null);
  const [session] = useState<UserSession>(getStoredSession);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [notification, setNotification] = useState<string | null>(null);

  // Modal states
  const [inspectCaseId, setInspectCaseId] = useState<string | null>(null);
  const [actionItem, setActionItem] = useState<{
    item: HumanReviewQueueItem;
    action: "APPROVE" | "DISMISS";
  } | null>(null);

  const loadQueue = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await fetchHumanReviewQueue();
      setQueue(data);
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : "Failed to load human review queue"
      );
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    let ignore = false;
    async function execute() {
      try {
        const data = await fetchHumanReviewQueue();
        if (!ignore) {
          setQueue(data);
          setError(null);
          setLoading(false);
        }
      } catch (err) {
        if (!ignore) {
          setError(
            err instanceof Error
              ? err.message
              : "Failed to load human review queue"
          );
          setLoading(false);
        }
      }
    }
    execute();
    return () => {
      ignore = true;
    };
  }, []);

  const handleActionSuccess = (msg: string) => {
    setNotification(msg);
    loadQueue();
    setTimeout(() => setNotification(null), 6000);
  };

  const isViewerOnly = session?.role === "viewer";

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 antialiased">
      <Navbar />

      <main className="mx-auto max-w-7xl px-4 py-8 sm:px-6 lg:px-8 space-y-6">
        {/* Header */}
        <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between border-b border-slate-800/80 pb-6">
          <div>
            <div className="flex items-center gap-2">
              <h1 className="text-2xl font-black tracking-tight text-white">
                Human Review Queue
              </h1>
              {queue && queue.total > 0 && (
                <span className="rounded-full bg-amber-500/20 border border-amber-500/40 px-2.5 py-0.5 text-xs font-bold text-amber-300">
                  {queue.total} Pending
                </span>
              )}
            </div>
            <p className="text-xs text-slate-400 mt-1">
              Deterministic Policy Engine safety clearance queue for high-risk or threshold recoveries
            </p>
          </div>

          <button
            onClick={loadQueue}
            disabled={loading}
            className="flex items-center gap-2 rounded-xl border border-slate-800 bg-slate-900 px-4 py-2 text-xs font-semibold text-slate-200 hover:bg-slate-800"
          >
            <svg
              className={`h-3.5 w-3.5 ${loading ? "animate-spin text-indigo-400" : ""}`}
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth="2"
                d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"
              />
            </svg>
            <span>Refresh Queue</span>
          </button>
        </div>

        {/* Notification Toast */}
        {notification && (
          <div className="rounded-xl border border-emerald-800/50 bg-emerald-950/60 p-4 text-xs font-medium text-emerald-300 shadow-lg animate-fade-in">
            {notification}
          </div>
        )}

        {error && (
          <div className="rounded-xl border border-rose-800/40 bg-rose-950/40 p-4 text-xs text-rose-300">
            {error}
          </div>
        )}

        {/* Informational Guidance Alert */}
        <div className="rounded-2xl border border-indigo-900/40 bg-indigo-950/20 p-4 text-xs text-indigo-300">
          <div className="flex items-start gap-3">
            <svg
              className="h-5 w-5 text-indigo-400 mt-0.5 shrink-0"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth="2"
                d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
              />
            </svg>
            <div>
              <strong className="font-semibold text-white">
                Human-in-the-Loop Safety Clearance
              </strong>
              <p className="text-slate-400 mt-0.5">
                AI recommendations are advisory. When a case triggers human review, verified operator authorization creates an authoritative ALLOWED PolicyDecision and dispatches the recovery action.
              </p>
            </div>
          </div>
        </div>

        {/* Queue Items */}
        {loading && !queue ? (
          <div className="flex h-64 items-center justify-center space-x-2">
            <div className="h-4 w-4 animate-spin rounded-full border-2 border-indigo-500 border-t-transparent" />
            <span className="text-xs text-slate-400">
              Loading review queue...
            </span>
          </div>
        ) : !queue || queue.items.length === 0 ? (
          <div className="rounded-2xl border border-slate-800 bg-slate-900/40 p-12 text-center">
            <div className="mx-auto flex h-12 w-12 items-center justify-center rounded-full bg-emerald-950/60 border border-emerald-800/40 text-emerald-400 mb-3">
              <svg
                className="h-6 w-6"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth="2"
                  d="M5 13l4 4L19 7"
                />
              </svg>
            </div>
            <h3 className="text-base font-bold text-white">
              Queue Clear — No Pending Human Reviews
            </h3>
            <p className="mt-1 text-xs text-slate-400">
              All automated recovery decisions have passed deterministic policy clearance without safety triggers.
            </p>
          </div>
        ) : (
          <div className="grid grid-cols-1 gap-6 md:grid-cols-2">
            {queue.items.map((item) => (
              <div
                key={item.case_id}
                className="rounded-2xl border border-slate-800 bg-slate-900/60 p-5 shadow-lg backdrop-blur-sm space-y-4 hover:border-slate-700 transition-all flex flex-col justify-between"
              >
                <div className="space-y-3">
                  {/* Top Bar */}
                  <div className="flex items-center justify-between border-b border-slate-800 pb-3">
                    <div className="flex items-center gap-2">
                      <span className="font-mono text-xs font-bold text-indigo-400">
                        {item.case_id.slice(0, 8)}...
                      </span>
                      <span className="rounded-full bg-amber-950/60 border border-amber-800/40 px-2 py-0.5 text-[10px] font-bold text-amber-400">
                        HUMAN_REVIEW
                      </span>
                    </div>

                    <span className="text-[11px] font-mono text-slate-400">
                      Tier:{" "}
                      <strong className="text-slate-200">
                        {item.customer_risk_tier}
                      </strong>
                    </span>
                  </div>

                  {/* Financial & Reason */}
                  <div className="flex items-baseline justify-between">
                    <div>
                      <span className="text-xl font-bold text-white">
                        {formatINR(item.amount_at_risk)}
                      </span>
                      <span className="ml-2 text-[11px] text-slate-400">
                        at risk
                      </span>
                    </div>
                    <span className="text-xs font-medium text-rose-400 bg-rose-950/30 border border-rose-900/40 px-2 py-0.5 rounded">
                      {item.latest_failure_reason || "unknown"}
                    </span>
                  </div>

                  {/* Policy Flag Reason */}
                  <div className="rounded-xl border border-amber-950/60 bg-amber-950/20 p-3 space-y-1 text-xs">
                    <span className="text-[10px] font-bold uppercase tracking-wider text-amber-400">
                      Triggered Safety Rule: {item.rule_name || item.triggered_rule_code}
                    </span>
                    <p className="text-slate-300 text-[11px]">
                      {item.policy_decision_reason}
                    </p>
                  </div>

                  {/* AI Recommendation */}
                  {item.proposed_action_type && (
                    <div className="rounded-xl border border-cyan-950/60 bg-cyan-950/20 p-3 space-y-1 text-xs">
                      <div className="flex justify-between">
                        <span className="text-[10px] font-bold uppercase tracking-wider text-cyan-400">
                          AI Proposed Action: {item.proposed_action_type}
                        </span>
                        {item.ai_confidence_score !== null && (
                          <span className="text-cyan-300 font-bold text-[10px]">
                            {(item.ai_confidence_score * 100).toFixed(0)}%
                            Confidence
                          </span>
                        )}
                      </div>
                      {item.ai_reasoning_summary && (
                        <p className="text-slate-300 text-[11px] italic">
                          &quot;{item.ai_reasoning_summary}&quot;
                        </p>
                      )}
                    </div>
                  )}
                </div>

                {/* Actions Footer */}
                <div className="border-t border-slate-800 pt-3 flex items-center justify-between gap-2">
                  <button
                    onClick={() => setInspectCaseId(item.case_id)}
                    className="rounded-lg border border-slate-700 bg-slate-800 px-3 py-1.5 text-xs font-medium text-slate-300 hover:bg-slate-700"
                  >
                    Inspect Trail
                  </button>

                  <div className="flex gap-2 items-center">
                    {isViewerOnly ? (
                      <span className="text-[10px] text-amber-400 bg-amber-950/40 border border-amber-800/40 px-2 py-1 rounded">
                        Viewer (Read-Only)
                      </span>
                    ) : (
                      <>
                        <button
                          onClick={() =>
                            setActionItem({ item, action: "DISMISS" })
                          }
                          className="rounded-lg border border-rose-900/60 bg-rose-950/40 px-3 py-1.5 text-xs font-semibold text-rose-300 hover:bg-rose-900/60 transition-colors"
                        >
                          Dismiss
                        </button>
                        <button
                          onClick={() =>
                            setActionItem({ item, action: "APPROVE" })
                          }
                          className="rounded-lg bg-emerald-600 px-3.5 py-1.5 text-xs font-bold text-white hover:bg-emerald-500 shadow-md shadow-emerald-600/20 transition-all"
                        >
                          Authorize Action
                        </button>
                      </>
                    )}
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}

        {/* Action Confirmation Modal */}
        {actionItem && (
          <HumanReviewModal
            item={actionItem.item}
            action={actionItem.action}
            onClose={() => setActionItem(null)}
            onSuccess={handleActionSuccess}
          />
        )}

        {/* Case Detail Modal */}
        {inspectCaseId && (
          <CaseDetailModal
            caseId={inspectCaseId}
            onClose={() => setInspectCaseId(null)}
          />
        )}
      </main>
    </div>
  );
}
