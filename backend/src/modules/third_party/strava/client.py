"""
Stateless Strava OAuth client for URL building and token exchange.
Per-user tokens are stored in the database via StravaService.
"""
from typing import Any
from urllib.parse import urlencode

import requests

from src.core.config import (
    STRAVA_CLIENT_ID,
    STRAVA_CLIENT_SECRET,
    STRAVA_REDIRECT_URI,
    STRAVA_SCOPE,
)


class StravaOAuthClient:
    """Stateless OAuth URL building and token exchange. No token persistence."""

    AUTH_URL = "https://www.strava.com/oauth/authorize"
    TOKEN_URL = "https://www.strava.com/oauth/token"

    def __init__(self):
        self.client_id = STRAVA_CLIENT_ID
        self.client_secret = STRAVA_CLIENT_SECRET
        self.redirect_uri = STRAVA_REDIRECT_URI
        self.scope = STRAVA_SCOPE

    def is_configured(self) -> bool:
        return bool(self.client_id and self.client_secret and self.redirect_uri)

    def ensure_configured(self) -> None:
        if not self.is_configured():
            missing = [
                n
                for n, v in [
                    ("STRAVA_CLIENT_ID", self.client_id),
                    ("STRAVA_CLIENT_SECRET", self.client_secret),
                    ("STRAVA_REDIRECT_URI", self.redirect_uri),
                ]
                if not v
            ]
            raise RuntimeError(f"Strava not configured: {', '.join(missing)}")

    def get_authorize_url(self, state: str | None = None) -> str:
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

    def exchange_code(self, code: str) -> dict[str, Any]:
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

    def refresh_access_token(self, refresh_token: str) -> dict[str, Any]:
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
