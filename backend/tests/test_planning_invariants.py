"""Historical and future planning invariants."""
from __future__ import annotations

from datetime import date

from sqlalchemy import select

from src.modules.planning.enums import LockState, PlanOperation
from src.modules.planning.immutability import PERMISSION_MATRIX
from src.modules.planning.models import Microcycle, PlanChangeLog, PlanItem
from src.modules.planning.schemas import (
    MesocycleUpdateRequest,
    MicrocycleCreateRequest,
    MicrocycleUpdateRequest,
)
from src.modules.planning.service import PlanningService
from src.modules.training.models import Workout, WorkoutStatus
from src.modules.training.schemas import WorkoutUpdateRequest
from src.modules.training.service import TrainingService
from tests.conftest import (
    SIMPLE_STEPS,
    enroll_sport,
    linked_coach_athlete,
    make_sport,
    make_workout,
)
from tests.planning_helpers import (
    add_item,
    add_meso,
    create_draft_plan,
    freeze_today,
    micro_row_snapshot,
)


TODAY = date(2026, 9, 15)


def test_permission_matrix_outcomes_match_every_pair():
    for state in LockState:
        for operation in PlanOperation:
            rule = PERMISSION_MATRIX[(state, operation)]
            if state == LockState.locked and operation != PlanOperation.metadata:
                assert rule.allowed is False
            if state == LockState.locked and operation == PlanOperation.metadata:
                assert rule.allowed is True
                assert rule.reason_required is True
            if state == LockState.current and operation == PlanOperation.delete:
                assert rule.allowed is False
            if state == LockState.future:
                assert rule.allowed is True


def test_cannot_add_microcycle_to_locked_mesocycle(db_session):
    coach, athlete = linked_coach_athlete(db_session)
    svc = PlanningService(db_session)
    plan = create_draft_plan(
        db_session, coach, athlete, start=date(2026, 7, 1), service=svc
    )
    meso = add_meso(db_session, coach, plan["id"], "Base", microcycle_count=2, service=svc)
    result, err, status = svc.create_microcycle(
        coach, meso["id"], MicrocycleCreateRequest(duration_days=7)
    )
    assert result is None
    assert status == 409
    assert "not allowed on a completed training period" in err


def test_cannot_reorder_across_a_locked_boundary(db_session, monkeypatch):
    freeze_today(monkeypatch, TODAY)
    coach, athlete = linked_coach_athlete(db_session)
    svc = PlanningService(db_session)
    plan = create_draft_plan(db_session, coach, athlete, service=svc)
    meso = add_meso(db_session, coach, plan["id"], "Base", microcycle_count=4, service=svc)
    ids = [m["id"] for m in meso["microcycles"]]
    swapped = [ids[2], ids[0], ids[1], ids[3]]
    result, err, status = svc.reorder_microcycles(coach, meso["id"], swapped)
    assert result is None
    assert status == 409
    assert "locked boundary" in err


def test_cannot_change_locked_microcycle_duration(db_session, monkeypatch):
    freeze_today(monkeypatch, TODAY)
    coach, athlete = linked_coach_athlete(db_session)
    svc = PlanningService(db_session)
    plan = create_draft_plan(db_session, coach, athlete, service=svc)
    meso = add_meso(db_session, coach, plan["id"], "Base", microcycle_count=4, service=svc)
    w1 = meso["microcycles"][0]
    result, err, status = svc.update_microcycle(
        coach, w1["id"], MicrocycleUpdateRequest(duration_days=10, reason="please")
    )
    assert result is None
    assert status == 409


def test_can_rename_locked_period_with_a_reason(db_session, monkeypatch):
    freeze_today(monkeypatch, TODAY)
    coach, athlete = linked_coach_athlete(db_session)
    svc = PlanningService(db_session)
    plan = create_draft_plan(db_session, coach, athlete, service=svc)
    meso = add_meso(db_session, coach, plan["id"], "Base", microcycle_count=2, service=svc)
    result, err, status = svc.update_mesocycle(
        coach, meso["id"], MesocycleUpdateRequest(name="Base Development", reason="typo")
    )
    assert err is None
    assert status == 200
    assert result["mesocycle"]["name"] == "Base Development"


def test_renaming_locked_period_without_reason_is_400(db_session, monkeypatch):
    freeze_today(monkeypatch, TODAY)
    coach, athlete = linked_coach_athlete(db_session)
    svc = PlanningService(db_session)
    plan = create_draft_plan(db_session, coach, athlete, service=svc)
    meso = add_meso(db_session, coach, plan["id"], "Base", microcycle_count=2, service=svc)
    result, err, status = svc.update_mesocycle(
        coach, meso["id"], MesocycleUpdateRequest(name="Base Development")
    )
    assert result is None
    assert status == 400
    assert "reason is required" in err


