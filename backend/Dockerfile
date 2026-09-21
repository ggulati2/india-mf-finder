FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# System deps for psycopg + building scipy/numpy if needed
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential libpq-dev curl \
  && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt \
 && pip install --no-cache-dir gunicorn uvicorn[standard]

COPY . .

# Non-root user for Render free tier
RUN useradd -m appuser && chown -R appuser:appuser /app
USER appuser

EXPOSE 8000

# Render provides $PORT; fallback 8000 locally
# --preload + 2 workers is safe for free tier (512 MB RAM); increase for paid
# timeout 120s for historic backfill endpoints
CMD ["sh", "-c", "alembic upgrade head && gunicorn app.main:app -k uvicorn.workers.UvicornWorker -w 2 --bind 0.0.0.0:${PORT:-8000} --timeout 120 --access-logfile - --error-logfile - --log-level info"]
