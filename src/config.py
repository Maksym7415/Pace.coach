"""
Configuration for Shoe Tracker backend.
"""
import os
from pathlib import Path
from urllib.parse import quote_plus

# Load .env from project root
ENV_PATH = Path(__file__).resolve().parents[1] / ".env"
if ENV_PATH.exists():
    from dotenv import load_dotenv
    load_dotenv(ENV_PATH)

# Database: build from DB_* vars (or use DATABASE_URL if set, e.g. for Supabase)
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

# JWT
JWT_SECRET = os.environ.get("JWT_SECRET", "change-me-in-production")
JWT_EXPIRY_HOURS = int(os.environ.get("JWT_EXPIRY_HOURS", "168"))  # 7 days default

# Strava
STRAVA_CLIENT_ID = os.environ.get("STRAVA_CLIENT_ID", "206188")
STRAVA_CLIENT_SECRET = os.environ.get("STRAVA_CLIENT_SECRET", "7353335f3f5611be29eca79e26b9c8cd3352f018")
STRAVA_REDIRECT_URI = os.environ.get("STRAVA_REDIRECT_URI", "https://fab5-195-168-204-5.ngrok-free.app/api/strava/callback")
STRAVA_SCOPE = os.environ.get("STRAVA_SCOPE", "activity:read_all,activity:write")
STRAVA_WEBHOOK_VERIFY_TOKEN = os.environ.get("STRAVA_WEBHOOK_VERIFY_TOKEN", "MEs61X5Qe7PU1wP")
STRAVA_FRONTEND_REDIRECT_URL = os.environ.get(
    "STRAVA_FRONTEND_REDIRECT_URL",
    "shoe-tracker://strava/callback"
)
BACKEND_URL = os.environ.get("BACKEND_URL", "https://fab5-195-168-204-5.ngrok-free.app")
STRAVA_WEBHOOK_CALLBACK_PATH = os.environ.get(
    "STRAVA_WEBHOOK_CALLBACK_PATH",
    "/api/webhooks/strava"
)
