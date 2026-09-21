"use client";

import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from "recharts";
import { Fund } from "@/types/fund";

interface RollingReturnsChartProps {
  funds: Fund[];
  selectedFunds: number[];
}

export function RollingReturnsChart({ funds, selectedFunds }: RollingReturnsChartProps) {
  const selectedFundsData = funds.filter((f) =>
    selectedFunds.includes(f.scheme_id)
  );

  const data = selectedFundsData.map((fund) => ({
    name: fund.scheme_name.split(" ").slice(0, 2).join(" "),
    cagr: fund.analytics.cagr,
    sharpe: fund.analytics.sharpe_ratio,
    sortino: fund.analytics.sortino_ratio,
  }));

  return (
    <div className="h-64">
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={data}>
          <CartesianGrid strokeDasharray="3 3" />
          <XAxis dataKey="name" />
          <YAxis />
          <Tooltip />
          <Bar dataKey="cagr" fill="#3b82f6" name="CAGR %" />
          <Bar dataKey="sharpe" fill="#10b981" name="Sharpe" />
          <Bar dataKey="sortino" fill="#f59e0b" name="Sortino" />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
