import React from "react";

interface MetricCardProps {
  title: string;
  value: string | number;
  subtitle?: string;
  badge?: {
    text: string;
    variant: "success" | "warning" | "info" | "danger";
  };
  icon?: React.ReactNode;
}

export default function MetricCard({
  title,
  value,
  subtitle,
  badge,
  icon,
}: MetricCardProps) {
  const badgeStyles = {
    success: "bg-emerald-950/60 text-emerald-400 border-emerald-800/40",
    warning: "bg-amber-950/60 text-amber-400 border-amber-800/40",
    info: "bg-indigo-950/60 text-indigo-400 border-indigo-800/40",
    danger: "bg-rose-950/60 text-rose-400 border-rose-800/40",
  };

  return (
    <div className="relative overflow-hidden rounded-2xl border border-slate-800 bg-slate-900/60 p-6 backdrop-blur-sm transition-all hover:border-slate-700 hover:shadow-lg hover:shadow-indigo-500/5 group">
      <div className="flex items-center justify-between">
        <span className="text-xs font-semibold uppercase tracking-wider text-slate-400">
          {title}
        </span>
        {icon && (
          <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-slate-800/80 text-indigo-400 group-hover:text-indigo-300 transition-colors">
            {icon}
          </div>
        )}
      </div>

      <div className="mt-4 flex items-baseline justify-between gap-2">
        <span className="text-2xl font-bold tracking-tight text-white">
          {value}
        </span>
        {badge && (
          <span
            className={`inline-flex items-center rounded-full border px-2 py-0.5 text-xs font-medium ${badgeStyles[badge.variant]}`}
          >
            {badge.text}
          </span>
        )}
      </div>

      {subtitle && (
        <p className="mt-1 text-xs text-slate-400">{subtitle}</p>
      )}
    </div>
  );
}
