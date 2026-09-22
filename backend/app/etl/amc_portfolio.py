"""Official holdings + SEBI Riskometer from AMC monthly portfolio disclosures.

Each AMC publishes one workbook per month: one sheet per scheme with the full portfolio, and a
Riskometer that is an *image* (a dial with the level printed in its caption). We identify the dial
by the SHA of its bytes against a table that was verified by eye (one entry per level per AMC).
An image not in the table is reported as unrecognised and NEVER guessed, so a redesigned dial
degrades to "no official Riskometer", not to a wrong one.

Adapters: nippon. (HDFC blocks scripted access; SBI/ICICI load files via JavaScript. Not done.)
"""
import hashlib
import html
import io
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


def _load_workbook(path: str, **kw):
    """openpyxl.load_workbook, but immune to a stale file extension.

    openpyxl decides whether to even attempt a file purely from os.path.splitext(path) - it
    never looks at the actual bytes - so an AMC that publishes modern zip-based XLSX content
    under a ".xls" URL (Bajaj Finserv does this) gets unconditionally rejected with "does not
    support the old .xls file format", even though the content is perfectly readable. Passing a
    file object instead of a path string skips that extension check entirely (openpyxl only
    branches on it for path-like input), which is exactly what we want since _sheet_dials
    already opens the same file via zipfile.ZipFile(path) - content-based, extension-agnostic -
    so the two would otherwise disagree about whether the file is parseable.
    """
    # BytesIO rather than a bare file object: several call sites use read_only=True, which reads
    # worksheet data lazily well after this function returns, so the underlying stream must
    # outlive the call - an in-memory buffer does that safely without leaking an open fd.
    with open(path, "rb") as f:
        buf = io.BytesIO(f.read())
    return openpyxl.load_workbook(buf, **kw)

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
    # Verified 2026-09-22 against 31-Aug-2026 disclosure. ICICI's dial (unlike Baroda/Helios)
    # carries only the level text, not the scheme name, so it IS a small reusable set (only 8
    # distinct images across all 147 scheme files, matching one-file-per-scheme like Helios).
    "icici": {
        "7eeff85e51e769a4ab604b704cc5b3f9": "Low",
        "99a0492738a753a28f6fcfd46c270495": "Low to Moderate",
        "66c0cadfc48747ae4bac27983bc46123": "Moderate",
        "08f133c1f1b22b80900962bc6f8fbf6f": "Moderately High",
        "24704776335646f8afff4b0a37131ca5": "High",
        "9865a9ce8e1f7956f554467c018fca24": "Very High",
    },
    # Verified 2026-09-22 against 31-Aug-2026 disclosure. Kotak re-renders the dial slightly
    # differently per scheme (font/needle antialiasing varies), so this is a wider table (18
    # entries for 6 levels) than Nippon/DSP/Axis, but every entry was viewed and none are guessed;
    # one further image (labelled "Benchmark Risk-o-meter") was excluded on purpose since it is
    # never the scheme's own level.
    "kotak": {
        "53d49cc6da0cdeb60160d919cb1fa15c": "Moderate",
        "4ba87e697bec493c9e894ef4f6190020": "Very High",
        "f8480a9bebafcda7708fe266353969e5": "Low",
        "48cdfbeb7dfe24b3e46239ee32c9529e": "High",
        "6974805f032dfee00f4614e8af8567f6": "Moderate",
        "97119823c663f19e5b809e0015efa3e9": "Moderate",
        "595ab3281958b7f5ef05d3dd91edec2e": "Moderate",
        "638ae36ba2fe191d69df002c1cfdbcdc": "Moderately High",
        "85f48f872425ee9136cbeb173eedf58e": "Low to Moderate",
        "3cb77ffdf66b971b1c230e536aa39554": "Moderately High",
        "ac96b6eacb3bd64dbcb47597144074a7": "Moderate",
        "f0d34ff96d2a1ad7409dc8a6bb270347": "Moderate",
        "e132e6b4964eec8c145eec576366dad8": "Moderate",
        "fd6e3df182571dd17f2537818035c5eb": "Moderately High",
        "a7a26ad96362537c858670f1f2b0618b": "Moderate",
        "f296081a2de8c09c24ca3b6e2c8370f1": "Low",
        "6aab55339cad38318a1e3594b65f600f": "Low to Moderate",
        "28f5cdad699881ef412c088548a4994d": "Moderate",
    },
    # Verified 2026-09-22 against 31-Aug-2026 disclosure.
    "franklin": {
        "28dcf6a2149859802f2f2fc1c14c0eaa": "Very High",
        "66b2f5475ab9a8adde6614cd38175ab6": "Low to Moderate",
        "7f1d0977728fb25b56e58db5e0ce626a": "Low",
        "9a35f63e58a4ee8aa6a7dfc88a0b9a27": "High",
        "bce797fb4104cc60590b59bcb4cd447f": "Moderately High",
        "f7a7f23a4ea53a803718a27ea5bd654c": "Moderate",
    },
    # Verified 2026-09-22 against 31-Aug-2026 disclosure. Only 5 of 6 levels appeared among
    # Motilal Oswal's schemes this month; "Moderately High" is absent, not guessed.
    "motilal": {
        "7b52146a887ca5689dfdd952ac77cd11": "Very High",
        "8725f9348eee56031f6ffe03c4c157f0": "Moderate",
        "9f3786c8d06fd28335db1eac1fca5438": "Low to Moderate",
        "be16cbb8be1f5e12f2e4f53481403ffe": "Low",
        "d3c42615d2ead5ed0b70af77a83366a8": "High",
    },
    # Verified 2026-09-22 against 31-Aug-2026 disclosure. Only 4 of 6 scheme levels appeared (the
    # other 2 distinct images were benchmark-labelled and excluded, not guessed as scheme levels).
    "iti": {
        "9642e4dc910baf9bd7c2cab91976506a": "Low",
        "a4fdad39958201315fcbf64c48ca4b88": "Low",
        "cb329fcfedb25e55ce16527cd1bc6636": "Very High",
        "eb217fdb024efb3cacbfab27b7ac7137": "Low to Moderate",
    },
    # Verified 2026-09-22 against 31-Aug-2026 disclosure (quantmutual.com, 29 sheets, 5 distinct dials).
    "quant": {
        "5ecfa70da1032387e4301afb6f30d122": "Very High",
        "7d8365e243b158c33ffdbed5e91addca": "High",
        "b5b97ed4b7924720b56d663b46476ef6": "Low",
        "b7641d009ac36217722c83b3116fb07c": "Moderate",
        "39461309437cd41c8491c20a593071b1": "Low to Moderate",
    },
    # Verified 2026-09-22 against 31-Aug-2026 disclosure (sundarammutual.com, 2 files - equity
    # (31 sheets) + debt (11 sheets) - 6 distinct dials; "Moderate" has two slightly different
    # renderings (equity-file vs debt-file template) that both read "Moderate" by eye.
    "sundaram": {
        "7b6d53e9a04ee038a0677f8829393714": "Very High",
        "7e571a2b95d57e185984c8e3a944e260": "High",
        "edd39b5c614e5d7e7a76e9e996d22b9f": "Moderate",
        "8fb011ca140bfb8a65b8c459a6ac1dc1": "Low",
        "aa0e74faa8dcbeedfde29451dd58c323": "Low to Moderate",
        "4f9e23311fcaba12998b4f55362001f5": "Moderate",
    },
    # Verified 2026-09-22 against 31-Aug-2026 disclosure (bajajamc.com, .xls URL but modern
    # zip-based XLSX content - see _load_workbook - 25 sheets, 4 distinct scheme dials; a 5th
    # image is a BENCHMARK dial, correctly excluded, not guessed).
    "bajaj": {
        "87aa183c4c0e9b38d403011dc3ce3cab": "Very High",
        "9175623ebc237835c4f983ad20192135": "Low",
        "d53af50563d2fae639b09db47e03fdca": "Low to Moderate",
        "cbafe7dcbc7bcf15802047ef21c6579f": "Moderate",
    },
    # Verified 2026-09-22 against 31-Aug-2026 disclosure (360.one, 12 sheets, 5 distinct dials).
    "360one": {
        "64394bbcec6a4ec4342e125b8a0d295d": "Very High",
        "bf0e575695c3694bb115b79180c522b3": "High",
        "94a73b65f86b400ed37e8e5c7bee07ed": "Moderately High",
        "be70b4cf27b346e04d0e0d66727fa0a4": "Low to Moderate",
        "771b7c30714f206c70159c13e5fdccb7": "Low",
    },
    # Verified 2026-09-22 against 31-Aug-2026 disclosure (mahindramanulife.com, 27 sheets, 5
    # distinct dials). Site publishes several months under GUID-named URLs with no date in the
    # filename - had to open each and read the embedded "as on" date to find the right one.
    "mahindra": {
        "f1cbf5c5592a1100d5e23425bcc4f445": "Very High",
        "6177730cd6250d73c8f9b9c42a2f1231": "Moderate",
        "e32fa4a5d39fcfb29c8f51ae3e7e4c0b": "Moderately High",
        "42c68ddb92ce0a37089834c6ac3010b6": "Low to Moderate",
        "d914d1cd87b7f6a0cbf7908d3ea28644": "Low",
    },
    # Verified 2026-09-22 against 31-Aug-2026 disclosure (unifimf.com, one file per scheme).
    # Unifi Dynamic Asset Allocation Fund's dial (hash 645e5732062dbcddde60ece5b1edb912) is
    # deliberately NOT in this table: its needle sits right at the Moderate/Moderately-High
    # boundary and is genuinely ambiguous by eye, so it is left unrecognised rather than guessed.
    "unifi": {
        "fbc6b986fb3a10d4c74676c5bd5f7536": "Very High",
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
    # unescape: workbook.xml XML-escapes the name attribute (e.g. "qL&amp;MF"), but openpyxl's
    # wb.sheetnames (what parse_workbook looks callers' sheet names up with) returns it decoded
    # ("qL&MF") - without this, any sheet name containing &, <, >, ' or " silently loses its
    # dial lookup to a dict-key mismatch. Found via quant's "qL&MF" sheet.
    sheets = [(html.unescape(n), rid) for n, rid in
              re.findall(r'<sheet [^>]*name="([^"]+)"[^>]*r:id="([^"]+)"', wbx)]
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
                r"<xdr:from><xdr:col>(\d+)</xdr:col><xdr:colOff>(\d+)</xdr:colOff><xdr:row>(\d+)</xdr:row><xdr:rowOff>(\d+)</xdr:rowOff>.*?r:embed=\"([^\"]+)\"",
                drx, re.S)
            rr = z.read(f"xl/drawings/_rels/{dr}.rels").decode()
            emb = {}
            for rel in re.findall(r"<Relationship [^>]*>", rr):
                i, t = re.search(r'Id="([^"]+)"', rel), re.search(r'Target="([^"]+)"', rel)
                if i and t and "media/" in t.group(1):
                    emb[i.group(1)] = t.group(1).split("media/")[-1]
            # Sort by cell position (row, col) first - that's the real "topmost, then leftmost"
            # signal - and only fall back to the sub-cell pixel offset (rowOff, colOff) to break
            # a tie between two images anchored in the exact same cell (found via Bajaj Finserv,
            # whose scheme + benchmark dials for one sheet are both anchored at row 125 col 1,
            # distinguished only by colOff). rowOff/colOff must NOT outrank (row, col): two
            # images in different cells can differ by a sub-pixel rowOff (tens of thousands of
            # EMU, noise-level) while very much NOT being vertically tied, and comparing that
            # first previously picked a benchmark dial one column to the right of the real scheme
            # dial, because its rowOff happened to be fractionally smaller.
            # A real riskometer dial (readable text on a filled arc) is always a substantial
            # image - every one verified across every AMC so far is 12.7 KB or more. Found via
            # 360 ONE: a sheet had a tiny (2 KB, 117x20px) decorative .emf anchored above the
            # real dial, which won the topmost-then-leftmost sort purely on position despite
            # obviously not being a dial at all. 5 KB is comfortably below every genuine dial
            # seen and comfortably above this decorative element, so filtering candidates below
            # it out before the position sort can only remove non-dial clutter.
            cands = sorted(((int(rw), int(c), int(roff), int(coff)), emb[r])
                            for c, coff, rw, roff, r in anchors
                            if r in emb and len(z.read("xl/media/" + emb[r])) >= 5000)
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
        has_name = any("name of the instrument" in c or "name of instrument" in c or "instrument name" in c for c in cells)
        if any("isin" in c for c in cells) and has_name:
            hdr = i
            # first match wins for each field: some AMCs have a second, unrelated column whose
            # long header text happens to also contain a field's keyword (e.g. Franklin's
            # "Outstanding derivative exposure AS % TO NET ASSETS Long/(Short)" alongside the
            # real "% to Net Assets" column) - the real column is always the earliest one.
            for j, c in enumerate(cells):
                if "name" not in col and (("name of" in c and "instrument" in c) or "instrument name" in c): col["name"] = j
                elif "isin" not in col and (c.strip() == "isin" or c.strip().startswith("isin")): col["isin"] = j
                elif "sector" not in col and ("industry" in c or "rating" in c): col["sector"] = j
                elif "pct" not in col and ("% to nav" in c or "% to net asset" in c or "% to aum" in c
                                           or "% of net asset" in c or "% of nav" in c or "% of aum" in c): col["pct"] = j
            break
    if hdr is None or "pct" not in col or "name" not in col:
        return []

    sample = rows[hdr + 1:hdr + 40]
    isin_base, name_base = col.get("isin"), col.get("name")

    def hits_at(base: Optional[int], shift: int, ok) -> int:
        if base is None:
            return 0
        c = base + shift
        return sum(1 for r in sample if 0 <= c < len(r) and ok(r[c]))

    def is_isin(v) -> bool:
        return bool(v) and bool(ISIN_RE.match(str(v).strip()))

    def looks_like_name(v) -> bool:
        s = str(v or "").strip()
        return len(s) > 3 and any(ch.isalpha() for ch in s) and not ISIN_RE.match(s)

    # Some AMCs omit a leading column (e.g. an internal scrip code) from the header row, so the
    # header's column indices no longer line up with the data rows. Detect and correct that shift
    # by finding where the ISIN column actually validates; if none does, the file is unparseable.
    best_shift = max(range(-2, 3), key=lambda sh: hits_at(isin_base, sh, is_isin))
    # Floor of 3, not 5: a concentrated debt fund can legitimately hold only a handful of
    # securities (found via Bajaj Finserv Gilt Fund: 1 G-Sec + 3 T-Bills, 4 ISINs total in the
    # whole sheet) and was being silently rejected as 0 holdings. The header already had to
    # explicitly declare both "ISIN" and a name column before this function even runs, so a
    # small hit count here is corroborating evidence for a real, sparse portfolio, not pure
    # coincidence the way scanning an arbitrary unlabelled column would be.
    if hits_at(isin_base, best_shift, is_isin) < 3:
        return []
    # A merged/spanning header cell (e.g. "Name of Instrument" merged across several blank
    # columns) can throw the name column off by a different amount than ISIN, so it is aligned
    # independently rather than assumed to share ISIN's shift.
    best_name_shift = max(range(-3, 4), key=lambda sh: hits_at(name_base, sh, looks_like_name))
    if hits_at(name_base, best_name_shift, looks_like_name) <= hits_at(name_base, best_shift, looks_like_name):
        best_name_shift = best_shift
    col = {k: v + best_shift for k, v in col.items()}
    col["name"] = name_base + best_name_shift

    raw = []
    for r in rows[hdr + 1:]:
        # Stop at "Grand Total"/"Total Portfolio": some AMCs (e.g. Sundaram) append an unrelated
        # footnote table below it - a legacy defaulted-paper recovery accounting note, with its
        # own mini header ("NAME OF THE SECURITY", "Total CP Outstanding", ...) that happens to
        # put a numeric value in the same column position as "% to NAV". Scanning past the real
        # total picked that up as a holding (once even corrupting the whole sheet's scale
        # detection, since its huge raw value alone looked plausible as an already-scaled total).
        # A real portfolio's holdings always precede its own Grand Total line, so stopping there
        # is safe for every AMC, not just Sundaram, whether or not they have trailing footnotes.
        if any(str(c or "").strip().lower() in ("grand total", "total portfolio") for c in r):
            break
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
        weight = pct * scale
        # A single holding can never legitimately exceed the whole portfolio's own sanity bound
        # (105% of NAV) - if it does, this row isn't really a holding line. Found via Sundaram's
        # arbitrage-fund sheets, which append an unrelated recovery-accounting footnote table
        # below the real holdings (for a legacy defaulted CP) that happens to have a valid-
        # looking ISIN and a numeric value in the same column position, producing a nonsense
        # 212%-of-NAV "holding". This bound can't reject a genuine holding (one position's
        # weight is always <= the portfolio total, which is itself capped at 105%).
        if abs(weight) > 105:
            continue
        out.append({"isin": str(isin).strip(), "name": str(r[col["name"]]).strip()[:255],
                    "sector": (str(r[col["sector"]]).strip()[:120] if col.get("sector") is not None and col["sector"] < len(r) and r[col["sector"]] else None),
                    "weight_pct": weight})
    return out



