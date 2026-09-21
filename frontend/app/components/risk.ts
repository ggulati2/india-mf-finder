export interface RiskInfo { level: string; score: number; basis: string }

const STYLES: Record<string, string> = {
  "Low": "text-green-600",
  "Low to Moderate": "text-green-600",
  "Moderate": "text-amber-600",
  "Moderately High": "text-orange-600",
  "High": "text-red-600",
  "Very High": "text-red-700",
};

export function riskColor(level?: string) { return (level && STYLES[level]) || "text-gray-500"; }
export function riskText(risk?: RiskInfo | null) { return risk?.level ?? "Unknown"; }
export function fmtTer(v: number | null | undefined) { return v == null ? "n/a" : `${v.toFixed(2)}%`; }
export const RISK_HELP = "Estimated from this fund's past volatility and worst fall, and never lower than its SEBI category implies. Not the official SEBI Riskometer.";
