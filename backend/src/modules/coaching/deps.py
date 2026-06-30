"""FastAPI dependencies for coaching module."""
from typing import Annotated

from fastapi import Depends
from sqlalchemy.orm import Session

from src.core.database import get_db
from src.core.responses import error_json
from src.modules.coaching.models import CoachAthleteRelation
from src.modules.coaching.relations import (
    COACH_ATHLETE_NOT_LINKED_ERROR,
    COACH_ATHLETE_NOT_LINKED_STATUS,
    get_active_coach_athlete_relation,
)
from src.modules.coaching.service import CoachingService
from src.modules.identity.deps import require_role
from src.modules.identity.models import User, UserRoleEnum


def get_coaching_service(db: Session = Depends(get_db)) -> CoachingService:
    return CoachingService(db)


def require_coach_athlete_access(
    athlete_id: int,
    coach: Annotated[User, Depends(require_role(UserRoleEnum.coach))],
    db: Session = Depends(get_db),
) -> CoachAthleteRelation:
    rel = get_active_coach_athlete_relation(db, coach.id, athlete_id)
    if not rel:
        raise error_json(COACH_ATHLETE_NOT_LINKED_STATUS, COACH_ATHLETE_NOT_LINKED_ERROR)
    return rel
