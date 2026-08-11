"""ORM models for workout execution matching."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    DateTime,
    Float,
    ForeignKey,
    Integer,
    JSON,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.core.database import Base


class WorkoutPlanSnapshot(Base):
    __tablename__ = "workout_plan_snapshots"

    id: Mapped[int] = mapped_column(primary_key=True)
    workout_id: Mapped[int] = mapped_column(
        ForeignKey("workouts.id", ondelete="CASCADE"), nullable=False, index=True
    )
    athlete_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    resolved_plan: Mapped[dict] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime | None] = mapped_column(default=datetime.utcnow)

    workout = relationship("Workout")
    athlete = relationship("User")
    executions = relationship("WorkoutExecution", back_populates="plan_snapshot")


class WorkoutExecution(Base):
    __tablename__ = "workout_executions"

    id: Mapped[int] = mapped_column(primary_key=True)
    workout_id: Mapped[int] = mapped_column(
        ForeignKey("workouts.id", ondelete="CASCADE"), nullable=False, index=True
    )
    activity_id: Mapped[int] = mapped_column(
        ForeignKey("activities.id", ondelete="CASCADE"), nullable=False, index=True
    )
    plan_snapshot_id: Mapped[int] = mapped_column(
        ForeignKey("workout_plan_snapshots.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    overall_confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    segmentation_strategy: Mapped[str | None] = mapped_column(String(64), nullable=True)
    algorithm_version: Mapped[str] = mapped_column(String(32), nullable=False)
    extra_work: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime | None] = mapped_column(default=datetime.utcnow)
    updated_at: Mapped[datetime | None] = mapped_column(
        default=datetime.utcnow, onupdate=datetime.utcnow
    )

    workout = relationship("Workout")
    activity = relationship("Activity")
    plan_snapshot = relationship("WorkoutPlanSnapshot", back_populates="executions")
    step_executions = relationship(
        "WorkoutStepExecution",
        back_populates="workout_execution",
        cascade="all, delete-orphan",
    )
    issues = relationship(
        "ExecutionIssue",
        back_populates="workout_execution",
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        UniqueConstraint(
            "workout_id",
            "activity_id",
            "algorithm_version",
            name="uq_workout_executions_workout_activity_version",
        ),
    )


class WorkoutStepExecution(Base):
    __tablename__ = "workout_step_executions"

    id: Mapped[int] = mapped_column(primary_key=True)
    workout_execution_id: Mapped[int] = mapped_column(
        ForeignKey("workout_executions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Identity
    authored_step_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    occurrence_path: Mapped[str] = mapped_column(String(255), nullable=False)
    occurrence_ordinal: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)

    # Window
    started_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    ended_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    match_confidence: Mapped[float | None] = mapped_column(Float, nullable=True)

    # Evidence
    match_evidence: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    # Metrics (query surface + blob)
    duration_moving_s: Mapped[float | None] = mapped_column(Float, nullable=True)
    duration_elapsed_s: Mapped[float | None] = mapped_column(Float, nullable=True)
    distance_m: Mapped[float | None] = mapped_column(Float, nullable=True)
    target_metric: Mapped[str | None] = mapped_column(String(64), nullable=True)
    time_in_target_pct: Mapped[float | None] = mapped_column(Float, nullable=True)
    target_deviation_pct: Mapped[float | None] = mapped_column(Float, nullable=True)
    metrics: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    metrics_computed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    # Score
    score: Mapped[float | None] = mapped_column(Float, nullable=True)
    score_components: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    scored_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    workout_execution = relationship("WorkoutExecution", back_populates="step_executions")

    __table_args__ = (
        UniqueConstraint(
            "workout_execution_id",
            "authored_step_id",
            "occurrence_ordinal",
            name="uq_step_exec_occurrence",
        ),
    )


class ExecutionIssue(Base):
    __tablename__ = "execution_issues"

    id: Mapped[int] = mapped_column(primary_key=True)
    workout_execution_id: Mapped[int] = mapped_column(
        ForeignKey("workout_executions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    authored_step_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    occurrence_ordinal: Mapped[int | None] = mapped_column(Integer, nullable=True)
    code: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    severity: Mapped[str] = mapped_column(String(16), nullable=False)
    dimension: Mapped[str] = mapped_column(String(32), nullable=False)
    payload: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime | None] = mapped_column(default=datetime.utcnow)

    # Athlete explanation (structured response to this algorithmic finding)
    athlete_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    athlete_reason: Mapped[str | None] = mapped_column(String(128), nullable=True)
    athlete_reason_other: Mapped[str | None] = mapped_column(Text, nullable=True)
    athlete_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    athlete_responded_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    workout_execution = relationship("WorkoutExecution", back_populates="issues")
    athlete = relationship("User", foreign_keys=[athlete_id])
