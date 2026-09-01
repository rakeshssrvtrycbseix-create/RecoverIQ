"use client";

import React, { useState } from "react";
import {
  approveHumanReview,
  dismissHumanReview,
  formatINR,
  HumanReviewQueueItem,
} from "../lib/api";
import { getStoredSession, UserSession } from "../lib/auth";

interface HumanReviewModalProps {
  item: HumanReviewQueueItem;
  action: "APPROVE" | "DISMISS";
  onClose: () => void;
  onSuccess: (message: string) => void;
}

export default function HumanReviewModal({
  item,
  action,
  onClose,
  onSuccess,
}: HumanReviewModalProps) {
  const [session] = useState<UserSession>(getStoredSession);
  const [notes, setNotes] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSubmitting(true);
    setError(null);

    try {
      if (action === "APPROVE") {
        const res = await approveHumanReview(item.case_id, notes);
        onSuccess(
          res.message || "Case successfully approved and recovery action scheduled."
        );
      } else {
        const res = await dismissHumanReview(item.case_id, notes);
        onSuccess(res.message || "Case successfully dismissed with audit log.");
      }
      onClose();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Action failed");
    } finally {
      setSubmitting(false);
    }
  };

  const isApprove = action === "APPROVE";

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/80 p-4 backdrop-blur-sm">
      <div className="relative w-full max-w-lg rounded-2xl border border-slate-800 bg-slate-900 shadow-2xl p-6 text-slate-200">
        <div className="flex items-center justify-between border-b border-slate-800 pb-3">
          <h3
            className={`text-base font-bold ${
              isApprove ? "text-emerald-400" : "text-rose-400"
            }`}
          >
            {isApprove ? "Confirm Action Approval" : "Confirm Case Dismissal"}
          </h3>
          <button
            onClick={onClose}
            className="rounded-lg p-1 text-slate-400 hover:bg-slate-800 hover:text-white"
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
        </div>

        <form onSubmit={handleSubmit} className="mt-4 space-y-4">
          <div className="rounded-xl border border-slate-800 bg-slate-950/50 p-3 space-y-2 text-xs">
            <div className="flex justify-between">
              <span className="text-slate-400">Case ID:</span>
              <span className="font-mono text-slate-200">{item.case_id}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-slate-400">Amount at Risk:</span>
              <span className="font-bold text-white">
                {formatINR(item.amount_at_risk)}
              </span>
            </div>
            <div className="flex justify-between">
              <span className="text-slate-400">AI Proposed Action:</span>
              <span className="font-semibold text-cyan-300">
                {item.proposed_action_type || "RETRY_PAYMENT"}
              </span>
            </div>
            <div className="flex justify-between">
              <span className="text-slate-400">Flagged Rule:</span>
              <span className="text-amber-400 font-medium">
                {item.rule_name || item.triggered_rule_code || "High Value Review"}
              </span>
            </div>
          </div>

          {/* Authenticated Context Display */}
          <div className="rounded-lg bg-slate-950 border border-slate-800 p-3 text-xs flex items-center justify-between">
            <span className="text-slate-400">Authenticated Actor:</span>
            <span className="font-mono font-semibold text-indigo-300">
              {session?.user_id || "operator_lead"}{" "}
              <span className="text-[10px] text-slate-400">
                ({session?.role || "operator"})
              </span>
            </span>
          </div>

          <div>
            <label className="block text-xs font-semibold uppercase tracking-wider text-slate-400 mb-1">
              Justification Notes (Required for Audit Log)
            </label>
            <textarea
              rows={3}
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              placeholder="Provide reason for approval or dismissal..."
              className="w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-xs text-slate-200 focus:border-indigo-500 focus:outline-none"
            />
          </div>

          {error && (
            <div className="rounded-lg bg-rose-950/50 border border-rose-800/40 p-3 text-xs text-rose-300">
              {error}
            </div>
          )}

          <div className="flex justify-end gap-3 pt-2">
            <button
              type="button"
              onClick={onClose}
              disabled={submitting}
              className="rounded-lg border border-slate-700 bg-slate-800 px-4 py-2 text-xs font-semibold text-slate-300 hover:bg-slate-700"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={submitting}
              className={`rounded-lg px-4 py-2 text-xs font-bold text-white shadow-lg transition-all ${
                isApprove
                  ? "bg-emerald-600 hover:bg-emerald-500 shadow-emerald-600/20"
                  : "bg-rose-600 hover:bg-rose-500 shadow-rose-600/20"
              } ${submitting ? "opacity-50 cursor-not-allowed" : ""}`}
            >
              {submitting
                ? "Submitting..."
                : isApprove
                ? "Authorize Action"
                : "Dismiss Case"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
