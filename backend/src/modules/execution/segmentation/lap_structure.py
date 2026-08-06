"""Lap-structure segmentation when device step indexes are absent."""
from __future__ import annotations

from datetime import timedelta

from src.modules.execution.domain import (
    ActivityEvidence,
    ExecutionWindow,
    MatchEvidence,
    PlanCorrelationResult,
    RejectedCandidate,
    ResolvedPlan,
    SegmentMatch,
)
from src.modules.execution.enums import EvidenceCapability, StepExecutionStatus
from src.modules.execution.segmentation.base import SegmentationStrategy


class LapStructureStrategy(SegmentationStrategy):
    strategy_id = "lap_structure"
    required_capabilities = {EvidenceCapability.lap_structure}

    def segment(
        self,
        evidence: ActivityEvidence,
        plan: ResolvedPlan,
        correlation: PlanCorrelationResult | None = None,
    ) -> list[SegmentMatch]:
        occurrences = plan.occurrences
        segments = [s for s in evidence.segments if s.start_time is not None]
        matches: list[SegmentMatch] = []

        if len(segments) != len(occurrences):
            # Still attempt 1:1 for the overlapping prefix; mark extras/missing
            pass

        for i, occurrence in enumerate(occurrences):
            if i >= len(segments):
                matches.append(
                    SegmentMatch(
                        window=None,
                        evidence=MatchEvidence(
                            strategy_id=self.strategy_id,
                            capabilities_used=[EvidenceCapability.lap_structure.value],
                            negative_claim=True,
                            details={"reason_code": "no_lap_for_occurrence"},
                            rejected_candidates=[
                                RejectedCandidate(
                                    reason_code="lap_count_shortfall",
                                    details={
                                        "occurrence_ordinal": occurrence.occurrence_ordinal,
                                        "lap_count": len(segments),
                                    },
                                )
                            ],
                        ),
                        status=StepExecutionStatus.not_attempted
                        if i > 0
                        else StepExecutionStatus.not_executed,
                        occurrence=occurrence,
                    )
                )
                continue

            segment = segments[i]
            ended = segment.end_time
            if ended is None and segment.start_time and segment.duration_elapsed_s is not None:
                ended = segment.start_time + timedelta(seconds=segment.duration_elapsed_s)
            if segment.start_time is None or ended is None:
                matches.append(
                    SegmentMatch(
                        window=None,
                        evidence=MatchEvidence(
                            strategy_id=self.strategy_id,
                            negative_claim=True,
                            details={"reason_code": "missing_timestamps"},
                        ),
                        status=StepExecutionStatus.unmatched,
                        occurrence=occurrence,
                    )
                )
                continue

            count_match = len(segments) == len(occurrences)
            confidence = 0.6 if count_match else 0.4

            matches.append(
                SegmentMatch(
                    window=ExecutionWindow(
                        started_at=segment.start_time,
                        ended_at=ended,
                        authored_step_id=occurrence.authored_step_id,
                        occurrence_path=occurrence.occurrence_path,
                        occurrence_ordinal=occurrence.occurrence_ordinal,
                        confidence=confidence,
                    ),
                    evidence=MatchEvidence(
                        strategy_id=self.strategy_id,
                        capabilities_used=[EvidenceCapability.lap_structure.value],
                        lap_ids=[segment.segment_id],
                        lap_message_indexes=(
                            [segment.message_index]
                            if segment.message_index is not None
                            else []
                        ),
                        lap_triggers=[segment.lap_trigger] if segment.lap_trigger else [],
                        details={
                            "lap_number": segment.lap_number,
                            "lap_count": len(segments),
                            "occurrence_count": len(occurrences),
                            "count_aligned": count_match,
                        },
                        capability_gaps=(
                            [EvidenceCapability.device_step_index.value]
                            if EvidenceCapability.device_step_index not in evidence.capabilities
                            else []
                        ),
                    ),
                    status=StepExecutionStatus.executed,
                    occurrence=occurrence,
                )
            )

        return matches
