"""Backfill historic NAV + analytics.

  python scripts/backfill.py ingest      # fetch NAV for schemes lacking it, then analytics
  python scripts/backfill.py recompute   # recompute analytics for all schemes that have NAV

Run from backend/ with PYTHONPATH=. Skips category "Other" (closed-ended/matured).
"""
import asyncio, sys, time
from datetime import date
import pandas as pd
from app.db.database import SessionLocal
from app.db.models import MutualFundScheme, SchemeNAVData, SchemeAnalytics
from app.etl.historic_nav import fetch_historic_nav_for_scheme
from app.engine.scoring import compute_scheme_analytics

ORDER = {'Large Cap': 0, 'Mid Cap': 1, 'Small Cap': 2, 'Flexi Cap': 3, 'ELSS': 4,
         'Hybrid': 5, 'Index': 6, 'Sectoral': 7, 'Debt': 8}


def compute_for(db, s):
    rows = db.query(SchemeNAVData).filter(SchemeNAVData.scheme_id == s.scheme_id).order_by(SchemeNAVData.time).all()
    if len(rows) < 50:
        return False
    df = pd.DataFrame([{'date': r.time, 'nav': float(r.nav)} for r in rows])
    df['date'] = pd.to_datetime(df['date'])
    db.query(SchemeAnalytics).filter(SchemeAnalytics.scheme_id == s.scheme_id).delete()
    for h in (1, 3, 5, 10):
        w = df[df['date'] >= df['date'].max() - pd.Timedelta(days=int(h * 365.25))]
        if len(w) < 20:
            w = df
        a = compute_scheme_analytics(nav_df=w, scheme=s, time_horizon_years=h)
        db.merge(SchemeAnalytics(
            scheme_id=s.scheme_id, computed_date=date.today(), time_horizon_years=h,
            cagr=a['cagr'], rolling_returns_mean=a['rolling_returns_mean'],
            rolling_returns_std=a['rolling_returns_std'], sharpe_ratio=a['sharpe_ratio'],
            sortino_ratio=a['sortino_ratio'], jensens_alpha=a['jensens_alpha'], beta=a['beta'],
            upside_capture=a['upside_capture'], downside_capture=a['downside_capture'],
            expense_ratio=s.expense_ratio or 0.0))
    db.commit()
    return True


async def main(mode):
    db = SessionLocal()
    schemes = [s for s in db.query(MutualFundScheme).all() if s.category != 'Other']
    have = {r[0] for r in db.query(SchemeNAVData.scheme_id).distinct()}
    if mode == 'ingest':
        todo = sorted([s for s in schemes if s.scheme_id not in have], key=lambda s: (ORDER.get(s.category, 9), s.amfi_code))
    else:
        todo = [s for s in schemes if s.scheme_id in have]
    print(f'{mode}: {len(todo)} schemes at {time.strftime("%H:%M:%S")}', flush=True)
    for i, s in enumerate(todo, 1):
        n = 0
        if mode == 'ingest':
            n = await fetch_historic_nav_for_scheme(s.amfi_code, s.scheme_id, db)
            await asyncio.sleep(0.3)
            if n == 0:
                continue
        ok = compute_for(db, s)
        print(f'[{i}/{len(todo)}] {s.category} {s.scheme_name[:50]} nav+{n} analytics={ok}', flush=True)

if __name__ == '__main__':
    asyncio.run(main(sys.argv[1] if len(sys.argv) > 1 else 'ingest'))
