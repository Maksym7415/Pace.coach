"""
Configuration for Shoe Tracker backend.

This module centralises environment handling and provides safer defaults for
local development. In production you should provide all sensitive values via
environment variables (or your secrets manager) and avoid relying on defaults.
"""
import os
from pathlib import Path
from urllib.parse import quote_plus

# Load .env from project root (useful for local development)
ENV_PATH = Path(__file__).resolve().parents[1] / ".env"
if ENV_PATH.exists():
    from dotenv import load_dotenv

    load_dotenv(ENV_PATH)


def _get_env() -> str:
    """Return current environment name: development, test, or production."""
    # Prefer FLASK_ENV / ENV but fall back to 'development'
    return os.environ.get("APP_ENV") or os.environ.get("FLASK_ENV") or os.environ.get("ENV") or "development"


APP_ENV = _get_env()
IS_PRODUCTION = APP_ENV.lower() == "production"


# Database: build from DB_* vars (or use DATABASE_URL if set, e.g. for Supabase)
def _build_database_url() -> str:
    if url := os.environ.get("DATABASE_URL"):
        return url

    # Reasonable local defaults; in production DATABASE_URL or DB_* must be set explicitly.
    user = os.environ.get("DB_USER", "shoe_tracker")
    password = os.environ.get("DB_PASSWORD", "shoe_tracker")
    host = os.environ.get("DB_HOST", "localhost")
    port = os.environ.get("DB_PORT", "5432")
    name = os.environ.get("DB_NAME", "shoe_tracker")
    password_encoded = quote_plus(password)
    return f"postgresql://{user}:{password_encoded}@{host}:{port}/{name}"


DATABASE_URL = _build_database_url()


def _require_env(name: str) -> str:
    """
    Read a required environment variable.

    - In production, missing values raise a RuntimeError.
    - In non-production, they fall back to an empty string so that features
      depending on them can detect misconfiguration and behave accordingly.
    """
    value = os.environ.get(name)
    if value:
        return value
    if IS_PRODUCTION:
        raise RuntimeError(f"Missing required environment variable: {name}")
    # Non-production: allow missing and return empty string so callers can check.
    return ""


# JWT
_raw_jwt_secret = os.environ.get("JWT_SECRET") or ""
if IS_PRODUCTION and not _raw_jwt_secret:
    # In production we fail fast if JWT_SECRET is not provided.
    raise RuntimeError("JWT_SECRET must be set in production")

# For local development we allow a deterministic but clearly unsafe default.
JWT_SECRET = _raw_jwt_secret or "dev-only-insecure-jwt-secret"
JWT_EXPIRY_HOURS = int(os.environ.get("JWT_EXPIRY_HOURS", "168"))  # 7 days default
JWT_AUDIENCE = os.environ.get("JWT_AUDIENCE", "shoe-tracker-api")


# Strava
# These are required for Strava integration to function; when unset,
# higher layers should treat Strava as "not configured".
STRAVA_CLIENT_ID = _require_env("STRAVA_CLIENT_ID")
STRAVA_CLIENT_SECRET = _require_env("STRAVA_CLIENT_SECRET")
STRAVA_REDIRECT_URI = os.environ.get("STRAVA_REDIRECT_URI", "")
STRAVA_SCOPE = os.environ.get("STRAVA_SCOPE", "activity:read_all,activity:write")
STRAVA_WEBHOOK_VERIFY_TOKEN = _require_env("STRAVA_WEBHOOK_VERIFY_TOKEN")

# Mobile deep-link / frontend redirect. This is not secret but should still be
# configurable via environment.
STRAVA_FRONTEND_REDIRECT_URL = os.environ.get(
    "STRAVA_FRONTEND_REDIRECT_URL",
    "shoe-tracker://strava/callback",
)

# Base backend URL (OAuth callbacks, webhook subscription). Required in production.
if IS_PRODUCTION:
    BACKEND_URL = _require_env("BACKEND_URL")
else:
    BACKEND_URL = os.environ.get("BACKEND_URL", "")

STRAVA_WEBHOOK_CALLBACK_PATH = os.environ.get(
    "STRAVA_WEBHOOK_CALLBACK_PATH",
    "/api/webhooks/strava",
)
