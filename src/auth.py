"""
JWT authentication helpers.
"""
from datetime import datetime, timedelta, timezone
from functools import wraps
from typing import Any, Dict, Optional

import jwt
from flask import request, jsonify

from src.config import JWT_SECRET, JWT_EXPIRY_HOURS, JWT_AUDIENCE


def _jwt_base_claims() -> Dict[str, Any]:
    """Common JWT claims (issuer, issued-at)."""
    now = datetime.now(timezone.utc)
    # Use a simple issuer string; in the future this could be derived from config.
    return {
        "iss": "shoe-tracker-backend",
        "iat": now,
    }


def create_token(user_id: int) -> str:
    """Create a JWT for the given user_id."""
    claims = _jwt_base_claims()
    claims.update(
        {
            "sub": str(user_id),  # RFC 7519 requires sub to be a string
            "aud": JWT_AUDIENCE,
            "exp": datetime.now(timezone.utc) + timedelta(hours=JWT_EXPIRY_HOURS),
        }
    )
    return jwt.encode(claims, JWT_SECRET, algorithm="HS256")


def decode_token(token: str) -> Optional[int]:
    """Decode JWT and return user_id, or None if invalid."""
    common = {
        "algorithms": ["HS256"],
        "issuer": "shoe-tracker-backend",
    }
    try:
        payload = jwt.decode(
            token,
            JWT_SECRET,
            audience=JWT_AUDIENCE,
            **common,
        )
    except jwt.InvalidTokenError:
        try:
            # Tokens minted before `aud` was added
            payload = jwt.decode(
                token,
                JWT_SECRET,
                options={"verify_aud": False},
                **common,
            )
        except jwt.InvalidTokenError:
            return None
    sub = payload.get("sub")
    if sub is None:
        return None
    try:
        return int(sub)
    except (TypeError, ValueError):
        return None


def require_auth(f):
    """Decorator: require valid JWT, attach request.user."""
    @wraps(f)
    def decorated(*args, **kwargs):
        auth_header = request.headers.get("Authorization")
        if not auth_header or not auth_header.startswith("Bearer "):
            return jsonify({"success": False, "error": "Missing or invalid Authorization header"}), 401
        token = auth_header[7:]
        user_id = decode_token(token)
        if user_id is None:
            return jsonify({"success": False, "error": "Invalid or expired token"}), 401
        from src.models import User
        user = User.query.get(user_id)
        if user is None:
            return jsonify({"success": False, "error": "User not found"}), 401
        request.user = user
        return f(*args, **kwargs)
    return decorated
