"""Per-occurrence scoring with intent-asymmetric penalties."""
from __future__ import annotations

from src.modules.execution.domain import (
    ExecutionMetrics,
    ExecutionScore,
    MatchEvidence,
    ResolvedOccurrence,
)
from src.modules.training.workout_steps import DurationType, StepType, TargetType


# Step intents where going too hard (above intensity) is the primary failure mode
_RECOVERY_INTENTS = {
    StepType.recovery,
    StepType.recovery_ride,
    StepType.rest,
    StepType.warmup,
    StepType.cooldown,
}

_WORK_INTENTS = {
    StepType.interval,
    StepType.run,
    StepType.ride,
}


def _clamp(value: float, low: float = 0.0, high: float = 100.0) -> float:
    return max(low, min(high, value))


def _completion_score(
    occurrence: ResolvedOccurrence,
    metrics: ExecutionMetrics,
) -> float | None:
    if occurrence.duration_type == DurationType.lap_button:
        # Open step: completed if any meaningful window exists
        if metrics.duration_elapsed_s is not None and metrics.duration_elapsed_s > 5:
            return 100.0
        if metrics.distance_m is not None and metrics.distance_m > 10:
            return 100.0
        return 0.0

    if occurrence.duration_type == DurationType.time:
        planned = (occurrence.duration_min or 0) * 60.0
        actual = metrics.duration_moving_s
        if planned <= 0 or actual is None:
            return None
        ratio = actual / planned
        return _clamp(ratio * 100.0)

    if occurrence.duration_type == DurationType.distance:
        planned = float(occurrence.distance_m or 0)
        actual = metrics.distance_m
        if planned <= 0 or actual is None:
            return None
        ratio = actual / planned
        return _clamp(ratio * 100.0)

    return None


def _intensity_score(
    occurrence: ResolvedOccurrence,
    metrics: ExecutionMetrics,
) -> float | None:
    target = occurrence.target
    if target.target_type is None or target.target_type == TargetType.none:
        return None
    if metrics.time_in_target_pct is None:
        return None

    base = metrics.time_in_target_pct
    deviation = metrics.target_deviation_pct

    if deviation is None:
        return _clamp(base)

    # Intent-asymmetric penalties
    # Pace: higher s/km = slower. Positive deviation = slower than mid-target.
    # HR/power/cadence: positive deviation = higher than mid-target.
    is_pace = target.target_type == TargetType.pace
    too_hard = (deviation < 0) if is_pace else (deviation > 0)
    too_easy = not too_hard and abs(deviation) > 2.0

    if occurrence.step_type in _RECOVERY_INTENTS:
        if too_hard:
            # Recovery run too fast / HR too high — failure
            penalty = min(60.0, abs(deviation) * 2.0)
            return _clamp(base - penalty)
        # Too easy on recovery is fine
        return _clamp(max(base, 90.0))

    if occurrence.step_type in _WORK_INTENTS:
        if too_easy:
            penalty = min(70.0, abs(deviation) * 2.5)
            return _clamp(base - penalty)
        if too_hard:
            # Mild pacing-discipline issue
            penalty = min(25.0, abs(deviation) * 0.8)
            return _clamp(base - penalty)

    return _clamp(base)


def _quality_score(
    occurrence: ResolvedOccurrence,
    metrics: ExecutionMetrics,
    evidence: MatchEvidence | None,
) -> float | None:
    # Suppress quality claims for approximate boundaries
    if evidence is not None:
        if evidence.strategy_id == "signal":
            return None
        if evidence.details.get("approximate"):
            return None

    components = []
    variability = metrics.metrics.get("pace_variability")
    if isinstance(variability, (int, float)):
        # 0 variability → 100; 0.1 (10%) → ~70
        components.append(_clamp(100.0 - float(variability) * 300.0))

    first = metrics.metrics.get("first_half_pace_s_per_km")
    second = metrics.metrics.get("second_half_pace_s_per_km")
    if isinstance(first, (int, float)) and isinstance(second, (int, float)) and first > 0:
        fade = (second - first) / first  # positive = slowed down
        if occurrence.step_type in _WORK_INTENTS:
            components.append(_clamp(100.0 - max(0.0, fade) * 400.0))
        else:
            components.append(100.0)

    hr_drift = metrics.metrics.get("hr_drift_pct")
    if isinstance(hr_drift, (int, float)):
        components.append(_clamp(100.0 - max(0.0, float(hr_drift) - 5.0) * 3.0))

    if not components:
        return None
    return _clamp(sum(components) / len(components))


def score_occurrence(
    occurrence: ResolvedOccurrence,
    metrics: ExecutionMetrics,
    evidence: MatchEvidence | None = None,
) -> ExecutionScore:
    completion = _completion_score(occurrence, metrics)
    intensity = _intensity_score(occurrence, metrics)
    quality = _quality_score(occurrence, metrics, evidence)

    parts = [p for p in (completion, intensity, quality) if p is not None]
    overall = sum(parts) / len(parts) if parts else None

    return ExecutionScore(
        score=round(overall, 1) if overall is not None else None,
        completion=round(completion, 1) if completion is not None else None,
        intensity_adherence=round(intensity, 1) if intensity is not None else None,
        execution_quality=round(quality, 1) if quality is not None else None,
        components={
            "completion": completion,
            "intensity_adherence": intensity,
            "execution_quality": quality,
            "weights": "equal_non_null",
        },
    )
