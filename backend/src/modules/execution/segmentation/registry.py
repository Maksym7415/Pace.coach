"""Strategy registry ordered by confidence."""
from __future__ import annotations

from src.modules.execution.domain import ActivityEvidence
from src.modules.execution.segmentation.base import SegmentationStrategy


class SegmentationRegistry:
    def __init__(self, strategies: list[SegmentationStrategy] | None = None):
        self._strategies = list(strategies or [])

    def register(self, strategy: SegmentationStrategy) -> None:
        self._strategies.append(strategy)

    def select(self, evidence: ActivityEvidence) -> SegmentationStrategy | None:
        for strategy in self._strategies:
            if strategy.supports(evidence):
                return strategy
        return None

    @property
    def strategies(self) -> list[SegmentationStrategy]:
        return list(self._strategies)
