"""ORM models for the training-plan / cycle layer.

FKs to workouts/users/sports are string-based so this module does not import
`src.modules.training`.
"""
from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import (
    CheckConstraint,
    Date,
    Enum as SAEnum,
    ForeignKey,
    Index,
    Integer,
    JSON,
    String,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.core.database import Base
from src.modules.planning.enums import (
    CoachReviewStatus,
    MesocycleFocus,
    PlacementType,
    PlanOperation,
    TrainingPlanStatus,
)


class TrainingPlan(Base):
    __tablename__ = "training_plans"

    id: Mapped[int] = mapped_column(primary_key=True)
    athlete_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    coach_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    goal: Mapped[str | None] = mapped_column(Text(), nullable=True)
    goal_event_date: Mapped[date | None] = mapped_column(Date(), nullable=True)
    start_date: Mapped[date | None] = mapped_column(Date(), nullable=True)
    end_date: Mapped[date | None] = mapped_column(Date(), nullable=True)
    status: Mapped[TrainingPlanStatus] = mapped_column(
        SAEnum(TrainingPlanStatus, native_enum=False, length=32),
        nullable=False,
        default=TrainingPlanStatus.draft,
    )
    planning_timezone: Mapped[str | None] = mapped_column(String(64), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text(), nullable=True)
    created_at: Mapped[datetime | None] = mapped_column(default=datetime.utcnow)
    updated_at: Mapped[datetime | None] = mapped_column(
        default=datetime.utcnow, onupdate=datetime.utcnow
    )

    mesocycles = relationship("Mesocycle", back_populates="training_plan", order_by="Mesocycle.ordinal")

    __table_args__ = (
        CheckConstraint("end_date >= start_date", name="ck_training_plans_date_order"),
        CheckConstraint(
            "status IN ('draft', 'active', 'completed', 'archived')",
            name="ck_training_plans_status",
        ),
        Index("ix_training_plans_athlete_start", "athlete_id", "start_date"),
    )


class Mesocycle(Base):
    __tablename__ = "mesocycles"

    id: Mapped[int] = mapped_column(primary_key=True)
    training_plan_id: Mapped[int] = mapped_column(
        ForeignKey("training_plans.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    focus: Mapped[MesocycleFocus | None] = mapped_column(
        SAEnum(MesocycleFocus, native_enum=False, length=32), nullable=True
    )
    intent: Mapped[str | None] = mapped_column(Text(), nullable=True)
    start_date: Mapped[date | None] = mapped_column(Date(), nullable=True)
    end_date: Mapped[date | None] = mapped_column(Date(), nullable=True)
    anchor_date: Mapped[date | None] = mapped_column(Date(), nullable=True)
    ordinal: Mapped[int] = mapped_column(Integer(), nullable=False)
    created_at: Mapped[datetime | None] = mapped_column(default=datetime.utcnow)
    updated_at: Mapped[datetime | None] = mapped_column(
        default=datetime.utcnow, onupdate=datetime.utcnow
    )

    training_plan = relationship("TrainingPlan", back_populates="mesocycles")
    microcycles = relationship(
        "Microcycle", back_populates="mesocycle", order_by="Microcycle.ordinal"
    )

    __table_args__ = (
        UniqueConstraint("training_plan_id", "ordinal", name="uq_mesocycles_plan_ordinal"),
        CheckConstraint("end_date >= start_date", name="ck_mesocycles_date_order"),
        Index("ix_mesocycles_plan_start", "training_plan_id", "start_date"),
    )


class Microcycle(Base):
    __tablename__ = "microcycles"

    id: Mapped[int] = mapped_column(primary_key=True)
    mesocycle_id: Mapped[int] = mapped_column(
        ForeignKey("mesocycles.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    intent: Mapped[str | None] = mapped_column(Text(), nullable=True)
    start_date: Mapped[date | None] = mapped_column(Date(), nullable=True)
    end_date: Mapped[date | None] = mapped_column(Date(), nullable=True)
    duration_days: Mapped[int] = mapped_column(Integer(), nullable=False)
    ordinal: Mapped[int] = mapped_column(Integer(), nullable=False)
    created_at: Mapped[datetime | None] = mapped_column(default=datetime.utcnow)
    updated_at: Mapped[datetime | None] = mapped_column(
        default=datetime.utcnow, onupdate=datetime.utcnow
    )

    mesocycle = relationship("Mesocycle", back_populates="microcycles")
    items = relationship("PlanItem", back_populates="microcycle", order_by="PlanItem.ordinal")

    __table_args__ = (
        UniqueConstraint("mesocycle_id", "ordinal", name="uq_microcycles_mesocycle_ordinal"),
        CheckConstraint("end_date >= start_date", name="ck_microcycles_date_order"),
        CheckConstraint(
            "duration_days BETWEEN 1 AND 28",
            name="ck_microcycles_duration_days",
        ),
        Index("ix_microcycles_meso_start", "mesocycle_id", "start_date"),
    )


class PlanItem(Base):
    __tablename__ = "plan_items"

    id: Mapped[int] = mapped_column(primary_key=True)
    microcycle_id: Mapped[int] = mapped_column(
        ForeignKey("microcycles.id", ondelete="CASCADE"), nullable=False, index=True
    )
    ordinal: Mapped[int] = mapped_column(Integer(), nullable=False)
    placement_type: Mapped[PlacementType | None] = mapped_column(
        SAEnum(PlacementType, native_enum=False, length=16), nullable=True
    )
    placement_day: Mapped[int | None] = mapped_column(Integer(), nullable=True)
    placement_date: Mapped[date | None] = mapped_column(Date(), nullable=True)
    workout_id: Mapped[int | None] = mapped_column(
        ForeignKey("workouts.id", ondelete="SET NULL"), nullable=True, index=True
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    intent: Mapped[str | None] = mapped_column(Text(), nullable=True)
    planned_workout_type: Mapped[str | None] = mapped_column(String(32), nullable=True)
    planned_sport_id: Mapped[int | None] = mapped_column(
        ForeignKey("sports.id", ondelete="SET NULL"), nullable=True
    )
    planned_duration_min: Mapped[int | None] = mapped_column(Integer(), nullable=True)
    planned_distance_m: Mapped[int | None] = mapped_column(Integer(), nullable=True)
    converted_at: Mapped[datetime | None] = mapped_column(nullable=True)
    converted_by_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime | None] = mapped_column(default=datetime.utcnow)
    updated_at: Mapped[datetime | None] = mapped_column(
        default=datetime.utcnow, onupdate=datetime.utcnow
    )

    microcycle = relationship("Microcycle", back_populates="items")

    __table_args__ = (
        UniqueConstraint("microcycle_id", "ordinal", name="uq_plan_items_microcycle_ordinal"),
        CheckConstraint(
            "placement_type IS NULL OR placement_type IN ('relative_day', 'specific_date')",
            name="ck_plan_items_placement_type",
        ),
        CheckConstraint(
            "("
            "  (placement_type IS NULL AND placement_day IS NULL AND placement_date IS NULL)"
            "  OR (placement_type = 'relative_day' AND placement_day IS NOT NULL"
            "      AND placement_day BETWEEN 1 AND 28 AND placement_date IS NULL)"
            "  OR (placement_type = 'specific_date' AND placement_date IS NOT NULL"
            "      AND placement_day IS NULL)"
            ")",
            name="ck_plan_items_placement_shape",
        ),
        Index("ix_plan_items_micro_placement_date", "microcycle_id", "placement_date"),
        Index(
            "uq_plan_items_workout_id",
            "workout_id",
            unique=True,
            postgresql_where=text("workout_id IS NOT NULL"),
        ),
    )


class CycleSystemAnalysis(Base):
    __tablename__ = "cycle_system_analyses"

    id: Mapped[int] = mapped_column(primary_key=True)
    mesocycle_id: Mapped[int] = mapped_column(
        ForeignKey("mesocycles.id", ondelete="CASCADE"), nullable=False, index=True
    )
    generated_at: Mapped[datetime] = mapped_column(nullable=False, default=datetime.utcnow)
    generator: Mapped[str] = mapped_column(String(64), nullable=False)
    generator_version: Mapped[str] = mapped_column(String(32), nullable=False)
    data_cutoff_date: Mapped[date] = mapped_column(Date(), nullable=False)
    summary: Mapped[str] = mapped_column(Text(), nullable=False)
    metrics: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    source_refs: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime | None] = mapped_column(default=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint(
            "mesocycle_id",
            "generator_version",
            "data_cutoff_date",
            name="uq_cycle_system_analyses_meso_version_cutoff",
        ),
    )


class CycleCoachReview(Base):
    __tablename__ = "cycle_coach_reviews"

    id: Mapped[int] = mapped_column(primary_key=True)
    mesocycle_id: Mapped[int] = mapped_column(
        ForeignKey("mesocycles.id", ondelete="CASCADE"), nullable=False, index=True
    )
    coach_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    source_analysis_id: Mapped[int | None] = mapped_column(
        ForeignKey("cycle_system_analyses.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    status: Mapped[CoachReviewStatus] = mapped_column(
        SAEnum(CoachReviewStatus, native_enum=False, length=32),
        nullable=False,
        default=CoachReviewStatus.draft,
    )
    content: Mapped[str] = mapped_column(Text(), nullable=False)
    next_cycle_focus: Mapped[str | None] = mapped_column(Text(), nullable=True)
    version: Mapped[int] = mapped_column(Integer(), nullable=False, default=1)
    superseded_by_id: Mapped[int | None] = mapped_column(
        ForeignKey("cycle_coach_reviews.id", ondelete="SET NULL"), nullable=True
    )
    approved_at: Mapped[datetime | None] = mapped_column(nullable=True)
    approved_by_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime | None] = mapped_column(default=datetime.utcnow)
    updated_at: Mapped[datetime | None] = mapped_column(
        default=datetime.utcnow, onupdate=datetime.utcnow
    )

    __table_args__ = (
        UniqueConstraint("mesocycle_id", "version", name="uq_cycle_coach_reviews_meso_version"),
        CheckConstraint(
            "status IN ('draft', 'approved')",
            name="ck_cycle_coach_reviews_status",
        ),
    )


class PlanChangeLog(Base):
    __tablename__ = "plan_change_log"

    id: Mapped[int] = mapped_column(primary_key=True)
    training_plan_id: Mapped[int] = mapped_column(
        ForeignKey("training_plans.id", ondelete="CASCADE"), nullable=False, index=True
    )
    entity_type: Mapped[str] = mapped_column(String(32), nullable=False)
    entity_id: Mapped[int] = mapped_column(Integer(), nullable=False)
    operation: Mapped[str] = mapped_column(String(32), nullable=False)
    plan_operation: Mapped[PlanOperation | None] = mapped_column(
        SAEnum(PlanOperation, native_enum=False, length=32), nullable=True
    )
    lock_state_at_change: Mapped[str] = mapped_column(String(16), nullable=False)
    changed_by_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    changed_at: Mapped[datetime] = mapped_column(nullable=False, default=datetime.utcnow)
    before: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    after: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    reason: Mapped[str | None] = mapped_column(Text(), nullable=True)

    __table_args__ = (
        CheckConstraint(
            "lock_state_at_change IN ('locked', 'current', 'future')",
            name="ck_plan_change_log_lock_state",
        ),
        Index("ix_plan_change_log_entity", "entity_type", "entity_id"),
        Index("ix_plan_change_log_changed_at", "changed_at"),
    )
