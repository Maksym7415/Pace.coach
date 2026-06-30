"""Pydantic request schemas for training endpoints."""
from __future__ import annotations

from datetime import date
from typing import Any

from pydantic import BaseModel, Field, field_validator

from src.modules.training.models import WorkoutType
from src.modules.training.workout_steps import RepeatBlockModel, WorkoutStepModel, parse_step_item


class WorkoutWriteRequest(BaseModel):
    """Shared fields for create and update."""

    scheduled_date: date
    sport_id: int = Field(..., ge=1)
    workout_type: WorkoutType = WorkoutType.easy
    title: str = Field(..., min_length=1, max_length=255)
    description: str | None = None
    steps: list[WorkoutStepModel | RepeatBlockModel] = Field(..., min_length=1)

    @field_validator("steps", mode="before")
    @classmethod
    def parse_steps(cls, value: Any) -> list[Any]:
        if not isinstance(value, list):
            raise ValueError("steps must be a list")
        return [parse_step_item(item) if isinstance(item, dict) else item for item in value]


class WorkoutCreateRequest(WorkoutWriteRequest):
    athlete_id: int


class WorkoutUpdateRequest(WorkoutWriteRequest):
    pass


class WorkoutCompleteRequest(BaseModel):
    notes: str | None = None
