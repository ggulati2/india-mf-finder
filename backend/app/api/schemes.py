from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from typing import List, Optional
from pydantic import BaseModel
from sqlalchemy.orm import Session
from app.db.models import MutualFundScheme, SchemeAnalytics
from app.db.database import get_db
from app.engine.recommendations import get_top_funds
import json

router = APIRouter()

class FundFilter(BaseModel):
    category: Optional[str] = None
    plan_type: Optional[str] = "Direct"
    option_type: Optional[str] = None
    min_rating: Optional[float] = None
    max_expense_ratio: Optional[float] = None

@router.get("/", response_model=List[dict])
async def get_schemes(
    filter: FundFilter = Depends(),
    db: Session = Depends(get_db)
):
    query = db.query(MutualFundScheme)

    if filter.category:
        query = query.filter(MutualFundScheme.category == filter.category)

    if filter.plan_type:
        query = query.filter(MutualFundScheme.plan_type == filter.plan_type)

    if filter.option_type:
        query = query.filter(MutualFundScheme.option_type == filter.option_type)

    if filter.min_rating:
        query = query.filter(MutualFundScheme.rating >= filter.min_rating)

    if filter.max_expense_ratio:
        query = query.filter(MutualFundScheme.expense_ratio <= filter.max_expense_ratio)

    return query.all()

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
    return await get_top_funds(
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
    return await compare_schemes_detailed(ids, db)
