"""Garmin device-step-index segmentation with repeat-cycle detection."""
from __future__ import annotations

from datetime import datetime, timedelta

from src.modules.execution.domain import (
    ActivityEvidence,
    EvidenceSegment,
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


def _group_consecutive_index_runs(
    segments: list[EvidenceSegment],
) -> list[list[EvidenceSegment]]:
    """Group consecutive segments sharing the same device_step_index into runs.

    A run of laps with equal wkt_step_index is one occurrence (Auto Lap safe).
    """
    runs: list[list[EvidenceSegment]] = []
    current: list[EvidenceSegment] = []
    current_index: int | None = None

    for segment in segments:
        idx = segment.device_step_index
        if idx is None:
            if current:
                runs.append(current)
                current = []
                current_index = None
            continue
        if current and idx == current_index:
            current.append(segment)
        else:
            if current:
                runs.append(current)
            current = [segment]
            current_index = idx
    if current:
        runs.append(current)
    return runs


def _window_from_run(run: list[EvidenceSegment]) -> tuple[datetime | None, datetime | None]:
    starts = [s.start_time for s in run if s.start_time is not None]
    if not starts:
        return None, None
    started = min(starts)
    ends: list[datetime] = []
    for segment in run:
        if segment.end_time is not None:
            ends.append(segment.end_time)
        elif segment.start_time is not None and segment.duration_elapsed_s is not None:
            ends.append(segment.start_time + timedelta(seconds=segment.duration_elapsed_s))
    if not ends:
        return started, None
    return started, max(ends)


def _trackpoint_range(
    evidence: ActivityEvidence,
    started: datetime,
    ended: datetime,
) -> tuple[int | None, int | None]:
    if not evidence.timeline:
        return None, None
    start_i = None
    end_i = None
    for i, point in enumerate(evidence.timeline):
        if point.timestamp is None:
            continue
        if start_i is None and point.timestamp >= started:
            start_i = i
        if point.timestamp <= ended:
            end_i = i
    return start_i, end_i


class DeviceStepIndexStrategy(SegmentationStrategy):
    strategy_id = "device_step_index"
    required_capabilities = {EvidenceCapability.device_step_index}

    def segment(
        self,
        evidence: ActivityEvidence,
        plan: ResolvedPlan,
        correlation: PlanCorrelationResult | None = None,
    ) -> list[SegmentMatch]:
        runs = _group_consecutive_index_runs(evidence.segments)
        index_run_counts: dict[int, int] = {}
        authored_to_device = (correlation.mapping if correlation else {}) or {}

        matches: list[SegmentMatch] = []
        run_pos = 0

        for occurrence in plan.occurrences:
            expected_idx = authored_to_device.get(occurrence.authored_step_id)

            if run_pos >= len(runs):
                matches.append(
                    self._negative_match(
                        occurrence,
                        status=StepExecutionStatus.not_attempted
                        if matches
                        else StepExecutionStatus.not_executed,
                        reason="no_remaining_segments",
                    )
                )
                continue

            # If correlation expects a specific index, advance past non-matching runs
            # only when that expected index appears later (skipped intermediate work).
            if expected_idx is not None:
                later_match = next(
                    (
                        i
                        for i in range(run_pos, len(runs))
                        if runs[i][0].device_step_index == expected_idx
                    ),
                    None,
                )
                if later_match is None:
                    observed = runs[run_pos][0].device_step_index
                    matches.append(
                        self._negative_match(
                            occurrence,
                            status=StepExecutionStatus.not_executed,
                            reason="expected_index_not_found",
                            details={
                                "expected_device_step_index": expected_idx,
                                "next_observed_device_step_index": observed,
                            },
                            rejected=[
                                RejectedCandidate(
                                    reason_code="expected_index_not_found",
                                    details={
                                        "expected": expected_idx,
                                        "next_observed": observed,
                                    },
                                )
                            ],
                        )
                    )
                    continue
                run_pos = later_match

            run = runs[run_pos]
            run_index = run[0].device_step_index
            assert run_index is not None

            prior = index_run_counts.get(run_index, 0)
            index_run_counts[run_index] = prior + 1
            started, ended = _window_from_run(run)

            if started is None or ended is None:
                matches.append(
                    self._negative_match(
                        occurrence,
                        status=StepExecutionStatus.unmatched,
                        reason="missing_timestamps",
                        details={"device_step_index": run_index},
                    )
                )
                run_pos += 1
                continue

            tp_start, tp_end = _trackpoint_range(evidence, started, ended)
            corr_payload = None
            if correlation is not None:
                corr_payload = {
                    "confidence": correlation.confidence,
                    "divergences": correlation.divergences,
                    "mapping": correlation.mapping,
                }

            confidence = 0.95
            if correlation is not None and correlation.confidence < 0.5:
                confidence = 0.7

            matches.append(
                SegmentMatch(
                    window=ExecutionWindow(
                        started_at=started,
                        ended_at=ended,
                        authored_step_id=occurrence.authored_step_id,
                        occurrence_path=occurrence.occurrence_path,
                        occurrence_ordinal=occurrence.occurrence_ordinal,
                        confidence=confidence,
                    ),
                    evidence=MatchEvidence(
                        strategy_id=self.strategy_id,
                        capabilities_used=[EvidenceCapability.device_step_index.value],
                        device_step_index=run_index,
                        repeat_cycle_run=prior + 1,
                        prior_runs_of_same_index=prior,
                        lap_ids=[s.segment_id for s in run],
                        lap_message_indexes=[
                            s.message_index for s in run if s.message_index is not None
                        ],
                        lap_triggers=[s.lap_trigger for s in run if s.lap_trigger],
                        trackpoint_index_start=tp_start,
                        trackpoint_index_end=tp_end,
                        plan_correlation=corr_payload,
                        details={
                            "segment_count_in_run": len(run),
                            "occurrence_path": occurrence.occurrence_path,
                        },
                    ),
                    status=StepExecutionStatus.executed,
                    occurrence=occurrence,
                )
            )
            run_pos += 1

        return matches

    def _negative_match(
        self,
        occurrence: ResolvedOccurrence,
        *,
        status: StepExecutionStatus,
        reason: str,
        details: dict | None = None,
        rejected: list[RejectedCandidate] | None = None,
    ) -> SegmentMatch:
        return SegmentMatch(
            window=None,
            evidence=MatchEvidence(
                strategy_id=self.strategy_id,
                capabilities_used=[EvidenceCapability.device_step_index.value],
                negative_claim=True,
                rejected_candidates=rejected or [],
                details={"reason_code": reason, **(details or {})},
            ),
            status=status,
            occurrence=occurrence,
        )
