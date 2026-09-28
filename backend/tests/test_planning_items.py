"""Plan items, placeholders, and workout integration."""
from __future__ import annotations

from datetime import date

from sqlalchemy import func, select

from src.modules.execution.models import WorkoutExecution
from src.modules.planning.models import PlanChangeLog, PlanItem
from src.modules.planning.schemas import PlanItemUpdateRequest
from src.modules.planning.service import PlanningService
from src.modules.training.activity_link import try_link_activity_to_workout
from src.modules.training.models import Workout, WorkoutStatus
from src.modules.training.service import TrainingService
from tests.conftest import (
    enroll_sport,
    linked_coach_athlete,
    make_activity,
    make_sport,
    make_user,
    make_workout,
)
from src.modules.identity.models import UserRoleEnum
from tests.planning_helpers import (
    add_item,
    add_meso,
    create_draft_plan,
    log_count,
    workout_create_payload,
)


def _tree(db, coach, athlete):
    svc = PlanningService(db)
    plan = create_draft_plan(db, coach, athlete, service=svc)
    meso = add_meso(db, coach, plan["id"], "Base", microcycle_count=1, service=svc)
    micro = meso["microcycles"][0]
    return svc, plan, meso, micro


def test_placeholder_created_without_workout_is_valid(db_session):
    coach, athlete = linked_coach_athlete(db_session)
    svc, plan, meso, micro = _tree(db_session, coach, athlete)
    item = add_item(db_session, coach, micro["id"], "Threshold", intent="sustain", service=svc)
    assert item["is_placeholder"] is True
    assert item["workout_id"] is None
    assert item["title"] == "Threshold"


def test_update_placeholder_title_and_intent_in_place(db_session):
    coach, athlete = linked_coach_athlete(db_session)
    svc, _, _, micro = _tree(db_session, coach, athlete)
    item = add_item(
        db_session, coach, micro["id"], "Threshold", intent="sustain", service=svc
    )
    before_count = db_session.scalar(select(func.count()).select_from(PlanItem)) or 0
    result, err, status = svc.update_item(
        coach,
        item["id"],
        PlanItemUpdateRequest(title="Tempo", intent="controlled"),
    )
    assert err is None
    assert status == 200
    updated = result["item"]
    assert updated["id"] == item["id"]
    assert updated["microcycle_id"] == item["microcycle_id"]
    assert updated["ordinal"] == item["ordinal"]
    assert updated["title"] == "Tempo"
    assert updated["intent"] == "controlled"
    assert updated["is_placeholder"] is True
    assert updated["workout_id"] is None
    assert updated["converted_at"] is None
    after_count = db_session.scalar(select(func.count()).select_from(PlanItem)) or 0
    assert after_count == before_count


def test_update_placeholder_does_not_create_workout_or_execution(db_session):
    coach, athlete = linked_coach_athlete(db_session)
    svc, _, _, micro = _tree(db_session, coach, athlete)
    item = add_item(db_session, coach, micro["id"], "Easy", service=svc)
    _, err, _ = svc.update_item(
        coach,
        item["id"],
        PlanItemUpdateRequest(title="Easy run", intent="keep it easy"),
    )
    assert err is None
    workouts = db_session.scalar(select(func.count()).select_from(Workout)) or 0
    executions = db_session.scalar(select(func.count()).select_from(WorkoutExecution)) or 0
    assert workouts == 0
    assert executions == 0


def test_update_placeholder_clears_intent(db_session):
    coach, athlete = linked_coach_athlete(db_session)
    svc, _, _, micro = _tree(db_session, coach, athlete)
    item = add_item(
        db_session, coach, micro["id"], "Threshold", intent="sustain", service=svc
    )
    result, err, status = svc.update_item(
        coach,
        item["id"],
        PlanItemUpdateRequest(intent=None),
    )
    assert err is None
    assert status == 200
    assert result["item"]["intent"] is None
    assert result["item"]["is_placeholder"] is True
    assert result["item"]["id"] == item["id"]


def test_update_placeholder_then_attach_uses_same_item(db_session):
    coach, athlete = linked_coach_athlete(db_session)
    running = make_sport(db_session, "running")
    svc, _, _, micro = _tree(db_session, coach, athlete)
    item = add_item(
        db_session, coach, micro["id"], "Threshold", intent="sustain", service=svc
    )
    _, err, _ = svc.update_item(
        coach,
        item["id"],
        PlanItemUpdateRequest(title="Tempo", intent="controlled"),
    )
    assert err is None
    workout = make_workout(
        db_session, athlete, sport=running, scheduled_date=date(2026, 9, 2), title="W"
    )
    db_session.commit()
    result, err, _ = svc.attach_workout(coach, item["id"], workout.id)
    assert err is None
    converted = result["item"]
    assert converted["id"] == item["id"]
    assert converted["ordinal"] == item["ordinal"]
    assert converted["title"] == "Tempo"
    assert converted["intent"] == "controlled"
    assert converted["is_placeholder"] is False
    assert converted["workout_id"] == workout.id


