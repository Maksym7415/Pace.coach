"""Planning API routes."""
from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, Query

from src.core.responses import error_json, success_json
from src.modules.identity.deps import require_role
from src.modules.identity.models import User, UserRoleEnum
from src.modules.planning.deps import get_planning_service
from src.modules.planning.schemas import (
    AttachWorkoutRequest,
    CoachReviewCreateRequest,
    CoachReviewUpdateRequest,
    MesocycleCreateRequest,
    MesocycleUpdateRequest,
    MicrocycleCreateRequest,
    MicrocycleUpdateRequest,
    PlanItemCreateRequest,
    PlanItemUpdateRequest,
    ReorderRequest,
    TrainingPlanCreateRequest,
    TrainingPlanUpdateRequest,
)
from src.modules.planning.service import PlanningService
from src.modules.training.schemas import WorkoutCreateRequest

router = APIRouter(prefix="/api/planning", tags=["planning"])


def _ok(result, err, status, default=200):
    if err:
        raise error_json(status, err)
    return success_json(result, status_code=status if status in (200, 201) else default)


@router.post("/plans", status_code=201)
def create_plan(
    body: TrainingPlanCreateRequest,
    coach: Annotated[User, Depends(require_role(UserRoleEnum.coach))],
    service: PlanningService = Depends(get_planning_service),
):
    return _ok(*service.create_plan(coach, body))


@router.get("/athletes/{athlete_id}/plans")
def list_athlete_plans(
    athlete_id: int,
    coach: Annotated[User, Depends(require_role(UserRoleEnum.coach))],
    service: PlanningService = Depends(get_planning_service),
):
    return _ok(*service.list_plans_for_athlete(coach, athlete_id))


@router.get("/plans/{plan_id}")
def get_plan(
    plan_id: int,
    coach: Annotated[User, Depends(require_role(UserRoleEnum.coach))],
    depth: str = Query("items"),
    service: PlanningService = Depends(get_planning_service),
):
    return _ok(*service.get_plan(coach, plan_id, depth))


@router.put("/plans/{plan_id}")
def update_plan(
    plan_id: int,
    body: TrainingPlanUpdateRequest,
    coach: Annotated[User, Depends(require_role(UserRoleEnum.coach))],
    service: PlanningService = Depends(get_planning_service),
):
    return _ok(*service.update_plan(coach, plan_id, body))


@router.delete("/plans/{plan_id}")
def delete_plan(
    plan_id: int,
    coach: Annotated[User, Depends(require_role(UserRoleEnum.coach))],
    service: PlanningService = Depends(get_planning_service),
):
    return _ok(*service.delete_plan(coach, plan_id))


@router.get("/plans/{plan_id}/change-log")
def list_change_log(
    plan_id: int,
    coach: Annotated[User, Depends(require_role(UserRoleEnum.coach))],
    entity_type: str | None = Query(None),
    entity_id: int | None = Query(None),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    service: PlanningService = Depends(get_planning_service),
):
    return _ok(*service.list_change_log(coach, plan_id, entity_type, entity_id, limit, offset))


@router.post("/plans/{plan_id}/mesocycles", status_code=201)
def create_mesocycle(
    plan_id: int,
    body: MesocycleCreateRequest,
    coach: Annotated[User, Depends(require_role(UserRoleEnum.coach))],
    service: PlanningService = Depends(get_planning_service),
):
    return _ok(*service.create_mesocycle(coach, plan_id, body))


@router.put("/mesocycles/{mesocycle_id}")
def update_mesocycle(
    mesocycle_id: int,
    body: MesocycleUpdateRequest,
    coach: Annotated[User, Depends(require_role(UserRoleEnum.coach))],
    service: PlanningService = Depends(get_planning_service),
):
    return _ok(*service.update_mesocycle(coach, mesocycle_id, body))


@router.delete("/mesocycles/{mesocycle_id}")
def delete_mesocycle(
    mesocycle_id: int,
    coach: Annotated[User, Depends(require_role(UserRoleEnum.coach))],
    service: PlanningService = Depends(get_planning_service),
):
    return _ok(*service.delete_mesocycle(coach, mesocycle_id))


