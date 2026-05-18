"""
Per-user Strava integration: OAuth flow, token storage in DB, token refresh.
"""
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from src.crypto_utils import encrypt_value, decrypt_value
from src.models import User, UserStrava
from src.strava_client import StravaOAuthClient


def _strava_expires_at_to_datetime(expires_at: int) -> datetime:
    """Convert Strava Unix timestamp to datetime."""
    return datetime.fromtimestamp(expires_at, tz=timezone.utc)


class StravaService:
    """Per-user Strava OAuth and token management."""

    def __init__(self, db_session: Session):
        self.db = db_session
        self.oauth = StravaOAuthClient()

    def get_authorize_url(self, user_id: int, redirect_uri: str | None = None) -> str:
        """Build OAuth URL with state=user_id (and optional redirect_uri) for callback association."""
        state = str(user_id)
        if redirect_uri:
            state = f"{state}|{redirect_uri}"
        return self.oauth.get_authorize_url(state=state)

    def exchange_code(self, code: str, state: str | None) -> UserStrava | None:
        """
        Exchange code for tokens, store in users_strava.
        state should be user_id or "user_id|redirect_uri" from the authorize URL.
        Returns UserStrava or None if state invalid.
        """
        if not state:
            return None
        user_id_str = state.split("|", 1)[0] if state else None
        if not user_id_str:
            return None
        try:
            user_id = int(user_id_str)
        except ValueError:
            return None
        user = self.db.get(User, user_id)
        if not user:
            return None

        token_data = self.oauth.exchange_code(code)
        athlete = token_data.get("athlete", {})
        strava_athlete_id = athlete.get("id")
        if not strava_athlete_id:
            return None

        expires_at = token_data.get("expires_at")
        token_expires_at = _strava_expires_at_to_datetime(expires_at) if expires_at else datetime.now(timezone.utc)

        existing = self.db.query(UserStrava).filter_by(user_id=user_id).first()
        if existing:
            existing.strava_athlete_id = strava_athlete_id
            existing.access_token = encrypt_value(token_data["access_token"])
            existing.refresh_token = encrypt_value(token_data["refresh_token"])
            existing.token_expires_at = token_expires_at
            self.db.commit()
            return existing

        us = UserStrava(
            user_id=user_id,
            strava_athlete_id=strava_athlete_id,
            access_token=encrypt_value(token_data["access_token"]),
            refresh_token=encrypt_value(token_data["refresh_token"]),
            token_expires_at=token_expires_at,
        )
        self.db.add(us)
        self.db.commit()
        return us

    def exchange_code_with_jwt_user(self, code: str, user_id: int) -> UserStrava | None:
        """Exchange code when user is known from JWT (e.g. POST callback with auth)."""
        return self.exchange_code(code, str(user_id))

    def get_tokens(self, user_id: int) -> dict | None:
        """Get valid access token for user, refreshing if expired. Returns None if not connected."""
        us = self.db.query(UserStrava).filter_by(user_id=user_id).first()
        if not us:
            return None
        expires_at = us.token_expires_at
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=timezone.utc)
        if expires_at > datetime.now(timezone.utc):
            return {
                "access_token": decrypt_value(us.access_token),
                "athlete": {"id": us.strava_athlete_id},
            }
        # Refresh
        token_data = self.oauth.refresh_access_token(decrypt_value(us.refresh_token))
        us.access_token = encrypt_value(token_data["access_token"])
        # If a new refresh token is not provided, keep the existing (already encrypted) one.
        new_refresh = token_data.get("refresh_token")
        if new_refresh:
            us.refresh_token = encrypt_value(new_refresh)
        expires_at = token_data.get("expires_at")
        if expires_at:
            us.token_expires_at = _strava_expires_at_to_datetime(expires_at)
        self.db.commit()
        return {
            "access_token": decrypt_value(us.access_token),
            "athlete": token_data.get("athlete", {"id": us.strava_athlete_id}),
        }

    def has_connection(self, user_id: int) -> bool:
        us = self.db.query(UserStrava).filter_by(user_id=user_id).first()
        return us is not None

    def get_connection_info(self, user_id: int) -> dict | None:
        """Return athlete info if connected, else None."""
        us = self.db.query(UserStrava).filter_by(user_id=user_id).first()
        if not us:
            return None
        return {"id": us.strava_athlete_id}

    def disconnect(self, user_id: int) -> bool:
        """Remove Strava link for user. Returns True if was connected."""
        us = self.db.query(UserStrava).filter_by(user_id=user_id).first()
        if us:
            self.db.delete(us)
            self.db.commit()
            return True
        return False