def test_update_converted_item_title_does_not_detach_workout(db_session):
    coach, athlete = linked_coach_athlete(db_session)
    running = make_sport(db_session, "running")
    svc, _, _, micro = _tree(db_session, coach, athlete)
    item = add_item(db_session, coach, micro["id"], "Easy", service=svc)
    workout = make_workout(
        db_session, athlete, sport=running, scheduled_date=date(2026, 9, 2)
    )
    db_session.commit()
    _, err, _ = svc.attach_workout(coach, item["id"], workout.id)
    assert err is None
    result, err, status = svc.update_item(
        coach,
        item["id"],
        PlanItemUpdateRequest(title="Renamed"),
    )
    assert err is None
    assert status == 200
    assert result["item"]["title"] == "Renamed"
    assert result["item"]["workout_id"] == workout.id
    assert result["item"]["is_placeholder"] is False


def test_conversion_preserves_ordinal_title_and_intent(db_session):
    coach, athlete = linked_coach_athlete(db_session)
    running = make_sport(db_session, "running")
    svc, plan, meso, micro = _tree(db_session, coach, athlete)
    item = add_item(
        db_session, coach, micro["id"], "Threshold", intent="sustain", service=svc
    )
    workout = make_workout(
        db_session, athlete, sport=running, scheduled_date=date(2026, 9, 2), title="W"
    )
    db_session.commit()
    result, err, _ = svc.attach_workout(coach, item["id"], workout.id)
    assert err is None
    converted = result["item"]
    assert converted["ordinal"] == item["ordinal"]
    assert converted["title"] == "Threshold"
    assert converted["intent"] == "sustain"
    assert converted["is_placeholder"] is False
    assert converted["workout_id"] == workout.id


def test_converted_item_records_converted_at_and_by(db_session):
    coach, athlete = linked_coach_athlete(db_session)
    running = make_sport(db_session, "running")
    svc, _, _, micro = _tree(db_session, coach, athlete)
    item = add_item(db_session, coach, micro["id"], "Easy", service=svc)
    workout = make_workout(
        db_session, athlete, sport=running, scheduled_date=date(2026, 9, 2)
    )
    db_session.commit()
    result, err, _ = svc.attach_workout(coach, item["id"], workout.id)
    assert err is None
    assert result["item"]["converted_at"] is not None
    assert result["item"]["converted_by_id"] == coach.id


def test_placeholder_produces_no_workout_execution(db_session):
    coach, athlete = linked_coach_athlete(db_session)
    svc, _, _, micro = _tree(db_session, coach, athlete)
    add_item(db_session, coach, micro["id"], "A", service=svc)
    add_item(db_session, coach, micro["id"], "B", service=svc)
    count = db_session.scalar(select(func.count()).select_from(WorkoutExecution))
    assert count == 0
    workouts = db_session.scalar(select(func.count()).select_from(Workout))
    assert workouts == 0


def test_placeholder_is_invisible_to_auto_link(db_session):
    coach, athlete = linked_coach_athlete(db_session)
    running = make_sport(db_session, "running")
    svc, _, _, micro = _tree(db_session, coach, athlete)
    add_item(db_session, coach, micro["id"], "Placeholder", service=svc)
    activity = make_activity(
        db_session, athlete, sport=running, activity_date=date(2026, 9, 2)
    )
    db_session.commit()
    linked = try_link_activity_to_workout(
        db_session, athlete.id, activity.id, date(2026, 9, 2), "running", running.id
    )
    assert linked is None


def test_placeholder_absent_from_training_calendar(db_session):
    coach, athlete = linked_coach_athlete(db_session)
    svc, _, _, micro = _tree(db_session, coach, athlete)
    add_item(db_session, coach, micro["id"], "Placeholder", service=svc)
    result, err, status = TrainingService(db_session).get_calendar(
        athlete, date(2026, 9, 1), date(2026, 9, 7)
    )
    assert err is None
    assert result["workouts"] == []


def test_attach_rejects_workout_of_another_athlete(db_session):
    coach, athlete = linked_coach_athlete(db_session)
    other = make_user(db_session, role=UserRoleEnum.athlete, username="other-athlete-attach")
    running = make_sport(db_session, "running")
    svc, _, _, micro = _tree(db_session, coach, athlete)
    item = add_item(db_session, coach, micro["id"], "Easy", service=svc)
    workout = make_workout(
        db_session, other, sport=running, scheduled_date=date(2026, 9, 2)
    )
    db_session.commit()
    result, err, status = svc.attach_workout(coach, item["id"], workout.id)
    assert result is None
    assert status == 404


def test_attach_rejects_workout_already_in_a_slot(db_session):
    coach, athlete = linked_coach_athlete(db_session)
    running = make_sport(db_session, "running")
    svc, _, _, micro = _tree(db_session, coach, athlete)
    a = add_item(db_session, coach, micro["id"], "A", service=svc)
    b = add_item(db_session, coach, micro["id"], "B", service=svc)
    workout = make_workout(
        db_session, athlete, sport=running, scheduled_date=date(2026, 9, 2)
    )
    db_session.commit()
    _, err, _ = svc.attach_workout(coach, a["id"], workout.id)
    assert err is None
    result, err, status = svc.attach_workout(coach, b["id"], workout.id)
    assert result is None
    assert status == 409
    assert "already part of a training cycle" in err


