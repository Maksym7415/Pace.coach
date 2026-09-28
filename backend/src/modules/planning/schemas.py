"""Pydantic request schemas for planning endpoints."""
from __future__ import annotations

from datetime import date

from pydantic import BaseModel, Field

from src.modules.planning.enums import (
    MesocycleFocus,
    PlacementType,
    TrainingPlanStatus,
)
from src.modules.training.models import WorkoutType


class PlanMutationMixin(BaseModel):
    reason: str | None = Field(None, max_length=1000)
    strict: bool = False


class TrainingPlanCreateRequest(PlanMutationMixin):
    athlete_id: int = Field(..., ge=1)
    name: str = Field(..., min_length=1, max_length=255)
    goal: str | None = None
    goal_event_date: date | None = None
    start_date: date | None = None
    planning_timezone: str | None = Field(None, max_length=64)
    notes: str | None = None


class TrainingPlanUpdateRequest(PlanMutationMixin):
    name: str | None = Field(None, min_length=1, max_length=255)
    goal: str | None = None
    goal_event_date: date | None = None
    status: TrainingPlanStatus | None = None
    notes: str | None = None
    planning_timezone: str | None = Field(None, max_length=64)
    start_date: date | None = None


class MesocycleCreateRequest(PlanMutationMixin):
    name: str = Field(..., min_length=1, max_length=255)
    focus: MesocycleFocus | None = None
    intent: str | None = None
    anchor_date: date | None = None
    duration_days: int | None = Field(None, ge=1, le=28)
    microcycle_count: int | None = Field(None, ge=1, le=52)
    microcycle_duration_days: int | None = Field(None, ge=1, le=28)
    insert_at_ordinal: int | None = Field(None, ge=0)


class MesocycleUpdateRequest(PlanMutationMixin):
    name: str | None = Field(None, min_length=1, max_length=255)
    focus: MesocycleFocus | None = None
    intent: str | None = None
    anchor_date: date | None = None


class MicrocycleCreateRequest(PlanMutationMixin):
    duration_days: int = Field(7, ge=1, le=28)
    name: str | None = Field(None, max_length=255)
    intent: str | None = None
    insert_at_ordinal: int | None = Field(None, ge=0)


class MicrocycleUpdateRequest(PlanMutationMixin):
    name: str | None = Field(None, max_length=255)
    intent: str | None = None
    duration_days: int | None = Field(None, ge=1, le=28)


class ReorderRequest(PlanMutationMixin):
    ordered_ids: list[int] = Field(..., min_length=1)


class PlanItemCreateRequest(PlanMutationMixin):
    title: str = Field(..., min_length=1, max_length=255)
    intent: str | None = None
    placement_type: PlacementType | None = None
    placement_day: int | None = Field(None, ge=1, le=28)
    placement_date: date | None = None
    planned_workout_type: WorkoutType | None = None
    planned_sport_id: int | None = Field(None, ge=1)
    planned_duration_min: int | None = Field(None, ge=1, le=600)
    planned_distance_m: int | None = Field(None, ge=1, le=200000)
    insert_at_ordinal: int | None = Field(None, ge=0)


class PlanItemUpdateRequest(PlanMutationMixin):
    title: str | None = Field(None, min_length=1, max_length=255)
    intent: str | None = None
    placement_type: PlacementType | None = None
    placement_day: int | None = Field(None, ge=1, le=28)
    placement_date: date | None = None
    planned_workout_type: WorkoutType | None = None
    planned_sport_id: int | None = Field(None, ge=1)
    planned_duration_min: int | None = Field(None, ge=1, le=600)
    planned_distance_m: int | None = Field(None, ge=1, le=200000)


class AttachWorkoutRequest(PlanMutationMixin):
    workout_id: int = Field(..., ge=1)


class CoachReviewCreateRequest(PlanMutationMixin):
    source_analysis_id: int | None = Field(None, ge=1)
    content: str | None = Field(None, min_length=1, max_length=20000)
    next_cycle_focus: str | None = Field(None, max_length=2000)


class CoachReviewUpdateRequest(PlanMutationMixin):
    content: str | None = Field(None, min_length=1, max_length=20000)
    next_cycle_focus: str | None = Field(None, max_length=2000)
