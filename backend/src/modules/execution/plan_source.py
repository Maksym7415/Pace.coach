"""PlanSource seam: authored workouts → ResolvedPlan (JSON today, relational later)."""
from __future__ import annotations

from abc import ABC, abstractmethod

from sqlalchemy.orm import Session

from src.modules.athlete_profile.models import Sport
from src.modules.execution.domain import ResolvedPlan
from src.modules.execution.plan_resolution import resolve_plan
from src.modules.training.models import Workout


class PlanSource(ABC):
    @abstractmethod
    def load(self, workout_id: int) -> ResolvedPlan:
        raise NotImplementedError


class JsonWorkoutPlanSource(PlanSource):
    """Reads workouts.steps JSON. Swap later for RelationalWorkoutPlanSource."""

    def __init__(self, db: Session):
        self.db = db

    def load(self, workout_id: int) -> ResolvedPlan:
        workout = self.db.get(Workout, workout_id)
        if workout is None:
            raise ValueError(f"Workout {workout_id} not found")

        sport_code = None
        if workout.sport_id is not None:
            sport = self.db.get(Sport, workout.sport_id)
            sport_code = sport.code if sport else None

        steps = workout.steps if isinstance(workout.steps, list) else None
        return resolve_plan(
            steps,
            workout_id=workout.id,
            sport_code=sport_code,
        )
