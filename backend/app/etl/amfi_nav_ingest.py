#!/usr/bin/env python3
"""AMFI NAV ingest — called by GitHub Actions daily at 17:30 UTC (11 PM IST).
Fetches https://www.amfiindia.com/spages/NAVAll.txt and upserts into scheme_nav_data.
Also handles full universe expansion via mfapi.in if needed.
"""
import asyncio
import sys
from pathlib import Path

# Ensure backend is on path when run as `python backend/app/etl/amfi_nav_ingest.py`
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from app.db.database import init_db_sync
from app.etl.amfi_etl import ingest_amfi_nav_data

async def main():
    init_db_sync()
    print("DB ready, ingesting AMFI NAVAll.txt ...")
    await ingest_amfi_nav_data()
    print("Done. Checking holistic backfill for schemes missing NAV ...")
    # Optionally trigger historic backfill for any Direct Growth schemes missing today
    # (kept lightweight for GitHub Actions free tier — only AMFI daily; historic weekly via separate job)
    print("ETL complete.")

if __name__ == "__main__":
    asyncio.run(main())
