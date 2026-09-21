"use client";

import { useState, useEffect } from "react";
import { FundCard } from "./components/fund-card";
import { ComparisonTable } from "./components/comparison-table";
import { RollingReturnsChart } from "./components/rolling-returns-chart";
import { OverlapMatrix } from "./components/overlap-matrix";
import { FundFilter } from "./components/fund-filter";
import { ChatTab } from "./components/chat-tab";
import { NavHistoryChart } from "./components/nav-history-chart";
import { HolisticPanel } from "./components/holistic-panel";
import { SipCalculator } from "./components/sip-calculator";

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
  const [loading, setLoading] = useState(false);
  const [hasSearched, setHasSearched] = useState(false);
  const [investmentAmount, setInvestmentAmount] = useState<number>(100000);
  const [horizonYears, setHorizonYears] = useState<number>(5);
  const [investmentMode, setInvestmentMode] = useState<"lump-sum" | "sip">("lump-sum");
  const [riskAppetite, setRiskAppetite] = useState<"low" | "medium" | "high">("medium");
  const [category, setCategory] = useState("");
  const [selectedFunds, setSelectedFunds] = useState<number[]>([]);
  const [activeTab, setActiveTab] = useState<"discover" | "chat">("discover");
  const [sortBy, setSortBy] = useState<"overall" | "return" | "stars" | "steadiness">("overall");
  const [minScore, setMinScore] = useState(0);
  const [minReturn, setMinReturn] = useState(0);
  const [minStars, setMinStars] = useState(1);
  const [steadinessFilter, setSteadinessFilter] = useState<string>("all");

  const fetchFunds = async () => {
    setLoading(true);
    setHasSearched(true);
    try {
      const params = new URLSearchParams({
        investment_amount: String(investmentAmount),
        investment_mode: investmentMode,
        horizon_years: String(horizonYears),
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

  // Filtering and sorting
  const steadinessVal = (sortino: number) => (sortino >= 0.9 ? 2 : sortino >= 0.6 ? 1 : 0);
  const filteredFunds = funds.filter((f) => {
    const stars = Math.max(1, Math.round(f.ocs_score / 20));
    const steady = steadinessVal(f.analytics.sortino_ratio);
    const steadyFilterVal = steadinessFilter === "all" ? -1 : steadinessFilter === "very" ? 2 : steadinessFilter === "steady" ? 1 : 0;
    return (
      f.ocs_score >= minScore &&
      f.analytics.cagr >= minReturn &&
      stars >= minStars &&
      (steadinessFilter === "all" || steady === steadyFilterVal || (steadinessFilter === "steady+" && steady >= 1))
    );
  });
  const sortedFunds = [...filteredFunds].sort((a, b) => {
    if (sortBy === "return") return b.analytics.cagr - a.analytics.cagr;
    if (sortBy === "stars") return Math.round(b.ocs_score/20) - Math.round(a.ocs_score/20);
    if (sortBy === "steadiness") return b.analytics.sortino_ratio - a.analytics.sortino_ratio;
    return b.ocs_score - a.ocs_score;
  });

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
          <h1 className="text-5xl md:text-6xl font-bold mb-3 text-white">
            AI-Powered Fund
            <br />
            <span className="text-blue-100">Recommendations</span>
          </h1>
          <p className="text-lg text-blue-50 max-w-2xl">
            Discover top-performing mutual funds with objective composite scoring, risk-adjusted analytics, and smart portfolio analysis.
          </p>
        </div>
      </header>

      {/* Tabs */}
      <div className="max-w-7xl mx-auto px-6 pt-6">
        <div className="flex gap-2 p-1 bg-gray-100 dark:bg-gray-800 rounded-xl w-fit">
          <button onClick={()=>setActiveTab("discover")} className={`px-5 py-2 rounded-lg text-sm font-semibold transition ${activeTab==="discover" ? "bg-white dark:bg-gray-700 shadow text-indigo-600" : "text-gray-500"}`}>Discover</button>
          <button onClick={()=>setActiveTab("chat")} className={`px-5 py-2 rounded-lg text-sm font-semibold transition ${activeTab==="chat" ? "bg-white dark:bg-gray-700 shadow text-indigo-600" : "text-gray-500"}`}>GenAI Chat</button>
        </div>
      </div>

      {/* Main Content */}
      <main className="max-w-7xl mx-auto px-6 py-8 space-y-8">
        {activeTab === "chat" ? (
          <ChatTab />
        ) : (
          <>
        {/* Investment Parameters — lean landing, only applicable funds after Find */}
        <section className="glass-card p-6">
          <div className="flex items-center gap-2 mb-4">
            <div className="w-8 h-8 bg-indigo-100 dark:bg-indigo-900/30 rounded-lg flex items-center justify-center">
              <svg className="w-4 h-4 text-indigo-600" fill="none" stroke="currentColor" viewBox="0 0/24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 6V4m0 2a2 2 0 100 4m0-4a2 2 0 110 4m-6 8a2 2 0 100-4m0 4a2 2 0 110-4m0 4v2m0-6V4m6 6v10m6-2a2 2 0 100-4m0 4a2 2 0 110-4m0 4v2m0-6V4" /></svg>
            </div>
            <h3 className="font-bold text-gray-800 dark:text-gray-100">Tell us about your investment</h3>
            <span className="text-xs text-gray-400 ml-2">We’ll show only funds that match</span>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-3 lg:grid-cols-6 gap-4">
            <div>
              <label className="block text-xs font-semibold text-gray-500 uppercase tracking-wider mb-1">Amount (₹)</label>
              <input type="number" value={investmentAmount} onChange={(e)=>setInvestmentAmount(Number(e.target.value))} placeholder="100000" className="w-full rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 px-3 py-2 text-sm" />
            </div>
            <div>
              <label className="block text-xs font-semibold text-gray-500 uppercase tracking-wider mb-1">Mode</label>
              <select value={investmentMode} onChange={(e)=>setInvestmentMode(e.target.value as any)} className="w-full rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 px-3 py-2 text-sm">
                <option value="lump-sum">Lump Sum</option>
                <option value="sip">SIP</option>
              </select>
            </div>
            <div>
              <label className="block text-xs font-semibold text-gray-500 uppercase tracking-wider mb-1">Horizon</label>
              <select value={horizonYears} onChange={(e)=>setHorizonYears(Number(e.target.value))} className="w-full rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 px-3 py-2 text-sm">
                <option value={1}>1 Year</option><option value={3}>3 Years</option><option value={5}>5 Years</option><option value={10}>10 Years</option>
              </select>
            </div>
            <div>
              <label className="block text-xs font-semibold text-gray-500 uppercase tracking-wider mb-1">Risk</label>
              <select value={riskAppetite} onChange={(e)=>setRiskAppetite(e.target.value as any)} className="w-full rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 px-3 py-2 text-sm">
                <option value="low">Low</option><option value="medium">Medium</option><option value="high">High</option>
              </select>
            </div>
            <div>
              <label className="block text-xs font-semibold text-gray-500 uppercase tracking-wider mb-1">Category</label>
              <select value={category} onChange={(e)=>setCategory(e.target.value)} className="w-full rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 px-3 py-2 text-sm">
                <option value="">All</option><option value="Large Cap">Large Cap</option><option value="Mid Cap">Mid Cap</option><option value="Small Cap">Small Cap</option><option value="Flexi Cap">Flexi Cap</option><option value="ELSS">ELSS</option><option value="Hybrid">Hybrid</option><option value="Debt">Debt</option><option value="Index">Index</option>
              </select>
            </div>
            <div className="flex items-end">
              <button onClick={fetchFunds} className="w-full rounded-xl bg-indigo-600 text-white px-4 py-2.5 text-sm font-semibold hover:bg-indigo-700 transition">Find Funds →</button>
            </div>
          </div>
          <p className="text-xs text-gray-400 mt-3">No funds are loaded until you click Find Funds — faster landing, only applicable funds shown. Uses Direct Growth, OCS with SIP/Lump adjustments.</p>
        </section>

        {/* Sort & Filter Sliders — only after search to keep landing lean */}
        {hasSearched && (
        <section className="glass-card p-5">
          <div className="flex items-center gap-2 mb-4">
            <div className="w-8 h-8 bg-amber-100 dark:bg-amber-900/30 rounded-lg flex items-center justify-center">
              <svg className="w-4 h-4 text-amber-600" fill="none" stroke="currentColor" viewBox="0 0/24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 4h13M3 8h9m-9 4h9m5-4v12m0 0l-4-4m4 4l4-4" /></svg>
            </div>
            <h3 className="font-bold text-gray-800 dark:text-gray-100">Sort & Filter</h3>
            <span className="text-xs text-gray-400 ml-2">{filteredFunds.length} of {funds.length} shown</span>
            <button onClick={()=>{setMinScore(0);setMinReturn(0);setMinStars(1);setSteadinessFilter("all");setSortBy("overall");}} className="ml-auto text-xs text-indigo-600 hover:underline">Reset</button>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-5 gap-4">
            <div>
              <label className="block text-xs font-semibold text-gray-500 uppercase tracking-wider mb-1">Sort by</label>
              <select value={sortBy} onChange={(e)=>setSortBy(e.target.value as any)} className="w-full rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 px-3 py-2 text-sm">
                <option value="overall">Overall Score</option>
                <option value="stars">Star Rating</option>
                <option value="return">Annual Return</option>
                <option value="steadiness">Steadiness</option>
              </select>
            </div>
            <div>
              <label className="block text-xs font-semibold text-gray-500 uppercase tracking-wider mb-1">Min Overall Score: {minScore}</label>
              <input type="range" min={0} max={100} value={minScore} onChange={(e)=>setMinScore(Number(e.target.value))} className="w-full accent-indigo-600" />
              <div className="flex justify-between text-xs text-gray-400"><span>0</span><span>100</span></div>
            </div>
            <div>
              <label className="block text-xs font-semibold text-gray-500 uppercase tracking-wider mb-1">Min Stars: {minStars}★</label>
              <input type="range" min={1} max={5} step={1} value={minStars} onChange={(e)=>setMinStars(Number(e.target.value))} className="w-full accent-amber-500" />
              <div className="flex justify-between text-xs text-gray-400"><span>1★</span><span>5★</span></div>
            </div>
            <div>
              <label className="block text-xs font-semibold text-gray-500 uppercase tracking-wider mb-1">Min Annual Return: {minReturn}%</label>
              <input type="range" min={0} max={25} value={minReturn} onChange={(e)=>setMinReturn(Number(e.target.value))} className="w-full accent-green-600" />
              <div className="flex justify-between text-xs text-gray-400"><span>0%</span><span>25%</span></div>
            </div>
            <div>
              <label className="block text-xs font-semibold text-gray-500 uppercase tracking-wider mb-1">Steadiness</label>
              <select value={steadinessFilter} onChange={(e)=>setSteadinessFilter(e.target.value)} className="w-full rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 px-3 py-2 text-sm">
                <option value="all">All</option>
                <option value="very">Very steady</option>
                <option value="steady">Steady</option>
                <option value="bumpy">Bumpy</option>
                <option value="steady+">Steady+</option>
              </select>
            </div>
          </div>
        </section>
        )}

        {!hasSearched && (
          <div className="glass-card p-12 text-center">
            <div className="w-16 h-16 bg-indigo-100 dark:bg-indigo-900/30 rounded-2xl flex items-center justify-center mx-auto mb-4">
              <svg className="w-8 h-8 text-indigo-500" fill="none" stroke="currentColor" viewBox="0 0/24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" /></svg>
            </div>
            <h3 className="text-lg font-semibold text-gray-800 dark:text-gray-100 mb-2">Ready to find your best funds?</h3>
            <p className="text-gray-500">Choose amount, horizon, risk and category above, then click <span className="font-semibold text-indigo-600">Find Funds</span>.</p>
            <p className="text-xs text-gray-400 mt-2">We’ll load only funds that match — faster, focused, holistic.</p>
          </div>
        )}

        {/* Stats Bar — only after search to keep landing lean */}
        {hasSearched && (
        <>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <div className="glass-card p-4">
            <p className="text-sm text-gray-500 mb-1">Funds Shown</p>
            <p className="text-2xl font-bold text-blue-600">{sortedFunds.length}<span className="text-sm font-normal text-gray-400">/{funds.length}</span></p>
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
              <span className="text-sm text-gray-500">Click to select for comparison • Sorted by {sortBy}</span>
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
            ) : sortedFunds.length === 0 ? (
              <div className="glass-card p-12 text-center">
                <div className="w-16 h-16 bg-blue-100 dark:bg-blue-900/30 rounded-2xl flex items-center justify-center mx-auto mb-4">
                  <svg className="w-8 h-8 text-blue-500" fill="none" stroke="currentColor" viewBox="0 0/24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9.172 16.172a4 4 0 015.656 0M9 10h.01M15 10h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                  </svg>
                </div>
                <h3 className="text-lg font-semibold text-gray-600 mb-2">No Funds Match Filters</h3>
                <p className="text-gray-500">Try lowering sliders or changing category.</p>
              </div>
            ) : (
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {sortedFunds.map((fund) => (
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
              <RollingReturnsChart funds={sortedFunds} selectedFunds={selectedFunds} />
            </div>

            <div className="glass-card p-6">
              <h2 className="text-xl font-bold text-gray-800 dark:text-gray-100 mb-4">Fund Comparison</h2>
              <ComparisonTable funds={sortedFunds} selectedFunds={selectedFunds} />
            </div>
          </div>
        </div>

        {/* Historic NAV Chart + Holistic for first selected fund */}
        {selectedFunds.length >= 1 && (
          <>
            <section className="glass-card p-6">
              <h2 className="text-xl font-bold text-gray-800 dark:text-gray-100 mb-4">Historic NAV — Detailed History</h2>
              {(() => {
                const f = sortedFunds.find(x => x.scheme_id === selectedFunds[0]) || funds.find(x => x.scheme_id === selectedFunds[0]);
                return f ? <NavHistoryChart schemeId={f.scheme_id} schemeName={f.scheme_name} /> : null;
              })()}
              <p className="text-xs text-gray-400 mt-2">Daily NAV from mfapi.in / AMFI • Use tabs 1Y/3Y/5Y • Data powers rolling returns, Sharpe, Sortino in OCS</p>
            </section>
            <section>
              {(() => {
                const f = sortedFunds.find(x => x.scheme_id === selectedFunds[0]) || funds.find(x => x.scheme_id === selectedFunds[0]);
                return f ? <HolisticPanel schemeId={f.scheme_id} /> : null;
              })()}
            </section>
            <section>
              {(() => {
                const f = sortedFunds.find(x => x.scheme_id === selectedFunds[0]) || funds.find(x => x.scheme_id === selectedFunds[0]);
                return f ? <SipCalculator schemeId={f.scheme_id} /> : null;
              })()}
            </section>
          </>
        )}

        {/* Overlap Matrix */}
        {selectedFunds.length >= 2 && (
          <section>
            <OverlapMatrix fundIds={selectedFunds} />
          </section>
        )}
          </>
        )}
          </>
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
