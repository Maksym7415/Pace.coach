"""FastAPI dependencies for athlete profile module."""
from fastapi import Depends
from sqlalchemy.orm import Session

from src.core.database import get_db
from src.modules.athlete_profile.service import AthleteProfileService


def get_athlete_profile_service(db: Session = Depends(get_db)) -> AthleteProfileService:
    return AthleteProfileService(db)
