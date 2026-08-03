"""Tests for FIT import duplicate detection."""

from datetime import datetime, timedelta
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from src.modules.activity_import.service import ActivityIngestionService
from src.modules.fit_parser.models import ActivityMeta


def _activity(
    *,
    start_time: datetime | None = None,
    total_hours: float | None = None,
    total_distance_km: float = 0.0,
):
    return SimpleNamespace(
        start_time=start_time,
        total_hours=total_hours,
        total_distance_km=total_distance_km,
    )


@pytest.fixture
def service() -> ActivityIngestionService:
    return ActivityIngestionService(db=None, storage=None, queue=None)


class TestIsDuplicate:
    def test_same_start_time_and_metrics_is_duplicate(self, service: ActivityIngestionService):
        start = datetime(2026, 7, 6, 8, 0, 0)
        existing = _activity(start_time=start, total_hours=1.0, total_distance_km=10.0)

        assert service._is_duplicate(existing, start, 3600.0, 10000.0) is True

    def test_different_start_time_on_same_day_is_not_duplicate(self, service: ActivityIngestionService):
        morning = datetime(2026, 7, 6, 7, 0, 0)
        evening = datetime(2026, 7, 6, 19, 0, 0)
        existing = _activity(start_time=morning, total_hours=1.0, total_distance_km=10.0)

        assert service._is_duplicate(existing, evening, 3600.0, 10000.0) is False

    def test_start_time_within_tolerance_is_duplicate(self, service: ActivityIngestionService):
        start = datetime(2026, 7, 6, 8, 0, 0)
        slightly_later = start + timedelta(minutes=3)
        existing = _activity(start_time=start, total_hours=1.0, total_distance_km=10.0)

        assert service._is_duplicate(existing, slightly_later, 3600.0, 10000.0) is True

    def test_start_time_outside_tolerance_is_not_duplicate(self, service: ActivityIngestionService):
        start = datetime(2026, 7, 6, 8, 0, 0)
        later = start + timedelta(minutes=6)
        existing = _activity(start_time=start, total_hours=1.0, total_distance_km=10.0)

        assert service._is_duplicate(existing, later, 3600.0, 10000.0) is False

    def test_existing_without_start_time_is_not_duplicate(self, service: ActivityIngestionService):
        existing = _activity(start_time=None, total_hours=1.0, total_distance_km=10.0)
        import_start = datetime(2026, 7, 6, 8, 0, 0)

        assert service._is_duplicate(existing, import_start, 3600.0, 10000.0) is False

    def test_missing_metrics_is_not_duplicate(self, service: ActivityIngestionService):
        start = datetime(2026, 7, 6, 8, 0, 0)
        existing = _activity(start_time=start, total_hours=None, total_distance_km=0.0)

        assert service._is_duplicate(existing, start, None, None) is False

    def test_partial_metrics_with_zero_stored_distance_is_not_duplicate(self, service: ActivityIngestionService):
        start = datetime(2026, 7, 6, 8, 0, 0)
        existing = _activity(start_time=start, total_hours=None, total_distance_km=0.0)

        assert service._is_duplicate(existing, start, 3.0, None) is False

    def test_duration_mismatch_is_not_duplicate(self, service: ActivityIngestionService):
        start = datetime(2026, 7, 6, 8, 0, 0)
        existing = _activity(start_time=start, total_hours=1.0, total_distance_km=10.0)

        assert service._is_duplicate(existing, start, 7200.0, 10000.0) is False

    def test_distance_mismatch_is_not_duplicate(self, service: ActivityIngestionService):
        start = datetime(2026, 7, 6, 8, 0, 0)
        existing = _activity(start_time=start, total_hours=1.0, total_distance_km=10.0)

        assert service._is_duplicate(existing, start, 3600.0, 20000.0) is False

    def test_normalizes_timezone_aware_start_times(self, service: ActivityIngestionService):
        from datetime import timezone

        existing = _activity(
            start_time=datetime(2026, 7, 6, 8, 0, 0, tzinfo=timezone.utc),
            total_hours=1.0,
            total_distance_km=10.0,
        )
        import_start = datetime(2026, 7, 6, 10, 0, 0, tzinfo=timezone(timedelta(hours=2)))

        assert service._is_duplicate(existing, import_start, 3600.0, 10000.0) is True


class TestChecksumDedup:
    def test_rejects_when_import_is_in_flight(self):
        db = MagicMock()
        db.scalar.return_value = 7
        storage = MagicMock()
        queue = MagicMock()
        service = ActivityIngestionService(db=db, storage=storage, queue=queue)

        result = service.ingest_fit_upload(b"fit-bytes", "run.fit", athlete_id=1)

        assert result == (None, "This file is already being imported", 409)
        storage.upload.assert_not_called()
        queue.enqueue.assert_not_called()

    def test_rejects_when_file_was_already_imported(self):
        db = MagicMock()
        db.scalar.side_effect = [None, 42]
        storage = MagicMock()
        queue = MagicMock()
        service = ActivityIngestionService(db=db, storage=storage, queue=queue)

        result = service.ingest_fit_upload(b"fit-bytes", "run.fit", athlete_id=1)

        assert result == (None, "This file has already been imported", 409)
        storage.upload.assert_not_called()
        queue.enqueue.assert_not_called()

    def test_checksum_conflict_none_when_clear(self):
        db = MagicMock()
        db.scalar.side_effect = [None, None]
        service = ActivityIngestionService(db=db, storage=MagicMock(), queue=MagicMock())

        assert service._checksum_import_conflict(1, "abc123") is None

    def test_checksum_conflict_detects_in_flight_import(self):
        db = MagicMock()
        db.scalar.return_value = 5
        service = ActivityIngestionService(db=db, storage=MagicMock(), queue=MagicMock())

        assert service._checksum_import_conflict(1, "abc123") == "This file is already being imported"

    def test_checksum_conflict_detects_existing_activity(self):
        db = MagicMock()
        db.scalar.side_effect = [None, 99]
        service = ActivityIngestionService(db=db, storage=MagicMock(), queue=MagicMock())

        assert service._checksum_import_conflict(1, "abc123") == "This file has already been imported"


class TestBuildActivityName:
    def test_prefers_activity_type_over_sport_and_device(self, service: ActivityIngestionService):
        meta = ActivityMeta(
            sport="cycling",
            activity_type="road_ride",
            device_name="garmin 3843",
            start_time=datetime(2026, 7, 23, 10, 0, 0),
        )

        assert service._build_activity_name(meta) == "Road Ride · 2026-07-23"

    def test_falls_back_to_sport_when_activity_type_missing(self, service: ActivityIngestionService):
        meta = ActivityMeta(
            sport="running",
            device_name="garmin fenix2",
            start_time=datetime(2026, 7, 6, 8, 0, 0),
        )

        assert service._build_activity_name(meta) == "Running · 2026-07-06"

    def test_does_not_use_device_name(self, service: ActivityIngestionService):
        meta = ActivityMeta(device_name="garmin 3843", start_time=datetime(2026, 7, 23, 10, 0, 0))

        assert service._build_activity_name(meta) == "Imported Activity · 2026-07-23"

    def test_missing_start_time_omits_date(self, service: ActivityIngestionService):
        meta = ActivityMeta(sport="cycling", activity_type="gravel_ride")

        assert service._build_activity_name(meta) == "Gravel Ride"

    def test_fully_missing_meta_uses_imported_activity(self, service: ActivityIngestionService):
        assert service._build_activity_name(ActivityMeta()) == "Imported Activity"
