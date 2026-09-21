"""initial — mutual_fund_schemes + scheme_nav_data + scheme_analytics
Revision ID: 09f25513d0d9
Revises: 
Create Date: 2026-09-21 22:14:21
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
revision: str = "09f25513d0d9"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    op.create_table("mutual_fund_schemes",
        sa.Column("scheme_id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("amfi_code", sa.Integer(), nullable=False),
        sa.Column("isin", sa.String(length=12), nullable=False),
        sa.Column("scheme_name", sa.String(length=255), nullable=False),
        sa.Column("amc_name", sa.String(length=100), nullable=False),
        sa.Column("category", sa.String(length=50), nullable=False),
        sa.Column("plan_type", sa.String(length=20), nullable=False),
        sa.Column("option_type", sa.String(length=20), nullable=False),
        sa.Column("launch_date", sa.Date(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("expense_ratio", sa.Numeric(), nullable=False),
        sa.PrimaryKeyConstraint("scheme_id"),
        sa.UniqueConstraint("amfi_code"),
        sa.UniqueConstraint("isin"),
    )
    op.create_table("scheme_nav_data",
        sa.Column("time", sa.Date(), nullable=False),
        sa.Column("scheme_id", sa.Integer(), nullable=False),
        sa.Column("nav", sa.Numeric(precision=10, scale=4), nullable=False),
        sa.Column("net_assets_cr", sa.Numeric(precision=12, scale=2), nullable=True),
        sa.ForeignKeyConstraint(["scheme_id"], ["mutual_fund_schemes.scheme_id"], ),
        sa.PrimaryKeyConstraint("time", "scheme_id"),
    )
    op.create_table("scheme_analytics",
        sa.Column("scheme_id", sa.Integer(), nullable=False),
        sa.Column("computed_date", sa.Date(), nullable=False),
        sa.Column("time_horizon_years", sa.Integer(), nullable=False),
        sa.Column("cagr", sa.Numeric(), nullable=True),
        sa.Column("rolling_returns_mean", sa.Numeric(), nullable=True),
        sa.Column("rolling_returns_std", sa.Numeric(), nullable=True),
        sa.Column("sharpe_ratio", sa.Numeric(), nullable=True),
        sa.Column("sortino_ratio", sa.Numeric(), nullable=True),
        sa.Column("jensens_alpha", sa.Numeric(), nullable=True),
        sa.Column("beta", sa.Numeric(), nullable=True),
        sa.Column("upside_capture", sa.Numeric(), nullable=True),
        sa.Column("downside_capture", sa.Numeric(), nullable=True),
        sa.Column("expense_ratio", sa.Numeric(), nullable=True),
        sa.ForeignKeyConstraint(["scheme_id"], ["mutual_fund_schemes.scheme_id"], ),
        sa.PrimaryKeyConstraint("scheme_id", "computed_date", "time_horizon_years"),
    )
    # TimescaleDB hypertable — no-op on plain Postgres/Neon
    op.execute(sa.text("SELECT create_hypertable('scheme_nav_data', 'time', if_not_exists => TRUE, migrate_data => TRUE)"))

def downgrade() -> None:
    op.drop_table("scheme_analytics")
    op.drop_table("scheme_nav_data")
    op.drop_table("mutual_fund_schemes")
