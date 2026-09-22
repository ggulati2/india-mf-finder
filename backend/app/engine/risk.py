import pandas as pd
import numpy as np
from datetime import date, timedelta

def max_drawdown(nav_series: pd.Series) -> float:
    """Max drawdown %"""
    if len(nav_series) < 2:
        return 0.0
    roll_max = nav_series.cummax()
    dd = (nav_series - roll_max) / roll_max
    return float(dd.min() * 100)

def rolling_returns_series(nav_df: pd.DataFrame, window_years: int = 3) -> list:
    """3Y rolling returns time series for chart.

    Vectorised with numpy instead of a per-row `.iloc[]` loop: for ~10 years of daily NAVs that
    loop made ~6,000 pandas row-indexing calls, each with real overhead, costing over a second.
    """
    window = int(window_years * 252)
    if len(nav_df) <= window:
        return []
    nav_df = nav_df.sort_values("date")
    navs = nav_df["nav"].to_numpy()
    dates = nav_df["date"].to_numpy()
    start, end = navs[:-window], navs[window:]
    valid = start > 0
    cagr = np.where(valid, (end / np.where(valid, start, 1.0)) ** (1 / window_years) - 1, np.nan)
    out = [
        {"date": str(pd.Timestamp(d).date()), "rolling_cagr": round(float(c * 100), 2)}
        for c, d in zip(cagr, dates[window:]) if not np.isnan(c)
    ]
    # downsample to ~100 points
    if len(out) > 120:
        step = len(out) // 100
        out = out[::step]
    return out

def sip_xirr(nav_df: pd.DataFrame, monthly_amount: float = 10000, years: int = 5) -> float:
    """SIP XIRR via weekly entry points simulation (approx)."""
    try:
        if len(nav_df) < 60:
            return 0.0
        nav_df = nav_df.sort_values("date")
        # take last N years
        cutoff = nav_df["date"].max() - pd.Timedelta(days=int(years*365.25))
        window = nav_df[nav_df["date"] >= cutoff].copy()
        if len(window) < 20:
            window = nav_df
        # monthly SIP: first trading day each month
        window["ym"] = window["date"].dt.to_period("M")
        monthly = window.groupby("ym").first().reset_index()
        if len(monthly) < 6:
            return 0.0
        # simulate units
        units = 0.0
        total_invest = 0.0
        for _, r in monthly.iterrows():
            units += monthly_amount / float(r["nav"])
            total_invest += monthly_amount
        final_nav = float(window.iloc[-1]["nav"])
        final_value = units * final_nav
        # XIRR approx via CAGR
        total_years = len(monthly)/12
        xirr = (final_value/total_invest)**(1/total_years) - 1 if total_invest else 0
        return round(float(xirr*100),2)
    except Exception:
        return 0.0