_NAME_BOILERPLATE = re.compile(
    r"^(back to index|portfolio statement|monthly portfolio|registered office|cin\s*:|"
    r"an open|an close|\(an open|\(an close|investment manager|asset management|"
    r"[a-z ]+ mutual fund\s*\(?live schemes\)?$)", re.I)


def find_scheme_name(ws, max_row: int = 10) -> Optional[str]:
    """Scan the top of a scheme sheet for its name, skipping the boilerplate some AMCs (e.g.
    Motilal Oswal: 'Back to Index', registered-office block) put in the first row(s) instead.
    Prefers a candidate containing "Fund"/"Plan"/"Scheme"/"ETF"/"FOF" if one exists."""
    rows = list(ws.iter_rows(min_row=1, max_row=max_row, values_only=True))
    candidates = [str(c).strip() for r in rows for c in r
                 if c and len(str(c).strip()) > 8 and not str(c).strip().startswith("(")
                 and not _NAME_BOILERPLATE.match(str(c).strip())]
    if not candidates:
        return None
    def is_bare_amc_name(c: str) -> bool:
        return bool(re.match(r"^[A-Za-z. ]+\s+mutual\s+fund$", c.strip(), re.I))
    # "fof" (fund-of-funds) alongside "fund": without it, a genuine FoF scheme name ending
    # "...REITs FOF" didn't match this preference list, while a LATER row - its one holding, the
    # underlying fund it invests in, which will almost always literally contain the word "Fund" -
    # did, and won by being the only "fundish" candidate. Found via Mahindra Manulife Asia
    # Pacific REITs FOF, whose only holding is "Manulife Global Fund SICAV-Asia Pacific REIT".
    fundish = [c for c in candidates if re.search(r"\b(fund|fof|plan|scheme|etf)\b", c, re.I) and not is_bare_amc_name(c)]
    return (fundish or [c for c in candidates if not is_bare_amc_name(c)] or candidates)[0]


