export interface ComparisonMetrics {
  cagr_range: [number, number];
  sharpe_range: [number, number];
  expense_ratio_range: [number, number];
  category_distribution: Record<string, number>;
}

export interface SchemeComparison {
  schemes: Array<{
    scheme: any;
    analytics: Record<number, any>;
  }>;
  overlap_matrix: Record<number, Record<number, number>>;
  comparison_metrics: ComparisonMetrics;
}

export interface OverlapData {
  matrix: Record<number, Record<number, number>>;
  top_overlaps: Array<{
    scheme_id: number;
    scheme_name: string;
    overlap_score: number;
  }>;
}
