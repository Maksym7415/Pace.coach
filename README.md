# Coach App (monorepo)

Adaptive endurance coaching platform with gear tracking. This repo contains:

- **`backend/`** — FastAPI API (migrated from the original Flask shoe-tracker)
- **`frontend/`** — React (Vite + TypeScript) web app for coach and athlete dashboards
- **`docs/`** — Product and technical documentation

The existing **React Native mobile app** continues to use the same REST API paths and JSON envelopes under `/api/*`.

## Quick start (local)

### 1. Database

```bash
docker compose up db -d
cp .env.example .env
```

### 2. Backend

```bash
python -m venv .venv && source .venv/bin/activate
make backend-install
make migrate
make backend-run
```

API: http://localhost:8000/api/health

### 3. Frontend

```bash
cp frontend/.env.example frontend/.env
make frontend-install
make frontend-run
```

Web app: http://localhost:5173

## Project structure

```
backend/src/
  core/           # config, db, auth, validation, rate limits
  api/            # FastAPI app factory
  modules/
    identity/     # auth, users, profile
    gear_track/   # shoes, gear, activities (legacy mobile API)
    third_party/
      strava/     # OAuth, webhooks
    coaching/     # scaffold (future)
    training/     # scaffold (future)
    recovery/     # scaffold (future)
    adaptation/   # scaffold (future)
    ai/           # scaffold (future)
frontend/src/
  app/            # shell, routing, styles
  modules/        # auth, athlete, coach, shared
```

## Backward compatibility

All legacy mobile endpoints are preserved:

- `/api/auth/*`, `/api/strava/*`, `/api/webhooks/strava`
- `/api/shoes/*`, `/api/gear/*`, `/api/activities/*`

JWT secret, claim shape, and Strava OAuth/deep-link behavior are unchanged.

Run contract smoke tests:

```bash
make backend-test
```

## Deployment

See [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md). Backend runs via gunicorn + uvicorn worker:

```bash
gunicorn src.api.app:app -k uvicorn.workers.UvicornWorker --bind :8080
```
