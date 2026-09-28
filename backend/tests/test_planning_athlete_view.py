"""Athlete read surface: no coach-only leaks, GET-only /my routes."""
from __future__ import annotations

from datetime import date

from src.api.app import create_app
from src.modules.identity.models import UserRoleEnum
from src.modules.planning.schemas import CoachReviewCreateRequest
from src.modules.planning.service import PlanningService
from tests.conftest import linked_coach_athlete, make_relation, make_user
from tests.planning_helpers import add_meso, create_draft_plan, freeze_today


def test_athlete_never_sees_system_analysis(db_session, monkeypatch):
    freeze_today(monkeypatch, date(2026, 9, 15))
    coach, athlete = linked_coach_athlete(db_session)
    svc = PlanningService(db_session)
    plan = create_draft_plan(db_session, coach, athlete, service=svc)
    meso = add_meso(db_session, coach, plan["id"], "Base", microcycle_count=2, service=svc)
    gen, err, _ = svc.generate_system_analysis(coach, meso["id"])
    assert err is None
    result, err, _ = svc.get_my_plan(athlete, plan["id"])
    assert err is None
    assert "system_analysis" not in result["plan"]
    assert "system_analyses" not in str(result)
    for meso_row in result["plan"]["mesocycles"]:
        assert "system_analysis" not in meso_row


def test_athlete_sees_own_plan_structure_and_intent(db_session, monkeypatch):
    freeze_today(monkeypatch, date(2026, 9, 15))
    coach, athlete = linked_coach_athlete(db_session)
    svc = PlanningService(db_session)
    plan = create_draft_plan(db_session, coach, athlete, service=svc)
    add_meso(db_session, coach, plan["id"], "Base", microcycle_count=2, service=svc)
    result, err, status = svc.get_my_plan(athlete, plan["id"])
    assert err is None
    assert status == 200
    assert result["plan"]["name"] == "Autumn 10K"
    assert "lock_state" not in result["plan"]["mesocycles"][0]
    assert "coach_id" not in result["plan"]


def test_athlete_never_sees_draft_coach_review(db_session, monkeypatch):
    freeze_today(monkeypatch, date(2026, 9, 15))
    coach, athlete = linked_coach_athlete(db_session)
    svc = PlanningService(db_session)
    plan = create_draft_plan(db_session, coach, athlete, service=svc)
    meso = add_meso(db_session, coach, plan["id"], "Base", microcycle_count=2, service=svc)
    created, err, _ = svc.create_coach_review(
        coach, meso["id"], CoachReviewCreateRequest(content="Secret draft")
    )
    assert err is None
    result, err, _ = svc.get_my_plan(athlete, plan["id"])
    assert result["plan"]["mesocycles"][0]["coach_review"] is None
    assert "Secret draft" not in str(result)


def test_athlete_never_sees_superseded_coach_review(db_session, monkeypatch):
    freeze_today(monkeypatch, date(2026, 9, 15))
    coach, athlete = linked_coach_athlete(db_session)
    svc = PlanningService(db_session)
    plan = create_draft_plan(db_session, coach, athlete, service=svc)
    meso = add_meso(db_session, coach, plan["id"], "Base", microcycle_count=2, service=svc)
    first, err, _ = svc.create_coach_review(
        coach, meso["id"], CoachReviewCreateRequest(content="Version one")
    )
    assert err is None
    svc.approve_coach_review(coach, first["coach_review"]["id"])
    successor, err, _ = svc.new_coach_review_version(coach, first["coach_review"]["id"])
    assert err is None
    from src.modules.planning.schemas import CoachReviewUpdateRequest

    svc.update_coach_review(
        coach,
        successor["coach_review"]["id"],
        CoachReviewUpdateRequest(content="Version two"),
    )
    svc.approve_coach_review(coach, successor["coach_review"]["id"])
    result, err, _ = svc.get_my_plan(athlete, plan["id"])
    review = result["plan"]["mesocycles"][0]["coach_review"]
    assert review is not None
    assert review["content"] == "Version two"
    assert "Version one" not in str(result)


def test_athlete_sees_approved_review_and_next_cycle_focus(db_session, monkeypatch):
    freeze_today(monkeypatch, date(2026, 9, 15))
    coach, athlete = linked_coach_athlete(db_session)
    svc = PlanningService(db_session)
    plan = create_draft_plan(db_session, coach, athlete, service=svc)
    meso = add_meso(db_session, coach, plan["id"], "Base", microcycle_count=4, service=svc)
    created, err, _ = svc.create_coach_review(
        coach,
        meso["id"],
        CoachReviewCreateRequest(content="Good block", next_cycle_focus="Hills"),
    )
    assert err is None
    svc.approve_coach_review(coach, created["coach_review"]["id"])
    result, err, _ = svc.get_my_plan(athlete, plan["id"])
    review = result["plan"]["mesocycles"][0]["coach_review"]
    assert review["content"] == "Good block"
    assert review["next_cycle_focus"] == "Hills"
    pos, err, status = svc.get_my_position(athlete)
    assert err is None
    assert status == 200
    assert pos["plan"]["id"] == plan["id"]
    assert pos["coach_review"]["next_cycle_focus"] == "Hills"


def test_athlete_cannot_read_another_athletes_plan(db_session):
    coach, athlete = linked_coach_athlete(db_session)
    other = make_user(db_session, role=UserRoleEnum.athlete, username="other-athlete-plan")
    make_relation(db_session, coach, other)
    svc = PlanningService(db_session)
    plan = create_draft_plan(db_session, coach, athlete, service=svc)
    result, err, status = svc.get_my_plan(other, plan["id"])
    assert result is None
    assert status == 404
    assert err == "Training plan not found"


def test_no_athlete_write_route_exists():
    app = create_app()
    my_paths = {
        path: methods
        for path, methods in app.openapi()["paths"].items()
        if path.startswith("/api/planning/my")
    }
    assert my_paths
    for methods in my_paths.values():
        assert set(methods) <= {"get"}
