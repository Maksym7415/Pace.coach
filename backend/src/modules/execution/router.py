"""WorkoutExecution read/write API routes."""
from fastapi import APIRouter, Depends

from src.core.auth import CurrentUser
from src.core.responses import error_json, success_json
from src.modules.execution.deps import get_workout_execution_service
from src.modules.execution.schemas import SaveAthleteResponsesIn
from src.modules.execution.service import WorkoutExecutionService

router = APIRouter(tags=["execution"])


@router.get("/api/activities/{activity_id}/workout-execution")
def get_workout_execution(
    activity_id: int,
    user: CurrentUser,
    service: WorkoutExecutionService = Depends(get_workout_execution_service),
):
    result, err, status = service.get_for_activity(user.id, activity_id)
    if err:
        raise error_json(status, err)
    return success_json(result)


@router.post("/api/activities/{activity_id}/workout-execution/rematch")
def rematch_workout_execution(
    activity_id: int,
    user: CurrentUser,
    service: WorkoutExecutionService = Depends(get_workout_execution_service),
):
    result, err, status = service.rematch_for_activity(user.id, activity_id)
    if err:
        raise error_json(status, err)
    return success_json(result)


@router.post("/api/activities/{activity_id}/workout-execution/athlete-responses")
def save_athlete_responses(
    activity_id: int,
    body: SaveAthleteResponsesIn,
    user: CurrentUser,
    service: WorkoutExecutionService = Depends(get_workout_execution_service),
):
    result, err, status = service.save_athlete_responses(user.id, activity_id, body)
    if err:
        raise error_json(status, err)
    return success_json(result)
