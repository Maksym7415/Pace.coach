"""
Strava webhook: verify subscription and handle activity create/update events.
"""
import logging
import queue
import threading
import time
from collections.abc import Callable
from datetime import date, datetime, timezone
from typing import Any

import requests
from sqlalchemy import func

from src.core.database import SessionLocal
from src.modules.athlete_profile.models import Sport
from src.modules.gear_track.models import Activity, ActivityGearUsage, Gear
from src.modules.gear_track.service import _gear_type_for_sport_code, _gear_usage_value
from src.modules.third_party.strava.models import UserStrava
from src.modules.training.activity_link import try_link_activity_to_workout

STRAVA_API_BASE = "https://www.strava.com/api/v3"

RUN_TYPES = {"Run", "VirtualRun", "Treadmill", "TrailRun", "ObstacleRun"}
BIKE_TYPES = {"Ride", "VirtualRide", "GravelRide", "MountainBikeRide", "EBikeRide"}
SWIM_TYPES = {"Swim", "PoolSwim", "OpenWaterSwim"}

logger = logging.getLogger("coach_app.strava.webhook")


def _fetch_strava_activity(access_token: str, object_id: int):
    """GET activity from Strava with simple backoff on rate limits / 5xx."""
    url = f"{STRAVA_API_BASE}/activities/{object_id}"
    headers = {"Authorization": f"Bearer {access_token}"}
    last_resp = None
    for attempt in range(3):
        if attempt:
            time.sleep(1.5 * attempt)
        last_resp = requests.get(url, headers=headers, timeout=15)
        if last_resp.status_code == 200:
            return last_resp
        if last_resp.status_code == 429 or last_resp.status_code >= 500:
            logger.warning(
                "Strava activity fetch retryable status=%s object_id=%s attempt=%s",
                last_resp.status_code,
                object_id,
                attempt,
            )
            continue
        return last_resp
    return last_resp


def _map_strava_sport_to_sport_code(sport_type: str) -> str | None:
    """Map Strava sport_type to internal sport code (running, cycling, swimming)."""
    if not sport_type:
        return None
    st = sport_type.strip()
    if st in RUN_TYPES or st.startswith("Run"):
        return "running"
    if st in BIKE_TYPES:
        return "cycling"
    if st in SWIM_TYPES:
        return "swimming"
    return None


def _is_supported_sport(sport_type: str) -> bool:
    """Check if we import this sport (running, cycling, swimming)."""
    return _map_strava_sport_to_sport_code(sport_type) is not None


def _parse_strava_local_start(iso: str) -> date:
    """Calendar day from Strava start_date_local (athlete wall-clock time)."""
    cleaned = iso.strip().removesuffix("Z")
    return datetime.fromisoformat(cleaned).date()


def _parse_strava_utc_start(iso: str) -> date:
    """Calendar day from Strava start_date (UTC)."""
    return datetime.fromisoformat(iso.replace("Z", "+00:00")).date()


def activity_date_from_strava_payload(data: dict) -> date:
    """
    Derive the activity calendar date aligned with the athlete's local day.
    Prefers start_date_local; falls back to UTC start_date, then today (UTC).
    """
    local = data.get("start_date_local")
    if local:
        try:
            return _parse_strava_local_start(local)
        except (ValueError, TypeError):
            logger.warning("Invalid start_date_local from Strava; falling back to start_date")

    utc_start = data.get("start_date")
    if utc_start:
        try:
            return _parse_strava_utc_start(utc_start)
        except (ValueError, TypeError):
            logger.warning("Invalid start_date from Strava; defaulting to current date")

    return datetime.now(timezone.utc).date()


_task_queue: "queue.Queue[tuple[Callable[..., Any], tuple[Any, ...], dict[str, Any]]]" = queue.Queue()
_worker_started = False
_worker_lock = threading.Lock()


def _ensure_worker() -> None:
    """Start a single background worker thread for webhook tasks."""
    global _worker_started
    if _worker_started:
        return
    with _worker_lock:
        if _worker_started:
            return

        def _worker() -> None:
            while True:
                func_, args, kwargs = _task_queue.get()
                try:
                    func_(*args, **kwargs)
                except Exception:
                    logger.exception("Unhandled exception in webhook worker")
                finally:
                    _task_queue.task_done()

        t = threading.Thread(target=_worker, name="strava-webhook-worker", daemon=True)
        t.start()
        _worker_started = True


def _enqueue_task(func_: Callable[..., Any], *args: Any, **kwargs: Any) -> None:
    """Enqueue a background task for the webhook worker."""
    _ensure_worker()
    _task_queue.put((func_, args, kwargs))


