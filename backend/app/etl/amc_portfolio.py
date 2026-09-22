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

LEVELS = ("Low", "Low to Moderate", "Moderate", "Moderately High", "High", "Very High")

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
    },
    # Verified 2026-08-31: DSP stacks scheme dial above benchmark dial in the same column;
    # both sets of six levels present, each hash viewed and matched to its printed caption.
    "dsp": {
        "3ec8a2cdec8f83d56bc0990631306644": "Low",
        "ec9c5df1bbfe81ccd490d9d6036c09dd": "Low to Moderate",
        "387648944acf503f7dc84b0714fda310": "Moderate",
        "e8483b48a3a15a815beab0d2ee5d616f": "Moderately High",
        "d238f38a509dcf8df037ca91fde13aaa": "High",
        "537ffa356476b57da4a2026c0a1bb52f": "Very High",
        "b94d26277eb380200e652205b8fbe9d9": "Low",
        "6dfc8d280bb95aae9187201e85399bdd": "Low to Moderate",
        "7c7cf1bb4e73885ffe85f77436095fdf": "Moderate",
        "1fdb1ebe64e9c0dd96b55e8b85f014fd": "Moderately High",
        "8f2308c2fd0d5cd7c3f28d92ed0409ef": "High",
        "023be0fb0cf6ddddee524d7097d9dc22": "Very High",
    },
    # Verified 2026-09-22 against 31-May-2026 disclosure (Axis's site 404s on later months at
    # this URL pattern; label as_of accordingly). Only "scheme" dials shown here (12 images total,
    # scheme + benchmark, but only the scheme-side 6 are ever the topmost/scheme-position anchor).
    "axis": {
        "1416ceaaa7fe55839f591227757e6f74": "High",
        "204f02844f9aa74f38662a97b503f0ad": "Moderately High",
        "4da90b93dd57fcfee1b16fbe3e7c22f6": "Moderate",
        "9f763a4fc076cf78de67cd0c6ce991a7": "Low",
        "afd7231f2ac3db5033890bc27afe1e8c": "Low to Moderate",
        "ed553eccc425c96b178ad329be8568c0": "Very High",
    },
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
    """sheet name -> md5 of the image anchored in the *scheme* dial position.

    AMCs place the pair of dials differently (Nippon: side by side, scheme on the left; DSP:
    stacked, scheme on top), so we take whichever anchor is topmost-then-leftmost.
    """
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
            anchors = re.findall(
                r"<xdr:from><xdr:col>(\d+)</xdr:col><xdr:colOff>\d+</xdr:colOff><xdr:row>(\d+)</xdr:row>.*?r:embed=\"([^\"]+)\"",
                drx, re.S)
            rr = z.read(f"xl/drawings/_rels/{dr}.rels").decode()
            emb = {}
            for rel in re.findall(r"<Relationship [^>]*>", rr):
                i, t = re.search(r'Id="([^"]+)"', rel), re.search(r'Target="([^"]+)"', rel)
                if i and t and "media/" in t.group(1):
                    emb[i.group(1)] = t.group(1).split("media/")[-1]
            cands = sorted(((int(rw), int(c)), emb[r]) for c, rw, r in anchors if r in emb)
            if cands:  # topmost, then leftmost image = scheme dial
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
        cells = [" ".join(str(c or "").lower().split()) for c in r]  # collapse embedded newlines/spaces
        has_name = any("name of the instrument" in c or "name of instrument" in c for c in cells)
        if any("isin" in c for c in cells) and has_name:
            hdr = i
            for j, c in enumerate(cells):
                if "name of" in c and "instrument" in c: col["name"] = j
                elif c.strip() == "isin" or c.strip().startswith("isin"): col["isin"] = j
                elif "industry" in c or "rating" in c: col["sector"] = j
                elif "% to nav" in c or "% to net asset" in c or "% to aum" in c: col["pct"] = j
            break
    if hdr is None or "pct" not in col or "name" not in col:
        return []

    def hits(shift: int) -> int:
        c = col.get("isin")
        if c is None:
            return 0
        return sum(1 for r in rows[hdr + 1:hdr + 40]
                  if c + shift < len(r) and r[c + shift] and ISIN_RE.match(str(r[c + shift]).strip()))

    # Some AMCs omit a leading column (e.g. an internal scrip code) from the header row, so the
    # header's column indices no longer line up with the data rows. Detect and correct that shift
    # by finding where the ISIN column actually validates; if none does, the file is unparseable.
    best_shift = max(range(-1, 2), key=hits) if col.get("isin") is not None else 0
    if hits(best_shift) < 5:
        return []
    col = {k: v + best_shift for k, v in col.items()}

    raw = []
    for r in rows[hdr + 1:]:
        isin = r[col["isin"]] if col["isin"] < len(r) else None
        pct = _num(r[col["pct"]]) if col["pct"] < len(r) else None
        if not (isin and ISIN_RE.match(str(isin).strip())) or pct is None:
            continue
        raw.append((isin, r, pct))
    if not raw:
        return []
    # Most AMCs store the weight as a fraction of NAV (0.0232 = 2.32%); some (Helios) already
    # store the percentage itself (2.32). Pick whichever scaling makes the total look like a
    # real portfolio (roughly 30-105% of NAV) rather than assuming one convention.
    total_raw = sum(p for *_, p in raw)
    scale = 1 if 30 <= total_raw <= 105 else 100
    out = []
    for isin, r, pct in raw:
        out.append({"isin": str(isin).strip(), "name": str(r[col["name"]]).strip()[:255],
                    "sector": (str(r[col["sector"]]).strip()[:120] if col.get("sector") is not None and col["sector"] < len(r) and r[col["sector"]] else None),
                    "weight_pct": pct * scale})
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


