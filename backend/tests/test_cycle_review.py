"""Cycle Review: append-only analysis and versioned coach reviews."""
from __future__ import annotations

from datetime import date

from sqlalchemy import select

from src.api.app import create_app
from src.modules.planning.models import CycleCoachReview, CycleSystemAnalysis, Mesocycle
from src.modules.planning.schemas import CoachReviewCreateRequest, CoachReviewUpdateRequest
from src.modules.planning.service import PlanningService
from tests.conftest import linked_coach_athlete, make_sport, make_workout
from tests.planning_helpers import add_item, add_meso, create_draft_plan, freeze_today


def _meso(db, coach, athlete):
    svc = PlanningService(db)
    plan = create_draft_plan(db, coach, athlete, service=svc)
    meso = add_meso(db, coach, plan["id"], "Base", microcycle_count=2, service=svc)
    return svc, plan, meso


def test_generate_analysis_is_deterministic_for_same_inputs(db_session):
    from src.modules.planning.analysis import generate_mesocycle_analysis

    coach, athlete = linked_coach_athlete(db_session)
    svc, plan, meso = _meso(db_session, coach, athlete)
    row = db_session.get(Mesocycle, meso["id"])
    cutoff = date(2026, 9, 14)
    a = generate_mesocycle_analysis(db_session, row, cutoff)
    b = generate_mesocycle_analysis(db_session, row, cutoff)
    assert a == b


def test_generate_analysis_is_idempotent_per_cutoff(db_session, monkeypatch):
    freeze_today(monkeypatch, date(2026, 9, 15))
    coach, athlete = linked_coach_athlete(db_session)
    svc, plan, meso = _meso(db_session, coach, athlete)
    first, err, status = svc.generate_system_analysis(coach, meso["id"])
    assert err is None
    assert status == 201
    second, err, status = svc.generate_system_analysis(coach, meso["id"])
    assert err is None
    assert status == 200
    assert second["system_analysis"]["id"] == first["system_analysis"]["id"]
    count = len(list(db_session.scalars(select(CycleSystemAnalysis))))
    assert count == 1


def test_regeneration_after_new_data_creates_a_second_row(db_session, monkeypatch):
    freeze_today(monkeypatch, date(2026, 8, 18))
    coach, athlete = linked_coach_athlete(db_session)
    running = make_sport(db_session, "running")
    svc, plan, meso = _meso(db_session, coach, athlete)
    first, err, _ = svc.generate_system_analysis(coach, meso["id"])
    assert err is None
    item = add_item(db_session, coach, meso["microcycles"][0]["id"], "Easy", service=svc)
    workout = make_workout(
        db_session, athlete, sport=running, scheduled_date=date(2026, 9, 2)
    )
    db_session.commit()
    _, aerr, _ = svc.attach_workout(coach, item["id"], workout.id)
    assert aerr is None
    freeze_today(monkeypatch, date(2026, 8, 19))
    second, err, status = svc.generate_system_analysis(coach, meso["id"])
    assert err is None
    assert status == 201
    assert second["system_analysis"]["id"] != first["system_analysis"]["id"]
    rows = list(db_session.scalars(select(CycleSystemAnalysis)))
    assert len(rows) == 2
    assert db_session.get(CycleSystemAnalysis, first["system_analysis"]["id"]) is not None


def test_analysis_has_no_update_or_delete_route():
    app = create_app()
    analysis_paths = {
        path: methods
        for path, methods in app.openapi()["paths"].items()
        if "system-analysis" in path
    }
    assert analysis_paths
    for methods in analysis_paths.values():
        assert set(methods).isdisjoint({"put", "patch", "delete"})


