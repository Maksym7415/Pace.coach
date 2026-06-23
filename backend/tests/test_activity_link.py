"""Tests for workout-activity auto-linking."""
from types import SimpleNamespace

from src.modules.training.activity_link import select_workout_for_activity
from src.modules.training.models import WorkoutType


def _workout(workout_type: WorkoutType):
    return SimpleNamespace(workout_type=workout_type)


def test_select_single_run_workout():
    candidates = [_workout(WorkoutType.easy)]
    assert select_workout_for_activity(candidates, "run") is candidates[0]


def test_select_ambiguous_when_multiple_run_workouts():
    candidates = [_workout(WorkoutType.easy), _workout(WorkoutType.intervals)]
    assert select_workout_for_activity(candidates, "run") is None


def test_select_none_when_only_rest_day():
    candidates = [_workout(WorkoutType.rest)]
    assert select_workout_for_activity(candidates, "run") is None
    assert select_workout_for_activity(candidates, "bike") is None
