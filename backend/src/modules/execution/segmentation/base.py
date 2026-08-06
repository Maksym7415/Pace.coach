"""Segmentation strategy interface."""
from __future__ import annotations

from abc import ABC, abstractmethod

from src.modules.execution.domain import (
    ActivityEvidence,
    PlanCorrelationResult,
    ResolvedPlan,
    SegmentMatch,
)
from src.modules.execution.enums import EvidenceCapability


class SegmentationStrategy(ABC):
    strategy_id: str
    required_capabilities: set[EvidenceCapability]

    def supports(self, evidence: ActivityEvidence) -> bool:
        return self.required_capabilities.issubset(evidence.capabilities)

    @abstractmethod
    def segment(
        self,
        evidence: ActivityEvidence,
        plan: ResolvedPlan,
        correlation: PlanCorrelationResult | None = None,
    ) -> list[SegmentMatch]:
        """Emit (ExecutionWindow, MatchEvidence) pairs. Window may be null for negative claims."""
        raise NotImplementedError
