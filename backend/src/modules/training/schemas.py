"""Pydantic request schemas for training endpoints."""
from datetime import date

from pydantic import BaseModel, Field

from src.modules.training.models import WorkoutType


class WorkoutCreateRequest(BaseModel):
    athlete_id: int
    scheduled_date: date
    workout_type: WorkoutType
    title: str = Field(..., min_length=1, max_length=255)
    description: str | None = None
    steps: dict | None = None
    duration_min: int | None = Field(None, ge=1)
    distance_m: int | None = Field(None, ge=1)


class WorkoutCompleteRequest(BaseModel):
    notes: str | None = None