def test_use_system_analysis_copies_text_into_a_new_review(db_session, monkeypatch):
    freeze_today(monkeypatch, date(2026, 9, 15))
    coach, athlete = linked_coach_athlete(db_session)
    svc, plan, meso = _meso(db_session, coach, athlete)
    gen, err, _ = svc.generate_system_analysis(coach, meso["id"])
    assert err is None
    summary = gen["system_analysis"]["summary"]
    result, err, status = svc.create_coach_review(
        coach,
        meso["id"],
        CoachReviewCreateRequest(source_analysis_id=gen["system_analysis"]["id"]),
    )
    assert err is None
    assert status == 201
    assert result["coach_review"]["content"] == summary
    assert result["coach_review"]["source_analysis_id"] == gen["system_analysis"]["id"]


def test_editing_review_leaves_analysis_byte_identical(db_session, monkeypatch):
    freeze_today(monkeypatch, date(2026, 9, 15))
    coach, athlete = linked_coach_athlete(db_session)
    svc, plan, meso = _meso(db_session, coach, athlete)
    gen, err, _ = svc.generate_system_analysis(coach, meso["id"])
    analysis_id = gen["system_analysis"]["id"]
    before = db_session.get(CycleSystemAnalysis, analysis_id)
    snapshot = {
        "summary": before.summary,
        "metrics": before.metrics,
        "source_refs": before.source_refs,
        "generator": before.generator,
        "generator_version": before.generator_version,
        "data_cutoff_date": before.data_cutoff_date,
    }
    review, err, _ = svc.create_coach_review(
        coach,
        meso["id"],
        CoachReviewCreateRequest(source_analysis_id=analysis_id),
    )
    assert err is None
    _, err, _ = svc.update_coach_review(
        coach,
        review["coach_review"]["id"],
        CoachReviewUpdateRequest(content="Coach rewrite"),
    )
    assert err is None
    after = db_session.get(CycleSystemAnalysis, analysis_id)
    assert after.summary == snapshot["summary"]
    assert after.metrics == snapshot["metrics"]
    assert after.source_refs == snapshot["source_refs"]
    assert after.generator == snapshot["generator"]
    assert after.generator_version == snapshot["generator_version"]
    assert after.data_cutoff_date == snapshot["data_cutoff_date"]


def test_editing_approved_review_returns_409(db_session, monkeypatch):
    freeze_today(monkeypatch, date(2026, 9, 15))
    coach, athlete = linked_coach_athlete(db_session)
    svc, plan, meso = _meso(db_session, coach, athlete)
    created, err, _ = svc.create_coach_review(
        coach, meso["id"], CoachReviewCreateRequest(content="Notes")
    )
    svc.approve_coach_review(coach, created["coach_review"]["id"])
    result, err, status = svc.update_coach_review(
        coach,
        created["coach_review"]["id"],
        CoachReviewUpdateRequest(content="Nope"),
    )
    assert result is None
    assert status == 409
    assert "new version" in err


def test_new_version_supersedes_previous_on_approval(db_session, monkeypatch):
    freeze_today(monkeypatch, date(2026, 9, 15))
    coach, athlete = linked_coach_athlete(db_session)
    svc, plan, meso = _meso(db_session, coach, athlete)
    first, err, _ = svc.create_coach_review(
        coach, meso["id"], CoachReviewCreateRequest(content="v1")
    )
    svc.approve_coach_review(coach, first["coach_review"]["id"])
    successor, err, _ = svc.new_coach_review_version(coach, first["coach_review"]["id"])
    assert err is None
    svc.update_coach_review(
        coach,
        successor["coach_review"]["id"],
        CoachReviewUpdateRequest(content="v2"),
    )
    _, err, _ = svc.approve_coach_review(coach, successor["coach_review"]["id"])
    assert err is None
    old = db_session.get(CycleCoachReview, first["coach_review"]["id"])
    new = db_session.get(CycleCoachReview, successor["coach_review"]["id"])
    assert old.superseded_by_id == new.id
    assert new.superseded_by_id is None
    assert new.version == old.version + 1


