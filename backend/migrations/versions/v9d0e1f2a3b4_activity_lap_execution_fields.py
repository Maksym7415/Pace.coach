"""add execution evidence fields to activity_laps

Revision ID: v9d0e1f2a3b4
Revises: u8c9d0e1f2a3
Create Date: 2026-08-05
"""
import sqlalchemy as sa
from alembic import op

revision = "v9d0e1f2a3b4"
down_revision = "u8c9d0e1f2a3"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("activity_laps", sa.Column("timer_time", sa.Float(), nullable=True))
    op.add_column("activity_laps", sa.Column("start_time", sa.DateTime(), nullable=True))
    op.add_column("activity_laps", sa.Column("message_index", sa.Integer(), nullable=True))
    op.add_column("activity_laps", sa.Column("wkt_step_index", sa.Integer(), nullable=True))
    op.add_column("activity_laps", sa.Column("lap_trigger", sa.String(length=64), nullable=True))
    op.add_column("activity_laps", sa.Column("intensity", sa.String(length=32), nullable=True))


def downgrade() -> None:
    op.drop_column("activity_laps", "intensity")
    op.drop_column("activity_laps", "lap_trigger")
    op.drop_column("activity_laps", "wkt_step_index")
    op.drop_column("activity_laps", "message_index")
    op.drop_column("activity_laps", "start_time")
    op.drop_column("activity_laps", "timer_time")
