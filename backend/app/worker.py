from celery import Celery
from datetime import date
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.db.models import MutualFundScheme, SchemeNAVData, SchemeAnalytics
from app.engine.scoring import compute_scheme_analytics
import pandas as pd
import logging

logger = logging.getLogger(__name__)

celery_app = Celery(
    'mfinder_tasks',
    broker='redis://redis:6379/0',
    backend='redis://redis:6379/0',
    include=['app.worker']
)

@celery_app.task(bind=True)
def compute_scheme_analytics_task(self, scheme_id: int, time_horizon_years: int):
    logger.info(f"Computing analytics for scheme {scheme_id}, horizon {time_horizon_years} years")
    try:
        db_gen = get_db()
        db = next(db_gen)
        nav_data = db.query(SchemeNAVData).filter(
            SchemeNAVData.scheme_id == scheme_id
        ).order_by(SchemeNAVData.time.desc()).all()
        if len(nav_data) < 10:
            return
        nav_df = pd.DataFrame([
            {'date': row.time, 'nav': float(row.nav)}
            for row in nav_data
        ])
        nav_df['date'] = pd.to_datetime(nav_df['date'])
        nav_df = nav_df.sort_values('date')
        scheme = db.query(MutualFundScheme).filter(
            MutualFundScheme.scheme_id == scheme_id
        ).first()
        analytics = compute_scheme_analytics(
            nav_df=nav_df, scheme=scheme, time_horizon_years=time_horizon_years
        )
        analytics_record = SchemeAnalytics(
            scheme_id=scheme_id,
            computed_date=date.today(),
            time_horizon_years=time_horizon_years,
            cagr=analytics['cagr'],
            rolling_returns_mean=analytics['rolling_returns_mean'],
            rolling_returns_std=analytics['rolling_returns_std'],
            sharpe_ratio=analytics['sharpe_ratio'],
            sortino_ratio=analytics['sortino_ratio'],
            jensens_alpha=analytics['jensens_alpha'],
            beta=analytics['beta'],
            upside_capture=analytics['upside_capture'],
            downside_capture=analytics['downside_capture'],
            expense_ratio=scheme.expense_ratio or 0.0
        )
        db.merge(analytics_record)
        next(db_gen)
        logger.info(f"Successfully computed analytics for scheme {scheme_id}")
    except Exception as e:
        logger.error(f"Error computing analytics for scheme {scheme_id}: {e}")
        raise

@celery_app.task(bind=True)
def compute_all_schemes_analytics(self):
    logger.info("Starting analytics computation for all schemes")
    db_gen = get_db()
    db = next(db_gen)
    schemes = db.query(MutualFundScheme).all()
    for scheme in schemes:
        for horizon in [1, 3, 5, 10]:
            compute_scheme_analytics_task.delay(scheme.scheme_id, horizon)
    next(db_gen)
    logger.info(f"Queued analytics computation for {len(schemes)} schemes across {len([1, 3, 5, 10])} horizons")