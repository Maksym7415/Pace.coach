"""Cycle context lookups for calendar and workout serialization.

Imports only planning models — training.service may import this freely.
"""
from __future__ import annotations

from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from src.modules.planning.models import Mesocycle, Microcycle, PlanItem, TrainingPlan


def cycle_context_for_workouts(db: Session, workout_ids: list[int]) -> dict[int, dict]:
    """One query: plan_items JOIN microcycles JOIN mesocycles JOIN training_plans."""
    if not workout_ids:
        return {}
    rows = db.execute(
        select(
            PlanItem.workout_id,
            PlanItem.id,
            PlanItem.title,
            Microcycle.id,
            Microcycle.name,
            Microcycle.ordinal,
            Microcycle.start_date,
            Microcycle.end_date,
            Mesocycle.id,
            Mesocycle.name,
            Mesocycle.intent,
            TrainingPlan.id,
            TrainingPlan.name,
        )
        .join(Microcycle, Microcycle.id == PlanItem.microcycle_id)
        .join(Mesocycle, Mesocycle.id == Microcycle.mesocycle_id)
        .join(TrainingPlan, TrainingPlan.id == Mesocycle.training_plan_id)
        .where(PlanItem.workout_id.in_(workout_ids))
    ).all()
    result: dict[int, dict] = {}
    for row in rows:
        (
            workout_id,
            item_id,
            item_title,
            micro_id,
            micro_name,
            micro_ordinal,
            micro_start,
            micro_end,
            meso_id,
            meso_name,
            meso_intent,
            plan_id,
            plan_name,
        ) = row
        if workout_id is None:
            continue
        result[workout_id] = {
            "training_plan_id": plan_id,
            "training_plan_name": plan_name,
            "mesocycle_id": meso_id,
            "mesocycle_name": meso_name,
            "mesocycle_intent": meso_intent,
            "microcycle_id": micro_id,
            "microcycle_name": micro_name,
            "microcycle_ordinal": micro_ordinal,
            "microcycle_start_date": micro_start.isoformat() if micro_start else None,
            "microcycle_end_date": micro_end.isoformat() if micro_end else None,
            "plan_item_id": item_id,
            "plan_item_title": item_title,
        }
    return result


def microcycle_range_for_workout(
    db: Session, workout_id: int
) -> tuple[int, date, date] | None:
    row = db.execute(
        select(Microcycle.id, Microcycle.start_date, Microcycle.end_date)
        .join(PlanItem, PlanItem.microcycle_id == Microcycle.id)
        .where(PlanItem.workout_id == workout_id)
    ).first()
    if row is None:
        return None
    return row[0], row[1], row[2]


def cycle_bands(db: Session, athlete_id: int, start: date, end: date) -> dict:
    mesos = db.execute(
        select(Mesocycle, TrainingPlan)
        .join(TrainingPlan, TrainingPlan.id == Mesocycle.training_plan_id)
        .where(
            TrainingPlan.athlete_id == athlete_id,
            Mesocycle.start_date.is_not(None),
            Mesocycle.end_date.is_not(None),
            Mesocycle.start_date <= end,
            Mesocycle.end_date >= start,
        )
        .order_by(Mesocycle.start_date.asc(), Mesocycle.id.asc())
    ).all()
    micros = db.execute(
        select(Microcycle, Mesocycle, TrainingPlan)
        .join(Mesocycle, Mesocycle.id == Microcycle.mesocycle_id)
        .join(TrainingPlan, TrainingPlan.id == Mesocycle.training_plan_id)
        .where(
            TrainingPlan.athlete_id == athlete_id,
            Microcycle.start_date.is_not(None),
            Microcycle.end_date.is_not(None),
            Microcycle.start_date <= end,
            Microcycle.end_date >= start,
        )
        .order_by(Microcycle.start_date.asc(), Microcycle.id.asc())
    ).all()
    return {
        "mesocycles": [
            {
                "id": meso.id,
                "training_plan_id": plan.id,
                "name": meso.name,
                "intent": meso.intent,
                "focus": meso.focus.value if meso.focus else None,
                "start_date": meso.start_date.isoformat(),
                "end_date": meso.end_date.isoformat(),
            }
            for meso, plan in mesos
        ],
        "microcycles": [
            {
                "id": micro.id,
                "mesocycle_id": meso.id,
                "training_plan_id": plan.id,
                "name": micro.name,
                "intent": micro.intent,
                "ordinal": micro.ordinal,
                "start_date": micro.start_date.isoformat(),
                "end_date": micro.end_date.isoformat(),
            }
            for micro, meso, plan in micros
        ],
    }
