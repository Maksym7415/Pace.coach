"""Pydantic request schemas for training endpoints."""
from __future__ import annotations

from datetime import date
from typing import Any

from pydantic import BaseModel, Field, field_validator, model_validator

from src.modules.training.models import WorkoutType
from src.modules.training.workout_steps import RepeatBlockModel, WorkoutStepModel, parse_step_item


def _parse_steps(value: Any) -> list[Any]:
    if not isinstance(value, list):
        raise ValueError("steps must be a list")
    return [parse_step_item(item) if isinstance(item, dict) else item for item in value]


class WorkoutIntentMixin(BaseModel):
    purpose: str | None = Field(None, max_length=255)
    target_rpe: int | None = Field(None, ge=1, le=10)


class WorkoutWriteRequest(WorkoutIntentMixin):
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
        return _parse_steps(value)


class WorkoutCreateRequest(WorkoutWriteRequest):
    athlete_id: int


class WorkoutUpdateRequest(WorkoutWriteRequest):
    pass


class WorkoutAssignRequest(WorkoutIntentMixin):
    athlete_ids: list[int] = Field(..., min_length=1)
    scheduled_dates: list[date] = Field(..., min_length=1)
    sport_id: int = Field(..., ge=1)
    workout_type: WorkoutType = WorkoutType.easy
    title: str = Field(..., min_length=1, max_length=255)
    description: str | None = None
    steps: list[WorkoutStepModel | RepeatBlockModel] = Field(..., min_length=1)

    @field_validator("steps", mode="before")
    @classmethod
    def parse_steps(cls, value: Any) -> list[Any]:
        return _parse_steps(value)

    @field_validator("athlete_ids")
    @classmethod
    def unique_athlete_ids(cls, value: list[int]) -> list[int]:
        if len(set(value)) != len(value):
            raise ValueError("athlete_ids must be unique")
        return value

    @field_validator("scheduled_dates")
    @classmethod
    def unique_dates(cls, value: list[date]) -> list[date]:
        if len(set(value)) != len(value):
            raise ValueError("scheduled_dates must be unique")
        return value

    @model_validator(mode="after")
    def cap_cartesian_product(self) -> WorkoutAssignRequest:
        if len(self.athlete_ids) * len(self.scheduled_dates) > 50:
            raise ValueError("Cannot create more than 50 workouts in one assign request")
        return self


class WorkoutTemplateWriteRequest(WorkoutIntentMixin):
    sport_id: int = Field(..., ge=1)
    workout_type: WorkoutType = WorkoutType.easy
    title: str = Field(..., min_length=1, max_length=255)
    description: str | None = None
    steps: list[WorkoutStepModel | RepeatBlockModel] = Field(..., min_length=1)

    @field_validator("steps", mode="before")
    @classmethod
    def parse_steps(cls, value: Any) -> list[Any]:
        return _parse_steps(value)


class WorkoutCompleteRequest(BaseModel):
    notes: str | None = None
