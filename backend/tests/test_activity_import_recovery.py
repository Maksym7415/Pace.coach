"""Tests for activity import job recovery and failure handling."""

from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from src.modules.activity_import.enums import ImportStatus
from src.modules.activity_import.recovery import (
    STALE_PROCESSING_AFTER,
    recover_stale_imports,
)
from src.modules.activity_import.service import ActivityIngestionService


@pytest.fixture
def service() -> ActivityIngestionService:
    return ActivityIngestionService(db=None, storage=None, queue=None)


class TestForceTerminalStatus:
    def test_force_failed_uses_fresh_session(self, service: ActivityIngestionService):
        activity_import = SimpleNamespace(
            id=7,
            status=ImportStatus.PROCESSING.value,
            error_message=None,
            completed_at=None,
        )
        mock_db = MagicMock()
        mock_db.get.return_value = activity_import

        with patch("src.modules.activity_import.service.SessionLocal", return_value=mock_db):
            service._force_failed_status(7, "boom")

        assert activity_import.status == ImportStatus.FAILED.value
        assert activity_import.error_message == "boom"
        assert activity_import.completed_at is not None
        mock_db.commit.assert_called_once()

    def test_force_completed_requires_existing_activity(self, service: ActivityIngestionService):
        activity_import = SimpleNamespace(
            id=8,
            status=ImportStatus.PROCESSING.value,
            error_message=None,
            completed_at=None,
        )
        mock_db = MagicMock()
        mock_db.get.return_value = activity_import

        with (
            patch("src.modules.activity_import.service.SessionLocal", return_value=mock_db),
            patch.object(service, "_activity_exists_for_import", return_value=False),
        ):
            service._force_completed_status(8)

        assert activity_import.status == ImportStatus.FAILED.value
        assert activity_import.error_message == "Import processing did not complete"

    def test_try_mark_failed_falls_back_when_session_commit_fails(
        self, service: ActivityIngestionService
    ):
        activity_import = SimpleNamespace(id=9)
        mock_db = MagicMock()
        mock_db.merge.side_effect = RuntimeError("session broken")

        with patch.object(service, "_force_failed_status") as force_failed:
            service._try_mark_failed(mock_db, activity_import, "parse error")

        force_failed.assert_called_once_with(9, "parse error")


class TestRecoverStaleImports:
    def test_requeues_stale_pending_and_resets_stale_processing(self):
        stale_pending_id = 1
        stale_processing = SimpleNamespace(
            id=2,
            status=ImportStatus.PROCESSING.value,
            started_at=datetime.now(timezone.utc) - STALE_PROCESSING_AFTER - timedelta(minutes=1),
        )
        mock_db = MagicMock()
        mock_db.scalars.side_effect = [
            SimpleNamespace(all=lambda: [stale_pending_id]),
            SimpleNamespace(all=lambda: [stale_processing]),
        ]
        mock_db.scalar.return_value = None
        enqueued: list[int] = []

        with patch("src.modules.activity_import.recovery.SessionLocal", return_value=mock_db):
            recovered = recover_stale_imports(enqueued.append)

        assert recovered == 2
        assert enqueued == [1, 2]
        mock_db.execute.assert_called_once()
        mock_db.commit.assert_called_once()

    def test_marks_stale_processing_completed_when_activity_exists(self):
        stale_processing = SimpleNamespace(
            id=3,
            status=ImportStatus.PROCESSING.value,
            started_at=datetime.now(timezone.utc) - STALE_PROCESSING_AFTER - timedelta(minutes=1),
            error_message="old",
            completed_at=None,
        )
        mock_db = MagicMock()
        mock_db.scalars.side_effect = [
            SimpleNamespace(all=lambda: []),
            SimpleNamespace(all=lambda: [stale_processing]),
        ]
        mock_db.scalar.return_value = 99
        enqueued: list[int] = []

        with patch("src.modules.activity_import.recovery.SessionLocal", return_value=mock_db):
            recovered = recover_stale_imports(enqueued.append)

        assert recovered == 1
        assert enqueued == []
        assert stale_processing.status == ImportStatus.COMPLETED.value
        assert stale_processing.error_message is None
        assert stale_processing.completed_at is not None

    def test_ignores_recent_pending_jobs(self):
        mock_db = MagicMock()
        mock_db.scalars.side_effect = [
            SimpleNamespace(all=lambda: []),
            SimpleNamespace(all=lambda: []),
        ]
        enqueued: list[int] = []

        with patch("src.modules.activity_import.recovery.SessionLocal", return_value=mock_db):
            recovered = recover_stale_imports(enqueued.append)

        assert recovered == 0
        assert enqueued == []
