"""
JWT authentication helpers.
"""
from datetime import datetime, timedelta, timezone
from functools import wraps

import jwt
from flask import request, jsonify

from src.config import JWT_SECRET, JWT_EXPIRY_HOURS


def create_token(user_id: int) -> str:
    """Create a JWT for the given user_id."""
    payload = {
        "sub": str(user_id),  # RFC 7519 requires sub to be a string
        "exp": datetime.now(timezone.utc) + timedelta(hours=JWT_EXPIRY_HOURS),
        "iat": datetime.now(timezone.utc),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm="HS256")


def decode_token(token: str) -> int | None:
    """Decode JWT and return user_id, or None if invalid."""
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=["HS256"])
        sub = payload.get("sub")
        if sub is None:
            return None
        return int(sub)
    except jwt.InvalidTokenError:
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
