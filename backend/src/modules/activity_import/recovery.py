"""Recovery for stale activity import jobs."""

from __future__ import annotations

import logging
from collections.abc import Callable
from datetime import datetime, timedelta, timezone

from sqlalchemy import select, update

from src.core.database import SessionLocal
from src.modules.activity_import.enums import ImportStatus
from src.modules.activity_import.models import ActivityImport
from src.modules.gear_track.models import Activity

logger = logging.getLogger("coach_app.activity_import.recovery")

STALE_PENDING_AFTER = timedelta(minutes=1)
STALE_PROCESSING_AFTER = timedelta(minutes=10)


def recover_stale_imports(enqueue: Callable[[int], None]) -> int:
    """Re-queue imports stuck in pending or processing. Returns count recovered."""
    now = datetime.now(timezone.utc)
    pending_cutoff = now.replace(tzinfo=None) - STALE_PENDING_AFTER
    processing_cutoff = now - STALE_PROCESSING_AFTER
    recovered = 0

    db = SessionLocal()
    try:
        stale_pending_ids = list(
            db.scalars(
                select(ActivityImport.id).where(
                    ActivityImport.status == ImportStatus.PENDING.value,
                    ActivityImport.created_at < pending_cutoff,
                )
            ).all()
        )

        stale_processing = list(
            db.scalars(
                select(ActivityImport).where(
                    ActivityImport.status == ImportStatus.PROCESSING.value,
                    ActivityImport.started_at < processing_cutoff,
                )
            ).all()
        )

        for import_id in stale_pending_ids:
            enqueue(import_id)
            recovered += 1
            logger.info("Re-queued stale pending import id=%s", import_id)

        for activity_import in stale_processing:
            activity_id = db.scalar(
                select(Activity.id).where(Activity.activity_import_id == activity_import.id)
            )
            if activity_id:
                activity_import.status = ImportStatus.COMPLETED.value
                activity_import.completed_at = now
                activity_import.error_message = None
                logger.info(
                    "Marked stale processing import id=%s completed (activity_id=%s exists)",
                    activity_import.id,
                    activity_id,
                )
            else:
                db.execute(
                    update(ActivityImport)
                    .where(ActivityImport.id == activity_import.id)
                    .values(
                        status=ImportStatus.PENDING.value,
                        started_at=None,
                        error_message=None,
                    )
                )
                enqueue(activity_import.id)
                logger.info("Reset stale processing import id=%s to pending", activity_import.id)
            recovered += 1

        db.commit()
    except Exception:
        logger.exception("Failed to recover stale activity imports")
        db.rollback()
    finally:
        db.close()

    return recovered
