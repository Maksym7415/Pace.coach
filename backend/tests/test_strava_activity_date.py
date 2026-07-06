"""Tests for Strava activity calendar date parsing."""
from datetime import date, datetime

from src.modules.third_party.strava.webhook_handler import (
    activity_date_from_strava_payload,
    activity_start_time_from_strava_payload,
)


def test_prefers_start_date_local_over_utc():
    payload = {
        "start_date_local": "2026-06-23T20:00:00",
        "start_date": "2026-06-24T03:00:00Z",
    }
    assert activity_date_from_strava_payload(payload) == date(2026, 6, 23)


def test_start_date_local_with_trailing_z_uses_wall_clock_day():
    payload = {"start_date_local": "2026-06-23T20:00:00Z"}
    assert activity_date_from_strava_payload(payload) == date(2026, 6, 23)


def test_falls_back_to_utc_start_date_when_local_missing():
    payload = {"start_date": "2026-06-24T03:00:00Z"}
    assert activity_date_from_strava_payload(payload) == date(2026, 6, 24)


def test_falls_back_to_utc_start_date_when_local_invalid():
    payload = {
        "start_date_local": "not-a-date",
        "start_date": "2026-06-24T03:00:00Z",
    }
    assert activity_date_from_strava_payload(payload) == date(2026, 6, 24)


def test_start_time_prefers_start_date_local():
    payload = {
        "start_date_local": "2026-06-23T20:00:00",
        "start_date": "2026-06-24T03:00:00Z",
    }
    assert activity_start_time_from_strava_payload(payload) == datetime(2026, 6, 23, 20, 0, 0)


def test_start_time_falls_back_to_utc_start_date():
    payload = {"start_date": "2026-06-24T03:00:00Z"}
    assert activity_start_time_from_strava_payload(payload) == datetime(2026, 6, 24, 3, 0, 0)
