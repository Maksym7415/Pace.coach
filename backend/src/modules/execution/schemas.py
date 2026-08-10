"""Pydantic response schemas for the WorkoutExecution read API."""
from __future__ import annotations

from datetime import date

from pydantic import BaseModel, Field


class PlannedStepOut(BaseModel):
    """Planned side of a matched occurrence, taken from the plan snapshot."""

    step_type: str
    duration_type: str | None = None
    duration_min: int | None = None
    distance_m: int | None = None
    target_type: str | None = None
    target_min: float | None = None
    target_max: float | None = None
    target_zone_name: str | None = None
    notes: str | None = None


class ExecutionIssueOut(BaseModel):
    """Objective algorithmic finding attached to one step occurrence."""

    id: int
    code: str
    severity: str
    dimension: str


class StepExecutionOut(BaseModel):
    """One planned occurrence matched to executed activity evidence."""

    authored_step_id: str
    occurrence_path: str
    occurrence_ordinal: int
    status: str
    planned: PlannedStepOut
    duration_moving_s: float | None = None
    distance_m: float | None = None
    target_metric: str | None = None
    time_in_target_pct: float | None = None
    target_deviation_pct: float | None = None
    score: float | None = None
    issues: list[ExecutionIssueOut] = Field(default_factory=list)


class WorkoutStubOut(BaseModel):
    id: int
    title: str
    sport_code: str | None = None
    scheduled_date: date


class WorkoutExecutionOut(BaseModel):
    """Root domain object for planned-vs-actual workout execution."""

    id: int
    workout_id: int
    activity_id: int
    status: str
    overall_confidence: float | None = None
    algorithm_version: str
    issue_count: int
    workout: WorkoutStubOut
    step_executions: list[StepExecutionOut] = Field(default_factory=list)
