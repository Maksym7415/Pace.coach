"""drop shoes and activity_shoe_distance tables

Revision ID: g4b5c6d7e8f9
Revises: f3a4b5c6d7e8
Create Date: 2026-03-13

Drops legacy shoes and activity_shoe_distance tables.
Data was migrated to gear/activity_gear_usage in e2f3a4b5c6d7.
"""
from alembic import op
import sqlalchemy as sa


revision = "g4b5c6d7e8f9"
down_revision = "f3a4b5c6d7e8"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Drop activity_shoe_distance first (FK to shoes)
    op.execute("DROP INDEX IF EXISTS ix_activity_shoe_distance_activity_shoe")
    op.drop_index(op.f("ix_activity_shoe_distance_shoe_id"), table_name="activity_shoe_distance")
    op.drop_index(op.f("ix_activity_shoe_distance_activity_id"), table_name="activity_shoe_distance")
    op.drop_table("activity_shoe_distance")

    op.drop_index(op.f("ix_shoes_user_id"), table_name="shoes")
    op.drop_table("shoes")


def downgrade() -> None:
    # Recreate tables (schema only; data cannot be restored from gear)
    op.create_table(
        "shoes",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("activity_type", sa.String(64), nullable=False),
        sa.Column("brand", sa.String(128), nullable=False),
        sa.Column("model", sa.String(128), nullable=False),
        sa.Column("nick", sa.String(128), nullable=True),
        sa.Column("max_distance_km", sa.Float(), nullable=True),
        sa.Column("distance_covered_km", sa.Float(), nullable=False, server_default="0"),
        sa.Column("is_default", sa.Boolean(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_shoes_user_id"), "shoes", ["user_id"], unique=False)

    op.create_table(
        "activity_shoe_distance",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("activity_id", sa.Integer(), nullable=True),
        sa.Column("shoe_id", sa.Integer(), nullable=False),
        sa.Column("distance_km", sa.Float(), nullable=False),
        sa.ForeignKeyConstraint(["activity_id"], ["activities.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["shoe_id"], ["shoes.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_activity_shoe_distance_activity_id"),
        "activity_shoe_distance",
        ["activity_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_activity_shoe_distance_shoe_id"),
        "activity_shoe_distance",
        ["shoe_id"],
        unique=False,
    )
    op.execute(
        "CREATE UNIQUE INDEX ix_activity_shoe_distance_activity_shoe "
        "ON activity_shoe_distance (activity_id, shoe_id) WHERE activity_id IS NOT NULL"
    )
