"""Unit tests for recovery module."""
from datetime import date, timedelta

import pytest
from fastapi.testclient import TestClient

from src.api.app import create_app
from src.modules.recovery.service import _compute_readiness

client = TestClient(create_app())


def test_compute_readiness_none_when_no_metrics():
    assert _compute_readiness(None, None, None, None, None) is None


def test_compute_readiness_fatigue_only():
    score = _compute_readiness(fatigue=1, soreness=None, mood=None, sleep_quality=None, body_battery=None)
    assert score == 100


def test_compute_readiness_full_metrics():
    score = _compute_readiness(fatigue=5, soreness=5, mood=5, sleep_quality=5, body_battery=50)
    assert score is not None
    assert 0 <= score <= 100


def test_recovery_entries_require_auth():
    response = client.post(
        "/api/recovery/entries",
        json={"entry_date": "2026-06-11", "fatigue": 3},
    )
    assert response.status_code == 401


def test_recovery_today_requires_auth():
    response = client.get("/api/recovery/entries/today")
    assert response.status_code == 401


def test_training_calendar_requires_auth():
    response = client.get("/api/training/calendar?start_date=2026-06-01&end_date=2026-06-30")
    assert response.status_code == 401


def test_training_create_workout_requires_auth():
    response = client.post(
        "/api/training/workouts",
        json={
            "athlete_id": 1,
            "scheduled_date": "2026-06-16",
            "workout_type": "easy",
            "title": "Easy run",
        },
    )
    assert response.status_code == 401


def test_training_assign_workouts_requires_auth():
    response = client.post(
        "/api/training/workouts/assign",
        json={
            "athlete_ids": [1],
            "scheduled_dates": ["2026-06-16"],
            "sport_id": 1,
            "title": "Easy run",
            "steps": [{"type": "run", "duration": 30, "distance": None}],
        },
    )
    assert response.status_code == 401


def test_training_templates_require_auth():
    assert client.get("/api/training/templates").status_code == 401
    assert (
        client.post(
            "/api/training/templates",
            json={
                "sport_id": 1,
                "title": "Easy",
                "steps": [{"type": "run", "duration": 30, "distance": None}],
            },
        ).status_code
        == 401
    )
