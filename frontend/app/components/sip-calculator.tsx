"use client";
import { useState } from "react";

export function SipCalculator({ schemeId }: { schemeId?: number }) {
  const [amount, setAmount] = useState(10000);
  const [years, setYears] = useState(5);
  const [result, setResult] = useState<any>(null);
  const calc = async () => {
    if (!schemeId) return;
    const r = await fetch(`/api/analytics/holistic?scheme_id=${schemeId}&years=${years}`);
    const d = await r.json();
    setResult(d.risk);
  };
  return (
    <div className="glass-card p-4">
      <h4 className="font-semibold mb-1">Try a monthly SIP <span className="text-gray-400 font-normal text-xs" title="We simulate putting money monthly on the first trading day using real past NAV">ⓘ</span></h4>
      <p className="text-xs text-gray-500 mb-3">See what past monthly investing would have grown to yearly</p>
      <div className="flex gap-2 mb-3">
        <label className="text-xs text-gray-500 flex flex-col">Monthly ₹<input type="number" value={amount} onChange={e=>setAmount(Number(e.target.value))} className="w-24 rounded-lg border px-2 py-1 text-sm" /></label>
        <label className="text-xs text-gray-500 flex flex-col">For <select value={years} onChange={e=>setYears(Number(e.target.value))} className="rounded-lg border px-2 py-1 text-sm"><option value={3}>3 years</option><option value={5}>5 years</option><option value={10}>10 years</option></select></label>
        <button onClick={calc} className="self-end rounded-lg bg-indigo-600 text-white px-3 py-1.5 text-sm">Show growth</button>
      </div>
      {result && (
        <div className="text-sm space-y-1 bg-green-50 border border-green-100 rounded-xl p-3">
          <p>Past SIP growth: <span className="font-bold text-green-600">{result.sip_xirr_5y}% per year</span> <span className="text-gray-400 text-xs" title="Not a promise — just what history shows">ⓘ</span></p>
          <p className="text-xs text-gray-500">Monthly ₹{amount.toLocaleString("en-IN")} for {years} years would have grown at this yearly pace. Worst fall in that time: <span className="font-bold text-red-600">{result.max_drawdown}%</span></p>
        </div>
      )}
    </div>
  );
}
