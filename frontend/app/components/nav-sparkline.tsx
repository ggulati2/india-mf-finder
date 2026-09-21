"use client";
import { useEffect, useRef, useState } from "react";
import { AreaChart, Area, XAxis, YAxis, Tooltip, ResponsiveContainer } from "recharts";

type Pt = { date: string; nav: number; value: number };
const cache = new Map<string, Pt[]>();

/** Growth of ₹100 over the fund's horizon. Loads only when scrolled into view. */
export function NavSparkline({ schemeId, years }: { schemeId: number; years: number }) {
  const ref = useRef<HTMLDivElement>(null);
  const [visible, setVisible] = useState(false);
  const [pts, setPts] = useState<Pt[] | null>(null);
  const [failed, setFailed] = useState(false);
  const key = `${schemeId}:${years}`;

  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    const io = new IntersectionObserver((e) => { if (e[0].isIntersecting) { setVisible(true); io.disconnect(); } }, { rootMargin: "200px" });
    io.observe(el);
    return () => io.disconnect();
  }, []);

  useEffect(() => {
    if (!visible) return;
    const hit = cache.get(key);
    if (hit) { setPts(hit); return; }
    fetch(`/api/analytics/history?scheme_id=${schemeId}&years=${years}&max_points=160`)
      .then((r) => r.json())
      .then((d) => { const p: Pt[] = d.points ?? []; if (p.length) { cache.set(key, p); setPts(p); } else setFailed(true); })
      .catch(() => setFailed(true));
  }, [visible, key, schemeId, years]);

  const up = pts && pts.length > 1 ? pts[pts.length - 1].value >= pts[0].value : true;
  const color = up ? "#16a34a" : "#dc2626";
  return (
    <div ref={ref} className="mt-3" onClick={(e) => e.stopPropagation()}>
      <div className="flex justify-between text-[10px] text-gray-400 mb-0.5">
        <span>Growth of ₹100 · past {years}Y</span>
        {pts && pts.length > 1 && <span className={up ? "text-green-600" : "text-red-600"}>₹100 → ₹{pts[pts.length - 1].value.toFixed(0)}</span>}
      </div>
      <div className="h-16">
        {pts ? (
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart data={pts} margin={{ top: 2, right: 0, left: 0, bottom: 0 }}>
              <XAxis dataKey="date" hide />
              <YAxis domain={["dataMin", "dataMax"]} hide />
              <Tooltip
                formatter={(v: number) => [`₹${v.toFixed(1)}`, "Value of ₹100"]}
                labelFormatter={(l) => String(l)}
                contentStyle={{ fontSize: 11, padding: "2px 6px" }}
              />
              <Area type="monotone" dataKey="value" stroke={color} fill={color} fillOpacity={0.12} strokeWidth={1.5} dot={false} isAnimationActive={false} />
            </AreaChart>
          </ResponsiveContainer>
        ) : failed ? (
          <div className="h-full flex items-center justify-center text-[10px] text-gray-400">History unavailable</div>
        ) : (
          <div className="h-full animate-pulse bg-gray-100 dark:bg-gray-800 rounded" />
        )}
      </div>
    </div>
  );
}
