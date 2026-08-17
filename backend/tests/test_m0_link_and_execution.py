"""Persistence tests for M0 link, rematch, auto-link, and complete/skip."""
from __future__ import annotations

from datetime import date

from sqlalchemy import func, select

from src.modules.execution.enums import ALGORITHM_VERSION
from src.modules.execution.models import (
    ExecutionIssue,
    WorkoutExecution,
    WorkoutPlanSnapshot,
    WorkoutStepExecution,
)
from src.modules.execution.scoring import aggregate_execution_score
from src.modules.execution.service import WorkoutExecutionService, rematch_workout_activity
from src.modules.identity.models import UserRoleEnum
from src.modules.training.activity_link import try_link_activity_to_workout
from src.modules.training.models import Workout, WorkoutStatus, WorkoutType
from src.modules.training.service import TrainingService

from tests.conftest import (
    make_activity,
    make_relation,
    make_sport,
    make_user,
    make_workout,
)


def test_manual_link_runs_matching_and_persists_execution(db_session):
    athlete = make_user(db_session, role=UserRoleEnum.athlete)
    running = make_sport(db_session, "running")
    workout = make_workout(db_session, athlete, sport=running)
    activity = make_activity(db_session, athlete, sport=running)
    db_session.commit()

    result, err, status = TrainingService(db_session).link_activity(
        athlete, workout.id, activity.id
    )
    assert err is None
    assert status == 200
    assert result["workout"]["activity_id"] == activity.id
    assert result["workout"]["status"] == "completed"
    assert result["workout_execution"] is not None

    count = db_session.scalar(select(func.count()).select_from(WorkoutExecution))
    assert count == 1


def test_rematch_twice_keeps_one_execution_and_drops_athlete_responses(db_session):
    athlete = make_user(db_session, role=UserRoleEnum.athlete)
    running = make_sport(db_session, "running")
    workout = make_workout(db_session, athlete, sport=running)
    activity = make_activity(db_session, athlete, sport=running)
    db_session.commit()

    service = TrainingService(db_session)
    _, err, _ = service.link_activity(athlete, workout.id, activity.id)
    assert err is None

    execution = db_session.scalar(select(WorkoutExecution))
    issue = ExecutionIssue(
        workout_execution_id=execution.id,
        authored_step_id="step-1",
        occurrence_ordinal=0,
        code="test_issue",
        severity="info",
        dimension="matching",
        athlete_id=athlete.id,
        athlete_reason="Felt tired",
    )
    db_session.add(issue)
    db_session.commit()

    execution2, err, status = rematch_workout_activity(
        db_session, workout_id=workout.id, activity_id=activity.id
    )
    assert err is None
    assert status == 200
    assert execution2 is not None

    rows = db_session.scalars(select(WorkoutExecution)).all()
    assert len(rows) == 1
    assert rows[0].algorithm_version == ALGORITHM_VERSION
    leftover = db_session.scalars(
        select(ExecutionIssue).where(ExecutionIssue.athlete_reason == "Felt tired")
    ).all()
    assert leftover == []


def test_ambiguous_same_day_auto_link_none_then_manual_succeeds(db_session):
    athlete = make_user(db_session, role=UserRoleEnum.athlete)
    running = make_sport(db_session, "running")
    day = date(2026, 8, 17)
    first = make_workout(
        db_session, athlete, sport=running, scheduled_date=day, title="AM", slot_ordinal=0
    )
    make_workout(
        db_session, athlete, sport=running, scheduled_date=day, title="PM", slot_ordinal=1
    )
    activity = make_activity(db_session, athlete, sport=running, activity_date=day)
    db_session.commit()

    linked = try_link_activity_to_workout(
        db_session, athlete.id, activity.id, day, "running", sport_id=running.id
    )
    assert linked is None

    result, err, status = TrainingService(db_session).link_activity(
        athlete, first.id, activity.id
    )
    assert err is None
    assert status == 200
    assert result["workout"]["id"] == first.id
    assert result["workout"]["activity_id"] == activity.id


