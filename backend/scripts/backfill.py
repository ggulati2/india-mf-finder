"""Backfill and (re)validate historic NAV + analytics.

  python scripts/backfill.py master      # refresh categories/AMC/TER/active flags from AMFI
  python scripts/backfill.py ingest      # fetch NAV history for ACTIVE schemes lacking it, then analytics
  python scripts/backfill.py recompute   # validate + recompute analytics for all active schemes with NAV

Run from backend/ with PYTHONPATH=. Category "Other" (FoF, closed-ended, ETF) is skipped.
"""
import asyncio, sys, time
from datetime import date
import pandas as pd
from app.db.database import SessionLocal, init_db_sync
from app.db.models import MutualFundScheme, SchemeNAVData, SchemeAnalytics
from app.etl.historic_nav import fetch_historic_nav_for_scheme
from app.etl.master_data import refresh_master, _add_flag
from app.engine.scoring import compute_scheme_analytics
import pandas as pd_
from app.engine.quality import clean_nav, window_for_horizon, window_flags, find_jumps

ORDER = {'Large Cap': 0, 'Mid Cap': 1, 'Small Cap': 2, 'Flexi Cap': 3, 'ELSS': 4,
         'Hybrid': 5, 'Index': 6, 'Sectoral': 7, 'Debt': 8}
NAV_FLAGS = ("repaired_points", "nav_jump_old", "nonpositive_nav", "nav_jump", "nav_gap", "sparse_history", "insufficient_history")
BLOCKING = set(NAV_FLAGS) - {"repaired_points", "nav_jump_old"}


def compute_for(db, s):
    """Validate NAVs, then write analytics only for horizons we truly have. Returns flag list."""
    rows = db.query(SchemeNAVData).filter(SchemeNAVData.scheme_id == s.scheme_id).order_by(SchemeNAVData.time).all()
    kept = [f for f in (s.data_flags or "").split(",") if f and f not in NAV_FLAGS]
    db.query(SchemeAnalytics).filter(SchemeAnalytics.scheme_id == s.scheme_id).delete()
    if len(rows) < 50:
        s.data_flags = ",".join(kept + ["insufficient_history"])
        db.commit()
        return ["insufficient_history"]
    df = pd.DataFrame([{'date': r.time, 'nav': float(r.nav)} for r in rows])
    df['date'] = pd.to_datetime(df['date'])
    df, flags = clean_nav(df, s.category)
    if df.empty:
        s.data_flags = ",".join(kept + sorted(set(flags + ["insufficient_history"])))
        db.commit()
        return sorted(set(flags + ["insufficient_history"]))
    s.history_start = df['date'].iloc[0].date()
    s.launch_date = s.history_start          # earliest NAV we hold; true launch may be earlier
    # A break in the series only invalidates horizons whose window contains it; it blocks the whole
    # scheme only if it is recent (last 12 months), since that taints every horizon.
    jumps = find_jumps(df, s.category)
    flags = [f for f in flags if f != "nav_jump"]
    if jumps:
        flags.append("nav_jump" if max(jumps) >= df['date'].max() - pd_.Timedelta(days=365) else "nav_jump_old")
    recent = window_for_horizon(df, 5) if len(df) else None
    flags += window_flags(recent if recent is not None else df)
    flags = sorted(set(flags))
    s.data_flags = ",".join(kept + flags) or None
    if BLOCKING & set(flags):
        db.commit()
        return flags
    for h in (1, 3, 5, 10):
        w = window_for_horizon(df, h)
        if w is None or any(j >= w['date'].iloc[0] for j in jumps):
            continue                          # never fake a horizon with shorter history
        a = compute_scheme_analytics(nav_df=w, scheme=s, time_horizon_years=h)
        db.add(SchemeAnalytics(
            scheme_id=s.scheme_id, computed_date=date.today(), time_horizon_years=h,
            cagr=a['cagr'], rolling_returns_mean=a['rolling_returns_mean'],
            rolling_returns_std=a['rolling_returns_std'], sharpe_ratio=a['sharpe_ratio'],
            sortino_ratio=a['sortino_ratio'], jensens_alpha=a['jensens_alpha'], beta=a['beta'],
            upside_capture=a['upside_capture'], downside_capture=a['downside_capture'],
            volatility=a['volatility'], max_drawdown=a['max_drawdown'], history_years=a['history_years'],
            expense_ratio=s.ter_pct))
    db.commit()
    return flags


async def main(mode):
    init_db_sync()
    db = SessionLocal()
    if mode == 'master':
        print(refresh_master(db)); return
    schemes = [s for s in db.query(MutualFundScheme).all() if s.is_active and s.category != 'Other']
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
        flags = compute_for(db, s)
        print(f'[{i}/{len(todo)}] {s.category} {s.scheme_name[:50]} nav+{n} flags={",".join(flags) or "ok"}', flush=True)

if __name__ == '__main__':
    asyncio.run(main(sys.argv[1] if len(sys.argv) > 1 else 'ingest'))