def parse_workbook(path: str, amc: str = "nippon") -> List[dict]:
    z = zipfile.ZipFile(path)
    dials = _sheet_dials(z)
    table = DIALS[amc]
    wb = _load_workbook(path, read_only=True, data_only=True)
    out = []
    for sn in wb.sheetnames:
        if sn.lower() == "index":
            continue
        ws = wb[sn]
        name = find_scheme_name(ws)
        if not name:
            continue
        h = dials.get(sn)
        out.append({"sheet": sn, "scheme": clean_scheme_name(name),
                    "holdings": parse_holdings(ws),
                    "riskometer": table.get(h) if h else None,
                    "riskometer_unrecognised": bool(h) and h not in table})
    return out


def clean_scheme_name(name: str) -> str:
    """Strip the wrapper text some AMCs (e.g. Kotak: "Portfolio of X as on 31-Aug-2026") put
    around the bare scheme name, and the usual trailing description in parentheses or after a
    dash (e.g. 360 ONE: "360 ONE Dynamic Term Fund -  An Open Ended Dynamic Term Scheme
    investing across duration. A relatively high interest rate risk..." - the long SEBI-mandated
    category/risk descriptor after " - " was left unstripped and matched nothing in our DB,
    whose AMFI-sourced names instead use that same dash for " - Direct Plan - Growth")."""
    n = name.strip()
    n = re.sub(r"^portfolio\s+of\s+", "", n, flags=re.I)
    n = re.sub(r"\s+as\s+on\s+.*$", "", n, flags=re.I)
    n = re.split(r"\s+\(", n, 1)[0].strip()
    return re.split(r"\s+-\s+", n, 1)[0].strip()


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

