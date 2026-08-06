"""Manual segmentation — coach/athlete declared boundaries (always wins when provided)."""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field

from src.modules.execution.domain import (
    ActivityEvidence,
    ExecutionWindow,
    MatchEvidence,
    PlanCorrelationResult,
    ResolvedPlan,
    SegmentMatch,
)
from src.modules.execution.enums import StepExecutionStatus
from src.modules.execution.segmentation.base import SegmentationStrategy


class ManualBoundary(BaseModel):
    authored_step_id: str
    occurrence_ordinal: int
    started_at: datetime
    ended_at: datetime
    occurrence_path: str | None = None


class ManualStrategy(SegmentationStrategy):
    strategy_id = "manual"
    required_capabilities = set()  # always eligible when boundaries are supplied

    def __init__(self, boundaries: list[ManualBoundary] | None = None):
        self.boundaries = list(boundaries or [])

    def supports(self, evidence: ActivityEvidence) -> bool:
        return bool(self.boundaries)

    def segment(
        self,
        evidence: ActivityEvidence,
        plan: ResolvedPlan,
        correlation: PlanCorrelationResult | None = None,
    ) -> list[SegmentMatch]:
        by_key = {
            (b.authored_step_id, b.occurrence_ordinal): b for b in self.boundaries
        }
        matches: list[SegmentMatch] = []
        for occurrence in plan.occurrences:
            key = (occurrence.authored_step_id, occurrence.occurrence_ordinal)
            boundary = by_key.get(key)
            if boundary is None:
                matches.append(
                    SegmentMatch(
                        window=None,
                        evidence=MatchEvidence(
                            strategy_id=self.strategy_id,
                            negative_claim=True,
                            details={"reason_code": "no_manual_boundary"},
                        ),
                        status=StepExecutionStatus.unmatched,
                        occurrence=occurrence,
                    )
                )
                continue
            matches.append(
                SegmentMatch(
                    window=ExecutionWindow(
                        started_at=boundary.started_at,
                        ended_at=boundary.ended_at,
                        authored_step_id=occurrence.authored_step_id,
                        occurrence_path=occurrence.occurrence_path,
                        occurrence_ordinal=occurrence.occurrence_ordinal,
                        confidence=1.0,
                    ),
                    evidence=MatchEvidence(
                        strategy_id=self.strategy_id,
                        capabilities_used=["manual"],
                        details={"source": "manual_boundary"},
                    ),
                    status=StepExecutionStatus.executed,
                    occurrence=occurrence,
                )
            )
        return matches
