from fastapi import APIRouter, Depends, HTTPException, Query
from typing import List, Optional
from sqlalchemy.orm import Session
from app.db.models import SchemeAnalytics, MutualFundScheme, SchemeNAVData
from app.db.database import get_db

router = APIRouter()

@router.get("/{scheme_id}/history")
async def get_scheme_history(
    scheme_id: int,
    years: Optional[int] = Query(5, description="Years of history"),
    db: Session = Depends(get_db),
):
    scheme = db.query(MutualFundScheme).filter(MutualFundScheme.scheme_id == scheme_id).first()
    if not scheme:
        raise HTTPException(status_code=404, detail="Scheme not found")
    q = db.query(SchemeNAVData).filter(SchemeNAVData.scheme_id == scheme_id).order_by(SchemeNAVData.time.asc())
    rows = q.all()
    # filter to last N years if requested
    if years and rows:
        from datetime import date, timedelta
        cutoff = date.today() - timedelta(days=int(years*365.25))
        rows = [r for r in rows if r.time >= cutoff]
    return {
        "scheme_id": scheme_id,
        "scheme_name": scheme.scheme_name,
        "amc_name": scheme.amc_name,
        "category": scheme.category,
        "points": [{"date": str(r.time), "nav": float(r.nav)} for r in rows],
        "count": len(rows),
    }

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
