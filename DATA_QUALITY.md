# Data quality and sources

Users make money decisions from this app, so every displayed number is either traceable to an
official source or clearly labelled as an estimate. Unknown is shown as "n/a", never a default.

| Data | Source | Notes |
|---|---|---|
| Scheme list, AMC, ISIN, SEBI category | AMFI `NAVAll.txt` (portal.amfiindia.com) | Direct + Growth + open-ended only; matured/merged schemes are inactive |
| NAV history | AMFI NAV history report (`portal.amfiindia.com/DownloadNAVHistoryReport_Po.aspx`), one request per fund house, last 11 years | Rebuilt entirely from AMFI on 2026-09-22 (2.25M rows, 57 fund houses). Old mfapi.in data agreed on 942,663 overlapping dates except 96 (0.01%). Independent check vs AMFI single-day reports: 3,142 compared, 0 mismatches (`scripts/verify_data.py`). mfapi.in is no longer used |
| Expense ratio (TER) | AMFI TER API (`/api/populate-te-rdata-revised`, one Excel per fund house), latest daily row | 1,441 of 1,481 active schemes (97%). Matched by normalised name; no match = "n/a", no fuzzy guessing. Falls back to captn3m0's CSV, which lags AMFI (e.g. Axis Small Cap: CSV 0.54% vs AMFI 0.71% on 18 Sep 2026) |
| Benchmark (beta, capture) | Nifty 50 price index, Yahoo Finance | Excludes dividends; cached daily in `backend/data/` |
| Risk level | Official SEBI Riskometer where imported, else a conservative estimate | See below. Every fund shows which one it is |
| Holdings / sector mix | AMC monthly portfolio disclosure (official) | 18 fund houses, 635 schemes (~36% of 1,776 active): ICICI Prudential (87), Kotak Mahindra (81), Nippon India (69), Axis (53), DSP (52), Tata (44), Baroda BNP Paribas (39), Franklin Templeton (34), Motilal Oswal (30), Sundaram (29), quant (27), Mahindra Manulife (24), Bajaj Finserv (20), ITI (18), Trust (10), 360 ONE (9), Helios (7), Unifi (2 of 3 - Liquid Fund's file wasn't discoverable). Others show "not imported yet". Earlier versions showed synthetic data |

## Validation applied to every NAV series (`app/engine/quality.py`)
- Zero/negative NAVs and isolated one-day spikes that reverse next day are dropped (`repaired_points`).
- An implausible persistent jump (>20% a day for equity, >5% debt, >12% hybrid) invalidates only the horizons whose window contains it (`nav_jump_old`); it blocks the whole scheme (`nav_jump`) only if it is within the last 12 months. A gap over 20 days or coverage under 80% also blocks the scheme. Blocked schemes get no analytics and are not recommended. Example: AMFI's own history has a 100x unit slip on Edelweiss Liquid in 2017.
- A horizon (1/3/5/10Y) is only computed if we hold that much history. Earlier code silently reused shorter history under a longer label.
- Inactive, matured, IDCW/bonus/regular options are excluded (their NAV drops on payouts, so returns are not comparable).

## Risk level (`app/engine/risk_level.py`)
Sharpe/Sortino are return per unit of risk and must never be used as the risk label.
- **Official:** the SEBI Riskometer that the AMC publishes monthly. In the workbook it is an *image*
  (dial with the level printed in its caption). `app/etl/amc_portfolio.py` identifies the scheme dial by the
  md5 of the image bytes against a table verified by eye. An unknown image is reported as unrecognised
  and never guessed. Imported: Nippon India (Aug 2026, all 107 sheets recognised) and DSP (Aug 2026, 61/62 recognised — DSP stacks its two dials vertically rather than side by side, which `_sheet_dials` now handles generically).
- **Estimate (no official level):** the highest of measured volatility band, worst-fall band and a
  category floor calibrated against the official levels (pure equity and most hybrids Very High, most debt
  Moderate, overnight/arbitrage Low). Calibration showed the first version under-warned, so floors are conservative.
- **Appetite filter** uses the displayed level: low = up to Moderate, medium = up to Moderately High, high = any.
  Because SEBI rates almost all equity funds Very High, equity funds appear only under "high".

## Holdings import (`scripts/import_portfolios.py`)
One sheet per scheme. Weights are validated: a portfolio is accepted only if its ISIN-bearing lines sum to
30-105% of NAV (Overnight funds hold repo/TREPS without ISINs and are rejected, correctly). Matching to our
schemes is by normalised name; duplicates (original + segregated-portfolio scheme) resolve to the lowest AMFI code.
Not done: HDFC (blocks scripted access), SBI and ICICI (files load via JavaScript). Baroda BNP Paribas uses a different format entirely: both dials plus their captions are baked into ONE
image per scheme (not a small reusable set), alongside a separate debt Potential-Risk-Class matrix image.
There is no hash table to build; each scheme's image was read by eye directly and the level recorded in
`BARODA_RISK_AUG2026` in `amc_portfolio.py`. This means, unlike Nippon/DSP, Baroda's mapping does NOT
self-update next month — it must be re-read by hand from each new month's file. Helios uses a third format: one file per scheme (not one workbook with many sheets) with the same
baked-in composite image as Baroda; `HELIOS_RISK_AUG2026` records its 8 schemes, read the same way.

