"""NAV history straight from AMFI's own history report (no third-party mirror).

  https://portal.amfiindia.com/DownloadNAVHistoryReport_Po.aspx?mf=<id>&tp=1&frmdt=DD-Mon-YYYY&todt=DD-Mon-YYYY

One request per fund house returns every open-ended scheme it runs, all years, in a single
semicolon-separated file. We keep only the Direct-Growth schemes we track, reconcile them against
whatever is already stored (reporting disagreements), then replace the stored history.
"""
import logging
import os
import re
import tempfile
import time
from datetime import date, datetime, timedelta
from typing import Dict, Iterable, Optional, Set

import httpx
from sqlalchemy import text

from app.db.models import MutualFundScheme, SchemeNAVData
from app.etl.master_data import AMFI_SITE

logger = logging.getLogger(__name__)

HISTORY_URL = "https://portal.amfiindia.com/DownloadNAVHistoryReport_Po.aspx"
YEARS_KEPT = 11   # covers a 10-year horizon; keeps the database small enough for a free Postgres tier
ROW_RE = re.compile(r"^(\d+);")


def amfi_mf_ids() -> Dict[str, str]:
    """AMFI fund-house id -> name, read from the TER page's own dropdown."""
    page = httpx.get(f"{AMFI_SITE}/ter-of-mf-schemes", headers={"User-Agent": "Mozilla/5.0"}, timeout=60,
                     follow_redirects=True).text.replace('\\"', '"')
    ids = re.findall(r'"mfId":"(\d+)","mfName":"([^"]+)"', page)
    if not ids:
        raise RuntimeError("could not read fund house ids from AMFI")
    return dict(ids)


def download_history(mf_id: str, frm: date, to: date, dest: str) -> int:
    fmt = lambda d: d.strftime("%d-%b-%Y")
    params = {"mf": mf_id, "tp": "1", "frmdt": fmt(frm), "todt": fmt(to)}
    size = 0
    with httpx.stream("GET", HISTORY_URL, params=params, headers={"User-Agent": "Mozilla/5.0"}, timeout=600,
                      follow_redirects=True) as r:
        r.raise_for_status()
        with open(dest, "wb") as f:
            for chunk in r.iter_bytes(1 << 20):
                f.write(chunk)
                size += len(chunk)
    return size


def parse_history(path: str, wanted: Set[int]) -> Dict[int, Dict[date, float]]:
    """{amfi_code: {date: nav}} for the codes we track."""
    out: Dict[int, Dict[date, float]] = {}
    with open(path, encoding="utf-8", errors="ignore") as f:
        for line in f:
            m = ROW_RE.match(line)
            if not m:
                continue
            code = int(m.group(1))
            if code not in wanted:
                continue
            p = line.rstrip("\n").split(";")
            if len(p) < 8:
                continue
            try:
                out.setdefault(code, {})[datetime.strptime(p[7].strip(), "%d-%b-%Y").date()] = float(p[6])
            except ValueError:
                continue   # "N.A." NAVs and blanks
    return out


def replace_history(db, scheme: MutualFundScheme, series: Dict[date, float]) -> dict:
    """Reconcile against stored rows, then replace them with AMFI's series."""
    old = {t: float(n) for t, n in db.query(SchemeNAVData.time, SchemeNAVData.nav).filter(SchemeNAVData.scheme_id == scheme.scheme_id)}
    overlap = [d for d in series if d in old]
    mismatched = sum(1 for d in overlap if abs(old[d] - series[d]) > 1e-4 * max(series[d], 1e-9))
    db.execute(text("DELETE FROM scheme_nav_data WHERE scheme_id = :s"), {"s": scheme.scheme_id})
    db.bulk_insert_mappings(SchemeNAVData, [{"time": d, "scheme_id": scheme.scheme_id, "nav": v} for d, v in sorted(series.items())])
    return {"old_rows": len(old), "new_rows": len(series), "overlap": len(overlap), "mismatched": mismatched}


def rebuild_history(db, only_mf: Optional[Iterable[str]] = None, log=print) -> dict:
    today = date.today()
    frm = today.replace(year=today.year - YEARS_KEPT)
    tracked = {s.amfi_code: s for s in db.query(MutualFundScheme).filter(
        MutualFundScheme.is_active == True, MutualFundScheme.category != "Other")}  # noqa: E712
    ids = amfi_mf_ids()
    if only_mf:
        ids = {k: v for k, v in ids.items() if k in set(only_mf)}
    stats = {"fund_houses": 0, "schemes_replaced": 0, "rows": 0, "overlap": 0, "mismatched": 0,
             "mismatch_schemes": [], "missing": set(tracked)}
    for mf_id, name in ids.items():
        tmp = os.path.join(tempfile.gettempdir(), f"amfi_hist_{mf_id}.txt")
        series, size, err = None, 0, None
        for attempt in range(1, 4):           # AMFI occasionally resets long downloads
            try:
                size = download_history(mf_id, frm, today, tmp)
                series = parse_history(tmp, set(tracked))
                break
            except Exception as e:
                err = e
                log(f"[{mf_id}] {name}: attempt {attempt} failed: {e}")
                time.sleep(15 * attempt)
            finally:
                if os.path.exists(tmp):
                    os.remove(tmp)
        if series is None:
            log(f"[{mf_id}] {name}: GAVE UP ({err})")
            stats.setdefault("failed_fund_houses", []).append(name)
            continue
        stats["fund_houses"] += 1
        for code, ser in series.items():
            if len(ser) < 20:
                continue
            r = replace_history(db, tracked[code], ser)
            stats["schemes_replaced"] += 1
            stats["rows"] += r["new_rows"]
            stats["overlap"] += r["overlap"]
            stats["mismatched"] += r["mismatched"]
            stats["missing"].discard(code)
            if r["mismatched"]:
                stats["mismatch_schemes"].append((tracked[code].scheme_name[:45], r["mismatched"], r["overlap"]))
        db.commit()
        log(f"[{mf_id}] {name}: {size/1e6:.0f} MB, {len(series)} tracked schemes")
    stats["missing"] = sorted(stats["missing"])
    return stats
