"""
Stateless Strava OAuth client for URL building and token exchange.
Per-user tokens are stored in the database via StravaService.
"""
import os
from pathlib import Path
from typing import Any, Dict, Optional
from urllib.parse import urlencode

import requests
from dotenv import load_dotenv

ENV_PATH = Path(__file__).resolve().parents[1] / ".env"
if ENV_PATH.exists():
    load_dotenv(ENV_PATH)


class StravaOAuthClient:
    """Stateless OAuth URL building and token exchange. No token persistence."""

    AUTH_URL = "https://www.strava.com/oauth/authorize"
    TOKEN_URL = "https://www.strava.com/oauth/token"

    def __init__(self):
        self.client_id = os.environ.get("STRAVA_CLIENT_ID")
        self.client_secret = os.environ.get("STRAVA_CLIENT_SECRET")
        self.redirect_uri = os.environ.get("STRAVA_REDIRECT_URI")
        self.scope = os.environ.get("STRAVA_SCOPE", "activity:read_all,activity:write")

    def is_configured(self) -> bool:
        return bool(self.client_id and self.client_secret and self.redirect_uri)

    def ensure_configured(self) -> None:
        if not self.is_configured():
            missing = [
                n for n, v in [
                    ("STRAVA_CLIENT_ID", self.client_id),
                    ("STRAVA_CLIENT_SECRET", self.client_secret),
                    ("STRAVA_REDIRECT_URI", self.redirect_uri),
                ]
                if not v
            ]
            raise RuntimeError(f"Strava not configured: {', '.join(missing)}")

    def get_authorize_url(self, state: Optional[str] = None) -> str:
        self.ensure_configured()
        params = {
            "client_id": self.client_id,
            "response_type": "code",
            "redirect_uri": self.redirect_uri,
            "approval_prompt": "auto",
            "scope": self.scope,
        }
        if state:
            params["state"] = state
        return f"{self.AUTH_URL}?{urlencode(params)}"

    def exchange_code(self, code: str) -> Dict[str, Any]:
        """Exchange authorization code for tokens. Returns raw Strava response."""
        self.ensure_configured()
        response = requests.post(
            self.TOKEN_URL,
            data={
                "client_id": self.client_id,
                "client_secret": self.client_secret,
                "code": code,
                "grant_type": "authorization_code",
            },
            timeout=10,
        )
        response.raise_for_status()
        return response.json()

    def refresh_access_token(self, refresh_token: str) -> Dict[str, Any]:
        """Refresh access token. Returns raw Strava response."""
        self.ensure_configured()
        response = requests.post(
            self.TOKEN_URL,
            data={
                "client_id": self.client_id,
                "client_secret": self.client_secret,
                "grant_type": "refresh_token",
                "refresh_token": refresh_token,
            },
            timeout=10,
        )
        response.raise_for_status()
        return response.json()