`parse_holdings` also had to learn that not every AMC stores weight as a fraction of NAV — Helios
stores the percentage directly (2.32, not 0.0232) — so it now picks whichever scaling makes the
portfolio total land near 100%, rather than assuming one convention.

Tata is the easiest AMC found so far: it publishes a single sheet ("Tata Scheme Risk-o-Meter")
listing every scheme's official level as plain text, so no image parsing or manual re-reading is
needed at all — it self-updates every month like Nippon/DSP's hash tables do, just via text instead.

Axis uses a small reusable dial set like Nippon/DSP (6 hashes verified), but its site 404s on
the URL pattern for June-August 2026 — the newest file that pattern resolves is 31-May-2026, so
Axis's risk levels and holdings are dated May 2026, four months old at time of import, not August
like the others. This is disclosed via `riskometer_source`/`riskometer_as_of` per scheme.

ICICI Prudential publishes one file per scheme (like Helios) but its dial image carries only the
level text, not the scheme name, so it IS a small reusable set (8 distinct images across 147
scheme files) despite the one-file-per-scheme layout. Found via advisorkhoj.com mirroring
icicipruamc.com's own blob storage; both August 2026 file and current live page agree.

Kotak's dial (unlike Nippon/DSP/Axis) is re-rendered slightly differently per scheme, so its
verified table has 18 entries for 6 levels rather than 6-12; one further image was a benchmark
dial and was deliberately excluded, never guessed as a scheme level. Found via advisorkhoj.com's
S3 mirror of vatseelabs-s3.kotakmf.com.

Fixed while adding Kotak: `parse_holdings` assumed one column shift applied to every field, but
Kotak's header has a merged "Name of Instrument" cell spanning several blank columns, throwing the
name column off by a different amount than ISIN. The name column is now aligned independently.

Two more general bugs fixed while adding Franklin Templeton: the scheme-name cell can sit in the
first column, not just the second/third (`first[1:3]` widened to `first[0:3]`), and a header can
have TWO columns whose text both contain a field's keyword (Franklin's real "% to Net Assets"
column, plus "Outstanding derivative exposure AS % TO NET ASSETS Long/(Short)" later in the same
row) — the later one was silently winning and only the few rows with a stray derivative value
survived. Column detection now keeps the first match for each field, not the last.

Motilal Oswal needed a third scheme-name fix: its sheets open with "Back to Index" and a
registered-office/CIN block before the real name, so name extraction (`find_scheme_name`) now
scans the first several rows, skips known boilerplate and parenthetical description lines, and
prefers a candidate containing "Fund"/"Plan"/"Scheme"/"ETF" when more than one plausible line exists.

`find_scheme_name` needed one more fix for ITI: its second candidate line was literally "ITI
Mutual Fund" (just the AMC's own name, which still contains the word "fund"), beating the real
scheme name on every sheet. Bare "<AMC name> Mutual Fund" lines are now excluded outright, not
just deprioritised.

### 2026-09-22 second pass: 7 more fund houses

quant, Sundaram, Bajaj Finserv, 360 ONE, Trust, Mahindra Manulife, Unifi - 18 total, 635 schemes.
AdvisorKhoj's per-AMC mirror
(`advisorkhoj.com/mutual-funds-research/mutual-fund-portfolio/<AMC>/2026`) unblocked several AMCs
whose own sites don't expose a plain file link. Real bugs found and fixed this pass (all
regression-tested against every previously-working AMC before shipping):

