from app.db.database import SessionLocal, init_db_sync
from app.db.models import MutualFundScheme
from datetime import date
import logging

logger = logging.getLogger(__name__)

# Real AMFI/mfapi scheme codes verified against https://api.mfapi.in/mf
schemes = [
    # Large Cap
    {"amfi_code": 119598, "isin": "INF200K01QQ1", "scheme_name": "SBI Large Cap Fund - Direct Plan - Growth", "amc_name": "SBI Mutual Fund", "category": "Large Cap", "plan_type": "Direct", "option_type": "Growth", "launch_date": date(2006, 2, 14), "is_active": True, "expense_ratio": 0.85},
    {"amfi_code": 118825, "isin": "INF769K01AX2", "scheme_name": "Mirae Asset Large Cap Fund - Direct Plan - Growth", "amc_name": "Mirae Asset Mutual Fund", "category": "Large Cap", "plan_type": "Direct", "option_type": "Growth", "launch_date": date(2008, 4, 1), "is_active": True, "expense_ratio": 0.55},
    {"amfi_code": 120586, "isin": "INF109K01K71", "scheme_name": "ICICI Prudential Large Cap Fund - Direct Plan - Growth", "amc_name": "ICICI Prudential Mutual Fund", "category": "Large Cap", "plan_type": "Direct", "option_type": "Growth", "launch_date": date(2008, 1, 1), "is_active": True, "expense_ratio": 0.72},
    # Mid Cap
    {"amfi_code": 118989, "isin": "INF179K01NS1", "scheme_name": "HDFC Mid Cap Fund - Direct Plan - Growth Option", "amc_name": "HDFC Mutual Fund", "category": "Mid Cap", "plan_type": "Direct", "option_type": "Growth", "launch_date": date(2013, 1, 1), "is_active": True, "expense_ratio": 0.80},
    {"amfi_code": 119716, "isin": "INF200K01QT8", "scheme_name": "SBI Midcap Fund - Direct Plan - Growth", "amc_name": "SBI Mutual Fund", "category": "Mid Cap", "plan_type": "Direct", "option_type": "Growth", "launch_date": date(2013, 1, 1), "is_active": True, "expense_ratio": 0.75},
    {"amfi_code": 119071, "isin": "INF740K01534", "scheme_name": "DSP Midcap Fund - Direct Plan - Growth", "amc_name": "DSP Mutual Fund", "category": "Mid Cap", "plan_type": "Direct", "option_type": "Growth", "launch_date": date(2013, 1, 1), "is_active": True, "expense_ratio": 0.78},
    # Small Cap
    {"amfi_code": 118778, "isin": "INF204K01K15", "scheme_name": "Nippon India Small Cap Fund - Direct Plan - Growth Option", "amc_name": "Nippon India Mutual Fund", "category": "Small Cap", "plan_type": "Direct", "option_type": "Growth", "launch_date": date(2013, 1, 1), "is_active": True, "expense_ratio": 0.68},
    {"amfi_code": 120828, "isin": "INF966L01689", "scheme_name": "Quant Small Cap Fund - Direct Plan - Growth Option", "amc_name": "Quant Mutual Fund", "category": "Small Cap", "plan_type": "Direct", "option_type": "Growth", "launch_date": date(2013, 1, 1), "is_active": True, "expense_ratio": 0.55},
    {"amfi_code": 125497, "isin": "INF200K01T51", "scheme_name": "SBI Small Cap Fund - Direct Plan - Growth", "amc_name": "SBI Mutual Fund", "category": "Small Cap", "plan_type": "Direct", "option_type": "Growth", "launch_date": date(2013, 1, 1), "is_active": True, "expense_ratio": 0.65},
    {"amfi_code": 120164, "isin": "INF174K01KT2", "scheme_name": "Kotak Small Cap Fund - Direct Plan - Growth", "amc_name": "Kotak Mahindra Mutual Fund", "category": "Small Cap", "plan_type": "Direct", "option_type": "Growth", "launch_date": date(2013, 1, 1), "is_active": True, "expense_ratio": 0.72},
    # Flexi Cap
    {"amfi_code": 122639, "isin": "INF879O01027", "scheme_name": "Parag Parikh Flexi Cap Fund - Direct Plan - Growth", "amc_name": "PPFAS Mutual Fund", "category": "Flexi Cap", "plan_type": "Direct", "option_type": "Growth", "launch_date": date(2013, 5, 24), "is_active": True, "expense_ratio": 0.52},
    {"amfi_code": 118955, "isin": "INF179K01UT0", "scheme_name": "HDFC Flexi Cap Fund - Direct Plan - Growth Option", "amc_name": "HDFC Mutual Fund", "category": "Flexi Cap", "plan_type": "Direct", "option_type": "Growth", "launch_date": date(2013, 1, 1), "is_active": True, "expense_ratio": 0.82},
    {"amfi_code": 119620, "isin": "INF183K01DF3", "scheme_name": "Aditya Birla Sun Life Flexi Cap Fund - Direct Plan - Growth", "amc_name": "Aditya Birla Sun Life Mutual Fund", "category": "Flexi Cap", "plan_type": "Direct", "option_type": "Growth", "launch_date": date(2013, 1, 1), "is_active": True, "expense_ratio": 0.72},
    # Hybrid
    {"amfi_code": 118968, "isin": "INF179K01WA6", "scheme_name": "HDFC Balanced Advantage Fund - Direct Plan - Growth Option", "amc_name": "HDFC Mutual Fund", "category": "Hybrid", "plan_type": "Direct", "option_type": "Growth", "launch_date": date(2013, 1, 1), "is_active": True, "expense_ratio": 0.75},
    {"amfi_code": 120377, "isin": "INF109K012B0", "scheme_name": "ICICI Prudential Balanced Advantage Fund - Direct Plan - Growth", "amc_name": "ICICI Prudential Mutual Fund", "category": "Hybrid", "plan_type": "Direct", "option_type": "Growth", "launch_date": date(2013, 1, 1), "is_active": True, "expense_ratio": 0.82},
    {"amfi_code": 119769, "isin": "INF174K01LS4", "scheme_name": "Kotak Aggressive Hybrid Fund - Direct Plan - Growth", "amc_name": "Kotak Mahindra Mutual Fund", "category": "Hybrid", "plan_type": "Direct", "option_type": "Growth", "launch_date": date(2013, 1, 1), "is_active": True, "expense_ratio": 0.65},
]

def seed_database():
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
            count = db.query(MutualFundScheme).filter(MutualFundScheme.category == category).count()
            logger.info(f"  {category}: {count} schemes")
    except Exception as e:
        logger.error(f"Error seeding database: {e}")
        db.rollback()
        raise
    finally:
        db.close()

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    seed_database()
