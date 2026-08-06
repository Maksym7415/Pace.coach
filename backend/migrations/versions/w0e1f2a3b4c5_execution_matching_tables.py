"""add workout execution matching tables and backfill step ids

Revision ID: w0e1f2a3b4c5
Revises: v9d0e1f2a3b4
Create Date: 2026-08-05
"""
from __future__ import annotations

import json
import uuid

import sqlalchemy as sa
from alembic import op

revision = "w0e1f2a3b4c5"
down_revision = "v9d0e1f2a3b4"
branch_labels = None
depends_on = None


def _ensure_ids(items: list) -> list:
    result = []
    for item in items:
        if not isinstance(item, dict):
            result.append(item)
            continue
        if "repeatCount" in item:
            block = dict(item)
            if not block.get("id"):
                block["id"] = str(uuid.uuid4())
            children = []
            for step in block.get("steps") or []:
                if isinstance(step, dict):
                    child = dict(step)
                    if not child.get("id"):
                        child["id"] = str(uuid.uuid4())
                    children.append(child)
                else:
                    children.append(step)
            block["steps"] = children
            result.append(block)
        else:
            step = dict(item)
            if not step.get("id"):
                step["id"] = str(uuid.uuid4())
            result.append(step)
    return result


def _backfill_step_ids(table_name: str) -> None:
    conn = op.get_bind()
    rows = conn.execute(sa.text(f"SELECT id, steps FROM {table_name}")).fetchall()
    for row_id, steps in rows:
        if steps is None:
            continue
        if isinstance(steps, str):
            try:
                steps = json.loads(steps)
            except json.JSONDecodeError:
                continue
        if not isinstance(steps, list):
            continue
        updated = _ensure_ids(steps)
        conn.execute(
            sa.text(f"UPDATE {table_name} SET steps = :steps WHERE id = :id"),
            {"steps": json.dumps(updated), "id": row_id},
        )


