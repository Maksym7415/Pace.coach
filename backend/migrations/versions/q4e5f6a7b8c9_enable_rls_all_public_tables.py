"""enable rls on all public tables

Revision ID: q4e5f6a7b8c9
Revises: p3d4e5f6a7b8
Create Date: 2026-06-24

Blocks Supabase PostgREST access to application tables. No RLS policies are
added, so anon/authenticated roles cannot read or write via the Data API.
The backend connects as postgres (superuser) and bypasses RLS.
"""
from alembic import op

revision = "q4e5f6a7b8c9"
down_revision = "p3d4e5f6a7b8"
branch_labels = None
depends_on = None

_PUBLIC_TABLES = (
    "alembic_version",
    "users",
    "user_roles",
    "users_strava",
    "activities",
    "gear",
    "gear_installations",
    "activity_gear_usage",
    "gear_services",
    "gear_service_logs",
    "activity_types",
    "workouts",
    "recovery_entries",
    "coach_athlete_relations",
    "sports",
    "athlete_sports",
    "athlete_sport_profiles",
    "athlete_zones",
    "athlete_baselines",
    "athlete_body_metrics",
)


def _set_rls(table: str, *, enable: bool) -> None:
    action = "ENABLE" if enable else "DISABLE"
    op.execute(f"ALTER TABLE public.{table} {action} ROW LEVEL SECURITY")


def upgrade() -> None:
    for table in _PUBLIC_TABLES:
        _set_rls(table, enable=True)


def downgrade() -> None:
    for table in reversed(_PUBLIC_TABLES):
        _set_rls(table, enable=False)
