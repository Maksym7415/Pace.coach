"""Recovery API routes."""
import logging
from datetime import date, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, Query

from src.core.responses import error_json, success_json
from src.modules.identity.deps import require_role
from src.modules.identity.models import User, UserRoleEnum
from src.modules.recovery.deps import get_recovery_service
from src.modules.recovery.schemas import RecoveryEntryCreateRequest
from src.modules.recovery.service import RecoveryService

logger = logging.getLogger("coach_app.recovery")
router = APIRouter(prefix="/api/recovery", tags=["recovery"])


@router.post("/entries")
def upsert_entry(
    body: RecoveryEntryCreateRequest,
    athlete: Annotated[User, Depends(require_role(UserRoleEnum.athlete))],
    service: RecoveryService = Depends(get_recovery_service),
):
    result, err, status = service.upsert_entry(athlete, body)
    if err:
        raise error_json(status, err)
    return success_json(result, status_code=status)


@router.get("/entries/today")
def get_today_entry(
    athlete: Annotated[User, Depends(require_role(UserRoleEnum.athlete))],
    service: RecoveryService = Depends(get_recovery_service),
):
    today = datetime.utcnow().date()
    result, err, status = service.get_today(athlete, today)
    if err:
        raise error_json(status, err)
    return success_json(result)


@router.get("/entries")
def list_entries(
    athlete: Annotated[User, Depends(require_role(UserRoleEnum.athlete))],
    start_date: date | None = Query(None),
    end_date: date | None = Query(None),
    service: RecoveryService = Depends(get_recovery_service),
):
    result, err, status = service.list_entries(athlete, start_date, end_date)
    if err:
        raise error_json(status, err)
    return success_json(result)


@router.get("/athletes/{athlete_id}/entries/today")
def coach_get_athlete_today_entry(
    athlete_id: int,
    coach: Annotated[User, Depends(require_role(UserRoleEnum.coach))],
    service: RecoveryService = Depends(get_recovery_service),
):
    today = datetime.utcnow().date()
    result, err, status = service.get_athlete_today_for_coach(coach, athlete_id, today)
    if err:
        raise error_json(status, err)
    return success_json(result)
