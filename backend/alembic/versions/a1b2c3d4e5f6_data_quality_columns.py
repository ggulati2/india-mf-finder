"""data quality columns: verified category/TER/history + risk metrics

Revision ID: a1b2c3d4e5f6
Revises: 09f25513d0d9
"""
from alembic import op
import sqlalchemy as sa

revision = "a1b2c3d4e5f6"
down_revision = "09f25513d0d9"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("mutual_fund_schemes", sa.Column("sebi_category", sa.String(120)))
    op.add_column("mutual_fund_schemes", sa.Column("ter_pct", sa.Numeric()))
    op.add_column("mutual_fund_schemes", sa.Column("history_start", sa.Date()))
    op.add_column("mutual_fund_schemes", sa.Column("latest_nav_date", sa.Date()))
    op.add_column("mutual_fund_schemes", sa.Column("data_flags", sa.String(255)))
    op.add_column("scheme_analytics", sa.Column("volatility", sa.Numeric()))
    op.add_column("scheme_analytics", sa.Column("max_drawdown", sa.Numeric()))
    op.add_column("scheme_analytics", sa.Column("history_years", sa.Numeric()))


def downgrade():
    for c in ("volatility", "max_drawdown", "history_years"):
        op.drop_column("scheme_analytics", c)
    for c in ("sebi_category", "ter_pct", "history_start", "latest_nav_date", "data_flags"):
        op.drop_column("mutual_fund_schemes", c)
