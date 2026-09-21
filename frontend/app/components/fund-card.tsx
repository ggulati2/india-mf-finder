import { Fund } from "../types/fund";

interface FundCardProps {
  fund: Fund;
  selected: boolean;
  onToggle: () => void;
}

export function FundCard({ fund, selected, onToggle }: FundCardProps) {
  const getScoreColor = (score: number) => {
    if (score >= 75) return "text-green-600";
    if (score >= 50) return "text-blue-600";
    if (score >= 25) return "text-amber-600";
    return "text-red-600";
  };

  const getScoreBadge = (score: number) => {
    if (score >= 75) return "bg-green-50 text-green-700 border-green-200";
    if (score >= 50) return "bg-blue-50 text-blue-700 border-blue-200";
    if (score >= 25) return "bg-amber-50 text-amber-700 border-amber-200";
    return "bg-red-50 text-red-700 border-red-200";
  };

  return (
    <div
      className={`group rounded-2xl border-2 p-5 transition-all duration-300 cursor-pointer ${
        selected
          ? "border-indigo-500 bg-indigo-50/50 shadow-md shadow-indigo-100 dark:shadow-indigo-900/20"
          : "border-gray-100 bg-white hover:border-indigo-300 hover:bg-indigo-50/30 dark:border-gray-800 dark:bg-gray-900 dark:hover:border-indigo-600 dark:hover:bg-gray-800/50"
      }`}
      onClick={onToggle}
    >
      <div className="flex items-start justify-between mb-3">
        <div className="flex-1 min-w-0">
          <h3 className="font-bold text-gray-900 dark:text-white truncate text-base">
            {fund.scheme_name}
          </h3>
          <p className="text-sm text-gray-500 dark:text-gray-400 mt-0.5">
            {fund.amc_name} · {fund.category}
          </p>
        </div>
        <div className="flex flex-col items-end gap-2 ml-3">
          <span
            className={`text-3xl font-bold ${getScoreColor(fund.ocs_score)}`}
          >
            {fund.ocs_score.toFixed(1)}
          </span>
          <span
            className={`text-xs font-semibold px-2 py-0.5 rounded-full border ${getScoreBadge(
              fund.ocs_score
            )}`}
          >
            OCS Score
          </span>
        </div>
      </div>

      <div className="grid grid-cols-3 gap-3 mt-4 pt-4 border-t border-gray-100 dark:border-gray-800">
        <div className="text-center">
          <p className="text-xs text-gray-400 mb-1">CAGR</p>
          <p className="text-sm font-bold text-green-600">
            {fund.analytics.cagr.toFixed(2)}%
          </p>
        </div>
        <div className="text-center">
          <p className="text-xs text-gray-400 mb-1">Sharpe</p>
          <p className="text-sm font-bold text-blue-600">
            {fund.analytics.sharpe_ratio.toFixed(2)}
          </p>
        </div>
        <div className="text-center">
          <p className="text-xs text-gray-400 mb-1">Sortino</p>
          <p className="text-sm font-bold text-amber-600">
            {fund.analytics.sortino_ratio.toFixed(2)}
          </p>
        </div>
      </div>

      {selected && (
        <div className="mt-3 pt-3 border-t border-indigo-100 dark:border-indigo-900/30">
          <div className="flex items-center justify-center gap-2">
            <div className="w-5 h-5 bg-indigo-500 rounded-full flex items-center justify-center">
              <svg className="w-3 h-3 text-white" fill="none" stroke="currentColor" viewBox="0 0/24 24">
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
