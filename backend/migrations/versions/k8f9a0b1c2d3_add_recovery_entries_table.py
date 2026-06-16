"""add recovery_entries table

Revision ID: k8f9a0b1c2d3
Revises: j7e8f9a0b1c2
Create Date: 2026-06-11

"""
from alembic import op
import sqlalchemy as sa


revision = "k8f9a0b1c2d3"
down_revision = "j7e8f9a0b1c2"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "recovery_entries",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("entry_date", sa.Date(), nullable=False),
        sa.Column("hrv_ms", sa.Float(), nullable=True),
        sa.Column("resting_hr_bpm", sa.Integer(), nullable=True),
        sa.Column("body_battery", sa.Integer(), nullable=True),
        sa.Column("fatigue", sa.Integer(), nullable=True),
        sa.Column("soreness", sa.Integer(), nullable=True),
        sa.Column("mood", sa.Integer(), nullable=True),
        sa.Column("sleep_quality", sa.Integer(), nullable=True),
        sa.Column("sleep_hours", sa.Float(), nullable=True),
        sa.Column("readiness_score", sa.Integer(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "entry_date", name="uq_recovery_user_date"),
    )
    op.create_index(op.f("ix_recovery_entries_user_id"), "recovery_entries", ["user_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_recovery_entries_user_id"), table_name="recovery_entries")
    op.drop_table("recovery_entries")