# Trust Mutual Fund: like Baroda, each sheet's dial+caption is baked into ONE unique image
# (11 sheets, 11 distinct hashes, no reuse) - read by eye against the 31-Aug-2026 disclosure.
# Must be re-verified by hand for later months, not reused blindly.
TRUST_RISK_AUG2026 = {
    "TMFLIQ": "Low to Moderate", "TMFST": "Low to Moderate", "TMFOF": "Low",
    "TMFMM": "Low to Moderate", "TMFCB": "Low to Moderate", "TMFFLEXI": "Very High",
    "TMFSCAP": "Very High", "TMFMCAP": "Very High", "TMFARB": "Low", "TMFMID": "Very High",
    "TMFLRMCF": "Very High",
}


def parse_workbook_manual_risk(path: str, sheet_risk: Dict[str, str]) -> List[dict]:
    """Like parse_workbook, but the Riskometer level comes from a hand-verified {sheet: level}
    map rather than an image hash table (for AMCs whose disclosure bakes captions into a
    per-scheme image, so there is no small reusable set of dial images to hash-match)."""
    wb = _load_workbook(path, read_only=True, data_only=True)
    out = []
    for sn in wb.sheetnames:
        if sn.lower() == "index":
            continue
        ws = wb[sn]
        name = find_scheme_name(ws)
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
    wb = _load_workbook(path, read_only=True, data_only=True)
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
    wb = _load_workbook(path, read_only=True, data_only=True)
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



