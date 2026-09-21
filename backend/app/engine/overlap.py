from sqlalchemy.orm import Session
from app.db.models import MutualFundScheme, SchemeNAVData, SchemeAnalytics
from app.db.database import get_db
from typing import List, Dict
import numpy as np
import logging

logger = logging.getLogger(__name__)

def calculate_overlap_matrix(scheme_ids: List[int], db: Session = None) -> Dict:
    """
    Calculate Jaccard similarity matrix for scheme holdings overlap.
    """
    try:
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
    """Get holdings for a scheme"""
    # Placeholder - would fetch actual holdings data from database
    # This would typically come from portfolio holdings table
    return set()

def get_fund_overlap(scheme_id: int, top_n: int = 10, db: Session = None) -> Dict:
    """Get overlap for a specific scheme with top N funds"""
    try:
        if db is None:
            db = next(get_db())

        # Get all schemes in the same category
        scheme = db.query(MutualFundScheme).filter(
            MutualFundScheme.scheme_id == scheme_id
        ).first()

        if not scheme:
            return {"error": "Scheme not found"}

        # Get other schemes in the same category
        other_schemes = db.query(MutualFundScheme).filter(
            MutualFundScheme.category == scheme.category,
            MutualFundScheme.scheme_id != scheme_id
        ).all()

        # Calculate overlap for each
        overlaps = []
        for other_scheme in other_schemes:
            holdings1 = get_scheme_holdings(scheme_id, db)
            holdings2 = get_scheme_holdings(other_scheme.scheme_id, db)
            similarity = calculate_jaccard_similarity(holdings1, holdings2)
            overlaps.append({
                "scheme_id": other_scheme.scheme_id,
                "scheme_name": other_scheme.scheme_name,
                "overlap_score": similarity
            })

        # Sort by overlap score descending and take top N
        overlaps.sort(key=lambda x: x["overlap_score"], reverse=True)
        return {"scheme_id": scheme_id, "top_overlaps": overlaps[:top_n]}

    except Exception as e:
        logger.error(f"Error getting fund overlap: {e}")
        return {"error": str(e)}

def compare_schemes_detailed(scheme_ids: List[int], db: Session = None) -> Dict:
    """
    Get detailed comparison data for a list of schemes.
    """
    try:
        if db is None:
            db = next(get_db())

        schemes_data = []
        for scheme_id in scheme_ids:
            scheme = db.query(MutualFundScheme).filter(
                MutualFundScheme.scheme_id == scheme_id
            ).first()

            if not scheme:
                continue

            analytics = db.query(SchemeAnalytics).filter(
                SchemeAnalytics.scheme_id == scheme_id
            ).all()

            schemes_data.append({
                "scheme": scheme,
                "analytics": {a.time_horizon_years: a for a in analytics}
            })

        overlap_matrix = calculate_overlap_matrix(scheme_ids, db)
        comparison_metrics = calculate_comparison_metrics(schemes_data)

        return {
            "schemes": schemes_data,
            "overlap_matrix": overlap_matrix,
            "comparison_metrics": comparison_metrics
        }

    except Exception as e:
        logger.error(f"Error comparing schemes: {e}")
        return {"schemes": [], "overlap_matrix": {}, "comparison_metrics": {}}

def calculate_comparison_metrics(schemes_data: List[Dict]) -> Dict:
    """Calculate comparative metrics across schemes"""
    try:
        metrics = {
            "cagr_range": [],
            "sharpe_range": [],
            "expense_ratio_range": [],
            "category_distribution": {}
        }

        for scheme_data in schemes_data:
            scheme = scheme_data["scheme"]
            category = scheme.category
            metrics["category_distribution"][category] = metrics["category_distribution"].get(category, 0) + 1

            for horizon, analytics in scheme_data["analytics"].items():
                metrics["cagr_range"].append(float(analytics.cagr) if analytics.cagr else 0.0)
                metrics["sharpe_range"].append(float(analytics.sharpe_ratio) if analytics.sharpe_ratio else 0.0)
                metrics["expense_ratio_range"].append(float(scheme.expense_ratio) if scheme.expense_ratio else 0.0)

        metrics["cagr_range"] = [min(metrics["cagr_range"]), max(metrics["cagr_range"])] if metrics["cagr_range"] else [0, 0]
        metrics["sharpe_range"] = [min(metrics["sharpe_range"]), max(metrics["sharpe_range"])] if metrics["sharpe_range"] else [0, 0]
        metrics["expense_ratio_range"] = [min(metrics["expense_ratio_range"]), max(metrics["expense_ratio_range"])] if metrics["expense_ratio_range"] else [0, 0]

        return metrics

    except Exception as e:
        logger.error(f"Error calculating comparison metrics: {e}")
        return {"cagr_range": [0, 0], "sharpe_range": [0, 0], "expense_ratio_range": [0, 0], "category_distribution": {}}