def test_renaming_locked_period_leaves_dates_ordinals_and_items_untouched(
    db_session, monkeypatch
):
    freeze_today(monkeypatch, TODAY)
    coach, athlete = linked_coach_athlete(db_session)
    svc = PlanningService(db_session)
    plan = create_draft_plan(db_session, coach, athlete, service=svc)
    meso = add_meso(db_session, coach, plan["id"], "Base", microcycle_count=2, service=svc)
    w1_id = meso["microcycles"][0]["id"]
    before = micro_row_snapshot(db_session.get(Microcycle, w1_id))
    _, err, _ = svc.update_mesocycle(
        coach, meso["id"], MesocycleUpdateRequest(name="Base Development", reason="typo")
    )
    assert err is None
    after = micro_row_snapshot(db_session.get(Microcycle, w1_id))
    assert after == before


def test_renaming_locked_period_appends_change_log_row_with_locked_state_and_reason(
    db_session, monkeypatch
):
    freeze_today(monkeypatch, TODAY)
    coach, athlete = linked_coach_athlete(db_session)
    svc = PlanningService(db_session)
    plan = create_draft_plan(db_session, coach, athlete, service=svc)
    meso = add_meso(db_session, coach, plan["id"], "Base", microcycle_count=2, service=svc)
    svc.update_mesocycle(
        coach, meso["id"], MesocycleUpdateRequest(name="Base Development", reason="typo")
    )
    row = db_session.scalar(select(PlanChangeLog).order_by(PlanChangeLog.id.desc()))
    assert row.lock_state_at_change == "locked"
    assert row.reason == "typo"
    assert row.entity_type == "mesocycle"


def test_mixed_payload_on_locked_period_is_classified_as_the_stricter_operation(
    db_session, monkeypatch
):
    freeze_today(monkeypatch, TODAY)
    coach, athlete = linked_coach_athlete(db_session)
    svc = PlanningService(db_session)
    plan = create_draft_plan(db_session, coach, athlete, service=svc)
    meso = add_meso(db_session, coach, plan["id"], "Base", microcycle_count=2, service=svc)
    w1 = meso["microcycles"][0]
    result, err, status = svc.update_microcycle(
        coach,
        w1["id"],
        MicrocycleUpdateRequest(name="Week 1", duration_days=10, reason="typo"),
    )
    assert result is None
    assert status == 409


def test_cannot_delete_microcycle_containing_a_workout(db_session):
    coach, athlete = linked_coach_athlete(db_session)
    running = make_sport(db_session, "running")
    svc = PlanningService(db_session)
    plan = create_draft_plan(db_session, coach, athlete, service=svc)
    meso = add_meso(db_session, coach, plan["id"], "Base", microcycle_count=2, service=svc)
    micro = meso["microcycles"][0]
    item = add_item(db_session, coach, micro["id"], "Easy", service=svc)
    workout = make_workout(
        db_session, athlete, sport=running, scheduled_date=date(2026, 9, 2)
    )
    db_session.commit()
    _, err, status = svc.attach_workout(coach, item["id"], workout.id)
    assert err is None
    result, err, status = svc.delete_microcycle(coach, micro["id"])
    assert result is None
    assert status == 409
    assert "contains a workout" in err


def test_cannot_move_executed_workout_between_microcycles(db_session):
    coach, athlete = linked_coach_athlete(db_session)
    running = make_sport(db_session, "running")
    svc = PlanningService(db_session)
    plan = create_draft_plan(db_session, coach, athlete, service=svc)
    meso = add_meso(db_session, coach, plan["id"], "Base", microcycle_count=2, service=svc)
    a = add_item(db_session, coach, meso["microcycles"][0]["id"], "A", service=svc)
    b = add_item(db_session, coach, meso["microcycles"][1]["id"], "B", service=svc)
    workout = make_workout(
        db_session,
        athlete,
        sport=running,
        scheduled_date=date(2026, 9, 2),
        status=WorkoutStatus.completed,
    )
    db_session.commit()
    _, err, _ = svc.attach_workout(coach, a["id"], workout.id)
    assert err is None
    result, err, status = svc.attach_workout(coach, b["id"], workout.id)
    assert result is None
    assert status == 409
    assert "already part of a training cycle" in err
    result, err, status = svc.detach_workout(coach, a["id"])
    assert result is None
    assert status == 409


