"""add planning cycle tables

Revision ID: z3c4d5e6f7a8
Revises: y2b3c4d5e6f7
Create Date: 2026-08-18
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "z3c4d5e6f7a8"
down_revision = "y2b3c4d5e6f7"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "training_plans",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "athlete_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "coach_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("goal", sa.Text(), nullable=True),
        sa.Column("goal_event_date", sa.Date(), nullable=True),
        sa.Column("start_date", sa.Date(), nullable=True),
        sa.Column("end_date", sa.Date(), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("planning_timezone", sa.String(length=64), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.CheckConstraint("end_date >= start_date", name="ck_training_plans_date_order"),
        sa.CheckConstraint(
            "status IN ('draft', 'active', 'completed', 'archived')",
            name="ck_training_plans_status",
        ),
    )
    op.create_index("ix_training_plans_athlete_id", "training_plans", ["athlete_id"])
    op.create_index("ix_training_plans_coach_id", "training_plans", ["coach_id"])
    op.create_index(
        "ix_training_plans_athlete_start", "training_plans", ["athlete_id", "start_date"]
    )
    op.execute("ALTER TABLE public.training_plans ENABLE ROW LEVEL SECURITY")

    op.create_table(
        "mesocycles",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "training_plan_id",
            sa.Integer(),
            sa.ForeignKey("training_plans.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("focus", sa.String(length=32), nullable=True),
        sa.Column("intent", sa.Text(), nullable=True),
        sa.Column("start_date", sa.Date(), nullable=True),
        sa.Column("end_date", sa.Date(), nullable=True),
        sa.Column("anchor_date", sa.Date(), nullable=True),
        sa.Column("ordinal", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.CheckConstraint("end_date >= start_date", name="ck_mesocycles_date_order"),
        sa.UniqueConstraint("training_plan_id", "ordinal", name="uq_mesocycles_plan_ordinal"),
    )
    op.create_index("ix_mesocycles_training_plan_id", "mesocycles", ["training_plan_id"])
    op.create_index(
        "ix_mesocycles_plan_start", "mesocycles", ["training_plan_id", "start_date"]
    )
    op.execute("ALTER TABLE public.mesocycles ENABLE ROW LEVEL SECURITY")

    op.create_table(
        "microcycles",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "mesocycle_id",
            sa.Integer(),
            sa.ForeignKey("mesocycles.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("name", sa.String(length=255), nullable=True),
        sa.Column("intent", sa.Text(), nullable=True),
        sa.Column("start_date", sa.Date(), nullable=True),
        sa.Column("end_date", sa.Date(), nullable=True),
        sa.Column("duration_days", sa.Integer(), nullable=False),
        sa.Column("ordinal", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.CheckConstraint("end_date >= start_date", name="ck_microcycles_date_order"),
        sa.CheckConstraint(
            "duration_days BETWEEN 1 AND 28",
            name="ck_microcycles_duration_days",
        ),
        sa.UniqueConstraint("mesocycle_id", "ordinal", name="uq_microcycles_mesocycle_ordinal"),
    )
    op.create_index("ix_microcycles_mesocycle_id", "microcycles", ["mesocycle_id"])
    op.create_index(
        "ix_microcycles_meso_start", "microcycles", ["mesocycle_id", "start_date"]
    )
    op.execute("ALTER TABLE public.microcycles ENABLE ROW LEVEL SECURITY")

    op.create_table(
        "plan_items",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "microcycle_id",
            sa.Integer(),
            sa.ForeignKey("microcycles.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("ordinal", sa.Integer(), nullable=False),
        sa.Column("placement_type", sa.String(length=16), nullable=True),
        sa.Column("placement_day", sa.Integer(), nullable=True),
        sa.Column("placement_date", sa.Date(), nullable=True),
        sa.Column(
            "workout_id",
            sa.Integer(),
            sa.ForeignKey("workouts.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("intent", sa.Text(), nullable=True),
        sa.Column("planned_workout_type", sa.String(length=32), nullable=True),
        sa.Column(
            "planned_sport_id",
            sa.Integer(),
            sa.ForeignKey("sports.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("planned_duration_min", sa.Integer(), nullable=True),
        sa.Column("planned_distance_m", sa.Integer(), nullable=True),
        sa.Column("converted_at", sa.DateTime(), nullable=True),
        sa.Column(
            "converted_by_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.UniqueConstraint(
            "microcycle_id", "ordinal", name="uq_plan_items_microcycle_ordinal"
        ),
        sa.CheckConstraint(
            "placement_type IS NULL OR placement_type IN ('relative_day', 'specific_date')",
            name="ck_plan_items_placement_type",
        ),
        sa.CheckConstraint(
            "("
            "  (placement_type IS NULL AND placement_day IS NULL AND placement_date IS NULL)"
            "  OR (placement_type = 'relative_day' AND placement_day IS NOT NULL"
            "      AND placement_day BETWEEN 1 AND 28 AND placement_date IS NULL)"
            "  OR (placement_type = 'specific_date' AND placement_date IS NOT NULL"
            "      AND placement_day IS NULL)"
            ")",
            name="ck_plan_items_placement_shape",
        ),
    )
    op.create_index("ix_plan_items_microcycle_id", "plan_items", ["microcycle_id"])
    op.create_index("ix_plan_items_workout_id", "plan_items", ["workout_id"])
    op.create_index(
        "ix_plan_items_micro_placement_date",
        "plan_items",
        ["microcycle_id", "placement_date"],
    )
    op.create_index(
        "uq_plan_items_workout_id",
        "plan_items",
        ["workout_id"],
        unique=True,
        postgresql_where=sa.text("workout_id IS NOT NULL"),
    )
    op.execute("ALTER TABLE public.plan_items ENABLE ROW LEVEL SECURITY")

    op.create_table(
        "cycle_system_analyses",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "mesocycle_id",
            sa.Integer(),
            sa.ForeignKey("mesocycles.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("generated_at", sa.DateTime(), nullable=False),
        sa.Column("generator", sa.String(length=64), nullable=False),
        sa.Column("generator_version", sa.String(length=32), nullable=False),
        sa.Column("data_cutoff_date", sa.Date(), nullable=False),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("metrics", sa.JSON(), nullable=True),
        sa.Column("source_refs", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.UniqueConstraint(
            "mesocycle_id",
            "generator_version",
            "data_cutoff_date",
            name="uq_cycle_system_analyses_meso_version_cutoff",
        ),
    )
    op.create_index(
        "ix_cycle_system_analyses_mesocycle_id",
        "cycle_system_analyses",
        ["mesocycle_id"],
    )
    op.execute("ALTER TABLE public.cycle_system_analyses ENABLE ROW LEVEL SECURITY")

    op.create_table(
        "cycle_coach_reviews",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "mesocycle_id",
            sa.Integer(),
            sa.ForeignKey("mesocycles.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "coach_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "source_analysis_id",
            sa.Integer(),
            sa.ForeignKey("cycle_system_analyses.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("next_cycle_focus", sa.Text(), nullable=True),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column(
            "superseded_by_id",
            sa.Integer(),
            sa.ForeignKey("cycle_coach_reviews.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("approved_at", sa.DateTime(), nullable=True),
        sa.Column(
            "approved_by_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.UniqueConstraint(
            "mesocycle_id", "version", name="uq_cycle_coach_reviews_meso_version"
        ),
        sa.CheckConstraint(
            "status IN ('draft', 'approved')",
            name="ck_cycle_coach_reviews_status",
        ),
    )
    op.create_index(
        "ix_cycle_coach_reviews_mesocycle_id", "cycle_coach_reviews", ["mesocycle_id"]
    )
    op.create_index(
        "ix_cycle_coach_reviews_source_analysis_id",
        "cycle_coach_reviews",
        ["source_analysis_id"],
    )
    op.execute("ALTER TABLE public.cycle_coach_reviews ENABLE ROW LEVEL SECURITY")

    op.create_table(
        "plan_change_log",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "training_plan_id",
            sa.Integer(),
            sa.ForeignKey("training_plans.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("entity_type", sa.String(length=32), nullable=False),
        sa.Column("entity_id", sa.Integer(), nullable=False),
        sa.Column("operation", sa.String(length=32), nullable=False),
        sa.Column("plan_operation", sa.String(length=32), nullable=True),
        sa.Column("lock_state_at_change", sa.String(length=16), nullable=False),
        sa.Column(
            "changed_by_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("changed_at", sa.DateTime(), nullable=False),
        sa.Column("before", sa.JSON(), nullable=True),
        sa.Column("after", sa.JSON(), nullable=True),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.CheckConstraint(
            "lock_state_at_change IN ('locked', 'current', 'future')",
            name="ck_plan_change_log_lock_state",
        ),
    )
    op.create_index(
        "ix_plan_change_log_training_plan_id", "plan_change_log", ["training_plan_id"]
    )
    op.create_index(
        "ix_plan_change_log_entity", "plan_change_log", ["entity_type", "entity_id"]
    )
    op.create_index("ix_plan_change_log_changed_at", "plan_change_log", ["changed_at"])
    op.execute("ALTER TABLE public.plan_change_log ENABLE ROW LEVEL SECURITY")


def downgrade() -> None:
    op.execute("ALTER TABLE public.plan_change_log DISABLE ROW LEVEL SECURITY")
    op.drop_index("ix_plan_change_log_changed_at", table_name="plan_change_log")
    op.drop_index("ix_plan_change_log_entity", table_name="plan_change_log")
    op.drop_index("ix_plan_change_log_training_plan_id", table_name="plan_change_log")
    op.drop_table("plan_change_log")

    op.execute("ALTER TABLE public.cycle_coach_reviews DISABLE ROW LEVEL SECURITY")
    op.drop_index(
        "ix_cycle_coach_reviews_source_analysis_id", table_name="cycle_coach_reviews"
    )
    op.drop_index("ix_cycle_coach_reviews_mesocycle_id", table_name="cycle_coach_reviews")
    op.drop_table("cycle_coach_reviews")

    op.execute("ALTER TABLE public.cycle_system_analyses DISABLE ROW LEVEL SECURITY")
    op.drop_index(
        "ix_cycle_system_analyses_mesocycle_id", table_name="cycle_system_analyses"
    )
    op.drop_table("cycle_system_analyses")

    op.execute("ALTER TABLE public.plan_items DISABLE ROW LEVEL SECURITY")
    op.drop_index("uq_plan_items_workout_id", table_name="plan_items")
    op.drop_index("ix_plan_items_micro_date", table_name="plan_items")
    op.drop_index("ix_plan_items_workout_id", table_name="plan_items")
    op.drop_index("ix_plan_items_microcycle_id", table_name="plan_items")
    op.drop_table("plan_items")

    op.execute("ALTER TABLE public.microcycles DISABLE ROW LEVEL SECURITY")
    op.drop_index("ix_microcycles_meso_start", table_name="microcycles")
    op.drop_index("ix_microcycles_mesocycle_id", table_name="microcycles")
    op.drop_table("microcycles")

    op.execute("ALTER TABLE public.mesocycles DISABLE ROW LEVEL SECURITY")
    op.drop_index("ix_mesocycles_plan_start", table_name="mesocycles")
    op.drop_index("ix_mesocycles_training_plan_id", table_name="mesocycles")
    op.drop_table("mesocycles")

    op.execute("ALTER TABLE public.training_plans DISABLE ROW LEVEL SECURITY")
    op.drop_index("ix_training_plans_athlete_start", table_name="training_plans")
    op.drop_index("ix_training_plans_coach_id", table_name="training_plans")
    op.drop_index("ix_training_plans_athlete_id", table_name="training_plans")
    op.drop_table("training_plans")
