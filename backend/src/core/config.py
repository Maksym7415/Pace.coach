"""
Configuration for Coach App backend.

Centralises environment handling and provides safer defaults for local development.
"""
import os
from pathlib import Path
from urllib.parse import quote_plus

# Load .env from repo root (backend/../.env) or backend/.env
_BACKEND_ROOT = Path(__file__).resolve().parents[2]
_REPO_ROOT = _BACKEND_ROOT.parent
for _env_path in (_REPO_ROOT / ".env", _BACKEND_ROOT / ".env"):
    if _env_path.exists():
        from dotenv import load_dotenv

        load_dotenv(_env_path)
        break


def _get_env() -> str:
    return os.environ.get("APP_ENV") or os.environ.get("FLASK_ENV") or os.environ.get("ENV") or "development"


APP_ENV = _get_env()
IS_PRODUCTION = APP_ENV.lower() == "production"


def _build_database_url() -> str:
    if url := os.environ.get("DATABASE_URL"):
        return url

    user = os.environ.get("DB_USER", "shoe_tracker")
    password = os.environ.get("DB_PASSWORD", "shoe_tracker")
    host = os.environ.get("DB_HOST", "localhost")
    port = os.environ.get("DB_PORT", "5432")
    name = os.environ.get("DB_NAME", "shoe_tracker")
    password_encoded = quote_plus(password)
    return f"postgresql://{user}:{password_encoded}@{host}:{port}/{name}"


DATABASE_URL = _build_database_url()

ACTIVITY_STORAGE_ROOT = Path(
    os.environ.get("ACTIVITY_STORAGE_PATH", str(_BACKEND_ROOT / "storage"))
).resolve()


def _require_env(name: str) -> str:
    value = os.environ.get(name)
    if value:
        return value
    if IS_PRODUCTION:
        raise RuntimeError(f"Missing required environment variable: {name}")
    return ""


_raw_jwt_secret = os.environ.get("JWT_SECRET") or ""
if IS_PRODUCTION and not _raw_jwt_secret:
    raise RuntimeError("JWT_SECRET must be set in production")

JWT_SECRET = _raw_jwt_secret or "dev-only-insecure-jwt-secret"
JWT_EXPIRY_HOURS = int(os.environ.get("JWT_EXPIRY_HOURS", "168"))
JWT_AUDIENCE = os.environ.get("JWT_AUDIENCE", "shoe-tracker-api")

STRAVA_CLIENT_ID = _require_env("STRAVA_CLIENT_ID")
STRAVA_CLIENT_SECRET = _require_env("STRAVA_CLIENT_SECRET")
STRAVA_REDIRECT_URI = os.environ.get("STRAVA_REDIRECT_URI", "")
STRAVA_SCOPE = os.environ.get("STRAVA_SCOPE", "activity:read_all,activity:write")
STRAVA_WEBHOOK_VERIFY_TOKEN = _require_env("STRAVA_WEBHOOK_VERIFY_TOKEN")

STRAVA_FRONTEND_REDIRECT_URL = os.environ.get(
    "STRAVA_FRONTEND_REDIRECT_URL",
    "shoe-tracker://strava/callback",
)

if IS_PRODUCTION:
    BACKEND_URL = _require_env("BACKEND_URL")
else:
    BACKEND_URL = os.environ.get("BACKEND_URL", "")

STRAVA_WEBHOOK_CALLBACK_PATH = os.environ.get(
    "STRAVA_WEBHOOK_CALLBACK_PATH",
    "/api/webhooks/strava",
)
