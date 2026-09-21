"""Authoritative scheme master data.

Sources (both official / AMFI-derived, no name-keyword guessing):
  * AMFI NAVAll.txt  -> SEBI category, AMC, ISIN, current NAV + date, "is the scheme still alive"
  * AMFI TER disclosure (republished daily as CSV by captn3m0/india-mutual-fund-ter-tracker)
    -> real Direct-plan total expense ratio

Anything we cannot verify stays NULL / flagged instead of being filled with a default.
"""
import csv
import io
import logging
import re
from datetime import date, datetime, timedelta

import httpx

from app.db.models import MutualFundScheme

logger = logging.getLogger(__name__)

AMFI_NAVALL_URLS = [
    "https://portal.amfiindia.com/spages/NAVAll.txt",
    "https://www.amfiindia.com/spages/NAVAll.txt",
]
TER_CSV_URL = "https://raw.githubusercontent.com/captn3m0/india-mutual-fund-ter-tracker/main/data.csv"


def bucket_from_sebi(sebi_category: str, open_ended: bool = True) -> str:
    """Map an official SEBI category string to the app's simplified buckets."""
    if not open_ended:
        return "Other"  # closed-ended / interval plans: fixed tenure, not comparable
    c = sebi_category.lower()
    if "elss" in c:
        return "ELSS"
    if "large & mid" in c or "large and mid" in c:
        return "Mid Cap"
    if "small cap" in c:
        return "Small Cap"
    if "mid cap" in c:
        return "Mid Cap"
    if "large cap" in c:
        return "Large Cap"
    if any(x in c for x in ("flexi cap", "multi cap", "focused", "value", "contra", "dividend yield")):
        return "Flexi Cap"
    if "sectoral" in c or "thematic" in c:
        return "Sectoral"
    if c.startswith("hybrid") or "arbitrage" in c or "equity savings" in c:
        return "Hybrid"
    if c.startswith("debt") or "income/debt" in c or "gilt" in c:
        return "Debt"
    if "index fund" in c:
        return "Index"
    return "Other"  # FoFs, ETFs, solution-oriented, unknown


def parse_navall(text: str):
    """Yield dicts for every scheme row in NAVAll.txt with its section context."""
    sebi_category, open_ended, amc = None, True, None
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("Scheme Code"):
            continue
        if ";" not in line:
            m = re.match(r"^(Open Ended|Close Ended|Interval Fund)[^()]*\((.*)\)$", line)
            if m:
                open_ended = m.group(1) == "Open Ended"
                sebi_category = m.group(2).strip()
            else:
                amc = line
            continue
        parts = line.split(";")
        if len(parts) < 8:
            continue
        code, isin_g, isin_r, name, plan, option, nav, dt = [p.strip() for p in parts[:8]]
        try:
            nav_v = float(nav)
            nav_d = datetime.strptime(dt, "%d-%b-%Y").date()
        except ValueError:
            continue  # "N.A." NAVs etc.
        yield {
            "amfi_code": int(code), "isin": isin_g if len(isin_g) == 12 else None, "name": name,
            "plan": plan, "option": option, "nav": nav_v, "date": nav_d,
            "amc": amc, "sebi_category": sebi_category, "open_ended": open_ended,
        }


def is_direct_growth(r) -> bool:
    n, p, o = r["name"].lower(), r["plan"].lower(), r["option"].lower()
    direct = p.startswith("direct") or (not p and "direct" in n)
    return direct and "growth" in (o + " " + n) and "idcw" not in o and "dividend" not in o


def fetch_navall() -> str:
    last = None
    for url in AMFI_NAVALL_URLS:
        try:
            r = httpx.get(url, timeout=90, follow_redirects=True)
            r.raise_for_status()
            if "Scheme Code" in r.text[:200]:
                return r.text
        except Exception as e:  # try next mirror
            last = e
    raise RuntimeError(f"AMFI NAVAll unavailable: {last}")


