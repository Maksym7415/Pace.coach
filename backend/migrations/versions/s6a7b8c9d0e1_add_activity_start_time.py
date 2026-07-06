"""add start_time to activities

Revision ID: s6a7b8c9d0e1
Revises: r5f6a7b8c9d0
Create Date: 2026-07-06

"""
import sqlalchemy as sa
from alembic import op

revision = "s6a7b8c9d0e1"
down_revision = "r5f6a7b8c9d0"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("activities", sa.Column("start_time", sa.DateTime(), nullable=True))
    op.create_index(
        op.f("ix_activities_start_time"),
        "activities",
        ["start_time"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_activities_start_time"), table_name="activities")
    op.drop_column("activities", "start_time")
