import { Fund } from "../types/fund";
import { NavSparkline } from "./nav-sparkline";
import { riskColor, fmtTer, riskHelp } from "./risk";

interface FundCardProps {
  fund: Fund;
  selected: boolean;
  onToggle: () => void;
}

function steadinessLabel(sortino: number) {
  if (sortino >= 0.9) return { label: "Very steady", color: "text-emerald-600 dark:text-emerald-400" };
  if (sortino >= 0.6) return { label: "Steady", color: "text-indigo-600 dark:text-indigo-400" };
  return { label: "Bumpy", color: "text-amber-600 dark:text-amber-400" };
}
function stars(ocs: number) {
  const n = Math.max(1, Math.round(ocs / 20));
  return "★".repeat(n) + "☆".repeat(5 - n);
}

export function FundCard({ fund, selected, onToggle }: FundCardProps) {
  const steady = steadinessLabel(fund.analytics.sortino_ratio);
  const ter = fund.expense_ratio;
  const expCost = ter == null ? "Cost n/a" : ter <= 0.6 ? "Low cost" : ter <= 0.9 ? "Medium cost" : "High cost";
  const horizon = fund.analytics.time_horizon ?? 5;
  const conf = fund.confidence;
  const MISSING: Record<string, string> = { category_verified: "category", nav_validated: "NAV validation", history_covers_horizon: "full history", data_fresh: "fresh data", expense_ratio_known: "expense ratio" };
  const confTitle = conf ? (conf.missing.length ? `Missing: ${conf.missing.map((m) => MISSING[m] ?? m).join(", ")}. ` : "All data checks passed. ") + `Not available for any fund: ${conf.not_available.join(", ")}.` : "";

  const getScoreColor = (score: number) => {
    if (score >= 75) return "text-emerald-600 dark:text-emerald-400";
    if (score >= 50) return "text-indigo-600 dark:text-indigo-400";
    if (score >= 25) return "text-amber-600 dark:text-amber-400";
    return "text-red-600 dark:text-red-400";
  };
  const getScoreBadge = (score: number) => {
    if (score >= 75) return "bg-emerald-50 text-emerald-700 border-emerald-200 dark:bg-emerald-950/40 dark:text-emerald-400 dark:border-emerald-900";
    if (score >= 50) return "bg-indigo-50 text-indigo-700 border-indigo-200 dark:bg-indigo-950/40 dark:text-indigo-400 dark:border-indigo-900";
    if (score >= 25) return "bg-amber-50 text-amber-700 border-amber-200 dark:bg-amber-950/40 dark:text-amber-400 dark:border-amber-900";
    return "bg-red-50 text-red-700 border-red-200 dark:bg-red-950/40 dark:text-red-400 dark:border-red-900";
  };

  return (
    <div
      className={`group rounded-xl border p-5 transition-colors duration-150 cursor-pointer ${
        selected
          ? "border-indigo-500 bg-indigo-50/60 dark:bg-indigo-950/20 ring-1 ring-indigo-500"
          : "border-slate-200 bg-white hover:border-indigo-300 dark:border-slate-800 dark:bg-slate-900 dark:hover:border-indigo-700"
      }`}
      onClick={onToggle}
    >
      <div className="flex items-start justify-between mb-3">
        <div className="flex-1 min-w-0">
          <h3 className="font-semibold text-slate-900 dark:text-white truncate text-base">
            {fund.scheme_name}
          </h3>
          <p className="text-sm text-slate-500 dark:text-slate-400 mt-0.5">
            {fund.amc_name} · {fund.category} · {expCost}{ter != null && ` (${fmtTer(ter)})`}
          </p>
        </div>
        <div className="flex flex-col items-end gap-1 ml-3">
          <span className={`text-3xl font-bold tnum ${getScoreColor(fund.ocs_score)}`}>
            {fund.ocs_score.toFixed(0)}
          </span>
          <span className={`text-xs font-semibold px-2 py-0.5 rounded-md border ${getScoreBadge(fund.ocs_score)}`}>
            Overall Score
          </span>
          {conf && <span className={`text-[10px] font-semibold px-2 py-0.5 rounded-md border ${conf.level === "Complete" ? "bg-emerald-50 text-emerald-700 border-emerald-200 dark:bg-emerald-950/40 dark:text-emerald-400 dark:border-emerald-900" : "bg-amber-50 text-amber-700 border-amber-200 dark:bg-amber-950/40 dark:text-amber-400 dark:border-amber-900"}`} title={confTitle}>{conf.level === "Complete" ? "Data complete" : "Partial data"}</span>}
          <span className="text-xs text-amber-500" title="Higher is better — combines returns, risk, consistency, cost and trend (0-100)">{stars(fund.ocs_score)}</span>
        </div>
      </div>

      <div className="grid grid-cols-3 gap-3 mt-4 pt-4 border-t border-slate-100 dark:border-slate-800">
        <div className="text-center" title="Compounded yearly return over the past period, from official NAVs. It is history, not a forecast, and equity returns swing with the market cycle.">
          <p className="text-xs text-slate-400 mb-1">Past {horizon}Y return / yr</p>
          <p className="text-sm font-bold text-emerald-600 dark:text-emerald-400 tnum">{fund.analytics.cagr.toFixed(1)}%</p>
        </div>
        <div className="text-center" title={riskHelp(fund.risk)}>
          <p className="text-xs text-slate-400 mb-1">Risk</p>
          <p className={`text-sm font-bold ${riskColor(fund.risk?.level)}`}>{fund.risk?.level ?? "Unknown"}</p>
          <p className={`text-[10px] ${fund.risk?.official ? "text-emerald-600 dark:text-emerald-400" : "text-slate-400"}`}>{fund.risk?.official ? "SEBI official" : "estimated"}</p>
          {fund.analytics.max_drawdown != null && <p className="text-[10px] text-slate-400">worst fall {fund.analytics.max_drawdown.toFixed(0)}%</p>}
        </div>
        <div className="text-center" title="How steady past gains were when markets fell. Steady = held up better in downs. Based on Sortino.">
          <p className="text-xs text-slate-400 mb-1">Steadiness</p>
          <p className={`text-sm font-bold ${steady.color}`}>{steady.label}</p>
        </div>
      </div>
      <NavSparkline schemeId={fund.scheme_id} years={horizon} />
      <details className="mt-3 text-xs text-slate-400">
        <summary className="cursor-pointer hover:text-slate-600">Show advanced (Sharpe {fund.analytics.sharpe_ratio.toFixed(2)}, Sortino {fund.analytics.sortino_ratio.toFixed(2)})</summary>
        <p className="mt-1">Sharpe = return per risk. Sortino = return per downside risk. Higher = better, but shown here for reference. Past performance does not guarantee future returns.{fund.data_as_of ? ` NAV data as of ${fund.data_as_of}.` : ""}</p>
      </details>

      {selected && (
        <div className="mt-3 pt-3 border-t border-indigo-100 dark:border-indigo-900/30">
          <div className="flex items-center justify-center gap-2">
            <div className="w-5 h-5 bg-indigo-500 rounded-full flex items-center justify-center">
              <svg className="w-3 h-3 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={3} d="M5 13l4 4L19 7" />
              </svg>
            </div>
            <span className="text-sm font-semibold text-indigo-600">Selected for comparison</span>
          </div>
        </div>
      )}
    </div>
  );
}
