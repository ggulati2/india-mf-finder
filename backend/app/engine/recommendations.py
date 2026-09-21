from sqlalchemy.orm import Session
from app.db.models import MutualFundScheme, SchemeAnalytics
from app.engine.scoring import calculate_ocs_score, compute_scheme_analytics
import pandas as pd
import logging

logger = logging.getLogger(__name__)

def get_category_scores(db: Session, scheme_id: int) -> dict:
    """Get category-based scores for normalizing within category"""
    try:
        scheme = db.query(MutualFundScheme).filter(
            MutualFundScheme.scheme_id == scheme_id
        ).first()
        
        if not scheme:
            return {'rolling_returns': 50.0, 'risk_adjusted': 50.0, 'consistency': 50.0, 
                   'fundamentals': 50.0, 'trend': 50.0}
        
        # Get analytics for the scheme
        analytics = db.query(SchemeAnalytics).filter(
            SchemeAnalytics.scheme_id == scheme_id
        ).first()
        
        # Get all schemes in the same category for comparison
        category_schemes = db.query(SchemeAnalytics).join(
            MutualFundScheme
        ).filter(
            MutualFundScheme.category == scheme.category
        ).all()
        
        if not category_schemes:
            return {'rolling_returns': 50.0, 'risk_adjusted': 50.0, 'consistency': 50.0, 
                   'fundamentals': 50.0, 'trend': 50.0}
        
        # Calculate category averages
        cagr_values = [a.cagr for a in category_schemes if a.cagr is not None]
        sharpe_values = [a.sharpe_ratio for a in category_schemes if a.sharpe_ratio is not None]
        std_values = [a.rolling_returns_std for a in category_schemes if a.rolling_returns_std is not None]
        sortino_values = [a.sortino_ratio for a in category_schemes if a.sortino_ratio is not None]
        
        # Calculate category averages
        category_avg_cagr = np.mean(cagr_values) if cagr_values else 0
        category_avg_sharpe = np.mean(sharpe_values) if sharpe_values else 0
        category_avg_std = np.mean(std_values) if std_values else 0
        category_avg_sortino = np.mean(sortino_values) if sortino_values else 0
        
        # Get current scheme metrics
        current_cagr = analytics.cagr if analytics else 0
        current_sharpe = analytics.sharpe_ratio if analytics else 0
        current_std = analytics.rolling_returns_std if analytics else 0
        current_sortino = analytics.sortino_ratio if analytics else 0
        
        # Calculate scores (0-100 scale)
        def calculate_percentile_score(value, values):
            if not values:
                return 50.0
            sorted_values = sorted(values)
            index = np.searchsorted(sorted_values, value)
            percentile = (index / len(sorted_values)) * 100
            return float(percentile)
        
        # Calculate component scores
        rolling_returns_score = calculate_percentile_score(current_cagr, cagr_values)
        risk_adjusted_score = calculate_percentile_score(current_sharpe, sharpe_values)
        consistency_score = calculate_percentile_score(category_avg_std, std_values)
        fundamentals_score = 50.0  # Placeholder
        trend_score = 50.0  # Placeholder
        
        # Invert consistency score (lower std = higher score)
        consistency_score = 100 - consistency_score
        
        return {
            'rolling_returns': rolling_returns_score,
            'risk_adjusted': risk_adjusted_score,
            'consistency': consistency_score,
            'fundamentals': fundamentals_score,
            'trend': trend_score
        }
        
    except Exception as e:
        logger.error(f"Error getting category scores: {e}")
        return {'rolling_returns': 50.0, 'risk_adjusted': 50.0, 'consistency': 50.0, 
               'fundamentals': 50.0, 'trend': 50.0}

def get_top_funds(
    investment_amount: float,
    investment_mode: str,
    horizon_years: int,
    risk_appetite: str,
    category: str = None,
    db: Session = None
) -> list:
    """
    Get top fund recommendations based on investment parameters.
    """
    try:
        # Default to all schemes if no category filter
        query = db.query(MutualFundScheme, SchemeAnalytics)
        
        if category:
            query = query.filter(MutualFundScheme.category == category)
        
        # Join with analytics for the default horizon (5 years if available)
        query = query.join(SchemeAnalytics).filter(
            SchemeAnalytics.time_horizon_years == horizon_years
        )
        
        # Filter to direct plans only
        query = query.filter(MutualFundScheme.plan_type == "Direct")
        
        # Execute query
        results = query.all()
        
        fund_scores = []
        
        for scheme, analytics in results:
            if not analytics:
                continue
            
            # Get category scores for anti-bias normalization
            category_scores = get_category_scores(db, scheme.scheme_id)
            
            # Prepare scheme data for OCS calculation
            scheme_data = {
                'scheme_id': scheme.scheme_id,
                'amc_name': scheme.amc_name,
                'category': scheme.category,
                'plan_type': scheme.plan_type,
                'option_type': scheme.option_type,
                'expense_ratio': float(scheme.expense_ratio) if scheme.expense_ratio else 0.0,
                'pe_ratio': None,  # Placeholder - would get from portfolio data
                'pb_ratio': None,  # Placeholder - would get from portfolio data
                'volatility': analytics.rolling_returns_std if analytics else 0.0,
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
            
            # Prepare fund recommendation
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
                'expense_ratio': float(scheme.expense_ratio) if scheme.expense_ratio else 0.0,
                'ocs_score': ocs_score,
                'analytics': {
                    'cagr': float(analytics.cagr) if analytics.cagr else 0.0,
                    'sharpe_ratio': float(analytics.sharpe_ratio) if analytics.sharpe_ratio else 0.0,
                    'sortino_ratio': float(analytics.sortino_ratio) if analytics.sortino_ratio else 0.0,
                    'beta': float(analytics.beta) if analytics.beta else 0.0,
                    'upside_capture': float(analytics.upside_capture) if analytics.upside_capture else 0.0,
                    'downside_capture': float(analytics.downside_capture) if analytics.downside_capture else 0.0,
                    'time_horizon': analytics.time_horizon_years
                },
                'investment_mode_adjusted_score': ocs_score * get_mode_multiplier(investment_mode, analytics)
            }
            
            fund_scores.append(fund_recommendation)
        
        # Sort by OCS score (highest first)
        fund_scores.sort(key=lambda x: x['investment_mode_adjusted_score'], reverse=True)
        
        # Filter out schemes with AMC cap violation for multi-fund portfolios
        filtered_funds = []
        amc_weights = {}
        
        for fund in fund_scores:
            amc_name = fund['amc_name']
            amc_weights[amc_name] = amc_weights.get(amc_name, 0) + 1
            
            if len(filtered_funds) == 0 or amc_weights.get(amc_name, 0) <= 1:
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