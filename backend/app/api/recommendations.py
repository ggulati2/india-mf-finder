from fastapi import APIRouter, Depends, HTTPException, Query
from typing import List, Optional
from sqlalchemy.orm import Session
from app.db.models import MutualFundScheme, SchemeAnalytics
from app.db.database import get_db
from app.engine.recommendations import get_top_funds, compare_schemes_detailed

router = APIRouter()

@router.get("/funds")
async def get_recommendations(
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

@router.get("/compare")
async def compare_schemes(
    scheme_ids: str = Query(..., description="Comma-separated scheme IDs"),
    db: Session = Depends(get_db)
):
    ids = [int(id.strip()) for id in scheme_ids.split(",") if id.strip()]
    return compare_schemes_detailed(ids, db)

@router.get("/category/{category}")
async def get_category_recommendations(
    category: str,
    investment_mode: str = Query(..., description="Lump Sum or SIP"),
    risk_appetite: str = Query(..., description="Low, Medium, or High"),
    db: Session = Depends(get_db)
):
    return get_top_funds(
        investment_amount=0,
        investment_mode=investment_mode,
        horizon_years=5,
        risk_appetite=risk_appetite,
        category=category,
        db=db
    )