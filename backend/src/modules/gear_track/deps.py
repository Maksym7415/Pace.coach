"""FastAPI dependencies for gear_track module."""
from fastapi import Depends
from sqlalchemy.orm import Session

from src.core.database import get_db
from src.modules.gear_track.service import GearTrackService


def get_gear_track_service(db: Session = Depends(get_db)) -> GearTrackService:
    return GearTrackService(db)
