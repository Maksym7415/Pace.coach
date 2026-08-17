"""add slot_ordinal to workouts

Revision ID: y2b3c4d5e6f7
Revises: x1a2b3c4d5e6
Create Date: 2026-08-17
"""
import sqlalchemy as sa
from alembic import op

revision = "y2b3c4d5e6f7"
down_revision = "x1a2b3c4d5e6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "workouts",
        sa.Column("slot_ordinal", sa.Integer(), nullable=False, server_default="0"),
    )


def downgrade() -> None:
    op.drop_column("workouts", "slot_ordinal")
