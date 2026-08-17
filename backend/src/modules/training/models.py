"""Training plan models."""
import enum
from datetime import date, datetime

from sqlalchemy import Date, Enum as SAEnum, ForeignKey, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.core.database import Base


class WorkoutType(str, enum.Enum):
    easy = "easy"
    recovery = "recovery"
    long_run = "long_run"
    threshold = "threshold"
    intervals = "intervals"
    hills = "hills"
    race_pace = "race_pace"
    rest = "rest"


class WorkoutStatus(str, enum.Enum):
    scheduled = "scheduled"
    completed = "completed"
    skipped = "skipped"


class Workout(Base):
    __tablename__ = "workouts"

    id: Mapped[int] = mapped_column(primary_key=True)
    athlete_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    created_by_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    scheduled_date: Mapped[date] = mapped_column(Date(), nullable=False, index=True)
    workout_type: Mapped[WorkoutType] = mapped_column(
        SAEnum(WorkoutType, native_enum=False, length=32), nullable=False
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    purpose: Mapped[str | None] = mapped_column(String(255), nullable=True)
    target_rpe: Mapped[int | None] = mapped_column(Integer(), nullable=True)
    description: Mapped[str | None] = mapped_column(Text(), nullable=True)
    steps: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    duration_min: Mapped[int | None] = mapped_column(Integer(), nullable=True)
    distance_m: Mapped[int | None] = mapped_column(Integer(), nullable=True)

    status: Mapped[WorkoutStatus] = mapped_column(
        SAEnum(WorkoutStatus, native_enum=False, length=32),
        nullable=False,
        default=WorkoutStatus.scheduled,
    )
    completed_at: Mapped[datetime | None] = mapped_column(nullable=True)
    notes: Mapped[str | None] = mapped_column(Text(), nullable=True)
    activity_id: Mapped[int | None] = mapped_column(
        ForeignKey("activities.id", ondelete="SET NULL"), nullable=True, index=True
    )
    sport_id: Mapped[int | None] = mapped_column(
        ForeignKey("sports.id", ondelete="SET NULL"), nullable=True, index=True
    )
    slot_ordinal: Mapped[int] = mapped_column(
        Integer(), nullable=False, default=0, server_default="0"
    )

    created_at: Mapped[datetime | None] = mapped_column(default=datetime.utcnow)
    updated_at: Mapped[datetime | None] = mapped_column(
        default=datetime.utcnow, onupdate=datetime.utcnow
    )

    athlete = relationship("User", foreign_keys=[athlete_id])
    created_by = relationship("User", foreign_keys=[created_by_id])
    activity = relationship("Activity", foreign_keys=[activity_id])
    sport = relationship("Sport", foreign_keys=[sport_id])


class WorkoutTemplate(Base):
    __tablename__ = "workout_templates"

    id: Mapped[int] = mapped_column(primary_key=True)
    coach_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    sport_id: Mapped[int] = mapped_column(
        ForeignKey("sports.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    workout_type: Mapped[WorkoutType] = mapped_column(
        SAEnum(WorkoutType, native_enum=False, length=32), nullable=False
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    purpose: Mapped[str | None] = mapped_column(String(255), nullable=True)
    target_rpe: Mapped[int | None] = mapped_column(Integer(), nullable=True)
    description: Mapped[str | None] = mapped_column(Text(), nullable=True)
    steps: Mapped[dict] = mapped_column(JSON, nullable=False)
    duration_min: Mapped[int | None] = mapped_column(Integer(), nullable=True)
    distance_m: Mapped[int | None] = mapped_column(Integer(), nullable=True)

    created_at: Mapped[datetime | None] = mapped_column(default=datetime.utcnow)
    updated_at: Mapped[datetime | None] = mapped_column(
        default=datetime.utcnow, onupdate=datetime.utcnow
    )

    coach = relationship("User", foreign_keys=[coach_id])
    sport = relationship("Sport", foreign_keys=[sport_id])
