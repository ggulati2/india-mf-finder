"use client";
import { useEffect, useState } from "react";
import { PieChart, Pie, Cell, ResponsiveContainer, Tooltip } from "recharts";

const COLORS = ["#4f46e5","#06b6d4","#10b981","#f59e0b","#ef4444","#8b5cf6","#ec4899","#14b8a6"];

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
  return (
    <div className="space-y-4">
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        <div className="glass-card p-3 text-center"><p className="text-xs text-gray-500">Max Drawdown</p><p className="text-lg font-bold text-red-600">{data.risk.max_drawdown}%</p></div>
        <div className="glass-card p-3 text-center"><p className="text-xs text-gray-500">3Y Rolling (latest)</p><p className="text-lg font-bold text-indigo-600">{data.risk.rolling_3y?.slice(-1)[0]?.rolling_cagr ?? "-"}%</p></div>
        <div className="glass-card p-3 text-center"><p className="text-xs text-gray-500">SIP XIRR 5Y (10k/mo)</p><p className="text-lg font-bold text-green-600">{data.risk.sip_xirr_5y}%</p></div>
        <div className="glass-card p-3 text-center"><p className="text-xs text-gray-500">vs Nifty 5Y</p><p className="text-lg font-bold text-amber-600">{data.risk.benchmark_nifty_cagr ?? "—"}%</p></div>
      </div>
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div className="glass-card p-4">
          <h4 className="font-semibold mb-2">Top Holdings (synthetic)</h4>
          <div className="space-y-1 text-sm">
            {data.holdings.slice(0,10).map((h:any)=>(
              <div key={h.ticker} className="flex justify-between"><span className="font-mono">{h.ticker}</span><span className="text-gray-500">{h.sector}</span><span className="font-semibold">{h.weight}%</span></div>
            ))}
          </div>
        </div>
        <div className="glass-card p-4">
          <h4 className="font-semibold mb-2">Sector Allocation</h4>
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
      <p className="text-xs text-gray-400 text-center">Holdings synthetic deterministic per category • Risk via NAV history • Benchmark via Yahoo Finance • {data.data_source.split("•")[0]}</p>
    </div>
  );
}
