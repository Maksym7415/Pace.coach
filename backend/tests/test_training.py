"""Unit tests for training module."""
from src.modules.training.models import WorkoutStatus
from src.modules.training.service import TrainingService


def test_workout_status_enum_values():
    assert WorkoutStatus.scheduled.value == "scheduled"
    assert WorkoutStatus.completed.value == "completed"
    assert WorkoutStatus.skipped.value == "skipped"
