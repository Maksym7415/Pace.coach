"""Pydantic response schemas for the WorkoutExecution read API."""
from __future__ import annotations

from datetime import date, datetime

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


class AthleteIssueResponseOut(BaseModel):
    reason: str | None = None
    reason_other: str | None = None
    notes: str | None = None
    responded_at: datetime | None = None


class ExecutionIssueOut(BaseModel):
    """Objective algorithmic finding attached to one step occurrence."""

    id: int
    code: str
    severity: str
    dimension: str
    athlete_response: AthleteIssueResponseOut | None = None


class AthleteIssueResponseIn(BaseModel):
    issue_id: int
    reason: str | None = None
    reason_other: str | None = None
    notes: str | None = None


class SaveAthleteResponsesIn(BaseModel):
    responses: list[AthleteIssueResponseIn] = Field(default_factory=list)


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
    execution_score: float | None = None
    issue_count: int
    responded_issue_count: int = 0
    workout: WorkoutStubOut
    step_executions: list[StepExecutionOut] = Field(default_factory=list)
