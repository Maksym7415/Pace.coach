"""Identity business logic: registration, login, profile, password reset."""
from __future__ import annotations

import logging
import secrets
from datetime import datetime, timedelta, timezone

import bcrypt
from sqlalchemy import select
from sqlalchemy.orm import Session

from src.core.auth import create_token
from src.core.validation import validate_password
from src.modules.identity.models import User
from src.modules.third_party.strava.models import UserStrava

logger = logging.getLogger("coach_app.identity")


def hash_password(plain: str) -> str:
    return bcrypt.hashpw(plain.encode("utf-8"), bcrypt.gensalt(rounds=12)).decode("utf-8")


def user_to_json(user: User, strava_connected: bool | None = None) -> dict:
    out = {
        "id": user.id,
        "email": user.email,
        "name": user.name,
        "avatar_url": user.avatar_url,
        "preferred_distance_unit": getattr(user, "preferred_distance_unit", None) or "km",
    }
    if strava_connected is not None:
        out["strava_connected"] = strava_connected
    return out


class IdentityService:
    def __init__(self, db: Session):
        self.db = db

    def register(self, email: str, password: str, name: str) -> tuple[dict | None, str | None, int]:
        email = email.strip().lower()
        name = name.strip()
        if not email or not password or not name:
            return None, "email, password, and name are required", 400
        pw_err = validate_password(password)
        if pw_err:
            return None, pw_err, 400
        existing = self.db.scalar(select(User).where(User.email == email))
        if existing:
            return None, "Email already registered", 409
        user = User(email=email, password_hash=hash_password(password), name=name)
        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)
        token = create_token(user.id)
        return {"token": token, "user": user_to_json(user)}, None, 201

    def login(self, email: str, password: str) -> tuple[dict | None, str | None, int]:
        email = email.strip().lower()
        if not email or not password:
            return None, "email and password are required", 400
        user = self.db.scalar(select(User).where(User.email == email))
        if not user or not bcrypt.checkpw(password.encode("utf-8"), user.password_hash.encode("utf-8")):
            logger.info("Failed login attempt for email=%s", email)
            return None, "Invalid email or password", 401
        logger.info("Successful login user_id=%s", user.id)
        token = create_token(user.id)
        return {"token": token, "user": user_to_json(user)}, None, 200

    def forgot_password(self, email: str) -> tuple[dict, str | None, int]:
        email = email.strip().lower()
        if not email:
            return {}, "email is required", 400
        user = self.db.scalar(select(User).where(User.email == email))
        if user:
            user.password_reset_token = secrets.token_urlsafe(32)
            user.password_reset_expires_at = datetime.now(timezone.utc) + timedelta(hours=1)
            self.db.commit()
        return {"message": "If the email exists, a reset link was sent"}, None, 200

    def reset_password(self, token: str, new_password: str) -> tuple[dict | None, str | None, int]:
        token = token.strip()
        if not token or not new_password:
            return None, "token and new_password are required", 400
        pw_err = validate_password(new_password)
        if pw_err:
            return None, pw_err, 400
        user = self.db.scalar(select(User).where(User.password_reset_token == token))
        if not user:
            return None, "Invalid or expired reset token", 400
        if user.password_reset_expires_at and user.password_reset_expires_at < datetime.now(timezone.utc):
            return None, "Reset token has expired", 400
        user.password_hash = hash_password(new_password)
        user.password_reset_token = None
        user.password_reset_expires_at = None
        self.db.commit()
        return {"message": "Password reset successfully"}, None, 200

    def get_me(self, user: User) -> dict:
        strava_connected = self.db.scalar(
            select(UserStrava).where(UserStrava.user_id == user.id)
        ) is not None
        return {"user": user_to_json(user, strava_connected=strava_connected)}

    def update_profile(self, user: User, data: dict) -> dict:
        if "name" in data and data["name"] is not None:
            user.name = str(data["name"]).strip() or user.name
        if "avatar_url" in data and data["avatar_url"] is not None:
            user.avatar_url = str(data["avatar_url"]).strip() or None
        if "preferred_distance_unit" in data and data["preferred_distance_unit"] is not None:
            unit = str(data["preferred_distance_unit"]).strip().lower()
            if unit in ("km", "miles"):
                user.preferred_distance_unit = unit
        self.db.commit()
        self.db.refresh(user)
        return {"user": user_to_json(user)}