def test_current_review_is_highest_version_with_null_superseded_by(db_session, monkeypatch):
    freeze_today(monkeypatch, date(2026, 9, 15))
    coach, athlete = linked_coach_athlete(db_session)
    svc, plan, meso = _meso(db_session, coach, athlete)
    first, _, _ = svc.create_coach_review(
        coach, meso["id"], CoachReviewCreateRequest(content="v1")
    )
    svc.approve_coach_review(coach, first["coach_review"]["id"])
    successor, _, _ = svc.new_coach_review_version(coach, first["coach_review"]["id"])
    svc.approve_coach_review(coach, successor["coach_review"]["id"])
    result, err, _ = svc.get_coach_review(coach, meso["id"])
    assert err is None
    assert result["coach_review"]["id"] == successor["coach_review"]["id"]
    assert result["coach_review"]["superseded_by_id"] is None


def test_no_row_means_not_reviewed(db_session):
    coach, athlete = linked_coach_athlete(db_session)
    svc, plan, meso = _meso(db_session, coach, athlete)
    result, err, status = svc.get_coach_review(coach, meso["id"])
    assert err is None
    assert status == 200
    assert result["coach_review"] is None


def test_next_cycle_focus_does_not_mutate_any_other_plan(db_session, monkeypatch):
    freeze_today(monkeypatch, date(2026, 9, 15))
    coach, athlete = linked_coach_athlete(db_session)
    svc = PlanningService(db_session)
    plan_a = create_draft_plan(db_session, coach, athlete, name="A", service=svc)
    plan_b = create_draft_plan(
        db_session,
        coach,
        athlete,
        name="B",
        start=date(2027, 1, 1),
        service=svc,
    )
    meso_a = add_meso(db_session, coach, plan_a["id"], "Base", microcycle_count=1, service=svc)
    meso_b = add_meso(db_session, coach, plan_b["id"], "Base", microcycle_count=1, service=svc)
    created, err, _ = svc.create_coach_review(
        coach,
        meso_a["id"],
        CoachReviewCreateRequest(content="A notes", next_cycle_focus="Hills"),
    )
    assert err is None
    svc.approve_coach_review(coach, created["coach_review"]["id"])
    other = db_session.get(Mesocycle, meso_b["id"])
    assert other.name == "Base"
    reviews_b = list(
        db_session.scalars(
            select(CycleCoachReview).where(CycleCoachReview.mesocycle_id == meso_b["id"])
        )
    )
    assert reviews_b == []


def test_analysis_source_refs_name_the_contributing_workouts(db_session):
    coach, athlete = linked_coach_athlete(db_session)
    running = make_sport(db_session, "running")
    svc, plan, meso = _meso(db_session, coach, athlete)
    item = add_item(db_session, coach, meso["microcycles"][0]["id"], "Easy", service=svc)
    workout = make_workout(
        db_session, athlete, sport=running, scheduled_date=date(2026, 9, 2)
    )
    db_session.commit()
    svc.attach_workout(coach, item["id"], workout.id)
    gen, err, _ = svc.generate_system_analysis(coach, meso["id"])
    assert err is None
    refs = gen["system_analysis"]["source_refs"]
    assert workout.id in refs["workout_ids"]
    assert "workout_execution_ids" in refs


def test_review_approval_is_recorded_in_the_change_log(db_session, monkeypatch):
    freeze_today(monkeypatch, date(2026, 9, 15))
    coach, athlete = linked_coach_athlete(db_session)
    svc, plan, meso = _meso(db_session, coach, athlete)
    created, err, _ = svc.create_coach_review(
        coach, meso["id"], CoachReviewCreateRequest(content="Notes")
    )
    svc.approve_coach_review(coach, created["coach_review"]["id"])
    from src.modules.planning.models import PlanChangeLog

    row = db_session.scalar(
        select(PlanChangeLog).where(PlanChangeLog.operation == "review_approve")
    )
    assert row is not None
    assert row.entity_id == created["coach_review"]["id"]
