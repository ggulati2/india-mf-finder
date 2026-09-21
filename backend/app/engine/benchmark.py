import httpx
import pandas as pd
from datetime import datetime, timedelta

async def fetch_nifty_history(days: int = 5*365):
    """Fetch Nifty 50 history via Yahoo Finance."""
    try:
        end = int(datetime.now().timestamp())
        start = int((datetime.now() - timedelta(days=days)).timestamp())
        url = f"https://query1.finance.yahoo.com/v8/finance/chart/%5ENSEI?period1={start}&period2={end}&interval=1d"
        async with httpx.AsyncClient(timeout=15, headers={"User-Agent":"Mozilla/5.0"}) as client:
            r = await client.get(url)
            if r.status_code != 200:
                return pd.DataFrame()
            j = r.json()
            result = j.get("chart",{}).get("result",[None])[0]
            if not result:
                return pd.DataFrame()
            ts = result.get("timestamp",[])
            quotes = result.get("indicators",{}).get("quote",[{}])[0].get("close",[])
            df = pd.DataFrame({"date": pd.to_datetime(ts, unit="s"), "close": quotes}).dropna()
            return df
    except Exception:
        return pd.DataFrame()


_NIFTY_CACHE = {"df": None}

def get_nifty_history_sync(days: int = 11 * 365) -> pd.DataFrame:
    """Nifty 50 closes (columns: date, close), cached in-process and on disk so
    batch analytics need only one Yahoo call. Empty frame if unavailable."""
    import os
    if _NIFTY_CACHE["df"] is not None:
        return _NIFTY_CACHE["df"]
    path = os.path.join(os.path.dirname(__file__), "..", "..", "data", "nifty.csv")
    try:
        if os.path.exists(path) and (datetime.now().timestamp() - os.path.getmtime(path)) < 86400:
            df = pd.read_csv(path, parse_dates=["date"])
        else:
            end = int(datetime.now().timestamp())
            start = int((datetime.now() - timedelta(days=days)).timestamp())
            url = f"https://query1.finance.yahoo.com/v8/finance/chart/%5ENSEI?period1={start}&period2={end}&interval=1d"
            r = httpx.get(url, timeout=20, headers={"User-Agent": "Mozilla/5.0"})
            r.raise_for_status()
            res = r.json()["chart"]["result"][0]
            df = pd.DataFrame({
                "date": pd.to_datetime(res["timestamp"], unit="s").normalize(),
                "close": res["indicators"]["quote"][0]["close"],
            }).dropna()
            os.makedirs(os.path.dirname(path), exist_ok=True)
            df.to_csv(path, index=False)
    except Exception:
        # stale cache beats nothing
        try:
            df = pd.read_csv(path, parse_dates=["date"])
        except Exception:
            df = pd.DataFrame(columns=["date", "close"])
    _NIFTY_CACHE["df"] = df
    return df
