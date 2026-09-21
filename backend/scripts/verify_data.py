"""Reconcile our stored NAV history against AMFI's official NAV history report.

  python scripts/verify_data.py [YYYY-MM-DD ...]     (default: ~1, 3 and 5 years ago)

For each date, downloads AMFI's report for that single day (independent of mfapi.in, where our
history came from) and compares every Direct-Growth scheme we hold. Exit code 1 if more than
0.5% of comparable NAVs disagree by over 0.01%.
"""
import sys
from datetime import date, datetime, timedelta

import httpx

from app.db.database import SessionLocal
from app.db.models import MutualFundScheme, SchemeNAVData

URL = "https://portal.amfiindia.com/DownloadNAVHistoryReport_Po.aspx?frmdt={d}&todt={d}"


def amfi_navs(d: date) -> dict:
    r = httpx.get(URL.format(d=d.strftime("%d-%b-%Y")), timeout=120, follow_redirects=True)
    r.raise_for_status()
    out = {}
    for line in r.text.splitlines():
        p = line.split(";")
        if len(p) >= 8 and p[0].isdigit():
            try:
                out[int(p[0])] = float(p[6])
            except ValueError:
                pass
    return out


def nearest_weekday(d: date) -> date:
    while d.weekday() >= 5:
        d -= timedelta(days=1)
    return d


def main(dates):
    db = SessionLocal()
    schemes = {s.scheme_id: s for s in db.query(MutualFundScheme).filter(MutualFundScheme.is_active == True)}  # noqa: E712
    total = bad = 0
    for d in dates:
        ref = amfi_navs(d)
        if not ref:
            print(f"{d}: AMFI returned no data (holiday?) - skipped")
            continue
        ours = {(r.scheme_id): float(r.nav) for r in db.query(SchemeNAVData).filter(SchemeNAVData.time == d)}
        cmp = mism = 0
        examples = []
        for sid, nav in ours.items():
            a = ref.get(schemes[sid].amfi_code) if sid in schemes else None
            if a is None:
                continue
            cmp += 1
            if abs(nav - a) / a > 1e-4:
                mism += 1
                if len(examples) < 5:
                    examples.append((schemes[sid].scheme_name[:45], nav, a))
        print(f"{d}: compared {cmp}, mismatched {mism}")
        for e in examples:
            print("   ", e)
        total += cmp
        bad += mism
    rate = bad / total if total else 0
    print(f"TOTAL compared {total}, mismatch rate {rate:.3%}")
    sys.exit(1 if total and rate > 0.005 else 0)


if __name__ == "__main__":
    args = [nearest_weekday(datetime.strptime(a, "%Y-%m-%d").date()) for a in sys.argv[1:]]
    if not args:
        today = date.today()
        args = [nearest_weekday(today - timedelta(days=365 * y + 3)) for y in (1, 3, 5)]
    main(args)
