"""add activity_types table and refactor activities sport FKs

Revision ID: p3d4e5f6a7b8
Revises: o2c3d4e5f6a7
Create Date: 2026-06-24

"""
import sqlalchemy as sa
from alembic import op

revision = "p3d4e5f6a7b8"
down_revision = "o2c3d4e5f6a7"
branch_labels = None
depends_on = None

_ACTIVITY_TYPE_SEEDS = [
    ("running", "road_run", "Road Run"),
    ("running", "trail_run", "Trail Run"),
    ("running", "track_run", "Track Run"),
    ("running", "treadmill_run", "Treadmill Run"),
    ("running", "race", "Race"),
    ("cycling", "road_ride", "Road Ride"),
    ("cycling", "gravel_ride", "Gravel Ride"),
    ("cycling", "mtb_ride", "MTB Ride"),
    ("cycling", "indoor_ride", "Indoor Ride"),
    ("cycling", "race", "Race"),
    ("swimming", "pool_swim", "Pool Swim"),
    ("swimming", "open_water_swim", "Open Water Swim"),
    ("strength", "strength", "Strength"),
    ("strength", "gym", "Gym"),
    ("strength", "core", "Core"),
    ("strength", "mobility", "Mobility"),
]


def upgrade() -> None:
    conn = op.get_bind()

    conn.execute(
        sa.text(
            """
            INSERT INTO sports (code, name, is_active, created_at)
            SELECT 'strength', 'Strength', true, NOW()
            WHERE NOT EXISTS (SELECT 1 FROM sports WHERE code = 'strength')
            """
        )
    )

    op.create_table(
        "activity_types",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("sport_id", sa.Integer(), nullable=False),
        sa.Column("code", sa.String(length=50), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["sport_id"], ["sports.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("sport_id", "code", name="uq_activity_types_sport_code"),
    )
    op.create_index(
        op.f("ix_activity_types_sport_id"), "activity_types", ["sport_id"], unique=False
    )

    for sport_code, type_code, type_name in _ACTIVITY_TYPE_SEEDS:
        conn.execute(
            sa.text(
                """
                INSERT INTO activity_types (sport_id, code, name, is_active, created_at, updated_at)
                SELECT s.id, :type_code, :type_name, true, NOW(), NOW()
                FROM sports s
                WHERE s.code = :sport_code
                  AND NOT EXISTS (
                    SELECT 1 FROM activity_types at
                    WHERE at.sport_id = s.id AND at.code = :type_code
                  )
                """
            ),
            {"sport_code": sport_code, "type_code": type_code, "type_name": type_name},
        )

    op.add_column("activities", sa.Column("sport_id", sa.Integer(), nullable=True))
    op.add_column("activities", sa.Column("activity_type_id", sa.Integer(), nullable=True))
    op.create_foreign_key(
        "fk_activities_sport_id",
        "activities",
        "sports",
        ["sport_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_foreign_key(
        "fk_activities_activity_type_id",
        "activities",
        "activity_types",
        ["activity_type_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index(op.f("ix_activities_sport_id"), "activities", ["sport_id"], unique=False)
    op.create_index(
        op.f("ix_activities_activity_type_id"), "activities", ["activity_type_id"], unique=False
    )

    conn.execute(
        sa.text(
            """
            UPDATE activities SET sport_id = (SELECT id FROM sports WHERE code = 'running')
            WHERE activity_type = 'run'
            """
        )
    )
    conn.execute(
        sa.text(
            """
            UPDATE activities SET sport_id = (SELECT id FROM sports WHERE code = 'cycling')
            WHERE activity_type = 'bike'
            """
        )
    )
    conn.execute(
        sa.text(
            """
            UPDATE activities SET sport_id = (SELECT id FROM sports WHERE code = 'swimming')
            WHERE activity_type = 'swim'
            """
        )
    )

    op.drop_column("activities", "activity_type")


def downgrade() -> None:
    op.add_column(
        "activities",
        sa.Column("activity_type", sa.String(length=32), nullable=True),
    )

    conn = op.get_bind()
    conn.execute(
        sa.text(
            """
            UPDATE activities SET activity_type = 'run'
            WHERE sport_id = (SELECT id FROM sports WHERE code = 'running')
            """
        )
    )
    conn.execute(
        sa.text(
            """
            UPDATE activities SET activity_type = 'bike'
            WHERE sport_id = (SELECT id FROM sports WHERE code = 'cycling')
            """
        )
    )
    conn.execute(
        sa.text(
            """
            UPDATE activities SET activity_type = 'swim'
            WHERE sport_id = (SELECT id FROM sports WHERE code = 'swimming')
            """
        )
    )
    conn.execute(
        sa.text(
            """
            UPDATE activities SET activity_type = 'other'
            WHERE sport_id IS NULL
            """
        )
    )

    op.drop_index(op.f("ix_activities_activity_type_id"), table_name="activities")
    op.drop_index(op.f("ix_activities_sport_id"), table_name="activities")
    op.drop_constraint("fk_activities_activity_type_id", "activities", type_="foreignkey")
    op.drop_constraint("fk_activities_sport_id", "activities", type_="foreignkey")
    op.drop_column("activities", "activity_type_id")
    op.drop_column("activities", "sport_id")

    op.drop_index(op.f("ix_activity_types_sport_id"), table_name="activity_types")
    op.drop_table("activity_types")

    conn.execute(sa.text("DELETE FROM sports WHERE code = 'strength'"))
