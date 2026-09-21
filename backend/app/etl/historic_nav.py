import httpx
import pandas as pd
from datetime import datetime
from sqlalchemy.orm import Session
from app.db.database import SessionLocal
from app.db.models import SchemeNAVData
import logging
import asyncio

logger = logging.getLogger(__name__)

MFAPI_BASE = "https://api.mfapi.in/mf"

async def fetch_historic_nav_for_scheme(amfi_code: int, scheme_id: int, db: Session) -> int:
    """Fetch full historic NAV from mfapi.in for a single scheme and upsert."""
    url = f"{MFAPI_BASE}/{amfi_code}"
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(url)
            if resp.status_code != 200:
                logger.warning(f"mfapi {amfi_code} returned {resp.status_code}")
                return 0
            payload = resp.json()
            data = payload.get("data", [])
            if not data:
                logger.warning(f"No historic data for {amfi_code}")
                return 0
            inserted = 0
            for entry in data:
                try:
                    nav_date = datetime.strptime(entry["date"], "%d-%m-%Y").date()
                    nav_val = float(entry["nav"])
                except Exception:
                    continue
                exists = db.query(SchemeNAVData).filter(
                    SchemeNAVData.scheme_id == scheme_id,
                    SchemeNAVData.time == nav_date
                ).first()
                if not exists:
                    db.add(SchemeNAVData(time=nav_date, scheme_id=scheme_id, nav=nav_val))
                    inserted += 1
                # batch commit every 500
                if inserted % 500 == 0:
                    db.commit()
            db.commit()
            logger.info(f"Scheme {scheme_id} (code {amfi_code}): {inserted} NAV rows inserted, total {len(data)} available")
            return inserted
    except Exception as e:
        logger.error(f"Error fetching historic NAV for {amfi_code}: {e}")
        return 0

async def backfill_all_historic_nav(limit: int = 25) -> dict:
    """Backfill historic NAV for all schemes in DB (or limit)."""
    from app.db.models import MutualFundScheme
    db = SessionLocal()
    try:
        schemes = db.query(MutualFundScheme).limit(limit).all()
        total = 0
        for s in schemes:
            n = await fetch_historic_nav_for_scheme(s.amfi_code, s.scheme_id, db)
            total += n
            await asyncio.sleep(0.5)  # be nice to api
        return {"schemes": len(schemes), "rows_inserted": total}
    finally:
        db.close()
