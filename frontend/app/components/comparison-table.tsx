import { Fund } from "@/types/fund";

interface ComparisonTableProps {
  funds: Fund[];
  selectedFunds: number[];
}

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
        </div>
      </div>
    );
  }

  const selectedFundsData = funds.filter((f) =>
    selectedFunds.includes(f.scheme_id)
  );

  const metrics = [
    { label: "CAGR", key: "cagr", format: (v: number) => `${v.toFixed(2)}%`, color: "text-green-600" },
    { label: "Sharpe Ratio", key: "sharpe_ratio", format: (v: number) => v.toFixed(2), color: "text-blue-600" },
    { label: "Sortino Ratio", key: "sortino_ratio", format: (v: number) => v.toFixed(2), color: "text-amber-600" },
    { label: "Beta", key: "beta", format: (v: number) => v.toFixed(2), color: "text-purple-600" },
    { label: "OCS Score", key: "ocs_score", format: (v: number) => v.toFixed(1), color: "text-indigo-600" },
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
          {metrics.map((metric) => (
            <tr key={metric.key} className="border-b border-gray-50 dark:border-gray-800 hover:bg-gray-50 dark:hover:bg-gray-800/50 transition-colors">
              <td className="p-3 text-gray-600 dark:text-gray-400 font-medium text-xs">{metric.label}</td>
              {selectedFundsData.map((fund) => {
                const value = metric.key === "ocs_score"
                  ? fund.ocs_score
                  : (fund.analytics[metric.key as keyof Fund['analytics']] || 0);
                return (
                  <td key={fund.scheme_id} className={`p-3 text-right font-bold ${metric.color}`}>
                    {metric.format(value as number)}
                  </td>
                );
              })}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
