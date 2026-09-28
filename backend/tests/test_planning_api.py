"""Planning API: plans, mesocycles, microcycles, change log."""
from __future__ import annotations

from datetime import date

from sqlalchemy import event, select

from src.modules.coaching.relations import COACH_ATHLETE_NOT_LINKED_ERROR
from src.modules.identity.models import UserRoleEnum
from src.modules.planning.enums import TrainingPlanStatus
from src.modules.planning.models import PlanChangeLog, TrainingPlan
from src.modules.planning.schemas import (
    MesocycleUpdateRequest,
    MicrocycleUpdateRequest,
    TrainingPlanCreateRequest,
    TrainingPlanUpdateRequest,
)
from src.modules.planning.service import PlanningService
from tests.conftest import linked_coach_athlete, make_user
from tests.planning_helpers import (
    PLAN_START,
    add_meso,
    create_draft_plan,
    log_count,
)


def test_create_plan_requires_active_relation(db_session):
    coach = make_user(db_session, role=UserRoleEnum.coach)
    athlete = make_user(db_session, role=UserRoleEnum.athlete)
    db_session.commit()
    result, err, status = PlanningService(db_session).create_plan(
        coach,
        TrainingPlanCreateRequest(
            athlete_id=athlete.id,
            name="Autumn 10K",
            start_date=PLAN_START,
        ),
    )
    assert result is None
    assert status == 404
    assert err == COACH_ATHLETE_NOT_LINKED_ERROR


def test_create_mesocycle_with_microcycle_count_generates_contiguous_periods(db_session):
    coach, athlete = linked_coach_athlete(db_session)
    plan = create_draft_plan(db_session, coach, athlete)
    meso = add_meso(db_session, coach, plan["id"], "Base", microcycle_count=4)
    micros = meso["microcycles"]
    assert len(micros) == 4
    assert micros[0]["start_date"] == "2026-09-01"
    assert micros[0]["end_date"] == "2026-09-07"
    assert micros[3]["start_date"] == "2026-09-22"
    assert micros[3]["end_date"] == "2026-09-28"
    for i in range(1, 4):
        prev_end = date.fromisoformat(micros[i - 1]["end_date"])
        start = date.fromisoformat(micros[i]["start_date"])
        assert (start - prev_end).days == 1


def test_microcycles_tile_their_mesocycle_exactly(db_session):
    coach, athlete = linked_coach_athlete(db_session)
    plan = create_draft_plan(db_session, coach, athlete)
    meso = add_meso(db_session, coach, plan["id"], "Base", microcycle_count=4)
    micros = meso["microcycles"]
    assert meso["start_date"] == micros[0]["start_date"]
    assert meso["end_date"] == micros[-1]["end_date"]
    covered = sum(m["duration_days"] for m in micros)
    assert covered == meso["duration_days"]


def test_reorder_mesocycles_two_phase_renumber_succeeds(db_session):
    coach, athlete = linked_coach_athlete(db_session)
    svc = PlanningService(db_session)
    plan = create_draft_plan(db_session, coach, athlete, service=svc)
    a = add_meso(db_session, coach, plan["id"], "Base", duration_days=14, service=svc)
    b = add_meso(db_session, coach, plan["id"], "Build", duration_days=14, service=svc)
    result, err, status = svc.reorder_mesocycles(coach, plan["id"], [b["id"], a["id"]])
    assert err is None
    assert status == 200
    names = [m["name"] for m in result["plan"]["mesocycles"]]
    assert names == ["Build", "Base"]
    assert [m["ordinal"] for m in result["plan"]["mesocycles"]] == [0, 1]


def test_reorder_rejects_unknown_or_missing_ids(db_session):
    coach, athlete = linked_coach_athlete(db_session)
    svc = PlanningService(db_session)
    plan = create_draft_plan(db_session, coach, athlete, service=svc)
    a = add_meso(db_session, coach, plan["id"], "Base", duration_days=7, service=svc)
    result, err, status = svc.reorder_mesocycles(coach, plan["id"], [a["id"], 999])
    assert result is None
    assert status == 400
    assert "ordered_ids" in err


def test_change_microcycle_duration_shifts_subsequent_periods(db_session):
    coach, athlete = linked_coach_athlete(db_session)
    svc = PlanningService(db_session)
    plan = create_draft_plan(db_session, coach, athlete, service=svc)
    meso = add_meso(db_session, coach, plan["id"], "Base", microcycle_count=3, service=svc)
    first = meso["microcycles"][0]
    second = meso["microcycles"][1]
    result, err, status = svc.update_microcycle(
        coach, first["id"], MicrocycleUpdateRequest(duration_days=10)
    )
    assert err is None
    assert status == 200
    assert result["microcycle"]["end_date"] == "2026-09-10"
    moved_ids = {m["id"] for m in result["moved"] if m["kind"] == "microcycle"}
    assert second["id"] in moved_ids
    tree, _, _ = svc.get_plan(coach, plan["id"])
    micros = tree["plan"]["mesocycles"][0]["microcycles"]
    assert micros[1]["start_date"] == "2026-09-11"


