"""add athlete profile tables

Revision ID: o2c3d4e5f6a7
Revises: n1a2b3c4d5e6
Create Date: 2026-06-23

"""
import sqlalchemy as sa
from alembic import op

revision = "o2c3d4e5f6a7"
down_revision = "n1a2b3c4d5e6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "sports",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("code", sa.String(length=50), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("code"),
    )

    op.create_table(
        "athlete_sports",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("athlete_id", sa.Integer(), nullable=False),
        sa.Column("sport_id", sa.Integer(), nullable=False),
        sa.Column("is_primary", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["athlete_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["sport_id"], ["sports.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("athlete_id", "sport_id", name="uq_athlete_sports_athlete_sport"),
    )
    op.create_index(
        op.f("ix_athlete_sports_athlete_id"), "athlete_sports", ["athlete_id"], unique=False
    )

    op.create_table(
        "athlete_sport_profiles",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("athlete_id", sa.Integer(), nullable=False),
        sa.Column("sport_id", sa.Integer(), nullable=False),
        sa.Column("threshold_pace_sec_per_km", sa.Integer(), nullable=True),
        sa.Column("threshold_hr", sa.Integer(), nullable=True),
        sa.Column("ftp_watts", sa.Integer(), nullable=True),
        sa.Column("css_pace_sec_per_100m", sa.Integer(), nullable=True),
        sa.Column("zone_source", sa.String(length=50), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["athlete_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["sport_id"], ["sports.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "athlete_id", "sport_id", name="uq_athlete_sport_profiles_athlete_sport"
        ),
    )
    op.create_index(
        op.f("ix_athlete_sport_profiles_athlete_id"),
        "athlete_sport_profiles",
        ["athlete_id"],
        unique=False,
    )

    op.create_table(
        "athlete_zones",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("athlete_sport_profile_id", sa.Integer(), nullable=False),
        sa.Column("zone_category", sa.String(length=50), nullable=False),
        sa.Column("zone_name", sa.String(length=50), nullable=False),
        sa.Column("min_value", sa.Float(), nullable=False),
        sa.Column("max_value", sa.Float(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(
            ["athlete_sport_profile_id"],
            ["athlete_sport_profiles.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_athlete_zones_athlete_sport_profile_id"),
        "athlete_zones",
        ["athlete_sport_profile_id"],
        unique=False,
    )

    op.create_table(
        "athlete_baselines",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("athlete_id", sa.Integer(), nullable=False),
        sa.Column("hrv_baseline_min", sa.Float(), nullable=True),
        sa.Column("hrv_baseline_max", sa.Float(), nullable=True),
        sa.Column("resting_hr_baseline", sa.Float(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["athlete_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("athlete_id"),
    )

    op.create_table(
        "athlete_body_metrics",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("athlete_id", sa.Integer(), nullable=False),
        sa.Column("weight_kg", sa.Float(), nullable=True),
        sa.Column("height_cm", sa.Float(), nullable=True),
        sa.Column("measured_at", sa.Date(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["athlete_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_athlete_body_metrics_athlete_id"),
        "athlete_body_metrics",
        ["athlete_id"],
        unique=False,
    )

    op.add_column("workouts", sa.Column("sport_id", sa.Integer(), nullable=True))
    op.create_foreign_key(
        "fk_workouts_sport_id",
        "workouts",
        "sports",
        ["sport_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index(op.f("ix_workouts_sport_id"), "workouts", ["sport_id"], unique=False)

    conn = op.get_bind()
    conn.execute(
        sa.text(
            """
            INSERT INTO sports (code, name, is_active, created_at) VALUES
              ('running', 'Running', true, NOW()),
              ('cycling', 'Cycling', true, NOW()),
              ('swimming', 'Swimming', true, NOW())
            """
        )
    )

    conn.execute(
        sa.text(
            """
            INSERT INTO athlete_sports (athlete_id, sport_id, is_primary, created_at)
            SELECT ur.user_id, s.id, true, NOW()
            FROM user_roles ur
            CROSS JOIN sports s
            WHERE ur.role = 'athlete'
              AND s.code = 'running'
              AND NOT EXISTS (
                SELECT 1 FROM athlete_sports asp
                WHERE asp.athlete_id = ur.user_id
              )
            """
        )
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_workouts_sport_id"), table_name="workouts")
    op.drop_constraint("fk_workouts_sport_id", "workouts", type_="foreignkey")
    op.drop_column("workouts", "sport_id")

    op.drop_index(op.f("ix_athlete_body_metrics_athlete_id"), table_name="athlete_body_metrics")
    op.drop_table("athlete_body_metrics")

    op.drop_table("athlete_baselines")

    op.drop_index(op.f("ix_athlete_zones_athlete_sport_profile_id"), table_name="athlete_zones")
    op.drop_table("athlete_zones")

    op.drop_index(
        op.f("ix_athlete_sport_profiles_athlete_id"), table_name="athlete_sport_profiles"
    )
    op.drop_table("athlete_sport_profiles")

    op.drop_index(op.f("ix_athlete_sports_athlete_id"), table_name="athlete_sports")
    op.drop_table("athlete_sports")

    op.drop_table("sports")
