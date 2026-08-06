"""Domain value objects for workout execution matching."""
from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from src.modules.execution.enums import EvidenceCapability, StepExecutionStatus
from src.modules.fit_parser.models import DeviceWorkout, FitEvent, TrackPoint
from src.modules.training.workout_steps import DurationType, StepType, TargetType


class EvidenceSegment(BaseModel):
    """Neutral segment derived from device evidence (typically a lap)."""

    segment_id: str
    lap_number: int | None = None
    message_index: int | None = None
    start_time: datetime | None = None
    end_time: datetime | None = None
    duration_elapsed_s: float | None = None
    duration_moving_s: float | None = None
    distance_m: float | None = None
    device_step_index: int | None = None
    lap_trigger: str | None = None
    intensity: str | None = None


class ActivityEvidence(BaseModel):
    """Vendor-normalized facts extracted from a device file. Input to matching."""

    vendor: str
    activity_id: int | None = None
    start_time: datetime | None = None
    end_time: datetime | None = None
    sport: str | None = None
    segments: list[EvidenceSegment] = Field(default_factory=list)
    timeline: list[TrackPoint] = Field(default_factory=list)
    markers: list[FitEvent] = Field(default_factory=list)
    device_plan: DeviceWorkout | None = None
    capabilities: set[EvidenceCapability] = Field(default_factory=set)


class ResolvedStepTarget(BaseModel):
    target_type: TargetType | None = None
    target_min: float | None = None
    target_max: float | None = None
    target_zone_id: int | None = None
    target_zone_name: str | None = None


class ResolvedOccurrence(BaseModel):
    """One concrete planned execution of an authored step (after repeat expansion)."""

    authored_step_id: str
    occurrence_path: str
    occurrence_ordinal: int
    step_type: StepType
    duration_type: DurationType
    duration_min: int | None = None
    distance_m: int | None = None
    target: ResolvedStepTarget = Field(default_factory=ResolvedStepTarget)
    notes: str | None = None
    template_step_id: str | None = None


class ResolvedPlanNode(BaseModel):
    """Tree node: either a leaf step or a repeat block (supports nesting)."""

    kind: str  # "step" | "repeat"
    id: str
    step: ResolvedOccurrence | None = None
    repeat_count: int | None = None
    children: list[ResolvedPlanNode] = Field(default_factory=list)


class ResolvedPlan(BaseModel):
    """Resolved workout plan: tree for structure + flat occurrences for matching."""

    workout_id: int | None = None
    sport_code: str | None = None
    tree: list[ResolvedPlanNode] = Field(default_factory=list)
    occurrences: list[ResolvedOccurrence] = Field(default_factory=list)


class PlanCorrelationResult(BaseModel):
    """Alignment between Pace.coach ResolvedPlan and device-embedded workout."""

    confidence: float
    mapping: dict[str, int] = Field(default_factory=dict)  # authored_step_id -> device message_index
    divergences: list[dict[str, Any]] = Field(default_factory=list)
    trusted_by_id: bool = False


class RejectedCandidate(BaseModel):
    reason_code: str
    details: dict[str, Any] = Field(default_factory=dict)


class MatchEvidence(BaseModel):
    """Why we believe a window corresponds to a planned occurrence. Structured claims only."""

    strategy_id: str
    capabilities_used: list[str] = Field(default_factory=list)
    device_step_index: int | None = None
    repeat_cycle_run: int | None = None
    prior_runs_of_same_index: int | None = None
    lap_ids: list[str] = Field(default_factory=list)
    lap_message_indexes: list[int] = Field(default_factory=list)
    lap_triggers: list[str] = Field(default_factory=list)
    trackpoint_index_start: int | None = None
    trackpoint_index_end: int | None = None
    plan_correlation: dict[str, Any] | None = None
    rejected_candidates: list[RejectedCandidate] = Field(default_factory=list)
    capability_gaps: list[str] = Field(default_factory=list)
    negative_claim: bool = False
    details: dict[str, Any] = Field(default_factory=dict)


class ExecutionWindow(BaseModel):
    """Contiguous time range for one occurrence. Nothing else."""

    started_at: datetime
    ended_at: datetime
    authored_step_id: str
    occurrence_path: str
    occurrence_ordinal: int
    confidence: float


class SegmentMatch(BaseModel):
    """Co-produced output of a segmentation strategy for one occurrence."""

    window: ExecutionWindow | None = None
    evidence: MatchEvidence
    status: StepExecutionStatus
    occurrence: ResolvedOccurrence


class ExecutionMetrics(BaseModel):
    """Measurements derived from an ExecutionWindow over the timeline."""

    duration_moving_s: float | None = None
    duration_elapsed_s: float | None = None
    distance_m: float | None = None
    target_metric: str | None = None
    time_in_target_pct: float | None = None
    target_deviation_pct: float | None = None
    metrics: dict[str, Any] = Field(default_factory=dict)


class ExecutionScore(BaseModel):
    """Per-occurrence score with independently nullable dimensions."""

    score: float | None = None
    completion: float | None = None
    intensity_adherence: float | None = None
    execution_quality: float | None = None
    components: dict[str, Any] = Field(default_factory=dict)


class ExecutionIssueDraft(BaseModel):
    code: str
    severity: str
    dimension: str
    authored_step_id: str | None = None
    occurrence_ordinal: int | None = None
    payload: dict[str, Any] = Field(default_factory=dict)


class InsightClaim(BaseModel):
    """Confidence-gated claim derived from issues + MatchEvidence."""

    code: str
    claim_type: str
    authored_step_id: str | None = None
    occurrence_ordinal: int | None = None
    suppressed: bool = False
    suppression_reason: str | None = None
    payload: dict[str, Any] = Field(default_factory=dict)
    text_key: str | None = None
