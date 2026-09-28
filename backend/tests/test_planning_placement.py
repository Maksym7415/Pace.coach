"""Calendar date resolution for PlanItem placement."""
from __future__ import annotations

from datetime import date

from src.modules.planning.enums import PlacementType
from src.modules.planning.schemas import (
    MicrocycleUpdateRequest,
    PlanItemCreateRequest,
    PlanItemUpdateRequest,
    TrainingPlanUpdateRequest,
)
from src.modules.planning.service import PlanningService
from tests.conftest import linked_coach_athlete, make_sport, make_workout
from tests.planning_helpers import add_item, add_meso, create_draft_plan


def _dated_tree(db, coach, athlete, *, microcycle_count=1, duration_days=7):
    svc = PlanningService(db)
    plan = create_draft_plan(db, coach, athlete, service=svc)
    meso = add_meso(
        db,
        coach,
        plan["id"],
        "Base",
        microcycle_count=microcycle_count,
        microcycle_duration_days=duration_days,
        service=svc,
    )
    micro = meso["microcycles"][0]
    return svc, plan, meso, micro


def test_unplaced_item_has_null_placement(db_session):
    coach, athlete = linked_coach_athlete(db_session)
    svc, _, _, micro = _dated_tree(db_session, coach, athlete)
    item = add_item(db_session, coach, micro["id"], "Easy", service=svc)
    assert item["placement"] is None
    assert item["is_placeholder"] is True


def test_relative_day_resolves_to_start_plus_offset(db_session):
    coach, athlete = linked_coach_athlete(db_session)
    svc = PlanningService(db_session)
    # Sep 28 – Oct 4: relativeDay(2) → Sep 29
    plan = create_draft_plan(
        db_session, coach, athlete, start=date(2026, 9, 28), service=svc
    )
    meso = add_meso(db_session, coach, plan["id"], "Base", microcycle_count=1, service=svc)
    micro = meso["microcycles"][0]
    assert micro["start_date"] == "2026-09-28"
    assert micro["end_date"] == "2026-10-04"
    item = add_item(
        db_session,
        coach,
        micro["id"],
        "Threshold",
        placement_type="relative_day",
        placement_day=2,
        service=svc,
    )
    assert item["placement"] == {
        "type": "relative_day",
        "day": 2,
        "resolved_date": "2026-09-29",
        "conflict": False,
    }


def test_relative_day_1_resolves_to_microcycle_start(db_session):
    coach, athlete = linked_coach_athlete(db_session)
    svc, _, _, micro = _dated_tree(db_session, coach, athlete)
    item = add_item(
        db_session,
        coach,
        micro["id"],
        "Easy",
        placement_type="relative_day",
        placement_day=1,
        service=svc,
    )
    assert item["placement"]["resolved_date"] == micro["start_date"]
    assert item["placement"]["conflict"] is False


def test_relative_day_undated_micro_null_resolved_date(db_session):
    coach, athlete = linked_coach_athlete(db_session)
    svc = PlanningService(db_session)
    plan = create_draft_plan(db_session, coach, athlete, start=None, service=svc)
    meso = add_meso(db_session, coach, plan["id"], "Base", microcycle_count=1, service=svc)
    micro = meso["microcycles"][0]
    assert micro["start_date"] is None
    item = add_item(
        db_session,
        coach,
        micro["id"],
        "Easy",
        placement_type="relative_day",
        placement_day=2,
        service=svc,
    )
    assert item["placement"] == {
        "type": "relative_day",
        "day": 2,
        "resolved_date": None,
        "conflict": False,
    }


def test_specific_date_resolves_to_stored_date(db_session):
    coach, athlete = linked_coach_athlete(db_session)
    svc, _, _, micro = _dated_tree(db_session, coach, athlete)
    item = add_item(
        db_session,
        coach,
        micro["id"],
        "Tempo",
        placement_type="specific_date",
        placement_date=date(2026, 9, 3),
        service=svc,
    )
    assert item["placement"] == {
        "type": "specific_date",
        "date": "2026-09-03",
        "resolved_date": "2026-09-03",
        "conflict": False,
    }


