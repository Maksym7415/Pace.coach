"""
Strava webhook: verify subscription and handle activity create/update events.
"""
import logging
import queue
import threading
import time
from datetime import datetime, timezone
from typing import Callable, Any

import requests
from sqlalchemy import func

from src.models import db, UserStrava, Activity, ActivityGearUsage, Gear

STRAVA_API_BASE = "https://www.strava.com/api/v3"

RUN_TYPES = {"Run", "VirtualRun", "Treadmill", "TrailRun", "ObstacleRun"}
BIKE_TYPES = {"Ride", "VirtualRide", "GravelRide", "MountainBikeRide", "EBikeRide"}
SWIM_TYPES = {"Swim", "PoolSwim", "OpenWaterSwim"}

logger = logging.getLogger("shoe_tracker.webhook")


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


def _map_strava_sport_to_activity_type(sport_type: str) -> str:
    """Map Strava sport_type to internal activity_type (run, bike, swim, other)."""
    if not sport_type:
        return "other"
    st = sport_type.strip()
    if st in RUN_TYPES or st.startswith("Run"):
        return "run"
    if st in BIKE_TYPES:
        return "bike"
    if st in SWIM_TYPES:
        return "swim"
    return "other"


def _is_supported_sport(sport_type: str) -> bool:
    """Check if we import this sport (run, bike, swim)."""
    return _map_strava_sport_to_activity_type(sport_type) in ("run", "bike", "swim")


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
                    # Errors are logged inside task functions; just avoid crashing the loop.
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


def process_activity_create(owner_id: int, object_id: int, app):
    """
    Background task: fetch activity from Strava, create in DB for run/bike/swim.
    owner_id = Strava athlete ID, object_id = Strava activity ID.
    """

    def _task() -> None:
        from src.services.strava_service import StravaService

        with app.app_context():
            try:
                logger.info("Processing Strava create event owner_id=%s object_id=%s", owner_id, object_id)
                us = db.session.query(UserStrava).filter_by(strava_athlete_id=owner_id).first()
                if not us:
                    logger.info("No UserStrava mapping found for owner_id=%s", owner_id)
                    return
                svc = StravaService(db.session)
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
                if db.session.query(Activity).filter_by(strava_activity_id=object_id, user_id=us.user_id).first():
                    logger.info("Activity already exists for user_id=%s strava_activity_id=%s", us.user_id, object_id)
                    return
                sport_type = data.get("type") or data.get("sport_type", "")
                if not _is_supported_sport(sport_type):
                    logger.info("Skipping unsupported Strava sport_type=%s", sport_type)
                    return
                activity_type = _map_strava_sport_to_activity_type(sport_type)
                distance_m = data.get("distance") or 0
                distance_km = round(distance_m / 1000.0, 2)
                moving_time_sec = data.get("moving_time") or 0
                moving_hours = round(moving_time_sec / 3600.0, 2) if moving_time_sec else None
                name = data.get("name") or "Strava Activity"
                start = data.get("start_date") or data.get("start_date_local")
                if start:
                    try:
                        dt = datetime.fromisoformat(start.replace("Z", "+00:00"))
                        date = dt.date()
                    except (ValueError, TypeError):
                        logger.warning("Invalid start_date from Strava; defaulting to current date")
                        date = datetime.now(timezone.utc).date()
                else:
                    date = datetime.now(timezone.utc).date()

                activity = Activity(
                    user_id=us.user_id,
                    name=name,
                    date=date,
                    total_distance_km=distance_km if distance_km else 0,
                    total_hours=moving_hours,
                    activity_type=activity_type,
                    source="strava",
                    strava_activity_id=object_id,
                )
                db.session.add(activity)
                db.session.flush()

                default_gear = db.session.query(Gear).filter_by(
                    user_id=us.user_id,
                    activity_type=activity_type,
                    is_default=True,
                    status="active",
                ).first()
                if default_gear:
                    value = distance_km if activity_type == "run" else (moving_hours or distance_km)
                    if value and value > 0:
                        db.session.add(
                            ActivityGearUsage(
                                activity_id=activity.id,
                                gear_id=default_gear.id,
                                value=value,
                            )
                        )
                        db.session.flush()
                        total = db.session.query(
                            func.coalesce(func.sum(ActivityGearUsage.value), 0)
                        ).filter_by(gear_id=default_gear.id).scalar()
                        default_gear.value_covered = round(float(total), 2)

                db.session.commit()
                logger.info("Created Strava activity user_id=%s activity_id=%s", us.user_id, activity.id)
            except Exception:
                logger.exception("Error while processing Strava create event owner_id=%s object_id=%s", owner_id, object_id)
                db.session.rollback()

    _enqueue_task(_task)


def process_activity_update(owner_id: int, object_id: int, updates: dict, app):
    """
    Background task: update activity title in DB when Strava sends an update event.
    owner_id = Strava athlete ID, object_id = Strava activity ID, updates = dict with changed fields.
    """

    def _task() -> None:
        with app.app_context():
            try:
                logger.info("Processing Strava update event owner_id=%s object_id=%s", owner_id, object_id)
                us = db.session.query(UserStrava).filter_by(strava_athlete_id=owner_id).first()
                if not us:
                    logger.info("No UserStrava mapping for Strava update owner_id=%s", owner_id)
                    return
                activity = db.session.query(Activity).filter_by(
                    strava_activity_id=object_id,
                    user_id=us.user_id,
                ).first()
                if not activity:
                    logger.info("No existing activity for Strava update object_id=%s user_id=%s", object_id, us.user_id)
                    return
                new_title = updates.get("title")
                if new_title is None:
                    return
                new_title = (new_title or "").strip()
                if new_title:
                    activity.name = new_title
                    db.session.commit()
                    logger.info("Updated activity title for activity_id=%s", activity.id)
            except Exception:
                logger.exception("Error while processing Strava update event owner_id=%s object_id=%s", owner_id, object_id)
                db.session.rollback()

    _enqueue_task(_task)
