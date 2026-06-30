"""Unit tests for shared coach-athlete relation checks."""
from unittest.mock import MagicMock

from src.modules.coaching.relations import (
    COACH_ATHLETE_NOT_LINKED_ERROR,
    COACH_ATHLETE_NOT_LINKED_STATUS,
    coach_athlete_relation_error,
    get_active_coach_athlete_relation,
)


def test_constants_are_consistent():
    assert COACH_ATHLETE_NOT_LINKED_STATUS == 404
    assert COACH_ATHLETE_NOT_LINKED_ERROR


def test_get_active_coach_athlete_relation_returns_scalar_result():
    rel = object()
    db = MagicMock()
    db.scalar.return_value = rel
    assert get_active_coach_athlete_relation(db, coach_id=1, athlete_id=2) is rel
    db.scalar.assert_called_once()


def test_coach_athlete_relation_error_when_missing():
    db = MagicMock()
    db.scalar.return_value = None
    assert coach_athlete_relation_error(db, 1, 2) == COACH_ATHLETE_NOT_LINKED_ERROR


def test_coach_athlete_relation_error_when_present():
    db = MagicMock()
    db.scalar.return_value = object()
    assert coach_athlete_relation_error(db, 1, 2) is None
