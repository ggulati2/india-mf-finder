"""Import official holdings + SEBI Riskometer from AMC monthly disclosures (currently: Nippon India).

  python scripts/import_portfolios.py            # downloads the latest month
  python scripts/import_portfolios.py FILE.xlsx YYYY-MM-DD   # use a local file

Prints match statistics; review `unmatched`, `holdings_rejected` and `riskometer_unrecognised`.
"""
import sys
from datetime import datetime
from app.db.database import SessionLocal, init_db_sync
from app.etl.amc_portfolio import import_nippon

if __name__ == "__main__":
    init_db_sync()
    db = SessionLocal()
    if len(sys.argv) == 3:
        res = import_nippon(db, path=sys.argv[1], as_of=datetime.strptime(sys.argv[2], "%Y-%m-%d").date())
    else:
        res = import_nippon(db)
    for k, v in res.items():
        print(k, v)
