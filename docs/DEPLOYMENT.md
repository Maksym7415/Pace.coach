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
    CR -->|FIT files| Storage[(Supabase Storage)]
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

`backend/.dockerignore` excludes `.env`, `.venv`, and other local artifacts from the Docker build. Cloud Run builds with `--source backend`, so the ignore file must live next to `backend/Dockerfile` (not at the repo root).

---

## Phase 4: Deploy to Cloud Run

### 4.1 Build and Deploy (from project root)

Deploy using the `backend/` directory as the build context (this picks up `backend/Dockerfile` and Gunicorn + Uvicorn):

```bash
gcloud run deploy YOUR_SERVICE_NAME \
  --source backend \
  --region YOUR_REGION \
  --allow-unauthenticated \
  --set-env-vars "APP_ENV=production,DATABASE_URL=postgresql://...,JWT_SECRET=your-secret,BACKEND_URL=https://YOUR_SERVICE-xxx.run.app"
```

Or run `./deploy-cloud-run.sh` after filling in `.env.production` with **non-secret** config (`BACKEND_URL`, `STRAVA_CLIENT_ID`, `STRAVA_REDIRECT_URI`, etc.). Sensitive values are loaded from **Secret Manager** at runtime (see below).

### 4.1a Secret Manager (required for `./deploy-cloud-run.sh`)

Create secrets once (use real values, not placeholders):

```bash
set -a && source .env.production && set +a

echo -n "$DATABASE_URL"                | gcloud secrets create DATABASE_URL --data-file=- 2>/dev/null \
  || echo -n "$DATABASE_URL"           | gcloud secrets versions add DATABASE_URL --data-file=-
echo -n "$JWT_SECRET"                  | gcloud secrets create JWT_SECRET --data-file=- 2>/dev/null \
  || echo -n "$JWT_SECRET"             | gcloud secrets versions add JWT_SECRET --data-file=-
echo -n "$ENCRYPTION_KEY"              | gcloud secrets create ENCRYPTION_KEY --data-file=- 2>/dev/null \
  || echo -n "$ENCRYPTION_KEY"         | gcloud secrets versions add ENCRYPTION_KEY --data-file=-
echo -n "$STRAVA_CLIENT_SECRET"        | gcloud secrets create STRAVA_CLIENT_SECRET --data-file=- 2>/dev/null \
  || echo -n "$STRAVA_CLIENT_SECRET"   | gcloud secrets versions add STRAVA_CLIENT_SECRET --data-file=-
echo -n "$STRAVA_WEBHOOK_VERIFY_TOKEN" | gcloud secrets create STRAVA_WEBHOOK_VERIFY_TOKEN --data-file=- 2>/dev/null \
  || echo -n "$STRAVA_WEBHOOK_VERIFY_TOKEN" | gcloud secrets versions add STRAVA_WEBHOOK_VERIFY_TOKEN --data-file=-
```

Grant the Cloud Run runtime service account access (replace with your project number):

```bash
SA="$(gcloud run services describe YOUR_SERVICE_NAME --region YOUR_REGION \
  --format='value(spec.template.spec.serviceAccountName)')"
# If empty, use: PROJECT_NUMBER-compute@developer.gserviceaccount.com

for s in DATABASE_URL JWT_SECRET ENCRYPTION_KEY STRAVA_CLIENT_SECRET STRAVA_WEBHOOK_VERIFY_TOKEN; do
  gcloud secrets add-iam-policy-binding "$s" \
    --member="serviceAccount:${SA}" \
    --role="roles/secretmanager.secretAccessor"
done
```

Then deploy:

```bash
./deploy-cloud-run.sh
```

Manual deploy equivalent:

```bash
gcloud run deploy YOUR_SERVICE_NAME \
  --source backend \
  --region YOUR_REGION \
  --allow-unauthenticated \
  --set-env-vars "APP_ENV=production,BACKEND_URL=https://YOUR_SERVICE-xxx.run.app,STRAVA_CLIENT_ID=...,STRAVA_REDIRECT_URI=..." \
  --set-secrets "DATABASE_URL=DATABASE_URL:latest,JWT_SECRET=JWT_SECRET:latest,ENCRYPTION_KEY=ENCRYPTION_KEY:latest,STRAVA_CLIENT_SECRET=STRAVA_CLIENT_SECRET:latest,STRAVA_WEBHOOK_VERIFY_TOKEN=STRAVA_WEBHOOK_VERIFY_TOKEN:latest"
```

