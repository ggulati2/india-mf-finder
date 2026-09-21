interface FundFilterProps {
  investmentMode: "lump-sum" | "sip";
  setInvestmentMode: (mode: "lump-sum" | "sip") => void;
  riskAppetite: "low" | "medium" | "high";
  setRiskAppetite: (appetite: "low" | "medium" | "high") => void;
  category: string;
  setCategory: (category: string) => void;
}

export function FundFilter({
  investmentMode,
  setInvestmentMode,
  riskAppetite,
  setRiskAppetite,
  category,
  setCategory,
}: FundFilterProps) {
  return (
    <div className="bg-card rounded-lg p-6 border mb-6">
      <h2 className="text-xl font-semibold mb-4">Investment Parameters</h2>

      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <div>
          <label className="block text-sm font-medium mb-2">
            Investment Mode
          </label>
          <select
            value={investmentMode}
            onChange={(e) =>
              setInvestmentMode(e.target.value as "lump-sum" | "sip")
            }
            className="w-full p-2 border rounded-md bg-background"
          >
            <option value="lump-sum">Lump Sum</option>
            <option value="sip">SIP</option>
          </select>
        </div>

        <div>
          <label className="block text-sm font-medium mb-2">
            Risk Appetite
          </label>
          <select
            value={riskAppetite}
            onChange={(e) =>
              setRiskAppetite(e.target.value as "low" | "medium" | "high")
            }
            className="w-full p-2 border rounded-md bg-background"
          >
            <option value="low">Low</option>
            <option value="medium">Medium</option>
            <option value="high">High</option>
          </select>
        </div>

        <div>
          <label className="block text-sm font-medium mb-2">Category</label>
          <select
            value={category}
            onChange={(e) => setCategory(e.target.value)}
            className="w-full p-2 border rounded-md bg-background"
          >
            <option value="">All Categories</option>
            <option value="Large Cap">Large Cap</option>
            <option value="Mid Cap">Mid Cap</option>
            <option value="Small Cap">Small Cap</option>
            <option value="Flexi Cap">Flexi Cap</option>
            <option value="Hybrid">Hybrid</option>
          </select>
        </div>

        <div>
          <label className="block text-sm font-medium mb-2">
            Time Horizon
          </label>
          <select className="w-full p-2 border rounded-md bg-background">
            <option value="1">1 Year</option>
            <option value="3">3 Years</option>
            <option value="5" selected>
              5 Years
            </option>
            <option value="10">10 Years</option>
          </select>
        </div>
      </div>
    </div>
  );
}
