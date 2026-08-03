"""Unit tests for training module."""
from datetime import date

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


def test_assign_request_caps_cartesian_product():
    from src.modules.training.schemas import WorkoutAssignRequest

    with pytest.raises(ValueError, match="50"):
        WorkoutAssignRequest(
            athlete_ids=list(range(1, 11)),
            scheduled_dates=[date(2026, 7, d) for d in range(1, 7)],
            sport_id=1,
            title="Too many",
            steps=[_step("run", duration=30)],
        )


def test_assign_request_accepts_valid_payload():
    from src.modules.training.schemas import WorkoutAssignRequest

    req = WorkoutAssignRequest(
        athlete_ids=[1, 2],
        scheduled_dates=[date(2026, 7, 24), date(2026, 7, 26)],
        sport_id=1,
        title="Threshold",
        purpose="Threshold development",
        target_rpe=7,
        steps=[_step("run", duration=40)],
    )
    assert len(req.athlete_ids) * len(req.scheduled_dates) == 4
    assert req.purpose == "Threshold development"
    assert req.target_rpe == 7


def test_template_write_request_includes_intent():
    from src.modules.training.schemas import WorkoutTemplateWriteRequest

    req = WorkoutTemplateWriteRequest(
        sport_id=1,
        title="Easy template",
        purpose="Aerobic base",
        target_rpe=3,
        steps=[_step("warmup", duration=10), _step("run", duration=40)],
    )
    assert req.purpose == "Aerobic base"
    assert req.target_rpe == 3


def test_assign_workouts_fail_all_on_unlinked_athlete(monkeypatch):
    from types import SimpleNamespace
    from unittest.mock import MagicMock

    from src.modules.training.schemas import WorkoutAssignRequest

    db = MagicMock()
    service = TrainingService(db)
    coach = SimpleNamespace(id=10)

    monkeypatch.setattr(service, "_assert_athlete_user", lambda _id: None)
    monkeypatch.setattr(
        "src.modules.training.service.coach_athlete_relation_error",
        lambda _db, _coach_id, athlete_id: (
            "Not linked to this athlete" if athlete_id == 2 else None
        ),
    )
    monkeypatch.setattr(
        service,
        "_prepare_workout_fields",
        lambda *_args: (
            {
                "sport_id": 1,
                "steps": [{"type": "interval", "distance": 800}],
                "duration_min": None,
                "distance_m": 800,
            },
            None,
            200,
        ),
    )

    data = WorkoutAssignRequest(
        athlete_ids=[1, 2],
        scheduled_dates=[date(2026, 7, 24)],
        sport_id=1,
        title="Intervals",
        steps=[_step("interval", distance=800)],
    )
    result, err, status = service.assign_workouts(coach, data)
    assert result is None
    assert status == 404
    assert "Athlete 2" in err
    db.add.assert_not_called()


def test_assign_workouts_creates_cartesian_product(monkeypatch):
    from types import SimpleNamespace
    from unittest.mock import MagicMock

    from src.modules.training.schemas import WorkoutAssignRequest

    db = MagicMock()
    service = TrainingService(db)
    coach = SimpleNamespace(id=10)
    created_ids = iter([101, 102, 103, 104])

    monkeypatch.setattr(service, "_assert_athlete_user", lambda _id: None)
    monkeypatch.setattr(
        "src.modules.training.service.coach_athlete_relation_error",
        lambda *_args: None,
    )
    monkeypatch.setattr(
        service,
        "_prepare_workout_fields",
        lambda *_args: (
            {
                "sport_id": 1,
                "steps": [{"type": "run", "duration": 30}],
                "duration_min": 30,
                "distance_m": None,
            },
            None,
            200,
        ),
    )

    def _fake_workout(**kwargs):
        return SimpleNamespace(**kwargs, id=None)

    monkeypatch.setattr("src.modules.training.service.Workout", _fake_workout)

    def _load(workout_id: int):
        return SimpleNamespace(
            id=workout_id,
            athlete_id=1,
            created_by_id=10,
            scheduled_date=date(2026, 7, 24),
            sport_id=1,
            sport=SimpleNamespace(code="running", name="Running"),
            workout_type=WorkoutType.easy,
            title="Easy",
            purpose=None,
            target_rpe=None,
            description=None,
            steps=[{"type": "run", "duration": 30}],
            duration_min=30,
            distance_m=None,
            status=WorkoutStatus.scheduled,
            completed_at=None,
            notes=None,
            activity_id=None,
            created_at=None,
            updated_at=None,
        )

    monkeypatch.setattr(service, "_load_workout", _load)

    def _add(obj):
        obj.id = next(created_ids)

    db.add.side_effect = _add

    data = WorkoutAssignRequest(
        athlete_ids=[1, 2],
        scheduled_dates=[date(2026, 7, 24), date(2026, 7, 26)],
        sport_id=1,
        title="Easy",
        steps=[_step("run", duration=30)],
    )
    result, err, status = service.assign_workouts(coach, data)
    assert err is None
    assert status == 201
    assert result["count"] == 4
    assert len(result["workouts"]) == 4
    assert db.add.call_count == 4
    db.commit.assert_called_once()


def test_create_template_ownership_check(monkeypatch):
    from types import SimpleNamespace
    from unittest.mock import MagicMock

    from src.modules.training.schemas import WorkoutTemplateWriteRequest

    db = MagicMock()
    service = TrainingService(db)
    coach = SimpleNamespace(id=10)
    other = SimpleNamespace(id=99)

    template = SimpleNamespace(
        id=5,
        coach_id=10,
        sport_id=1,
        sport=SimpleNamespace(code="running", name="Running"),
        workout_type=WorkoutType.easy,
        title="Mine",
        purpose=None,
        target_rpe=None,
        description=None,
        steps=[],
        duration_min=30,
        distance_m=None,
        created_at=None,
        updated_at=None,
    )
    monkeypatch.setattr(service, "_load_template", lambda _id: template)

    result, err, status = service.get_template(coach, 5)
    assert err is None
    assert result["template"]["title"] == "Mine"

    result, err, status = service.get_template(other, 5)
    assert result is None
    assert status == 404
    assert err == "Template not found"

    data = WorkoutTemplateWriteRequest(
        sport_id=1,
        title="Updated",
        steps=[_step("run", duration=30)],
    )
    monkeypatch.setattr(
        service,
        "_prepare_template_fields",
        lambda *_args: (
            {
                "sport_id": 1,
                "steps": [{"type": "run", "duration": 30}],
                "duration_min": 30,
                "distance_m": None,
            },
            None,
            200,
        ),
    )
    result, err, status = service.update_template(other, 5, data)
    assert result is None
    assert status == 404
