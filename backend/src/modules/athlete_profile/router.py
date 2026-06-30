"""Athlete profile API routes."""
import logging
from typing import Annotated

from fastapi import APIRouter, Depends, Query

from src.core.auth import CurrentUser
from src.core.responses import error_json, success_json
from src.modules.athlete_profile.deps import get_athlete_profile_service
from src.modules.athlete_profile.schemas import (
    AddSportRequest,
    BaselineUpsertRequest,
    BodyMetricCreateRequest,
    SportProfileUpsertRequest,
    ZoneCreateRequest,
)
from src.modules.athlete_profile.service import AthleteProfileService
from src.modules.coaching.deps import require_coach_athlete_access
from src.modules.coaching.models import CoachAthleteRelation
from src.modules.identity.deps import require_role
from src.modules.identity.models import User, UserRoleEnum

logger = logging.getLogger("coach_app.athlete_profile")
router = APIRouter(prefix="/api/athlete-profile", tags=["athlete-profile"])


@router.get("/sports")
def list_sports(
    _user: CurrentUser,
    service: AthleteProfileService = Depends(get_athlete_profile_service),
):
    return success_json(service.list_sports())


@router.get("/my/sports")
def my_sports(
    athlete: Annotated[User, Depends(require_role(UserRoleEnum.athlete))],
    service: AthleteProfileService = Depends(get_athlete_profile_service),
):
    return success_json(service.get_athlete_sports(athlete.id))


@router.post("/my/sports", status_code=201)
def add_my_sport(
    body: AddSportRequest,
    athlete: Annotated[User, Depends(require_role(UserRoleEnum.athlete))],
    service: AthleteProfileService = Depends(get_athlete_profile_service),
):
    result, err, status = service.add_athlete_sport(
        athlete.id, body.sport_id, body.is_primary
    )
    if err:
        raise error_json(status, err)
    return success_json(result, status_code=status)


@router.delete("/my/sports/{sport_id}")
def remove_my_sport(
    sport_id: int,
    athlete: Annotated[User, Depends(require_role(UserRoleEnum.athlete))],
    service: AthleteProfileService = Depends(get_athlete_profile_service),
):
    result, err, status = service.remove_athlete_sport(athlete.id, sport_id)
    if err:
        raise error_json(status, err)
    return success_json(result)


@router.put("/my/sports/{sport_id}/primary")
def set_my_primary_sport(
    sport_id: int,
    athlete: Annotated[User, Depends(require_role(UserRoleEnum.athlete))],
    service: AthleteProfileService = Depends(get_athlete_profile_service),
):
    result, err, status = service.set_primary_sport(athlete.id, sport_id)
    if err:
        raise error_json(status, err)
    return success_json(result)


@router.get("/my/baselines")
def get_my_baselines(
    athlete: Annotated[User, Depends(require_role(UserRoleEnum.athlete))],
    service: AthleteProfileService = Depends(get_athlete_profile_service),
):
    result, err, status = service.get_baseline(athlete.id)
    if err:
        raise error_json(status, err)
    return success_json(result)


@router.put("/my/baselines")
def upsert_my_baselines(
    body: BaselineUpsertRequest,
    athlete: Annotated[User, Depends(require_role(UserRoleEnum.athlete))],
    service: AthleteProfileService = Depends(get_athlete_profile_service),
):
    result, err, status = service.upsert_baseline(athlete.id, body)
    if err:
        raise error_json(status, err)
    return success_json(result, status_code=status)


@router.post("/my/body-metrics", status_code=201)
def add_my_body_metric(
    body: BodyMetricCreateRequest,
    athlete: Annotated[User, Depends(require_role(UserRoleEnum.athlete))],
    service: AthleteProfileService = Depends(get_athlete_profile_service),
):
    result, err, status = service.add_body_metric(athlete.id, body)
    if err:
        raise error_json(status, err)
    return success_json(result, status_code=status)