def test_run_and_ride_same_day_sport_filter_is_unambiguous(db_session):
    athlete = make_user(db_session, role=UserRoleEnum.athlete)
    running = make_sport(db_session, "running")
    cycling = make_sport(db_session, "cycling")
    day = date(2026, 8, 17)
    run_workout = make_workout(
        db_session, athlete, sport=running, scheduled_date=day, title="Run"
    )
    make_workout(
        db_session,
        athlete,
        sport=cycling,
        scheduled_date=day,
        workout_type=WorkoutType.easy,
        title="Ride",
    )
    activity = make_activity(db_session, athlete, sport=running, activity_date=day)
    db_session.commit()

    linked = try_link_activity_to_workout(
        db_session, athlete.id, activity.id, day, "running", sport_id=running.id
    )
    assert linked is not None
    assert linked.id == run_workout.id


def test_calendar_orders_by_slot_ordinal(db_session):
    athlete = make_user(db_session, role=UserRoleEnum.athlete)
    running = make_sport(db_session, "running")
    day = date(2026, 8, 17)
    make_workout(
        db_session, athlete, sport=running, scheduled_date=day, slot_ordinal=1, title="Second"
    )
    make_workout(
        db_session, athlete, sport=running, scheduled_date=day, slot_ordinal=0, title="First"
    )
    db_session.commit()

    result, err, status = TrainingService(db_session).get_calendar(athlete, day, day)
    assert err is None
    assert status == 200
    titles = [w["title"] for w in result["workouts"]]
    assert titles == ["First", "Second"]


def test_calendar_returns_aggregated_execution_score(db_session):
    athlete = make_user(db_session, role=UserRoleEnum.athlete)
    running = make_sport(db_session, "running")
    day = date(2026, 8, 17)
    activity = make_activity(db_session, athlete, sport=running, activity_date=day)
    workout = make_workout(
        db_session,
        athlete,
        sport=running,
        scheduled_date=day,
        status=WorkoutStatus.completed,
        activity_id=activity.id,
    )
    snapshot = WorkoutPlanSnapshot(
        workout_id=workout.id, athlete_id=athlete.id, resolved_plan={}
    )
    db_session.add(snapshot)
    db_session.flush()
    execution = WorkoutExecution(
        workout_id=workout.id,
        activity_id=activity.id,
        plan_snapshot_id=snapshot.id,
        status="matched",
        algorithm_version=ALGORITHM_VERSION,
    )
    db_session.add(execution)
    db_session.flush()
    db_session.add(
        WorkoutStepExecution(
            workout_execution_id=execution.id,
            authored_step_id="a",
            occurrence_path="a",
            occurrence_ordinal=0,
            status="executed",
            score=80.0,
        )
    )
    db_session.add(
        WorkoutStepExecution(
            workout_execution_id=execution.id,
            authored_step_id="b",
            occurrence_path="b",
            occurrence_ordinal=0,
            status="executed",
            score=90.0,
        )
    )
    db_session.commit()

    result, err, _ = TrainingService(db_session).get_calendar(athlete, day, day)
    assert err is None
    assert result["workouts"][0]["execution_score"] == 85.0
    assert result["workouts"][0]["execution_status"] == "matched"


def test_unlink_hides_execution_but_preserves_row(db_session):
    athlete = make_user(db_session, role=UserRoleEnum.athlete)
    running = make_sport(db_session, "running")
    workout = make_workout(db_session, athlete, sport=running)
    activity = make_activity(db_session, athlete, sport=running)
    db_session.commit()

    service = TrainingService(db_session)
    _, err, _ = service.link_activity(athlete, workout.id, activity.id)
    assert err is None
    assert db_session.scalar(select(func.count()).select_from(WorkoutExecution)) == 1

    _, err, status = service.unlink_activity(athlete, workout.id)
    assert err is None
    assert status == 200
    reloaded = db_session.get(Workout, workout.id)
    assert reloaded.activity_id is None
    assert reloaded.status == WorkoutStatus.scheduled
    assert db_session.scalar(select(func.count()).select_from(WorkoutExecution)) == 1

    payload, err, _ = WorkoutExecutionService(db_session).get_for_activity(
        athlete.id, activity.id
    )
    assert err is None
    assert payload["workout_execution"] is None


