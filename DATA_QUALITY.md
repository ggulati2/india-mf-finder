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
| Holdings / sector mix | AMC monthly portfolio disclosure (official) | Currently Nippon India (107), DSP (62), Baroda BNP Paribas (41), Helios (8), Tata (60), Axis (64) — 6 fund houses, 342 schemes. Others show "not imported yet". Earlier versions showed synthetic data |

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

Every other AMC is undone. LIC's disclosure link on its own downloads page 404s (stale page cache
at LIC's end, not ours). Sundaram, Quantum, Choice had no plain file link in the fetched page (need
proper discovery, e.g. a JS-driven API the way DSP/AMFI needed). Zerodha, Shriram, NJ, Unifi didn't
show a current monthly-portfolio file in a first pass. Not attempted: the remaining ~45 fund houses.

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
