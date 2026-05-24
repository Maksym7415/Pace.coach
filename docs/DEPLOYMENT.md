# GCP + Supabase Deployment Guide for Shoe Tracker

## Local Development

`docker-compose.yml` provides a **db-only** PostgreSQL service for local development:

```bash
docker compose up -d
# Then: DATABASE_URL=postgresql://shoe_tracker:shoe_tracker@localhost:5432/shoe_tracker ./run.sh
```

Production uses Supabase for the database (see below).

---

## Architecture Overview

```mermaid
flowchart LR
    subgraph supabase [Supabase]
        PG[(PostgreSQL)]
    end
    subgraph gcp [GCP]
        CR[Cloud Run]
    end
    Client[Client / Frontend] --> CR
    CR -->|DATABASE_URL| PG
    Strava[Strava Webhooks] --> CR
```

---

## Phase 1: Supabase Database Setup

### 1.1 Create Supabase Project

1. Go to [supabase.com](https://supabase.com) and sign in / create account
2. Click **New Project** → choose org, name (e.g. `shoe-tracker`), set database password
3. Select region closest to your GCP Cloud Run region
4. Wait for project provisioning

### 1.2 Get Connection Strings

1. In Supabase dashboard: **Project Settings** → **Database**
2. Copy **Connection string** → **URI** (Direct connection)
3. For Cloud Run (serverless), use **Connection pooling** (Transaction mode) if you expect many concurrent connections. Supabase provides:
   - **Direct**: `postgresql://postgres:[PASSWORD]@db.[PROJECT_REF].supabase.co:5432/postgres`
   - **Pooled** (recommended for Cloud Run): `postgresql://postgres.[PROJECT_REF]:[PASSWORD]@aws-0-[REGION].pooler.supabase.com:6543/postgres`
4. Replace `[PASSWORD]` with your actual database password

### 1.3 Run Migrations Against Supabase

From the repo root with `DATABASE_URL` set to the Supabase URI:

```bash
export DATABASE_URL="postgresql://postgres.[PROJECT_REF]:[PASSWORD]@aws-0-[REGION].pooler.supabase.com:6543/postgres"
cd backend && alembic -c alembic.ini upgrade head
```

---

## Phase 2: GCP Setup

### 2.1 Prerequisites

- [Google Cloud SDK (gcloud)](https://cloud.google.com/sdk/docs/install)
- Docker installed locally
- GCP project created at [console.cloud.google.com](https://console.cloud.google.com)

### 2.2 Enable APIs and Configure

```bash
gcloud config set project YOUR_PROJECT_ID
gcloud services enable run.googleapis.com
gcloud services enable artifactregistry.googleapis.com
```

### 2.3 Authentication

```bash
gcloud auth login
gcloud auth configure-docker
```

---

## Phase 3: Production App Artifacts

### 3.1 Production ASGI Server

The backend is **FastAPI**. Production runs via **Gunicorn + Uvicorn worker** (see `backend/Dockerfile`).

### 3.2 Dockerfile

`backend/Dockerfile`:

- Uses `python:3.12-slim` base image
- Installs dependencies from `backend/pyproject.toml`
- Binds Gunicorn + Uvicorn worker to `$PORT` (Cloud Run uses 8080 by default)
- Uses 1 worker with 8 threads (suitable for Cloud Run's per-instance scaling)
- Sets `--timeout 0` to avoid killing long-running Strava webhook processing

### 3.3 .dockerignore

A `.dockerignore` file excludes `.env`, `.venv`, and other local artifacts from the Docker build.

---

## Phase 4: Deploy to Cloud Run

### 4.1 Build and Deploy (from project root)

Deploy from the `backend/` directory context:

```bash
gcloud run deploy shoe-tracker-api \
  --source backend \
  --region YOUR_REGION \
  --allow-unauthenticated \
  --set-env-vars "DATABASE_URL=postgresql://...,JWT_SECRET=your-secret,BACKEND_URL=https://shoe-tracker-xxx.run.app"
```

Or use **Secret Manager** for sensitive env vars (recommended):

```bash
# Create secrets first
echo -n "your-jwt-secret" | gcloud secrets create JWT_SECRET --data-file=-
echo -n "postgresql://..." | gcloud secrets create DATABASE_URL --data-file=-

# Deploy with secrets
gcloud run deploy shoe-tracker-api \
  --source backend \
  --region us-central1 \
  --allow-unauthenticated \
  --set-env-vars "BACKEND_URL=https://shoe-tracker-xxx.run.app,STRAVA_CLIENT_ID=...,STRAVA_CLIENT_SECRET=..." \
  --set-secrets "DATABASE_URL=DATABASE_URL:latest,JWT_SECRET=JWT_SECRET:latest"
```

### 4.2 Required Environment Variables

| Variable                       | Source                                                  | Required           |
| ------------------------------ | ------------------------------------------------------- | ------------------ |
| `DATABASE_URL`                 | Supabase pooled URI                                     | Yes                |
| `JWT_SECRET`                   | Generate secure random string                           | Yes                |
| `BACKEND_URL`                  | Cloud Run URL (e.g. `https://shoe-tracker-xxx.run.app`) | Yes                |
| `STRAVA_CLIENT_ID`             | Strava API                                              | Yes (for Strava)   |
| `STRAVA_CLIENT_SECRET`         | Strava API                                              | Yes (for Strava)   |
| `STRAVA_REDIRECT_URI`          | `{BACKEND_URL}/api/strava/callback`                     | Yes (for Strava)   |
| `STRAVA_WEBHOOK_VERIFY_TOKEN`  | Your chosen token                                       | Yes (for webhooks) |
| `STRAVA_FRONTEND_REDIRECT_URL` | Frontend callback URL                                   | Yes (for Strava)   |
| `JWT_EXPIRY_HOURS`             | Optional (default 168)                                  | No                 |

---

## Phase 5: Strava Webhook Configuration

1. After deployment, note your Cloud Run URL (e.g. `https://shoe-tracker-api-xxx.run.app`)
2. In Strava API settings:
   - **Authorization Callback Domain**: add the domain (e.g. `shoe-tracker-api-xxx.run.app`)
   - **Webhook**: set callback URL to `https://YOUR_CLOUD_RUN_URL/api/webhooks/strava`
3. Run `python -m scripts.subscribe_strava` from `backend/` to register the webhook subscription (with `BACKEND_URL` and `STRAVA_WEBHOOK_VERIFY_TOKEN` set)

---

## Phase 6: Post-Deployment Verification

1. **Health check**: `curl https://YOUR_CLOUD_RUN_URL/api/health`
2. **Auth**: Test `POST /api/auth/register` and `POST /api/auth/login`
3. **Strava**: Verify OAuth flow and webhook reachability

---

## Security-related configuration

- Set `APP_ENV=production` on Cloud Run so missing secrets fail fast, CORS uses only `FRONTEND_WEB_ORIGIN`, and the dev server is never used in production (Gunicorn: `gunicorn src.api.app:app -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8080`).
- **Required in production**: `JWT_SECRET`, `BACKEND_URL`, Strava variables you rely on (`STRAVA_CLIENT_ID`, `STRAVA_CLIENT_SECRET`, `STRAVA_WEBHOOK_VERIFY_TOKEN`, `STRAVA_REDIRECT_URI`, etc.), and `DATABASE_URL`.
- Prefer **token encryption at rest** for Strava OAuth tokens: set `ENCRYPTION_KEY` to a Fernet key (see `.env.example`). Manage all secrets via your platform’s secret manager, not committed files.
- After enabling JWT `aud` verification, existing sessions may need to sign in again once; optional `JWT_AUDIENCE` defaults to `shoe-tracker-api`.

---

## Deployment Flow (Summary)

```mermaid
sequenceDiagram
    participant Dev as Developer
    participant Supabase as Supabase
    participant GCP as Cloud Run
    participant Strava as Strava

    Dev->>Supabase: 1. Create project, get DATABASE_URL
    Dev->>Supabase: 2. Run alembic upgrade head
    Dev->>GCP: 3. gcloud run deploy
    GCP->>GCP: 4. Build image, deploy
    Dev->>Strava: 5. Update callback URLs, subscribe webhook
    Dev->>GCP: 6. Verify /api/health
```
