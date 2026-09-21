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
        from app.engine.quality import clean_nav
        nav_df, _ = clean_nav(nav_df, scheme.category)

    # analytics
    analytics = {a.time_horizon_years: a for a in db.query(SchemeAnalytics).filter(SchemeAnalytics.scheme_id == scheme_id).all()}

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

    vol5 = next((analytics[h] for h in (5, 3, 1) if h in analytics), None)
    from app.engine.risk_level import risk_level
    level = risk_level(scheme.category, scheme.sebi_category,
                       float(vol5.volatility) if vol5 and vol5.volatility is not None else None,
                       float(vol5.max_drawdown) if vol5 and vol5.max_drawdown is not None else None)

    from app.engine.confidence import data_confidence
    conf = data_confidence(scheme, vol5, years)

    def n(x):
        return float(x) if x is not None else None

    return {
        "scheme": {
            "scheme_id": scheme.scheme_id,
            "scheme_name": scheme.scheme_name,
            "amc_name": scheme.amc_name,
            "category": scheme.category,
            "sebi_category": scheme.sebi_category,
            "expense_ratio": n(scheme.ter_pct),
            "launch_date": str(scheme.history_start) if scheme.history_start else None,
        },
        "analytics": {k: {"cagr": n(v.cagr), "sharpe": n(v.sharpe_ratio), "sortino": n(v.sortino_ratio), "beta": n(v.beta),
                          "volatility": n(v.volatility), "max_drawdown": n(v.max_drawdown), "history_years": n(v.history_years)}
                      for k, v in analytics.items()},
        "risk": {**level, "max_drawdown": round(mdd, 2), "rolling_3y": rolling[:100],
                 "sip_xirr_5y": sip, "benchmark_nifty_cagr": bench_cagr},
        "confidence": conf,
        "holdings": [],
        "sector_allocation": [],
        "holdings_note": "Portfolio holdings are not shown: there is no verified public data feed for them yet.",
        "nav_history": [{"date": str(d.date()), "nav": float(v)} for d, v in zip(nav_df["date"], nav_df["nav"])][-252*years:] if not nav_df.empty else [],
        "data_quality": {
            "nav_source": "AMFI NAV data via mfapi.in; validated (spikes repaired, gaps/jumps flagged)",
            "category_source": "AMFI/SEBI scheme category",
            "expense_source": "AMFI TER disclosure" if scheme.ter_pct is not None else "not available for this scheme",
            "benchmark": "Nifty 50 price index (Yahoo Finance), excludes dividends",
            "nav_as_of": str(scheme.latest_nav_date) if scheme.latest_nav_date else None,
            "flags": [f for f in (scheme.data_flags or "").split(",") if f],
            "sip_note": "SIP figure is a hypothetical back-test, not a forecast.",
        },
    }
