"""FastAPI dependencies for identity module."""
from fastapi import Depends
from sqlalchemy.orm import Session

from src.core.database import get_db
from src.modules.identity.service import IdentityService


def get_identity_service(db: Session = Depends(get_db)) -> IdentityService:
    return IdentityService(db)
