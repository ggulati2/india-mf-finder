"use client";

import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend } from "recharts";
import { Fund } from "../types/fund";

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
      {data.length === 0 ? (
        <div className="flex items-center justify-center h-full text-gray-400 text-sm">
          Select funds to see analytics
        </div>
      ) : (
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={data} barGap={4}>
            <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
            <XAxis dataKey="name" tick={{ fontSize: 12, fill: '#9ca3af' }} axisLine={false} tickLine={false} />
            <YAxis tick={{ fontSize: 12, fill: '#9ca3af' }} axisLine={false} tickLine={false} />
            <Tooltip
              contentStyle={{
                borderRadius: '12px',
                border: '1px solid #e5e7eb',
                boxShadow: '0 4px 6px -1px rgba(0, 0, 0, 0.1)',
              }}
            />
            <Legend wrapperStyle={{ fontSize: '12px', paddingTop: '10px' }} />
            <Bar dataKey="cagr" fill="#3b82f6" name="CAGR %" radius={[4, 4, 0, 0]} />
            <Bar dataKey="sharpe" fill="#10b981" name="Sharpe" radius={[4, 4, 0, 0]} />
            <Bar dataKey="sortino" fill="#f59e0b" name="Sortino" radius={[4, 4, 0, 0]} />
          </BarChart>
        </ResponsiveContainer>
      )}
    </div>
  );
}
