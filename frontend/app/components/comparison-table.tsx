import { Fund } from "@/types/fund";

interface ComparisonTableProps {
  funds: Fund[];
  selectedFunds: number[];
}

export function ComparisonTable({ funds, selectedFunds }: ComparisonTableProps) {
  if (selectedFunds.length < 2 || !funds || funds.length === 0) {
    return (
      <div className="text-center text-gray-500 py-8">
        Select at least 2 funds to compare
      </div>
    );
  }

  const selectedFundsData = funds.filter((f) =>
    selectedFunds.includes(f.scheme_id)
  );

  const metrics = [
    { label: "CAGR", key: "cagr", format: (v: number) => `${v.toFixed(2)}%` },
    { label: "Sharpe Ratio", key: "sharpe_ratio", format: (v: number) => v.toFixed(2) },
    { label: "Sortino Ratio", key: "sortino_ratio", format: (v: number) => v.toFixed(2) },
    { label: "Beta", key: "beta", format: (v: number) => v.toFixed(2) },
    { label: "OCS Score", key: "ocs_score", format: (v: number) => v.toFixed(1) },
  ];

  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b">
            <th className="text-left p-2">Metric</th>
            {selectedFundsData.map((fund) => (
              <th key={fund.scheme_id} className="text-right p-2">
                {fund.scheme_name}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {metrics.map((metric) => (
            <tr key={metric.key} className="border-b last:border-0">
              <td className="p-2 text-gray-600">{metric.label}</td>
              {selectedFundsData.map((fund) => {
                const value = metric.key === "ocs_score" 
                  ? fund.ocs_score 
                  : fund.analytics[metric.key as keyof Fund['analytics']] || 0;
                return (
                  <td key={fund.scheme_id} className="p-2 text-right font-medium">
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
