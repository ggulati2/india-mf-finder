from sqlalchemy import create_engine, Column, Integer, String, Date, Boolean, Numeric, ForeignKey, UniqueConstraint, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from datetime import date
import os
from typing import Generator, Iterator

Base = declarative_base()

# Database connection string
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./mfinder.db")

# Create engine — Neon/Supabase serverless needs small pool + SSL
if DATABASE_URL.startswith("sqlite"):
    engine = create_engine(DATABASE_URL, echo=True, connect_args={"check_same_thread": False})
else:
    # pool_size 3 is safe for Neon free tier (max 5-10 connections) + Render free (1 instance)
    # pool_pre_ping handles Neon cold starts; connect_args adds sslmode if not in URL
    connect_args = {}
    if "sslmode" not in DATABASE_URL:
        connect_args["sslmode"] = "require"
    engine = create_engine(
        DATABASE_URL,
        echo=False,
        pool_size=3,
        max_overflow=2,
        pool_timeout=30,
        pool_recycle=300,
        pool_pre_ping=True,
        connect_args=connect_args,
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

def init_db_sync():
    """Initialize database tables"""
    from app.db.models import MutualFundScheme, SchemeNAVData, SchemeAnalytics
    Base.metadata.create_all(bind=engine)
    print("Database initialized")

async def init_db():
    """Initialize database tables"""
    init_db_sync()
    print("Database initialized")

# Alembic configuration
alembic_config = {
    'sqlalchemy.url': DATABASE_URL,
    'sqlalchemy.echo': True,
    'sqlalchemy.pool_size': 10,
    'sqlalchemy.max_overflow': 20,
}