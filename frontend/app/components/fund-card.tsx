import { Fund } from "@/types/fund";

interface FundCardProps {
  fund: Fund;
  selected: boolean;
  onToggle: () => void;
}

export function FundCard({ fund, selected, onToggle }: FundCardProps) {
  return (
    <div
      className={`p-4 rounded-lg border cursor-pointer transition-all hover:shadow-md ${
        selected ? "border-primary bg-primary/5" : "border-gray-200 bg-white"
      }`}
      onClick={onToggle}
    >
      <div className="flex justify-between items-start">
        <div>
          <h3 className="font-semibold text-primary">{fund.scheme_name}</h3>
          <p className="text-sm text-gray-600">{fund.amc_name}</p>
          <p className="text-xs text-gray-500">{fund.category}</p>
        </div>
        <div className="text-right">
          <span className="text-2xl font-bold text-primary">
            {fund.ocs_score.toFixed(1)}
          </span>
          <p className="text-xs text-gray-500">OCS Score</p>
        </div>
      </div>

      <div className="mt-3 grid grid-cols-3 gap-2 text-sm">
        <div>
          <p className="text-gray-500">CAGR</p>
          <p className="font-medium">{fund.analytics.cagr.toFixed(2)}%</p>
        </div>
        <div>
          <p className="text-gray-500">Sharpe</p>
          <p className="font-medium">{fund.analytics.sharpe_ratio.toFixed(2)}</p>
        </div>
        <div>
          <p className="text-gray-500">Sortino</p>
          <p className="font-medium">{fund.analytics.sortino_ratio.toFixed(2)}</p>
        </div>
      </div>

      {selected && (
        <div className="mt-2 text-center text-primary text-sm font-medium">
          ✓ Selected
        </div>
      )}
    </div>
  );
}
