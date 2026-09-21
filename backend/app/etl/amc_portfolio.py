"""Official holdings + SEBI Riskometer from AMC monthly portfolio disclosures.

Each AMC publishes one workbook per month: one sheet per scheme with the full portfolio, and a
Riskometer that is an *image* (a dial with the level printed in its caption). We identify the dial
by the SHA of its bytes against a table that was verified by eye (one entry per level per AMC).
An image not in the table is reported as unrecognised and NEVER guessed, so a redesigned dial
degrades to "no official Riskometer", not to a wrong one.

Adapters: nippon. (HDFC blocks scripted access; SBI/ICICI load files via JavaScript. Not done.)
"""
import hashlib
import logging
import re
import zipfile
from datetime import date, datetime
from typing import Dict, List, Optional

import httpx
import openpyxl

from app.db.models import MutualFundScheme, SchemeHolding
from app.etl.master_data import norm_name

logger = logging.getLogger(__name__)

# md5 of the *scheme* dial image -> level (verified by viewing each image's printed caption)
DIALS = {
    "nippon": {
        "ae1b962985cd737977f46d9a0ee7985f": "Low",
        "124cb3a8dd58c981d78b9718a08b4db7": "Low to Moderate",
        "3ef15b40760d44e9ad78985cd698f535": "Moderate",
        "680ea1a8cd8e498472e4de667655c206": "Moderately High",
        "4c277ee2c5204cd59b1e30859e13e31c": "High",
        "1c2084171efd47909f7b625137954611": "Very High",
    }
}
NIPPON_BASE = "https://mf.nipponindiaim.com"
NIPPON_PAGE = NIPPON_BASE + "/investor-service/downloads/factsheet-portfolio-and-other-disclosures"
UA = {"User-Agent": "Mozilla/5.0"}
ISIN_RE = re.compile(r"^IN[A-Z0-9]{10}$")
MONTHS = {m: i for i, m in enumerate(["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"], 1)}


def latest_nippon_monthly_url() -> tuple:
    html = httpx.get(NIPPON_PAGE, headers=UA, timeout=60, follow_redirects=True).text
    best = None
    for path in set(re.findall(r'href="(/InvestorServices/FactsheetsDocuments/[^"]*MONTHLY[^"]*\.xlsx?)"', html, re.I)):
        m = re.search(r"(\d{1,2})[-_ ]?([A-Za-z]{3})[A-Za-z]*[-_ ]?(\d{2,4})", path.rsplit("/", 1)[-1])
        if not m or m.group(2).lower() not in MONTHS:
            continue
        yr = int(m.group(3)) + (2000 if len(m.group(3)) == 2 else 0)
        d = date(yr, MONTHS[m.group(2).lower()], 1)
        if best is None or d > best[0]:
            best = (d, path)
    if not best:
        raise RuntimeError("no monthly portfolio file found on Nippon page")
    return best[0], NIPPON_BASE + best[1]


def _sheet_dials(z: zipfile.ZipFile) -> Dict[str, Optional[str]]:
    """sheet name -> md5 of the image anchored in the *scheme* dial position (left-most)."""
    wbx = z.read("xl/workbook.xml").decode()
    rels = z.read("xl/_rels/workbook.xml.rels").decode()
    sheets = re.findall(r'<sheet [^>]*name="([^"]+)"[^>]*r:id="([^"]+)"', wbx)
    rid2t = {}
    for rel in re.findall(r"<Relationship [^>]*>", rels):
        i, t = re.search(r'Id="([^"]+)"', rel), re.search(r'Target="([^"]+)"', rel)
        if i and t:
            rid2t[i.group(1)] = t.group(1)
    out = {}
    names = set(z.namelist())
    for name, rid in sheets:
        target = rid2t[rid].lstrip("/")
        path = target if target.startswith("xl/") else "xl/" + target
        srels = "xl/worksheets/_rels/" + path.rsplit("/", 1)[-1] + ".rels"
        out[name] = None
        if srels not in names:
            continue
        for dr in re.findall(r"drawings/(drawing\d+\.xml)", z.read(srels).decode()):
            drx = z.read("xl/drawings/" + dr).decode()
            anchors = re.findall(r"<xdr:from><xdr:col>(\d+)</xdr:col>.*?</xdr:from>.*?r:embed=\"([^\"]+)\"", drx, re.S)
            rr = z.read(f"xl/drawings/_rels/{dr}.rels").decode()
            emb = {}
            for rel in re.findall(r"<Relationship [^>]*>", rr):
                i, t = re.search(r'Id="([^"]+)"', rel), re.search(r'Target="([^"]+)"', rel)
                if i and t and "media/" in t.group(1):
                    emb[i.group(1)] = t.group(1).split("media/")[-1]
            cands = sorted((int(c), emb[r]) for c, r in anchors if r in emb)
            if cands:  # left-most image = scheme dial, next = benchmark dial
                out[name] = hashlib.md5(z.read("xl/media/" + cands[0][1])).hexdigest()
    return out