def test_get_plan_tree_query_count_is_bounded(db_session):
    coach, athlete = linked_coach_athlete(db_session)
    svc = PlanningService(db_session)
    plan = create_draft_plan(db_session, coach, athlete, service=svc)
    add_meso(db_session, coach, plan["id"], "Base", microcycle_count=4, service=svc)
    add_meso(db_session, coach, plan["id"], "Build", microcycle_count=4, service=svc)
    statements: list[str] = []

    def before_cursor(conn, cursor, statement, parameters, context, executemany):
        statements.append(statement)

    event.listen(db_session.bind, "before_cursor_execute", before_cursor)
    try:
        result, err, status = svc.get_plan(coach, plan["id"], "items")
    finally:
        event.remove(db_session.bind, "before_cursor_execute", before_cursor)

    assert err is None
    assert status == 200
    assert result["plan"]["mesocycles"][0]["lock_state"] is not None
    assert len(statements) <= 8


def test_overlapping_active_plan_rejected(db_session):
    coach, athlete = linked_coach_athlete(db_session)
    svc = PlanningService(db_session)
    first = create_draft_plan(db_session, coach, athlete, service=svc)
    _, err, status = svc.update_plan(
        coach, first["id"], TrainingPlanUpdateRequest(status=TrainingPlanStatus.active)
    )
    assert err is None
    second = create_draft_plan(
        db_session, coach, athlete, name="Clash", service=svc
    )
    result, err, status = svc.update_plan(
        coach, second["id"], TrainingPlanUpdateRequest(status=TrainingPlanStatus.active)
    )
    assert result is None
    assert status == 409
    assert err == "Athlete already has an active plan covering these dates"


def test_overlapping_draft_plan_allowed(db_session):
    coach, athlete = linked_coach_athlete(db_session)
    create_draft_plan(db_session, coach, athlete, name="Current")
    create_draft_plan(db_session, coach, athlete, name="Next draft")
    plans = db_session.scalars(select(TrainingPlan)).all()
    assert len(plans) == 2


def test_activating_a_draft_that_overlaps_an_active_plan_is_rejected(db_session):
    test_overlapping_active_plan_rejected(db_session)


def test_mesocycles_tile_the_plan_contiguously(db_session):
    coach, athlete = linked_coach_athlete(db_session)
    svc = PlanningService(db_session)
    plan = create_draft_plan(db_session, coach, athlete, service=svc)
    add_meso(db_session, coach, plan["id"], "Base", microcycle_count=2, service=svc)
    add_meso(db_session, coach, plan["id"], "Build", microcycle_count=2, service=svc)
    tree, _, _ = svc.get_plan(coach, plan["id"])
    mesos = tree["plan"]["mesocycles"]
    assert mesos[0]["start_date"] == tree["plan"]["start_date"]
    assert mesos[-1]["end_date"] == tree["plan"]["end_date"]
    prev_end = date.fromisoformat(mesos[0]["end_date"])
    nxt = date.fromisoformat(mesos[1]["start_date"])
    assert (nxt - prev_end).days == 1


def test_invalid_planning_timezone_rejected(db_session):
    coach, athlete = linked_coach_athlete(db_session)
    result, err, status = PlanningService(db_session).create_plan(
        coach,
        TrainingPlanCreateRequest(
            athlete_id=athlete.id,
            name="Bad tz",
            start_date=PLAN_START,
            planning_timezone="Not/AZone",
        ),
    )
    assert result is None
    assert status == 400
    assert "IANA" in err


def test_plan_with_only_mesocycles_is_valid(db_session):
    coach, athlete = linked_coach_athlete(db_session)
    svc = PlanningService(db_session)
    plan = create_draft_plan(db_session, coach, athlete, service=svc)
    meso = add_meso(db_session, coach, plan["id"], "Base", duration_days=21, service=svc)
    assert meso["microcycles"] == []
    tree, err, status = svc.get_plan(coach, plan["id"])
    assert err is None
    assert tree["plan"]["mesocycles"][0]["microcycles"] == []


def test_plan_with_no_children_is_valid(db_session):
    coach, athlete = linked_coach_athlete(db_session)
    plan = create_draft_plan(db_session, coach, athlete)
    tree, err, status = PlanningService(db_session).get_plan(coach, plan["id"])
    assert err is None
    assert status == 200
    assert tree["plan"]["id"] == plan["id"]
    assert tree["plan"]["mesocycles"] == []


def test_every_mutation_appends_exactly_one_change_log_row(db_session):
    coach, athlete = linked_coach_athlete(db_session)
    svc = PlanningService(db_session)
    before = log_count(db_session)
    plan = create_draft_plan(db_session, coach, athlete, service=svc)
    assert log_count(db_session, plan["id"]) - before == 1

    before = log_count(db_session, plan["id"])
    _, err, _ = svc.update_plan(coach, plan["id"], TrainingPlanUpdateRequest(name="Renamed"))
    assert err is None
    assert log_count(db_session, plan["id"]) - before == 1

    meso = add_meso(db_session, coach, plan["id"], "Base", duration_days=7, service=svc)
    before = log_count(db_session, plan["id"])
    _, err, _ = svc.update_mesocycle(
        coach, meso["id"], MesocycleUpdateRequest(intent="Aerobic")
    )
    assert err is None
    assert log_count(db_session, plan["id"]) - before == 1


