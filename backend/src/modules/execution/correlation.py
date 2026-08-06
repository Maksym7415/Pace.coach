"""Structural plan correlation: Pace.coach plan ↔ device-embedded workout."""
from __future__ import annotations

from src.modules.execution.domain import PlanCorrelationResult, ResolvedPlan
from src.modules.fit_parser.models import DeviceWorkout, DeviceWorkoutStep
from src.modules.training.workout_steps import DurationType, StepType


_REPEAT_DURATION_TYPES = {
    "repeat_until_steps_cmplt",
    "repeat_until_time",
    "repeat_until_distance",
    "repeat_until_calories",
    "repeat_until_hr_less_than",
    "repeat_until_hr_greater_than",
    "repeat_until_power_less_than",
    "repeat_until_power_greater_than",
}


def _is_repeat_step(step: DeviceWorkoutStep) -> bool:
    return (step.duration_type or "") in _REPEAT_DURATION_TYPES


def _device_leaf_steps(device_plan: DeviceWorkout) -> list[DeviceWorkoutStep]:
    return [s for s in device_plan.steps if not _is_repeat_step(s)]


def _intensity_compatible(step_type: StepType, intensity: str | None) -> bool:
    if intensity is None:
        return True
    intensity = intensity.lower()
    mapping = {
        StepType.warmup: {"warmup"},
        StepType.cooldown: {"cooldown"},
        StepType.interval: {"active", "interval"},
        StepType.run: {"active", "interval"},
        StepType.ride: {"active", "interval"},
        StepType.recovery: {"rest", "recovery"},
        StepType.recovery_ride: {"rest", "recovery"},
        StepType.rest: {"rest", "recovery"},
    }
    allowed = mapping.get(step_type)
    if not allowed:
        return True
    return intensity in allowed


def _duration_compatible(duration_type: DurationType, device_duration_type: str | None) -> bool:
    if device_duration_type is None:
        return True
    device_duration_type = device_duration_type.lower()
    if duration_type == DurationType.time:
        return device_duration_type in {"time", "open"}
    if duration_type == DurationType.distance:
        return device_duration_type in {"distance", "open"}
    if duration_type == DurationType.lap_button:
        return device_duration_type in {"open", "lap_button"}
    return True


def correlate_structurally(
    plan: ResolvedPlan,
    device_plan: DeviceWorkout | None,
) -> PlanCorrelationResult:
    """Align authored occurrences' unique steps to device workout_step message_indexes.

    Maps each unique authored_step_id to a device message_index by sequential walk
    over unique authored steps vs non-repeat device steps.
    """
    if device_plan is None or not device_plan.steps:
        return PlanCorrelationResult(
            confidence=0.0,
            divergences=[{"code": "no_device_plan"}],
        )

    # Unique authored steps in first-occurrence order
    seen: set[str] = set()
    unique_authored = []
    for occ in plan.occurrences:
        if occ.authored_step_id in seen:
            continue
        seen.add(occ.authored_step_id)
        unique_authored.append(occ)

    device_leaves = _device_leaf_steps(device_plan)
    mapping: dict[str, int] = {}
    divergences: list[dict] = []

    if len(unique_authored) != len(device_leaves):
        divergences.append(
            {
                "code": "step_count_mismatch",
                "authored_unique": len(unique_authored),
                "device_leaf": len(device_leaves),
            }
        )

    pairs = min(len(unique_authored), len(device_leaves))
    compatible = 0
    for i in range(pairs):
        authored = unique_authored[i]
        device = device_leaves[i]
        if device.message_index is None:
            divergences.append(
                {
                    "code": "missing_device_message_index",
                    "authored_step_id": authored.authored_step_id,
                }
            )
            continue
        ok = _intensity_compatible(authored.step_type, device.intensity) and _duration_compatible(
            authored.duration_type, device.duration_type
        )
        if ok:
            compatible += 1
            mapping[authored.authored_step_id] = device.message_index
        else:
            divergences.append(
                {
                    "code": "structure_mismatch",
                    "authored_step_id": authored.authored_step_id,
                    "authored_type": authored.step_type.value,
                    "device_intensity": device.intensity,
                    "device_duration_type": device.duration_type,
                    "device_message_index": device.message_index,
                }
            )
            # Still map positionally — segmentation may still use indices
            mapping[authored.authored_step_id] = device.message_index

    if pairs == 0:
        confidence = 0.0
    else:
        count_penalty = 0.0 if len(unique_authored) == len(device_leaves) else 0.2
        confidence = max(0.0, (compatible / pairs) - count_penalty)

    return PlanCorrelationResult(
        confidence=confidence,
        mapping=mapping,
        divergences=divergences,
        trusted_by_id=False,
    )
