"""Link imported activities to scheduled workouts on the same day."""
from __future__ import annotations

import logging
from datetime import date, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from src.modules.training.models import Workout, WorkoutStatus, WorkoutType

logger = logging.getLogger("coach_app.training.activity_link")

RUN_WORKOUT_TYPES = {
    WorkoutType.easy,
    WorkoutType.recovery,
    WorkoutType.long_run,
    WorkoutType.threshold,
    WorkoutType.intervals,
    WorkoutType.hills,
    WorkoutType.race_pace,
}


def select_workout_for_activity(
    candidates: list[Workout],
    sport_code: str,
    sport_id: int | None = None,
) -> Workout | None:
    """Pick a single workout to link, or None if ambiguous.

    Never guesses when more than one eligible workout remains. Filtering by
    sport_id (when both sides have one) is disambiguation, not ranking.
    """
    if not candidates:
        return None

    if sport_code == "running":
        eligible = [w for w in candidates if w.workout_type in RUN_WORKOUT_TYPES]
    else:
        eligible = [w for w in candidates if w.workout_type != WorkoutType.rest]

    if sport_id is not None:
        eligible = [
            w
            for w in eligible
            if getattr(w, "sport_id", None) is None or w.sport_id == sport_id
        ]

    if len(eligible) == 1:
        return eligible[0]
    return None


def try_link_activity_to_workout(
    db: Session,
    athlete_id: int,
    activity_id: int,
    activity_date: date,
    sport_code: str,
    sport_id: int | None = None,
) -> Workout | None:
    """
    Auto-complete a scheduled workout when a matching activity is imported.
    Links only when there is a single unambiguous candidate on the same day.
    """
    candidates = db.scalars(
        select(Workout)
        .where(
            Workout.athlete_id == athlete_id,
            Workout.scheduled_date == activity_date,
            Workout.status == WorkoutStatus.scheduled,
            Workout.activity_id.is_(None),
        )
        .order_by(Workout.slot_ordinal.asc(), Workout.id.asc())
    ).all()

    if not candidates:
        return None

    workout = select_workout_for_activity(list(candidates), sport_code, sport_id=sport_id)
    if not workout:
        return None

    workout.activity_id = activity_id
    workout.status = WorkoutStatus.completed
    workout.completed_at = datetime.utcnow()
    logger.info(
        "Linked activity %s to workout %s for athlete %s",
        activity_id,
        workout.id,
        athlete_id,
    )
    return workout
