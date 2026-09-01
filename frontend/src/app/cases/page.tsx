"use client";

import React, { useCallback, useEffect, useState } from "react";
import CaseDetailModal from "../../components/CaseDetailModal";
import Navbar from "../../components/Navbar";
import {
  fetchRecoveryCases,
  formatINR,
  PaginatedRecoveryCasesResponse,
  RecoveryCaseListItem,
} from "../../lib/api";

export default function RecoveryCasesPage() {
  const [data, setData] = useState<PaginatedRecoveryCasesResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Filters & Pagination State
  const [page, setPage] = useState(1);
  const [status, setStatus] = useState<string>("");
  const [recoveryStage, setRecoveryStage] = useState<string>("");
  const [search, setSearch] = useState<string>("");
  const [selectedCaseId, setSelectedCaseId] = useState<string | null>(null);

  const loadCases = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await fetchRecoveryCases({
        page,
        page_size: 15,
        status: status || undefined,
        recovery_stage: recoveryStage || undefined,
        search: search || undefined,
      });
      setData(res);
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Failed to load recovery cases"
      );
    } finally {
      setLoading(false);
    }
  }, [page, status, recoveryStage, search]);

  useEffect(() => {
    let ignore = false;
    async function execute() {
      try {
        const res = await fetchRecoveryCases({
          page,
          page_size: 15,
          status: status || undefined,
          recovery_stage: recoveryStage || undefined,
          search: search || undefined,
        });
        if (!ignore) {
          setData(res);
          setError(null);
          setLoading(false);
        }
      } catch (err) {
        if (!ignore) {
          setError(
            err instanceof Error ? err.message : "Failed to load recovery cases"
          );
          setLoading(false);
        }
      }
    }
    execute();
    return () => {
      ignore = true;
    };
  }, [page, status, recoveryStage, search]);

  const handleSearchSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setPage(1);
    loadCases();
  };

  const getStatusBadge = (st: string) => {
    switch (st) {
      case "RECOVERED":
        return "bg-emerald-950/60 text-emerald-400 border-emerald-800/40";
      case "OPEN":
      case "IN_RECOVERY":
        return "bg-indigo-950/60 text-indigo-400 border-indigo-800/40";
      case "ESCALATED_HUMAN":
        return "bg-amber-950/60 text-amber-400 border-amber-800/40";
      case "CLOSED":
        return "bg-slate-800 text-slate-400 border-slate-700";
      default:
        return "bg-slate-800 text-slate-300 border-slate-700";
    }
  };

  const getPolicyBadge = (pol: string | null) => {
    if (!pol) return "text-slate-400";
    switch (pol) {
      case "ALLOWED":
        return "text-emerald-400 bg-emerald-950/40 border-emerald-800/40";
      case "HUMAN_REVIEW":
        return "text-amber-400 bg-amber-950/40 border-amber-800/40";
      case "BLOCKED":
        return "text-rose-400 bg-rose-950/40 border-rose-800/40";
      default:
        return "text-slate-300";
    }
  };

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 antialiased">
      <Navbar />

      <main className="mx-auto max-w-7xl px-4 py-8 sm:px-6 lg:px-8 space-y-6">
        {/* Header */}
        <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <h1 className="text-2xl font-black tracking-tight text-white">
              Recovery Cases
            </h1>
            <p className="text-xs text-slate-400 mt-1">
              Autonomous lifecycle tracking, policy validation & action timeline
            </p>
          </div>
          <span className="text-xs text-slate-400 font-mono">
            {data ? `Showing ${data.items.length} of ${data.total} cases` : ""}
          </span>
        </div>

        {/* Filter Controls Bar */}
        <div className="rounded-2xl border border-slate-800 bg-slate-900/60 p-4 backdrop-blur-sm">
          <form
            onSubmit={handleSearchSubmit}
            className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-4"
          >
            {/* Search */}
            <div>
              <label className="block text-[11px] font-semibold uppercase tracking-wider text-slate-400 mb-1">
                Search
              </label>
              <div className="flex gap-2">
                <input
                  type="text"
                  placeholder="Customer ID or reason..."
                  value={search}
                  onChange={(e) => setSearch(e.target.value)}
                  className="w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-1.5 text-xs text-slate-200 focus:border-indigo-500 focus:outline-none"
                />
                <button
                  type="submit"
                  className="rounded-lg bg-indigo-600 px-3 py-1.5 text-xs font-semibold text-white hover:bg-indigo-500"
                >
                  Search
                </button>
              </div>
            </div>

            {/* Status Filter */}
            <div>
              <label className="block text-[11px] font-semibold uppercase tracking-wider text-slate-400 mb-1">
                Case Status
              </label>
              <select
                value={status}
                onChange={(e) => {
                  setStatus(e.target.value);
                  setPage(1);
                }}
                className="w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-1.5 text-xs text-slate-200 focus:border-indigo-500 focus:outline-none"
              >
                <option value="">All Statuses</option>
                <option value="OPEN">OPEN</option>
                <option value="IN_RECOVERY">IN_RECOVERY</option>
                <option value="ESCALATED_HUMAN">ESCALATED_HUMAN</option>
                <option value="RECOVERED">RECOVERED</option>
                <option value="CLOSED">CLOSED</option>
              </select>
            </div>

            {/* Stage Filter */}
            <div>
              <label className="block text-[11px] font-semibold uppercase tracking-wider text-slate-400 mb-1">
                Recovery Stage
              </label>
              <select
                value={recoveryStage}
                onChange={(e) => {
                  setRecoveryStage(e.target.value);
                  setPage(1);
                }}
                className="w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-1.5 text-xs text-slate-200 focus:border-indigo-500 focus:outline-none"
              >
                <option value="">All Stages</option>
                <option value="INITIAL_FAILURE">INITIAL_FAILURE</option>
                <option value="SMART_RETRY">SMART_RETRY</option>
                <option value="COMMUNICATION">COMMUNICATION</option>
                <option value="ESCALATION">ESCALATION</option>
              </select>
            </div>

            {/* Reset */}
            <div className="flex items-end">
              <button
                type="button"
                onClick={() => {
                  setStatus("");
                  setRecoveryStage("");
                  setSearch("");
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

        {/* Cases Table */}
        <div className="overflow-hidden rounded-2xl border border-slate-800 bg-slate-900/60 shadow-xl">
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="border-b border-slate-800 bg-slate-950/60 text-[11px] font-semibold uppercase tracking-wider text-slate-400">
                <tr>
                  <th className="px-4 py-3.5">Case ID / Customer</th>
                  <th className="px-4 py-3.5">Amount at Risk</th>
                  <th className="px-4 py-3.5">Failure Reason</th>
                  <th className="px-4 py-3.5">AI Proposed Action</th>
                  <th className="px-4 py-3.5">Policy Evaluation</th>
                  <th className="px-4 py-3.5">Status / Stage</th>
                  <th className="px-4 py-3.5 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/60">
                {loading ? (
                  <tr>
                    <td colSpan={7} className="py-12 text-center text-slate-400">
                      <div className="flex items-center justify-center space-x-2">
                        <div className="h-4 w-4 animate-spin rounded-full border-2 border-indigo-500 border-t-transparent" />
                        <span>Loading cases...</span>
                      </div>
                    </td>
                  </tr>
                ) : !data || data.items.length === 0 ? (
                  <tr>
                    <td colSpan={7} className="py-12 text-center text-slate-400">
                      No recovery cases found matching filters.
                    </td>
                  </tr>
                ) : (
                  data.items.map((item: RecoveryCaseListItem) => (
                    <tr
                      key={item.id}
                      className="hover:bg-slate-800/40 transition-colors group"
                    >
                      <td className="px-4 py-3.5">
                        <div className="font-mono text-slate-200 font-semibold">
                          {item.id.slice(0, 8)}...
                        </div>
                        <div className="text-[10px] text-slate-400 font-mono">
                          Cust: {item.customer_id.slice(0, 8)}
                        </div>
                      </td>

                      <td className="px-4 py-3.5">
                        <div className="font-bold text-white">
                          {formatINR(item.amount_at_risk)}
                        </div>
                        {item.recovered_amount > 0 && (
                          <div className="text-[10px] text-emerald-400">
                            Rec: {formatINR(item.recovered_amount)}
                          </div>
                        )}
                      </td>

                      <td className="px-4 py-3.5 text-slate-300">
                        <span className="font-medium text-slate-200">
                          {item.latest_failure_reason || "unknown"}
                        </span>
                        <div className="text-[10px] text-slate-400">
                          {item.total_attempts_count} / {item.max_allowed_attempts}{" "}
                          attempts
                        </div>
                      </td>

                      <td className="px-4 py-3.5">
                        {item.ai_proposed_action ? (
                          <div>
                            <span className="font-mono text-cyan-300 font-medium">
                              {item.ai_proposed_action}
                            </span>
                            {item.ai_confidence_score !== null && (
                              <span className="ml-1 text-[10px] text-slate-400">
                                ({(item.ai_confidence_score * 100).toFixed(0)}%)
                              </span>
                            )}
                          </div>
                        ) : (
                          <span className="text-slate-400">—</span>
                        )}
                      </td>

                      <td className="px-4 py-3.5">
                        {item.latest_policy_result ? (
                          <span
                            className={`rounded-full border px-2 py-0.5 text-[10px] font-bold ${getPolicyBadge(
                              item.latest_policy_result
                            )}`}
                          >
                            {item.latest_policy_result}
                          </span>
                        ) : (
                          <span className="text-slate-400">—</span>
                        )}
                      </td>

                      <td className="px-4 py-3.5">
                        <div className="flex flex-col gap-1 items-start">
                          <span
                            className={`rounded-full border px-2 py-0.5 text-[10px] font-bold ${getStatusBadge(
                              item.status
                            )}`}
                          >
                            {item.status}
                          </span>
                          <span className="text-[10px] text-slate-400">
                            {item.recovery_stage}
                          </span>
                        </div>
                      </td>

                      <td className="px-4 py-3.5 text-right">
                        <button
                          onClick={() => setSelectedCaseId(item.id)}
                          className="rounded-lg border border-slate-700 bg-slate-800 px-3 py-1 text-xs font-medium text-indigo-300 hover:bg-indigo-600 hover:text-white transition-all shadow-sm"
                        >
                          View Trail
                        </button>
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>

          {/* Pagination Controls */}
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

        {/* Case Detail Modal */}
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
