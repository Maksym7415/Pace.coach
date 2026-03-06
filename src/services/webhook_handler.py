"""
Strava webhook: verify subscription and handle activity create/update events.
"""
import threading
from datetime import datetime, timezone

import requests
from sqlalchemy import func

from src.models import db, UserStrava, Activity, ActivityShoeDistance, Shoe

STRAVA_API_BASE = "https://www.strava.com/api/v3"
RUNNING_TYPES = {"Run", "VirtualRun", "Treadmill", "TrailRun", "ObstacleRun"}


def _is_running(sport_type: str) -> bool:
    """Check if sport type indicates running."""
    if not sport_type:
        return False
    return sport_type in RUNNING_TYPES or sport_type.startswith("Run")


def process_activity_create(owner_id: int, object_id: int, app):
    """
    Background task: fetch activity from Strava, create in DB if running.
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
                # Avoid duplicate import
                if db.session.query(Activity).filter_by(strava_activity_id=object_id).first():
                    return
                if not _is_running(data.get("type") or data.get("sport_type", "")):
                    return
                distance_m = data.get("distance") or 0
                distance_km = round(distance_m / 1000.0, 2)
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
                    total_distance_km=distance_km,
                    source="strava",
                    strava_activity_id=object_id,
                )
                db.session.add(activity)
                db.session.flush()

                default_shoe = db.session.query(Shoe).filter_by(user_id=us.user_id, is_default=True).first()
                if default_shoe:
                    db.session.add(
                        ActivityShoeDistance(
                            activity_id=activity.id,
                            shoe_id=default_shoe.id,
                            distance_km=distance_km,
                        )
                    )
                    db.session.flush()
                    total = db.session.query(
                        func.coalesce(func.sum(ActivityShoeDistance.distance_km), 0)
                    ).filter_by(shoe_id=default_shoe.id).scalar()
                    default_shoe.distance_covered_km = round(float(total), 2)

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