def _num(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def parse_holdings(ws) -> List[dict]:
    rows = list(ws.iter_rows(values_only=True))
    hdr, col = None, {}
    for i, r in enumerate(rows[:15]):
        cells = [str(c or "").lower() for c in r]
        if any("isin" in c for c in cells) and any("name of the instrument" in c for c in cells):
            hdr = i
            for j, c in enumerate(cells):
                if "name of the instrument" in c: col["name"] = j
                elif "isin" in c: col["isin"] = j
                elif "industry" in c or "rating" in c: col["sector"] = j
                elif "% to nav" in c: col["pct"] = j
            break
    if hdr is None or "pct" not in col or "name" not in col:
        return []
    out = []
    for r in rows[hdr + 1:]:
        isin = r[col["isin"]] if col.get("isin") is not None and col["isin"] < len(r) else None
        pct = _num(r[col["pct"]]) if col["pct"] < len(r) else None
        if not (isin and ISIN_RE.match(str(isin).strip())) or pct is None:
            continue
        out.append({"isin": str(isin).strip(), "name": str(r[col["name"]]).strip()[:255],
                    "sector": (str(r[col["sector"]]).strip()[:120] if col.get("sector") is not None and col["sector"] < len(r) and r[col["sector"]] else None),
                    "weight_pct": pct * 100})  # file stores fractions of NAV
    return out


def parse_workbook(path: str, amc: str = "nippon") -> List[dict]:
    z = zipfile.ZipFile(path)
    dials = _sheet_dials(z)
    table = DIALS[amc]
    wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
    out = []
    for sn in wb.sheetnames:
        if sn.lower() == "index":
            continue
        ws = wb[sn]
        first = next(ws.iter_rows(min_row=1, max_row=1, values_only=True), ())
        name = next((str(c) for c in first[1:3] if c and len(str(c)) > 8), None)
        if not name:
            continue
        h = dials.get(sn)
        out.append({"sheet": sn, "scheme": re.split(r"\s+\(", name.strip(), 1)[0],
                    "holdings": parse_holdings(ws),
                    "riskometer": table.get(h) if h else None,
                    "riskometer_unrecognised": bool(h) and h not in table})
    return out


def import_nippon(db, path: str = None, as_of: date = None) -> dict:
    if path is None:
        as_of, url = latest_nippon_monthly_url()
        path = f"/tmp/nippon_{as_of:%Y%m}.xlsx"
        r = httpx.get(url, headers=UA, timeout=300, follow_redirects=True)
        r.raise_for_status()
        open(path, "wb").write(r.content)
    parsed = parse_workbook(path)
    index = {}
    for s in db.query(MutualFundScheme).filter(MutualFundScheme.is_active == True, MutualFundScheme.amc_name.ilike("%nippon%")):  # noqa: E712
        index.setdefault(norm_name(s.scheme_name), []).append(s)
    stats = {"sheets": len(parsed), "matched": 0, "unmatched": [], "ambiguous": [], "holdings_rejected": [],
             "riskometer_set": 0, "riskometer_unrecognised": 0}
    src = f"Nippon India MF monthly portfolio {as_of:%b %Y}"
    for p in parsed:
        cands = index.get(norm_name(p["scheme"]), [])
        if not cands:
            stats["unmatched"].append(p["scheme"][:60])
            continue
        if len(cands) > 1:
            # same name twice = the original scheme plus a later segregated-portfolio scheme;
            # the original is the one with the lowest AMFI code
            stats["ambiguous"].append(p["scheme"][:60])
            cands.sort(key=lambda x: x.amfi_code)
        s = cands[0]
        stats["matched"] += 1
        if p["riskometer"]:
            s.riskometer, s.riskometer_as_of, s.riskometer_source = p["riskometer"], as_of, src
            stats["riskometer_set"] += 1
        elif p["riskometer_unrecognised"]:
            stats["riskometer_unrecognised"] += 1
        total = sum(h["weight_pct"] for h in p["holdings"])
        if p["holdings"] and 30 <= total <= 105:   # a real portfolio is mostly invested and never exceeds NAV
            db.query(SchemeHolding).filter(SchemeHolding.scheme_id == s.scheme_id).delete()
            for h in p["holdings"]:
                db.add(SchemeHolding(scheme_id=s.scheme_id, as_of=as_of, source=src, **h))
        elif p["holdings"]:
            stats["holdings_rejected"].append((p["scheme"][:40], round(total, 1)))
    db.commit()
    return stats