def test_link_conflict_when_workout_already_linked(db_session):
    athlete = make_user(db_session, role=UserRoleEnum.athlete)
    running = make_sport(db_session, "running")
    first_activity = make_activity(db_session, athlete, sport=running, name="one")
    second_activity = make_activity(db_session, athlete, sport=running, name="two")
    workout = make_workout(
        db_session, athlete, sport=running, activity_id=first_activity.id
    )
    db_session.commit()

    _, err, status = TrainingService(db_session).link_activity(
        athlete, workout.id, second_activity.id
    )
    assert status == 409
    assert "already linked to a different activity" in err


def test_link_conflict_when_activity_already_linked(db_session):
    athlete = make_user(db_session, role=UserRoleEnum.athlete)
    running = make_sport(db_session, "running")
    activity = make_activity(db_session, athlete, sport=running)
    make_workout(
        db_session, athlete, sport=running, title="Linked", activity_id=activity.id
    )
    other = make_workout(db_session, athlete, sport=running, title="Free")
    db_session.commit()

    _, err, status = TrainingService(db_session).link_activity(
        athlete, other.id, activity.id
    )
    assert status == 409
    assert "already linked to another workout" in err


def test_link_unauthorized_user_is_not_found(db_session):
    owner = make_user(db_session, role=UserRoleEnum.athlete)
    stranger = make_user(db_session, role=UserRoleEnum.athlete, username="stranger")
    running = make_sport(db_session, "running")
    workout = make_workout(db_session, owner, sport=running)
    activity = make_activity(db_session, owner, sport=running)
    db_session.commit()

    _, err, status = TrainingService(db_session).link_activity(
        stranger, workout.id, activity.id
    )
    assert status == 404


def test_coach_can_link_linked_athlete_workout(db_session):
    athlete = make_user(db_session, role=UserRoleEnum.athlete)
    coach = make_user(db_session, role=UserRoleEnum.coach)
    make_relation(db_session, coach, athlete)
    running = make_sport(db_session, "running")
    workout = make_workout(db_session, athlete, sport=running)
    activity = make_activity(db_session, athlete, sport=running)
    db_session.commit()

    result, err, status = TrainingService(db_session).link_activity(
        coach, workout.id, activity.id
    )
    assert err is None
    assert status == 200
    assert result["workout"]["activity_id"] == activity.id


def test_mark_completed_and_skipped_reject_non_scheduled(db_session):
    athlete = make_user(db_session, role=UserRoleEnum.athlete)
    running = make_sport(db_session, "running")
    completed = make_workout(
        db_session, athlete, sport=running, status=WorkoutStatus.completed, title="Done"
    )
    skipped = make_workout(
        db_session, athlete, sport=running, status=WorkoutStatus.skipped, title="Skip"
    )
    db_session.commit()

    service = TrainingService(db_session)
    _, err, status = service.mark_completed(athlete, completed.id, None)
    assert status == 400
    assert err is not None

    _, err, status = service.mark_skipped(athlete, skipped.id)
    assert status == 400

    scheduled = make_workout(db_session, athlete, sport=running, title="Today")
    db_session.commit()
    result, err, status = service.mark_completed(athlete, scheduled.id, "felt good")
    assert err is None
    assert status == 200
    assert result["workout"]["status"] == "completed"


def test_rematch_without_streams_returns_422(db_session):
    athlete = make_user(db_session, role=UserRoleEnum.athlete)
    running = make_sport(db_session, "running")
    workout = make_workout(db_session, athlete, sport=running)
    activity = make_activity(db_session, athlete, sport=running, with_streams=False)
    db_session.commit()

    execution, err, status = rematch_workout_activity(
        db_session, workout_id=workout.id, activity_id=activity.id
    )
    assert execution is None
    assert status == 422
    assert "lap or stream" in err
    assert db_session.scalar(select(func.count()).select_from(WorkoutExecution)) == 0


def test_aggregate_execution_score_mean_null_and_empty():
    assert aggregate_execution_score([80.0, 90.0, None]) == 85.0
    assert aggregate_execution_score([None, None]) is None
    assert aggregate_execution_score([]) is None
    assert aggregate_execution_score([81.14, 82.14]) == 81.6
