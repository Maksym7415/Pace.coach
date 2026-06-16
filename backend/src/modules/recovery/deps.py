"""FastAPI dependencies for recovery module."""
from fastapi import Depends
from sqlalchemy.orm import Session

from src.core.database import get_db
from src.modules.recovery.service import RecoveryService


def get_recovery_service(db: Session = Depends(get_db)) -> RecoveryService:
    return RecoveryService(db)