# --- Baroda BNP Paribas: risk level + caption are baked into ONE image per scheme (not a small
# reusable set like Nippon/DSP), so there is no hash table to build. Each month's file needs this
# mapping re-read by eye from the images `_sheet_dials` finds (the topmost, largest .jpg per
# sheet). This snapshot was verified 2026-09-22 against the 31-Aug-2026 disclosure; it must be
# refreshed by hand for later months rather than reused blindly.
BARODA_RISK_AUG2026 = {
    "T0MD09": "Low to Moderate", "T0MD12": "Moderate", "T0MD13": "Low to Moderate",
    "T0MD28": "Low to Moderate", "T0ME02": "Very High", "T0ME04": "Very High",
    "T0ME05": "Very High", "T0ME08": "Moderately High", "T0ME18": "Low", "T0ME19": "Very High",
    "T0ME20": "Very High", "T0ME21": "Very High", "T0ME24": "Very High", "T0ME25": "Very High",
    "T0ME26": "Very High", "T0ME30": "Very High", "T0ME31": "High", "T0ME32": "Very High",
    "T0ME33": "Very High", "T0ME34": "Very High", "T0ME35": "Very High", "T0ME36": "Very High",
    "T0ME37": "Very High", "T0ME38": "Very High", "T0ME39": "Very High", "T0ME40": "Very High",
    "T0ME41": "Very High", "T0ME42": "Very High", "T0ME43": "Low to Moderate", "T0ME44": "High",
    "T0ME45": "Very High", "T0ME46": "High", "T0ME47": "Very High", "T0ME48": "Very High",
    "T0ME49": "Very High", "YR04": "Moderate", "YR07": "Low to Moderate", "YR11": "Very High",
    "YR15": "Very High", "YR29": "Low", "YR47": "Low to Moderate", "YR48": "Very High",
    "YR51": "Low", "YR52": "Low to Moderate", "YR53": "Moderately High", "YR54": "Very High",
    "YR56": "Very High",
}


def parse_workbook_manual_risk(path: str, sheet_risk: Dict[str, str]) -> List[dict]:
    """Like parse_workbook, but the Riskometer level comes from a hand-verified {sheet: level}
    map rather than an image hash table (for AMCs whose disclosure bakes captions into a
    per-scheme image, so there is no small reusable set of dial images to hash-match)."""
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
        level = sheet_risk.get(sn)
        out.append({"sheet": sn, "scheme": re.split(r"\s+\(", name.strip(), 1)[0],
                    "holdings": parse_holdings(ws),
                    "riskometer": level, "riskometer_unrecognised": level is None})
    return out


# --- Helios: one file per scheme (not one workbook with many sheets), riskometer baked into a
# single composite image per file like Baroda. Verified by eye 2026-09-22 against the
# 31-Aug-2026 monthly disclosures; needs re-reading by hand for later months.
HELIOS_RISK_AUG2026 = {
    "Helios Small Cap Fund": "Very High",
    "Helios Arbitrage Fund": "Low",
    "Helios Balanced Advantage Fund": "Very High",
    "Helios Financial Services Fund": "Very High",
    "Helios Flexi Cap Fund": "Very High",
    "Helios Large & Mid Cap Fund": "Very High",
    "Helios Mid Cap Fund": "Very High",
    "Helios Overnight Fund": "Low",
}


def parse_single_scheme_workbook(path: str, scheme_risk: Dict[str, str]) -> List[dict]:
    """AMCs (e.g. Helios) that publish one file per scheme rather than one workbook with many
    sheets. The scheme name is read from the sheet itself and matched against a hand-verified
    {scheme name: level} map."""
    wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
    ws = wb[wb.sheetnames[0]]
    rows = list(ws.iter_rows(min_row=1, max_row=6, values_only=True))
    name = None
    for r in rows:
        for c in r:
            if c and str(c).strip().lower().startswith("scheme name"):
                idx = r.index(c)
                rest = [x for x in r[idx + 1:] if x]
                if rest:
                    name = str(rest[0]).strip()
        if name:
            break
    if not name:  # fallback: first long text cell
        name = next((str(c) for r in rows for c in r if c and len(str(c)) > 8), None)
    if not name:
        return []
    scheme = re.split(r"\s+\(", name, 1)[0].strip()
    level = next((v for k, v in scheme_risk.items() if k.lower() == scheme.lower()), None)
    return [{"sheet": wb.sheetnames[0], "scheme": scheme, "holdings": parse_holdings(ws),
            "riskometer": level, "riskometer_unrecognised": level is None}]



