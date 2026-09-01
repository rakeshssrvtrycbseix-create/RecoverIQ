"use client";

import React, { useCallback, useEffect, useState } from "react";
import CaseDetailModal from "../../components/CaseDetailModal";
import Navbar from "../../components/Navbar";
import {
  AuditLogSummary,
  fetchAuditLogs,
  PaginatedAuditLogsResponse,
} from "../../lib/api";

export default function AuditTrailPage() {
  const [data, setData] = useState<PaginatedAuditLogsResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [page, setPage] = useState(1);
  const [eventType, setEventType] = useState("");
  const [caseId, setCaseId] = useState("");
  const [selectedCaseId, setSelectedCaseId] = useState<string | null>(null);
  const [expandedLogId, setExpandedLogId] = useState<number | null>(null);

  const loadLogs = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await fetchAuditLogs({
        page,
        page_size: 20,
        event_type: eventType || undefined,
        case_id: caseId || undefined,
      });
      setData(res);
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Failed to load audit logs"
      );
    } finally {
      setLoading(false);
    }
  }, [page, eventType, caseId]);

  useEffect(() => {
    let ignore = false;
    async function execute() {
      try {
        const res = await fetchAuditLogs({
          page,
          page_size: 20,
          event_type: eventType || undefined,
          case_id: caseId || undefined,
        });
        if (!ignore) {
          setData(res);
          setError(null);
          setLoading(false);
        }
      } catch (err) {
        if (!ignore) {
          setError(
            err instanceof Error ? err.message : "Failed to load audit logs"
          );
          setLoading(false);
        }
      }
    }
    execute();
    return () => {
      ignore = true;
    };
  }, [page, eventType, caseId]);

  const handleFilterSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setPage(1);
    loadLogs();
  };

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 antialiased">
      <Navbar />

      <main className="mx-auto max-w-7xl px-4 py-8 sm:px-6 lg:px-8 space-y-6">
        <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between border-b border-slate-800/80 pb-6">
          <div>
            <h1 className="text-2xl font-black tracking-tight text-white">
              Immutable Audit Trail
            </h1>
            <p className="text-xs text-slate-400 mt-1">
              Append-only compliance audit trail for decisions, state transitions & actions
            </p>
          </div>
          <span className="text-xs text-slate-400 font-mono">
            {data ? `Total Events: ${data.total}` : ""}
          </span>
        </div>

        {/* Filter Controls */}
        <div className="rounded-2xl border border-slate-800 bg-slate-900/60 p-4 backdrop-blur-sm">
          <form
            onSubmit={handleFilterSubmit}
            className="grid grid-cols-1 gap-3 sm:grid-cols-3"
          >
            <div>
              <label className="block text-[11px] font-semibold uppercase tracking-wider text-slate-400 mb-1">
                Event Type
              </label>
              <select
                value={eventType}
                onChange={(e) => {
                  setEventType(e.target.value);
                  setPage(1);
                }}
                className="w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-1.5 text-xs text-slate-200 focus:border-indigo-500 focus:outline-none"
              >
                <option value="">All Events</option>
                <option value="CASE_CREATED">CASE_CREATED</option>
                <option value="PAYMENT_ATTEMPT_RECORDED">PAYMENT_ATTEMPT_RECORDED</option>
                <option value="AGENT_DECISION_GENERATED">AGENT_DECISION_GENERATED</option>
                <option value="POLICY_EVALUATED">POLICY_EVALUATED</option>
                <option value="RECOVERY_ACTION_SCHEDULED">RECOVERY_ACTION_SCHEDULED</option>
                <option value="ACTION_EXECUTION_COMPLETED">ACTION_EXECUTION_COMPLETED</option>
                <option value="ACTION_EXECUTION_FAILED">ACTION_EXECUTION_FAILED</option>
                <option value="ACTION_EXECUTION_TIMED_OUT">ACTION_EXECUTION_TIMED_OUT</option>
                <option value="HUMAN_REVIEW_APPROVED">HUMAN_REVIEW_APPROVED</option>
                <option value="HUMAN_REVIEW_DISMISSED">HUMAN_REVIEW_DISMISSED</option>
              </select>
            </div>

            <div>
              <label className="block text-[11px] font-semibold uppercase tracking-wider text-slate-400 mb-1">
                Case ID
              </label>
              <div className="flex gap-2">
                <input
                  type="text"
                  placeholder="UUID..."
                  value={caseId}
                  onChange={(e) => setCaseId(e.target.value)}
                  className="w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-1.5 text-xs text-slate-200 focus:border-indigo-500 focus:outline-none"
                />
                <button
                  type="submit"
                  className="rounded-lg bg-indigo-600 px-3 py-1.5 text-xs font-semibold text-white hover:bg-indigo-500"
                >
                  Filter
                </button>
              </div>
            </div>

            <div className="flex items-end">
              <button
                type="button"
                onClick={() => {
                  setEventType("");
                  setCaseId("");
                  setPage(1);
                }}
                className="w-full rounded-lg border border-slate-700 bg-slate-800 px-3 py-1.5 text-xs font-semibold text-slate-300 hover:bg-slate-700"
              >
                Reset Filters
              </button>
            </div>
          </form>
        </div>

        {error && (
          <div className="rounded-xl bg-rose-950/40 border border-rose-800/40 p-4 text-xs text-rose-300">
            {error}
          </div>
        )}

        {/* Audit Log Table */}
        <div className="overflow-hidden rounded-2xl border border-slate-800 bg-slate-900/60 shadow-xl">
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="border-b border-slate-800 bg-slate-950/60 text-[11px] font-semibold uppercase tracking-wider text-slate-400">
                <tr>
                  <th className="px-4 py-3.5">Timestamp</th>
                  <th className="px-4 py-3.5">Event Type</th>
                  <th className="px-4 py-3.5">Actor</th>
                  <th className="px-4 py-3.5">Entity</th>
                  <th className="px-4 py-3.5">Details</th>
                  <th className="px-4 py-3.5 text-right">Action</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/60">
                {loading ? (
                  <tr>
                    <td colSpan={6} className="py-12 text-center text-slate-400">
                      <div className="flex items-center justify-center space-x-2">
                        <div className="h-4 w-4 animate-spin rounded-full border-2 border-indigo-500 border-t-transparent" />
                        <span>Loading audit logs...</span>
                      </div>
                    </td>
                  </tr>
                ) : !data || data.items.length === 0 ? (
                  <tr>
                    <td colSpan={6} className="py-12 text-center text-slate-400">
                      No audit logs found matching criteria.
                    </td>
                  </tr>
                ) : (
                  data.items.map((log: AuditLogSummary) => {
                    const isExpanded = expandedLogId === log.id;
                    return (
                      <React.Fragment key={log.id}>
                        <tr className="hover:bg-slate-800/40 transition-colors">
                          <td className="px-4 py-3.5 text-slate-400 whitespace-nowrap text-[11px]">
                            {new Date(log.created_at).toLocaleString()}
                          </td>

                          <td className="px-4 py-3.5 font-mono font-semibold text-indigo-300">
                            {log.event_type}
                          </td>

                          <td className="px-4 py-3.5">
                            <span className="text-slate-200 font-medium">
                              {log.actor_id}
                            </span>
                            <span className="ml-1 text-[10px] text-slate-400">
                              ({log.actor_type})
                            </span>
                          </td>

                          <td className="px-4 py-3.5">
                            <span className="text-slate-300 font-mono text-[11px]">
                              {log.entity_type}
                            </span>
                            {log.entity_id && (
                              <div className="text-[10px] text-slate-400 font-mono">
                                {log.entity_id.slice(0, 8)}...
                              </div>
                            )}
                          </td>

                          <td className="px-4 py-3.5">
                            <button
                              onClick={() =>
                                setExpandedLogId(isExpanded ? null : log.id)
                              }
                              className="text-[11px] text-cyan-400 hover:underline font-mono"
                            >
                              {isExpanded ? "Hide Payload" : "View Payload"}
                            </button>
                          </td>

                          <td className="px-4 py-3.5 text-right">
                            {log.entity_id &&
                              log.entity_type === "recovery_cases" && (
                                <button
                                  onClick={() => setSelectedCaseId(log.entity_id)}
                                  className="rounded border border-slate-700 bg-slate-800 px-2 py-1 text-[11px] text-slate-300 hover:bg-slate-700"
                                >
                                  Inspect Case
                                </button>
                              )}
                          </td>
                        </tr>

                        {isExpanded && (
                          <tr className="bg-slate-950/80">
                            <td colSpan={6} className="p-4">
                              <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-[11px] font-mono">
                                {log.previous_state && (
                                  <div className="rounded bg-slate-900 p-3 border border-slate-800">
                                    <span className="text-slate-400 font-bold block mb-1">
                                      Previous State:
                                    </span>
                                    <pre className="text-slate-300 whitespace-pre-wrap">
                                      {JSON.stringify(log.previous_state, null, 2)}
                                    </pre>
                                  </div>
                                )}
                                {log.new_state && (
                                  <div className="rounded bg-slate-900 p-3 border border-slate-800">
                                    <span className="text-emerald-400 font-bold block mb-1">
                                      New State:
                                    </span>
                                    <pre className="text-slate-300 whitespace-pre-wrap">
                                      {JSON.stringify(log.new_state, null, 2)}
                                    </pre>
                                  </div>
                                )}
                                {log.metadata_json &&
                                  Object.keys(log.metadata_json).length > 0 && (
                                    <div className="col-span-2 rounded bg-slate-900 p-3 border border-slate-800">
                                      <span className="text-indigo-400 font-bold block mb-1">
                                        Metadata:
                                      </span>
                                      <pre className="text-slate-300 whitespace-pre-wrap">
                                        {JSON.stringify(log.metadata_json, null, 2)}
                                      </pre>
                                    </div>
                                  )}
                              </div>
                            </td>
                          </tr>
                        )}
                      </React.Fragment>
                    );
                  })
                )}
              </tbody>
            </table>
          </div>

          {/* Pagination */}
          {data && data.total_pages > 1 && (
            <div className="flex items-center justify-between border-t border-slate-800 px-4 py-3 bg-slate-950/40 text-xs">
              <span className="text-slate-400">
                Page <strong className="text-white">{data.page}</strong> of{" "}
                <strong className="text-white">{data.total_pages}</strong>
              </span>

              <div className="flex gap-2">
                <button
                  disabled={data.page <= 1}
                  onClick={() => setPage((p) => Math.max(1, p - 1))}
                  className="rounded border border-slate-700 bg-slate-800 px-3 py-1 font-medium text-slate-300 disabled:opacity-40"
                >
                  Previous
                </button>
                <button
                  disabled={data.page >= data.total_pages}
                  onClick={() => setPage((p) => p + 1)}
                  className="rounded border border-slate-700 bg-slate-800 px-3 py-1 font-medium text-slate-300 disabled:opacity-40"
                >
                  Next
                </button>
              </div>
            </div>
          )}
        </div>

        {selectedCaseId && (
          <CaseDetailModal
            caseId={selectedCaseId}
            onClose={() => setSelectedCaseId(null)}
          />
        )}
      </main>
    </div>
  );
}
