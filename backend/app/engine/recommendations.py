from sqlalchemy.orm import Session
from app.db.models import MutualFundScheme, SchemeAnalytics
from app.engine.scoring import calculate_ocs_score, compute_scheme_analytics
import numpy as np
import pandas as pd
import logging
from app.engine.risk_level import risk_info
from app.engine.confidence import data_confidence

logger = logging.getLogger(__name__)

def _calculate_percentile_score(value, sorted_values) -> float:
    if not sorted_values or value is None:
        return 50.0
    index = np.searchsorted(sorted_values, value)
    return float(index / len(sorted_values) * 100)


def build_category_stats(schemes: list, analytics_by_scheme: dict) -> dict:
    """Precompute each category's cagr/sharpe/std distributions ONCE, instead of re-querying and
    re-aggregating the whole category for every single scheme (that was the O(n * category_size)
    query blow-up that made recommendations take 15s+)."""
    by_category = {}
    for scheme in schemes:
        a = analytics_by_scheme.get(scheme.scheme_id)
        if not a:
            continue
        by_category.setdefault(scheme.category, {'cagr': [], 'sharpe': [], 'std': [], 'sortino': []})
        if a.cagr is not None: by_category[scheme.category]['cagr'].append(float(a.cagr))
        if a.sharpe_ratio is not None: by_category[scheme.category]['sharpe'].append(float(a.sharpe_ratio))
        if a.rolling_returns_std is not None: by_category[scheme.category]['std'].append(float(a.rolling_returns_std))
        if a.sortino_ratio is not None: by_category[scheme.category]['sortino'].append(float(a.sortino_ratio))
    for cat, v in by_category.items():
        for k in v:
            v[k].sort()
    return by_category


def get_category_scores(category: str, analytics, category_stats: dict) -> dict:
    """Percentile-rank a scheme's analytics against its precomputed category distribution."""
    stats = category_stats.get(category)
    default = {'rolling_returns': 50.0, 'risk_adjusted': 50.0, 'consistency': 50.0,
              'fundamentals': 50.0, 'trend': 50.0}
    if not stats or not analytics:
        return default
    try:
        category_avg_std = np.mean(stats['std']) if stats['std'] else 0
        rolling_returns_score = _calculate_percentile_score(analytics.cagr, stats['cagr'])
        risk_adjusted_score = _calculate_percentile_score(analytics.sharpe_ratio, stats['sharpe'])
        consistency_score = 100 - _calculate_percentile_score(category_avg_std, stats['std'])
        return {
            'rolling_returns': rolling_returns_score,
            'risk_adjusted': risk_adjusted_score,
            'consistency': consistency_score,
            'fundamentals': 50.0,  # Placeholder
            'trend': 50.0,  # Placeholder
        }
    except Exception as e:
        logger.error(f"Error getting category scores: {e}")
        return default

