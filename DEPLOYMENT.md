# Deployment — Vercel (frontend) + Render (backend) + Neon (Postgres) — 100% free tier + custom domain

> OpenRouter only routes LLM calls; it does **not** host your FastAPI/Next.js. Use **Vercel** for the Next.js frontend and **Render** (or Koyeb) for the FastAPI backend; **Neon** for the Postgres with serverless pooling.

---

## 0) Prerequisites

- GitHub repo (this project)
- Accounts: [Neon](https://neon.tech) (free Postgres), [Render](https://render.com) (free web service), [Vercel](https://vercel.com) (free Next.js)
- Custom domain `mydomain.com` with DNS access (e.g., Cloudflare / Namecheap)

---

## 1) Push to GitHub

```bash
git remote add origin https://github.com/<you>/india-mf-finder.git
git branch -M main
git push -u origin main
```

---

## 2) Link Neon PostgreSQL (`DATABASE_URL`)

1. Neon → New Project → Region **Singapore** (closest to India) → Create.
2. Copy the **Pooled connection string** (ends with `?sslmode=require`). Example:
   ```
   postgresql://neondb_owner:xxx@ep-xxx.ap-southeast-1.aws.neon.tech/neondb?sslmode=require&channel_binding=require
   ```
   The pooled host (`-pooler`) is required for serverless — pooling is configured in `backend/app/db/database.py:13` (`pool_size=3`, `pool_pre_ping=True`, `pool_recycle=300`).
3. Save it as `DATABASE_URL` for the next steps.
4. Locally, `alembic upgrade head` will run automatically on Render startup via `backend/Dockerfile:26` (`alembic upgrade head && gunicorn ...`). No manual migration needed. TimescaleDB `create_hypertable` is a no-op on Neon.

To test locally:
```bash
export DATABASE_URL='postgresql://...'
alembic upgrade head
python backend/app/etl/amfi_nav_ingest.py
```

---

## 3) Deploy backend to Render with one click (`render.yaml`)

This repo includes `render.yaml` (Infrastructure as Code) at the root.

1. Render Dashboard → **New + → Blueprint** → Connect your GitHub repo.
2. Render detects `render.yaml` → shows service `india-mf-finder-api` (Docker, `backend/Dockerfile`, `python:3.12-slim` + `gunicorn -k uvicorn.workers.UvicornWorker -w 2`).
3. Set **Environment variables** in Render (or in `render.yaml` `envVars`):
   - `DATABASE_URL` → paste Neon pooled URL (mark **Sync: false** if you want to set it manually in dashboard)
   - `OPENAI_API_KEY` → your OpenRouter/OpenAI key (optional; chat falls back to heuristic without it)
   - `REDIS_URL` → leave empty on free tier (caching disabled) or add Upstash Redis free URL
   - `CORS_ORIGINS` → `https://app.mydomain.com,https://*.vercel.app`
   - `NEXT_PUBLIC_API_URL` → `https://india-mf-finder-api.onrender.com`
4. **Deploy**. Health check is `GET /healthz` (`backend/app/main.py:87`) — Render will not mark it unhealthy during cold starts.
   - Also available: `/health` and `/api/v1/health`.

Render free tier spins down after 15 min idle — first request after idle takes ~30s. The daily GitHub Action pings `/healthz` to keep it warm (optional).

To use **Neon** instead of Render’s free Postgres, delete the `databases:` block in `render.yaml` and set `DATABASE_URL` manually to your Neon pooled URL.

---

## 4) Deploy frontend to Vercel and map custom domain

`vercel.json` at the root is already configured (`framework: nextjs`, `outputDirectory: frontend/.next`, security headers).

**Option A — Vercel Dashboard (recommended):**
1. Vercel → **Add New Project** → Import GitHub repo.
2. **Root Directory:** leave empty (monorepo). Build Command is overridden in `vercel.json`: `cd frontend && npm ci && npm run build`. Output is `frontend/.next`.
3. **Environment Variables** → Add `NEXT_PUBLIC_API_URL` = `https://india-mf-finder-api.onrender.com`.
4. Deploy.

**Option B — CLI:**
```bash
npm i -g vercel
vercel --prod
```

**Custom domain** (`app.mydomain.com` + `api.mydomain.com`):

- **Frontend** (`app.mydomain.com`): Vercel → Project → Settings → Domains → Add `app.mydomain.com` → Add the shown `CNAME` (`cname.vercel-dns.com`) in your DNS provider. Vercel auto-provisions HTTPS.
- **Backend** (`api.mydomain.com`): Render → Service `india-mf-finder-api` → Settings → Custom Domains → Add `api.mydomain.com` → Add the shown `CNAME` (`<service>.onrender.com`) in DNS. Then update:
  - Vercel env `NEXT_PUBLIC_API_URL` → `https://api.mydomain.com`
  - Render env `NEXT_PUBLIC_API_URL` and `CORS_ORIGINS` to match `https://app.mydomain.com`
  - Redeploy both.

For `www.mydomain.com` → add a redirect in your DNS or Vercel domain settings to `app.mydomain.com`.

---

## 5) Automated daily ETL (GitHub Actions, 17:30 UTC)

`.github/workflows/daily_etl.yml` runs every night at **17:30 UTC = 23:00 IST**:

```yaml
on:
  schedule:
    - cron: "30 17 * * *"
```

- Checks out repo, `pip install -r backend/requirements.txt`, then `python backend/app/etl/amfi_nav_ingest.py` which fetches `https://www.amfiindia.com/spages/NAVAll.txt` and upserts into `scheme_nav_data`.
- Needs repo secret `DATABASE_URL` (Neon pooled URL): GitHub → Settings → Secrets → **Actions** → New repository secret → `DATABASE_URL`.
- Manual trigger: Actions tab → `daily-etl` → **Run workflow**.
- Also pings `https://india-mf-finder-api.onrender.com/healthz` to keep Render warm.

To verify: Actions → latest run → logs should show `DB ready, ingesting AMFI NAVAll.txt ... Done.`

---

## 6) Verify

- Backend: `https://api.mydomain.com/healthz` → `{"status":"ok"}`
- Backend docs: `https://api.mydomain.com/docs`
- Frontend: `https://app.mydomain.com` → Discover → Find Funds
- Logs: Render → Logs, Vercel → Deployments → Logs, GitHub → Actions

---

## Free-tier limits & notes

- **Neon free:** 0.5 GB storage, 5 concurrent connections — hence `pool_size=3` in `database.py:18`.
- **Render free:** 512 MB RAM, 750 hrs/month, spins down after 15 min idle (first hit slow). Use `alembic upgrade head` on startup, not at build time.
- **Vercel free:** 100 GB bandwidth, serverless functions for `/api/*` proxies.
- **GitHub Actions free:** 2,000 minutes/month — daily ETL is ~2 min.