def parse_single_scheme_workbook_hashed(path: str, amc: str) -> List[dict]:
    """Like parse_single_scheme_workbook, but the Riskometer comes from the DIALS hash table
    (for AMCs like ICICI that publish one file per scheme, but whose dial image carries only the
    level text, not the scheme name, so a small reusable hash set works)."""
    import zipfile as _zip
    z = _zip.ZipFile(path)
    dials = _sheet_dials(z)
    table = DIALS[amc]
    wb = _load_workbook(path, read_only=True, data_only=True)
    ws = wb[wb.sheetnames[0]]
    rows = list(ws.iter_rows(min_row=1, max_row=6, values_only=True))
    # ICICI's layout is fixed: row 0 = AMC name, row 1 = scheme name, row 2 = "Portfolio as on ..."
    candidates = [str(c) for r in rows for c in r if c and len(str(c)) > 8]
    name = next((c for c in candidates if c.strip().lower() != "icici prudential mutual fund"
                and not c.lower().startswith("portfolio as")), None)
    if not name:
        return []
    scheme = re.split(r"\s+\(", name.strip(), 1)[0]
    h = dials.get(wb.sheetnames[0])
    return [{"sheet": wb.sheetnames[0], "scheme": scheme, "holdings": parse_holdings(ws),
            "riskometer": table.get(h) if h else None, "riskometer_unrecognised": bool(h) and h not in table}]