def test_base_ends_after_w3_scenario_leaves_w1_w2_byte_identical(db_session, monkeypatch):
    freeze_today(monkeypatch, TODAY)
    coach, athlete = linked_coach_athlete(db_session)
    svc = PlanningService(db_session)
    plan = create_draft_plan(db_session, coach, athlete, service=svc)
    base = add_meso(db_session, coach, plan["id"], "Base", microcycle_count=4, service=svc)
    add_meso(db_session, coach, plan["id"], "Build", microcycle_count=1, service=svc)
    tree, _, _ = svc.get_plan(coach, plan["id"])
    base_row = tree["plan"]["mesocycles"][0]
    build_row = tree["plan"]["mesocycles"][1]
    w1 = db_session.get(Microcycle, base_row["microcycles"][0]["id"])
    w2 = db_session.get(Microcycle, base_row["microcycles"][1]["id"])
    w4_id = base_row["microcycles"][3]["id"]
    before_w1 = micro_row_snapshot(w1)
    before_w2 = micro_row_snapshot(w2)
    result, err, status = svc.move_microcycle(
        coach, w4_id, build_row["id"], insert_at_ordinal=0
    )
    assert err is None, err
    assert status == 200
    db_session.expire_all()
    assert micro_row_snapshot(db_session.get(Microcycle, w1.id)) == before_w1
    assert micro_row_snapshot(db_session.get(Microcycle, w2.id)) == before_w2
    tree, _, _ = svc.get_plan(coach, plan["id"])
    base_after = tree["plan"]["mesocycles"][0]
    assert base_after["end_date"] == base_after["microcycles"][-1]["end_date"]
    assert len(base_after["microcycles"]) == 3
    assert tree["plan"]["mesocycles"][1]["microcycles"][0]["id"] == w4_id


def test_reflow_rolls_back_when_a_locked_date_would_change(db_session):
    coach, athlete = linked_coach_athlete(db_session)
    running = make_sport(db_session, "running")
    svc = PlanningService(db_session)
    plan = create_draft_plan(db_session, coach, athlete, service=svc)
    meso = add_meso(db_session, coach, plan["id"], "Base", microcycle_count=2, service=svc)
    later = meso["microcycles"][1]
    workout = make_workout(
        db_session,
        athlete,
        sport=running,
        scheduled_date=date(2026, 9, 10),
        status=WorkoutStatus.completed,
    )
    item = add_item(db_session, coach, later["id"], "Done", service=svc)
    _, err, _ = svc.attach_workout(coach, item["id"], workout.id)
    assert err is None
    later_before = micro_row_snapshot(db_session.get(Microcycle, later["id"]))
    first = meso["microcycles"][0]
    result, err, status = svc.update_microcycle(
        coach, first["id"], MicrocycleUpdateRequest(duration_days=10)
    )
    assert result is None
    assert status == 409
    assert "later period blocks this change" in err
    assert micro_row_snapshot(db_session.get(Microcycle, later["id"])) == later_before


def test_future_scheduled_workouts_shift_with_their_microcycle(db_session):
    coach, athlete = linked_coach_athlete(db_session)
    running = make_sport(db_session, "running")
    svc = PlanningService(db_session)
    plan = create_draft_plan(db_session, coach, athlete, service=svc)
    meso = add_meso(db_session, coach, plan["id"], "Base", microcycle_count=2, service=svc)
    second = meso["microcycles"][1]
    item = add_item(db_session, coach, second["id"], "Easy", service=svc)
    workout = make_workout(
        db_session, athlete, sport=running, scheduled_date=date(2026, 9, 10)
    )
    db_session.commit()
    _, err, _ = svc.attach_workout(coach, item["id"], workout.id)
    assert err is None
    first = meso["microcycles"][0]
    result, err, status = svc.update_microcycle(
        coach, first["id"], MicrocycleUpdateRequest(duration_days=10)
    )
    assert err is None
    db_session.refresh(workout)
    assert workout.scheduled_date == date(2026, 9, 13)


