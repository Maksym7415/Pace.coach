"""Tests for workout-activity auto-linking."""
from types import SimpleNamespace

from src.modules.training.activity_link import select_workout_for_activity
from src.modules.training.models import WorkoutType


def _workout(workout_type: WorkoutType):
    return SimpleNamespace(workout_type=workout_type)


def test_select_single_run_workout():
    candidates = [_workout(WorkoutType.easy)]
    assert select_workout_for_activity(candidates, "running") is candidates[0]


def test_select_ambiguous_when_multiple_run_workouts():
    candidates = [_workout(WorkoutType.easy), _workout(WorkoutType.intervals)]
    assert select_workout_for_activity(candidates, "running") is None


def test_select_none_when_only_rest_day():
    candidates = [_workout(WorkoutType.rest)]
    assert select_workout_for_activity(candidates, "running") is None
    assert select_workout_for_activity(candidates, "cycling") is None


def test_select_run_and_ride_disambiguated_by_sport_id():
    run = SimpleNamespace(workout_type=WorkoutType.easy, sport_id=1)
    ride = SimpleNamespace(workout_type=WorkoutType.easy, sport_id=2)
    assert select_workout_for_activity([run, ride], "running", sport_id=1) is run
    assert select_workout_for_activity([run, ride], "cycling", sport_id=2) is ride


def test_select_null_sport_id_stays_eligible():
    open_slot = SimpleNamespace(workout_type=WorkoutType.easy, sport_id=None)
    assert select_workout_for_activity([open_slot], "running", sport_id=1) is open_slot


def test_select_still_ambiguous_when_two_same_sport():
    a = SimpleNamespace(workout_type=WorkoutType.easy, sport_id=1)
    b = SimpleNamespace(workout_type=WorkoutType.intervals, sport_id=1)
    assert select_workout_for_activity([a, b], "running", sport_id=1) is None
