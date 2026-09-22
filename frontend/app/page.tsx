"use client";

import { useState, useEffect } from "react";
import { FundCard } from "./components/fund-card";
import { ComparisonTable } from "./components/comparison-table";
import { RollingReturnsChart } from "./components/rolling-returns-chart";
import { OverlapMatrix } from "./components/overlap-matrix";
import { ChatTab } from "./components/chat-tab";
import { NavHistoryChart } from "./components/nav-history-chart";
import { HolisticPanel } from "./components/holistic-panel";
import { SipCalculator } from "./components/sip-calculator";
import type { Fund } from "./types/fund";

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
  const [completeOnly, setCompleteOnly] = useState(false);
  const [amcFilter, setAmcFilter] = useState("all");
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
        complete_only: String(completeOnly),
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
  const amcOptions = Array.from(new Set(funds.map((f) => f.amc_name))).sort();
  const filteredFunds = funds.filter((f) => {
    const stars = Math.max(1, Math.round(f.ocs_score / 20));
    const steady = steadinessVal(f.analytics.sortino_ratio);
    const steadyFilterVal = steadinessFilter === "all" ? -1 : steadinessFilter === "very" ? 2 : steadinessFilter === "steady" ? 1 : 0;
    return (
      f.ocs_score >= minScore &&
      f.analytics.cagr >= minReturn &&
      stars >= minStars &&
      (steadinessFilter === "all" || steady === steadyFilterVal || (steadinessFilter === "steady+" && steady >= 1)) &&
      (amcFilter === "all" || f.amc_name === amcFilter)
    );
  });
  const sortedFunds = [...filteredFunds].sort((a, b) => {
    if (sortBy === "return") return b.analytics.cagr - a.analytics.cagr;
    if (sortBy === "stars") return Math.round(b.ocs_score/20) - Math.round(a.ocs_score/20);
    if (sortBy === "steadiness") return b.analytics.sortino_ratio - a.analytics.sortino_ratio;
    return b.ocs_score - a.ocs_score;
  });

  return (
    <div className="min-h-screen bg-slate-50 dark:bg-slate-950">
      {/* Top bar */}
      <header className="bg-white dark:bg-slate-900 border-b border-slate-200 dark:border-slate-800">
        <div className="max-w-[1600px] mx-auto px-6 h-16 flex items-center gap-3">
          <div className="w-8 h-8 rounded-lg bg-indigo-600 flex items-center justify-center flex-shrink-0">
            <svg className="w-4.5 h-4.5 text-white" width="18" height="18" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.25} d="M13 7h8m0 0v8m0-8l-8 8-4-4-6 6" />
            </svg>
          </div>
          <span className="font-semibold text-slate-900 dark:text-white tracking-tight">India Mutual Fund Finder</span>
        </div>
      </header>

      {/* Hero */}
      <section className="border-b border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900">
        <div className="max-w-[1600px] mx-auto px-6 py-14 md:py-20">
          <h1 className="text-4xl md:text-5xl font-bold tracking-tight text-slate-900 dark:text-white mb-4 max-w-2xl">
            Objective, data-driven <span className="text-indigo-600">fund recommendations</span>
          </h1>
          <p className="text-lg text-slate-500 dark:text-slate-400 max-w-2xl">
            Composite scoring and risk-adjusted analytics across Direct Growth mutual funds, built on official AMFI data.
          </p>
        </div>
      </section>

      {/* Disclaimer Banner */}
      <div className="bg-amber-50 dark:bg-amber-950/30 border-b border-amber-200 dark:border-amber-900/50">
        <div className="max-w-[1600px] mx-auto px-6 py-2.5 flex items-start gap-2 text-sm text-amber-800 dark:text-amber-300">
          <svg className="w-4.5 h-4.5 flex-shrink-0 mt-0.5" width="18" height="18" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" /></svg>
          <p><span className="font-semibold">Not financial advice.</span> This tool is for informational purposes only and does not constitute investment advice. Please do your own research and consult a SEBI-registered adviser before investing.</p>
        </div>
      </div>

      {/* Tabs */}
      <div className="max-w-[1600px] mx-auto px-6 pt-6">
        <div className="flex gap-1 p-1 bg-slate-100 dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-lg w-fit">
          <button onClick={()=>setActiveTab("discover")} className={`px-4 py-1.5 rounded-md text-sm font-semibold transition-colors ${activeTab==="discover" ? "bg-white dark:bg-slate-800 shadow-sm text-indigo-600 dark:text-indigo-400" : "text-slate-500 hover:text-slate-700 dark:hover:text-slate-300"}`}>Discover</button>
          <button onClick={()=>setActiveTab("chat")} className={`px-4 py-1.5 rounded-md text-sm font-semibold transition-colors flex items-center gap-1.5 ${activeTab==="chat" ? "bg-white dark:bg-slate-800 shadow-sm text-indigo-600 dark:text-indigo-400" : "text-slate-500 hover:text-slate-700 dark:hover:text-slate-300"}`}>
            Ask Me
            <span className="text-[10px] font-bold bg-amber-100 text-amber-700 dark:bg-amber-900/50 dark:text-amber-400 px-1.5 py-0.5 rounded">SOON</span>
          </button>
        </div>
      </div>

      {/* Main Content */}
      <main className="max-w-[1600px] mx-auto px-6 py-8 space-y-8">
        {activeTab === "chat" ? (
          <ChatTab />
        ) : (
          <>
        {/* Investment Parameters — lean landing, only applicable funds after Find */}
        <section className="card p-6">
          <div className="flex items-center gap-2 mb-4">
            <div className="w-8 h-8 bg-indigo-50 dark:bg-indigo-950/40 rounded-lg flex items-center justify-center">
              <svg className="w-4 h-4 text-indigo-600" fill="none" stroke="currentColor" viewBox="0 0/24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 6V4m0 2a2 2 0 100 4m0-4a2 2 0 110 4m-6 8a2 2 0 100-4m0 4a2 2 0 110-4m0 4v2m0-6V4m6 6v10m6-2a2 2 0 100-4m0 4a2 2 0 110-4m0 4v2m0-6V4" /></svg>
            </div>
            <h3 className="font-bold text-slate-800 dark:text-slate-100">Tell us about your investment</h3>
            <span className="text-xs text-slate-400 ml-2">We’ll show only funds that match</span>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-3 lg:grid-cols-6 gap-4">
            <div>
              <label className="block text-xs font-semibold text-slate-500 uppercase tracking-wider mb-1">Amount (₹)</label>
              <input type="number" value={investmentAmount} onChange={(e)=>setInvestmentAmount(Number(e.target.value))} placeholder="100000" className="w-full rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-900 px-3 py-2 text-sm" />
            </div>
            <div>
              <label className="block text-xs font-semibold text-slate-500 uppercase tracking-wider mb-1">Mode</label>
              <select value={investmentMode} onChange={(e)=>setInvestmentMode(e.target.value as any)} className="w-full rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-900 px-3 py-2 text-sm">
                <option value="lump-sum">Lump Sum</option>
                <option value="sip">SIP</option>
              </select>
            </div>
            <div>
              <label className="block text-xs font-semibold text-slate-500 uppercase tracking-wider mb-1">Horizon</label>
              <select value={horizonYears} onChange={(e)=>setHorizonYears(Number(e.target.value))} className="w-full rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-900 px-3 py-2 text-sm">
                <option value={1}>1 Year</option><option value={3}>3 Years</option><option value={5}>5 Years</option><option value={10}>10 Years</option>
              </select>
            </div>
            <div>
              <label className="block text-xs font-semibold text-slate-500 uppercase tracking-wider mb-1">Risk</label>
              <select value={riskAppetite} onChange={(e)=>setRiskAppetite(e.target.value as any)} className="w-full rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-900 px-3 py-2 text-sm">
                <option value="low">Low</option><option value="medium">Medium</option><option value="high">High</option>
              </select>
            </div>
            <div>
              <label className="block text-xs font-semibold text-slate-500 uppercase tracking-wider mb-1">Category</label>
              <select value={category} onChange={(e)=>setCategory(e.target.value)} className="w-full rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-900 px-3 py-2 text-sm">
                <option value="">All</option><option value="Large Cap">Large Cap</option><option value="Mid Cap">Mid Cap</option><option value="Small Cap">Small Cap</option><option value="Flexi Cap">Flexi Cap</option><option value="ELSS">ELSS</option><option value="Hybrid">Hybrid</option><option value="Debt">Debt</option><option value="Index">Index</option>
              </select>
            </div>
            <div className="flex items-end">
              <button onClick={fetchFunds} className="w-full rounded-lg bg-indigo-600 text-white px-4 py-2.5 text-sm font-semibold hover:bg-indigo-700 transition-colors">Find Funds →</button>
            </div>
          </div>
          <p className="text-xs text-slate-400 mt-3">No funds are loaded until you click Find Funds — faster landing, only applicable funds shown. Uses Direct Growth, OCS with SIP/Lump adjustments.</p>
        </section>

        {/* Sort & Filter Sliders — only after search to keep landing lean */}
        {hasSearched && (
        <section className="card p-5">
          <div className="flex items-center gap-2 mb-4">
            <div className="w-8 h-8 bg-amber-50 dark:bg-amber-950/40 rounded-lg flex items-center justify-center">
              <svg className="w-4 h-4 text-amber-600" fill="none" stroke="currentColor" viewBox="0 0/24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 4h13M3 8h9m-9 4h9m5-4v12m0 0l-4-4m4 4l4-4" /></svg>
            </div>
            <h3 className="font-bold text-slate-800 dark:text-slate-100">Sort & Filter</h3>
            <span className="text-xs text-slate-400 ml-2">{filteredFunds.length} of {funds.length} shown</span>
            <label className="flex items-center gap-1.5 text-xs text-slate-600 dark:text-slate-300" title="Hide funds where any data check is missing (for example expense ratio). Click Find Funds again to apply."><input type="checkbox" checked={completeOnly} onChange={(e)=>setCompleteOnly(e.target.checked)} />Only complete data</label>
            <button onClick={()=>{setMinScore(0);setMinReturn(0);setMinStars(1);setSteadinessFilter("all");setAmcFilter("all");setSortBy("overall");}} className="ml-auto text-xs text-indigo-600 hover:underline">Reset</button>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-6 gap-4">
            <div>
              <label className="block text-xs font-semibold text-slate-500 uppercase tracking-wider mb-1">Sort by</label>
              <select value={sortBy} onChange={(e)=>setSortBy(e.target.value as any)} className="w-full rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-900 px-3 py-2 text-sm">
                <option value="overall">Overall Score</option>
                <option value="stars">Star Rating</option>
                <option value="return">Annual Return</option>
                <option value="steadiness">Steadiness</option>
              </select>
            </div>
            <div>
              <label className="block text-xs font-semibold text-slate-500 uppercase tracking-wider mb-1">AMC</label>
              <select value={amcFilter} onChange={(e)=>setAmcFilter(e.target.value)} className="w-full rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-900 px-3 py-2 text-sm">
                <option value="all">All AMCs</option>
                {amcOptions.map((amc) => (<option key={amc} value={amc}>{amc}</option>))}
              </select>
            </div>
            <div>
              <label className="block text-xs font-semibold text-slate-500 uppercase tracking-wider mb-1">Min Overall Score: {minScore}</label>
              <input type="range" min={0} max={100} value={minScore} onChange={(e)=>setMinScore(Number(e.target.value))} className="w-full accent-indigo-600" />
              <div className="flex justify-between text-xs text-slate-400"><span>0</span><span>100</span></div>
            </div>
            <div>
              <label className="block text-xs font-semibold text-slate-500 uppercase tracking-wider mb-1">Min Stars: {minStars}★</label>
              <input type="range" min={1} max={5} step={1} value={minStars} onChange={(e)=>setMinStars(Number(e.target.value))} className="w-full accent-amber-500" />
              <div className="flex justify-between text-xs text-slate-400"><span>1★</span><span>5★</span></div>
            </div>
            <div>
              <label className="block text-xs font-semibold text-slate-500 uppercase tracking-wider mb-1">Min Annual Return: {minReturn}%</label>
              <input type="range" min={0} max={25} value={minReturn} onChange={(e)=>setMinReturn(Number(e.target.value))} className="w-full accent-green-600" />
              <div className="flex justify-between text-xs text-slate-400"><span>0%</span><span>25%</span></div>
            </div>
            <div>
              <label className="block text-xs font-semibold text-slate-500 uppercase tracking-wider mb-1">Steadiness</label>
              <select value={steadinessFilter} onChange={(e)=>setSteadinessFilter(e.target.value)} className="w-full rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-900 px-3 py-2 text-sm">
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
          <div className="card p-12 text-center">
            <div className="w-16 h-16 bg-indigo-50 dark:bg-indigo-950/40 rounded-xl flex items-center justify-center mx-auto mb-4">
              <svg className="w-8 h-8 text-indigo-500" fill="none" stroke="currentColor" viewBox="0 0/24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" /></svg>
            </div>
            <h3 className="text-lg font-semibold text-slate-800 dark:text-slate-100 mb-2">Ready to find your best funds?</h3>
            <p className="text-slate-500">Choose amount, horizon, risk and category above, then click <span className="font-semibold text-indigo-600">Find Funds</span>.</p>
            <p className="text-xs text-slate-400 mt-2">We’ll load only funds that match — faster, focused, holistic.</p>
          </div>
        )}

        {/* Stats Bar — only after search to keep landing lean */}
        {hasSearched && (
        <>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <div className="card p-4">
            <p className="text-xs font-semibold text-slate-500 uppercase tracking-wide mb-1">Funds Shown</p>
            <p className="text-2xl font-bold text-slate-900 dark:text-white tnum">{sortedFunds.length}<span className="text-sm font-normal text-slate-400">/{funds.length}</span></p>
          </div>
          <div className="card p-4">
            <p className="text-xs font-semibold text-slate-500 uppercase tracking-wide mb-1">Mode</p>
            <p className="text-2xl font-bold text-slate-900 dark:text-white capitalize">{investmentMode}</p>
          </div>
          <div className="card p-4">
            <p className="text-xs font-semibold text-slate-500 uppercase tracking-wide mb-1">Risk Level</p>
            <p className="text-2xl font-bold text-slate-900 dark:text-white capitalize">{riskAppetite}</p>
          </div>
          <div className="card p-4">
            <p className="text-xs font-semibold text-slate-500 uppercase tracking-wide mb-1">Selected</p>
            <p className="text-2xl font-bold text-slate-900 dark:text-white tnum">{selectedFunds.length}</p>
          </div>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
          {/* Fund Cards */}
          <div className="lg:col-span-3">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-xl font-bold text-slate-800 dark:text-slate-100">Recommended Funds</h2>
              <span className="text-sm text-slate-500">Click to select for comparison • Sorted by {sortBy}</span>
            </div>

            {loading ? (
              <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-3 gap-4">
                {[1, 2, 3, 4, 5, 6].map((i) => (
                  <div key={i} className="card p-6 animate-pulse">
                    <div className="h-4 bg-slate-200 rounded w-3/4 mb-3"></div>
                    <div className="h-3 bg-slate-200 rounded w-1/2 mb-2"></div>
                    <div className="h-8 bg-slate-200 rounded w-1/3"></div>
                  </div>
                ))}
              </div>
            ) : sortedFunds.length === 0 ? (
              <div className="card p-12 text-center">
                <div className="w-16 h-16 bg-slate-100 dark:bg-slate-800 rounded-xl flex items-center justify-center mx-auto mb-4">
                  <svg className="w-8 h-8 text-slate-400" fill="none" stroke="currentColor" viewBox="0 0/24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9.172 16.172a4 4 0 015.656 0M9 10h.01M15 10h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                  </svg>
                </div>
                <h3 className="text-lg font-semibold text-slate-600 mb-2">No Funds Match Filters</h3>
                <p className="text-slate-500">Try lowering sliders or changing category.</p>
              </div>
            ) : (
              <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-3 gap-4">
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
            <div className="card p-6">
              <h2 className="text-xl font-bold text-slate-800 dark:text-slate-100 mb-4">Portfolio Analytics</h2>
              <RollingReturnsChart funds={sortedFunds} selectedFunds={selectedFunds} />
            </div>

            <div className="card p-6">
              <h2 className="text-xl font-bold text-slate-800 dark:text-slate-100 mb-4">Fund Comparison</h2>
              <ComparisonTable funds={sortedFunds} selectedFunds={selectedFunds} />
            </div>
          </div>
        </div>

        {/* Historic NAV Chart + Holistic for first selected fund */}
        {selectedFunds.length >= 1 && (
          <>
            <section className="card p-6">
              <h2 className="text-xl font-bold text-slate-800 dark:text-slate-100 mb-4">Historic NAV — Detailed History</h2>
              {(() => {
                const f = sortedFunds.find(x => x.scheme_id === selectedFunds[0]) || funds.find(x => x.scheme_id === selectedFunds[0]);
                return f ? <NavHistoryChart schemeId={f.scheme_id} schemeName={f.scheme_name} /> : null;
              })()}
              <p className="text-xs text-slate-400 mt-2">Daily NAV from mfapi.in / AMFI • Use tabs 1Y/3Y/5Y • Data powers rolling returns, Sharpe, Sortino in OCS</p>
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
      <footer className="border-t border-slate-200 dark:border-slate-800 mt-12">
        <div className="max-w-[1600px] mx-auto px-6 py-6 flex items-center justify-between text-sm text-slate-500">
          <p>© 2024 India Mutual Fund Finder</p>
          <p>AI-Powered Analytics Engine</p>
        </div>
        <p className="max-w-[1600px] mx-auto px-6 pb-6 text-xs text-slate-400">
          Information only, not investment advice. Returns are computed from official AMFI NAVs of funds that exist today, so they exclude funds that were closed or merged (survivorship bias) and reflect past market conditions; they are not a forecast. Risk levels are our estimate from past volatility, not the SEBI Riskometer published by each fund house. Expense ratios come from the AMFI disclosure where a match was found. Read the scheme documents and consider a SEBI-registered adviser before investing.
        </p>
      </footer>
    </div>
  );
}