def process_activity_create(owner_id: int, object_id: int) -> None:
    """
    Background task: fetch activity from Strava, create in DB for run/bike/swim.
    owner_id = Strava athlete ID, object_id = Strava activity ID.
    """

    def _task() -> None:
        from src.modules.third_party.strava.service import StravaService

        db = SessionLocal()
        try:
            logger.info("Processing Strava create event owner_id=%s object_id=%s", owner_id, object_id)
            us = db.query(UserStrava).filter_by(strava_athlete_id=owner_id).first()
            if not us:
                logger.info("No UserStrava mapping found for owner_id=%s", owner_id)
                return
            svc = StravaService(db)
            tokens = svc.get_tokens(us.user_id)
            if not tokens:
                logger.warning("No valid Strava tokens for user_id=%s", us.user_id)
                return
            access_token = tokens["access_token"]
            resp = _fetch_strava_activity(access_token, object_id)
            if resp.status_code != 200:
                logger.warning(
                    "Failed to fetch Strava activity id=%s status=%s",
                    object_id,
                    resp.status_code,
                )
                return
            data = resp.json()
            if db.query(Activity).filter_by(strava_activity_id=object_id, user_id=us.user_id).first():
                logger.info("Activity already exists for user_id=%s strava_activity_id=%s", us.user_id, object_id)
                return
            sport_type = data.get("type") or data.get("sport_type", "")
            if not _is_supported_sport(sport_type):
                logger.info("Skipping unsupported Strava sport_type=%s", sport_type)
                return
            sport_code = _map_strava_sport_to_sport_code(sport_type)
            if not sport_code:
                return
            sport = db.query(Sport).filter_by(code=sport_code, is_active=True).first()
            if not sport:
                logger.warning("Sport not found for code=%s", sport_code)
                return
            distance_m = data.get("distance") or 0
            distance_km = round(distance_m / 1000.0, 2)
            moving_time_sec = data.get("moving_time") or 0
            moving_hours = round(moving_time_sec / 3600.0, 2) if moving_time_sec else None
            name = data.get("name") or "Strava Activity"
            date = activity_date_from_strava_payload(data)

            activity = Activity(
                user_id=us.user_id,
                name=name,
                date=date,
                total_distance_km=distance_km if distance_km else 0,
                total_hours=moving_hours,
                sport_id=sport.id,
                activity_type_id=None,
                source="strava",
                strava_activity_id=object_id,
            )
            db.add(activity)
            db.flush()

            gear_type = _gear_type_for_sport_code(sport_code)
            default_gear = None
            if gear_type:
                default_gear = (
                    db.query(Gear)
                    .filter_by(
                        user_id=us.user_id,
                        activity_type=gear_type,
                        is_default=True,
                        status="active",
                    )
                    .first()
                )
            if default_gear:
                value = _gear_usage_value(
                    default_gear,
                    total_distance_km=distance_km,
                    total_hours=moving_hours,
                )
                if value and value > 0:
                    db.add(
                        ActivityGearUsage(
                            activity_id=activity.id,
                            gear_id=default_gear.id,
                            value=value,
                        )
                    )
                    db.flush()
                    total = db.query(func.coalesce(func.sum(ActivityGearUsage.value), 0)).filter_by(
                        gear_id=default_gear.id
                    ).scalar()
                    default_gear.value_covered = round(float(total), 2)

            try_link_activity_to_workout(
                db, us.user_id, activity.id, date, sport_code
            )

            db.commit()
            logger.info("Created Strava activity user_id=%s activity_id=%s", us.user_id, activity.id)
        except Exception:
            logger.exception(
                "Error while processing Strava create event owner_id=%s object_id=%s",
                owner_id,
                object_id,
            )
            db.rollback()
        finally:
            db.close()

    _enqueue_task(_task)


def process_activity_update(owner_id: int, object_id: int, updates: dict) -> None:
    """
    Background task: update activity title in DB when Strava sends an update event.
    owner_id = Strava athlete ID, object_id = Strava activity ID, updates = dict with changed fields.
    """

    def _task() -> None:
        db = SessionLocal()
        try:
            logger.info("Processing Strava update event owner_id=%s object_id=%s", owner_id, object_id)
            us = db.query(UserStrava).filter_by(strava_athlete_id=owner_id).first()
            if not us:
                logger.info("No UserStrava mapping for Strava update owner_id=%s", owner_id)
                return
            activity = (
                db.query(Activity)
                .filter_by(
                    strava_activity_id=object_id,
                    user_id=us.user_id,
                )
                .first()
            )
            if not activity:
                logger.info(
                    "No existing activity for Strava update object_id=%s user_id=%s",
                    object_id,
                    us.user_id,
                )
                return
            new_title = updates.get("title")
            if new_title is None:
                return
            new_title = (new_title or "").strip()
            if new_title:
                activity.name = new_title
                db.commit()
                logger.info("Updated activity title for activity_id=%s", activity.id)
        except Exception:
            logger.exception(
                "Error while processing Strava update event owner_id=%s object_id=%s",
                owner_id,
                object_id,
            )
            db.rollback()
        finally:
            db.close()

    _enqueue_task(_task)
