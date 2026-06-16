"""FastAPI dependencies for coaching module."""
from fastapi import Depends
from sqlalchemy.orm import Session

from src.core.database import get_db
from src.modules.coaching.service import CoachingService


def get_coaching_service(db: Session = Depends(get_db)) -> CoachingService:
    return CoachingService(db)
