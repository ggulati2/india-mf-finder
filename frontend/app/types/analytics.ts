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

export interface NAVDataPoint {
  time: string;
  nav: number;
  net_assets_cr: number;
}

export interface FundMetrics {
  cagr: number;
  sharpe: number;
  sortino: number;
  beta: number;
  volatility: number;
  alpha: number;
}
