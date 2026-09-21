"use client";
import { useEffect, useState } from "react";
import { PieChart, Pie, Cell, ResponsiveContainer, Tooltip } from "recharts";

const COLORS = ["#4f46e5","#06b6d4","#10b981","#f59e0b","#ef4444","#8b5cf6","#ec4899","#14b8a6"];

function riskText(sharpe:number){ if(sharpe>=1) return "Low risk"; if(sharpe>=0.5) return "Medium risk"; return "High risk"; }

export function HolisticPanel({ schemeId }: { schemeId: number }) {
  const [data, setData] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  useEffect(() => {
    setLoading(true);
    fetch(`/api/analytics/holistic?scheme_id=${schemeId}&years=5`)
      .then(r => r.json()).then(setData).finally(()=>setLoading(false));
  }, [schemeId]);
  if (loading) return <div className="glass-card p-6 animate-pulse h-64" />;
  if (!data) return null;
  const sharpe = data.analytics?.["5"]?.sharpe ?? data.analytics?.["3"]?.sharpe ?? 0;
  return (
    <div className="space-y-4">
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        <div className="glass-card p-3 text-center" title="Worst fall from a peak — lower is better"><p className="text-xs text-gray-500">Worst fall</p><p className="text-lg font-bold text-red-600">{data.risk.max_drawdown}%</p><p className="text-xs text-gray-400">max drop</p></div>
        <div className="glass-card p-3 text-center" title="Latest 3-year yearly return — shows consistency over time"><p className="text-xs text-gray-500">Last 3Y return</p><p className="text-lg font-bold text-indigo-600">{data.risk.rolling_3y?.slice(-1)[0]?.rolling_cagr ?? "-"}%</p><p className="text-xs text-gray-400">rolling 3Y</p></div>
        <div className="glass-card p-3 text-center" title="What a monthly SIP of ₹10k would have grown to yearly"><p className="text-xs text-gray-500">SIP growth</p><p className="text-lg font-bold text-green-600">{data.risk.sip_xirr_5y}%<span className="text-xs font-normal">/yr</span></p><p className="text-xs text-gray-400">10k/mo 5Y</p></div>
        <div className="glass-card p-3 text-center" title="Overall steadiness vs market (from Sharpe)"><p className="text-xs text-gray-500">Steadiness</p><p className="text-lg font-bold text-amber-600">{riskText(sharpe)}</p><p className="text-xs text-gray-400">risk level</p></div>
      </div>
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div className="glass-card p-4">
          <h4 className="font-semibold mb-2" title="Where your money is invested — top stocks in this fund">Top holdings <span className="text-gray-400 font-normal text-xs">(what it owns)</span></h4>
          <div className="space-y-1 text-sm">
            {data.holdings.slice(0,10).map((h:any)=>(
              <div key={h.ticker} className="flex justify-between"><span className="font-mono">{h.ticker}</span><span className="text-gray-500">{h.sector}</span><span className="font-semibold">{h.weight}%</span></div>
            ))}
          </div>
        </div>
        <div className="glass-card p-4">
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
      <p className="text-xs text-gray-400 text-center">Holdings synthetic per category • Risk from 10y NAV • Benchmark Nifty via Yahoo • Tap (?) for plain-English help</p>
    </div>
  );
}
