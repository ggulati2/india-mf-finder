"use client";
import { useEffect, useState } from "react";
import { PieChart, Pie, Cell, ResponsiveContainer, Tooltip } from "recharts";
import { riskColor, riskHelp, fmtTer } from "./risk";

const COLORS = ["#4f46e5","#06b6d4","#10b981","#f59e0b","#ef4444","#8b5cf6","#ec4899","#14b8a6"];


export function HolisticPanel({ schemeId }: { schemeId: number }) {
  const [data, setData] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  useEffect(() => {
    setLoading(true);
    fetch(`/api/analytics/holistic?scheme_id=${schemeId}&years=5`)
      .then(r => r.json()).then(setData).finally(()=>setLoading(false));
  }, [schemeId]);
  if (loading) return <div className="card p-6 animate-pulse h-64" />;
  if (!data) return null;
  const hasHoldings = (data.holdings?.length ?? 0) > 0;
  const dq = data.data_quality;
  return (
    <div className="space-y-4">
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        <div className="card p-3 text-center" title="Worst fall from a peak — lower is better"><p className="text-xs text-slate-500">Worst fall</p><p className="text-lg font-bold text-red-600">{data.risk.max_drawdown}%</p><p className="text-xs text-slate-400">max drop</p></div>
        <div className="card p-3 text-center" title="Latest 3-year yearly return — shows consistency over time"><p className="text-xs text-slate-500">Last 3Y return</p><p className="text-lg font-bold text-indigo-600">{data.risk.rolling_3y?.slice(-1)[0]?.rolling_cagr ?? "-"}%</p><p className="text-xs text-slate-400">rolling 3Y</p></div>
        <div className="card p-3 text-center" title="Hypothetical back-test of a ₹10k monthly SIP over the past 5 years. Not a forecast."><p className="text-xs text-slate-500">SIP back-test</p><p className="text-lg font-bold text-green-600">{data.risk.sip_xirr_5y}%<span className="text-xs font-normal">/yr</span></p><p className="text-xs text-slate-400">10k/mo 5Y</p></div>
        <div className="card p-3 text-center" title={riskHelp(data.risk)}><p className="text-xs text-slate-500">Risk {data.risk?.official ? "(SEBI official)" : "(estimated)"}</p><p className={`text-lg font-bold ${riskColor(data.risk?.level)}`}>{data.risk?.level ?? "Unknown"}</p><p className="text-xs text-slate-400">{data.risk?.official ? `as of ${data.risk?.as_of ?? ""}` : "from past volatility"}</p></div>
      </div>
      {hasHoldings ? (
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div className="card p-4">
          <h4 className="font-semibold mb-2" title="Where your money is invested — top stocks in this fund">Top holdings <span className="text-slate-400 font-normal text-xs">(top 10 = {data.top10_weight}% · {data.holdings_source})</span></h4>
          <div className="space-y-1 text-sm">
            {data.holdings.slice(0,10).map((h:any)=>(
              <div key={h.isin ?? h.name} className="flex justify-between"><span className="truncate mr-2" title={h.isin}>{h.name}</span><span className="text-slate-500 truncate mr-2">{h.sector}</span><span className="font-semibold">{h.weight}%</span></div>
            ))}
          </div>
        </div>
        <div className="card p-4">
          <h4 className="font-semibold mb-2" title="Where the fund bets — sector mix">Where it invests</h4>
          <div className="h-40">
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie data={data.sector_allocation} dataKey="weight" nameKey="sector" cx="50%" cy="50%" outerRadius={60}>
                  {data.sector_allocation.map((_:any,i:number)=>(<Cell key={i} fill={COLORS[i%COLORS.length]} />))}
                </Pie>
                <Tooltip />
              </PieChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>
      ) : (
        <div className="card p-4 text-sm text-slate-500">Portfolio holdings: not shown. {data.holdings_note}</div>
      )}
      <div className="text-xs text-slate-400 text-center space-y-0.5">
        <p>Expense ratio: {fmtTer(data.scheme?.expense_ratio)}{data.scheme?.expense_ratio == null ? " (no verified figure yet)" : ""} · NAV data as of {dq?.nav_as_of ?? "n/a"} · Benchmark: {dq?.benchmark}</p>
        <p>{dq?.nav_source}. Past performance does not guarantee future returns.</p>
      </div>
    </div>
  );
}
