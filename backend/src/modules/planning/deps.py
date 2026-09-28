"""FastAPI dependencies for the planning module."""
from fastapi import Depends
from sqlalchemy.orm import Session

from src.core.database import get_db
from src.modules.planning.service import PlanningService


def get_planning_service(db: Session = Depends(get_db)) -> PlanningService:
    return PlanningService(db)
