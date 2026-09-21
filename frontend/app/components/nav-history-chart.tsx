"use client";
import { useEffect, useState } from "react";
import { LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer } from "recharts";

export function NavHistoryChart({ schemeId, schemeName }: { schemeId: number; schemeName: string }) {
  const [data, setData] = useState<any[]>([]);
  const [years, setYears] = useState(1);
  const [loading, setLoading] = useState(true);
  useEffect(() => {
    setLoading(true);
    fetch(`/api/analytics/history?scheme_id=${schemeId}&years=${years}`)
      .then(r => r.json())
      .then(d => setData(d.points || []))
      .finally(() => setLoading(false));
  }, [schemeId, years]);
  if (loading) return <div className="h-48 animate-pulse bg-gray-100 rounded-xl" />;
  if (!data.length) return <div className="text-sm text-gray-500">No historic NAV available.</div>;
  return (
    <div>
      <div className="flex items-center justify-between mb-2">
        <h4 className="text-sm font-semibold">{schemeName} — NAV ({years}Y)</h4>
        <div className="flex gap-1">
          {[1,3,5].map(y=> <button key={y} onClick={()=>setYears(y)} className={`text-xs px-2 py-1 rounded-full ${years===y ? "bg-indigo-600 text-white" : "bg-gray-100"}`}>{y}Y</button>)}
        </div>
      </div>
      <div className="h-48">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={data}>
            <XAxis dataKey="date" tick={{fontSize:10}} hide />
            <YAxis tick={{fontSize:10}} domain={['auto','auto']} />
            <Tooltip />
            <Line type="monotone" dataKey="nav" stroke="#4f46e5" dot={false} strokeWidth={2} />
          </LineChart>
        </ResponsiveContainer>
      </div>
      <p className="text-xs text-gray-400 mt-1">{data.length} daily points • Source: mfapi.in / AMFI</p>
    </div>
  );
}