_STRIP = re.compile(r"\(.*?\)|\b(direct|regular|plan|growth|option|idcw|fund|scheme|the)\b|[^a-z0-9 ]")


def norm_name(name: str) -> str:
    return " ".join(_STRIP.sub(" ", name.lower().replace("&", " and ")).split())


def load_ter() -> dict:
    """normalized scheme name -> Direct plan total TER (%)."""
    r = httpx.get(TER_CSV_URL, timeout=60, follow_redirects=True)
    r.raise_for_status()
    out = {}
    for row in csv.DictReader(io.StringIO(r.text)):
        try:
            ter = float(row["Direct Plan - Total TER (%)"])
        except (KeyError, ValueError):
            continue
        if 0 < ter < 4:  # SEBI caps TER well under 3%; anything else is a parse error
            out[norm_name(row["Scheme Name"])] = ter
    return out


def refresh_master(db, add_new: bool = True) -> dict:
    text = fetch_navall()
    rows = {r["amfi_code"]: r for r in parse_navall(text)}
    newest = max(r["date"] for r in rows.values())
    alive_cutoff = newest - timedelta(days=10)
    ter_map = load_ter()
    stats = {"amfi_rows": len(rows), "as_of": newest.isoformat(), "updated": 0, "added": 0,
             "deactivated": 0, "ter_matched": 0, "ter_missing": 0}

    used_isins = {i for (i,) in db.query(MutualFundScheme.isin)}
    existing = {s.amfi_code: s for s in db.query(MutualFundScheme)}

    if add_new:
        for code, r in rows.items():
            if code in existing or not is_direct_growth(r) or not r["open_ended"]:
                continue
            isin = r["isin"] if r["isin"] and r["isin"] not in used_isins else f"INF{code:09d}"[:12]
            used_isins.add(isin)
            s = MutualFundScheme(
                amfi_code=code, isin=isin, scheme_name=r["name"], amc_name=r["amc"] or "Unknown",
                category="Other", plan_type="Direct", option_type="Growth",
                launch_date=r["date"], is_active=True, expense_ratio=0.0)
            db.add(s)
            existing[code] = s
            stats["added"] += 1

    for code, s in existing.items():
        r = rows.get(code)
        if r is None:
            # vanished from AMFI's live list: matured / merged / wound up
            s.is_active = False
            s.data_flags = _add_flag(s.data_flags, "not_in_amfi")
            stats["deactivated"] += 1
            continue
        if not is_direct_growth(r):
            # IDCW/Bonus/Regular options: NAV falls on payouts, so returns are not comparable
            s.is_active = False
            s.data_flags = _add_flag(s.data_flags, "not_direct_growth")
            stats["deactivated"] += 1
            continue
        s.data_flags = _drop_flag(s.data_flags, "not_direct_growth")
        s.option_type = "Growth"
        s.sebi_category = r["sebi_category"]
        s.category = bucket_from_sebi(r["sebi_category"] or "", r["open_ended"])
        if r["amc"]:
            s.amc_name = r["amc"]
        if r["isin"] and r["isin"] != s.isin and r["isin"] not in used_isins:
            used_isins.discard(s.isin)
            s.isin = r["isin"]
            used_isins.add(r["isin"])
        s.latest_nav_date = r["date"]
        s.is_active = r["date"] >= alive_cutoff
        s.data_flags = _drop_flag(_drop_flag(s.data_flags, "not_in_amfi"), "stale_nav")
        if not s.is_active:
            s.data_flags = _add_flag(s.data_flags, "stale_nav")
        ter = ter_map.get(norm_name(s.scheme_name))
        s.ter_pct = ter
        stats["ter_matched" if ter is not None else "ter_missing"] += 1
        stats["updated"] += 1
    db.commit()
    return stats


def _flags(s):
    return [f for f in (s or "").split(",") if f]


def _add_flag(s, flag):
    f = _flags(s)
    if flag not in f:
        f.append(flag)
    return ",".join(f)


def _drop_flag(s, flag):
    return ",".join(f for f in _flags(s) if f != flag) or None
