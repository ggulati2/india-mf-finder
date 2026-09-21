from fastapi import APIRouter, Depends, HTTPException, Query
from typing import List, Optional
from sqlalchemy.orm import Session
from app.db.models import MutualFundScheme
from app.db.database import get_db
from app.engine.overlap import calculate_overlap_matrix, get_fund_overlap

router = APIRouter()

@router.get("/matrix")
async def get_overlap_matrix(
    scheme_ids: str = Query(..., description="Comma-separated scheme IDs"),
    db: Session = Depends(get_db)
):
    ids = [int(id.strip()) for id in scheme_ids.split(",") if id.strip()]
    return await calculate_overlap_matrix(ids, db)

@router.get("/fund/{scheme_id}")
async def get_fund_overlap_with_all(
    scheme_id: int,
    top_n: int = Query(10, description="Number of top funds to compare with"),
    db: Session = Depends(get_db)
):
    return await get_fund_overlap(scheme_id, top_n, db)

@router.get("/schemes/compare")
async def compare_schemes(
    scheme_ids: str = Query(..., description="Comma-separated scheme IDs"),
    db: Session = Depends(get_db)
):
    ids = [int(id.strip()) for id in scheme_ids.split(",") if id.strip()]
    return await compare_schemes_detailed(ids, db)
