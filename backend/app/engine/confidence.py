"""Per-fund data confidence.

Each check is a named, verifiable fact. Level:
  Complete - every check passes
  Partial  - the core checks (category, NAV validation, history, freshness) pass but a
             supporting fact such as the expense ratio is unknown
  Low      - a core check fails (such funds are excluded from recommendations)
The Riskometer and holdings are never available, so they are listed as standing gaps, not checks.
"""
from datetime import date, timedelta

CORE = ("category_verified", "nav_validated", "history_covers_horizon", "data_fresh")


def data_confidence(scheme, analytics, horizon_years: int) -> dict:
    hist = float(analytics.history_years) if analytics is not None and analytics.history_years is not None else 0.0
    checks = {
        "category_verified": bool(scheme.sebi_category),
        "nav_validated": not any(f in (scheme.data_flags or "") for f in ("nav_jump", "nav_gap", "sparse_history", "nonpositive_nav")),
        "history_covers_horizon": hist >= horizon_years * 0.95,
        "data_fresh": bool(scheme.latest_nav_date and scheme.latest_nav_date >= date.today() - timedelta(days=10)),
        "expense_ratio_known": scheme.ter_pct is not None,
    }
    core_ok = all(checks[c] for c in CORE)
    level = "Low" if not core_ok else ("Complete" if all(checks.values()) else "Partial")
    return {
        "level": level,
        "checks": checks,
        "missing": [k for k, v in checks.items() if not v],
        "not_available": ["official SEBI Riskometer", "portfolio holdings"],
    }