def upgrade() -> None:
    op.create_table(
        "workout_plan_snapshots",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("workout_id", sa.Integer(), sa.ForeignKey("workouts.id", ondelete="CASCADE"), nullable=False),
        sa.Column("athlete_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("resolved_plan", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=True),
    )
    op.create_index("ix_workout_plan_snapshots_workout_id", "workout_plan_snapshots", ["workout_id"])
    op.create_index("ix_workout_plan_snapshots_athlete_id", "workout_plan_snapshots", ["athlete_id"])
    op.execute("ALTER TABLE public.workout_plan_snapshots ENABLE ROW LEVEL SECURITY")

    op.create_table(
        "workout_executions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("workout_id", sa.Integer(), sa.ForeignKey("workouts.id", ondelete="CASCADE"), nullable=False),
        sa.Column("activity_id", sa.Integer(), sa.ForeignKey("activities.id", ondelete="CASCADE"), nullable=False),
        sa.Column(
            "plan_snapshot_id",
            sa.Integer(),
            sa.ForeignKey("workout_plan_snapshots.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("overall_confidence", sa.Float(), nullable=True),
        sa.Column("segmentation_strategy", sa.String(length=64), nullable=True),
        sa.Column("algorithm_version", sa.String(length=32), nullable=False),
        sa.Column("extra_work", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.UniqueConstraint(
            "workout_id",
            "activity_id",
            "algorithm_version",
            name="uq_workout_executions_workout_activity_version",
        ),
    )
    op.create_index("ix_workout_executions_workout_id", "workout_executions", ["workout_id"])
    op.create_index("ix_workout_executions_activity_id", "workout_executions", ["activity_id"])
    op.create_index("ix_workout_executions_plan_snapshot_id", "workout_executions", ["plan_snapshot_id"])
    op.execute("ALTER TABLE public.workout_executions ENABLE ROW LEVEL SECURITY")

    op.create_table(
        "workout_step_executions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "workout_execution_id",
            sa.Integer(),
            sa.ForeignKey("workout_executions.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("authored_step_id", sa.String(length=36), nullable=False),
        sa.Column("occurrence_path", sa.String(length=255), nullable=False),
        sa.Column("occurrence_ordinal", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("started_at", sa.DateTime(), nullable=True),
        sa.Column("ended_at", sa.DateTime(), nullable=True),
        sa.Column("match_confidence", sa.Float(), nullable=True),
        sa.Column("match_evidence", sa.JSON(), nullable=True),
        sa.Column("duration_moving_s", sa.Float(), nullable=True),
        sa.Column("duration_elapsed_s", sa.Float(), nullable=True),
        sa.Column("distance_m", sa.Float(), nullable=True),
        sa.Column("target_metric", sa.String(length=64), nullable=True),
        sa.Column("time_in_target_pct", sa.Float(), nullable=True),
        sa.Column("target_deviation_pct", sa.Float(), nullable=True),
        sa.Column("metrics", sa.JSON(), nullable=True),
        sa.Column("metrics_computed_at", sa.DateTime(), nullable=True),
        sa.Column("score", sa.Float(), nullable=True),
        sa.Column("score_components", sa.JSON(), nullable=True),
        sa.Column("scored_at", sa.DateTime(), nullable=True),
        sa.UniqueConstraint(
            "workout_execution_id",
            "authored_step_id",
            "occurrence_ordinal",
            name="uq_step_exec_occurrence",
        ),
    )
    op.create_index(
        "ix_workout_step_executions_workout_execution_id",
        "workout_step_executions",
        ["workout_execution_id"],
    )
    op.create_index(
        "ix_workout_step_executions_authored_step_id",
        "workout_step_executions",
        ["authored_step_id"],
    )
    op.execute("ALTER TABLE public.workout_step_executions ENABLE ROW LEVEL SECURITY")

    op.create_table(
        "execution_issues",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "workout_execution_id",
            sa.Integer(),
            sa.ForeignKey("workout_executions.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("authored_step_id", sa.String(length=36), nullable=True),
        sa.Column("occurrence_ordinal", sa.Integer(), nullable=True),
        sa.Column("code", sa.String(length=64), nullable=False),
        sa.Column("severity", sa.String(length=16), nullable=False),
        sa.Column("dimension", sa.String(length=32), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
    )
    op.create_index("ix_execution_issues_workout_execution_id", "execution_issues", ["workout_execution_id"])
    op.create_index("ix_execution_issues_authored_step_id", "execution_issues", ["authored_step_id"])
    op.create_index("ix_execution_issues_code", "execution_issues", ["code"])
    op.execute("ALTER TABLE public.execution_issues ENABLE ROW LEVEL SECURITY")

    _backfill_step_ids("workouts")
    _backfill_step_ids("workout_templates")


def downgrade() -> None:
    op.execute("ALTER TABLE public.execution_issues DISABLE ROW LEVEL SECURITY")
    op.drop_index("ix_execution_issues_code", table_name="execution_issues")
    op.drop_index("ix_execution_issues_authored_step_id", table_name="execution_issues")
    op.drop_index("ix_execution_issues_workout_execution_id", table_name="execution_issues")
    op.drop_table("execution_issues")

    op.execute("ALTER TABLE public.workout_step_executions DISABLE ROW LEVEL SECURITY")
    op.drop_index("ix_workout_step_executions_authored_step_id", table_name="workout_step_executions")
    op.drop_index(
        "ix_workout_step_executions_workout_execution_id",
        table_name="workout_step_executions",
    )
    op.drop_table("workout_step_executions")

    op.execute("ALTER TABLE public.workout_executions DISABLE ROW LEVEL SECURITY")
    op.drop_index("ix_workout_executions_plan_snapshot_id", table_name="workout_executions")
    op.drop_index("ix_workout_executions_activity_id", table_name="workout_executions")
    op.drop_index("ix_workout_executions_workout_id", table_name="workout_executions")
    op.drop_table("workout_executions")

    op.execute("ALTER TABLE public.workout_plan_snapshots DISABLE ROW LEVEL SECURITY")
    op.drop_index("ix_workout_plan_snapshots_athlete_id", table_name="workout_plan_snapshots")
    op.drop_index("ix_workout_plan_snapshots_workout_id", table_name="workout_plan_snapshots")
    op.drop_table("workout_plan_snapshots")