def test_detach_rejects_executed_workout(db_session):
    coach, athlete = linked_coach_athlete(db_session)
    running = make_sport(db_session, "running")
    svc, _, _, micro = _tree(db_session, coach, athlete)
    item = add_item(db_session, coach, micro["id"], "Easy", service=svc)
    workout = make_workout(
        db_session,
        athlete,
        sport=running,
        scheduled_date=date(2026, 9, 2),
        status=WorkoutStatus.completed,
    )
    db_session.commit()
    _, err, _ = svc.attach_workout(coach, item["id"], workout.id)
    assert err is None
    result, err, status = svc.detach_workout(coach, item["id"])
    assert result is None
    assert status == 409


def test_detach_reverts_slot_to_placeholder_keeping_title(db_session):
    coach, athlete = linked_coach_athlete(db_session)
    running = make_sport(db_session, "running")
    svc, _, _, micro = _tree(db_session, coach, athlete)
    item = add_item(
        db_session, coach, micro["id"], "Easy", intent="keep me", service=svc
    )
    workout = make_workout(
        db_session, athlete, sport=running, scheduled_date=date(2026, 9, 2)
    )
    db_session.commit()
    svc.attach_workout(coach, item["id"], workout.id)
    result, err, _ = svc.detach_workout(coach, item["id"])
    assert err is None
    assert result["item"]["is_placeholder"] is True
    assert result["item"]["title"] == "Easy"
    assert result["item"]["intent"] == "keep me"
    assert result["item"]["workout_id"] is None


def test_builder_context_includes_plan_mesocycle_microcycle_and_suggestions(db_session):
    coach, athlete = linked_coach_athlete(db_session)
    running = make_sport(db_session, "running")
    svc, plan, meso, micro = _tree(db_session, coach, athlete)
    item = add_item(
        db_session,
        coach,
        micro["id"],
        "Threshold",
        intent="tempo",
        placement_type="specific_date",
        placement_date=date(2026, 9, 3),
        service=svc,
    )
    result, err, status = svc.get_builder_context(coach, item["id"])
    assert err is None
    assert result["training_plan"]["id"] == plan["id"]
    assert result["mesocycle"]["id"] == meso["id"]
    assert result["microcycle"]["id"] == micro["id"]
    assert result["suggested"]["scheduled_date"] == "2026-09-03"
    assert result["title"] == "Threshold"
    assert result["intent"] == "tempo"
    assert running.id or True


def test_create_workout_for_item_is_atomic(db_session):
    coach, athlete = linked_coach_athlete(db_session)
    running = make_sport(db_session, "running")
    enroll_sport(db_session, athlete, running)
    svc, _, _, micro = _tree(db_session, coach, athlete)
    item = add_item(db_session, coach, micro["id"], "Easy", service=svc)
    before = db_session.scalar(select(func.count()).select_from(Workout)) or 0
    result, err, status = svc.create_workout_for_item(
        coach,
        item["id"],
        workout_create_payload(athlete.id, running.id, date(2026, 12, 1), "Out of range"),
    )
    assert result is None
    assert status == 400
    after = db_session.scalar(select(func.count()).select_from(Workout)) or 0
    assert after == before
    slot = db_session.get(PlanItem, item["id"])
    assert slot.workout_id is None


def test_attach_and_detach_are_recorded_in_the_change_log(db_session):
    coach, athlete = linked_coach_athlete(db_session)
    running = make_sport(db_session, "running")
    svc, plan, _, micro = _tree(db_session, coach, athlete)
    item = add_item(db_session, coach, micro["id"], "Easy", service=svc)
    workout = make_workout(
        db_session, athlete, sport=running, scheduled_date=date(2026, 9, 2)
    )
    db_session.commit()
    svc.attach_workout(coach, item["id"], workout.id)
    svc.detach_workout(coach, item["id"])
    ops = {
        r.operation
        for r in db_session.scalars(
            select(PlanChangeLog).where(PlanChangeLog.training_plan_id == plan["id"])
        )
    }
    assert "attach_workout" in ops
    assert "detach_workout" in ops


def test_change_log_row_survives_deletion_of_its_plan_item(db_session):
    coach, athlete = linked_coach_athlete(db_session)
    svc, plan, _, micro = _tree(db_session, coach, athlete)
    item = add_item(db_session, coach, micro["id"], "Easy", service=svc)
    item_id = item["id"]
    _, err, _ = svc.delete_item(coach, item_id)
    assert err is None
    row = db_session.scalar(
        select(PlanChangeLog).where(
            PlanChangeLog.entity_type == "plan_item",
            PlanChangeLog.entity_id == item_id,
            PlanChangeLog.operation == "delete",
        )
    )
    assert row is not None
    assert db_session.get(PlanItem, item_id) is None
