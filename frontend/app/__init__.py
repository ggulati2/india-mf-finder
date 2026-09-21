from typing import List, Optional
from pydantic import BaseModel

class FundRecommendation(BaseModel):
    scheme_id: int
    scheme_name: str
    amc_name: str
    category: str
    ocs_score: float
    analytics: dict
    plan_type: str = "Direct"
    expense_ratio: float

class SchemeComparison(BaseModel):
    scheme_ids: List[int]
    comparison_metrics: dict
    overlap_matrix: dict

class HealthCheck(BaseModel):
    status: str
