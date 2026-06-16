"""add workouts table

Revision ID: l9a0b1c2d3e4
Revises: k8f9a0b1c2d3
Create Date: 2026-06-11

"""
from alembic import op
import sqlalchemy as sa


revision = "l9a0b1c2d3e4"
down_revision = "k8f9a0b1c2d3"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "workouts",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("athlete_id", sa.Integer(), nullable=False),
        sa.Column("created_by_id", sa.Integer(), nullable=True),
        sa.Column("scheduled_date", sa.Date(), nullable=False),
        sa.Column("workout_type", sa.String(length=32), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("steps", sa.JSON(), nullable=True),
        sa.Column("duration_min", sa.Integer(), nullable=True),
        sa.Column("distance_m", sa.Integer(), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="scheduled"),
        sa.Column("completed_at", sa.DateTime(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["athlete_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["created_by_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_workouts_athlete_id"), "workouts", ["athlete_id"], unique=False)
    op.create_index(op.f("ix_workouts_scheduled_date"), "workouts", ["scheduled_date"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_workouts_scheduled_date"), table_name="workouts")
    op.drop_index(op.f("ix_workouts_athlete_id"), table_name="workouts")
    op.drop_table("workouts")
