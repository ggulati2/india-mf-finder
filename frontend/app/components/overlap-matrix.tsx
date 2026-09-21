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

  if (loading) {
    return <div className="animate-pulse h-64 bg-gray-200 rounded" />;
  }

  return (
    <div className="bg-card rounded-lg p-6 border">
      <h2 className="text-xl font-semibold mb-4">Portfolio Overlap Analysis</h2>
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b">
              <th className="p-2 text-left">Fund</th>
              {fundIds.map((id) => (
                <th key={id} className="p-2 text-right">
                  #{id}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {fundIds.map((rowId) => (
              <tr key={rowId} className="border-b last:border-0">
                <td className="p-2 font-medium">#{rowId}</td>
                {fundIds.map((colId) => (
                  <td key={colId} className="p-2 text-right">
                    {matrix[rowId]?.[colId] !== undefined
                      ? (matrix[rowId][colId] * 100).toFixed(1) + "%"
                      : "-"}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <p className="text-xs text-gray-500 mt-2">
        Jaccard similarity based on portfolio holdings overlap
      </p>
    </div>
  );
}
