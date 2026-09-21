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
      <h4 className="font-semibold mb-3">SIP Calculator (based on historic NAV)</h4>
      <div className="flex gap-2 mb-3">
        <input type="number" value={amount} onChange={e=>setAmount(Number(e.target.value))} className="w-24 rounded-lg border px-2 py-1 text-sm" placeholder="Monthly" />
        <select value={years} onChange={e=>setYears(Number(e.target.value))} className="rounded-lg border px-2 py-1 text-sm">
          <option value={3}>3Y</option><option value={5}>5Y</option><option value={10}>10Y</option>
        </select>
        <button onClick={calc} className="rounded-lg bg-indigo-600 text-white px-3 py-1 text-sm">Calculate</button>
      </div>
      {result && (
        <div className="text-sm space-y-1">
          <p>SIP XIRR: <span className="font-bold text-green-600">{result.sip_xirr_5y}%</span> (10k/mo over {years}Y)</p>
          <p>Max Drawdown: <span className="font-bold text-red-600">{result.max_drawdown}%</span></p>
          <p>vs Nifty: <span className="font-bold">{result.benchmark_nifty_cagr ?? "—"}%</span></p>
        </div>
      )}
      <p className="text-xs text-gray-400 mt-2">Uses daily NAV history to simulate monthly SIP entry on first trading day.</p>
    </div>
  );
}
