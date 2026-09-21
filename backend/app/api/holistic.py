from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Optional
from app.db.database import get_db
from app.db.models import MutualFundScheme, SchemeNAVData, SchemeAnalytics
import pandas as pd

router = APIRouter()

@router.get("/{scheme_id}/holistic")
async def get_holistic(scheme_id: int, years: int = Query(5), db: Session = Depends(get_db)):
    scheme = db.query(MutualFundScheme).filter(MutualFundScheme.scheme_id == scheme_id).first()
    if not scheme:
        raise HTTPException(404, "Scheme not found")
    # NAV history
    nav_rows = db.query(SchemeNAVData).filter(SchemeNAVData.scheme_id == scheme_id).order_by(SchemeNAVData.time.asc()).all()
    nav_df = pd.DataFrame([{"date": r.time, "nav": float(r.nav)} for r in nav_rows]) if nav_rows else pd.DataFrame()
    if not nav_df.empty:
        nav_df["date"] = pd.to_datetime(nav_df["date"])
        nav_df = nav_df.sort_values("date")

    # analytics
    analytics = {a.time_horizon_years: a for a in db.query(SchemeAnalytics).filter(SchemeAnalytics.scheme_id == scheme_id).all()}

    # holdings
    from app.engine.holdings import get_holdings_detail
    holdings = get_holdings_detail(scheme_id, scheme.category)
    # sector allocation
    from collections import Counter
    sector_w = Counter()
    for h in holdings:
        sector_w[h["sector"]] += h["weight"]
    sector_alloc = [{"sector": k, "weight": round(v,1)} for k,v in sector_w.most_common()]

    # risk
    from app.engine.risk import max_drawdown, rolling_returns_series, sip_xirr
    mdd = 0.0
    rolling = []
    sip = 0.0
    if not nav_df.empty:
        mdd = max_drawdown(nav_df["nav"])
        rolling = rolling_returns_series(nav_df, window_years=3)
        sip = sip_xirr(nav_df, monthly_amount=10000, years=years)

    # benchmark comparison (optional, not blocking)
    bench_cagr = None
    try:
        from app.engine.benchmark import fetch_nifty_history
        bench_df = await fetch_nifty_history(days=int(years*365))
        if not bench_df.empty and not nav_df.empty:
            # compute bench CAGR over same window
            cutoff = nav_df["date"].max() - pd.Timedelta(days=int(years*365.25))
            b = bench_df[bench_df["date"] >= cutoff]
            if len(b) > 20:
                bench_cagr = round(float((b.iloc[-1]["close"]/b.iloc[0]["close"])**(1/years)-1)*100,2)
    except Exception:
        bench_cagr = None

    return {
        "scheme": {
            "scheme_id": scheme.scheme_id,
            "scheme_name": scheme.scheme_name,
            "amc_name": scheme.amc_name,
            "category": scheme.category,
            "expense_ratio": float(scheme.expense_ratio),
            "launch_date": str(scheme.launch_date),
        },
        "analytics": {k: {"cagr": float(v.cagr) if v.cagr else 0, "sharpe": float(v.sharpe_ratio) if v.sharpe_ratio else 0, "sortino": float(v.sortino_ratio) if v.sortino_ratio else 0, "beta": float(v.beta) if v.beta else 0} for k,v in analytics.items()},
        "risk": {"max_drawdown": round(mdd,2), "rolling_3y": rolling[:100], "sip_xirr_5y": sip, "benchmark_nifty_cagr": bench_cagr},
        "holdings": holdings[:20],
        "sector_allocation": sector_alloc,
        "nav_history": [{"date": str(r.time), "nav": float(r.nav)} for r in nav_rows[-252*years:]] if nav_rows else [],
        "data_source": "mfapi.in / AMFI via historic_nav.py; holdings synthetic deterministic per category; Nifty via Yahoo Finance",
    }

@router.get("/{scheme_id}/holdings")
async def get_holdings(scheme_id: int, db: Session = Depends(get_db)):
    scheme = db.query(MutualFundScheme).filter(MutualFundScheme.scheme_id == scheme_id).first()
    if not scheme:
        raise HTTPException(404, "Scheme not found")
    from app.engine.holdings import get_holdings_detail
    holdings = get_holdings_detail(scheme_id, scheme.category)
    return {"scheme_id": scheme_id, "scheme_name": scheme.scheme_name, "holdings": holdings}