def parse_single_scheme_workbook_hashed_generic(path: str, amc: str) -> List[dict]:
    """Like parse_single_scheme_workbook_hashed, but for an AMC (e.g. Unifi) whose sheet layout
    doesn't follow ICICI's fixed row order - uses the same general find_scheme_name/
    clean_scheme_name machinery as the multi-sheet parse_workbook instead."""
    z = zipfile.ZipFile(path)
    dials = _sheet_dials(z)
    table = DIALS[amc]
    wb = _load_workbook(path, read_only=True, data_only=True)
    ws = wb[wb.sheetnames[0]]
    name = find_scheme_name(ws)
    if not name:
        return []
    h = dials.get(wb.sheetnames[0])
    return [{"sheet": wb.sheetnames[0], "scheme": clean_scheme_name(name), "holdings": parse_holdings(ws),
            "riskometer": table.get(h) if h else None, "riskometer_unrecognised": bool(h) and h not in table}]


def import_amc(db, amc_key: str, amc_name_like: str, paths: List[str], as_of: date, source_label: str) -> dict:
    """Shared import path for any fund house: parse each workbook, match by name, load holdings
    and Riskometer. `paths` may be several files (e.g. one AMC often splits equity/debt/FoF)."""
    parsed = []
    for path in paths:
        parsed += parse_workbook(path, amc_key)
    return _import_parsed(db, amc_name_like, parsed, as_of, source_label)


def import_amc_manual_risk(db, amc_name_like: str, paths: List[str], sheet_risk: Dict[str, str],
                            as_of: date, source_label: str) -> dict:
    """Like import_amc, for a baked-caption AMC (e.g. Baroda, Trust) parsed with
    parse_workbook_manual_risk instead of the image-hash table."""
    parsed = []
    for path in paths:
        parsed += parse_workbook_manual_risk(path, sheet_risk)
    return _import_parsed(db, amc_name_like, parsed, as_of, source_label)


def _import_parsed(db, amc_name_like: str, parsed: List[dict], as_of: date, source_label: str) -> dict:
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