@router.get("/my/body-metrics")
def list_my_body_metrics(
    athlete: Annotated[User, Depends(require_role(UserRoleEnum.athlete))],
    limit: int = Query(20, ge=1, le=100),
    service: AthleteProfileService = Depends(get_athlete_profile_service),
):
    result, err, status = service.list_body_metrics(athlete.id, limit)
    if err:
        raise error_json(status, err)
    return success_json(result)


@router.get("/my/sport-profiles/{sport_id}")
def get_my_sport_profile(
    sport_id: int,
    athlete: Annotated[User, Depends(require_role(UserRoleEnum.athlete))],
    service: AthleteProfileService = Depends(get_athlete_profile_service),
):
    result, err, status = service.get_sport_profile(athlete.id, sport_id)
    if err:
        raise error_json(status, err)
    return success_json(result)


@router.put("/my/sport-profiles/{sport_id}")
def upsert_my_sport_profile(
    sport_id: int,
    body: SportProfileUpsertRequest,
    athlete: Annotated[User, Depends(require_role(UserRoleEnum.athlete))],
    service: AthleteProfileService = Depends(get_athlete_profile_service),
):
    result, err, status = service.upsert_sport_profile(athlete.id, sport_id, body)
    if err:
        raise error_json(status, err)
    return success_json(result)


@router.get("/my/sport-profiles/{sport_id}/zones")
def list_my_zones(
    sport_id: int,
    athlete: Annotated[User, Depends(require_role(UserRoleEnum.athlete))],
    service: AthleteProfileService = Depends(get_athlete_profile_service),
):
    result, err, status = service.list_zones(athlete.id, sport_id)
    if err:
        raise error_json(status, err)
    return success_json(result)


@router.post("/my/sport-profiles/{sport_id}/zones", status_code=201)
def create_my_zone(
    sport_id: int,
    body: ZoneCreateRequest,
    athlete: Annotated[User, Depends(require_role(UserRoleEnum.athlete))],
    service: AthleteProfileService = Depends(get_athlete_profile_service),
):
    result, err, status = service.create_zone(athlete.id, sport_id, body)
    if err:
        raise error_json(status, err)
    return success_json(result, status_code=status)


@router.delete("/my/zones/{zone_id}")
def delete_my_zone(
    zone_id: int,
    athlete: Annotated[User, Depends(require_role(UserRoleEnum.athlete))],
    service: AthleteProfileService = Depends(get_athlete_profile_service),
):
    result, err, status = service.delete_zone(athlete.id, zone_id)
    if err:
        raise error_json(status, err)
    return success_json(result)


@router.get("/athletes/{athlete_id}/sports")
def coach_list_athlete_sports(
    athlete_id: int,
    _relation: Annotated[CoachAthleteRelation, Depends(require_coach_athlete_access)],
    service: AthleteProfileService = Depends(get_athlete_profile_service),
):
    return success_json(service.get_athlete_sports(athlete_id))


@router.get("/athletes/{athlete_id}/baselines")
def coach_get_baselines(
    athlete_id: int,
    _relation: Annotated[CoachAthleteRelation, Depends(require_coach_athlete_access)],
    service: AthleteProfileService = Depends(get_athlete_profile_service),
):
    result, err, status = service.get_baseline(athlete_id)
    if err:
        raise error_json(status, err)
    return success_json(result)


@router.get("/athletes/{athlete_id}/sport-profiles/{sport_id}")
def coach_get_sport_profile(
    athlete_id: int,
    sport_id: int,
    _relation: Annotated[CoachAthleteRelation, Depends(require_coach_athlete_access)],
    service: AthleteProfileService = Depends(get_athlete_profile_service),
):
    result, err, status = service.get_sport_profile(athlete_id, sport_id)
    if err:
        raise error_json(status, err)
    return success_json(result)


@router.get("/athletes/{athlete_id}/sport-profiles/{sport_id}/zones")
def coach_list_zones(
    athlete_id: int,
    sport_id: int,
    _relation: Annotated[CoachAthleteRelation, Depends(require_coach_athlete_access)],
    service: AthleteProfileService = Depends(get_athlete_profile_service),
):
    result, err, status = service.list_zones(athlete_id, sport_id)
    if err:
        raise error_json(status, err)
    return success_json(result)
