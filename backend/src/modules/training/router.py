"""Training API routes."""
import logging
from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, Query

from src.core.responses import error_json, success_json
from src.modules.identity.deps import require_role
from src.modules.identity.models import User, UserRoleEnum
from src.modules.training.deps import get_training_service
from src.modules.training.schemas import WorkoutCompleteRequest, WorkoutCreateRequest
from src.modules.training.service import TrainingService

logger = logging.getLogger("coach_app.training")
router = APIRouter(prefix="/api/training", tags=["training"])


@router.post("/workouts", status_code=201)
def create_workout(
    body: WorkoutCreateRequest,
    coach: Annotated[User, Depends(require_role(UserRoleEnum.coach))],
    service: TrainingService = Depends(get_training_service),
):
    result, err, status = service.create_workout(coach, body)
    if err:
        raise error_json(status, err)
    return success_json(result, status_code=status)


@router.get("/calendar")
def get_calendar(
    athlete: Annotated[User, Depends(require_role(UserRoleEnum.athlete))],
    start_date: date = Query(...),
    end_date: date = Query(...),
    service: TrainingService = Depends(get_training_service),
):
    result, err, status = service.get_calendar(athlete, start_date, end_date)
    if err:
        raise error_json(status, err)
    return success_json(result)


@router.get("/workouts/{workout_id}")
def get_workout(
    workout_id: int,
    athlete: Annotated[User, Depends(require_role(UserRoleEnum.athlete))],
    service: TrainingService = Depends(get_training_service),
):
    result, err, status = service.get_workout(athlete, workout_id)
    if err:
        raise error_json(status, err)
    return success_json(result)


@router.put("/workouts/{workout_id}/complete")
def mark_completed(
    workout_id: int,
    body: WorkoutCompleteRequest,
    athlete: Annotated[User, Depends(require_role(UserRoleEnum.athlete))],
    service: TrainingService = Depends(get_training_service),
):
    result, err, status = service.mark_completed(athlete, workout_id, body.notes)
    if err:
        raise error_json(status, err)
    return success_json(result)


@router.put("/workouts/{workout_id}/skip")
def mark_skipped(
    workout_id: int,
    athlete: Annotated[User, Depends(require_role(UserRoleEnum.athlete))],
    service: TrainingService = Depends(get_training_service),
):
    result, err, status = service.mark_skipped(athlete, workout_id)
    if err:
        raise error_json(status, err)
    return success_json(result)