# --- Tata: unlike every AMC so far, publishes ALL schemes' Riskometer levels as plain text in a
# single dedicated sheet ("Tata Scheme Risk-o-Meter") -- no image parsing needed at all, and this
# self-updates every month automatically (unlike Baroda/Helios's baked-in-image snapshots).
def parse_tata_workbook(path: str) -> List[dict]:
    wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
    risk_sheet = next((n for n in wb.sheetnames if "risk-o-meter" in n.lower() and "benchmark" not in n.lower() and "debt" not in n.lower()), None)
    levels = {}
    if risk_sheet:
        for r in wb[risk_sheet].iter_rows(values_only=True):
            if len(r) > 2 and r[1] and r[2] and str(r[2]).strip() in LEVELS:
                levels[str(r[1]).strip().lower()] = str(r[2]).strip()
    out = []
    for sn in wb.sheetnames:
        if "risk-o-meter" in sn.lower() or sn.lower() in ("index", "debt replication index", "dividend history"):
            continue
        ws = wb[sn]
        first = next(ws.iter_rows(min_row=1, max_row=6, values_only=True), ())
        name = next((str(c) for row in [first] for c in row if c and len(str(c)) > 8 and "tata" in str(c).lower()), None)
        if not name:
            continue
        scheme = re.split(r"\s+\(", name.strip(), 1)[0]
        level = levels.get(scheme.lower())
        out.append({"sheet": sn, "scheme": scheme, "holdings": parse_holdings(ws),
                    "riskometer": level, "riskometer_unrecognised": level is None})
    return out


def import_amc(db, amc_key: str, amc_name_like: str, paths: List[str], as_of: date, source_label: str) -> dict:
    """Shared import path for any fund house: parse each workbook, match by name, load holdings
    and Riskometer. `paths` may be several files (e.g. one AMC often splits equity/debt/FoF)."""
    parsed = []
    for path in paths:
        parsed += parse_workbook(path, amc_key)
    index = {}
    for sch in db.query(MutualFundScheme).filter(MutualFundScheme.is_active == True, MutualFundScheme.amc_name.ilike(f"%{amc_name_like}%")):  # noqa: E712
        index.setdefault(norm_name(sch.scheme_name), []).append(sch)
    stats = {"sheets": len(parsed), "matched": 0, "unmatched": [], "ambiguous": [], "holdings_rejected": [],
             "riskometer_set": 0, "riskometer_unrecognised": 0}
    src = source_label
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


def import_amc_multi_file(db, amc_name_like: str, paths: List[str], as_of: date, source_label: str, parser) -> dict:
    """Like import_amc, for AMCs (e.g. Helios) that publish one file per scheme instead of one
    workbook with many sheets. `parser(path)` must return the same shape as parse_workbook."""
    parsed = []
    for p in paths:
        parsed += parser(p)
    index = {}
    for sch in db.query(MutualFundScheme).filter(MutualFundScheme.is_active == True, MutualFundScheme.amc_name.ilike(f"%{amc_name_like}%")):  # noqa: E712
        index.setdefault(norm_name(sch.scheme_name), []).append(sch)
    stats = {"sheets": len(parsed), "matched": 0, "unmatched": [], "ambiguous": [], "holdings_rejected": [],
             "riskometer_set": 0, "riskometer_unrecognised": 0}
    for p in parsed:
        cands = index.get(norm_name(p["scheme"]), [])
        if not cands:
            stats["unmatched"].append(p["scheme"][:60])
            continue
        if len(cands) > 1:
            stats["ambiguous"].append(p["scheme"][:60])
            cands.sort(key=lambda x: x.amfi_code)
        s = cands[0]
        stats["matched"] += 1
        if p["riskometer"]:
            s.riskometer, s.riskometer_as_of, s.riskometer_source = p["riskometer"], as_of, source_label
            stats["riskometer_set"] += 1
        elif p["riskometer_unrecognised"]:
            stats["riskometer_unrecognised"] += 1
        total = sum(h["weight_pct"] for h in p["holdings"])
        if p["holdings"] and 30 <= total <= 105:
            db.query(SchemeHolding).filter(SchemeHolding.scheme_id == s.scheme_id).delete()
            for h in p["holdings"]:
                db.add(SchemeHolding(scheme_id=s.scheme_id, as_of=as_of, source=source_label, **h))
        elif p["holdings"]:
            stats["holdings_rejected"].append((p["scheme"][:40], round(total, 1)))
    db.commit()
    return stats
