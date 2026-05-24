"""JWT authentication helpers."""
from datetime import datetime, timedelta, timezone
from typing import Annotated, Any, Dict, Optional

import jwt
from fastapi import Depends, Header
from sqlalchemy.orm import Session

from src.core.config import JWT_AUDIENCE, JWT_EXPIRY_HOURS, JWT_SECRET
from src.core.database import get_db
from src.core.responses import error_json
from src.modules.identity.models import User


def _jwt_base_claims() -> Dict[str, Any]:
    now = datetime.now(timezone.utc)
    return {
        "iss": "shoe-tracker-backend",
        "iat": now,
    }


def create_token(user_id: int) -> str:
    claims = _jwt_base_claims()
    claims.update(
        {
            "sub": str(user_id),
            "aud": JWT_AUDIENCE,
            "exp": datetime.now(timezone.utc) + timedelta(hours=JWT_EXPIRY_HOURS),
        }
    )
    return jwt.encode(claims, JWT_SECRET, algorithm="HS256")


def decode_token(token: str) -> Optional[int]:
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


def get_current_user(
    authorization: Annotated[str | None, Header()] = None,
    db: Session = Depends(get_db),
) -> User:
    if not authorization or not authorization.startswith("Bearer "):
        raise error_json(401, "Missing or invalid Authorization header")
    token = authorization[7:]
    user_id = decode_token(token)
    if user_id is None:
        raise error_json(401, "Invalid or expired token")
    user = db.get(User, user_id)
    if user is None:
        raise error_json(401, "User not found")
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]