@router.post("/plans/{plan_id}/mesocycles/reorder")
def reorder_mesocycles(
    plan_id: int,
    body: ReorderRequest,
    coach: Annotated[User, Depends(require_role(UserRoleEnum.coach))],
    service: PlanningService = Depends(get_planning_service),
):
    return _ok(*service.reorder_mesocycles(coach, plan_id, body.ordered_ids, body.reason))


@router.post("/mesocycles/{mesocycle_id}/microcycles", status_code=201)
def create_microcycle(
    mesocycle_id: int,
    body: MicrocycleCreateRequest,
    coach: Annotated[User, Depends(require_role(UserRoleEnum.coach))],
    service: PlanningService = Depends(get_planning_service),
):
    return _ok(*service.create_microcycle(coach, mesocycle_id, body))


@router.put("/microcycles/{microcycle_id}")
def update_microcycle(
    microcycle_id: int,
    body: MicrocycleUpdateRequest,
    coach: Annotated[User, Depends(require_role(UserRoleEnum.coach))],
    service: PlanningService = Depends(get_planning_service),
):
    return _ok(*service.update_microcycle(coach, microcycle_id, body))


@router.delete("/microcycles/{microcycle_id}")
def delete_microcycle(
    microcycle_id: int,
    coach: Annotated[User, Depends(require_role(UserRoleEnum.coach))],
    service: PlanningService = Depends(get_planning_service),
):
    return _ok(*service.delete_microcycle(coach, microcycle_id))


@router.post("/mesocycles/{mesocycle_id}/microcycles/reorder")
def reorder_microcycles(
    mesocycle_id: int,
    body: ReorderRequest,
    coach: Annotated[User, Depends(require_role(UserRoleEnum.coach))],
    service: PlanningService = Depends(get_planning_service),
):
    return _ok(*service.reorder_microcycles(coach, mesocycle_id, body.ordered_ids, body.reason))


@router.post("/microcycles/{microcycle_id}/items", status_code=201)
def create_item(
    microcycle_id: int,
    body: PlanItemCreateRequest,
    coach: Annotated[User, Depends(require_role(UserRoleEnum.coach))],
    service: PlanningService = Depends(get_planning_service),
):
    return _ok(*service.create_item(coach, microcycle_id, body))


@router.put("/items/{item_id}")
def update_item(
    item_id: int,
    body: PlanItemUpdateRequest,
    coach: Annotated[User, Depends(require_role(UserRoleEnum.coach))],
    service: PlanningService = Depends(get_planning_service),
):
    return _ok(*service.update_item(coach, item_id, body))


@router.delete("/items/{item_id}")
def delete_item(
    item_id: int,
    coach: Annotated[User, Depends(require_role(UserRoleEnum.coach))],
    service: PlanningService = Depends(get_planning_service),
):
    return _ok(*service.delete_item(coach, item_id))


@router.post("/microcycles/{microcycle_id}/items/reorder")
def reorder_items(
    microcycle_id: int,
    body: ReorderRequest,
    coach: Annotated[User, Depends(require_role(UserRoleEnum.coach))],
    service: PlanningService = Depends(get_planning_service),
):
    return _ok(*service.reorder_items(coach, microcycle_id, body.ordered_ids, body.reason))


@router.post("/items/{item_id}/attach-workout")
def attach_workout(
    item_id: int,
    body: AttachWorkoutRequest,
    coach: Annotated[User, Depends(require_role(UserRoleEnum.coach))],
    service: PlanningService = Depends(get_planning_service),
):
    return _ok(*service.attach_workout(coach, item_id, body.workout_id, body.reason))


@router.delete("/items/{item_id}/attach-workout")
def detach_workout(
    item_id: int,
    coach: Annotated[User, Depends(require_role(UserRoleEnum.coach))],
    service: PlanningService = Depends(get_planning_service),
):
    return _ok(*service.detach_workout(coach, item_id))


@router.get("/items/{item_id}/builder-context")
def builder_context(
    item_id: int,
    coach: Annotated[User, Depends(require_role(UserRoleEnum.coach))],
    service: PlanningService = Depends(get_planning_service),
):
    return _ok(*service.get_builder_context(coach, item_id))


