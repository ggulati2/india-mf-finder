"use client";

import { useEffect, useState } from "react";

interface OverlapMatrixProps {
  fundIds: number[];
}

interface OverlapData {
  [key: string]: { [key: string]: number };
}

export function OverlapMatrix({ fundIds }: OverlapMatrixProps) {
  const [matrix, setMatrix] = useState<OverlapData>({});
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchOverlapMatrix();
  }, [fundIds]);

  const fetchOverlapMatrix = async () => {
    try {
      const ids = fundIds.join(",");
      const response = await fetch(`/api/overlap/matrix?scheme_ids=${ids}`);
      const data = await response.json();
      setMatrix(data);
    } catch (error) {
      console.error("Error fetching overlap matrix:", error);
    } finally {
      setLoading(false);
    }
  };

  const getOverlapColor = (value: number) => {
    if (value >= 0.7) return "bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400";
    if (value >= 0.4) return "bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-400";
    if (value > 0) return "bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400";
    return "bg-slate-100 text-slate-500 dark:bg-slate-800 dark:text-slate-400";
  };

  if (loading) {
    return (
      <div className="card p-6 animate-pulse">
        <div className="h-6 bg-slate-200 rounded w-48 mb-4"></div>
        <div className="grid gap-2" style={{ gridTemplateColumns: `repeat(${fundIds.length + 1}, 1fr)` }}>
          <div className="h-10 bg-slate-200 rounded"></div>
          {fundIds.map((id) => (
            <div key={id} className="h-10 bg-slate-200 rounded"></div>
          ))}
          {fundIds.map((id) => (
            <div key={`row-${id}`} className="h-10 bg-slate-200 rounded"></div>
          ))}
        </div>
      </div>
    );
  }

  return (
    <div className="card p-6">
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <div className="w-8 h-8 bg-violet-50 dark:bg-violet-950/40 rounded-lg flex items-center justify-center">
            <svg className="w-4 h-4 text-violet-600 dark:text-violet-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 5a1 1 0 011-1h14a1 1 0 011 1v2a1 1 0 01-1 1H5a1 1 0 01-1-1V5zM4 13a1 1 0 011-1h6a1 1 0 011 1v6a1 1 0 01-1 1H5a1 1 0 01-1-1v-6zM16 13a1 1 0 011-1h2a1 1 0 011 1v6a1 1 0 01-1 1h-2a1 1 0 01-1-1v-6z" />
            </svg>
          </div>
          <h2 className="text-xl font-bold text-slate-800 dark:text-slate-100">Portfolio Overlap Analysis</h2>
        </div>
        <span className="text-xs text-slate-500 bg-slate-100 dark:bg-slate-800 px-3 py-1 rounded-full">
          Jaccard Similarity
        </span>
      </div>

      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-slate-100 dark:border-slate-700">
              <th className="p-3 text-left text-xs font-semibold text-slate-500 uppercase">Fund</th>
              {fundIds.map((id) => (
                <th key={id} className="p-3 text-center">
                  <span className="text-xs font-bold text-slate-600 dark:text-slate-300 bg-slate-100 dark:bg-slate-800 px-2 py-1 rounded-lg">
                    #{id}
                  </span>
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {fundIds.map((rowId) => (
              <tr key={rowId} className="border-b border-slate-50 dark:border-slate-800">
                <td className="p-3 font-medium text-slate-700 dark:text-slate-300">
                  <span className="bg-slate-100 dark:bg-slate-800 px-2 py-1 rounded-lg text-xs font-semibold">
                    #{rowId}
                  </span>
                </td>
                {fundIds.map((colId) => {
                  const value = matrix[rowId]?.[colId];
                  return (
                    <td key={colId} className="p-3 text-center">
                      {value !== undefined ? (
                        <span className={`inline-block px-3 py-1 rounded-lg text-xs font-bold ${getOverlapColor(value)}`}>
                          {(value * 100).toFixed(1)}%
                        </span>
                      ) : (
                        <span className="text-slate-300 dark:text-slate-600">—</span>
                      )}
                    </td>
                  );
                })}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <p className="text-xs text-slate-400 mt-3 text-center">
        Higher values indicate greater portfolio overlap between funds
      </p>
    </div>
  );
}