def get_top_funds(
    investment_amount: float,
    investment_mode: str,
    horizon_years: int,
    risk_appetite: str,
    category: str = None,
    db: Session = None,
    complete_only: bool = False
) -> list:
    """
    Get top fund recommendations based on investment parameters.
    """
    try:
        query = db.query(MutualFundScheme)
        
        if category:
            query = query.filter(MutualFundScheme.category == category)
        else:
            # "Other" holds closed-ended / unclassifiable schemes; never recommend them unprompted
            query = query.filter(MutualFundScheme.category != "Other")

        # Filter to direct plans only
        query = query.filter(MutualFundScheme.plan_type == "Direct")
        
        # Only verified, live Direct-Growth schemes; analytics rows exist only if NAV validation passed
        query = query.filter(MutualFundScheme.is_active == True)  # noqa: E712
        results = query.all()
        scheme_ids = [s.scheme_id for s in results]

        from app.db.models import SchemeHolding
        with_holdings = {r[0] for r in db.query(SchemeHolding.scheme_id).distinct()}
        # One query for every scheme's analytics at this horizon, instead of one query per scheme
        # (was N+1: ~1200 schemes -> ~1200 queries, plus another full category re-scan per scheme).
        analytics_by_scheme = {
            a.scheme_id: a for a in db.query(SchemeAnalytics).filter(
                SchemeAnalytics.scheme_id.in_(scheme_ids),
                SchemeAnalytics.time_horizon_years == horizon_years,
            )
        }
        category_stats = build_category_stats(results, analytics_by_scheme)
        fund_scores = []

        for scheme in results:
            # Get analytics if available — skip funds without real history for holistic decision
            analytics = analytics_by_scheme.get(scheme.scheme_id)
            # Require real historic analytics (non-zero CAGR/Sharpe) to ensure holistic data
            if not analytics or (float(analytics.cagr or 0) == 0 and float(analytics.sharpe_ratio or 0) == 0):
                continue
            
            risk = risk_info(scheme,
                             float(analytics.volatility) if analytics.volatility is not None else None,
                             float(analytics.max_drawdown) if analytics.max_drawdown is not None else None)
            # Appetite gate on the SAME level the user sees (official Riskometer when known):
            # low -> up to Moderate, medium -> up to Moderately High, high -> anything.
            max_risk = {'low': 3, 'medium': 4}.get(risk_appetite.lower(), 6)
            if risk['score'] > max_risk:
                continue

            confidence = data_confidence(scheme, analytics, horizon_years, scheme.scheme_id in with_holdings)
            if confidence['level'] == 'Low' or (complete_only and confidence['level'] != 'Complete'):
                continue

            # Get category scores for anti-bias normalization
            category_scores = get_category_scores(scheme.category, analytics, category_stats)
            
            # Prepare scheme data for OCS calculation
            scheme_data = {
                'scheme_id': scheme.scheme_id,
                'amc_name': scheme.amc_name,
                'category': scheme.category,
                'plan_type': scheme.plan_type,
                'option_type': scheme.option_type,
                'expense_ratio': float(scheme.expense_ratio) if scheme.expense_ratio else 0.0,
                'pe_ratio': None,
                'pb_ratio': None,
                'volatility': float(analytics.rolling_returns_std) if analytics and analytics.rolling_returns_std else 0.0,
                'launch_date': scheme.launch_date,
                'is_active': scheme.is_active
            }
            
            # Calculate OCS score
            ocs_score = calculate_ocs_score(
                scheme_data=scheme_data,
                category_scores=category_scores,
                investment_mode=investment_mode,
                risk_appetite=risk_appetite
            )
            
            fund_recommendation = {
                'scheme_id': scheme.scheme_id,
                'amfi_code': scheme.amfi_code,
                'isin': scheme.isin,
                'scheme_name': scheme.scheme_name,
                'amc_name': scheme.amc_name,
                'category': scheme.category,
                'plan_type': scheme.plan_type,
                'option_type': scheme.option_type,
                'launch_date': scheme.launch_date,
                'expense_ratio': float(scheme.ter_pct) if scheme.ter_pct is not None else None,
                'sebi_category': scheme.sebi_category,
                'risk': risk,
                'confidence': confidence,
                'data_as_of': scheme.latest_nav_date.isoformat() if scheme.latest_nav_date else None,
                'history_start': scheme.history_start.isoformat() if scheme.history_start else None,
                'ocs_score': ocs_score,
                'analytics': {
                    'cagr': float(analytics.cagr) if analytics and analytics.cagr else 0.0,
                    'sharpe_ratio': float(analytics.sharpe_ratio) if analytics and analytics.sharpe_ratio else 0.0,
                    'sortino_ratio': float(analytics.sortino_ratio) if analytics and analytics.sortino_ratio else 0.0,
                    'beta': float(analytics.beta) if analytics and analytics.beta else 1.0,
                    'upside_capture': float(analytics.upside_capture) if analytics and analytics.upside_capture else 100.0,
                    'downside_capture': float(analytics.downside_capture) if analytics and analytics.downside_capture else 100.0,
                    'volatility': float(analytics.volatility) if analytics.volatility is not None else None,
                    'max_drawdown': float(analytics.max_drawdown) if analytics.max_drawdown is not None else None,
                    'history_years': float(analytics.history_years) if analytics.history_years is not None else None,
                    'time_horizon': analytics.time_horizon_years if analytics else horizon_years
                },
                'investment_mode_adjusted_score': ocs_score
            }
            
            fund_scores.append(fund_recommendation)
        
        # Risk-aware sorting — handle None/inf gracefully
        def safe(v):
            try:
                f = float(v) if v is not None else 0.0
                return f if __import__('math').isfinite(f) else 0.0
            except: return 0.0
        if risk_appetite.lower() == 'low':
            fund_scores.sort(key=lambda x: (safe(x['analytics']['sharpe_ratio']) + safe(x['analytics']['sortino_ratio']))/2, reverse=True)
        elif risk_appetite.lower() == 'high':
            fund_scores.sort(key=lambda x: safe(x['analytics']['cagr']), reverse=True)
        else:
            fund_scores.sort(key=lambda x: safe(x['investment_mode_adjusted_score']), reverse=True)
        
        # Apply AMC cap rule: no single AMC > 33%
        filtered_funds = []
        amc_counts = {}
        for fund in fund_scores:
            amc = fund['amc_name']
            amc_counts[amc] = amc_counts.get(amc, 0) + 1
            if len(filtered_funds) == 0 or amc_counts.get(amc, 0) <= 1:
                filtered_funds.append(fund)
        
        return filtered_funds
        
    except Exception as e:
        logger.error(f"Error getting top funds: {e}")
        return []

