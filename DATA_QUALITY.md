# Data quality and sources

Users make money decisions from this app, so every displayed number is either traceable to an
official source or clearly labelled as an estimate. Unknown is shown as "n/a", never a default.

| Data | Source | Notes |
|---|---|---|
| Scheme list, AMC, ISIN, SEBI category | AMFI `NAVAll.txt` (portal.amfiindia.com) | Direct + Growth + open-ended only; matured/merged schemes are inactive |
| NAV history | AMFI NAV data via mfapi.in | Reconciled against AMFI's own history report (`scripts/verify_data.py`): 0 mismatches over 524 sampled NAVs at 1/3/5 years back |
| Expense ratio (TER) | AMFI TER API (`/api/populate-te-rdata-revised`, one Excel per fund house), latest daily row | 1,441 of 1,481 active schemes (97%). Matched by normalised name; no match = "n/a", no fuzzy guessing. Falls back to captn3m0's CSV, which lags AMFI (e.g. Axis Small Cap: CSV 0.54% vs AMFI 0.71% on 18 Sep 2026) |
| Benchmark (beta, capture) | Nifty 50 price index, Yahoo Finance | Excludes dividends; cached daily in `backend/data/` |
| Risk level | Official SEBI Riskometer where imported, else a conservative estimate | See below. Every fund shows which one it is |
| Holdings / sector mix | AMC monthly portfolio disclosure (official) | Currently Nippon India only (74 schemes). Others show "not imported yet". Earlier versions showed synthetic data |

## Validation applied to every NAV series (`app/engine/quality.py`)
- Zero/negative NAVs and isolated one-day spikes that reverse next day are dropped (`repaired_points`).
- Any remaining implausible persistent jump (>20% a day for equity, >5% debt, >12% hybrid), a gap over 20 days, or coverage under 80% blocks the scheme (`data_flags`); it gets no analytics and is not recommended.
- A horizon (1/3/5/10Y) is only computed if we hold that much history. Earlier code silently reused shorter history under a longer label.
- Inactive, matured, IDCW/bonus/regular options are excluded (their NAV drops on payouts, so returns are not comparable).

## Risk level (`app/engine/risk_level.py`)
Sharpe/Sortino are return per unit of risk and must never be used as the risk label.
- **Official:** the SEBI Riskometer that the AMC publishes monthly. In the workbook it is an *image*
  (dial with the level printed in its caption). `app/etl/amc_portfolio.py` identifies the scheme dial by the
  md5 of the image bytes against a table verified by eye. An unknown image is reported as unrecognised
  and never guessed. Imported: Nippon India, Aug 2026 (74 schemes, all dials recognised).
- **Estimate (no official level):** the highest of measured volatility band, worst-fall band and a
  category floor calibrated against the official levels (pure equity and most hybrids Very High, most debt
  Moderate, overnight/arbitrage Low). Calibration showed the first version under-warned, so floors are conservative.
- **Appetite filter** uses the displayed level: low = up to Moderate, medium = up to Moderately High, high = any.
  Because SEBI rates almost all equity funds Very High, equity funds appear only under "high".

## Holdings import (`scripts/import_portfolios.py`)
One sheet per scheme. Weights are validated: a portfolio is accepted only if its ISIN-bearing lines sum to
30-105% of NAV (Overnight funds hold repo/TREPS without ISINs and are rejected, correctly). Matching to our
schemes is by normalised name; duplicates (original + segregated-portfolio scheme) resolve to the lowest AMFI code.
Not done: HDFC (blocks scripted access), SBI and ICICI (files load via JavaScript), and every other AMC.

## Known limits
- Returns are past, point-to-point, from funds that survive today (survivorship bias).
- Nifty benchmark is a price index, not TRI.
- TER changes month to month (base rate, brokerage, statutory levies), so values are as of the latest AMFI row, not fixed. Official Riskometer and holdings exist for Nippon India only; every other fund shows an estimated risk and no holdings.
- Rerun `scripts/backfill.py master` then `recompute` after data source changes; `verify_data.py` should exit 0.

## Where fund houses publish portfolios (probe of AMFI's directory, 53 fund houses)
AMFI does not host portfolio files; its Portfolio Disclosure page only links out to each fund house.
Probe result: 18 expose plain file links, 23 load them via JavaScript, 12 blocked or unreachable to a script.
