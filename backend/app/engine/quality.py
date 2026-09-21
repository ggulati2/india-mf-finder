"""NAV validation and horizon integrity.

A number is only shown if the history behind it passes these checks. Failing schemes get
`data_flags` and are excluded from recommendations rather than shown with doubtful figures.
"""
from typing import List, Optional, Tuple

import pandas as pd

# Largest believable one-day NAV move. Debt/liquid funds essentially never move >2% a day;
# equity funds (even small caps in March 2020) stay well inside 20%.
MAX_DAILY_MOVE = {"Debt": 0.05, "Hybrid": 0.12}
DEFAULT_MAX_DAILY_MOVE = 0.20
MAX_GAP_DAYS = 20          # longest tolerated hole between two NAVs in the analysed window
MIN_COVERAGE = 0.80        # observations / expected trading days
HORIZON_TOLERANCE_DAYS = 20


def _drop_spikes(df: pd.DataFrame, limit: float) -> Tuple[pd.DataFrame, int]:
    """Remove isolated one-day spikes: a jump beyond `limit` that reverses the next day."""
    dropped = 0
    while True:
        nav = df["nav"].values
        bad = None
        for i in range(1, len(nav) - 1):
            r_in, r_out = nav[i] / nav[i - 1] - 1, nav[i + 1] / nav[i] - 1
            if abs(r_in) > limit and r_in * r_out < 0 and abs(nav[i + 1] / nav[i - 1] - 1) < limit / 3:
                bad = i
                break
        if bad is None:
            return df, dropped
        df = df.drop(df.index[bad]).reset_index(drop=True)
        dropped += 1


def clean_nav(df: pd.DataFrame, bucket: str) -> Tuple[pd.DataFrame, List[str]]:
    """Return (clean df sorted by date, flags). df has columns date, nav.

    Repairs (drops) zero/negative points and isolated reverting spikes, flagging
    `repaired_points`; blocks (`nav_jump`) on any remaining implausible persistent move.
    """
    flags: List[str] = []
    df = df.dropna().drop_duplicates("date").sort_values("date")
    n0 = len(df)
    df = df[df["nav"] > 0].reset_index(drop=True)
    limit = MAX_DAILY_MOVE.get(bucket, DEFAULT_MAX_DAILY_MOVE)
    df, spikes = _drop_spikes(df, limit)
    repaired = (n0 - len(df))
    if repaired:
        flags.append("repaired_points")
        if repaired > max(3, 0.005 * n0):  # more than a handful of bad points: don't trust the feed
            flags.append("nonpositive_nav" if spikes == 0 else "nav_jump")
    if len(df) < 2:
        return df, flags + ["insufficient_history"]
    if (df["nav"].pct_change().abs() > limit).any():
        flags.append("nav_jump")
    return df, flags


def window_for_horizon(df: pd.DataFrame, years: int) -> Optional[pd.DataFrame]:
    """The last `years` years of NAVs, or None if we do not truly hold that much history."""
    end = df["date"].max()
    start = end - pd.Timedelta(days=int(years * 365.25))
    if df["date"].min() > start + pd.Timedelta(days=HORIZON_TOLERANCE_DAYS):
        return None
    w = df[df["date"] >= start]
    return w if len(w) >= 20 else None


def window_flags(w: pd.DataFrame) -> List[str]:
    flags = []
    if w["date"].diff().dt.days.max() > MAX_GAP_DAYS:
        flags.append("nav_gap")
    span_years = (w["date"].iloc[-1] - w["date"].iloc[0]).days / 365.25
    if span_years > 0 and len(w) / (span_years * 250) < MIN_COVERAGE:
        flags.append("sparse_history")
    return flags
