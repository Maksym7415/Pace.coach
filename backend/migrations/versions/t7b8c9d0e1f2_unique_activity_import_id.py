"""partial unique index on activities.activity_import_id

Revision ID: t7b8c9d0e1f2
Revises: s6a7b8c9d0e1
Create Date: 2026-07-06

Prevents duplicate activities for the same import job on retry.
"""
import sqlalchemy as sa
from alembic import op

revision = "t7b8c9d0e1f2"
down_revision = "s6a7b8c9d0e1"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_index(op.f("ix_activities_activity_import_id"), table_name="activities")
    op.create_index(
        "uq_activities_activity_import_id",
        "activities",
        ["activity_import_id"],
        unique=True,
        postgresql_where=sa.text("activity_import_id IS NOT NULL"),
    )


def downgrade() -> None:
    op.drop_index("uq_activities_activity_import_id", table_name="activities")
    op.create_index(
        op.f("ix_activities_activity_import_id"),
        "activities",
        ["activity_import_id"],
        unique=False,
    )
