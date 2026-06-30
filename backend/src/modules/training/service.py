"""Training business logic."""
from __future__ import annotations

import logging
from datetime import date, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from src.modules.athlete_profile.models import AthleteSport, Sport
from src.modules.coaching.relations import (
    COACH_ATHLETE_NOT_LINKED_STATUS,
    coach_athlete_relation_error,
)
from src.modules.gear_track.models import Activity
from src.modules.identity.models import User, UserRole, UserRoleEnum
from src.modules.training.models import Workout, WorkoutStatus
from src.modules.training.schemas import WorkoutCreateRequest, WorkoutUpdateRequest
from src.modules.training.workout_steps import compute_rollups, validate_steps

logger = logging.getLogger("coach_app.training")


class TrainingService:
    def __init__(self, db: Session):
        self.db = db

    def _activity_summary(self, activity: Activity) -> dict:
        return {
            "id": activity.id,
            "name": activity.name,
            "date": activity.date.isoformat() if hasattr(activity.date, "isoformat") else str(activity.date),
            "total_distance_km": activity.total_distance_km,
            "total_hours": activity.total_hours,
            "sport_id": activity.sport_id,
            "sport_code": activity.sport.code if activity.sport else None,
            "activity_type_id": activity.activity_type_id,
            "activity_type_code": activity.activity_type.code if activity.activity_type else None,
            "source": activity.source,
        }

    def _workout_to_dict(self, workout: Workout) -> dict:
        linked_activity = None
        if workout.activity_id:
            activity = self.db.scalar(
                select(Activity)
                .options(joinedload(Activity.sport), joinedload(Activity.activity_type))
                .where(Activity.id == workout.activity_id)
            )
            if activity:
                linked_activity = self._activity_summary(activity)

        sport = workout.sport
        return {
            "id": workout.id,
            "athlete_id": workout.athlete_id,
            "created_by_id": workout.created_by_id,
            "scheduled_date": workout.scheduled_date.isoformat(),
            "sport_id": workout.sport_id,
            "sport_code": sport.code if sport else None,
            "sport_name": sport.name if sport else None,
            "workout_type": workout.workout_type.value,
            "title": workout.title,
            "description": workout.description,
            "steps": workout.steps,
            "duration_min": workout.duration_min,
            "distance_m": workout.distance_m,
            "status": workout.status.value,
            "completed_at": workout.completed_at.isoformat() if workout.completed_at else None,
            "notes": workout.notes,
            "activity_id": workout.activity_id,
            "linked_activity": linked_activity,
            "created_at": workout.created_at.isoformat() if workout.created_at else None,
            "updated_at": workout.updated_at.isoformat() if workout.updated_at else None,
        }

    def _load_workout(self, workout_id: int) -> Workout | None:
        return self.db.scalar(
            select(Workout)
            .options(joinedload(Workout.sport))
            .where(Workout.id == workout_id)
        )

    def _assert_athlete_has_sport(self, athlete_id: int, sport_id: int) -> str | None:
        enrolled = self.db.scalar(
            select(AthleteSport).where(
                AthleteSport.athlete_id == athlete_id,
                AthleteSport.sport_id == sport_id,
            )
        )
        if not enrolled:
            return "Athlete is not enrolled in this sport"
        return None

    def _resolve_sport(self, sport_id: int) -> tuple[Sport | None, str | None]:
        sport = self.db.scalar(
            select(Sport).where(Sport.id == sport_id, Sport.is_active.is_(True))
        )
        if not sport:
            return None, "Sport not found"
        return sport, None

    def _prepare_workout_fields(
        self,
        athlete_id: int,
        sport_id: int,
        steps: list,
    ) -> tuple[dict | None, str | None, int]:
        sport, err = self._resolve_sport(sport_id)
        if err:
            return None, err, 404

        enroll_err = self._assert_athlete_has_sport(athlete_id, sport_id)
        if enroll_err:
            return None, enroll_err, 400

        try:
            validated_steps = validate_steps(sport.code, steps)
        except ValueError as exc:
            return None, str(exc), 400

        duration_min, distance_m = compute_rollups(steps)
        return {
            "sport_id": sport_id,
            "steps": validated_steps,
            "duration_min": duration_min,
            "distance_m": distance_m,
        }, None, 200

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

        relation_err = coach_athlete_relation_error(self.db, coach.id, data.athlete_id)
        if relation_err:
            return None, relation_err, COACH_ATHLETE_NOT_LINKED_STATUS

        fields, err, status = self._prepare_workout_fields(
            data.athlete_id, data.sport_id, data.steps
        )
        if err:
            return None, err, status

        workout = Workout(
            athlete_id=data.athlete_id,
            created_by_id=coach.id,
            scheduled_date=data.scheduled_date,
            sport_id=fields["sport_id"],
            workout_type=data.workout_type,
            title=data.title,
            description=data.description,
            steps=fields["steps"],
            duration_min=fields["duration_min"],
            distance_m=fields["distance_m"],
            status=WorkoutStatus.scheduled,
        )
        self.db.add(workout)
        self.db.commit()
        workout = self._load_workout(workout.id)
        logger.info(
            "Coach %s created workout %s for athlete %s",
            coach.id,
            workout.id,
            data.athlete_id,
        )
        return {"workout": self._workout_to_dict(workout)}, None, 201

    def update_workout(
        self,
        coach: User,
        workout_id: int,
        data: WorkoutUpdateRequest,
    ) -> tuple[dict | None, str | None, int]:
        workout = self._load_workout(workout_id)
        if not workout:
            return None, "Workout not found", 404

        relation_err = coach_athlete_relation_error(self.db, coach.id, workout.athlete_id)
        if relation_err:
            return None, relation_err, COACH_ATHLETE_NOT_LINKED_STATUS

        if workout.status != WorkoutStatus.scheduled:
            return None, "Only scheduled workouts can be edited", 400

        fields, err, status = self._prepare_workout_fields(
            workout.athlete_id, data.sport_id, data.steps
        )
        if err:
            return None, err, status

        workout.scheduled_date = data.scheduled_date
        workout.sport_id = fields["sport_id"]
        workout.workout_type = data.workout_type
        workout.title = data.title
        workout.description = data.description
        workout.steps = fields["steps"]
        workout.duration_min = fields["duration_min"]
        workout.distance_m = fields["distance_m"]
        workout.updated_at = datetime.utcnow()

        self.db.commit()
        workout = self._load_workout(workout_id)
        logger.info("Coach %s updated workout %s", coach.id, workout_id)
        return {"workout": self._workout_to_dict(workout)}, None, 200

    def delete_workout(
        self,
        coach: User,
        workout_id: int,
    ) -> tuple[dict | None, str | None, int]:
        workout = self._load_workout(workout_id)
        if not workout:
            return None, "Workout not found", 404

        relation_err = coach_athlete_relation_error(self.db, coach.id, workout.athlete_id)
        if relation_err:
            return None, relation_err, COACH_ATHLETE_NOT_LINKED_STATUS

        if workout.status != WorkoutStatus.scheduled:
            return None, "Only scheduled workouts can be deleted", 400

        self.db.delete(workout)
        self.db.commit()
        logger.info("Coach %s deleted workout %s", coach.id, workout_id)
        return {"deleted": True, "workout_id": workout_id}, None, 200

    def get_calendar_for_coach(
        self,
        coach: User,
        athlete_id: int,
        start_date: date,
        end_date: date,
    ) -> tuple[dict | None, str | None, int]:
        relation_err = coach_athlete_relation_error(self.db, coach.id, athlete_id)
        if relation_err:
            return None, relation_err, COACH_ATHLETE_NOT_LINKED_STATUS
        athlete = self.db.get(User, athlete_id)
        if not athlete:
            return None, "Athlete not found", 404
        return self.get_calendar(athlete, start_date, end_date)

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
            .options(joinedload(Workout.sport))
            .where(
                Workout.athlete_id == athlete.id,
                Workout.scheduled_date >= start_date,
                Workout.scheduled_date <= end_date,
            )
            .order_by(Workout.scheduled_date.asc())
        ).all()
        result = [self._workout_to_dict(w) for w in workouts]
        return {"workouts": result, "count": len(result)}, None, 200

    def get_workout_for_user(
        self,
        user: User,
        workout_id: int,
        is_coach: bool,
        is_athlete: bool = False,
    ) -> tuple[dict | None, str | None, int]:
        workout = self._load_workout(workout_id)
        if not workout:
            return None, "Workout not found", 404

        if is_athlete and workout.athlete_id == user.id:
            return {"workout": self._workout_to_dict(workout)}, None, 200

        if is_coach:
            relation_err = coach_athlete_relation_error(self.db, user.id, workout.athlete_id)
            if relation_err:
                return None, relation_err, COACH_ATHLETE_NOT_LINKED_STATUS
            return {"workout": self._workout_to_dict(workout)}, None, 200

        return None, "Workout not found", 404

    def get_workout(
        self, athlete: User, workout_id: int
    ) -> tuple[dict | None, str | None, int]:
        return self.get_workout_for_user(athlete, workout_id, is_coach=False)

    def mark_completed(
        self,
        athlete: User,
        workout_id: int,
        notes: str | None,
    ) -> tuple[dict | None, str | None, int]:
        workout = self._load_workout(workout_id)
        if not workout or workout.athlete_id != athlete.id:
            return None, "Workout not found", 404
        if workout.status != WorkoutStatus.scheduled:
            return None, "Workout cannot be marked complete/skipped in its current status", 400
        workout.status = WorkoutStatus.completed
        workout.completed_at = datetime.utcnow()
        if notes is not None:
            workout.notes = notes
        self.db.commit()
        workout = self._load_workout(workout_id)
        return {"workout": self._workout_to_dict(workout)}, None, 200

    def mark_skipped(
        self,
        athlete: User,
        workout_id: int,
    ) -> tuple[dict | None, str | None, int]:
        workout = self._load_workout(workout_id)
        if not workout or workout.athlete_id != athlete.id:
            return None, "Workout not found", 404
        if workout.status != WorkoutStatus.scheduled:
            return None, "Workout cannot be marked complete/skipped in its current status", 400
        workout.status = WorkoutStatus.skipped
        self.db.commit()
        workout = self._load_workout(workout_id)
        return {"workout": self._workout_to_dict(workout)}, None, 200
