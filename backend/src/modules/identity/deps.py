"""FastAPI dependencies for identity module."""
from typing import Annotated, Callable

from fastapi import Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from src.core.auth import get_current_user
from src.core.database import get_db
from src.core.responses import error_json
from src.modules.identity.models import User, UserRole, UserRoleEnum
from src.modules.identity.service import IdentityService


def get_identity_service(db: Session = Depends(get_db)) -> IdentityService:
    return IdentityService(db)


def require_role(role: UserRoleEnum) -> Callable:
    """Factory returning a FastAPI dependency that enforces the given role."""

    def _check(
        user: Annotated[User, Depends(get_current_user)],
        db: Session = Depends(get_db),
    ) -> User:
        has_role = db.scalar(
            select(UserRole).where(
                UserRole.user_id == user.id,
                UserRole.role == role,
            )
        )
        if not has_role:
            raise error_json(403, f"Requires role: {role.value}")
        return user

    return _check
