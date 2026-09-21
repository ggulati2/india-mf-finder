import asyncio
from sqlalchemy.orm import Session
from app.db.database import engine, SessionLocal, init_db_sync
from app.db.models import MutualFundScheme
from datetime import date
import logging

logger = logging.getLogger(__name__)

schemes = [
    # Large Cap
    {"amfi_code": 1001, "isin": "INF109K01E25", "scheme_name": "SBI Bluechip Fund - Direct", "amc_name": "SBI Mutual Fund", "category": "Large Cap", "plan_type": "Direct", "option_type": "Growth", "launch_date": date(2006, 2, 1), "is_active": True, "expense_ratio": 0.85},
    {"amfi_code": 1002, "isin": "INF204K01F50", "scheme_name": "HDFC Top 100 Fund - Direct", "amc_name": "HDFC Mutual Fund", "category": "Large Cap", "plan_type": "Direct", "option_type": "Growth", "launch_date": date(1994, 8, 1), "is_active": True, "expense_ratio": 0.78},
    {"amfi_code": 1003, "isin": "INF109K01G22", "scheme_name": "ICICI Prudential Bluechip Fund - Direct", "amc_name": "ICICI Prudential Mutual Fund", "category": "Large Cap", "plan_type": "Direct", "option_type": "Growth", "launch_date": date(2005, 5, 1), "is_active": True, "expense_ratio": 0.72},
    {"amfi_code": 1004, "isin": "INF204K01H56", "scheme_name": "Axis Bluechip Fund - Direct", "amc_name": "Axis Mutual Fund", "category": "Large Cap", "plan_type": "Direct", "option_type": "Growth", "launch_date": date(2009, 1, 1), "is_active": True, "expense_ratio": 0.65},
    {"amfi_code": 1005, "isin": "INF109K01I28", "scheme_name": "Mirae Asset Large Cap Fund - Direct", "amc_name": "Mirae Asset Mutual Fund", "category": "Large Cap", "plan_type": "Direct", "option_type": "Growth", "launch_date": date(2010, 12, 1), "is_active": True, "expense_ratio": 0.55},
    # Mid Cap
    {"amfi_code": 1011, "isin": "INF109K01J26", "scheme_name": "Kotak Emerging Equity Fund - Direct", "amc_name": "Kotak Mahindra Mutual Fund", "category": "Mid Cap", "plan_type": "Direct", "option_type": "Growth", "launch_date": date(1998, 6, 1), "is_active": True, "expense_ratio": 0.75},
    {"amfi_code": 1012, "isin": "INF204K01K22", "scheme_name": "HDFC Mid-Cap Opportunities Fund - Direct", "amc_name": "HDFC Mutual Fund", "category": "Mid Cap", "plan_type": "Direct", "option_type": "Growth", "launch_date": date(2007, 12, 1), "is_active": True, "expense_ratio": 0.80},
    {"amfi_code": 1013, "isin": "INF109K01L24", "scheme_name": "Axis Midcap Fund - Direct", "amc_name": "Axis Mutual Fund", "category": "Mid Cap", "plan_type": "Direct", "option_type": "Growth", "launch_date": date(2009, 12, 1), "is_active": True, "expense_ratio": 0.60},
    {"amfi_code": 1014, "isin": "INF204K01L28", "scheme_name": "Kotak Emerging Equity Fund - Direct", "amc_name": "Kotak Mahindra Mutual Fund", "category": "Mid Cap", "plan_type": "Direct", "option_type": "Growth", "launch_date": date(1998, 6, 1), "is_active": True, "expense_ratio": 0.72},
    {"amfi_code": 1015, "isin": "INF109K01M24", "scheme_name": "Franklin India Prima Fund - Direct", "amc_name": "Franklin Templeton Mutual Fund", "category": "Mid Cap", "plan_type": "Direct", "option_type": "Growth", "launch_date": date(1994, 6, 1), "is_active": True, "expense_ratio": 0.85},
    # Small Cap
    {"amfi_code": 1021, "isin": "INF204K01N20", "scheme_name": "Nippon India Small Cap Fund - Direct", "amc_name": "Nippon India Mutual Fund", "category": "Small Cap", "plan_type": "Direct", "option_type": "Growth", "launch_date": date(2005, 9, 1), "is_active": True, "expense_ratio": 0.68},
    {"amfi_code": 1022, "isin": "INF109K01O22", "scheme_name": "Kotak Small Cap Fund - Direct", "amc_name": "Kotak Mahindra Mutual Fund", "category": "Small Cap", "plan_type": "Direct", "option_type": "Growth", "launch_date": date(1998, 2, 1), "is_active": True, "expense_ratio": 0.72},
    {"amfi_code": 1023, "isin": "INF204K01P24", "scheme_name": "Quant Small Cap Fund - Direct", "amc_name": "Quant Mutual Fund", "category": "Small Cap", "plan_type": "Direct", "option_type": "Growth", "launch_date": date(1996, 6, 1), "is_active": True, "expense_ratio": 0.55},
    {"amfi_code": 1024, "isin": "INF109K01Q20", "scheme_name": "SBI Small Cap Fund - Direct", "amc_name": "SBI Mutual Fund", "category": "Small Cap", "plan_type": "Direct", "option_type": "Growth", "launch_date": date(2009, 9, 1), "is_active": True, "expense_ratio": 0.65},
    {"amfi_code": 1025, "isin": "INF204K01R22", "scheme_name": "HDFC Small Cap Fund - Direct", "amc_name": "HDFC Mutual Fund", "category": "Small Cap", "plan_type": "Direct", "option_type": "Growth", "launch_date": date(2012, 1, 1), "is_active": True, "expense_ratio": 0.75},
    # Flexi Cap
    {"amfi_code": 1031, "isin": "INF204K01S28", "scheme_name": "Parag Parikh Flexi Cap Fund - Direct", "amc_name": "PPFAS Mutual Fund", "category": "Flexi Cap", "plan_type": "Direct", "option_type": "Growth", "launch_date": date(2013, 5, 1), "is_active": True, "expense_ratio": 0.52},
    {"amfi_code": 1032, "isin": "INF109K01T26", "scheme_name": "HDFC Flexi Cap Fund - Direct", "amc_name": "HDFC Mutual Fund", "category": "Flexi Cap", "plan_type": "Direct", "option_type": "Growth", "launch_date": date(1994, 8, 1), "is_active": True, "expense_ratio": 0.82},
    {"amfi_code": 1033, "isin": "INF204K01U24", "scheme_name": "ICICI Prudential Flexi Cap Fund - Direct", "amc_name": "ICICI Prudential Mutual Fund", "category": "Flexi Cap", "plan_type": "Direct", "option_type": "Growth", "launch_date": date(1999, 3, 1), "is_active": True, "expense_ratio": 0.72},
    {"amfi_code": 1034, "isin": "INF109K01V22", "scheme_name": "Quant Flexi Cap Fund - Direct", "amc_name": "Quant Mutual Fund", "category": "Flexi Cap", "plan_type": "Direct", "option_type": "Growth", "launch_date": date(1996, 6, 1), "is_active": True, "expense_ratio": 0.58},
    {"amfi_code": 1035, "isin": "INF204K01V20", "scheme_name": "Kotak Flexi Cap Fund - Direct", "amc_name": "Kotak Mahindra Mutual Fund", "category": "Flexi Cap", "plan_type": "Direct", "option_type": "Growth", "launch_date": date(1998, 12, 1), "is_active": True, "expense_ratio": 0.78},
    # Hybrid
    {"amfi_code": 1041, "isin": "INF204K01W26", "scheme_name": "HDFC Balanced Advantage Fund - Direct", "amc_name": "HDFC Mutual Fund", "category": "Hybrid", "plan_type": "Direct", "option_type": "Growth", "launch_date": date(2000, 12, 1), "is_active": True, "expense_ratio": 0.75},
    {"amfi_code": 1042, "isin": "INF109K01X24", "scheme_name": "ICICI Prudential Equity & Debt Fund - Direct", "amc_name": "ICICI Prudential Mutual Fund", "category": "Hybrid", "plan_type": "Direct", "option_type": "Growth", "launch_date": date(1998, 10, 1), "is_active": True, "expense_ratio": 0.82},
    {"amfi_code": 1043, "isin": "INF204K01Y22", "scheme_name": "Kotak Equity Arbitrage Fund - Direct", "amc_name": "Kotak Mahindra Mutual Fund", "category": "Hybrid", "plan_type": "Direct", "option_type": "Growth", "launch_date": date(2007, 6, 1), "is_active": True, "expense_ratio": 0.55},
    {"amfi_code": 1044, "isin": "INF109K01Z20", "scheme_name": "SBI Equity Hybrid Fund - Direct", "amc_name": "SBI Mutual Fund", "category": "Hybrid", "plan_type": "Direct", "option_type": "Growth", "launch_date": date(2000, 12, 1), "is_active": True, "expense_ratio": 0.80},
    {"amfi_code": 1045, "isin": "INF204K01Z28", "scheme_name": "Mirae Asset Hybrid Equity Fund - Direct", "amc_name": "Mirae Asset Mutual Fund", "category": "Hybrid", "plan_type": "Direct", "option_type": "Growth", "launch_date": date(2007, 6, 1), "is_active": True, "expense_ratio": 0.65},
]

def seed_database():
    """Seed the database with mutual fund schemes"""
    init_db_sync()
    db = SessionLocal()
    try:
        existing = db.query(MutualFundScheme).count()
        if existing > 0:
            logger.info(f"Database already has {existing} schemes. Skipping seed.")
            return
        
        for scheme_data in schemes:
            scheme = MutualFundScheme(**scheme_data)
            db.add(scheme)
        
        db.commit()
        logger.info(f"Successfully seeded {len(schemes)} mutual fund schemes")
        
        for category in ["Large Cap", "Mid Cap", "Small Cap", "Flexi Cap", "Hybrid"]:
            count = db.query(MutualFundScheme).filter(
                MutualFundScheme.category == category
            ).count()
            logger.info(f"  {category}: {count} schemes")
            
    except Exception as e:
        logger.error(f"Error seeding database: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    seed_database()
