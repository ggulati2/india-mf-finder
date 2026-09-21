from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from app.db.database import init_db, init_db_sync, get_db
from app.db.models import MutualFundScheme, SchemeNAVData, SchemeAnalytics
from app.etl.amfi_etl import ingest_amfi_nav_data, ingest_portfolio_holdings
from app.worker import celery_app
from app.api import schemes_router, recommendations_router, analytics_router, overlap_router
import logging
import asyncio

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        init_db_sync()
        logger.info("Database initialized")
    except Exception as e:
        logger.warning(f"Database not available: {e}. Running without DB.")

    # Schedule daily ETL jobs
    try:
        from apscheduler.schedulers.background import BackgroundScheduler
        scheduler = BackgroundScheduler()
        scheduler.add_job(
            ingest_amfi_nav_data,
            'cron',
            hour=9,
            minute=30,
            id='amfi_nav_etl'
        )
        scheduler.add_job(
            ingest_portfolio_holdings,
            'cron',
            day=1,
            hour=10,
            minute=0,
            id='portfolio_etl'
        )
        scheduler.start()
    except Exception as e:
        logger.warning(f"Could not schedule ETL jobs: {e}")

    yield

app = FastAPI(
    title="India Mutual Fund Finder API",
    description="AI-powered mutual fund recommendation & analytics tool",
    version="1.0.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(
    schemes_router, prefix="/api/v1/schemes", tags=["Schemes"]
)
app.include_router(
    recommendations_router, prefix="/api/v1/recommendations", tags=["Recommendations"]
)
app.include_router(
    analytics_router, prefix="/api/v1/analytics", tags=["Analytics"]
)
app.include_router(
    overlap_router, prefix="/api/v1/overlap", tags=["Overlap Analysis"]
)

@app.get("/api/v1/health")
async def health_check():
    return {"status": "healthy"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
