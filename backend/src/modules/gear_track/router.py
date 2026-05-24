"""Gear and activities API routes."""
from typing import Any

from fastapi import APIRouter, Body, Depends, Query

from src.core.auth import CurrentUser
from src.core.responses import error_json, success_json
from src.modules.gear_track.deps import get_gear_track_service
from src.modules.gear_track.service import GearTrackService

router = APIRouter(tags=["gear"])


def _handle(result: dict | None, err: str | None, status: int):
    if err:
        raise error_json(status, err)
    if status != 200:
        return success_json(result, status_code=status)
    return success_json(result)


# --- Shoes (legacy) ---


@router.get("/api/shoes")
def list_shoes(user: CurrentUser, service: GearTrackService = Depends(get_gear_track_service)):
    return success_json(service.list_shoes(user.id))


@router.post("/api/shoes")
def create_shoe(
    user: CurrentUser,
    body: dict[str, Any] = Body(default_factory=dict),
    service: GearTrackService = Depends(get_gear_track_service),
):
    result, err, status = service.create_shoe(user.id, body)
    return _handle(result, err, status)


@router.get("/api/shoes/{shoe_id}")
def get_shoe(
    shoe_id: int,
    user: CurrentUser,
    service: GearTrackService = Depends(get_gear_track_service),
):
    result, err, status = service.get_shoe(user.id, shoe_id)
    return _handle(result, err, status)


@router.put("/api/shoes/{shoe_id}")
def update_shoe(
    shoe_id: int,
    user: CurrentUser,
    body: dict[str, Any] = Body(default_factory=dict),
    service: GearTrackService = Depends(get_gear_track_service),
):
    result, err, status = service.update_shoe(user.id, shoe_id, body)
    return _handle(result, err, status)


@router.delete("/api/shoes/{shoe_id}")
def delete_shoe(
    shoe_id: int,
    user: CurrentUser,
    service: GearTrackService = Depends(get_gear_track_service),
):
    result, err, status = service.delete_shoe(user.id, shoe_id)
    return _handle(result, err, status)


@router.put("/api/shoes/{shoe_id}/default")
def set_default_shoe(
    shoe_id: int,
    user: CurrentUser,
    service: GearTrackService = Depends(get_gear_track_service),
):
    result, err, status = service.set_default_shoe(user.id, shoe_id)
    return _handle(result, err, status)


# --- Activities ---


@router.get("/api/activities")
def list_activities(user: CurrentUser, service: GearTrackService = Depends(get_gear_track_service)):
    return success_json(service.list_activities(user.id))


@router.post("/api/activities")
def create_activity(
    user: CurrentUser,
    body: dict[str, Any] = Body(default_factory=dict),
    service: GearTrackService = Depends(get_gear_track_service),
):
    result, err, status = service.create_activity(user.id, body)
    return _handle(result, err, status)


@router.get("/api/activities/{activity_id}")
def get_activity(
    activity_id: int,
    user: CurrentUser,
    service: GearTrackService = Depends(get_gear_track_service),
):
    result, err, status = service.get_activity(user.id, activity_id)
    return _handle(result, err, status)


@router.put("/api/activities/{activity_id}")
def update_activity(
    activity_id: int,
    user: CurrentUser,
    body: dict[str, Any] = Body(default_factory=dict),
    service: GearTrackService = Depends(get_gear_track_service),
):
    result, err, status = service.update_activity(user.id, activity_id, body)
    return _handle(result, err, status)


@router.delete("/api/activities/{activity_id}")
def delete_activity(
    activity_id: int,
    user: CurrentUser,
    service: GearTrackService = Depends(get_gear_track_service),
):
    result, err, status = service.delete_activity(user.id, activity_id)
    return _handle(result, err, status)


@router.put("/api/activities/{activity_id}/shoes")
def update_activity_shoes(
    activity_id: int,
    user: CurrentUser,
    body: list[Any] = Body(...),
    service: GearTrackService = Depends(get_gear_track_service),
):
    result, err, status = service.update_activity_shoes(user.id, activity_id, body)
    return _handle(result, err, status)


@router.put("/api/activities/{activity_id}/gear")
def update_activity_gear(
    activity_id: int,
    user: CurrentUser,
    body: list[Any] = Body(...),
    service: GearTrackService = Depends(get_gear_track_service),
):
    result, err, status = service.update_activity_gear(user.id, activity_id, body)
    return _handle(result, err, status)


# --- Gear ---


@router.get("/api/gear")
def list_gear(
    user: CurrentUser,
    activity_type: str | None = Query(None),
    gear_type: str | None = Query(None),
    service: GearTrackService = Depends(get_gear_track_service),
):
    return success_json(service.list_gear(user.id, activity_type=activity_type, gear_type=gear_type))


