from fastapi import APIRouter, Depends, HTTPException, Query
from typing import List, Optional
from sqlalchemy.orm import Session
from app.db.models import SchemeAnalytics, MutualFundScheme
from app.db.database import get_db

router = APIRouter()

@router.get("/{scheme_id}")
async def get_scheme_analytics(
    scheme_id: int,
    time_horizon: Optional[int] = Query(None, description="Time horizon in years"),
    db: Session = Depends(get_db)
):
    query = db.query(SchemeAnalytics).filter(SchemeAnalytics.scheme_id == scheme_id)
    if time_horizon:
        query = query.filter(SchemeAnalytics.time_horizon_years == time_horizon)
    return query.all()

@router.get("/category/{category}")
async def get_category_analytics(
    category: str,
    time_horizon: Optional[int] = Query(None, description="Time horizon in years"),
    db: Session = Depends(get_db)
):
    query = db.query(SchemeAnalytics).join(MutualFundScheme).filter(
        MutualFundScheme.category == category
    )
    if time_horizon:
        query = query.filter(SchemeAnalytics.time_horizon_years == time_horizon)
    return query.all()