def test_moved_micro_relative_day_follows_new_start(db_session):
    coach, athlete = linked_coach_athlete(db_session)
    # Two weeks so end_date stays after a modest start shift.
    svc, plan, _, micro = _dated_tree(db_session, coach, athlete, microcycle_count=2)
    item = add_item(
        db_session,
        coach,
        micro["id"],
        "Easy",
        placement_type="relative_day",
        placement_day=2,
        service=svc,
    )
    assert item["placement"]["resolved_date"] == "2026-09-02"
    result, err, status = svc.update_plan(
        coach,
        plan["id"],
        TrainingPlanUpdateRequest(start_date=date(2026, 9, 8)),
    )
    assert err is None, err
    assert status == 200
    tree = result["plan"]
    moved_micro = tree["mesocycles"][0]["microcycles"][0]
    assert moved_micro["start_date"] == "2026-09-08"
    placed = next(i for i in moved_micro["items"] if i["id"] == item["id"])
    assert placed["placement"]["type"] == "relative_day"
    assert placed["placement"]["day"] == 2
    assert placed["placement"]["resolved_date"] == "2026-09-09"
    assert placed["placement"]["conflict"] is False


def test_moved_micro_specific_date_stays_no_conflict(db_session):
    coach, athlete = linked_coach_athlete(db_session)
    svc, plan, _, micro = _dated_tree(db_session, coach, athlete, microcycle_count=2)
    # Place on Sep 3 (day 3 of first week Sep 1–7). Shift plan by +1 day → Sep 2–8.
    item = add_item(
        db_session,
        coach,
        micro["id"],
        "Pinned",
        placement_type="specific_date",
        placement_date=date(2026, 9, 3),
        service=svc,
    )
    result, err, status = svc.update_plan(
        coach,
        plan["id"],
        TrainingPlanUpdateRequest(start_date=date(2026, 9, 2)),
    )
    assert err is None
    assert status == 200
    tree = result["plan"]
    moved_micro = tree["mesocycles"][0]["microcycles"][0]
    assert moved_micro["start_date"] == "2026-09-02"
    assert moved_micro["end_date"] == "2026-09-08"
    placed = next(i for i in moved_micro["items"] if i["id"] == item["id"])
    assert placed["placement"]["date"] == "2026-09-03"
    assert placed["placement"]["resolved_date"] == "2026-09-03"
    assert placed["placement"]["conflict"] is False


def test_moved_micro_specific_date_outside_range_emits_conflict(db_session):
    coach, athlete = linked_coach_athlete(db_session)
    svc, _, _, micro = _dated_tree(db_session, coach, athlete)
    item = add_item(
        db_session,
        coach,
        micro["id"],
        "Long",
        placement_type="specific_date",
        placement_date=date(2026, 9, 7),
        service=svc,
    )
    result, err, status = svc.update_microcycle(
        coach, micro["id"], MicrocycleUpdateRequest(duration_days=5)
    )
    assert err is None
    assert status == 200
    kinds = {c["kind"] for c in result["conflicts"]}
    assert "placement_conflict" in kinds
    conflict = next(c for c in result["conflicts"] if c["kind"] == "placement_conflict")
    assert conflict["plan_item_id"] == item["id"]
    assert conflict["placement_date"] == "2026-09-07"
    # Item still carries the pinned date with conflict=True
    from src.modules.planning.models import PlanItem

    row = db_session.get(PlanItem, item["id"])
    assert row.placement_date == date(2026, 9, 7)
    assert row.placement_type == PlacementType.specific_date
    payload = svc._item_to_dict(svc._load_item(item["id"]))
    assert payload["placement"]["conflict"] is True
    assert payload["placement"]["resolved_date"] == "2026-09-07"


def test_custom_duration_micro_relative_day_last_day(db_session):
    coach, athlete = linked_coach_athlete(db_session)
    svc, _, _, micro = _dated_tree(db_session, coach, athlete, duration_days=5)
    assert micro["duration_days"] == 5
    assert micro["end_date"] == "2026-09-05"
    item = add_item(
        db_session,
        coach,
        micro["id"],
        "Last day",
        placement_type="relative_day",
        placement_day=5,
        service=svc,
    )
    assert item["placement"]["resolved_date"] == "2026-09-05"
    assert item["placement"]["conflict"] is False


