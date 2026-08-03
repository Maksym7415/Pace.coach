"""add workout intent fields and workout_templates

Revision ID: u8c9d0e1f2a3
Revises: t7b8c9d0e1f2
Create Date: 2026-07-23
"""
import sqlalchemy as sa
from alembic import op

revision = "u8c9d0e1f2a3"
down_revision = "t7b8c9d0e1f2"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("workouts", sa.Column("purpose", sa.String(length=255), nullable=True))
    op.add_column("workouts", sa.Column("target_rpe", sa.Integer(), nullable=True))

    op.create_table(
        "workout_templates",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("coach_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("sport_id", sa.Integer(), sa.ForeignKey("sports.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("workout_type", sa.String(length=32), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("purpose", sa.String(length=255), nullable=True),
        sa.Column("target_rpe", sa.Integer(), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("steps", sa.JSON(), nullable=False),
        sa.Column("duration_min", sa.Integer(), nullable=True),
        sa.Column("distance_m", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
    )
    op.create_index(op.f("ix_workout_templates_coach_id"), "workout_templates", ["coach_id"], unique=False)
    op.create_index(op.f("ix_workout_templates_sport_id"), "workout_templates", ["sport_id"], unique=False)
    op.execute("ALTER TABLE public.workout_templates ENABLE ROW LEVEL SECURITY")


def downgrade() -> None:
    op.execute("ALTER TABLE public.workout_templates DISABLE ROW LEVEL SECURITY")
    op.drop_index(op.f("ix_workout_templates_sport_id"), table_name="workout_templates")
    op.drop_index(op.f("ix_workout_templates_coach_id"), table_name="workout_templates")
    op.drop_table("workout_templates")
    op.drop_column("workouts", "target_rpe")
    op.drop_column("workouts", "purpose")
