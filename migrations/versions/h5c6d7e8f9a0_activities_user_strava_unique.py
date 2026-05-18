"""partial unique index on (user_id, strava_activity_id)

Revision ID: h5c6d7e8f9a0
Revises: g4b5c6d7e8f9
Create Date: 2026-04-03

Prevents duplicate Strava imports per user. Null strava_activity_id (manual activities) still allowed.
"""
from alembic import op
import sqlalchemy as sa


revision = "h5c6d7e8f9a0"
down_revision = "g4b5c6d7e8f9"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_index(
        "uq_activities_user_strava_activity",
        "activities",
        ["user_id", "strava_activity_id"],
        unique=True,
        postgresql_where=sa.text("strava_activity_id IS NOT NULL"),
    )


def downgrade() -> None:
    op.drop_index("uq_activities_user_strava_activity", table_name="activities")
