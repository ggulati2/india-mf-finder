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
    max_points: int = Query(250, ge=20, le=2000, description="Downsample to at most this many points"),
    db: Session = Depends(get_db),
):
    scheme = db.query(MutualFundScheme).filter(MutualFundScheme.scheme_id == scheme_id).first()
    if not scheme:
        raise HTTPException(status_code=404, detail="Scheme not found")
    rows = db.query(SchemeNAVData).filter(SchemeNAVData.scheme_id == scheme_id).order_by(SchemeNAVData.time.asc()).all()
    points = []
    if rows:
        import pandas as pd
        from app.engine.quality import clean_nav
        df = pd.DataFrame([{"date": pd.Timestamp(r.time), "nav": float(r.nav)} for r in rows])
        df, _ = clean_nav(df, scheme.category)   # same validated series the analytics use
        if years:
            df = df[df["date"] >= df["date"].max() - pd.Timedelta(days=int(years * 365.25))]
        if len(df) > max_points:
            step = len(df) / max_points
            idx = sorted({int(i * step) for i in range(max_points)} | {len(df) - 1})
            df = df.iloc[idx]
        base = float(df["nav"].iloc[0]) if len(df) else 1.0
        points = [{"date": str(d.date()), "nav": float(v), "value": round(float(v) / base * 100, 2)}
                  for d, v in zip(df["date"], df["nav"])]
    return {
        "scheme_id": scheme_id,
        "scheme_name": scheme.scheme_name,
        "amc_name": scheme.amc_name,
        "category": scheme.category,
        "points": points,
        "count": len(points),
        "as_of": str(scheme.latest_nav_date) if scheme.latest_nav_date else None,
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