- `_sheet_dials` didn't XML-unescape sheet names read from `workbook.xml`, so a sheet name
  containing `&`/`<`/`>` (e.g. quant's "qL&MF") never matched openpyxl's decoded name and silently
  lost its Riskometer to a dict-key miss.
- `parse_holdings` had no stop condition, so it read straight through an AMC's real "Grand Total"
  line into unrelated trailing content - Sundaram appends a legacy defaulted-CP recovery-accounting
  footnote there whose own mini-header coincidentally lines up with the "% to NAV" column, once
  producing a nonsense 212%-of-NAV holding and once corrupting a whole sheet's fraction-vs-percent
  scale detection. Now stops at "Grand Total"/"Total Portfolio", plus a per-row cap (no single
  holding can exceed the portfolio's own 105% bound).
- `norm_name()` didn't equate a cap-size term written as one word vs two ("Midcap" vs "Mid Cap",
  "Flexicap" vs "Flexi Cap") between an AMC's own disclosure and its AMFI-registered name.
- openpyxl only decides if a file is readable from its **extension**, never its content - Bajaj
  Finserv publishes modern XLSX bytes under a stale `.xls` URL, so every load failed outright
  despite the file being perfectly valid. Added `_load_workbook()`, which reads into a BytesIO
  buffer first, sidestepping the extension check entirely.
- The dial anchor-position sort used only whole-cell (row, col), discarding the sub-cell pixel
  offset - so two images sharing one anchor cell (Bajaj) fell back to comparing embedded filenames
  (meaningless) and picked the wrong one. Fixed by using (row, col) first, pixel offset only as a
  same-cell tie-breaker - proven against a second case (360 ONE) where getting that priority order
  backwards regressed a different sheet.
- `_sheet_dials` had no minimum image-size filter, so a tiny 2 KB decorative element (not a dial at
  all) beat the real ~13 KB dial purely on being topmost. Filtered candidates under 5 KB.
- The ISIN-hits floor for trusting a detected column shift (5) was too strict for a small,
  legitimately concentrated debt fund (Bajaj Finserv Gilt Fund: exactly 4 securities) - lowered to 3.
- `clean_scheme_name()` only stripped a trailing parenthetical or "as on <date>", not a trailing
  description after " - " (360 ONE bakes the full SEBI category/risk text after a dash, where our
  AMFI-sourced names use that same dash for "- Direct Plan - Growth").
- `find_scheme_name()`'s "prefer a Fund/Plan/Scheme/ETF candidate" rule didn't recognise "FOF"
  (fund-of-funds) as equivalent to "Fund", so a genuine FoF scheme's real name lost to a later
  row - its one holding, the underlying fund it invests in, which (like almost any FoF's holding)
  itself contains the word "Fund".

Two genuinely ambiguous Riskometer dials were left unrecognised rather than guessed: Unifi Dynamic
Asset Allocation Fund's needle sits right at the Moderate/Moderately-High boundary.

Known-blocked this pass: Capitalmind, Abakkus and Old Bridge's sites reject the TLS handshake
outright (works from a real browser, not from this environment - likely WAF fingerprinting of
non-browser clients, not fixable from here). Edelweiss returns 403 even via AdvisorKhoj's direct
link to the AMC's own host. Aditya Birla Sun Life's legacy binary `.xls` format was previously
investigated far enough to extract 24 valid embedded images, but per-sheet correlation was not
completed (needs OfficeArt/Escher blip-store index parsing). LIC's disclosure link on its own
downloads page 404s (stale page cache at LIC's end, not ours). Not attempted: the remaining
~28 fund houses.

## Known limits
- Returns are past, point-to-point, from funds that survive today (survivorship bias).
- Nifty benchmark is a price index, not TRI.
- TER changes month to month (base rate, brokerage, statutory levies), so values are as of the latest AMFI row, not fixed. Official Riskometer and holdings exist for Nippon India only; every other fund shows an estimated risk and no holdings.
- Rerun `scripts/backfill.py master` then `recompute` after data source changes; `verify_data.py` should exit 0.

## Where fund houses publish portfolios (probe of AMFI's directory, 53 fund houses)
AMFI does not host portfolio files; its Portfolio Disclosure page only links out to each fund house.
Probe result: 18 expose plain file links, 23 load them via JavaScript, 12 blocked or unreachable to a script.

## Rebuilding
`scripts/overnight.sh` (from `backend/`): master data + TER, NAV history for every fund house, validated analytics, then `verify_data.py`. About 22 minutes. Run 2026-09-22: 1,481 active schemes, 1,407 clean, 31 with an old break (shorter horizons only), 40 too new, 3 blocked for a recent break.

## Ongoing data sanitation checks
Two scripts should be run regularly (after every import/rebuild, and periodically otherwise —
not just when adding a new AMC), both from `backend/`:
- `scripts/verify_data.py` — reconciles our stored NAV history against AMFI's own single-day
  report, independent of the mfapi.in/AMFI bulk source our history was built from. Exits 1 if
  more than 0.5% of comparable NAVs disagree.
- `scripts/data_health_check.py` — sweeps everything else: Riskometer values are one of the 6
  official SEBI levels and not stale (>45 days), holdings weights are sane and each scheme's
  holdings total lands in [30,105]%, no orphaned/duplicate rows that would corrupt a total, scheme
  identity fields (amfi_code/isin/name) are unique and non-blank, and NAV/holdings staleness is
  flagged. It deliberately does NOT fail on legitimate AMC disclosure quirks it had to be taught to
  recognise on first run: multi-asset/hybrid funds publish small **negative** weights for short
  derivative/hedge legs (e.g. "ICICI BANK LTD^" at -0.49%), and the same ISIN can legitimately
  appear as several distinct lines (cash equity + derivative leg, or multiple futures expiries in
  an arbitrage fund) — sometimes with an identical weight by coincidence. These are reported as
  informational notes, not failures; only a genuinely out-of-band value or a per-scheme total
  outside [30,105]% fails the run.
  Run 2026-09-22 (11 AMCs, 620 schemes with holdings): all checks passed. Notes: Axis's holdings
  are from its "May 2026 (latest available)" file — 3+ months older than every other AMC's Aug 2026
  file, worth re-checking whether Axis has since published Aug/Sep; 3 newly-launched target-maturity
  index funds hadn't had a NAV update in 10+ days (thin/new, not a pipeline issue).
