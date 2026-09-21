# India Mutual Fund Finder

An AI-powered mutual fund recommendation & analytics tool.

## Overview

This application provides mutual fund recommendations based on user investment amount, mode (Lump Sum vs SIP), investment horizon, and risk appetite using advanced mathematical models and statistical analysis.

## Stack

- **Backend**: Python 3.12, FastAPI, Pandas, NumPy, SciPy, PostgreSQL with TimescaleDB extension, Redis (for caching), and Celery/APScheduler for daily ETL jobs
- **Frontend**: Next.js (App Router), TypeScript, Tailwind CSS, Lucide React, and Recharts/Shadcn UI

## Key Features

1. **Fund Discovery**: AI-powered recommendations based on user preferences
2. **Risk-Adjusted Scoring**: Comprehensive metrics including Sharpe, Sortino, Alpha, Beta ratios
3. **Objective Composite Score (OCS)**: Category-wise scoring to avoid AMC bias
4. **Mode-Specific Analysis**: Dynamic adjustments for Lump Sum vs SIP investing
5. **Portfolio Analysis**: Scheme comparisons and overlap analysis
6. **Daily ETL**: Automatic data ingestion from AMFI

## APIs

### Schemes API (`/api/v1/schemes`)
- Get all schemes with optional filters (category, plan_type, option_type, min_rating, max_expense_ratio)
- Get scheme by ID

### Recommendations API (`/api/v1/recommendations`)
- Get top funds based on investment amount, mode, horizon, and risk appetite
- Compare schemes by IDs

### Analytics API (`/api/v1/analytics`)
- Get analytics for a specific scheme by ID
- Get analytics for all schemes in a category

### Overlap Analysis API (`/api/v1/overlap`)
- Calculate overlap matrix for a set of schemes
- Get overlap for a specific scheme with top N funds

## Database Schema

### `mutual_fund_schemes`
Core scheme information including AMC, category, plan type, option type, launch date, and status.

### `scheme_nav_data` (TimescaleDB hypertable)
Historical NAV and net asset data partitioned by date.

### `scheme_analytics`
Pre-computed analytics for different time horizons (1, 3, 5, 10 years) including returns, risk ratios, and performance metrics.

## License

This project is part of the open-source initiative to democratize financial services in India.
