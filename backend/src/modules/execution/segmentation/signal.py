"""Vendor-neutral signal-based segmentation (change-point against planned targets)."""
from __future__ import annotations

from datetime import datetime, timedelta

from src.modules.execution.domain import (
    ActivityEvidence,
    ExecutionWindow,
    MatchEvidence,
    PlanCorrelationResult,
    RejectedCandidate,
    ResolvedOccurrence,
    ResolvedPlan,
    SegmentMatch,
)
from src.modules.execution.enums import EvidenceCapability, StepExecutionStatus
from src.modules.execution.segmentation.base import SegmentationStrategy
from src.modules.fit_parser.models import TrackPoint
from src.modules.training.workout_steps import DurationType, TargetType


def _point_target_value(point: TrackPoint, target_type: TargetType | None) -> float | None:
    if target_type is None or target_type == TargetType.none:
        return None
    if target_type == TargetType.pace:
        return point.pace
    if target_type == TargetType.heart_rate:
        return float(point.heart_rate) if point.heart_rate is not None else None
    if target_type == TargetType.power:
        return float(point.power) if point.power is not None else None
    if target_type == TargetType.cadence:
        return float(point.cadence) if point.cadence is not None else None
    return None


def _planned_duration_s(occurrence: ResolvedOccurrence) -> float | None:
    if occurrence.duration_type == DurationType.time and occurrence.duration_min is not None:
        return float(occurrence.duration_min * 60)
    return None


def _planned_distance_m(occurrence: ResolvedOccurrence) -> float | None:
    if occurrence.duration_type == DurationType.distance:
        return float(occurrence.distance_m) if occurrence.distance_m is not None else None
    return None