@router.post("/items/{item_id}/workout", status_code=201)
def create_workout_for_item(
    item_id: int,
    body: WorkoutCreateRequest,
    coach: Annotated[User, Depends(require_role(UserRoleEnum.coach))],
    service: PlanningService = Depends(get_planning_service),
):
    return _ok(*service.create_workout_for_item(coach, item_id, body))


@router.post("/mesocycles/{mesocycle_id}/system-analysis", status_code=201)
def generate_system_analysis(
    mesocycle_id: int,
    coach: Annotated[User, Depends(require_role(UserRoleEnum.coach))],
    service: PlanningService = Depends(get_planning_service),
):
    result, err, status = service.generate_system_analysis(coach, mesocycle_id)
    if err:
        raise error_json(status, err)
    return success_json(result, status_code=status)


@router.get("/mesocycles/{mesocycle_id}/system-analysis")
def get_system_analysis(
    mesocycle_id: int,
    coach: Annotated[User, Depends(require_role(UserRoleEnum.coach))],
    all: bool = Query(False),
    service: PlanningService = Depends(get_planning_service),
):
    return _ok(*service.get_system_analysis(coach, mesocycle_id, all_rows=all))


@router.post("/mesocycles/{mesocycle_id}/coach-review", status_code=201)
def create_coach_review(
    mesocycle_id: int,
    body: CoachReviewCreateRequest,
    coach: Annotated[User, Depends(require_role(UserRoleEnum.coach))],
    service: PlanningService = Depends(get_planning_service),
):
    return _ok(*service.create_coach_review(coach, mesocycle_id, body))


@router.put("/coach-reviews/{review_id}")
def update_coach_review(
    review_id: int,
    body: CoachReviewUpdateRequest,
    coach: Annotated[User, Depends(require_role(UserRoleEnum.coach))],
    service: PlanningService = Depends(get_planning_service),
):
    return _ok(*service.update_coach_review(coach, review_id, body))


@router.post("/coach-reviews/{review_id}/new-version", status_code=201)
def new_coach_review_version(
    review_id: int,
    coach: Annotated[User, Depends(require_role(UserRoleEnum.coach))],
    service: PlanningService = Depends(get_planning_service),
):
    return _ok(*service.new_coach_review_version(coach, review_id))


@router.post("/coach-reviews/{review_id}/approve")
def approve_coach_review(
    review_id: int,
    coach: Annotated[User, Depends(require_role(UserRoleEnum.coach))],
    service: PlanningService = Depends(get_planning_service),
):
    return _ok(*service.approve_coach_review(coach, review_id))


@router.get("/mesocycles/{mesocycle_id}/coach-review")
def get_coach_review(
    mesocycle_id: int,
    coach: Annotated[User, Depends(require_role(UserRoleEnum.coach))],
    history: bool = Query(False),
    service: PlanningService = Depends(get_planning_service),
):
    return _ok(*service.get_coach_review(coach, mesocycle_id, history=history))


@router.get("/my/plans")
def my_plans(
    athlete: Annotated[User, Depends(require_role(UserRoleEnum.athlete))],
    service: PlanningService = Depends(get_planning_service),
):
    return _ok(*service.list_my_plans(athlete))


@router.get("/my/plans/{plan_id}")
def my_plan(
    plan_id: int,
    athlete: Annotated[User, Depends(require_role(UserRoleEnum.athlete))],
    service: PlanningService = Depends(get_planning_service),
):
    return _ok(*service.get_my_plan(athlete, plan_id))


@router.get("/my/position")
def my_position(
    athlete: Annotated[User, Depends(require_role(UserRoleEnum.athlete))],
    service: PlanningService = Depends(get_planning_service),
):
    return _ok(*service.get_my_position(athlete))


@router.get("/context")
def planning_context(
    athlete_id: int,
    coach: Annotated[User, Depends(require_role(UserRoleEnum.coach))],
    start_date: date = Query(...),
    end_date: date = Query(...),
    service: PlanningService = Depends(get_planning_service),
):
    return _ok(*service.get_cycle_bands(coach, athlete_id, start_date, end_date))
