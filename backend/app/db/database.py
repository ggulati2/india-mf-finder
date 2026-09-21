from sqlalchemy import create_engine, Column, Integer, String, Date, Boolean, Numeric, ForeignKey, UniqueConstraint, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from datetime import date
import os
from typing import Generator, Iterator

Base = declarative_base()

# Database connection string
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://mfinder:mfinder_password@localhost:5432/mfinder")

# Create engine with appropriate settings for TimescaleDB
engine = create_engine(
    DATABASE_URL,
    echo=True,
    pool_size=10,
    max_overflow=20,
    pool_timeout=30,
    pool_recycle=1800
)

# Session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db() -> Generator:
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()

async def init_db():
    """Initialize database tables and TimescaleDB hypertable"""
    from app.db.models import MutualFundScheme, SchemeNAVData, SchemeAnalytics

    # Create all tables
    Base.metadata.create_all(bind=engine)

    # Convert scheme_nav_data to TimescaleDB hypertable if it exists
    try:
        with engine.connect() as conn:
            result = conn.execute(text("SELECT to_regclass('scheme_nav_data')")).scalar()
            if result:
                conn.execute(text("SELECT create_hypertable('scheme_nav_data', 'time', chunk_time='7 days')"))
                print("Created TimescaleDB hypertable for scheme_nav_data")
    except Exception as e:
        print(f"Note: Could not create hypertable (may already exist): {e}")

    print("Database initialized")

# Alembic configuration
alembic_config = {
    'sqlalchemy.url': DATABASE_URL,
    'sqlalchemy.echo': True,
    'sqlalchemy.pool_size': 10,
    'sqlalchemy.max_overflow': 20,
}