@router.post("/api/gear")
def create_gear(
    user: CurrentUser,
    body: dict[str, Any] = Body(default_factory=dict),
    service: GearTrackService = Depends(get_gear_track_service),
):
    result, err, status = service.create_gear(user.id, body)
    return _handle(result, err, status)


@router.get("/api/gear/{gear_id}")
def get_gear(
    gear_id: int,
    user: CurrentUser,
    service: GearTrackService = Depends(get_gear_track_service),
):
    result, err, status = service.get_gear(user.id, gear_id)
    return _handle(result, err, status)


@router.put("/api/gear/{gear_id}")
def update_gear(
    gear_id: int,
    user: CurrentUser,
    body: dict[str, Any] = Body(default_factory=dict),
    service: GearTrackService = Depends(get_gear_track_service),
):
    result, err, status = service.update_gear(user.id, gear_id, body)
    return _handle(result, err, status)


@router.delete("/api/gear/{gear_id}")
def delete_gear(
    gear_id: int,
    user: CurrentUser,
    service: GearTrackService = Depends(get_gear_track_service),
):
    result, err, status = service.delete_gear(user.id, gear_id)
    return _handle(result, err, status)


@router.put("/api/gear/{gear_id}/default")
def set_default_gear(
    gear_id: int,
    user: CurrentUser,
    service: GearTrackService = Depends(get_gear_track_service),
):
    result, err, status = service.set_default_gear(user.id, gear_id)
    return _handle(result, err, status)


@router.delete("/api/gear/{gear_id}/default")
def unset_default_gear(
    gear_id: int,
    user: CurrentUser,
    service: GearTrackService = Depends(get_gear_track_service),
):
    result, err, status = service.unset_default_gear(user.id, gear_id)
    return _handle(result, err, status)


@router.get("/api/gear/{gear_id}/components")
def get_gear_components(
    gear_id: int,
    user: CurrentUser,
    service: GearTrackService = Depends(get_gear_track_service),
):
    result, err, status = service.get_gear_components(user.id, gear_id)
    return _handle(result, err, status)


@router.post("/api/gear/{gear_id}/installations")
def create_gear_installation(
    gear_id: int,
    user: CurrentUser,
    body: dict[str, Any] = Body(default_factory=dict),
    service: GearTrackService = Depends(get_gear_track_service),
):
    result, err, status = service.create_gear_installation(user.id, gear_id, body)
    return _handle(result, err, status)


@router.delete("/api/gear/{gear_id}/installations/{installation_id}")
def remove_gear_installation(
    gear_id: int,
    installation_id: int,
    user: CurrentUser,
    service: GearTrackService = Depends(get_gear_track_service),
):
    result, err, status = service.remove_gear_installation(user.id, gear_id, installation_id)
    return _handle(result, err, status)


@router.get("/api/gear/{gear_id}/services")
def list_gear_services(
    gear_id: int,
    user: CurrentUser,
    service: GearTrackService = Depends(get_gear_track_service),
):
    result, err, status = service.list_gear_services(user.id, gear_id)
    return _handle(result, err, status)


@router.post("/api/gear/{gear_id}/services")
def create_gear_service(
    gear_id: int,
    user: CurrentUser,
    body: dict[str, Any] = Body(default_factory=dict),
    service: GearTrackService = Depends(get_gear_track_service),
):
    result, err, status = service.create_gear_service(user.id, gear_id, body)
    return _handle(result, err, status)


@router.put("/api/gear/{gear_id}/services/{service_id}")
def update_gear_service(
    gear_id: int,
    service_id: int,
    user: CurrentUser,
    body: dict[str, Any] = Body(default_factory=dict),
    service: GearTrackService = Depends(get_gear_track_service),
):
    result, err, status = service.update_gear_service(user.id, gear_id, service_id, body)
    return _handle(result, err, status)


@router.delete("/api/gear/{gear_id}/services/{service_id}")
def delete_gear_service(
    gear_id: int,
    service_id: int,
    user: CurrentUser,
    service: GearTrackService = Depends(get_gear_track_service),
):
    result, err, status = service.delete_gear_service(user.id, gear_id, service_id)
    return _handle(result, err, status)


@router.post("/api/gear/{gear_id}/services/{service_id}/logs")
def log_gear_service(
    gear_id: int,
    service_id: int,
    user: CurrentUser,
    service: GearTrackService = Depends(get_gear_track_service),
):
    result, err, status = service.log_gear_service(user.id, gear_id, service_id)
    return _handle(result, err, status)


@router.put("/api/gear/{gear_id}/retire")
def retire_gear(
    gear_id: int,
    user: CurrentUser,
    service: GearTrackService = Depends(get_gear_track_service),
):
    result, err, status = service.retire_gear(user.id, gear_id)
    return _handle(result, err, status)


@router.get("/api/gear/alerts")
def list_gear_alerts(user: CurrentUser, service: GearTrackService = Depends(get_gear_track_service)):
    return success_json(service.list_gear_alerts(user.id))