class SignalSegmentationStrategy(SegmentationStrategy):
    """Approximate boundaries via planned duration/distance along the timeline.

    Used when device step indexes are unavailable (Polar/Suunto/Coros, free runs).
    Boundaries are approximate by construction — MatchEvidence records that fact.
    """

    strategy_id = "signal"
    required_capabilities = {EvidenceCapability.timeline}

    def segment(
        self,
        evidence: ActivityEvidence,
        plan: ResolvedPlan,
        correlation: PlanCorrelationResult | None = None,
    ) -> list[SegmentMatch]:
        timeline = [p for p in evidence.timeline if p.timestamp is not None]
        if not timeline:
            return [
                SegmentMatch(
                    window=None,
                    evidence=MatchEvidence(
                        strategy_id=self.strategy_id,
                        negative_claim=True,
                        capability_gaps=[EvidenceCapability.timeline.value],
                        details={"reason_code": "empty_timeline"},
                    ),
                    status=StepExecutionStatus.unmatched,
                    occurrence=occ,
                )
                for occ in plan.occurrences
            ]

        matches: list[SegmentMatch] = []
        cursor = 0
        activity_start = evidence.start_time or timeline[0].timestamp
        assert activity_start is not None

        for occurrence in plan.occurrences:
            if cursor >= len(timeline):
                matches.append(
                    SegmentMatch(
                        window=None,
                        evidence=MatchEvidence(
                            strategy_id=self.strategy_id,
                            capabilities_used=[EvidenceCapability.timeline.value],
                            negative_claim=True,
                            details={"reason_code": "timeline_exhausted"},
                            capability_gaps=[
                                c.value
                                for c in (
                                    EvidenceCapability.device_step_index,
                                    EvidenceCapability.lap_structure,
                                )
                                if c not in evidence.capabilities
                            ],
                        ),
                        status=StepExecutionStatus.not_attempted,
                        occurrence=occurrence,
                    )
                )
                continue

            started = timeline[cursor].timestamp
            assert started is not None

            end_cursor = self._find_end_index(timeline, cursor, occurrence)
            if end_cursor is None or end_cursor < cursor:
                matches.append(
                    SegmentMatch(
                        window=None,
                        evidence=MatchEvidence(
                            strategy_id=self.strategy_id,
                            negative_claim=True,
                            details={"reason_code": "could_not_bound_window"},
                            rejected_candidates=[
                                RejectedCandidate(
                                    reason_code="insufficient_signal",
                                    details={"start_index": cursor},
                                )
                            ],
                        ),
                        status=StepExecutionStatus.unmatched,
                        occurrence=occurrence,
                    )
                )
                continue

            ended = timeline[end_cursor].timestamp
            assert ended is not None

            # Prefer target-signal refinement when targets exist
            refined_end = self._refine_by_target_change(
                timeline, cursor, end_cursor, occurrence
            )
            if refined_end is not None:
                end_cursor = refined_end
                ended = timeline[end_cursor].timestamp
                assert ended is not None

            matches.append(
                SegmentMatch(
                    window=ExecutionWindow(
                        started_at=started,
                        ended_at=ended,
                        authored_step_id=occurrence.authored_step_id,
                        occurrence_path=occurrence.occurrence_path,
                        occurrence_ordinal=occurrence.occurrence_ordinal,
                        confidence=0.45,
                    ),
                    evidence=MatchEvidence(
                        strategy_id=self.strategy_id,
                        capabilities_used=[EvidenceCapability.timeline.value],
                        trackpoint_index_start=cursor,
                        trackpoint_index_end=end_cursor,
                        capability_gaps=[
                            c.value
                            for c in (
                                EvidenceCapability.device_step_index,
                                EvidenceCapability.lap_structure,
                            )
                            if c not in evidence.capabilities
                        ],
                        details={
                            "boundary_method": "planned_duration_or_distance",
                            "approximate": True,
                            "target_type": (
                                occurrence.target.target_type.value
                                if occurrence.target.target_type
                                else None
                            ),
                        },
                    ),
                    status=StepExecutionStatus.executed,
                    occurrence=occurrence,
                )
            )
            cursor = end_cursor + 1

        return matches

    def _find_end_index(
        self,
        timeline: list[TrackPoint],
        start_i: int,
        occurrence: ResolvedOccurrence,
    ) -> int | None:
        start_ts = timeline[start_i].timestamp
        if start_ts is None:
            return None

        planned_s = _planned_duration_s(occurrence)
        if planned_s is not None:
            target_end = start_ts + timedelta(seconds=planned_s)
            end_i = start_i
            for i in range(start_i, len(timeline)):
                ts = timeline[i].timestamp
                if ts is None:
                    continue
                end_i = i
                if ts >= target_end:
                    return i
            return end_i

        planned_m = _planned_distance_m(occurrence)
        if planned_m is not None:
            start_dist = timeline[start_i].distance or 0.0
            end_i = start_i
            for i in range(start_i, len(timeline)):
                dist = timeline[i].distance
                if dist is None:
                    continue
                end_i = i
                if (dist - start_dist) >= planned_m:
                    return i
            return end_i

        # Open / lap_button: take until next large signal change or end
        if start_i + 1 >= len(timeline):
            return start_i
        # Default open step: remaining activity
        return len(timeline) - 1

    def _refine_by_target_change(
        self,
        timeline: list[TrackPoint],
        start_i: int,
        end_i: int,
        occurrence: ResolvedOccurrence,
    ) -> int | None:
        target = occurrence.target
        if target.target_type is None or target.target_min is None or target.target_max is None:
            return None
        # Look for sustained departure from target after mid-window as a soft boundary hint.
        # Keep planned end if no clear change; this refinement is intentionally conservative.
        mid = start_i + (end_i - start_i) // 2
        outside = 0
        for i in range(mid, end_i + 1):
            value = _point_target_value(timeline[i], target.target_type)
            if value is None:
                continue
            if value < target.target_min or value > target.target_max:
                outside += 1
            else:
                outside = 0
            if outside >= 5:
                return max(mid, i - 4)
        return None