def test_reflow_logs_one_entry_carrying_the_whole_diff(db_session):
    coach, athlete = linked_coach_athlete(db_session)
    svc = PlanningService(db_session)
    plan = create_draft_plan(db_session, coach, athlete, service=svc)
    meso = add_meso(db_session, coach, plan["id"], "Base", microcycle_count=3, service=svc)
    result, err, _ = svc.update_microcycle(
        coach, meso["microcycles"][0]["id"], MicrocycleUpdateRequest(duration_days=10)
    )
    assert err is None
    assert result["moved"]
    reflow_rows = list(
        db_session.scalars(
            select(PlanChangeLog)
            .where(
                PlanChangeLog.training_plan_id == plan["id"],
                PlanChangeLog.operation == "reflow",
            )
            .order_by(PlanChangeLog.id.desc())
        ).all()
    )
    assert len(reflow_rows) >= 1
    latest = reflow_rows[0]
    assert "moved" in (latest.after or {})
    assert latest.after["moved"] == result["moved"]


def test_change_log_is_readable(db_session):
    coach, athlete = linked_coach_athlete(db_session)
    svc = PlanningService(db_session)
    plan = create_draft_plan(db_session, coach, athlete, service=svc)
    result, err, status = svc.list_change_log(coach, plan["id"])
    assert err is None
    assert status == 200
    assert result["count"] >= 1
    assert result["changes"][0]["entity_type"] == "training_plan"


def test_create_plan_without_start_date_is_duration_mode(db_session):
    coach, athlete = linked_coach_athlete(db_session)
    svc = PlanningService(db_session)
    plan = create_draft_plan(db_session, coach, athlete, start=None, service=svc)
    assert plan["start_date"] is None
    assert plan["end_date"] is None
    meso = add_meso(
        db_session, coach, plan["id"], "Base", microcycle_count=2, service=svc
    )
    assert meso["start_date"] is None
    assert meso["microcycles"][0]["start_date"] is None
    assert meso["microcycles"][0]["duration_days"] == 7
    assert meso["microcycles"][1]["duration_days"] == 7


def test_adding_start_date_derives_dates_without_changing_structure(db_session):
    coach, athlete = linked_coach_athlete(db_session)
    svc = PlanningService(db_session)
    plan = create_draft_plan(db_session, coach, athlete, start=None, service=svc)
    add_meso(
        db_session,
        coach,
        plan["id"],
        "Base",
        microcycle_count=2,
        microcycle_duration_days=5,
        service=svc,
    )
    result, err, status = svc.update_plan(
        coach,
        plan["id"],
        TrainingPlanUpdateRequest(start_date=date(2026, 9, 1)),
    )
    assert err is None
    assert status == 200
    tree = result["plan"]
    assert tree["start_date"] == "2026-09-01"
    assert tree["end_date"] == "2026-09-10"
    micros = tree["mesocycles"][0]["microcycles"]
    assert micros[0]["duration_days"] == 5
    assert micros[0]["start_date"] == "2026-09-01"
    assert micros[1]["start_date"] == "2026-09-06"
    assert len(micros) == 2


def test_anchor_creates_gap_and_can_be_cleared(db_session):
    coach, athlete = linked_coach_athlete(db_session)
    svc = PlanningService(db_session)
    plan = create_draft_plan(db_session, coach, athlete, service=svc)
    add_meso(db_session, coach, plan["id"], "Base", microcycle_count=1, service=svc)
    add_meso(
        db_session,
        coach,
        plan["id"],
        "Threshold",
        microcycle_count=1,
        anchor_date=date(2026, 9, 15),
        service=svc,
    )
    tree, _, _ = svc.get_plan(coach, plan["id"])
    assert tree["plan"]["gaps"]
    assert tree["plan"]["gaps"][0]["days"] == 7
    threshold = tree["plan"]["mesocycles"][1]
    assert threshold["anchor_date"] == "2026-09-15"
    assert threshold["start_date"] == "2026-09-15"
    result, err, status = svc.update_mesocycle(
        coach, threshold["id"], MesocycleUpdateRequest(anchor_date=None)
    )
    assert err is None
    assert status == 200
    assert result["mesocycle"]["anchor_date"] is None
    assert result["gaps"] == []


def test_empty_block_is_valid(db_session):
    coach, athlete = linked_coach_athlete(db_session)
    meso = add_meso(
        db_session,
        coach,
        create_draft_plan(db_session, coach, athlete)["id"],
        "Base",
    )
    assert meso["microcycles"] == []
    assert meso["duration_days"] == 0
