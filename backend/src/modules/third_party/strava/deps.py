"""FastAPI dependencies for Strava module."""
from fastapi import Depends
from sqlalchemy.orm import Session

from src.core.database import get_db
from src.modules.third_party.strava.service import StravaService


def get_strava_service(db: Session = Depends(get_db)) -> StravaService:
    return StravaService(db)
