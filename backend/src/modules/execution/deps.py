"""FastAPI dependencies for the execution module."""
from fastapi import Depends
from sqlalchemy.orm import Session

from src.core.database import get_db
from src.modules.execution.service import WorkoutExecutionService


def get_workout_execution_service(db: Session = Depends(get_db)) -> WorkoutExecutionService:
    return WorkoutExecutionService(db)
