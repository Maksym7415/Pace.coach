"""SQLite in-memory fixtures and ORM builders for persistence tests."""
from __future__ import annotations

from collections.abc import Generator
from datetime import date, datetime, timedelta

import pytest
from sqlalchemy import create_engine, event, select
from sqlalchemy.orm import Session, sessionmaker

from src.core.database import Base
import src.models  # noqa: F401 — register all tables on Base.metadata
from src.modules.activity_import.models import ActivityLap, ActivityTrackPoint
from src.modules.athlete_profile.models import Sport
from src.modules.coaching.models import CoachAthleteRelation, RelationStatus
from src.modules.gear_track.models import Activity
from src.modules.identity.models import User, UserRole, UserRoleEnum
from src.modules.training.models import Workout, WorkoutStatus, WorkoutType
from src.modules.training.workout_steps import validate_steps

SIMPLE_STEPS = validate_steps(
    "running",
    [{"type": "run", "durationType": "time", "duration": 10}],
)


@pytest.fixture
def db_session() -> Generator[Session, None, None]:
    engine = create_engine("sqlite:///:memory:")

    @event.listens_for(engine, "connect")
    def _enable_foreign_keys(dbapi_conn, _connection_record):  # noqa: ANN001
        dbapi_conn.execute("PRAGMA foreign_keys=ON")

    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()
    try:
        yield session
    finally:
        session.close()
        engine.dispose()


def make_user(
    db: Session,
    *,
    role: UserRoleEnum,
    username: str | None = None,
) -> User:
    suffix = f"{role.value}-{id(object()) % 10_000_000}"
    user = User(
        username=username or suffix[:30],
        email=f"{suffix}@example.test",
        password_hash="x",
        name=suffix,
    )
    db.add(user)
    db.flush()
    db.add(UserRole(user_id=user.id, role=role))
    db.flush()
    return user


def make_sport(db: Session, code: str, name: str | None = None) -> Sport:
    existing = db.scalar(select(Sport).where(Sport.code == code))
    if existing:
        return existing
    sport = Sport(code=code, name=name or code.title(), is_active=True)
    db.add(sport)
    db.flush()
    return sport


def make_workout(
    db: Session,
    athlete: User,
    *,
    scheduled_date: date | None = None,
    sport: Sport | None = None,
    workout_type: WorkoutType = WorkoutType.easy,
    status: WorkoutStatus = WorkoutStatus.scheduled,
    slot_ordinal: int = 0,
    steps: list | None = SIMPLE_STEPS,
    activity_id: int | None = None,
    title: str = "Test workout",
) -> Workout:
    workout = Workout(
        athlete_id=athlete.id,
        scheduled_date=scheduled_date or date(2026, 8, 17),
        sport_id=sport.id if sport else None,
        workout_type=workout_type,
        title=title,
        steps=steps,
        status=status,
        slot_ordinal=slot_ordinal,
        activity_id=activity_id,
    )
    db.add(workout)
    db.flush()
    return workout


def make_activity(
    db: Session,
    athlete: User,
    *,
    sport: Sport | None = None,
    activity_date: date | None = None,
    start_time: datetime | None = None,
    name: str = "Test activity",
    with_streams: bool = True,
) -> Activity:
    started = start_time or datetime(2026, 8, 17, 7, 0, 0)
    activity = Activity(
        user_id=athlete.id,
        name=name,
        date=activity_date or date(2026, 8, 17),
        start_time=started,
        total_distance_km=5.0,
        total_hours=0.2,
        sport_id=sport.id if sport else None,
        source="fit",
    )
    db.add(activity)
    db.flush()
    if with_streams:
        db.add(
            ActivityLap(
                activity_id=activity.id,
                lap_number=1,
                duration=600.0,
                timer_time=600.0,
                distance=5000.0,
                start_time=started,
            )
        )
        for i in range(10):
            db.add(
                ActivityTrackPoint(
                    activity_id=activity.id,
                    timestamp=started + timedelta(seconds=i * 60),
                    distance=float(i * 500),
                    speed=2.8,
                    heart_rate=140,
                )
            )
        db.flush()
    return activity


def make_relation(db: Session, coach: User, athlete: User) -> CoachAthleteRelation:
    relation = CoachAthleteRelation(
        coach_id=coach.id,
        athlete_id=athlete.id,
        status=RelationStatus.active,
    )
    db.add(relation)
    db.flush()
    return relation
