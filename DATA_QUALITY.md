# Data quality and sources

Users make money decisions from this app, so every displayed number is either traceable to an
official source or clearly labelled as an estimate. Unknown is shown as "n/a", never a default.

| Data | Source | Notes |
|---|---|---|
| Scheme list, AMC, ISIN, SEBI category | AMFI `NAVAll.txt` (portal.amfiindia.com) | Direct + Growth + open-ended only; matured/merged schemes are inactive |
| NAV history | AMFI NAV data via mfapi.in | Reconciled against AMFI's own history report (`scripts/verify_data.py`): 0 mismatches over 524 sampled NAVs at 1/3/5 years back |
| Expense ratio (TER) | AMFI TER disclosure, republished daily by captn3m0/india-mutual-fund-ter-tracker | Matched by name; about 55% of active schemes match (the source lags fund renames). No match = "n/a" (no fuzzy guessing) |
| Benchmark (beta, capture) | Nifty 50 price index, Yahoo Finance | Excludes dividends; cached daily in `backend/data/` |
| Risk level | Our estimate | See below. **Not** the SEBI Riskometer |
| Holdings / sector mix | none | Removed: there is no free verified per-scheme feed. Earlier versions showed synthetic data |

## Validation applied to every NAV series (`app/engine/quality.py`)
- Zero/negative NAVs and isolated one-day spikes that reverse next day are dropped (`repaired_points`).
- Any remaining implausible persistent jump (>20% a day for equity, >5% debt, >12% hybrid), a gap over 20 days, or coverage under 80% blocks the scheme (`data_flags`); it gets no analytics and is not recommended.
- A horizon (1/3/5/10Y) is only computed if we hold that much history. Earlier code silently reused shorter history under a longer label.
- Inactive, matured, IDCW/bonus/regular options are excluded (their NAV drops on payouts, so returns are not comparable).

## Risk level (`app/engine/risk_level.py`)
Sharpe/Sortino measure return per unit of risk, so they must not be used as the risk label. The level
uses SEBI's six labels and is the highest of: annualised volatility band, worst-fall band, and a floor
from the SEBI category (e.g. small/mid/sectoral equity is never below Very High, large/flexi equity never below High).
Risk appetite filters by this level: low = up to Moderate, medium = up to High, high = any.

## Known limits
- Returns are past, point-to-point, from funds that survive today (survivorship bias).
- Nifty benchmark is a price index, not TRI.
- TER coverage is partial; holdings are unavailable; the SEBI Riskometer is not ingested (no machine-readable feed).
- Rerun `scripts/backfill.py master` then `recompute` after data source changes; `verify_data.py` should exit 0.
