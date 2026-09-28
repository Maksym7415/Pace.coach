"""Calendar cycle_context and planning bands."""
from __future__ import annotations

from datetime import date

from sqlalchemy import event

from src.modules.planning.service import PlanningService
from src.modules.training.service import TrainingService
from tests.conftest import linked_coach_athlete, make_sport, make_workout
from tests.planning_helpers import add_item, add_meso, create_draft_plan


def test_calendar_includes_cycle_context_for_planned_workouts(db_session):
    coach, athlete = linked_coach_athlete(db_session)
    running = make_sport(db_session, "running")
    svc = PlanningService(db_session)
    plan = create_draft_plan(db_session, coach, athlete, service=svc)
    meso = add_meso(db_session, coach, plan["id"], "Base", microcycle_count=1, service=svc)
    item = add_item(db_session, coach, meso["microcycles"][0]["id"], "Easy", service=svc)
    workout = make_workout(
        db_session, athlete, sport=running, scheduled_date=date(2026, 9, 2), title="Easy"
    )
    db_session.commit()
    _, err, _ = svc.attach_workout(coach, item["id"], workout.id)
    assert err is None
    result, err, status = TrainingService(db_session).get_calendar(
        athlete, date(2026, 9, 1), date(2026, 9, 7)
    )
    assert err is None
    ctx = result["workouts"][0]["cycle_context"]
    assert ctx is not None
    assert ctx["training_plan_id"] == plan["id"]
    assert ctx["mesocycle_id"] == meso["id"]
    assert ctx["plan_item_id"] == item["id"]
    assert ctx["plan_item_title"] == "Easy"


def test_calendar_cycle_context_is_null_for_adhoc_workouts(db_session):
    coach, athlete = linked_coach_athlete(db_session)
    running = make_sport(db_session, "running")
    make_workout(
        db_session, athlete, sport=running, scheduled_date=date(2026, 9, 2), title="Ad hoc"
    )
    db_session.commit()
    result, err, _ = TrainingService(db_session).get_calendar(
        athlete, date(2026, 9, 1), date(2026, 9, 7)
    )
    assert err is None
    assert "cycle_context" in result["workouts"][0]
    assert result["workouts"][0]["cycle_context"] is None


def test_calendar_adds_exactly_one_query(db_session):
    coach, athlete = linked_coach_athlete(db_session)
    running = make_sport(db_session, "running")
    svc = PlanningService(db_session)
    plan = create_draft_plan(db_session, coach, athlete, service=svc)
    meso = add_meso(db_session, coach, plan["id"], "Base", microcycle_count=1, service=svc)
    item = add_item(db_session, coach, meso["microcycles"][0]["id"], "Easy", service=svc)
    workout = make_workout(
        db_session, athlete, sport=running, scheduled_date=date(2026, 9, 2)
    )
    db_session.commit()
    svc.attach_workout(coach, item["id"], workout.id)
    statements: list[str] = []

    def before_cursor(conn, cursor, statement, parameters, context, executemany):
        statements.append(statement)

    event.listen(db_session.bind, "before_cursor_execute", before_cursor)
    try:
        TrainingService(db_session).get_calendar(athlete, date(2026, 9, 1), date(2026, 9, 7))
    finally:
        event.remove(db_session.bind, "before_cursor_execute", before_cursor)

    planning_sql = [s for s in statements if "plan_items" in s.lower()]
    assert len(planning_sql) == 1


def test_cycle_bands_returns_overlapping_periods_only(db_session):
    coach, athlete = linked_coach_athlete(db_session)
    svc = PlanningService(db_session)
    plan = create_draft_plan(db_session, coach, athlete, service=svc)
    add_meso(db_session, coach, plan["id"], "Base", microcycle_count=4, service=svc)
    add_meso(db_session, coach, plan["id"], "Build", microcycle_count=2, service=svc)
    result, err, status = svc.get_cycle_bands(
        coach, athlete.id, date(2026, 9, 1), date(2026, 9, 10)
    )
    assert err is None
    assert status == 200
    names = [m["name"] for m in result["mesocycles"]]
    assert "Base" in names
    assert "Build" not in names
    assert all(
        date.fromisoformat(m["start_date"]) <= date(2026, 9, 10)
        and date.fromisoformat(m["end_date"]) >= date(2026, 9, 1)
        for m in result["microcycles"]
    )
