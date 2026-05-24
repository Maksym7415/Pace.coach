"""refactor activity_shoe_distance

Revision ID: b2c3d4e5f6a7
Revises: a1b2c3d4e5f6
Create Date: 2026-02-28

Replaces activity_shoes with activity_shoe_distance.
- activity_id nullable: null = manual edit, non-null = from activity
- shoe.distance_covered_km = SUM(activity_shoe_distance) for that shoe
"""
from alembic import op
import sqlalchemy as sa


revision = "b2c3d4e5f6a7"
down_revision = "a1b2c3d4e5f6"
branch_labels = None
depends_on = None


def upgrade() -> None:
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
    # Partial unique: one distance per (activity, shoe) when activity_id IS NOT NULL
    op.execute(
        "CREATE UNIQUE INDEX ix_activity_shoe_distance_activity_shoe "
        "ON activity_shoe_distance (activity_id, shoe_id) WHERE activity_id IS NOT NULL"
    )

    # Migrate data from activity_shoes
    op.execute("""
        INSERT INTO activity_shoe_distance (activity_id, shoe_id, distance_km)
        SELECT activity_id, shoe_id, distance_km FROM activity_shoes
    """)

    # Drop activity_shoes
    op.drop_index(op.f("ix_activity_shoes_shoe_id"), table_name="activity_shoes")
    op.drop_index(op.f("ix_activity_shoes_activity_id"), table_name="activity_shoes")
    op.drop_table("activity_shoes")

    # Recompute shoe.distance_covered_km from activity_shoe_distance
    op.execute("""
        UPDATE shoes s
        SET distance_covered_km = COALESCE(
            (SELECT SUM(distance_km) FROM activity_shoe_distance WHERE shoe_id = s.id), 0
        )
    """)


def downgrade() -> None:
    op.create_table(
        "activity_shoes",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("activity_id", sa.Integer(), nullable=False),
        sa.Column("shoe_id", sa.Integer(), nullable=False),
        sa.Column("distance_km", sa.Float(), nullable=False),
        sa.ForeignKeyConstraint(["activity_id"], ["activities.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["shoe_id"], ["shoes.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_activity_shoes_activity_id"), "activity_shoes", ["activity_id"], unique=False)
    op.create_index(op.f("ix_activity_shoes_shoe_id"), "activity_shoes", ["shoe_id"], unique=False)

    # Migrate back: only rows with activity_id set
    op.execute("""
        INSERT INTO activity_shoes (activity_id, shoe_id, distance_km)
        SELECT activity_id, shoe_id, distance_km
        FROM activity_shoe_distance
        WHERE activity_id IS NOT NULL
    """)

    # Recompute shoe.distance_covered_km from activity_shoes (manual rows lost)
    op.execute("""
        UPDATE shoes s
        SET distance_covered_km = COALESCE(
            (SELECT SUM(distance_km) FROM activity_shoes WHERE shoe_id = s.id), 0
        )
    """)

    op.execute("DROP INDEX IF EXISTS ix_activity_shoe_distance_activity_shoe")
    op.drop_index(op.f("ix_activity_shoe_distance_shoe_id"), table_name="activity_shoe_distance")
    op.drop_index(op.f("ix_activity_shoe_distance_activity_id"), table_name="activity_shoe_distance")
    op.drop_table("activity_shoe_distance")
