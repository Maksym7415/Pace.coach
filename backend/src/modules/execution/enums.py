"""Execution matching enums (application-layer, stored as VARCHAR)."""
from __future__ import annotations

import enum


class StepExecutionStatus(str, enum.Enum):
    executed = "executed"
    partially_executed = "partially_executed"
    not_executed = "not_executed"
    not_attempted = "not_attempted"
    substituted = "substituted"
    unmatched = "unmatched"


class WorkoutExecutionStatus(str, enum.Enum):
    pending = "pending"
    matched = "matched"
    partial = "partial"
    unmatched = "unmatched"
    failed = "failed"


class IssueSeverity(str, enum.Enum):
    info = "info"
    warning = "warning"
    critical = "critical"


class IssueDimension(str, enum.Enum):
    completion = "completion"
    intensity = "intensity"
    quality = "quality"
    matching = "matching"
    structure = "structure"


class EvidenceCapability(str, enum.Enum):
    device_step_index = "device_step_index"
    device_plan = "device_plan"
    lap_structure = "lap_structure"
    timeline = "timeline"
    heart_rate = "heart_rate"
    pace = "pace"
    power = "power"
    cadence = "cadence"


ALGORITHM_VERSION = "1.0.0"