### 4.2 Environment Variables

| Variable                       | Source / notes                                                                 | Required                    |
| ------------------------------ | ------------------------------------------------------------------------------ | --------------------------- |
| `APP_ENV`                      | Set to `production` on Cloud Run (strict env checks, production CORS)          | Yes                         |
| `DATABASE_URL`                 | Supabase pooled URI — **Secret Manager**                                       | Yes                         |
| `JWT_SECRET`                   | Generate secure random string — **Secret Manager**                             | Yes                         |
| `BACKEND_URL`                  | Cloud Run URL (e.g. `https://YOUR_SERVICE-xxx.run.app`)                      | Yes                         |
| `STRAVA_CLIENT_ID`             | Strava API                                                                     | Yes (for Strava)            |
| `STRAVA_CLIENT_SECRET`         | Strava API — **Secret Manager**                                                | Yes (for Strava)            |
| `STRAVA_REDIRECT_URI`          | `{BACKEND_URL}/api/strava/callback` (registered with Strava)                   | Yes (for Strava)            |
| `STRAVA_WEBHOOK_VERIFY_TOKEN`  | Your chosen token — **Secret Manager**                                         | Yes (for webhooks)          |
| `FRONTEND_WEB_ORIGIN`          | Browser web app origin for CORS (e.g. `https://app.example.com`)               | Yes (for browser clients)   |
| `STRAVA_FRONTEND_REDIRECT_URL` | Where `GET /api/strava/callback` redirects after token exchange                | No (defaults to `shoe-tracker://strava/callback` for React Native; set for web OAuth pages) |
| `ENCRYPTION_KEY`               | Fernet key for Strava token encryption — **Secret Manager** (see `.env.example`) | No (recommended)            |
| `JWT_EXPIRY_HOURS`             | Token lifetime in hours (default 168)                                          | No                          |
| `JWT_AUDIENCE`                 | JWT `aud` claim (default `shoe-tracker-api`)                                   | No                          |
| `SUPABASE_URL`                 | Supabase project URL (e.g. `https://YOUR_PROJECT.supabase.co`)                 | Yes (FIT upload)            |
| `SUPABASE_SERVICE_ROLE_KEY`    | Service role key — **Secret Manager**. Bypasses Storage RLS; never expose.     | Yes (FIT upload)            |
| `ACTIVITY_STORAGE_BUCKET`      | Private Storage bucket name (default `activity-files`)                         | No                          |

---

## Phase 5: Strava Webhook Configuration

1. After deployment, note your Cloud Run URL (e.g. `https://YOUR_SERVICE-xxx.run.app`)
2. In Strava API settings:
   - **Authorization Callback Domain**: add the Cloud Run host (e.g. `YOUR_SERVICE-xxx.run.app`)
   - **Webhook**: set callback URL to `https://YOUR_CLOUD_RUN_URL/api/webhooks/strava`
3. Run `python -m scripts.subscribe_strava` from `backend/` to register the webhook subscription (with `BACKEND_URL` and `STRAVA_WEBHOOK_VERIFY_TOKEN` set)

---

## Phase 6: Post-Deployment Verification

1. **Health check**: `curl https://YOUR_CLOUD_RUN_URL/api/health`
2. **Auth**: Test `POST /api/auth/register` and `POST /api/auth/login`
3. **Strava**: Verify OAuth flow and webhook reachability

---

## Security-related configuration

- Always set `APP_ENV=production` on Cloud Run so missing secrets fail fast, CORS is limited to `FRONTEND_WEB_ORIGIN`, and the dev Uvicorn server is never used (production uses Gunicorn: `gunicorn src.api.app:app -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:$PORT`).
- Manage sensitive values (`DATABASE_URL`, `JWT_SECRET`, `ENCRYPTION_KEY`, `SUPABASE_SERVICE_ROLE_KEY`) via **Secret Manager** when possible, not plain `--set-env-vars` or committed files.
- Create a **private** Storage bucket (default name `activity-files`) in the Supabase dashboard. The backend uploads FIT files with the service-role key and never serves objects publicly.
- React Native Strava OAuth does not require `STRAVA_FRONTEND_REDIRECT_URL` unless you override the default deep link (`shoe-tracker://strava/callback`); the app can also pass `redirect_uri` to `GET /api/strava/connect`.
- After enabling JWT `aud` verification, existing sessions may need to sign in again once.

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
