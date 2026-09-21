import random
import hashlib
from typing import Set, Dict, List
from sqlalchemy.orm import Session
from app.db.database import SessionLocal
from app.db.models import MutualFundScheme

# Realistic Nifty 500 universe segmented by cap
UNIVERSE = {
    "Large Cap": ["RELIANCE","TCS","HDFCBANK","ICICIBANK","INFY","SBIN","BHARTIARTL","ITC","KOTAKBANK","LT","AXISBANK","MARUTI","WIPRO","ASIANPAINT","HCLTECH","SUNPHARMA","TITAN","BAJFINANCE","NESTLEIND","ULTRACEMCO"],
    "Mid Cap": ["MPHASIS","COFORGE","PERSISTENT","CUMMINSIND","ASHOKLEY","CONCOR","IPCALAB","FEDERALBNK","ESCORTS","APOLLOTYRE","COLPAL","BHARATFORG","AUROPHARMA","MRF","TRENT","JINDALSTEL","SAIL","GLENMARK","MUTHOOTFIN","LUPIN"],
    "Small Cap": ["IRCTC","CDSL","KPRMILL","KEI","RADICO","ANUP","CHOLAHLDNG","CRAFTSMAN","MASTEK","MEDPLUS","PRAJIND","SAPPHIRE","TANLA","VGUARD","FINEORG","HONAUT","NEOGEN","ROSSARI","TRIDENT","AVANTIFEED"],
    "Flexi Cap": ["RELIANCE","TCS","MPHASIS","IRCTC","HDFCBANK","COFORGE","CDSL","INFY","KPRMILL","SBIN"],
    "Hybrid": ["HDFCBANK","RELIANCE","SBIN","ICICIBANK","INFY","TCS","ITC","LT","MPHASIS","IRCTC"],
    "ELSS": ["INFY","RELIANCE","HDFCBANK","TCS","ICICIBANK","KOTAKBANK","BAJFINANCE","MARUTI","SUNPHARMA","TITAN"],
    "Debt": ["GOVTSEC","TBILL","CORPBOND","CP","CD","SDL"],
    "Index": ["RELIANCE","HDFCBANK","ICICIBANK","INFY","TCS","ITC","SBIN","BHARTIARTL","KOTAKBANK","LT"],
    "Sectoral": ["TCS","INFY","WIPRO","HCLTECH","MPHASIS","COFORGE","PERSISTENT","LTTS","TECHM","MINDTREE"],
}

SECTOR_MAP = {
    "RELIANCE":"Energy","TCS":"IT","HDFCBANK":"Financials","ICICIBANK":"Financials","INFY":"IT","SBIN":"Financials","BHARTIARTL":"Telecom","ITC":"FMCG","KOTAKBANK":"Financials","LT":"Infra",
    "MPHASIS":"IT","COFORGE":"IT","IRCTC":"Services","CDSL":"Financials","KPRMILL":"Textiles","PERSISTENT":"IT","CUMMINSIND":"Auto","ASHOKLEY":"Auto","IPCALAB":"Pharma","FEDERALBNK":"Financials",
}

def deterministic_holdings(scheme_id: int, category: str, n: int = 35) -> List[Dict]:
    """Deterministic synthetic holdings per scheme_id so same scheme always same portfolio."""
    universe = UNIVERSE.get(category, UNIVERSE["Flexi Cap"])
    # Expand universe for variety
    if category in ["Small Cap","Mid Cap"] and len(universe) < 40:
        universe = universe + UNIVERSE["Flexi Cap"]
    h = hashlib.md5(f"{scheme_id}".encode()).hexdigest()
    seed = int(h[:8], 16)
    rnd = random.Random(seed)
    picks = rnd.sample(universe, min(n, len(universe)))
    # Add some cross-category overlap for realism (20% from Large Cap)
    if category in ["Mid Cap","Small Cap"]:
        cross = rnd.sample(UNIVERSE["Large Cap"], 5)
        picks = list(set(picks + cross))[:n]
    weights = [rnd.random() for _ in picks]
    total = sum(weights)
    weights = [w/total*100 for w in weights]
    # sort by weight desc
    paired = sorted(zip(picks, weights), key=lambda x: -x[1])
    return [{"ticker": t, "weight": round(w,2), "sector": SECTOR_MAP.get(t,"Others")} for t,w in paired]

def get_scheme_holdings_set(scheme_id: int, category: str) -> Set[str]:
    return set(h["ticker"] for h in deterministic_holdings(scheme_id, category))

def get_holdings_detail(scheme_id: int, category: str) -> List[Dict]:
    return deterministic_holdings(scheme_id, category)
