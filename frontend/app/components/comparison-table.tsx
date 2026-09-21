import { Fund } from "../types/fund";
import { riskHelp, fmtTer } from "./risk";

interface ComparisonTableProps {
  funds: Fund[];
  selectedFunds: number[];
}

function steadinessLabel(sortino: number) { return sortino >= 0.9 ? "Very steady" : sortino >= 0.6 ? "Steady" : "Bumpy"; }

export function ComparisonTable({ funds, selectedFunds }: ComparisonTableProps) {
  if (selectedFunds.length < 2 || !funds || funds.length === 0) {
    return (
      <div className="flex items-center justify-center h-full">
        <div className="text-center">
          <div className="w-12 h-12 bg-gray-100 dark:bg-gray-800 rounded-full flex items-center justify-center mx-auto mb-3">
            <svg className="w-6 h-6 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0/24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
            </svg>
          </div>
          <p className="text-sm text-gray-500">Select at least 2 funds to compare</p>
          <p className="text-xs text-gray-400 mt-1">We’ll show simple Annual return, Risk, Steadiness</p>
        </div>
      </div>
    );
  }
  const selectedFundsData = funds.filter((f) => selectedFunds.includes(f.scheme_id));
  const rows = [
    { label: "Past annual return", help: "Compounded yearly return over the chosen past period; history, not a forecast", get: (f:Fund)=> `${f.analytics.cagr.toFixed(1)}%`, cls: "text-green-600" },
    { label: "Overall Score", help: "Our 0-100 combined score (higher = better balance of return, risk, consistency, cost)", get: (f:Fund)=> f.ocs_score.toFixed(0), cls: "text-indigo-600" },
    { label: "Risk level", help: "Official SEBI Riskometer where marked, otherwise our conservative estimate", get: (f:Fund)=> `${f.risk?.level ?? "Unknown"}${f.risk?.official ? " (SEBI)" : " (est.)"}${f.analytics.volatility != null ? ` (vol ${f.analytics.volatility.toFixed(0)}%)` : ""}`, cls: "text-amber-600" },
    { label: "Worst fall", help: "Largest peak-to-trough drop over the period", get: (f:Fund)=> f.analytics.max_drawdown != null ? `${f.analytics.max_drawdown.toFixed(1)}%` : "n/a", cls: "text-red-600" },
    { label: "Steadiness", help: "How it held up when markets fell (from Sortino)", get: (f:Fund)=> steadinessLabel(f.analytics.sortino_ratio), cls: "text-blue-600" },
    { label: "Annual cost", help: "Expense ratio per year", get: (f:Fund)=> fmtTer(f.expense_ratio), cls: "text-gray-600" },
  ];
  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-gray-100 dark:border-gray-700">
            <th className="text-left p-3 text-xs font-semibold text-gray-500 uppercase">Metric</th>
            {selectedFundsData.map((fund) => (
              <th key={fund.scheme_id} className="text-right p-3">
                <span className="text-xs font-semibold text-gray-600 dark:text-gray-300 max-w-[120px] truncate block">
                  {fund.scheme_name.split(" ").slice(0, 2).join(" ")}
                </span>
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((r) => (
            <tr key={r.label} className="border-b border-gray-50 dark:border-gray-800">
              <td className="p-3 text-gray-600 dark:text-gray-400 font-medium text-xs" title={r.help}>{r.label}<span className="ml-1 text-gray-300">ⓘ</span></td>
              {selectedFundsData.map((fund) => (
                <td key={fund.scheme_id} className={`p-3 text-right font-bold ${r.cls}`}>{r.get(fund)}</td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
      <p className="text-xs text-gray-400 mt-2 text-center">Tap ⓘ for plain-English help • Advanced Sharpe/Sortino hidden for simplicity</p>
    </div>
  );
}
