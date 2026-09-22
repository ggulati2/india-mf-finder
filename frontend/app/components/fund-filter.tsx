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
    <div className="card p-6">
      <div className="flex items-center gap-2 mb-4">
        <div className="w-8 h-8 bg-indigo-100 dark:bg-indigo-900/30 rounded-lg flex items-center justify-center">
          <svg className="w-4 h-4 text-indigo-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 6V4m0 2a2 2 0 100 4m0-4a2 2 0 110 4m-6 8a2 2 0 100-4m0 4a2 2 0 110-4m0 4v2m0-6V4m6 6v10m6-2a2 2 0 100-4m0 4a2 2 0 110-4m0 4v2m0-6V4" />
          </svg>
        </div>
        <h2 className="text-xl font-bold text-slate-800 dark:text-slate-100">Investment Parameters</h2>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <div>
          <label className="block text-xs font-semibold text-slate-500 uppercase tracking-wider mb-2">
            Investment Mode
          </label>
          <div className="relative">
            <select
              value={investmentMode}
              onChange={(e) => setInvestmentMode(e.target.value as "lump-sum" | "sip")}
              className="w-full appearance-none rounded-xl border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 px-4 py-3 text-sm font-medium text-slate-700 dark:text-slate-200 transition-all focus:border-indigo-500 focus:ring-2 focus:ring-indigo-100 dark:focus:ring-indigo-900/50 focus:outline-none"
            >
              <option value="lump-sum" className="py-2">💰 Lump Sum</option>
              <option value="sip" className="py-2">📈 SIP (Monthly)</option>
            </select>
            <div className="absolute inset-y-0 right-0 flex items-center px-3 pointer-events-none">
              <svg className="w-4 h-4 text-slate-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
              </svg>
            </div>
          </div>
        </div>

        <div>
          <label className="block text-xs font-semibold text-slate-500 uppercase tracking-wider mb-2">
            Risk Appetite
          </label>
          <div className="relative">
            <select
              value={riskAppetite}
              onChange={(e) => setRiskAppetite(e.target.value as "low" | "medium" | "high")}
              className="w-full appearance-none rounded-xl border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 px-4 py-3 text-sm font-medium text-slate-700 dark:text-slate-200 transition-all focus:border-indigo-500 focus:ring-2 focus:ring-indigo-100 dark:focus:ring-indigo-900/50 focus:outline-none"
            >
              <option value="low">🛡️ Low Risk</option>
              <option value="medium">⚖️ Medium Risk</option>
              <option value="high">🚀 High Risk</option>
            </select>
            <div className="absolute inset-y-0 right-0 flex items-center px-3 pointer-events-none">
              <svg className="w-4 h-4 text-slate-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
              </svg>
            </div>
          </div>
        </div>

        <div>
          <label className="block text-xs font-semibold text-slate-500 uppercase tracking-wider mb-2">
            Category
          </label>
          <div className="relative">
            <select
              value={category}
              onChange={(e) => setCategory(e.target.value)}
              className="w-full appearance-none rounded-xl border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 px-4 py-3 text-sm font-medium text-slate-700 dark:text-slate-200 transition-all focus:border-indigo-500 focus:ring-2 focus:ring-indigo-100 dark:focus:ring-indigo-900/50 focus:outline-none"
            >
              <option value="">All Categories</option>
              <option value="Large Cap">Large Cap</option>
              <option value="Mid Cap">Mid Cap</option>
              <option value="Small Cap">Small Cap</option>
              <option value="Flexi Cap">Flexi Cap</option>
              <option value="Hybrid">Hybrid</option>
            </select>
            <div className="absolute inset-y-0 right-0 flex items-center px-3 pointer-events-none">
              <svg className="w-4 h-4 text-slate-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
              </svg>
            </div>
          </div>
        </div>

        <div>
          <label className="block text-xs font-semibold text-slate-500 uppercase tracking-wider mb-2">
            Time Horizon
          </label>
          <div className="relative">
            <select className="w-full appearance-none rounded-xl border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 px-4 py-3 text-sm font-medium text-slate-700 dark:text-slate-200 transition-all focus:border-indigo-500 focus:ring-2 focus:ring-indigo-100 dark:focus:ring-indigo-900/50 focus:outline-none">
              <option value="1">1 Year</option>
              <option value="3">3 Years</option>
              <option value="5" selected>5 Years</option>
              <option value="10">10 Years</option>
            </select>
            <div className="absolute inset-y-0 right-0 flex items-center px-3 pointer-events-none">
              <svg className="w-4 h-4 text-slate-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
              </svg>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
