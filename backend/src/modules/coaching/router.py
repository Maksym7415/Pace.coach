"""Coaching API routes."""
import logging
from typing import Annotated

from fastapi import APIRouter, Depends, Query

from src.core.auth import CurrentUser
from src.core.responses import error_json, success_json
from src.modules.coaching.deps import get_coaching_service
from src.modules.coaching.schemas import InviteAthleteRequest
from src.modules.coaching.service import CoachingService
from src.modules.identity.deps import require_role
from src.modules.identity.models import User, UserRoleEnum

logger = logging.getLogger("coach_app.coaching")
router = APIRouter(prefix="/api/coaching", tags=["coaching"])


@router.post("/invitations", status_code=201)
def invite_athlete(
    body: InviteAthleteRequest,
    coach: Annotated[User, Depends(require_role(UserRoleEnum.coach))],
    service: CoachingService = Depends(get_coaching_service),
):
    result, err, status = service.invite_athlete(coach, body.athlete_id)
    if err:
        raise error_json(status, err)
    return success_json(result, status_code=status)


@router.get("/invitations/pending")
def pending_invitations(
    user: CurrentUser,
    service: CoachingService = Depends(get_coaching_service),
):
    return success_json(service.list_pending_invitations(user))


@router.put("/invitations/{relation_id}/accept")
def accept_invitation(
    relation_id: int,
    athlete: Annotated[User, Depends(require_role(UserRoleEnum.athlete))],
    service: CoachingService = Depends(get_coaching_service),
):
    result, err, status = service.accept_invitation(athlete, relation_id)
    if err:
        raise error_json(status, err)
    return success_json(result)


@router.put("/invitations/{relation_id}/reject")
def reject_invitation(
    relation_id: int,
    athlete: Annotated[User, Depends(require_role(UserRoleEnum.athlete))],
    service: CoachingService = Depends(get_coaching_service),
):
    result, err, status = service.reject_invitation(athlete, relation_id)
    if err:
        raise error_json(status, err)
    return success_json(result)


@router.get("/athletes")
def my_athletes(
    coach: Annotated[User, Depends(require_role(UserRoleEnum.coach))],
    service: CoachingService = Depends(get_coaching_service),
):
    return success_json(service.list_my_athletes(coach))


@router.get("/coaches")
def my_coaches(
    athlete: Annotated[User, Depends(require_role(UserRoleEnum.athlete))],
    service: CoachingService = Depends(get_coaching_service),
):
    return success_json(service.list_my_coaches(athlete))


@router.delete("/relations/{relation_id}")
def revoke_relation(
    relation_id: int,
    user: CurrentUser,
    service: CoachingService = Depends(get_coaching_service),
):
    result, err, status = service.revoke_relation(user, relation_id)
    if err:
        raise error_json(status, err)
    return success_json(result)


@router.get("/users/search")
def search_users(
    _user: CurrentUser,
    q: str = Query(..., min_length=2, description="Name or username substring, min 2 chars"),
    role: UserRoleEnum | None = Query(None, description="Filter by role: athlete or coach"),
    limit: int = Query(20, ge=1, le=50),
    service: CoachingService = Depends(get_coaching_service),
):
    return success_json(service.search_users(q, role, limit))
