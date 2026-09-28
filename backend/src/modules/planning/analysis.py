"""Deterministic mesocycle system analysis. No AI, no randomness."""
from __future__ import annotations

from datetime import date

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from src.modules.execution.enums import ALGORITHM_VERSION
from src.modules.execution.models import ExecutionIssue, WorkoutExecution, WorkoutStepExecution
from src.modules.execution.scoring import aggregate_execution_score
from src.modules.planning.models import Mesocycle, Microcycle, PlanItem
from src.modules.training.models import Workout, WorkoutStatus

DETERMINISTIC_GENERATOR = "deterministic"
DETERMINISTIC_VERSION = "1.0.0"


def generate_mesocycle_analysis(
    db: Session, mesocycle: Mesocycle, cutoff: date
) -> dict:
    """Aggregate real execution data into summary/metrics/source_refs."""
    item_rows = db.execute(
        select(PlanItem)
        .join(Microcycle, Microcycle.id == PlanItem.microcycle_id)
        .where(Microcycle.mesocycle_id == mesocycle.id)
    ).scalars().all()

    workout_ids = [i.workout_id for i in item_rows if i.workout_id is not None]
    workouts: list[Workout] = []
    if workout_ids:
        workouts = list(
            db.scalars(select(Workout).where(Workout.id.in_(workout_ids))).all()
        )

    completed = sum(1 for w in workouts if w.status == WorkoutStatus.completed)
    skipped = sum(1 for w in workouts if w.status == WorkoutStatus.skipped)
    scheduled = sum(1 for w in workouts if w.status == WorkoutStatus.scheduled)

    execution_ids: list[int] = []
    step_scores: list[float | None] = []
    if workout_ids:
        exec_rows = db.execute(
            select(WorkoutExecution.id, WorkoutStepExecution.score)
            .outerjoin(
                WorkoutStepExecution,
                WorkoutStepExecution.workout_execution_id == WorkoutExecution.id,
            )
            .where(
                WorkoutExecution.workout_id.in_(workout_ids),
                WorkoutExecution.algorithm_version == ALGORITHM_VERSION,
            )
        ).all()
        seen: set[int] = set()
        scores_by_exec: dict[int, list[float | None]] = {}
        for exec_id, score in exec_rows:
            seen.add(exec_id)
            scores_by_exec.setdefault(exec_id, []).append(score)
        execution_ids = sorted(seen)
        step_scores = [
            aggregate_execution_score(scores)
            for scores in scores_by_exec.values()
        ]

    mean_score = aggregate_execution_score(step_scores) if step_scores else None

    issue_counts: dict[str, int] = {}
    if execution_ids:
        issue_rows = db.execute(
            select(ExecutionIssue.code, func.count())
            .where(ExecutionIssue.workout_execution_id.in_(execution_ids))
            .group_by(ExecutionIssue.code)
        ).all()
        issue_counts = {code: count for code, count in issue_rows}

    metrics = {
        "planned_item_count": len(item_rows),
        "workouts_attached": len(workouts),
        "completed_count": completed,
        "skipped_count": skipped,
        "scheduled_count": scheduled,
        "mean_execution_score": mean_score,
        "issue_counts": issue_counts,
    }
    source_refs = {
        "workout_ids": sorted(workout_ids),
        "workout_execution_ids": execution_ids,
    }
    score_text = f"{mean_score}" if mean_score is not None else "n/a"
    summary = (
        f"Mesocycle '{mesocycle.name}': {len(item_rows)} planned items, "
        f"{len(workouts)} workouts ({completed} completed, {skipped} skipped, "
        f"{scheduled} scheduled). Mean execution score: {score_text}."
    )
    return {
        "summary": summary,
        "metrics": metrics,
        "source_refs": source_refs,
        "generator": DETERMINISTIC_GENERATOR,
        "generator_version": DETERMINISTIC_VERSION,
        "data_cutoff_date": cutoff,
    }
