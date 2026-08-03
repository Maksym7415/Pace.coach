"""Training API routes."""
import logging
from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from src.core.auth import get_current_user
from src.core.database import get_db
from src.core.responses import error_json, success_json
from src.modules.identity.deps import require_role
from src.modules.identity.models import User, UserRole, UserRoleEnum
from src.modules.training.deps import get_training_service
from src.modules.training.schemas import (
    WorkoutAssignRequest,
    WorkoutCompleteRequest,
    WorkoutCreateRequest,
    WorkoutTemplateWriteRequest,
    WorkoutUpdateRequest,
)
from src.modules.training.service import TrainingService

logger = logging.getLogger("coach_app.training")
router = APIRouter(prefix="/api/training", tags=["training"])


def _user_is_coach(user: User, db: Session) -> bool:
    return bool(
        db.scalar(
            select(UserRole).where(
                UserRole.user_id == user.id,
                UserRole.role == UserRoleEnum.coach,
            )
        )
    )


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


@router.post("/workouts/assign", status_code=201)
def assign_workouts(
    body: WorkoutAssignRequest,
    coach: Annotated[User, Depends(require_role(UserRoleEnum.coach))],
    service: TrainingService = Depends(get_training_service),
):
    result, err, status = service.assign_workouts(coach, body)
    if err:
        raise error_json(status, err)
    return success_json(result, status_code=status)


@router.put("/workouts/{workout_id}")
def update_workout(
    workout_id: int,
    body: WorkoutUpdateRequest,
    coach: Annotated[User, Depends(require_role(UserRoleEnum.coach))],
    service: TrainingService = Depends(get_training_service),
):
    result, err, status = service.update_workout(coach, workout_id, body)
    if err:
        raise error_json(status, err)
    return success_json(result)


@router.delete("/workouts/{workout_id}")
def delete_workout(
    workout_id: int,
    coach: Annotated[User, Depends(require_role(UserRoleEnum.coach))],
    service: TrainingService = Depends(get_training_service),
):
    result, err, status = service.delete_workout(coach, workout_id)
    if err:
        raise error_json(status, err)
    return success_json(result)


@router.get("/templates")
def list_templates(
    coach: Annotated[User, Depends(require_role(UserRoleEnum.coach))],
    service: TrainingService = Depends(get_training_service),
):
    return success_json(service.list_templates(coach))


@router.post("/templates", status_code=201)
def create_template(
    body: WorkoutTemplateWriteRequest,
    coach: Annotated[User, Depends(require_role(UserRoleEnum.coach))],
    service: TrainingService = Depends(get_training_service),
):
    result, err, status = service.create_template(coach, body)
    if err:
        raise error_json(status, err)
    return success_json(result, status_code=status)


@router.get("/templates/{template_id}")
def get_template(
    template_id: int,
    coach: Annotated[User, Depends(require_role(UserRoleEnum.coach))],
    service: TrainingService = Depends(get_training_service),
):
    result, err, status = service.get_template(coach, template_id)
    if err:
        raise error_json(status, err)
    return success_json(result)


@router.put("/templates/{template_id}")
def update_template(
    template_id: int,
    body: WorkoutTemplateWriteRequest,
    coach: Annotated[User, Depends(require_role(UserRoleEnum.coach))],
    service: TrainingService = Depends(get_training_service),
):
    result, err, status = service.update_template(coach, template_id, body)
    if err:
        raise error_json(status, err)
    return success_json(result)


@router.delete("/templates/{template_id}")
def delete_template(
    template_id: int,
    coach: Annotated[User, Depends(require_role(UserRoleEnum.coach))],
    service: TrainingService = Depends(get_training_service),
):
    result, err, status = service.delete_template(coach, template_id)
    if err:
        raise error_json(status, err)
    return success_json(result)


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


@router.get("/athletes/{athlete_id}/calendar")
def get_athlete_calendar_for_coach(
    athlete_id: int,
    coach: Annotated[User, Depends(require_role(UserRoleEnum.coach))],
    start_date: date = Query(...),
    end_date: date = Query(...),
    service: TrainingService = Depends(get_training_service),
):
    result, err, status = service.get_calendar_for_coach(
        coach, athlete_id, start_date, end_date
    )
    if err:
        raise error_json(status, err)
    return success_json(result)


@router.get("/workouts/{workout_id}")
def get_workout(
    workout_id: int,
    user: Annotated[User, Depends(get_current_user)],
    db: Session = Depends(get_db),
    service: TrainingService = Depends(get_training_service),
):
    is_coach = _user_is_coach(user, db)
    is_athlete = bool(
        db.scalar(
            select(UserRole).where(
                UserRole.user_id == user.id,
                UserRole.role == UserRoleEnum.athlete,
            )
        )
    )
    if not is_coach and not is_athlete:
        raise error_json(403, "Requires role: athlete or coach")

    result, err, status = service.get_workout_for_user(
        user, workout_id, is_coach=is_coach, is_athlete=is_athlete
    )
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
