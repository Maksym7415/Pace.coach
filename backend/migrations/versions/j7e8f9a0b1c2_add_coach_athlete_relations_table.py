"""add coach_athlete_relations table

Revision ID: j7e8f9a0b1c2
Revises: i6d7e8f9a0b1
Create Date: 2026-06-10

"""
from alembic import op
import sqlalchemy as sa


revision = "j7e8f9a0b1c2"
down_revision = "i6d7e8f9a0b1"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "coach_athlete_relations",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("coach_id", sa.Integer(), nullable=False),
        sa.Column("athlete_id", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="pending"),
        sa.Column("permissions", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["athlete_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["coach_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("coach_id", "athlete_id", name="uq_coach_athlete"),
    )
    op.create_index(
        op.f("ix_coach_athlete_relations_athlete_id"),
        "coach_athlete_relations",
        ["athlete_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_coach_athlete_relations_coach_id"),
        "coach_athlete_relations",
        ["coach_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        op.f("ix_coach_athlete_relations_coach_id"), table_name="coach_athlete_relations"
    )
    op.drop_index(
        op.f("ix_coach_athlete_relations_athlete_id"), table_name="coach_athlete_relations"
    )
    op.drop_table("coach_athlete_relations")