def test_executed_workout_is_never_rescheduled_and_is_reported_as_conflict(db_session):
    coach, athlete = linked_coach_athlete(db_session)
    running = make_sport(db_session, "running")
    svc = PlanningService(db_session)
    plan = create_draft_plan(db_session, coach, athlete, service=svc)
    meso = add_meso(db_session, coach, plan["id"], "Base", microcycle_count=1, service=svc)
    micro = meso["microcycles"][0]
    item = add_item(
        db_session,
        coach,
        micro["id"],
        "Long",
        placement_type="specific_date",
        placement_date=date(2026, 9, 7),
        service=svc,
    )
    workout = make_workout(
        db_session, athlete, sport=running, scheduled_date=date(2026, 9, 7)
    )
    db_session.commit()
    _, err, _ = svc.attach_workout(coach, item["id"], workout.id)
    assert err is None
    result, err, status = svc.update_microcycle(
        coach, micro["id"], MicrocycleUpdateRequest(duration_days=5)
    )
    assert err is None
    assert status == 200
    db_session.refresh(workout)
    assert workout.scheduled_date == date(2026, 9, 7)
    kinds = {c["kind"] for c in result["conflicts"]}
    assert "workout_not_rescheduled" in kinds or "placement_conflict" in kinds


def test_strict_true_turns_conflicts_into_409(db_session):
    coach, athlete = linked_coach_athlete(db_session)
    running = make_sport(db_session, "running")
    svc = PlanningService(db_session)
    plan = create_draft_plan(db_session, coach, athlete, service=svc)
    meso = add_meso(db_session, coach, plan["id"], "Base", microcycle_count=1, service=svc)
    micro = meso["microcycles"][0]
    item = add_item(
        db_session,
        coach,
        micro["id"],
        "Long",
        placement_type="specific_date",
        placement_date=date(2026, 9, 7),
        service=svc,
    )
    workout = make_workout(
        db_session, athlete, sport=running, scheduled_date=date(2026, 9, 7)
    )
    db_session.commit()
    svc.attach_workout(coach, item["id"], workout.id)
    result, err, status = svc.update_microcycle(
        coach, micro["id"], MicrocycleUpdateRequest(duration_days=5, strict=True)
    )
    assert result is None
    assert status == 409


def test_update_workout_rejects_date_outside_its_microcycle(db_session):
    coach, athlete = linked_coach_athlete(db_session)
    running = make_sport(db_session, "running")
    enroll_sport(db_session, athlete, running)
    svc = PlanningService(db_session)
    plan = create_draft_plan(db_session, coach, athlete, service=svc)
    meso = add_meso(db_session, coach, plan["id"], "Base", microcycle_count=1, service=svc)
    item = add_item(db_session, coach, meso["microcycles"][0]["id"], "Easy", service=svc)
    workout = make_workout(
        db_session, athlete, sport=running, scheduled_date=date(2026, 9, 2)
    )
    db_session.commit()
    _, err, _ = svc.attach_workout(coach, item["id"], workout.id)
    assert err is None
    result, err, status = TrainingService(db_session).update_workout(
        coach,
        workout.id,
        WorkoutUpdateRequest(
            scheduled_date=date(2026, 10, 1),
            sport_id=running.id,
            title=workout.title,
            steps=SIMPLE_STEPS,
        ),
    )
    assert result is None
    assert status == 409
    assert "planning API" in err


def test_update_workout_unaffected_for_workouts_with_no_plan_item(db_session):
    coach, athlete = linked_coach_athlete(db_session)
    running = make_sport(db_session, "running")
    enroll_sport(db_session, athlete, running)
    workout = make_workout(
        db_session, athlete, sport=running, scheduled_date=date(2026, 9, 2)
    )
    db_session.commit()
    result, err, status = TrainingService(db_session).update_workout(
        coach,
        workout.id,
        WorkoutUpdateRequest(
            scheduled_date=date(2026, 10, 1),
            sport_id=running.id,
            title=workout.title,
            steps=SIMPLE_STEPS,
        ),
    )
    assert err is None
    assert status == 200
    assert result["workout"]["scheduled_date"] == "2026-10-01"


def test_delete_scheduled_workout_reverts_slot_to_placeholder(db_session):
    coach, athlete = linked_coach_athlete(db_session)
    running = make_sport(db_session, "running")
    svc = PlanningService(db_session)
    plan = create_draft_plan(db_session, coach, athlete, service=svc)
    meso = add_meso(db_session, coach, plan["id"], "Base", microcycle_count=1, service=svc)
    item = add_item(
        db_session, coach, meso["microcycles"][0]["id"], "Easy", intent="aerobic", service=svc
    )
    workout = make_workout(
        db_session, athlete, sport=running, scheduled_date=date(2026, 9, 2)
    )
    db_session.commit()
    svc.attach_workout(coach, item["id"], workout.id)
    _, err, status = TrainingService(db_session).delete_workout(coach, workout.id)
    assert err is None
    slot = db_session.get(PlanItem, item["id"])
    assert slot.workout_id is None
    assert slot.title == "Easy"
    assert slot.intent == "aerobic"
    assert db_session.get(Workout, workout.id) is None
