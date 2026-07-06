"""add activity import and ingestion tables

Revision ID: r5f6a7b8c9d0
Revises: q4e5f6a7b8c9
Create Date: 2026-07-01

"""
import sqlalchemy as sa
from alembic import op

revision = "r5f6a7b8c9d0"
down_revision = "q4e5f6a7b8c9"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "stored_files",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("provider", sa.String(length=64), nullable=False),
        sa.Column("bucket", sa.String(length=255), nullable=False),
        sa.Column("object_key", sa.String(length=512), nullable=False),
        sa.Column("original_filename", sa.String(length=512), nullable=False),
        sa.Column("mime_type", sa.String(length=128), nullable=False),
        sa.Column("checksum", sa.String(length=128), nullable=False),
        sa.Column("file_size", sa.BigInteger(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.execute("ALTER TABLE public.stored_files ENABLE ROW LEVEL SECURITY")

    op.create_table(
        "activity_imports",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("athlete_id", sa.Integer(), nullable=False),
        sa.Column("stored_file_id", sa.Integer(), nullable=False),
        sa.Column("source", sa.String(length=32), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("started_at", sa.DateTime(), nullable=True),
        sa.Column("completed_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.CheckConstraint(
            "status IN ('pending', 'processing', 'completed', 'failed')",
            name="ck_activity_imports_status",
        ),
        sa.ForeignKeyConstraint(["athlete_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["stored_file_id"], ["stored_files.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_activity_imports_athlete_id"), "activity_imports", ["athlete_id"], unique=False
    )
    op.create_index(
        op.f("ix_activity_imports_stored_file_id"),
        "activity_imports",
        ["stored_file_id"],
        unique=False,
    )
    op.execute("ALTER TABLE public.activity_imports ENABLE ROW LEVEL SECURITY")

    op.add_column("activities", sa.Column("activity_import_id", sa.Integer(), nullable=True))
    op.create_foreign_key(
        "fk_activities_activity_import_id",
        "activities",
        "activity_imports",
        ["activity_import_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index(
        op.f("ix_activities_activity_import_id"),
        "activities",
        ["activity_import_id"],
        unique=False,
    )

    op.create_table(
        "activity_laps",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("activity_id", sa.Integer(), nullable=False),
        sa.Column("lap_number", sa.Integer(), nullable=False),
        sa.Column("duration", sa.Float(), nullable=True),
        sa.Column("distance", sa.Float(), nullable=True),
        sa.Column("avg_hr", sa.Integer(), nullable=True),
        sa.Column("max_hr", sa.Integer(), nullable=True),
        sa.Column("avg_power", sa.Integer(), nullable=True),
        sa.Column("avg_speed", sa.Float(), nullable=True),
        sa.Column("avg_pace", sa.Float(), nullable=True),
        sa.ForeignKeyConstraint(["activity_id"], ["activities.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_activity_laps_activity_id"), "activity_laps", ["activity_id"], unique=False
    )
    op.execute("ALTER TABLE public.activity_laps ENABLE ROW LEVEL SECURITY")

    op.create_table(
        "activity_track_points",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("activity_id", sa.Integer(), nullable=False),
        sa.Column("timestamp", sa.DateTime(), nullable=True),
        sa.Column("latitude", sa.Float(), nullable=True),
        sa.Column("longitude", sa.Float(), nullable=True),
        sa.Column("altitude", sa.Float(), nullable=True),
        sa.Column("distance", sa.Float(), nullable=True),
        sa.Column("speed", sa.Float(), nullable=True),
        sa.Column("pace", sa.Float(), nullable=True),
        sa.Column("heart_rate", sa.Integer(), nullable=True),
        sa.Column("cadence", sa.Integer(), nullable=True),
        sa.Column("power", sa.Integer(), nullable=True),
        sa.Column("temperature", sa.Float(), nullable=True),
        sa.Column("running_power", sa.Integer(), nullable=True),
        sa.Column("stride_length", sa.Float(), nullable=True),
        sa.Column("vertical_oscillation", sa.Float(), nullable=True),
        sa.Column("ground_contact_time", sa.Float(), nullable=True),
        sa.Column("left_right_balance", sa.Float(), nullable=True),
        sa.Column("stamina", sa.Float(), nullable=True),
        sa.ForeignKeyConstraint(["activity_id"], ["activities.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_activity_track_points_activity_id"),
        "activity_track_points",
        ["activity_id"],
        unique=False,
    )
    op.execute("ALTER TABLE public.activity_track_points ENABLE ROW LEVEL SECURITY")

    op.create_table(
        "activity_sources",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("activity_id", sa.Integer(), nullable=False),
        sa.Column("provider", sa.String(length=64), nullable=False),
        sa.Column("external_id", sa.String(length=255), nullable=True),
        sa.Column("raw_metadata", sa.JSON(), nullable=True),
        sa.ForeignKeyConstraint(["activity_id"], ["activities.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_activity_sources_activity_id"), "activity_sources", ["activity_id"], unique=False
    )
    op.execute("ALTER TABLE public.activity_sources ENABLE ROW LEVEL SECURITY")


def downgrade() -> None:
    op.execute("ALTER TABLE public.activity_sources DISABLE ROW LEVEL SECURITY")
    op.drop_index(op.f("ix_activity_sources_activity_id"), table_name="activity_sources")
    op.drop_table("activity_sources")

    op.execute("ALTER TABLE public.activity_track_points DISABLE ROW LEVEL SECURITY")
    op.drop_index(
        op.f("ix_activity_track_points_activity_id"), table_name="activity_track_points"
    )
    op.drop_table("activity_track_points")

    op.execute("ALTER TABLE public.activity_laps DISABLE ROW LEVEL SECURITY")
    op.drop_index(op.f("ix_activity_laps_activity_id"), table_name="activity_laps")
    op.drop_table("activity_laps")

    op.drop_index(op.f("ix_activities_activity_import_id"), table_name="activities")
    op.drop_constraint("fk_activities_activity_import_id", "activities", type_="foreignkey")
    op.drop_column("activities", "activity_import_id")

    op.execute("ALTER TABLE public.activity_imports DISABLE ROW LEVEL SECURITY")
    op.drop_index(op.f("ix_activity_imports_stored_file_id"), table_name="activity_imports")
    op.drop_index(op.f("ix_activity_imports_athlete_id"), table_name="activity_imports")
    op.drop_table("activity_imports")

    op.execute("ALTER TABLE public.stored_files DISABLE ROW LEVEL SECURITY")
    op.drop_table("stored_files")
