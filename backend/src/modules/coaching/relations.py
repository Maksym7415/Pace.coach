"""Shared coach-athlete relation checks."""
from sqlalchemy import select
from sqlalchemy.orm import Session

from src.modules.coaching.models import CoachAthleteRelation, RelationStatus

COACH_ATHLETE_NOT_LINKED_ERROR = "Athlete not found or not linked to you"
COACH_ATHLETE_NOT_LINKED_STATUS = 404


def get_active_coach_athlete_relation(
    db: Session, coach_id: int, athlete_id: int
) -> CoachAthleteRelation | None:
    return db.scalar(
        select(CoachAthleteRelation).where(
            CoachAthleteRelation.coach_id == coach_id,
            CoachAthleteRelation.athlete_id == athlete_id,
            CoachAthleteRelation.status == RelationStatus.active,
        )
    )


def coach_athlete_relation_error(
    db: Session, coach_id: int, athlete_id: int
) -> str | None:
    if get_active_coach_athlete_relation(db, coach_id, athlete_id):
        return None
    return COACH_ATHLETE_NOT_LINKED_ERROR
