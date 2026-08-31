import React from "react";
import { BreakdownItem, formatINR, RecoveryMetricsResponse } from "../lib/api";

interface ChartsSectionProps {
  metrics: RecoveryMetricsResponse;
}

export default function ChartsSection({ metrics }: ChartsSectionProps) {
  const { financial, actions, policy, failure_reasons, action_types } = metrics;

  return (
    <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
      {/* Financial Recovery Ratio Card */}
      <div className="rounded-2xl border border-slate-800 bg-slate-900/60 p-6 backdrop-blur-sm">
        <div className="flex items-center justify-between">
          <div>
            <h3 className="text-sm font-semibold uppercase tracking-wider text-slate-400">
              Financial Recovery Performance
            </h3>
            <p className="text-xs text-slate-400 mt-0.5">
              Net captured revenue vs total pipeline risk
            </p>
          </div>
          <span className="text-xl font-bold text-emerald-400">
            {financial.recovery_rate_pct.toFixed(1)}%
          </span>
        </div>

        <div className="mt-6 space-y-2">
          <div className="flex justify-between text-xs">
            <span className="text-slate-400">
              Recovered:{" "}
              <strong className="text-emerald-400">
                {formatINR(financial.amount_recovered)}
              </strong>
            </span>
            <span className="text-slate-400">
              At Risk:{" "}
              <strong className="text-slate-200">
                {formatINR(financial.amount_at_risk)}
              </strong>
            </span>
          </div>

          <div className="h-3 w-full overflow-hidden rounded-full bg-slate-800">
            <div
              className="h-full rounded-full bg-gradient-to-r from-indigo-500 via-cyan-400 to-emerald-400 transition-all duration-500"
              style={{
                width: `${Math.min(100, Math.max(0, financial.recovery_rate_pct))}%`,
              }}
            />
          </div>
        </div>

        <div className="mt-6 grid grid-cols-3 gap-2 border-t border-slate-800 pt-4 text-center">
          <div className="p-2">
            <span className="block text-xs text-slate-400">Total Cases</span>
            <span className="text-base font-bold text-white">
              {metrics.cases.total}
            </span>
          </div>
          <div className="p-2">
            <span className="block text-xs text-slate-400">Active</span>
            <span className="text-base font-bold text-indigo-400">
              {metrics.cases.active}
            </span>
          </div>
          <div className="p-2">
            <span className="block text-xs text-slate-400">Recovered</span>
            <span className="text-base font-bold text-emerald-400">
              {metrics.cases.recovered}
            </span>
          </div>
        </div>
      </div>

      {/* Policy Engine Evaluation Outcomes */}
      <div className="rounded-2xl border border-slate-800 bg-slate-900/60 p-6 backdrop-blur-sm">
        <div className="flex items-center justify-between">
          <div>
            <h3 className="text-sm font-semibold uppercase tracking-wider text-slate-400">
              Deterministic Policy Engine
            </h3>
            <p className="text-xs text-slate-400 mt-0.5">
              Safety rule evaluation distribution
            </p>
          </div>
          <span className="text-xs font-semibold text-indigo-400 border border-indigo-800/40 bg-indigo-950/60 px-2 py-0.5 rounded-full">
            {policy.clearance_rate_pct.toFixed(1)}% Allowed
          </span>
        </div>

        <div className="mt-6 grid grid-cols-3 gap-3">
          <div className="rounded-xl border border-emerald-900/40 bg-emerald-950/20 p-4 text-center">
            <span className="text-xs font-medium text-emerald-400">Allowed</span>
            <span className="mt-1 block text-2xl font-bold text-emerald-300">
              {policy.allowed}
            </span>
            <span className="text-[10px] text-emerald-400/70">
              Auto-scheduled
            </span>
          </div>

          <div className="rounded-xl border border-amber-900/40 bg-amber-950/20 p-4 text-center">
            <span className="text-xs font-medium text-amber-400">Human Review</span>
            <span className="mt-1 block text-2xl font-bold text-amber-300">
              {policy.human_review}
            </span>
            <span className="text-[10px] text-amber-400/70">
              Pending triage
            </span>
          </div>

          <div className="rounded-xl border border-rose-900/40 bg-rose-950/20 p-4 text-center">
            <span className="text-xs font-medium text-rose-400">Blocked</span>
            <span className="mt-1 block text-2xl font-bold text-rose-300">
              {policy.blocked}
            </span>
            <span className="text-[10px] text-rose-400/70">
              Safety limit hit
            </span>
          </div>
        </div>

        <div className="mt-4 flex h-2 w-full overflow-hidden rounded-full bg-slate-800">
          {policy.total > 0 && (
            <>
              <div
                className="bg-emerald-500"
                style={{ width: `${(policy.allowed / policy.total) * 100}%` }}
              />
              <div
                className="bg-amber-500"
                style={{ width: `${(policy.human_review / policy.total) * 100}%` }}
              />
              <div
                className="bg-rose-500"
                style={{ width: `${(policy.blocked / policy.total) * 100}%` }}
              />
            </>
          )}
        </div>
      </div>

      {/* Action Execution Distribution */}
      <div className="rounded-2xl border border-slate-800 bg-slate-900/60 p-6 backdrop-blur-sm">
        <h3 className="text-sm font-semibold uppercase tracking-wider text-slate-400">
          Recovery Actions Pipeline
        </h3>
        <p className="text-xs text-slate-400 mt-0.5 mb-4">
          Lifecycle state distribution across action scheduler & dispatcher
        </p>

        <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
          <div className="rounded-xl bg-slate-800/40 border border-slate-700/50 p-3 text-center">
            <span className="text-[11px] font-medium text-slate-400">
              Scheduled
            </span>
            <span className="mt-1 block text-xl font-bold text-indigo-400">
              {actions.scheduled}
            </span>
          </div>
          <div className="rounded-xl bg-slate-800/40 border border-slate-700/50 p-3 text-center">
            <span className="text-[11px] font-medium text-slate-400">
              Executing
            </span>
            <span className="mt-1 block text-xl font-bold text-cyan-400">
              {actions.executing}
            </span>
          </div>
          <div className="rounded-xl bg-slate-800/40 border border-slate-700/50 p-3 text-center">
            <span className="text-[11px] font-medium text-slate-400">
              Completed
            </span>
            <span className="mt-1 block text-xl font-bold text-emerald-400">
              {actions.completed}
            </span>
          </div>
          <div className="rounded-xl bg-slate-800/40 border border-slate-700/50 p-3 text-center">
            <span className="text-[11px] font-medium text-slate-400">
              Failed
            </span>
            <span className="mt-1 block text-xl font-bold text-rose-400">
              {actions.failed}
            </span>
          </div>
        </div>

        {action_types.length > 0 && (
          <div className="mt-5 space-y-2 border-t border-slate-800 pt-4">
            <span className="text-xs font-semibold text-slate-400">
              Action Channels
            </span>
            <div className="space-y-1.5">
              {action_types.map((at) => (
                <div
                  key={at.category}
                  className="flex items-center justify-between text-xs"
                >
                  <span className="text-slate-300 font-mono text-[11px]">
                    {at.category}
                  </span>
                  <span className="text-slate-400 font-medium">
                    {at.count} ({at.percentage}%)
                  </span>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>

      {/* Top Failure Reasons */}
      <div className="rounded-2xl border border-slate-800 bg-slate-900/60 p-6 backdrop-blur-sm">
        <h3 className="text-sm font-semibold uppercase tracking-wider text-slate-400">
          Payment Failure Taxonomy
        </h3>
        <p className="text-xs text-slate-400 mt-0.5 mb-4">
          Failure reasons diagnosed from webhook events
        </p>

        {failure_reasons.length === 0 ? (
          <div className="flex h-32 items-center justify-center text-xs text-slate-400">
            No failure reasons recorded yet
          </div>
        ) : (
          <div className="space-y-3">
            {failure_reasons.slice(0, 5).map((fr: BreakdownItem) => (
              <div key={fr.category} className="space-y-1">
                <div className="flex justify-between text-xs">
                  <span className="text-slate-300 font-medium">
                    {fr.category}
                  </span>
                  <span className="text-slate-400">
                    {fr.count} ({fr.percentage}%)
                  </span>
                </div>
                <div className="h-2 w-full overflow-hidden rounded-full bg-slate-800">
                  <div
                    className="h-full rounded-full bg-indigo-500"
                    style={{ width: `${fr.percentage}%` }}
                  />
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
