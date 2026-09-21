"use client";

import { useState, useEffect } from "react";
import { FundCard } from "@/components/fund-card";
import { ComparisonTable } from "@/components/comparison-table";
import { RollingReturnsChart } from "@/components/rolling-returns-chart";
import { OverlapMatrix } from "@/components/overlap-matrix";
import { FundFilter } from "@/components/fund-filter";

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
    <div className="min-h-screen bg-background p-6">
      <h1 className="text-4xl font-bold text-primary mb-8">
        India Mutual Fund Finder
      </h1>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2">
          <FundFilter
            investmentMode={investmentMode}
            setInvestmentMode={setInvestmentMode}
            riskAppetite={riskAppetite}
            setRiskAppetite={setRiskAppetite}
            category={category}
            setCategory={setCategory}
          />

          {loading ? (
            <div className="animate-pulse space-y-4">
              {[1, 2, 3].map((i) => (
                <div key={i} className="h-24 bg-gray-200 rounded" />
              ))}
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mt-4">
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

        <div className="space-y-6">
          <div className="bg-card rounded-lg p-6 border">
            <h2 className="text-xl font-semibold mb-4">Portfolio Analytics</h2>
            <RollingReturnsChart funds={funds} selectedFunds={selectedFunds} />
          </div>

          <div className="bg-card rounded-lg p-6 border">
            <h2 className="text-xl font-semibold mb-4">Fund Comparison</h2>
            <ComparisonTable funds={funds} selectedFunds={selectedFunds} />
          </div>
        </div>
      </div>

      {selectedFunds.length >= 2 && (
        <div className="mt-8">
          <OverlapMatrix fundIds={selectedFunds} />
        </div>
      )}
    </div>
  );
}
