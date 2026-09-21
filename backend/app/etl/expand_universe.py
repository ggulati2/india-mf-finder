from app.db.database import SessionLocal, init_db_sync
from app.db.models import MutualFundScheme
from datetime import date
import json
import logging
import httpx

logger = logging.getLogger(__name__)

# Use cached mf_list or fetch fresh
async def expand_universe_from_mfapi(limit_per_category=20):
    init_db_sync()
    db = SessionLocal()
    try:
        # Load mf_list.json if exists, else fetch
        import os
        mf_list_path = "/tmp/mf_list.json"
        if os.path.exists(mf_list_path):
            with open(mf_list_path) as f:
                all_schemes = json.load(f)
        else:
            async with httpx.AsyncClient(timeout=30) as client:
                r = await client.get("https://api.mfapi.in/mf")
                all_schemes = r.json()

        # Filter Direct + Growth only
        direct_growth = [s for s in all_schemes if "direct" in s["schemeName"].lower() and "growth" in s["schemeName"].lower()]
        logger.info(f"Found {len(direct_growth)} Direct Growth schemes")

        # Categorize by keywords
        def categorize(name):
            n = name.lower()
            if "small cap" in n: return "Small Cap"
            if "mid cap" in n or "midcap" in n: return "Mid Cap"
            if "large cap" in n: return "Large Cap"
            if "flexi cap" in n: return "Flexi Cap"
            if "elss" in n or "tax saver" in n: return "ELSS"
            if any(x in n for x in ["interval","treasury","fixed maturity","fixed term","fmp","income","bond","duration","floater","savings","cash","gilt","liquid","debt","banking & psu","banking and psu","credit risk","overnight","money market","maturity","target","ftif","ftp","fixed horizon","fixed tenure","ultra short","short term","short to","dual advantage","dynamic term","days)"]): return "Debt"
            if "hybrid" in n or "balanced" in n or "arbitrage" in n or "equity savings" in n or "multi asset" in n: return "Hybrid"
            if any(x in n for x in ["index","nifty","sensex","etf","gold","silver","fund of fund","fof"]): return "Index"
            if any(x in n for x in ["sector","pharma","bank","infra","technology","it fund","consumption","psu","manufactur","energy","health"]): return "Sectoral"
            if "focused" in n or "multi cap" in n or "multicap" in n or "value" in n or "contra" in n or "dividend yield" in n: return "Flexi Cap"
            return "Other"

        # Group and sample
        from collections import defaultdict
        grouped = defaultdict(list)
        for s in direct_growth:
            cat = categorize(s["schemeName"])
            grouped[cat].append(s)

        # Pick balanced sample
        picked = []
        categories = ["Large Cap","Mid Cap","Small Cap","Flexi Cap","ELSS","Hybrid","Debt","Index"]
        for cat in categories:
            pool = grouped.get(cat, [])[:limit_per_category]
            # sort to get most relevant (shorter names first)
            pool = sorted(pool, key=lambda x: len(x["schemeName"]))[:limit_per_category//2 if cat in ["Debt","Index"] else limit_per_category]
            picked.extend(pool)

        # If not enough, fill from remaining
        if len(picked) < 80:
            remaining = [s for s in direct_growth if s not in picked]
            picked.extend(remaining[:80-len(picked)])

        logger.info(f"Picked {len(picked)} schemes across categories")
        for cat in categories:
            logger.info(f"  {cat}: {len([p for p in picked if categorize(p['schemeName'])==cat])}")

        # Insert into DB if not exists
        inserted = 0
        for s in picked[:100]:
            exists = db.query(MutualFundScheme).filter(MutualFundScheme.amfi_code == s["schemeCode"]).first()
            if exists:
                continue
            # derive AMC from scheme name prefix
            amc = s["schemeName"].split(" ")[0] + " Mutual Fund"
            cat = categorize(s["schemeName"])
            # isin may be null
            isin = s.get("isinGrowth") or f"INF000000{str(s['schemeCode']).zfill(5)}"
            if not isin or len(isin) != 12:
                isin = f"INF{s['schemeCode']:06d}0000"[:12]
            scheme = MutualFundScheme(
                amfi_code=s["schemeCode"],
                isin=isin[:12],
                scheme_name=s["schemeName"],
                amc_name=amc,
                category=cat,
                plan_type="Direct",
                option_type="Growth",
                launch_date=date(2013,1,1),
                is_active=True,
                expense_ratio=0.6
            )
            db.add(scheme)
            inserted += 1
        db.commit()
        logger.info(f"Inserted {inserted} new schemes, total now {db.query(MutualFundScheme).count()}")
        return inserted
    finally:
        db.close()

if __name__ == "__main__":
    import asyncio
    logging.basicConfig(level=logging.INFO)
    asyncio.run(expand_universe_from_mfapi())
