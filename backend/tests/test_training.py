"""Unit tests for training module."""
import pytest

from src.modules.training.models import WorkoutStatus, WorkoutType
from src.modules.training.service import TrainingService
from src.modules.training.workout_steps import (
    DurationType,
    RepeatBlockModel,
    StepType,
    WorkoutStepModel,
    compute_rollups,
    validate_steps,
)


def test_workout_status_enum_values():
    assert WorkoutStatus.scheduled.value == "scheduled"
    assert WorkoutStatus.completed.value == "completed"
    assert WorkoutStatus.skipped.value == "skipped"


def _step(
    step_type: str,
    duration: int | None = None,
    distance: int | None = None,
    **kwargs,
) -> dict:
    payload = {
        "type": step_type,
        "duration": duration,
        "distance": distance,
        "targetType": kwargs.get("target_type"),
        "targetMin": kwargs.get("target_min"),
        "targetMax": kwargs.get("target_max"),
        "targetZoneId": kwargs.get("target_zone_id"),
        "targetZoneName": kwargs.get("target_zone_name"),
        "notes": kwargs.get("notes"),
    }
    if "duration_type" in kwargs:
        payload["durationType"] = kwargs["duration_type"]
    return payload


def test_validate_steps_rejects_cycling_step_on_running():
    items = [_step("ride", duration=30)]
    with pytest.raises(ValueError, match="not allowed"):
        validate_steps("running", items)


def test_validate_steps_rejects_unsupported_sport():
    with pytest.raises(ValueError, match="not available"):
        validate_steps("swimming", [_step("warmup", duration=10)])


def test_validate_steps_requires_at_least_one():
    with pytest.raises(ValueError, match="at least one"):
        validate_steps("running", [])


def test_validate_steps_repeat_block():
    items = [
        _step("warmup", duration=15),
        {
            "repeatCount": 6,
            "steps": [
                _step("interval", distance=800),
                _step("recovery", duration=2),
            ],
        },
        _step("cooldown", duration=10),
    ]
    result = validate_steps("running", items)
    assert len(result) == 3
    assert result[1]["repeatCount"] == 6
    assert len(result[1]["steps"]) == 2


def test_compute_rollups_interval_workout():
    items = [
        WorkoutStepModel(type=StepType.warmup, duration_type=DurationType.time, duration=15, distance=None),
        RepeatBlockModel(
            repeatCount=6,
            steps=[
                WorkoutStepModel(
                    type=StepType.interval,
                    duration_type=DurationType.distance,
                    duration=None,
                    distance=800,
                ),
                WorkoutStepModel(
                    type=StepType.recovery,
                    duration_type=DurationType.time,
                    duration=2,
                    distance=None,
                ),
            ],
        ),
        WorkoutStepModel(type=StepType.cooldown, duration_type=DurationType.time, duration=10, distance=None),
    ]
    duration_min, distance_m = compute_rollups(items)
    assert duration_min == 37  # 15 + 6*2 + 10
    assert distance_m == 4800  # 6 * 800


def test_lap_button_step_has_no_rollup():
    items = [
        WorkoutStepModel(
            type=StepType.run,
            duration_type=DurationType.lap_button,
            duration=None,
            distance=None,
        ),
    ]
    duration_min, distance_m = compute_rollups(items)
    assert duration_min is None
    assert distance_m is None


def test_time_step_requires_duration():
    with pytest.raises(ValueError, match="require duration"):
        WorkoutStepModel(
            type=StepType.run,
            duration_type=DurationType.time,
            duration=None,
            distance=None,
        )


def test_distance_step_requires_distance():
    with pytest.raises(ValueError, match="require distance"):
        WorkoutStepModel(
            type=StepType.interval,
            duration_type=DurationType.distance,
            duration=None,
            distance=None,
        )


def test_step_rejects_both_duration_and_distance():
    with pytest.raises(ValueError, match="not both"):
        WorkoutStepModel(type=StepType.run, duration=10, distance=800)


def test_lap_button_step_valid():
    step = WorkoutStepModel(
        type=StepType.run,
        duration_type=DurationType.lap_button,
        duration=None,
        distance=None,
    )
    assert step.duration_type == DurationType.lap_button


def test_repeat_block_requires_positive_count():
    with pytest.raises(ValueError):
        RepeatBlockModel(
            repeatCount=0,
            steps=[
                WorkoutStepModel(
                    type=StepType.run,
                    duration_type=DurationType.time,
                    duration=10,
                    distance=None,
                )
            ],
        )
