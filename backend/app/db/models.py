from sqlalchemy import Column, Integer, String, Date, Boolean, Numeric, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship
from datetime import date

from app.db.database import Base

class MutualFundScheme(Base):
    __tablename__ = "mutual_fund_schemes"

    scheme_id = Column(Integer, primary_key=True, autoincrement=True)
    amfi_code = Column(Integer, unique=True, nullable=False)
    isin = Column(String(12), unique=True, nullable=False)
    scheme_name = Column(String(255), nullable=False)
    amc_name = Column(String(100), nullable=False)
    category = Column(String(50), nullable=False)
    plan_type = Column(String(20), default="Direct", nullable=False)
    option_type = Column(String(20), nullable=False)
    launch_date = Column(Date, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    expense_ratio = Column(Numeric, default=0.0, nullable=False)  # legacy placeholder; use ter_pct
    # Verified fields (see DATA_QUALITY.md). NULL means "unknown", never a made-up default.
    sebi_category = Column(String(120))      # official AMFI/SEBI category from NAVAll.txt
    ter_pct = Column(Numeric)                # Direct plan total expense ratio (AMFI disclosure)
    history_start = Column(Date)             # first NAV date we hold (launch date proxy)
    latest_nav_date = Column(Date)
    data_flags = Column(String(255))         # comma-separated validation flags; non-empty = excluded
    riskometer = Column(String(30))          # official SEBI Riskometer level published by the AMC
    riskometer_as_of = Column(Date)
    riskometer_source = Column(String(120))

    nav_data = relationship("SchemeNAVData", back_populates="scheme")
    analytics = relationship("SchemeAnalytics", back_populates="scheme")

    def __repr__(self):
        return f"<MutualFundScheme(id={self.scheme_id}, name={self.scheme_name})>"

class SchemeNAVData(Base):
    __tablename__ = "scheme_nav_data"

    time = Column(Date, primary_key=True, nullable=False)
    scheme_id = Column(Integer, ForeignKey("mutual_fund_schemes.scheme_id"), primary_key=True, nullable=False)
    nav = Column(Numeric(10, 4), nullable=False)
    net_assets_cr = Column(Numeric(12, 2))

    scheme = relationship("MutualFundScheme", back_populates="nav_data")

    def __repr__(self):
        return f"<SchemeNAVData(time={self.time}, scheme_id={self.scheme_id}, nav={self.nav})>"

class SchemeAnalytics(Base):
    __tablename__ = "scheme_analytics"

    scheme_id = Column(Integer, ForeignKey("mutual_fund_schemes.scheme_id"), primary_key=True, nullable=False)
    computed_date = Column(Date, primary_key=True, nullable=False)
    time_horizon_years = Column(Integer, primary_key=True, nullable=False)
    cagr = Column(Numeric)
    rolling_returns_mean = Column(Numeric)
    rolling_returns_std = Column(Numeric)
    sharpe_ratio = Column(Numeric)
    sortino_ratio = Column(Numeric)
    jensens_alpha = Column(Numeric)
    beta = Column(Numeric)
    upside_capture = Column(Numeric)
    downside_capture = Column(Numeric)
    expense_ratio = Column(Numeric)
    volatility = Column(Numeric)      # annualised std-dev of daily returns, %
    max_drawdown = Column(Numeric)    # worst peak-to-trough fall inside the window, %
    history_years = Column(Numeric)   # actual length of the window used

    scheme = relationship("MutualFundScheme", back_populates="analytics")

    def __repr__(self):
        return f"<SchemeAnalytics(scheme_id={self.scheme_id}, computed_date={self.computed_date}, horizon={self.time_horizon_years})>"


class SchemeHolding(Base):
    """One line of an AMC's monthly portfolio disclosure (official, as published)."""
    __tablename__ = "scheme_holdings"

    id = Column(Integer, primary_key=True, autoincrement=True)
    scheme_id = Column(Integer, ForeignKey("mutual_fund_schemes.scheme_id"), index=True, nullable=False)
    as_of = Column(Date, nullable=False)
    isin = Column(String(12))
    name = Column(String(255), nullable=False)
    sector = Column(String(120))          # industry for equity, rating/instrument type for debt
    weight_pct = Column(Numeric, nullable=False)   # % of scheme NAV
    source = Column(String(120))
