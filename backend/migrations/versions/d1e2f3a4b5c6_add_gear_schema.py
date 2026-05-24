"""add gear schema

Revision ID: d1e2f3a4b5c6
Revises: b2c3d4e5f6a7
Create Date: 2026-03-08

Add gear tables, activity_gear_usage, gear_installations, gear_services, gear_service_logs.
Extend users with preferred_distance_unit, activities with total_hours, total_sessions, activity_type.
"""
from alembic import op
import sqlalchemy as sa


revision = "d1e2f3a4b5c6"
down_revision = "b2c3d4e5f6a7"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add preferred_distance_unit to users
    op.add_column(
        "users",
        sa.Column("preferred_distance_unit", sa.String(8), nullable=True, server_default="km"),
    )

    # Extend activities
    op.add_column("activities", sa.Column("total_hours", sa.Float(), nullable=True))
    op.add_column("activities", sa.Column("total_sessions", sa.Float(), nullable=True))
    op.add_column("activities", sa.Column("activity_type", sa.String(32), nullable=True))

    # Create gear table
    op.create_table(
        "gear",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("activity_type", sa.String(32), nullable=False),
        sa.Column("gear_type", sa.String(32), nullable=False),
        sa.Column("brand", sa.String(128), nullable=False),
        sa.Column("model", sa.String(128), nullable=False),
        sa.Column("nick", sa.String(128), nullable=True),
        sa.Column("metric_type", sa.String(32), nullable=False, server_default="distance"),
        sa.Column("max_value", sa.Float(), nullable=True),
        sa.Column("value_covered", sa.Float(), nullable=False, server_default="0"),
        sa.Column("is_default", sa.Boolean(), nullable=False, server_default="0"),
        sa.Column("status", sa.String(16), nullable=False, server_default="active"),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_gear_user_id"), "gear", ["user_id"], unique=False)

    # Create activity_gear_usage table
    op.create_table(
        "activity_gear_usage",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("activity_id", sa.Integer(), nullable=True),
        sa.Column("gear_id", sa.Integer(), nullable=False),
        sa.Column("value", sa.Float(), nullable=False),
        sa.ForeignKeyConstraint(["activity_id"], ["activities.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["gear_id"], ["gear.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_activity_gear_usage_activity_id"),
        "activity_gear_usage",
        ["activity_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_activity_gear_usage_gear_id"),
        "activity_gear_usage",
        ["gear_id"],
        unique=False,
    )
    op.execute(
        "CREATE UNIQUE INDEX ix_activity_gear_usage_activity_gear "
        "ON activity_gear_usage (activity_id, gear_id) WHERE activity_id IS NOT NULL"
    )

    # Create gear_installations table
    op.create_table(
        "gear_installations",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("child_gear_id", sa.Integer(), nullable=False),
        sa.Column("parent_gear_id", sa.Integer(), nullable=False),
        sa.Column("installed_at", sa.DateTime(), nullable=True),
        sa.Column("removed_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["child_gear_id"], ["gear.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["parent_gear_id"], ["gear.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_gear_installations_child_gear_id"),
        "gear_installations",
        ["child_gear_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_gear_installations_parent_gear_id"),
        "gear_installations",
        ["parent_gear_id"],
        unique=False,
    )

    # Create gear_services table
    op.create_table(
        "gear_services",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("gear_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(128), nullable=False),
        sa.Column("interval_value", sa.Float(), nullable=False),
        sa.Column("interval_unit", sa.String(32), nullable=False),
        sa.Column("early_warning_ratio", sa.Float(), nullable=True),
        sa.Column("last_performed_value", sa.Float(), nullable=True),
        sa.ForeignKeyConstraint(["gear_id"], ["gear.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_gear_services_gear_id"),
        "gear_services",
        ["gear_id"],
        unique=False,
    )

    # Create gear_service_logs table
    op.create_table(
        "gear_service_logs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("gear_service_id", sa.Integer(), nullable=False),
        sa.Column("performed_at", sa.DateTime(), nullable=True),
        sa.Column("value_at_perform", sa.Float(), nullable=False),
        sa.ForeignKeyConstraint(["gear_service_id"], ["gear_services.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_gear_service_logs_gear_service_id"),
        "gear_service_logs",
        ["gear_service_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_gear_service_logs_gear_service_id"), table_name="gear_service_logs")
    op.drop_table("gear_service_logs")
    op.drop_index(op.f("ix_gear_services_gear_id"), table_name="gear_services")
    op.drop_table("gear_services")
    op.drop_index(op.f("ix_gear_installations_parent_gear_id"), table_name="gear_installations")
    op.drop_index(op.f("ix_gear_installations_child_gear_id"), table_name="gear_installations")
    op.drop_table("gear_installations")
    op.execute("DROP INDEX IF EXISTS ix_activity_gear_usage_activity_gear")
    op.drop_index(op.f("ix_activity_gear_usage_gear_id"), table_name="activity_gear_usage")
    op.drop_index(op.f("ix_activity_gear_usage_activity_id"), table_name="activity_gear_usage")
    op.drop_table("activity_gear_usage")
    op.drop_index(op.f("ix_gear_user_id"), table_name="gear")
    op.drop_table("gear")
    op.drop_column("activities", "activity_type")
    op.drop_column("activities", "total_sessions")
    op.drop_column("activities", "total_hours")
    op.drop_column("users", "preferred_distance_unit")
