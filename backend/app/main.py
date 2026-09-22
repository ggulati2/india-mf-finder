from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from app.db.database import init_db, init_db_sync, get_db
from app.db.models import MutualFundScheme, SchemeNAVData, SchemeAnalytics
from app.etl.amfi_etl import ingest_amfi_nav_data, ingest_portfolio_holdings
from app.worker import celery_app
from app.api import schemes_router, recommendations_router, analytics_router, overlap_router
from app.api.chat import router as chat_router
from app.api.holistic import router as holistic_router
import logging
import asyncio
import os

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

_cors_origins_env = os.getenv("CORS_ORIGINS", "")
_cors_origins = [o.strip() for o in _cors_origins_env.split(",") if o.strip()] or ["http://localhost:3000"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    # allow_origins can't glob-match "*.vercel.app"; this regex covers Vercel preview/prod URLs.
    allow_origin_regex=r"https://.*\.vercel\.app",
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
app.include_router(
    chat_router, prefix="/api/v1/chat", tags=["GenAI Chat"]
)
app.include_router(
    holistic_router, prefix="/api/v1/analytics", tags=["Holistic Analytics"]
)

@app.get("/api/v1/health")
async def health_check():
    return {"status": "healthy"}

@app.get("/healthz")
async def healthz():
    return {"status": "ok"}

@app.get("/health")
async def health_alias():
    return {"status": "ok"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
