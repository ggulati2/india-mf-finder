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
    <div className="card flex flex-col h-[640px] relative overflow-hidden">
      <div className="p-4 border-b border-slate-200 dark:border-slate-800 flex items-center gap-2">
        <div className="w-8 h-8 bg-indigo-600 rounded-lg flex items-center justify-center text-white">✦</div>
        <div>
          <h3 className="font-bold text-slate-900 dark:text-slate-100">Ask Me</h3>
          <p className="text-xs text-slate-500">Ask about SIP vs Lump Sum, categories, risk, OCS — grounded in our fund universe</p>
        </div>
        <span className="ml-auto text-xs bg-emerald-50 text-emerald-700 dark:bg-emerald-950/40 dark:text-emerald-400 px-2 py-1 rounded-md border border-emerald-200 dark:border-emerald-900 font-medium">Direct Growth only</span>
      </div>

      {/* Coming Soon overlay */}
      <div className="absolute inset-0 top-[65px] z-10 flex items-center justify-center bg-white/90 dark:bg-slate-900/90 backdrop-blur-sm">
        <div className="text-center px-6">
          <div className="w-14 h-14 bg-indigo-600 rounded-xl flex items-center justify-center text-white text-2xl mx-auto mb-4">✦</div>
          <h4 className="text-lg font-bold text-slate-900 dark:text-slate-100 mb-1">Coming Soon</h4>
          <p className="text-sm text-slate-500 max-w-sm">Ask Me is still in development. Soon you'll be able to chat about SIP vs Lump Sum, risk, and fund picks in plain language.</p>
        </div>
      </div>

      <div className="flex-1 overflow-y-auto p-4 space-y-4 pointer-events-none select-none opacity-40">
        {msgs.map((m, i) => (
          <div key={i} className={`flex ${m.role === "user" ? "justify-end" : "justify-start"}`}>
            <div className={`max-w-[85%] rounded-xl px-4 py-3 text-sm whitespace-pre-wrap ${m.role === "user" ? "bg-indigo-600 text-white" : "bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700"}`}>
              {m.content}
            </div>
          </div>
        ))}
        <div ref={endRef} />
      </div>
      <div className="p-3 border-t border-slate-200 dark:border-slate-800 flex gap-2">
        <input disabled value={input} onChange={(e)=>setInput(e.target.value)} onKeyDown={(e)=> e.key==="Enter" && send()} placeholder="Coming soon…" className="flex-1 rounded-lg border border-slate-300 dark:border-slate-700 bg-slate-100 dark:bg-slate-800 px-4 py-3 text-sm cursor-not-allowed" />
        <button disabled className="btn-primary px-5 py-3 text-sm opacity-50 cursor-not-allowed">Send</button>
      </div>
    </div>
  );
}
