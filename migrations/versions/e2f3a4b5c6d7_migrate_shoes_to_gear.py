"""migrate shoes to gear

Revision ID: e2f3a4b5c6d7
Revises: d1e2f3a4b5c6
Create Date: 2026-03-08

Migrate shoes -> gear, activity_shoe_distance -> activity_gear_usage.
Normalize activity_type: "running" -> "run", etc.
"""
from alembic import op
import sqlalchemy as sa


revision = "e2f3a4b5c6d7"
down_revision = "d1e2f3a4b5c6"
branch_labels = None
depends_on = None


def _normalize_activity_type(at):
    """Map shoe activity_type to gear activity_type (run/bike/swim/other)."""
    if not at:
        return "run"
    at = (at or "").strip().lower()
    if at in ("run", "running"):
        return "run"
    if at in ("bike", "cycling", "biking"):
        return "bike"
    if at in ("swim", "swimming"):
        return "swim"
    return "other"


def upgrade() -> None:
    # Add temporary shoe_id to gear for mapping
    op.add_column("gear", sa.Column("_migrated_from_shoe_id", sa.Integer(), nullable=True))
    op.create_index("ix_gear_migrated_shoe", "gear", ["_migrated_from_shoe_id"], unique=False)

    # Migrate shoes -> gear
    conn = op.get_bind()
    shoes = conn.execute(sa.text("SELECT id, user_id, activity_type, brand, model, nick, max_distance_km, distance_covered_km, is_default, created_at FROM shoes")).fetchall()
    for row in shoes:
        shoe_id, user_id, activity_type, brand, model, nick, max_distance_km, distance_covered_km, is_default, created_at = row
        act_type = _normalize_activity_type(activity_type)
        conn.execute(
            sa.text("""
                INSERT INTO gear (user_id, activity_type, gear_type, brand, model, nick, metric_type, max_value, value_covered, is_default, status, created_at, _migrated_from_shoe_id)
                VALUES (:user_id, :activity_type, 'shoe', :brand, :model, :nick, 'distance', :max_value, :value_covered, :is_default, 'active', :created_at, :shoe_id)
            """),
            {
                "user_id": user_id,
                "activity_type": act_type,
                "brand": brand or "",
                "model": model or "",
                "nick": nick,
                "max_value": max_distance_km,
                "value_covered": float(distance_covered_km or 0),
                "is_default": bool(is_default),
                "created_at": created_at,
                "shoe_id": shoe_id,
            },
        )

    # Migrate activity_shoe_distance -> activity_gear_usage
    op.execute("""
        INSERT INTO activity_gear_usage (activity_id, gear_id, value)
        SELECT asd.activity_id, g.id, asd.distance_km
        FROM activity_shoe_distance asd
        JOIN gear g ON g._migrated_from_shoe_id = asd.shoe_id
    """)

    # Drop temp column
    op.drop_index("ix_gear_migrated_shoe", table_name="gear")
    op.drop_column("gear", "_migrated_from_shoe_id")

    # Set activity_type on existing activities (default run for backwards compat)
    op.execute("UPDATE activities SET activity_type = 'run' WHERE activity_type IS NULL")


def downgrade() -> None:
    # Remove migrated shoe gear and their usage. Cannot restore shoes table data.
    op.execute("""
        DELETE FROM activity_gear_usage
        WHERE gear_id IN (SELECT id FROM gear WHERE gear_type = 'shoe')
    """)
    op.execute("DELETE FROM gear WHERE gear_type = 'shoe'")
    op.execute("UPDATE activities SET activity_type = NULL")
