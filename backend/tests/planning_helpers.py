"""Shared builders for planning persistence tests."""
from __future__ import annotations

from datetime import date

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from src.modules.identity.models import User
from src.modules.planning.models import PlanChangeLog
from src.modules.planning.schemas import (
    MesocycleCreateRequest,
    MicrocycleCreateRequest,
    PlanItemCreateRequest,
    TrainingPlanCreateRequest,
)
from src.modules.planning.service import PlanningService
from src.modules.training.schemas import WorkoutCreateRequest
from tests.conftest import SIMPLE_STEPS


PLAN_START = date(2026, 9, 1)
PLAN_END = date(2026, 11, 23)


def freeze_today(monkeypatch, day: date) -> None:
    monkeypatch.setattr(
        "src.modules.planning.service.planning_today", lambda _plan: day
    )
    monkeypatch.setattr(
        "src.modules.planning.clock.planning_today", lambda _plan: day
    )


def log_count(db: Session, plan_id: int | None = None) -> int:
    stmt = select(func.count()).select_from(PlanChangeLog)
    if plan_id is not None:
        stmt = stmt.where(PlanChangeLog.training_plan_id == plan_id)
    return db.scalar(stmt) or 0


def create_draft_plan(
    db: Session,
    coach: User,
    athlete: User,
    *,
    name: str = "Autumn 10K",
    start: date | None = PLAN_START,
    timezone: str | None = "Europe/Warsaw",
    service: PlanningService | None = None,
) -> dict:
    svc = service or PlanningService(db)
    result, err, status = svc.create_plan(
        coach,
        TrainingPlanCreateRequest(
            athlete_id=athlete.id,
            name=name,
            start_date=start,
            planning_timezone=timezone,
        ),
    )
    assert err is None, err
    assert status == 201
    return result["plan"]


def add_meso(
    db: Session,
    coach: User,
    plan_id: int,
    name: str,
    *,
    microcycle_count: int | None = None,
    microcycle_duration_days: int = 7,
    duration_days: int | None = None,
    anchor_date: date | None = None,
    service: PlanningService | None = None,
) -> dict:
    svc = service or PlanningService(db)
    result, err, status = svc.create_mesocycle(
        coach,
        plan_id,
        MesocycleCreateRequest(
            name=name,
            microcycle_count=microcycle_count,
            microcycle_duration_days=microcycle_duration_days,
            duration_days=duration_days,
            anchor_date=anchor_date,
        ),
    )
    assert err is None, err
    assert status == 201
    return result["mesocycle"]


def add_micro(
    db: Session,
    coach: User,
    mesocycle_id: int,
    *,
    duration_days: int = 7,
    name: str | None = None,
    service: PlanningService | None = None,
) -> dict:
    svc = service or PlanningService(db)
    result, err, status = svc.create_microcycle(
        coach,
        mesocycle_id,
        MicrocycleCreateRequest(duration_days=duration_days, name=name),
    )
    assert err is None, err
    assert status == 201
    return result["microcycle"]


def add_item(
    db: Session,
    coach: User,
    microcycle_id: int,
    title: str,
    *,
    intent: str | None = None,
    placement_type: str | None = None,
    placement_day: int | None = None,
    placement_date: date | None = None,
    service: PlanningService | None = None,
) -> dict:
    from src.modules.planning.enums import PlacementType

    svc = service or PlanningService(db)
    ptype = PlacementType(placement_type) if placement_type else None
    result, err, status = svc.create_item(
        coach,
        microcycle_id,
        PlanItemCreateRequest(
            title=title,
            intent=intent,
            placement_type=ptype,
            placement_day=placement_day,
            placement_date=placement_date,
        ),
    )
    assert err is None, err
    assert status == 201
    return result["item"]


def workout_create_payload(
    athlete_id: int,
    sport_id: int,
    scheduled_date: date,
    title: str = "Session",
) -> WorkoutCreateRequest:
    return WorkoutCreateRequest(
        athlete_id=athlete_id,
        scheduled_date=scheduled_date,
        sport_id=sport_id,
        title=title,
        steps=SIMPLE_STEPS,
    )


def micro_row_snapshot(micro) -> dict:
    return {
        "id": micro.id,
        "mesocycle_id": micro.mesocycle_id,
        "name": micro.name,
        "intent": micro.intent,
        "start_date": micro.start_date,
        "end_date": micro.end_date,
        "ordinal": micro.ordinal,
    }
