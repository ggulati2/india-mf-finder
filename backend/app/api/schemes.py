from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from typing import List, Optional
from sqlalchemy.orm import Session
from app.db.models import MutualFundScheme, SchemeAnalytics
from app.db.database import get_db
from app.engine.recommendations import get_top_funds, compare_schemes_detailed
import json

router = APIRouter()

@router.get("/")
async def get_schemes(
    plan_type: Optional[str] = Query("Direct", description="Plan type"),
    category: Optional[str] = Query(None, description="Filter by category"),
    option_type: Optional[str] = Query(None, description="Filter by option type"),
    db: Session = Depends(get_db)
):
    query = db.query(MutualFundScheme).filter(MutualFundScheme.is_active == True)

    if category:
        query = query.filter(MutualFundScheme.category == category)

    if plan_type:
        query = query.filter(MutualFundScheme.plan_type == plan_type)

    if option_type:
        query = query.filter(MutualFundScheme.option_type == option_type)

    results = query.all()
    return [
        {
            "scheme_id": s.scheme_id,
            "amfi_code": s.amfi_code,
            "isin": s.isin,
            "scheme_name": s.scheme_name,
            "amc_name": s.amc_name,
            "category": s.category,
            "plan_type": s.plan_type,
            "option_type": s.option_type,
            "launch_date": str(s.launch_date),
            "expense_ratio": float(s.ter_pct) if s.ter_pct is not None else None,
            "sebi_category": s.sebi_category,
            "is_active": s.is_active
        }
        for s in results
    ]

@router.get("/{scheme_id}")
async def get_scheme(scheme_id: int, db: Session = Depends(get_db)):
    scheme = db.query(MutualFundScheme).filter(MutualFundScheme.scheme_id == scheme_id).first()
    if not scheme:
        raise HTTPException(status_code=404, detail="Scheme not found")
    return scheme

@router.get("/recommendations/top-funds")
async def get_top_funds_endpoint(
    investment_amount: float = Query(..., description="Investment amount in INR"),
    investment_mode: str = Query(..., description="Lump Sum or SIP"),
    horizon_years: int = Query(..., description="Investment horizon in years"),
    risk_appetite: str = Query(..., description="Low, Medium, or High"),
    category: Optional[str] = Query(None, description="Filter by category"),
    db: Session = Depends(get_db)
):
    return get_top_funds(
        investment_amount=investment_amount,
        investment_mode=investment_mode,
        horizon_years=horizon_years,
        risk_appetite=risk_appetite,
        category=category,
        db=db
    )

@router.get("/recommendations/compare")
async def compare_schemes(
    scheme_ids: str = Query(..., description="Comma-separated scheme IDs"),
    db: Session = Depends(get_db)
):
    ids = [int(id.strip()) for id in scheme_ids.split(",") if id.strip()]
    return compare_schemes_detailed(ids, db)
