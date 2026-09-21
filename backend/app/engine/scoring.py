import numpy as np
import pandas as pd
from app.engine.benchmark import get_nifty_history_sync
from scipy import stats
from typing import Dict, List, Tuple
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)

def calculate_rolling_returns_score(returns: pd.Series, time_horizon_years: int) -> float:
    if len(returns) < 2:
        return 50.0
    annual_returns = []
    for i in range(len(returns) - 1):
        years = (i + 1) / 252
        if years <= time_horizon_years:
            annual_return = (returns.iloc[-1] / returns.iloc[-(i + 1)]) ** (1 / years) - 1
            annual_returns.append(annual_return)
    if not annual_returns:
        return 50.0
    mean_return = np.mean(annual_returns)
    std_return = np.std(annual_returns)
    if std_return == 0:
        return 50.0
    z_score = (mean_return - (-0.05)) / (0.3 - (-0.05))
    score = max(0, min(100, (z_score * 20 + 50)))
    return float(score)

def calculate_risk_adjusted_score(returns: pd.Series, risk_free_rate: float = 0.05) -> float:
    if len(returns) < 2:
        return 50.0
    daily_returns = returns.pct_change().dropna()
    excess_returns = daily_returns - risk_free_rate / 252
    sharpe_ratio = (excess_returns.mean() / excess_returns.std()) * np.sqrt(252)
    score = max(0, min(100, (sharpe_ratio + 2) * 20))
    return float(score)

def calculate_sortino_score(returns: pd.Series, risk_free_rate: float = 0.05) -> float:
    if len(returns) < 2:
        return 50.0
    daily_returns = returns.pct_change().dropna()
    target_return = risk_free_rate / 252
    downside_returns = daily_returns[daily_returns < target_return]
    downside_deviation = downside_returns.std() if len(downside_returns) > 0 else 0.01
    excess_returns = daily_returns - target_return
    sortino_ratio = (excess_returns.mean() / downside_deviation) * np.sqrt(252) if downside_deviation > 0 else 0
    score = max(0, min(100, sortino_ratio * 25))
    return float(score)

def calculate_consistency_score(returns: pd.Series, time_horizon_years: int) -> float:
    if len(returns) < 10:
        return 50.0
    daily_returns = returns.pct_change().dropna()
    rolling_vol = daily_returns.rolling(window=20).std() * np.sqrt(252)
    mean_return = daily_returns.mean() * 252
    std_return = daily_returns.std() * np.sqrt(252)
    cv = abs(std_return / mean_return) if mean_return != 0 else 1.0
    cv_normalized = min(cv, 5.0) / 5.0
    score = max(0, 100 - (cv_normalized * 100))
    return float(score)

def calculate_fundamentals_score(scheme_data: Dict) -> float:
    return 50.0

def calculate_trend_score(returns: pd.Series, short_window: int = 20, long_window: int = 50) -> float:
    if len(returns) < long_window:
        return 50.0
    short_ma = returns.rolling(window=short_window).mean()
    long_ma = returns.rolling(window=long_window).mean()
    price_above_ma = returns > short_ma
    ma_above_long = short_ma > long_ma
    bullish_count = price_above_ma.sum() + ma_above_long.sum()
    total_signals = len(returns.dropna())
    if total_signals == 0:
        return 50.0
    trend_score = (bullish_count / (total_signals * 2)) * 100
    return float(min(100, max(0, trend_score)))

def calculate_beta(fund_returns: pd.Series, market_returns: pd.Series) -> float:
    """Beta of daily fund returns vs daily market returns (aligned on date index)."""
    df = pd.concat([fund_returns, market_returns], axis=1, join="inner").dropna()
    if len(df) < 30:
        return 1.0
    market_variance = df.iloc[:, 1].var()
    if not market_variance or market_variance <= 0:
        return 1.0
    return float(df.iloc[:, 0].cov(df.iloc[:, 1]) / market_variance)

def calculate_capture_ratios(fund_returns: pd.Series, market_returns: pd.Series) -> Tuple[float, float]:
    """Upside/downside capture (%): mean fund return / mean market return on up / down market days."""
    try:
        df = pd.concat([fund_returns, market_returns], axis=1, join="inner").dropna()
        df.columns = ["f", "m"]
        up, down = df[df.m > 0], df[df.m < 0]
        if len(up) < 10 or len(down) < 10 or up.m.mean() == 0 or down.m.mean() == 0:
            return 100.0, 100.0
        return float(up.f.mean() / up.m.mean() * 100), float(down.f.mean() / down.m.mean() * 100)
    except Exception:
        return 100.0, 100.0

