"use client";

import { useState, useEffect } from "react";
import { FundCard } from "./components/fund-card";
import { ComparisonTable } from "./components/comparison-table";
import { RollingReturnsChart } from "./components/rolling-returns-chart";
import { OverlapMatrix } from "./components/overlap-matrix";
import { FundFilter } from "./components/fund-filter";

interface Fund {
  scheme_id: number;
  scheme_name: string;
  amc_name: string;
  category: string;
  ocs_score: number;
  analytics: {
    cagr: number;
    sharpe_ratio: number;
    sortino_ratio: number;
    beta: number;
  };
}

export default function Dashboard() {
  const [funds, setFunds] = useState<Fund[]>([]);
  const [loading, setLoading] = useState(true);
  const [investmentMode, setInvestmentMode] = useState<"lump-sum" | "sip">("lump-sum");
  const [riskAppetite, setRiskAppetite] = useState<"low" | "medium" | "high">("medium");
  const [category, setCategory] = useState("");
  const [selectedFunds, setSelectedFunds] = useState<number[]>([]);

  useEffect(() => {
    fetchFunds();
  }, [investmentMode, riskAppetite, category]);

  const fetchFunds = async () => {
    try {
      const params = new URLSearchParams({
        investment_mode: investmentMode,
        risk_appetite: riskAppetite,
        category: category,
      });
      const response = await fetch(`/api/recommendations/funds?${params}`);
      const data = await response.json();
      setFunds(Array.isArray(data) ? data : []);
    } catch (error) {
      console.error("Error fetching funds:", error);
      setFunds([]);
    } finally {
      setLoading(false);
    }
  };

  const toggleFund = (schemeId: number) => {
    setSelectedFunds((prev) =>
      prev.includes(schemeId)
        ? prev.filter((id) => id !== schemeId)
        : [...prev, schemeId]
    );
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 via-blue-50/30 to-indigo-50/30 dark:from-slate-900 dark:via-slate-800 dark:to-indigo-900/30">
      {/* Hero Header */}
      <header className="relative overflow-hidden bg-gradient-to-r from-blue-600 via-indigo-600 to-purple-600 text-white">
        <div className="absolute inset-0 opacity-10">
          <div className="absolute top-0 left-1/4 w-96 h-96 bg-white rounded-full blur-3xl -translate-y-1/2"></div>
          <div className="absolute bottom-0 right-1/4 w-96 h-96 bg-white rounded-full blur-3xl translate-y-1/2"></div>
        </div>
        <div className="relative max-w-7xl mx-auto px-6 py-12 md:py-16">
          <div className="flex items-center gap-3 mb-4">
            <div className="w-10 h-10 bg-white/20 rounded-xl flex items-center justify-center backdrop-blur-sm">
              <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0/24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 7h8m0 0v8m0-8l-8 8-4-4-6 6" />
              </svg>
            </div>
            <span className="text-sm font-medium text-blue-100 tracking-wide uppercase">India Mutual Fund Finder</span>
          </div>
          <h1 className="text-5xl md:text-6xl font-bold mb-3 gradient-text">
            AI-Powered Fund
            <br />
            <span className="text-white">Recommendations</span>
          </h1>
          <p className="text-lg text-blue-100 max-w-2xl">
            Discover top-performing mutual funds with objective composite scoring, risk-adjusted analytics, and smart portfolio analysis.
          </p>
        </div>
      </header>

      {/* Main Content */}
      <main className="max-w-7xl mx-auto px-6 py-8 space-y-8">
        {/* Investment Parameters */}
        <section>
          <FundFilter
            investmentMode={investmentMode}
            setInvestmentMode={setInvestmentMode}
            riskAppetite={riskAppetite}
            setRiskAppetite={setRiskAppetite}
            category={category}
            setCategory={setCategory}
          />
        </section>

        {/* Stats Bar */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <div className="glass-card p-4">
            <p className="text-sm text-gray-500 mb-1">Funds Analyzed</p>
            <p className="text-2xl font-bold text-blue-600">{funds.length}</p>
          </div>
          <div className="glass-card p-4">
            <p className="text-sm text-gray-500 mb-1">Mode</p>
            <p className="text-2xl font-bold text-indigo-600 capitalize">{investmentMode}</p>
          </div>
          <div className="glass-card p-4">
            <p className="text-sm text-gray-500 mb-1">Risk Level</p>
            <p className="text-2xl font-bold text-amber-600 capitalize">{riskAppetite}</p>
          </div>
          <div className="glass-card p-4">
            <p className="text-sm text-gray-500 mb-1">Selected</p>
            <p className="text-2xl font-bold text-purple-600">{selectedFunds.length}</p>
          </div>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Fund Cards */}
          <div className="lg:col-span-2">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-xl font-bold text-gray-800 dark:text-gray-100">Recommended Funds</h2>
              <span className="text-sm text-gray-500">Click to select for comparison</span>
            </div>

            {loading ? (
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {[1, 2, 3, 4].map((i) => (
                  <div key={i} className="glass-card p-6 animate-pulse">
                    <div className="h-4 bg-gray-200 rounded w-3/4 mb-3"></div>
                    <div className="h-3 bg-gray-200 rounded w-1/2 mb-2"></div>
                    <div className="h-8 bg-gray-200 rounded w-1/3"></div>
                  </div>
                ))}
              </div>
            ) : funds.length === 0 ? (
              <div className="glass-card p-12 text-center">
                <div className="w-16 h-16 bg-blue-100 dark:bg-blue-900/30 rounded-2xl flex items-center justify-center mx-auto mb-4">
                  <svg className="w-8 h-8 text-blue-500" fill="none" stroke="currentColor" viewBox="0 0/24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9.172 16.172a4 4 0 015.656 0M9 10h.01M15 10h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                  </svg>
                </div>
                <h3 className="text-lg font-semibold text-gray-600 mb-2">No Funds Found</h3>
                <p className="text-gray-500">Try adjusting your filters or investment parameters.</p>
              </div>
            ) : (
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {funds.map((fund) => (
                  <FundCard
                    key={fund.scheme_id}
                    fund={fund}
                    selected={selectedFunds.includes(fund.scheme_id)}
                    onToggle={() => toggleFund(fund.scheme_id)}
                  />
                ))}
              </div>
            )}
          </div>

          {/* Right Sidebar */}
          <div className="space-y-6">
            <div className="glass-card p-6">
              <h2 className="text-xl font-bold text-gray-800 dark:text-gray-100 mb-4">Portfolio Analytics</h2>
              <RollingReturnsChart funds={funds} selectedFunds={selectedFunds} />
            </div>

            <div className="glass-card p-6">
              <h2 className="text-xl font-bold text-gray-800 dark:text-gray-100 mb-4">Fund Comparison</h2>
              <ComparisonTable funds={funds} selectedFunds={selectedFunds} />
            </div>
          </div>
        </div>

        {/* Overlap Matrix */}
        {selectedFunds.length >= 2 && (
          <section>
            <OverlapMatrix fundIds={selectedFunds} />
          </section>
        )}
      </main>

      {/* Footer */}
      <footer className="border-t border-gray-200 dark:border-gray-800 mt-12">
        <div className="max-w-7xl mx-auto px-6 py-6 flex items-center justify-between text-sm text-gray-500">
          <p>© 2024 India Mutual Fund Finder</p>
          <p>AI-Powered Analytics Engine</p>
        </div>
      </footer>
    </div>
  );
}
