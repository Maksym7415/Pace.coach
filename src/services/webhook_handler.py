"""
Strava webhook: verify subscription and handle activity create/update events.
"""
import threading
from datetime import datetime, timezone

import requests
from sqlalchemy import func

from src.models import db, UserStrava, Activity, ActivityGearUsage, Gear

STRAVA_API_BASE = "https://www.strava.com/api/v3"

RUN_TYPES = {"Run", "VirtualRun", "Treadmill", "TrailRun", "ObstacleRun"}
BIKE_TYPES = {"Ride", "VirtualRide", "GravelRide", "MountainBikeRide", "EBikeRide"}
SWIM_TYPES = {"Swim", "PoolSwim", "OpenWaterSwim"}


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


def process_activity_create(owner_id: int, object_id: int, app):
    """
    Background task: fetch activity from Strava, create in DB for run/bike/swim.
    owner_id = Strava athlete ID, object_id = Strava activity ID.
    """
    def run():
        from src.services.strava_service import StravaService
        with app.app_context():
            try:
                us = db.session.query(UserStrava).filter_by(strava_athlete_id=owner_id).first()
                if not us:
                    return
                svc = StravaService(db.session)
                tokens = svc.get_tokens(us.user_id)
                if not tokens:
                    return
                access_token = tokens["access_token"]
                resp = requests.get(
                    f"{STRAVA_API_BASE}/activities/{object_id}",
                    headers={"Authorization": f"Bearer {access_token}"},
                    timeout=10,
                )
                if resp.status_code != 200:
                    return
                data = resp.json()
                if db.session.query(Activity).filter_by(strava_activity_id=object_id).first():
                    return
                sport_type = data.get("type") or data.get("sport_type", "")
                if not _is_supported_sport(sport_type):
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
            except Exception:
                db.session.rollback()
                raise

    t = threading.Thread(target=run)
    t.daemon = True
    t.start()


def process_activity_update(owner_id: int, object_id: int, updates: dict, app):
    """
    Background task: update activity title in DB when Strava sends an update event.
    owner_id = Strava athlete ID, object_id = Strava activity ID, updates = dict with changed fields.
    """
    def run():
        with app.app_context():
            try:
                activity = db.session.query(Activity).filter_by(strava_activity_id=object_id).first()
                if not activity:
                    return
                new_title = updates.get("title")
                if new_title is None:
                    return
                new_title = (new_title or "").strip()
                if new_title:
                    activity.name = new_title
                    db.session.commit()
            except Exception:
                db.session.rollback()
                raise

    t = threading.Thread(target=run)
    t.daemon = True
    t.start()
