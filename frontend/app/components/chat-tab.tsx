"use client";
import { useState, useRef, useEffect } from "react";

interface Msg { role: "user" | "assistant"; content: string }

export function ChatTab() {
  const [msgs, setMsgs] = useState<Msg[]>([
    { role: "assistant", content: "Hi! I'm your mutual fund copilot. Tell me your goal, amount, horizon, and risk — e.g. 'I have 5 lakh for 5 years via SIP, moderate risk, prefer flexi cap' — and I'll rank the best Direct Growth funds with OCS reasoning." },
  ]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const endRef = useRef<HTMLDivElement>(null);
  useEffect(() => { endRef.current?.scrollIntoView({ behavior: "smooth" }); }, [msgs]);

  const send = async () => {
    if (!input.trim() || loading) return;
    const userMsg: Msg = { role: "user", content: input };
    setMsgs((m) => [...m, userMsg]);
    setInput("");
    setLoading(true);
    try {
      const r = await fetch("/api/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message: userMsg.content, history: msgs }),
      });
      const data = await r.json();
      const reply = data.reply || "Sorry, I couldn't answer that.";
      let recText = "";
      if (data.recommendations?.length) {
        recText = "\n\n**Top picks for you:**\n" + data.recommendations.map((x: any, i:number)=> `${i+1}. ${x.scheme_name} (${x.category}, ${x.amc_name}) — OCS ${x.ocs_score.toFixed(1)}, CAGR ${x.analytics.cagr.toFixed(1)}%`).join("\n");
      }
      setMsgs((m) => [...m, { role: "assistant", content: reply + recText }]);
    } catch {
      setMsgs((m) => [...m, { role: "assistant", content: "Network error. Try again." }]);
    } finally { setLoading(false); }
  };

  return (
    <div className="glass-card flex flex-col h-[640px]">
      <div className="p-4 border-b border-gray-100 dark:border-gray-800 flex items-center gap-2">
        <div className="w-8 h-8 bg-gradient-to-br from-blue-600 to-indigo-600 rounded-lg flex items-center justify-center text-white">✦</div>
        <div>
          <h3 className="font-bold text-gray-800 dark:text-gray-100">GenAI Fund Advisor</h3>
          <p className="text-xs text-gray-500">Ask about SIP vs Lump Sum, categories, risk, OCS — grounded in our 16-fund universe</p>
        </div>
        <span className="ml-auto text-xs bg-green-50 text-green-700 px-2 py-1 rounded-full border border-green-200">Direct Growth only</span>
      </div>
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {msgs.map((m, i) => (
          <div key={i} className={`flex ${m.role === "user" ? "justify-end" : "justify-start"}`}>
            <div className={`max-w-[85%] rounded-2xl px-4 py-3 text-sm whitespace-pre-wrap ${m.role === "user" ? "bg-indigo-600 text-white" : "bg-gray-50 dark:bg-gray-800 border border-gray-100 dark:border-gray-700"}`}>
              {m.content}
            </div>
          </div>
        ))}
        <div ref={endRef} />
      </div>
      <div className="p-3 border-t border-gray-100 dark:border-gray-800 flex gap-2">
        <input value={input} onChange={(e)=>setInput(e.target.value)} onKeyDown={(e)=> e.key==="Enter" && send()} placeholder="e.g. 10k SIP for 7 years, high risk, small cap" className="flex-1 rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 px-4 py-3 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-100" />
        <button onClick={send} disabled={loading} className="rounded-xl bg-indigo-600 text-white px-5 py-3 text-sm font-semibold disabled:opacity-50">{loading ? "…" : "Send"}</button>
      </div>
      <div className="px-4 pb-3 flex gap-2 flex-wrap">
        {["1 lakh lump sum 3y low risk large cap", "50k SIP 10y high risk small cap", "Explain OCS scoring", "Best flexi cap for conservative investor?"].map(q=>(
          <button key={q} onClick={()=>setInput(q)} className="text-xs bg-gray-100 dark:bg-gray-800 px-2 py-1 rounded-full hover:bg-indigo-50">{q}</button>
        ))}
      </div>
    </div>
  );
}
