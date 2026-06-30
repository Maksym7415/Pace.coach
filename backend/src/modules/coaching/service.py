"""Coaching business logic."""
from __future__ import annotations

import logging
from datetime import date, timedelta

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, joinedload

from src.modules.coaching.models import CoachAthleteRelation, RelationStatus
from src.modules.coaching.relations import (
    COACH_ATHLETE_NOT_LINKED_ERROR,
    COACH_ATHLETE_NOT_LINKED_STATUS,
    get_active_coach_athlete_relation,
)
from src.modules.identity.models import User, UserRole, UserRoleEnum
from src.modules.training.models import Workout, WorkoutStatus

logger = logging.getLogger("coach_app.coaching")


def _user_summary(user: User) -> dict:
    return {
        "id": user.id,
        "name": user.name,
        "username": user.username,
        "email": user.email,
    }


def _athlete_summary(user: User) -> dict:
    return _user_summary(user)


class CoachingService:
    def __init__(self, db: Session):
        self.db = db

    def _rel_to_dict(self, rel: CoachAthleteRelation) -> dict:
        return {
            "id": rel.id,
            "coach_id": rel.coach_id,
            "athlete_id": rel.athlete_id,
            "status": rel.status.value,
            "permissions": rel.permissions,
            "created_at": rel.created_at.isoformat() if rel.created_at else None,
            "updated_at": rel.updated_at.isoformat() if rel.updated_at else None,
        }

    def invite_athlete(
        self, coach: User, athlete_id: int
    ) -> tuple[dict | None, str | None, int]:
        if coach.id == athlete_id:
            return None, "Cannot invite yourself", 400
        athlete = self.db.get(User, athlete_id)
        if not athlete:
            return None, "User not found", 404
        has_athlete_role = self.db.scalar(
            select(UserRole).where(
                UserRole.user_id == athlete_id,
                UserRole.role == UserRoleEnum.athlete,
            )
        )
        if not has_athlete_role:
            return None, "Target user is not an athlete", 400
        existing = self.db.scalar(
            select(CoachAthleteRelation).where(
                CoachAthleteRelation.coach_id == coach.id,
                CoachAthleteRelation.athlete_id == athlete_id,
                CoachAthleteRelation.status.in_(
                    [RelationStatus.pending, RelationStatus.active]
                ),
            )
        )
        if existing:
            return None, "An active or pending relation already exists", 409
        rel = CoachAthleteRelation(coach_id=coach.id, athlete_id=athlete_id)
        self.db.add(rel)
        self.db.commit()
        self.db.refresh(rel)
        logger.info("Coach %s invited athlete %s", coach.id, athlete_id)
        return {"relation": self._rel_to_dict(rel)}, None, 201

    def accept_invitation(
        self, athlete: User, relation_id: int
    ) -> tuple[dict | None, str | None, int]:
        rel = self.db.get(CoachAthleteRelation, relation_id)
        if not rel or rel.athlete_id != athlete.id:
            return None, "Invitation not found", 404
        if rel.status != RelationStatus.pending:
            return None, "Invitation is not pending", 400
        rel.status = RelationStatus.active
        self.db.commit()
        return {"relation": self._rel_to_dict(rel)}, None, 200

    def reject_invitation(
        self, athlete: User, relation_id: int
    ) -> tuple[dict | None, str | None, int]:
        rel = self.db.get(CoachAthleteRelation, relation_id)
        if not rel or rel.athlete_id != athlete.id:
            return None, "Invitation not found", 404
        if rel.status != RelationStatus.pending:
            return None, "Invitation is not pending", 400
        rel.status = RelationStatus.rejected
        self.db.commit()
        return {"relation": self._rel_to_dict(rel)}, None, 200

    def revoke_relation(
        self, user: User, relation_id: int
    ) -> tuple[dict | None, str | None, int]:
        rel = self.db.get(CoachAthleteRelation, relation_id)
        if not rel:
            return None, "Relation not found", 404
        if rel.coach_id != user.id and rel.athlete_id != user.id:
            return None, "Not authorized", 403
        if rel.status not in (RelationStatus.pending, RelationStatus.active):
            return None, "Relation cannot be revoked in its current status", 400
        rel.status = RelationStatus.revoked
        self.db.commit()
        return {"relation": self._rel_to_dict(rel)}, None, 200

    def list_my_athletes(self, coach: User) -> dict:
        rels = (
            self.db.scalars(
                select(CoachAthleteRelation)
                .where(
                    CoachAthleteRelation.coach_id == coach.id,
                    CoachAthleteRelation.status == RelationStatus.active,
                )
                .options(joinedload(CoachAthleteRelation.athlete))
            )
            .unique()
            .all()
        )
        athletes = []
        for rel in rels:
            athlete = rel.athlete
            if not athlete:
                continue
            athletes.append(
                {
                    "relation_id": rel.id,
                    "athlete": _athlete_summary(athlete),
                    "status": rel.status.value,
                    "created_at": rel.created_at.isoformat() if rel.created_at else None,
                }
            )
        return {"athletes": athletes, "count": len(athletes)}

    def get_athlete_detail(
        self, coach: User, athlete_id: int
    ) -> tuple[dict | None, str | None, int]:
        rel = get_active_coach_athlete_relation(self.db, coach.id, athlete_id)
        if not rel:
            return None, COACH_ATHLETE_NOT_LINKED_ERROR, COACH_ATHLETE_NOT_LINKED_STATUS
        athlete = self.db.get(User, athlete_id)
        if not athlete:
            return None, "Athlete not found", 404

        today = date.today()
        upcoming_end = today + timedelta(days=7)
        upcoming_count = self.db.scalar(
            select(func.count())
            .select_from(Workout)
            .where(
                Workout.athlete_id == athlete_id,
                Workout.scheduled_date >= today,
                Workout.scheduled_date <= upcoming_end,
                Workout.status == WorkoutStatus.scheduled,
            )
        )

        return (
            {
                "relation_id": rel.id,
                "coaching_since": rel.created_at.isoformat() if rel.created_at else None,
                "athlete": _athlete_summary(athlete),
                "upcoming_workouts_count": int(upcoming_count or 0),
            },
            None,
            200,
        )

    def list_my_coaches(self, athlete: User) -> dict:
        rels = self.db.scalars(
            select(CoachAthleteRelation).where(
                CoachAthleteRelation.athlete_id == athlete.id,
                CoachAthleteRelation.status == RelationStatus.active,
            )
        ).all()
        return {"relations": [self._rel_to_dict(r) for r in rels]}

    def list_pending_invitations(self, user: User) -> dict:
        rels = (
            self.db.scalars(
                select(CoachAthleteRelation)
                .where(
                    CoachAthleteRelation.athlete_id == user.id,
                    CoachAthleteRelation.status == RelationStatus.pending,
                )
                .options(joinedload(CoachAthleteRelation.coach))
            )
            .unique()
            .all()
        )
        invitations = []
        for rel in rels:
            coach = rel.coach
            if not coach:
                continue
            invitations.append(
                {
                    "relation_id": rel.id,
                    "coach": _user_summary(coach),
                    "status": rel.status.value,
                    "created_at": rel.created_at.isoformat() if rel.created_at else None,
                }
            )
        return {"invitations": invitations, "count": len(invitations)}

    def search_users(
        self,
        query: str,
        role: UserRoleEnum | None = None,
        limit: int = 20,
    ) -> dict:
        limit = min(limit, 50)
        stmt = select(User).where(
            or_(
                User.name.ilike(f"%{query}%"),
                User.username.ilike(f"%{query}%"),
            )
        )
        if role is not None:
            stmt = stmt.join(UserRole, User.id == UserRole.user_id).where(
                UserRole.role == role
            )
        stmt = stmt.limit(limit)
        users = self.db.scalars(stmt).all()
        return {
            "users": [
                {
                    "id": u.id,
                    "name": u.name,
                    "username": u.username,
                    "roles": [r.role.value for r in u.roles],
                }
                for u in users
            ]
        }
