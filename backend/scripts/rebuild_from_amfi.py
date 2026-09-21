"""Rebuild everything from AMFI only: master data + TER, NAV history, then validated analytics.

  python scripts/rebuild_from_amfi.py            # all fund houses (~35 min)
  python scripts/rebuild_from_amfi.py 53 3       # only these AMFI fund-house ids (testing)
"""
import sys
import time
from app.db.database import SessionLocal, init_db_sync
from app.etl.master_data import refresh_master
from app.etl.amfi_history import rebuild_history
from app.db.models import MutualFundScheme
from scripts.backfill import compute_for

if __name__ == "__main__":
    init_db_sync()
    db = SessionLocal()
    t0 = time.time()
    print("master:", refresh_master(db), flush=True)
    st = rebuild_history(db, only_mf=sys.argv[1:] or None, log=lambda m: print(m, flush=True))
    print({k: (v if not isinstance(v, list) else len(v)) for k, v in st.items()}, flush=True)
    for name, bad, tot in st["mismatch_schemes"][:20]:
        print("  mismatch vs previous source:", name, f"{bad}/{tot}")
    ok = 0
    for s in db.query(MutualFundScheme).filter(MutualFundScheme.is_active == True, MutualFundScheme.category != "Other"):  # noqa: E712
        compute_for(db, s)
        ok += 1
    print(f"analytics recomputed for {ok} schemes in {time.time()-t0:.0f}s total")
