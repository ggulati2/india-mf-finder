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
