"""FastAPI dependencies for training module."""
from fastapi import Depends
from sqlalchemy.orm import Session

from src.core.database import get_db
from src.modules.training.service import TrainingService


def get_training_service(db: Session = Depends(get_db)) -> TrainingService:
    return TrainingService(db)
