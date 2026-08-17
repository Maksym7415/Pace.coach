"""Activity ingestion pipeline service."""

from __future__ import annotations

import hashlib
import logging
from datetime import datetime, timedelta, timezone
from pathlib import Path

from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from src.core.database import SessionLocal
from src.modules.activity_import.background import BackgroundTaskQueue
from src.modules.activity_import.enums import ImportSource, ImportStatus
from src.modules.activity_import.models import (
    ActivityImport,
    ActivityLap,
    ActivitySource,
    ActivityTrackPoint,
    StoredFile,
)
from src.modules.activity_import.storage import StorageProvider
from src.modules.athlete_profile.models import Sport
from src.modules.fit_parser import FitParser, FitParserError
from src.modules.fit_parser.models import ActivityMeta, NormalizedActivity
from src.modules.gear_track.models import Activity, ActivityGearUsage, ActivityType, Gear
from src.modules.gear_track.service import (
    _gear_type_for_sport_code,
    _gear_usage_value,
    _recompute_gear_value_covered,
    _round_km,
)
from src.modules.training.activity_link import try_link_activity_to_workout

logger = logging.getLogger("coach_app.activity_import")

MAX_FILE_SIZE_BYTES = 20 * 1024 * 1024
ALLOWED_EXTENSIONS = {".fit"}
FIT_MIME_TYPE = "application/vnd.ant.fit"

DUPLICATE_DURATION_TOLERANCE_SECONDS = 5
DUPLICATE_DISTANCE_TOLERANCE_METERS = 10
DUPLICATE_START_TIME_TOLERANCE = timedelta(minutes=5)


class DuplicateActivityError(Exception):
    """Raised when an imported activity matches an existing one."""