def compute_scheme_analytics(
    nav_df: pd.DataFrame,
    scheme: Dict,
    time_horizon_years: int
) -> Dict:
    try:
        returns = nav_df['nav']
        start_nav = returns.iloc[0]
        end_nav = returns.iloc[-1]
        years = (nav_df['date'].iloc[-1] - nav_df['date'].iloc[0]).days / 365.25
        if start_nav > 0 and years > 0:
            cagr = (end_nav / start_nav) ** (1 / years) - 1
        else:
            cagr = 0.0
        rolling_returns = returns.pct_change().dropna()
        risk_free_rate = 0.05
        excess_returns = rolling_returns - risk_free_rate / 252
        sharpe_ratio = (excess_returns.mean() / excess_returns.std()) * np.sqrt(252) if excess_returns.std() > 0 else 0
        target_return = risk_free_rate / 252
        downside_returns = rolling_returns[rolling_returns < target_return]
        downside_deviation = downside_returns.std() if len(downside_returns) > 0 else 0.01
        sortino_ratio = (excess_returns.mean() / downside_deviation) * np.sqrt(252) if downside_deviation > 0 else 0
        fund_daily = rolling_returns.copy()
        fund_daily.index = nav_df['date'].iloc[1:].values
        bench = get_nifty_history_sync()
        if len(bench):
            market_daily = bench.set_index('date')['close'].pct_change().dropna()
            beta = calculate_beta(fund_daily, market_daily)
            upside_capture, downside_capture = calculate_capture_ratios(fund_daily, market_daily)
        else:
            beta, (upside_capture, downside_capture) = 1.0, (100.0, 100.0)
        jensens_alpha = cagr - (beta * (risk_free_rate + excess_returns.std()))
        volatility = rolling_returns.std() * np.sqrt(252)
        def _sanitize(v):
            if not np.isfinite(v):
                return 0.0
            return float(np.clip(v, -1e6, 1e6))
        analytics = {
            'cagr': _sanitize(cagr * 100),
            'rolling_returns_mean': _sanitize(rolling_returns.mean() * 100),
            'rolling_returns_std': _sanitize(rolling_returns.std() * 100),
            'sharpe_ratio': _sanitize(sharpe_ratio),
            'sortino_ratio': _sanitize(sortino_ratio),
            'jensens_alpha': _sanitize(jensens_alpha * 100),
            'beta': _sanitize(float(np.clip(beta, -5, 5))),
            'upside_capture': _sanitize(upside_capture),
            'downside_capture': _sanitize(downside_capture),
            'volatility': _sanitize(volatility * 100)
        }
        return analytics
    except Exception as e:
        logger.error(f"Error computing analytics: {e}")
        return {
            'cagr': 0.0, 'rolling_returns_mean': 0.0, 'rolling_returns_std': 0.0,
            'sharpe_ratio': 0.0, 'sortino_ratio': 0.0, 'jensens_alpha': 0.0,
            'beta': 0.0, 'upside_capture': 0.0, 'downside_capture': 0.0, 'volatility': 0.0
        }

def calculate_ocs_score(
    scheme_data: Dict,
    category_scores: Dict,
    investment_mode: str,
    risk_appetite: str
) -> float:
    rolling_returns_score = category_scores.get('rolling_returns', 50.0)
    risk_adjusted_score = category_scores.get('risk_adjusted', 50.0)
    consistency_score = category_scores.get('consistency', 50.0)
    fundamentals_score = category_scores.get('fundamentals', 50.0)
    trend_score = category_scores.get('trend', 50.0)
    # Risk-aware weighting — makes risk filter actually change ranking
    if risk_appetite.lower() == 'low':
        # Conservative: ultra-favor risk-adjusted & consistency
        w_rolling, w_risk, w_cons, w_fund, w_trend = 0.05, 0.50, 0.35, 0.05, 0.05
    elif risk_appetite.lower() == 'high':
        # Aggressive: ultra-favor rolling returns & trend
        w_rolling, w_risk, w_cons, w_fund, w_trend = 0.50, 0.05, 0.05, 0.15, 0.25
    else:
        w_rolling, w_risk, w_cons, w_fund, w_trend = 0.25, 0.25, 0.20, 0.15, 0.15
    ocs = (
        w_rolling * rolling_returns_score +
        w_risk * risk_adjusted_score +
        w_cons * consistency_score +
        w_fund * fundamentals_score +
        w_trend * trend_score
    )
    if investment_mode.lower() == 'lump sum':
        ocs *= 1.05
        pe_ratio = scheme_data.get('pe_ratio', 0)
        if pe_ratio > 1.5:
            ocs *= 0.9
    elif investment_mode.lower() == 'sip':
        ocs *= 1.02
        volatility = scheme_data.get('volatility', 0)
        if volatility > 0.3:
            ocs *= 0.97
    ocs = max(0.0, min(100.0, ocs))
    return float(ocs)