def test_relative_day_exceeds_duration_rejected(db_session):
    coach, athlete = linked_coach_athlete(db_session)
    svc, _, _, micro = _dated_tree(db_session, coach, athlete, duration_days=5)
    result, err, status = svc.create_item(
        coach,
        micro["id"],
        PlanItemCreateRequest(
            title="Too far",
            placement_type=PlacementType.relative_day,
            placement_day=6,
        ),
    )
    assert result is None
    assert status == 400
    assert "placement_day must be between 1 and 5" in err


def test_specific_date_outside_micro_range_rejected_at_create(db_session):
    coach, athlete = linked_coach_athlete(db_session)
    svc, _, _, micro = _dated_tree(db_session, coach, athlete)
    result, err, status = svc.create_item(
        coach,
        micro["id"],
        PlanItemCreateRequest(
            title="Out",
            placement_type=PlacementType.specific_date,
            placement_date=date(2026, 9, 10),
        ),
    )
    assert result is None
    assert status == 400
    assert "placement_date must fall inside the microcycle" in err


def test_duration_mode_plan_relative_day_has_null_resolved(db_session):
    coach, athlete = linked_coach_athlete(db_session)
    svc = PlanningService(db_session)
    plan = create_draft_plan(db_session, coach, athlete, start=None, service=svc)
    meso = add_meso(
        db_session,
        coach,
        plan["id"],
        "Base",
        microcycle_count=1,
        microcycle_duration_days=7,
        service=svc,
    )
    micro = meso["microcycles"][0]
    item = add_item(
        db_session,
        coach,
        micro["id"],
        "Easy",
        placement_type="relative_day",
        placement_day=3,
        service=svc,
    )
    assert item["placement"]["resolved_date"] is None
    assert item["placement"]["conflict"] is False
    # Adding a start date later should resolve without changing placement_day
    result, err, status = svc.update_plan(
        coach,
        plan["id"],
        TrainingPlanUpdateRequest(start_date=date(2026, 9, 28)),
    )
    assert err is None
    assert status == 200
    placed = result["plan"]["mesocycles"][0]["microcycles"][0]["items"][0]
    assert placed["id"] == item["id"]
    assert placed["placement"]["day"] == 3
    assert placed["placement"]["resolved_date"] == "2026-09-30"
    assert placed["placement"]["conflict"] is False


def test_placement_distinguishes_placeholder_and_workout(db_session):
    coach, athlete = linked_coach_athlete(db_session)
    running = make_sport(db_session, "running")
    svc, _, _, micro = _dated_tree(db_session, coach, athlete)
    placeholder = add_item(
        db_session,
        coach,
        micro["id"],
        "Placeholder",
        placement_type="relative_day",
        placement_day=2,
        service=svc,
    )
    converted = add_item(
        db_session,
        coach,
        micro["id"],
        "Converted",
        placement_type="specific_date",
        placement_date=date(2026, 9, 3),
        service=svc,
    )
    workout = make_workout(
        db_session, athlete, sport=running, scheduled_date=date(2026, 9, 3)
    )
    db_session.commit()
    result, err, _ = svc.attach_workout(coach, converted["id"], workout.id)
    assert err is None
    assert placeholder["is_placeholder"] is True
    assert placeholder["workout_id"] is None
    assert placeholder["placement"]["type"] == "relative_day"
    assert result["item"]["is_placeholder"] is False
    assert result["item"]["workout_id"] == workout.id
    assert result["item"]["placement"]["type"] == "specific_date"
    assert result["item"]["placement"]["resolved_date"] == "2026-09-03"


def test_clear_placement_via_update(db_session):
    coach, athlete = linked_coach_athlete(db_session)
    svc, _, _, micro = _dated_tree(db_session, coach, athlete)
    item = add_item(
        db_session,
        coach,
        micro["id"],
        "Easy",
        placement_type="relative_day",
        placement_day=2,
        service=svc,
    )
    result, err, status = svc.update_item(
        coach,
        item["id"],
        PlanItemUpdateRequest(placement_type=None),
    )
    assert err is None
    assert status == 200
    assert result["item"]["placement"] is None