class ActivityIngestionService:
    def __init__(
        self,
        db: Session,
        storage: StorageProvider,
        queue: BackgroundTaskQueue,
        parser: FitParser | None = None,
    ) -> None:
        self.db = db
        self.storage = storage
        self.queue = queue
        self.parser = parser or FitParser()

    def ingest_fit_upload(
        self,
        file_bytes: bytes,
        filename: str,
        athlete_id: int,
    ) -> tuple[ActivityImport | None, str | None, int]:
        error = self._validate_file(file_bytes, filename)
        if error:
            return None, error, 400

        checksum = hashlib.sha256(file_bytes).hexdigest()
        conflict = self._checksum_import_conflict(athlete_id, checksum)
        if conflict:
            return None, conflict, 409

        try:
            metadata = self.storage.upload(
                file_bytes,
                filename=filename,
                content_type=FIT_MIME_TYPE,
            )
        except Exception as exc:
            logger.exception("Failed to upload FIT file for athlete_id=%s", athlete_id)
            return None, f"Failed to store file: {exc}", 500

        stored_file = StoredFile(
            provider=metadata.provider,
            bucket=metadata.bucket,
            object_key=metadata.object_key,
            original_filename=filename,
            mime_type=FIT_MIME_TYPE,
            checksum=checksum,
            file_size=metadata.file_size,
        )
        activity_import = ActivityImport(
            athlete_id=athlete_id,
            stored_file=stored_file,
            source=ImportSource.FIT_UPLOAD.value,
            status=ImportStatus.PENDING.value,
        )
        self.db.add(stored_file)
        self.db.add(activity_import)
        self.db.commit()
        self.db.refresh(activity_import)

        self.queue.enqueue(self._process_import, activity_import.id)
        return activity_import, None, 202

    def _checksum_import_conflict(self, athlete_id: int, checksum: str) -> str | None:
        in_flight_import_id = self.db.scalar(
            select(ActivityImport.id)
            .join(StoredFile)
            .where(
                ActivityImport.athlete_id == athlete_id,
                StoredFile.checksum == checksum,
                ActivityImport.status.in_(
                    [ImportStatus.PENDING.value, ImportStatus.PROCESSING.value]
                ),
            )
            .limit(1)
        )
        if in_flight_import_id is not None:
            return "This file is already being imported"

        existing_activity_id = self.db.scalar(
            select(Activity.id)
            .join(ActivitySource)
            .where(
                Activity.user_id == athlete_id,
                ActivitySource.provider == ImportSource.FIT_UPLOAD.value,
                ActivitySource.external_id == checksum,
            )
            .limit(1)
        )
        if existing_activity_id is not None:
            return "This file has already been imported"

        return None

    def _process_import(self, import_id: int) -> None:
        db = SessionLocal()
        try:
            self._process_import_with_session(db, import_id)
        except Exception as exc:
            logger.exception("Unhandled error processing activity import id=%s", import_id)
            self._force_failed_status(import_id, str(exc))
        finally:
            db.close()

    def _process_import_with_session(self, db: Session, import_id: int) -> None:
        activity_import = db.get(ActivityImport, import_id)
        if activity_import is None:
            logger.error("Activity import id=%s not found", import_id)
            return

        if activity_import.status in (
            ImportStatus.COMPLETED.value,
            ImportStatus.FAILED.value,
        ):
            return

        if self._activity_exists_for_import(db, import_id):
            self._try_mark_completed(db, activity_import)
            return

        if not self._claim_import(db, import_id):
            logger.debug("Activity import id=%s is already being processed", import_id)
            return

        activity_import = db.get(ActivityImport, import_id)
        if activity_import is None:
            logger.error("Activity import id=%s not found after claim", import_id)
            return

        stored_file = activity_import.stored_file
        if stored_file is None:
            self._try_mark_failed(db, activity_import, "Stored file record is missing")
            return

        try:
            file_bytes = self.storage.download(stored_file.object_key)
            normalized = self.parser.parse(file_bytes)
            self._check_duplicate(db, activity_import.athlete_id, normalized.meta)
            activity = self._persist_activity(db, activity_import, normalized)
            activity_import.status = ImportStatus.COMPLETED.value
            activity_import.completed_at = datetime.now(timezone.utc)
            activity_import.error_message = None
            db.commit()
            logger.info(
                "Completed activity import id=%s activity_id=%s",
                import_id,
                activity.id,
            )
        except DuplicateActivityError as exc:
            db.rollback()
            self._try_mark_failed(db, activity_import, str(exc))
        except FitParserError as exc:
            db.rollback()
            self._try_mark_failed(db, activity_import, f"FIT parse error: {exc}")
        except IntegrityError:
            db.rollback()
            if self._activity_exists_for_import(db, import_id):
                activity_import = db.get(ActivityImport, import_id)
                if activity_import is not None:
                    self._try_mark_completed(db, activity_import)
            else:
                logger.exception("Integrity error processing activity import id=%s", import_id)
                self._try_mark_failed(db, activity_import, "Failed to persist activity")
        except Exception as exc:
            db.rollback()
            logger.exception("Failed to process activity import id=%s", import_id)
            self._try_mark_failed(db, activity_import, str(exc))

    @staticmethod
    def _activity_exists_for_import(db: Session, import_id: int) -> bool:
        return (
            db.scalar(select(Activity.id).where(Activity.activity_import_id == import_id))
            is not None
        )

    def _claim_import(self, db: Session, import_id: int) -> bool:
        now = datetime.now(timezone.utc)
        result = db.execute(
            update(ActivityImport)
            .where(
                ActivityImport.id == import_id,
                ActivityImport.status == ImportStatus.PENDING.value,
            )
            .values(
                status=ImportStatus.PROCESSING.value,
                started_at=now,
                error_message=None,
            )
        )
        if result.rowcount:
            db.commit()
            return True
        db.rollback()
        return False

    def _try_mark_completed(self, db: Session, activity_import: ActivityImport) -> None:
        try:
            self._mark_completed(db, activity_import)
        except Exception:
            logger.exception("Failed to mark import id=%s as completed in-session", activity_import.id)
            self._force_completed_status(activity_import.id)

    def _try_mark_failed(self, db: Session, activity_import: ActivityImport, message: str) -> None:
        try:
            self._mark_failed(db, activity_import, message)
        except Exception:
            logger.exception("Failed to mark import id=%s as failed in-session", activity_import.id)
            self._force_failed_status(activity_import.id, message)

    def _mark_completed(self, db: Session, activity_import: ActivityImport) -> None:
        activity_import = db.merge(activity_import)
        activity_import.status = ImportStatus.COMPLETED.value
        activity_import.completed_at = datetime.now(timezone.utc)
        activity_import.error_message = None
        db.commit()

    def _force_completed_status(self, import_id: int) -> None:
        self._force_terminal_status(import_id, ImportStatus.COMPLETED)

    def _force_failed_status(self, import_id: int, message: str) -> None:
        self._force_terminal_status(import_id, ImportStatus.FAILED, error_message=message)

    def _force_terminal_status(
        self,
        import_id: int,
        status: ImportStatus,
        *,
        error_message: str | None = None,
    ) -> None:
        db = SessionLocal()
        try:
            activity_import = db.get(ActivityImport, import_id)
            if activity_import is None:
                return
            if activity_import.status in (
                ImportStatus.COMPLETED.value,
                ImportStatus.FAILED.value,
            ):
                return
            if status == ImportStatus.COMPLETED and not self._activity_exists_for_import(
                db, import_id
            ):
                status = ImportStatus.FAILED
                error_message = error_message or "Import processing did not complete"
            activity_import.status = status.value
            activity_import.error_message = error_message
            activity_import.completed_at = datetime.now(timezone.utc)
            db.commit()
        except Exception:
            logger.exception(
                "Failed to force status=%s for activity import id=%s",
                status.value,
                import_id,
            )
            db.rollback()
        finally:
            db.close()

    def _validate_file(self, file_bytes: bytes, filename: str) -> str | None:
        extension = Path(filename or "").suffix.lower()
        if extension not in ALLOWED_EXTENSIONS:
            return "Only .fit files are supported"
        if not file_bytes:
            return "Uploaded file is empty"
        if len(file_bytes) > MAX_FILE_SIZE_BYTES:
            return "File exceeds maximum size of 20 MB"
        return None

    def _check_duplicate(self, db: Session, athlete_id: int, meta: ActivityMeta) -> None:
        if meta.start_time is None:
            return

        activity_date = meta.start_time.date()
        duration_seconds = meta.duration
        distance_meters = meta.distance

        candidates = db.scalars(
            select(Activity).where(
                Activity.user_id == athlete_id,
                Activity.date == activity_date,
            )
        ).all()

        for existing in candidates:
            if not self._is_duplicate(
                existing,
                meta.start_time,
                duration_seconds,
                distance_meters,
            ):
                continue
            raise DuplicateActivityError(
                "Duplicate activity detected for athlete, start time, duration, and distance"
            )

    @staticmethod
    def _normalize_start_time(start_time: datetime) -> datetime:
        if start_time.tzinfo is not None:
            return start_time.astimezone(timezone.utc).replace(tzinfo=None)
        return start_time

    def _is_duplicate(
        self,
        existing: Activity,
        import_start_time: datetime,
        duration_seconds: float | None,
        distance_meters: float | None,
    ) -> bool:
        if existing.start_time is not None:
            delta_seconds = abs(
                (
                    self._normalize_start_time(existing.start_time)
                    - self._normalize_start_time(import_start_time)
                ).total_seconds()
            )
            if delta_seconds > DUPLICATE_START_TIME_TOLERANCE.total_seconds():
                return False
        else:
            return False

        comparisons = 0

        if duration_seconds is not None and existing.total_hours is not None:
            comparisons += 1
            existing_duration_seconds = existing.total_hours * 3600
            if abs(existing_duration_seconds - duration_seconds) > DUPLICATE_DURATION_TOLERANCE_SECONDS:
                return False

        if (
            distance_meters is not None
            and distance_meters > 0
            and existing.total_distance_km > 0
        ):
            comparisons += 1
            existing_distance_meters = existing.total_distance_km * 1000
            if abs(existing_distance_meters - distance_meters) > DUPLICATE_DISTANCE_TOLERANCE_METERS:
                return False

        return comparisons > 0

    def _persist_activity(
        self,
        db: Session,
        activity_import: ActivityImport,
        normalized: NormalizedActivity,
    ) -> Activity:
        meta = normalized.meta
        sport_id, activity_type_id = self._resolve_sport_ids(db, meta)

        if meta.start_time is None:
            raise ValueError("FIT file is missing activity start time")

        total_distance_km = _round_km((meta.distance or 0) / 1000, 0.0)
        total_hours = None
        if meta.duration is not None:
            total_hours = round(meta.duration / 3600, 2)

        activity = Activity(
            user_id=activity_import.athlete_id,
            name=self._build_activity_name(meta),
            date=meta.start_time.date(),
            start_time=meta.start_time,
            total_distance_km=total_distance_km,
            total_hours=total_hours,
            sport_id=sport_id,
            activity_type_id=activity_type_id,
            source=ImportSource.FIT_UPLOAD.value,
            activity_import_id=activity_import.id,
        )
        db.add(activity)
        db.flush()

        for lap in normalized.laps:
            db.add(
                ActivityLap(
                    activity_id=activity.id,
                    lap_number=lap.lap_number,
                    duration=lap.duration,
                    timer_time=lap.timer_time,
                    distance=lap.distance,
                    avg_hr=lap.avg_hr,
                    max_hr=lap.max_hr,
                    avg_power=lap.avg_power,
                    avg_speed=lap.avg_speed,
                    avg_pace=lap.avg_pace,
                    start_time=lap.start_time,
                    message_index=lap.message_index,
                    wkt_step_index=lap.wkt_step_index,
                    lap_trigger=lap.lap_trigger,
                    intensity=lap.intensity,
                )
            )

        for point in normalized.track_points:
            db.add(
                ActivityTrackPoint(
                    activity_id=activity.id,
                    timestamp=point.timestamp,
                    latitude=point.latitude,
                    longitude=point.longitude,
                    altitude=point.altitude,
                    distance=point.distance,
                    speed=point.speed,
                    pace=point.pace,
                    heart_rate=point.heart_rate,
                    cadence=point.cadence,
                    power=point.power,
                    temperature=point.temperature,
                    running_power=point.running_power,
                    stride_length=point.stride_length,
                    vertical_oscillation=point.vertical_oscillation,
                    ground_contact_time=point.ground_contact_time,
                    left_right_balance=point.left_right_balance,
                    stamina=point.stamina,
                )
            )

        raw_metadata: dict = {
            "device_name": meta.device_name,
            "developer_fields": normalized.developer_fields,
        }
        if normalized.device_workout is not None:
            raw_metadata["device_workout"] = normalized.device_workout.model_dump(
                mode="json"
            )
        if normalized.events:
            raw_metadata["events"] = [
                event.model_dump(mode="json") for event in normalized.events
            ]

        db.add(
            ActivitySource(
                activity_id=activity.id,
                provider=ImportSource.FIT_UPLOAD.value,
                external_id=activity_import.stored_file.checksum if activity_import.stored_file else None,
                raw_metadata=raw_metadata,
            )
        )

        sport = db.get(Sport, sport_id) if sport_id else None
        if sport:
            self._assign_default_gear(
                db,
                activity_import.athlete_id,
                activity.id,
                sport.code,
                total_distance_km=total_distance_km,
                total_hours=total_hours,
            )
            linked = try_link_activity_to_workout(
                db,
                activity_import.athlete_id,
                activity.id,
                activity.date,
                sport.code,
                sport_id=activity.sport_id,
            )
            if linked is not None and linked.steps:
                try:
                    from src.modules.execution.service import ExecutionMatchingService

                    ExecutionMatchingService(db).match_from_normalized(
                        workout_id=linked.id,
                        activity_id=activity.id,
                        normalized=normalized,
                        vendor="garmin",
                    )
                except Exception:
                    logger.exception(
                        "Execution matching failed for workout %s activity %s",
                        linked.id,
                        activity.id,
                    )

        return activity

    def _resolve_sport_ids(
        self,
        db: Session,
        meta: ActivityMeta,
    ) -> tuple[int | None, int | None]:
        sport_id = None
        activity_type_id = None

        if meta.sport:
            sport = db.scalar(
                select(Sport).where(Sport.code == meta.sport, Sport.is_active.is_(True))
            )
            if sport:
                sport_id = sport.id
                if meta.activity_type:
                    activity_type = db.scalar(
                        select(ActivityType).where(
                            ActivityType.sport_id == sport.id,
                            ActivityType.code == meta.activity_type,
                            ActivityType.is_active.is_(True),
                        )
                    )
                    if activity_type:
                        activity_type_id = activity_type.id

        return sport_id, activity_type_id

    def _build_activity_name(self, meta: ActivityMeta) -> str:
        label = meta.activity_type or meta.sport
        base = label.replace("_", " ").title() if label else "Imported Activity"
        if meta.start_time is None:
            return base
        return f"{base} · {meta.start_time.date().isoformat()}"

    def _assign_default_gear(
        self,
        db: Session,
        athlete_id: int,
        activity_id: int,
        sport_code: str,
        *,
        total_distance_km: float,
        total_hours: float | None,
    ) -> None:
        gear_type = _gear_type_for_sport_code(sport_code)
        if not gear_type:
            return

        default_gear = db.scalar(
            select(Gear).where(
                Gear.user_id == athlete_id,
                Gear.activity_type == gear_type,
                Gear.is_default.is_(True),
                Gear.status == "active",
            )
        )
        if not default_gear:
            return

        value = _gear_usage_value(
            default_gear,
            total_distance_km=total_distance_km,
            total_hours=total_hours,
        )
        if value <= 0:
            return

        db.add(ActivityGearUsage(activity_id=activity_id, gear_id=default_gear.id, value=value))
        db.flush()
        _recompute_gear_value_covered(db, default_gear.id)

    def _mark_failed(self, db: Session, activity_import: ActivityImport, message: str) -> None:
        activity_import = db.merge(activity_import)
        activity_import.status = ImportStatus.FAILED.value
        activity_import.error_message = message
        activity_import.completed_at = datetime.now(timezone.utc)
        db.commit()
