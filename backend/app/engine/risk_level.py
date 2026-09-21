"""Risk level shown to users.

Sharpe/Sortino measure return *per unit of risk*; they say nothing about how risky a fund is
(a small cap in a bull run has a great Sharpe). The level here is derived from measured
volatility and worst fall, floored by the fund's SEBI category, on SEBI's six Riskometer labels.

It is an estimate from past NAVs, NOT the SEBI Riskometer the AMC publishes monthly.
"""
from typing import Optional

LEVELS = ["Low", "Low to Moderate", "Moderate", "Moderately High", "High", "Very High"]

# annualised volatility (%) upper bounds for levels 1..5; above -> Very High
_VOL_BANDS = [1.0, 3.0, 6.0, 10.0, 15.0]
# worst peak-to-trough fall (%, negative) -> minimum level index
_MDD_FLOORS = [(-30, 5), (-20, 4), (-12, 3), (-6, 2)]

_EQUITY_HIGH = {"Large Cap", "Flexi Cap", "ELSS", "Index"}
_EQUITY_VERY_HIGH = {"Mid Cap", "Small Cap", "Sectoral"}


def _category_floor(bucket: str, sebi_category: Optional[str]) -> int:
    c = (sebi_category or "").lower()
    if bucket in _EQUITY_VERY_HIGH:
        return 5
    if bucket in _EQUITY_HIGH:
        return 4
    if bucket == "Hybrid":
        if "arbitrage" in c:
            return 0
        if "conservative" in c or "equity savings" in c:
            return 2
        return 3
    if bucket == "Debt":
        if "credit risk" in c:
            return 3
        if any(k in c for k in ("long duration", "medium to long", "dynamic bond", "gilt", "corporate bond", "medium duration")):
            return 2
        return 0
    return 3


def measured_risk(bucket: str, sebi_category: Optional[str], volatility: Optional[float],
               max_drawdown: Optional[float]) -> dict:
    idx = _category_floor(bucket, sebi_category)
    basis = "category"
    if volatility is not None:
        v = next((i for i, b in enumerate(_VOL_BANDS) if volatility <= b), 5)
        if v > idx:
            idx, basis = v, "volatility"
    if max_drawdown is not None:
        for thr, lvl in _MDD_FLOORS:
            if max_drawdown <= thr:
                if lvl > idx:
                    idx, basis = lvl, "worst fall"
                break
    return {"level": LEVELS[idx], "score": idx + 1, "basis": basis}


# Conservative display floors, calibrated against official Riskometers published by an AMC
# (69 Nippon schemes, Aug 2026): pure equity and most hybrids are "Very High", most debt
# funds "Moderate", overnight/arbitrage "Low". Used only when no official level is available.
def _display_floor(bucket: str, sebi_category: Optional[str]) -> int:
    c = (sebi_category or "").lower()
    if bucket in _EQUITY_HIGH | _EQUITY_VERY_HIGH:
        return 5
    if bucket == "Hybrid":
        if "arbitrage" in c:
            return 0
        if "conservative" in c or "equity savings" in c:
            return 3
        return 5
    if bucket == "Debt":
        if "overnight" in c:
            return 0
        if "credit risk" in c:
            return 3
        return 2
    return 3


def risk_info(scheme, volatility: Optional[float], max_drawdown: Optional[float]) -> dict:
    """What the UI shows, plus the finer measured score used to filter by risk appetite.

    level/official: the AMC-published SEBI Riskometer when we hold it, otherwise a conservative
    estimate (never below the calibrated category floor, never below the measured level).
    gate_score: the finer measured 1-6 score, kept for reference/ranking; the appetite filter uses
    `score` so that what is filtered matches the label the user sees.
    """
    m = measured_risk(scheme.category, scheme.sebi_category, volatility, max_drawdown)
    est_idx = max(m["score"] - 1, _display_floor(scheme.category, scheme.sebi_category))
    out = {"gate_score": m["score"], "measured": m["level"], "basis": m["basis"]}
    if getattr(scheme, "riskometer", None) in LEVELS:
        idx = LEVELS.index(scheme.riskometer)
        out.update(level=scheme.riskometer, score=idx + 1, official=True,
                   source=scheme.riskometer_source,
                   as_of=scheme.riskometer_as_of.isoformat() if scheme.riskometer_as_of else None)
    else:
        out.update(level=LEVELS[est_idx], score=est_idx + 1, official=False, source="Estimated from past NAVs and category")
    return out
