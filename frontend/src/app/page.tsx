"use client";

import React, { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import CaseDetailModal from "./../components/CaseDetailModal";
import ChartsSection from "./../components/Charts";
import MetricCard from "./../components/MetricCard";
import Navbar from "./../components/Navbar";
import {
  fetchRecoveryMetrics,
  formatINR,
  RecoveryMetricsResponse,
} from "./../lib/api";

export default function DashboardOverviewPage() {
  const [metrics, setMetrics] = useState<RecoveryMetricsResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedCaseId, setSelectedCaseId] = useState<string | null>(null);

  const loadData = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await fetchRecoveryMetrics();
      setMetrics(data);
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : "Failed to connect to RecoverIQ API"
      );
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    let ignore = false;
    async function execute() {
      try {
        const data = await fetchRecoveryMetrics();
        if (!ignore) {
          setMetrics(data);
          setError(null);
          setLoading(false);
        }
      } catch (err) {
        if (!ignore) {
          setError(
            err instanceof Error
              ? err.message
              : "Failed to connect to RecoverIQ API"
          );
          setLoading(false);
        }
      }
    }
    execute();
    const interval = setInterval(execute, 15000); // 15s auto-refresh
    return () => {
      ignore = true;
      clearInterval(interval);
    };
  }, []);

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 antialiased">
      <Navbar />

      <main className="mx-auto max-w-7xl px-4 py-8 sm:px-6 lg:px-8 space-y-8">
        {/* Header Banner */}
        <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between border-b border-slate-800/80 pb-6">
          <div>
            <h1 className="text-2xl font-black tracking-tight text-white sm:text-3xl">
              Recovery Executive Overview
            </h1>
            <p className="mt-1 text-sm text-slate-400">
              Autonomous AI agent & deterministic policy revenue recovery pipeline
            </p>
          </div>

          <div className="flex items-center gap-3">
            <button
              onClick={loadData}
              disabled={loading}
              className="flex items-center gap-2 rounded-xl border border-slate-800 bg-slate-900 px-4 py-2 text-xs font-semibold text-slate-200 hover:bg-slate-800 hover:text-white transition-all shadow-sm"
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
              <span>{loading ? "Refreshing..." : "Refresh"}</span>
            </button>

            <Link
              href="/review"
              className="rounded-xl bg-gradient-to-r from-indigo-600 to-indigo-500 px-4 py-2 text-xs font-bold text-white shadow-lg shadow-indigo-500/20 hover:from-indigo-500 hover:to-indigo-400 transition-all"
            >
              Review Queue
              {metrics && metrics.policy.human_review > 0 && (
                <span className="ml-2 rounded-full bg-amber-400 px-1.5 py-0.5 text-[10px] font-black text-slate-950">
                  {metrics.policy.human_review}
                </span>
              )}
            </Link>
          </div>
        </div>

        {error && (
          <div className="rounded-2xl border border-rose-800/40 bg-rose-950/40 p-4 text-sm text-rose-300">
            <div className="flex items-center justify-between">
              <span>{error}</span>
              <button
                onClick={loadData}
                className="underline hover:text-white text-xs font-semibold"
              >
                Retry
              </button>
            </div>
          </div>
        )}

        {loading && !metrics ? (
          <div className="flex h-96 items-center justify-center">
            <div className="flex flex-col items-center gap-3">
              <div className="h-8 w-8 animate-spin rounded-full border-3 border-indigo-500 border-t-transparent" />
              <span className="text-sm font-medium text-slate-400">
                Connecting to Autonomous Recovery Engine...
              </span>
            </div>
          </div>
        ) : metrics ? (
          <>
            {/* Top KPI Metrics Cards */}
            <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
              <MetricCard
                title="Recovered Revenue"
                value={formatINR(metrics.financial.amount_recovered)}
                subtitle={`Recovery Rate: ${metrics.financial.recovery_rate_pct.toFixed(
                  1
                )}%`}
                badge={{
                  text: `${metrics.financial.recovery_rate_pct.toFixed(1)}%`,
                  variant: "success",
                }}
                icon={
                  <svg
                    className="h-4 w-4"
                    fill="none"
                    stroke="currentColor"
                    viewBox="0 0 24 24"
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth="2"
                      d="M12 8c-1.657 0-3 .895-3 2s1.343 2 3 2 3 .895 3 2-1.343 2-3 2m0-8c1.11 0 2.08.402 2.599 1M12 8V7m0 1v8m0 0v1m0-1c-1.11 0-2.08-.402-2.599-1M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
                    />
                  </svg>
                }
              />

              <MetricCard
                title="Amount at Risk"
                value={formatINR(metrics.financial.amount_at_risk)}
                subtitle={`${metrics.cases.active} currently active cases`}
                badge={{
                  text: `${metrics.cases.active} Active`,
                  variant: "info",
                }}
                icon={
                  <svg
                    className="h-4 w-4"
                    fill="none"
                    stroke="currentColor"
                    viewBox="0 0 24 24"
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth="2"
                      d="M13 10V3L4 14h7v7l9-11h-7z"
                    />
                  </svg>
                }
              />

              <MetricCard
                title="Policy Clearance"
                value={`${metrics.policy.clearance_rate_pct.toFixed(1)}%`}
                subtitle={`${metrics.policy.allowed} allowed / ${metrics.policy.total} total`}
                badge={{
                  text:
                    metrics.policy.human_review > 0
                      ? `${metrics.policy.human_review} Review`
                      : "Clear",
                  variant:
                    metrics.policy.human_review > 0 ? "warning" : "success",
                }}
                icon={
                  <svg
                    className="h-4 w-4"
                    fill="none"
                    stroke="currentColor"
                    viewBox="0 0 24 24"
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth="2"
                      d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z"
                    />
                  </svg>
                }
              />

              <MetricCard
                title="Worker Engine"
                value={metrics.worker.status.toUpperCase()}
                subtitle={`Queue: ${metrics.worker.queue_depth} | Claimed: ${metrics.worker.actions_claimed}`}
                badge={{
                  text:
                    metrics.worker.status === "running" ? "Online" : "Idle",
                  variant:
                    metrics.worker.status === "running" ? "success" : "info",
                }}
                icon={
                  <svg
                    className="h-4 w-4"
                    fill="none"
                    stroke="currentColor"
                    viewBox="0 0 24 24"
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth="2"
                      d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10"
                    />
                  </svg>
                }
              />
            </div>

            {/* Visual Analytics Grid */}
            <ChartsSection metrics={metrics} />

            {/* Background Worker Telemetry Card */}
            <div className="rounded-2xl border border-slate-800 bg-slate-900/40 p-6">
              <div className="flex items-center justify-between border-b border-slate-800 pb-4">
                <div className="flex items-center gap-3">
                  <div className="flex h-3 w-3 items-center justify-center">
                    <span className="relative flex h-2.5 w-2.5">
                      <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-indigo-400 opacity-75" />
                      <span className="relative inline-flex rounded-full h-2.5 w-2.5 bg-indigo-500" />
                    </span>
                  </div>
                  <div>
                    <h3 className="text-sm font-bold text-white">
                      Phase 8B Background Worker & Polling Telemetry
                    </h3>
                    <p className="text-xs text-slate-400">
                      Atomic claiming, timeout resolution & non-overlapping reconciliation
                    </p>
                  </div>
                </div>
                <span className="text-xs font-mono text-slate-400">
                  Runs: {metrics.worker.reconciliation_runs} sweeps
                </span>
              </div>

              <div className="mt-4 grid grid-cols-2 gap-4 sm:grid-cols-4 text-xs">
                <div className="rounded-xl bg-slate-950/60 p-3 border border-slate-800/80">
                  <span className="text-slate-400 block">Queue Depth</span>
                  <span className="text-lg font-bold text-indigo-400">
                    {metrics.worker.queue_depth} actions
                  </span>
                </div>
                <div className="rounded-xl bg-slate-950/60 p-3 border border-slate-800/80">
                  <span className="text-slate-400 block">Actions Claimed</span>
                  <span className="text-lg font-bold text-cyan-400">
                    {metrics.worker.actions_claimed}
                  </span>
                </div>
                <div className="rounded-xl bg-slate-950/60 p-3 border border-slate-800/80">
                  <span className="text-slate-400 block">
                    Actions Completed
                  </span>
                  <span className="text-lg font-bold text-emerald-400">
                    {metrics.worker.actions_completed}
                  </span>
                </div>
                <div className="rounded-xl bg-slate-950/60 p-3 border border-slate-800/80">
                  <span className="text-slate-400 block">Actions Failed</span>
                  <span className="text-lg font-bold text-rose-400">
                    {metrics.worker.actions_failed}
                  </span>
                </div>
              </div>
            </div>

            {/* Recent Audit Activity Stream */}
            <div className="rounded-2xl border border-slate-800 bg-slate-900/60 p-6">
              <div className="flex items-center justify-between border-b border-slate-800 pb-4">
                <div>
                  <h3 className="text-sm font-bold text-white">
                    Live System Audit Trail
                  </h3>
                  <p className="text-xs text-slate-400">
                    Immutable event log of decisions, executions, and policy evaluations
                  </p>
                </div>
                <Link
                  href="/audit"
                  className="text-xs font-semibold text-indigo-400 hover:text-indigo-300"
                >
                  View Full Audit Log &rarr;
                </Link>
              </div>

              <div className="mt-4 space-y-2">
                {metrics.recent_activity.length === 0 ? (
                  <div className="py-8 text-center text-xs text-slate-400">
                    No recent audit activity
                  </div>
                ) : (
                  metrics.recent_activity.map((item) => (
                    <div
                      key={item.id}
                      className="flex flex-wrap items-center justify-between gap-2 rounded-xl border border-slate-800/80 bg-slate-950/40 p-3 text-xs"
                    >
                      <div className="flex items-center gap-3">
                        <span className="font-mono font-semibold text-indigo-300">
                          {item.event_type}
                        </span>
                        <span className="text-[11px] text-slate-400">
                          by <strong className="text-slate-300">{item.actor_id}</strong> ({item.actor_type})
                        </span>
                      </div>

                      <div className="flex items-center gap-3">
                        {item.case_id && (
                          <button
                            onClick={() => setSelectedCaseId(item.case_id)}
                            className="font-mono text-[11px] text-cyan-400 hover:underline"
                          >
                            Case: {item.case_id.slice(0, 8)}...
                          </button>
                        )}
                        <span className="text-[10px] text-slate-400">
                          {new Date(item.created_at).toLocaleTimeString()}
                        </span>
                      </div>
                    </div>
                  ))
                )}
              </div>
            </div>
          </>
        ) : null}

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