def compare_schemes_detailed(scheme_ids: list, db: Session = None) -> dict:
    """
    Get detailed comparison data for a list of schemes.
    """
    try:
        # Get all schemes and their analytics
        schemes_data = []
        for scheme_id in scheme_ids:
            scheme = db.query(MutualFundScheme).filter(
                MutualFundScheme.scheme_id == scheme_id
            ).first()
            
            if not scheme:
                continue
            
            # Get analytics for different horizons
            analytics = db.query(SchemeAnalytics).filter(
                SchemeAnalytics.scheme_id == scheme_id
            ).all()
            
            schemes_data.append({
                'scheme': scheme,
                'analytics': {a.time_horizon_years: a for a in analytics}
            })
        
        # Calculate overlap if needed
        overlap_matrix = calculate_overlap_matrix(scheme_ids, db)
        
        return {
            'schemes': schemes_data,
            'overlap_matrix': overlap_matrix,
            'comparison_metrics': calculate_comparison_metrics(schemes_data)
        }
        
    except Exception as e:
        logger.error(f"Error comparing schemes: {e}")
        return {'schemes': [], 'overlap_matrix': {}, 'comparison_metrics': {}}

def calculate_overlap_matrix(scheme_ids: list, db: Session = None) -> dict:
    """
    Calculate Jaccard similarity matrix for scheme holdings overlap.
    """
    try:
        # Placeholder implementation - would use actual holdings data
        overlap_matrix = {}
        
        for i, scheme_id in enumerate(scheme_ids):
            scheme_holdings = get_scheme_holdings(scheme_id, db)
            overlap_matrix[scheme_id] = {}
            
            for j, other_scheme_id in enumerate(scheme_ids):
                if i == j:
                    overlap_matrix[scheme_id][other_scheme_id] = 1.0
                else:
                    other_holdings = get_scheme_holdings(other_scheme_id, db)
                    jaccard_sim = calculate_jaccard_similarity(scheme_holdings, other_holdings)
                    overlap_matrix[scheme_id][other_scheme_id] = jaccard_sim
        
        return overlap_matrix
        
    except Exception as e:
        logger.error(f"Error calculating overlap matrix: {e}")
        return {}

def calculate_jaccard_similarity(set1: set, set2: set) -> float:
    """Calculate Jaccard similarity between two sets"""
    if not set1 and not set2:
        return 1.0
    if not set1 or not set2:
        return 0.0
    
    intersection = len(set1.intersection(set2))
    union = len(set1.union(set2))
    
    return intersection / union if union > 0 else 0.0

def get_scheme_holdings(scheme_id: int, db: Session = None) -> set:
    """Get holdings for a scheme (placeholder)"""
    # Placeholder - would fetch actual holdings data from database
    # This would typically come from portfolio holdings table
    return set()

def get_mode_multiplier(investment_mode: str, analytics) -> float:
    """Get mode-specific multiplier for scoring"""
    if investment_mode.lower() == 'lump sum':
        return 1.1  # Favor stability for lump sum
    elif investment_mode.lower() == 'sip':
        return 1.05  # Slightly favor SIP flexibility
    return 1.0

def calculate_comparison_metrics(schemes_data: list) -> dict:
    """Calculate comparative metrics across schemes"""
    try:
        metrics = {
            'cagr_range': [],
            'sharpe_range': [],
            'expense_ratio_range': [],
            'category_distribution': {}
        }
        
        for scheme_data in schemes_data:
            scheme = scheme_data['scheme']
            category = scheme.category
            metrics['category_distribution'][category] = metrics['category_distribution'].get(category, 0) + 1
            
            for horizon, analytics in scheme_data['analytics'].items():
                metrics['cagr_range'].append(float(analytics.cagr) if analytics.cagr else 0.0)
                metrics['sharpe_range'].append(float(analytics.sharpe_ratio) if analytics.sharpe_ratio else 0.0)
                metrics['expense_ratio_range'].append(float(scheme.expense_ratio) if scheme.expense_ratio else 0.0)
        
        # Calculate ranges
        metrics['cagr_range'] = [min(metrics['cagr_range']), max(metrics['cagr_range'])]
        metrics['sharpe_range'] = [min(metrics['sharpe_range']), max(metrics['sharpe_range'])]
        metrics['expense_ratio_range'] = [min(metrics['expense_ratio_range']), max(metrics['expense_ratio_range'])]
        
        return metrics
        
    except Exception as e:
        logger.error(f"Error calculating comparison metrics: {e}")
        return {'cagr_range': [0, 0], 'sharpe_range': [0, 0], 'expense_ratio_range': [0, 0], 'category_distribution': {}}