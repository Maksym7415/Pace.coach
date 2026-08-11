"""add athlete response fields to execution_issues

Revision ID: x1a2b3c4d5e6
Revises: w0e1f2a3b4c5
Create Date: 2026-08-11

"""
import sqlalchemy as sa
from alembic import op

revision = "x1a2b3c4d5e6"
down_revision = "w0e1f2a3b4c5"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "execution_issues",
        sa.Column("athlete_id", sa.Integer(), nullable=True),
    )
    op.add_column(
        "execution_issues",
        sa.Column("athlete_reason", sa.String(length=128), nullable=True),
    )
    op.add_column(
        "execution_issues",
        sa.Column("athlete_reason_other", sa.Text(), nullable=True),
    )
    op.add_column(
        "execution_issues",
        sa.Column("athlete_notes", sa.Text(), nullable=True),
    )
    op.add_column(
        "execution_issues",
        sa.Column("athlete_responded_at", sa.DateTime(), nullable=True),
    )
    op.create_index(
        "ix_execution_issues_athlete_id",
        "execution_issues",
        ["athlete_id"],
    )
    op.create_foreign_key(
        "fk_execution_issues_athlete_id",
        "execution_issues",
        "users",
        ["athlete_id"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    op.drop_constraint("fk_execution_issues_athlete_id", "execution_issues", type_="foreignkey")
    op.drop_index("ix_execution_issues_athlete_id", table_name="execution_issues")
    op.drop_column("execution_issues", "athlete_responded_at")
    op.drop_column("execution_issues", "athlete_notes")
    op.drop_column("execution_issues", "athlete_reason_other")
    op.drop_column("execution_issues", "athlete_reason")
    op.drop_column("execution_issues", "athlete_id")
