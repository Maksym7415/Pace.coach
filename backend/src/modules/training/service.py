"""Training business logic."""
from __future__ import annotations

import logging
from datetime import date, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from src.modules.coaching.models import CoachAthleteRelation, RelationStatus
from src.modules.identity.models import User, UserRole, UserRoleEnum
from src.modules.training.models import Workout, WorkoutStatus
from src.modules.training.schemas import WorkoutCreateRequest

logger = logging.getLogger("coach_app.training")


class TrainingService:
    def __init__(self, db: Session):
        self.db = db

    def _workout_to_dict(self, workout: Workout) -> dict:
        return {
            "id": workout.id,
            "athlete_id": workout.athlete_id,
            "created_by_id": workout.created_by_id,
            "scheduled_date": workout.scheduled_date.isoformat(),
            "workout_type": workout.workout_type.value,
            "title": workout.title,
            "description": workout.description,
            "steps": workout.steps,
            "duration_min": workout.duration_min,
            "distance_m": workout.distance_m,
            "status": workout.status.value,
            "completed_at": workout.completed_at.isoformat() if workout.completed_at else None,
            "notes": workout.notes,
            "created_at": workout.created_at.isoformat() if workout.created_at else None,
            "updated_at": workout.updated_at.isoformat() if workout.updated_at else None,
        }

    def create_workout(
        self,
        coach: User,
        data: WorkoutCreateRequest,
    ) -> tuple[dict | None, str | None, int]:
        athlete = self.db.get(User, data.athlete_id)
        if not athlete:
            return None, "Athlete not found", 404
        has_athlete_role = self.db.scalar(
            select(UserRole).where(
                UserRole.user_id == data.athlete_id,
                UserRole.role == UserRoleEnum.athlete,
            )
        )
        if not has_athlete_role:
            return None, "Athlete not found", 404
        relation = self.db.scalar(
            select(CoachAthleteRelation).where(
                CoachAthleteRelation.coach_id == coach.id,
                CoachAthleteRelation.athlete_id == data.athlete_id,
                CoachAthleteRelation.status == RelationStatus.active,
            )
        )
        if not relation:
            return None, "You do not have an active coaching relationship with this athlete", 403

        workout = Workout(
            athlete_id=data.athlete_id,
            created_by_id=coach.id,
            scheduled_date=data.scheduled_date,
            workout_type=data.workout_type,
            title=data.title,
            description=data.description,
            steps=data.steps,
            duration_min=data.duration_min,
            distance_m=data.distance_m,
            status=WorkoutStatus.scheduled,
        )
        self.db.add(workout)
        self.db.commit()
        self.db.refresh(workout)
        logger.info(
            "Coach %s created workout %s for athlete %s",
            coach.id,
            workout.id,
            data.athlete_id,
        )
        return {"workout": self._workout_to_dict(workout)}, None, 201

    def get_calendar(
        self,
        athlete: User,
        start_date: date,
        end_date: date,
    ) -> tuple[dict | None, str | None, int]:
        if start_date > end_date:
            return None, "start_date must be before or equal to end_date", 400
        if (end_date - start_date).days > 365:
            return None, "Date range cannot exceed 365 days", 400

        workouts = self.db.scalars(
            select(Workout)
            .where(
                Workout.athlete_id == athlete.id,
                Workout.scheduled_date >= start_date,
                Workout.scheduled_date <= end_date,
            )
            .order_by(Workout.scheduled_date.asc())
        ).all()
        result = [self._workout_to_dict(w) for w in workouts]
        return {"workouts": result, "count": len(result)}, None, 200

    def get_workout(
        self, athlete: User, workout_id: int
    ) -> tuple[dict | None, str | None, int]:
        workout = self.db.get(Workout, workout_id)
        if not workout or workout.athlete_id != athlete.id:
            return None, "Workout not found", 404
        return {"workout": self._workout_to_dict(workout)}, None, 200

    def mark_completed(
        self,
        athlete: User,
        workout_id: int,
        notes: str | None,
    ) -> tuple[dict | None, str | None, int]:
        workout = self.db.get(Workout, workout_id)
        if not workout or workout.athlete_id != athlete.id:
            return None, "Workout not found", 404
        if workout.status != WorkoutStatus.scheduled:
            return None, "Workout cannot be marked complete/skipped in its current status", 400
        workout.status = WorkoutStatus.completed
        workout.completed_at = datetime.utcnow()
        if notes is not None:
            workout.notes = notes
        self.db.commit()
        self.db.refresh(workout)
        return {"workout": self._workout_to_dict(workout)}, None, 200

    def mark_skipped(
        self,
        athlete: User,
        workout_id: int,
    ) -> tuple[dict | None, str | None, int]:
        workout = self.db.get(Workout, workout_id)
        if not workout or workout.athlete_id != athlete.id:
            return None, "Workout not found", 404
        if workout.status != WorkoutStatus.scheduled:
            return None, "Workout cannot be marked complete/skipped in its current status", 400
        workout.status = WorkoutStatus.skipped
        self.db.commit()
        self.db.refresh(workout)
        return {"workout": self._workout_to_dict(workout)}, None, 200
