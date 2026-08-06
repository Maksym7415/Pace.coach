"""Evidence adapter interfaces."""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from src.modules.execution.domain import ActivityEvidence
from src.modules.fit_parser.models import DeviceWorkout, NormalizedActivity


class EvidenceAdapter(ABC):
    vendor: str

    @abstractmethod
    def adapt(
        self,
        normalized: NormalizedActivity,
        *,
        activity_id: int | None = None,
    ) -> ActivityEvidence:
        raise NotImplementedError


class DevicePlanExtractor(ABC):
    vendor: str

    @abstractmethod
    def extract(self, source: Any) -> DeviceWorkout | None:
        raise NotImplementedError
