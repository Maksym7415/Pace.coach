"""add activity_id to workouts

Revision ID: n1a2b3c4d5e6
Revises: m0b1c2d3e4f5
Create Date: 2026-06-16

"""
import sqlalchemy as sa
from alembic import op

revision = "n1a2b3c4d5e6"
down_revision = "m0b1c2d3e4f5"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("workouts", sa.Column("activity_id", sa.Integer(), nullable=True))
    op.create_foreign_key(
        "fk_workouts_activity_id",
        "workouts",
        "activities",
        ["activity_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index(op.f("ix_workouts_activity_id"), "workouts", ["activity_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_workouts_activity_id"), table_name="workouts")
    op.drop_constraint("fk_workouts_activity_id", "workouts", type_="foreignkey")
    op.drop_column("workouts", "activity_id")
