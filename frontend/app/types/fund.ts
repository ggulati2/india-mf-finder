export interface Fund {
  scheme_id: number;
  amfi_code: number;
  isin: string;
  scheme_name: string;
  amc_name: string;
  category: string;
  plan_type: string;
  option_type: string;
  launch_date: string;
  expense_ratio: number | null;
  sebi_category?: string;
  risk: { level: string; score: number; basis: string; official?: boolean; source?: string; as_of?: string | null; measured?: string };
  confidence?: { level: "Complete" | "Partial" | "Low"; checks: Record<string, boolean>; missing: string[]; not_available: string[] };
  data_as_of?: string | null;
  history_start?: string | null;
  ocs_score: number;
  analytics: {
    cagr: number;
    sharpe_ratio: number;
    sortino_ratio: number;
    beta: number;
    upside_capture: number;
    downside_capture: number;
    volatility?: number | null;
    max_drawdown?: number | null;
    history_years?: number | null;
    time_horizon?: number;
  };
}

export interface SchemeAnalytics {
  scheme_id: number;
  computed_date: string;
  time_horizon_years: number;
  cagr: number;
  rolling_returns_mean: number;
  rolling_returns_std: number;
  sharpe_ratio: number;
  sortino_ratio: number;
  jensens_alpha: number;
  beta: number;
  upside_capture: number;
  downside_capture: number;
  expense_ratio: number;
}
