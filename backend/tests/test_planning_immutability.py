"""Lock-state and permission-matrix tests."""
from __future__ import annotations

from datetime import date, datetime, timedelta, timezone

from sqlalchemy import event

from src.modules.execution.enums import ALGORITHM_VERSION
from src.modules.execution.models import WorkoutExecution, WorkoutPlanSnapshot
from src.modules.identity.models import UserRoleEnum
from src.modules.planning.enums import LockState, PlanOperation
from src.modules.planning.immutability import (
    PERMISSION_MATRIX,
    REASON_REQUIRED_MESSAGE,
    assert_mutable,
    bulk_evidence_microcycle_ids,
    mesocycle_lock_state,
    microcycle_lock_state,
)
from src.modules.planning.models import Mesocycle, Microcycle, PlanItem, TrainingPlan
from src.modules.training.models import WorkoutStatus

from tests.conftest import make_activity, make_sport, make_user, make_workout


TODAY = date(2026, 9, 15)


def _plan(db, athlete, **kwargs) -> TrainingPlan:
    plan = TrainingPlan(
        athlete_id=athlete.id,
        name=kwargs.get("name", "Autumn 10K"),
        start_date=kwargs.get("start_date", date(2026, 9, 1)),
        end_date=kwargs.get("end_date", date(2026, 11, 23)),
        planning_timezone=kwargs.get("planning_timezone"),
        status=kwargs.get("status", "draft"),
    )
    db.add(plan)
    db.flush()
    return plan


def _meso(db, plan, start, end, ordinal=0, name="Base") -> Mesocycle:
    meso = Mesocycle(
        training_plan_id=plan.id,
        name=name,
        start_date=start,
        end_date=end,
        ordinal=ordinal,
    )
    db.add(meso)
    db.flush()
    return meso


def _micro(db, meso, start, end, ordinal=0) -> Microcycle:
    micro = Microcycle(
        mesocycle_id=meso.id,
        start_date=start,
        end_date=end,
        duration_days=(end - start).days + 1,
        ordinal=ordinal,
    )
    db.add(micro)
    db.flush()
    return micro


def test_microcycle_locked_when_end_date_in_past(db_session):
    athlete = make_user(db_session, role=UserRoleEnum.athlete)
    plan = _plan(db_session, athlete)
    meso = _meso(db_session, plan, date(2026, 9, 1), date(2026, 9, 7))
    micro = _micro(db_session, meso, date(2026, 9, 1), date(2026, 9, 7))
    db_session.commit()
    assert microcycle_lock_state(db_session, micro, TODAY) == LockState.locked


def test_microcycle_locked_when_contains_completed_workout(db_session):
    athlete = make_user(db_session, role=UserRoleEnum.athlete)
    running = make_sport(db_session, "running")
    plan = _plan(db_session, athlete)
    meso = _meso(db_session, plan, date(2026, 9, 15), date(2026, 9, 21))
    micro = _micro(db_session, meso, date(2026, 9, 15), date(2026, 9, 21))
    workout = make_workout(
        db_session,
        athlete,
        sport=running,
        scheduled_date=date(2026, 9, 16),
        status=WorkoutStatus.completed,
    )
    db_session.add(
        PlanItem(
            microcycle_id=micro.id,
            ordinal=0,
            title="Threshold",
            workout_id=workout.id,
        )
    )
    db_session.commit()
    assert microcycle_lock_state(db_session, micro, TODAY) == LockState.locked


def test_microcycle_locked_when_contains_workout_execution(db_session):
    athlete = make_user(db_session, role=UserRoleEnum.athlete)
    running = make_sport(db_session, "running")
    plan = _plan(db_session, athlete)
    meso = _meso(db_session, plan, date(2026, 9, 15), date(2026, 9, 21))
    micro = _micro(db_session, meso, date(2026, 9, 15), date(2026, 9, 21))
    activity = make_activity(db_session, athlete, sport=running, activity_date=date(2026, 9, 16))
    workout = make_workout(
        db_session,
        athlete,
        sport=running,
        scheduled_date=date(2026, 9, 16),
        status=WorkoutStatus.scheduled,
        activity_id=None,
    )
    db_session.add(
        PlanItem(
            microcycle_id=micro.id,
            ordinal=0,
            title="Threshold",
            workout_id=workout.id,
        )
    )
    snapshot = WorkoutPlanSnapshot(
        workout_id=workout.id, athlete_id=athlete.id, resolved_plan={}
    )
    db_session.add(snapshot)
    db_session.flush()
    db_session.add(
        WorkoutExecution(
            workout_id=workout.id,
            activity_id=activity.id,
            plan_snapshot_id=snapshot.id,
            status="matched",
            algorithm_version=ALGORITHM_VERSION,
        )
    )
    db_session.commit()
    assert microcycle_lock_state(db_session, micro, TODAY) == LockState.locked


def test_microcycle_locked_when_workout_has_activity_id(db_session):
    athlete = make_user(db_session, role=UserRoleEnum.athlete)
    running = make_sport(db_session, "running")
    plan = _plan(db_session, athlete)
    meso = _meso(db_session, plan, date(2026, 9, 15), date(2026, 9, 21))
    micro = _micro(db_session, meso, date(2026, 9, 15), date(2026, 9, 21))
    activity = make_activity(db_session, athlete, sport=running, activity_date=date(2026, 9, 16))
    workout = make_workout(
        db_session,
        athlete,
        sport=running,
        scheduled_date=date(2026, 9, 16),
        status=WorkoutStatus.scheduled,
        activity_id=activity.id,
    )
    db_session.add(
        PlanItem(
            microcycle_id=micro.id,
            ordinal=0,
            title="Threshold",
            workout_id=workout.id,
        )
    )
    db_session.commit()
    assert microcycle_lock_state(db_session, micro, TODAY) == LockState.locked


def test_microcycle_current_when_today_inside_range(db_session):
    athlete = make_user(db_session, role=UserRoleEnum.athlete)
    plan = _plan(db_session, athlete)
    meso = _meso(db_session, plan, date(2026, 9, 15), date(2026, 9, 21))
    micro = _micro(db_session, meso, date(2026, 9, 15), date(2026, 9, 21))
    db_session.commit()
    assert microcycle_lock_state(db_session, micro, TODAY) == LockState.current


def test_microcycle_future_when_start_date_after_today(db_session):
    athlete = make_user(db_session, role=UserRoleEnum.athlete)
    plan = _plan(db_session, athlete)
    meso = _meso(db_session, plan, date(2026, 9, 22), date(2026, 9, 28))
    micro = _micro(db_session, meso, date(2026, 9, 22), date(2026, 9, 28))
    db_session.commit()
    assert microcycle_lock_state(db_session, micro, TODAY) == LockState.future


def test_future_dated_microcycle_locks_when_a_workout_is_executed_early(db_session):
    athlete = make_user(db_session, role=UserRoleEnum.athlete)
    running = make_sport(db_session, "running")
    plan = _plan(db_session, athlete)
    meso = _meso(db_session, plan, date(2026, 9, 22), date(2026, 9, 28))
    micro = _micro(db_session, meso, date(2026, 9, 22), date(2026, 9, 28))
    workout = make_workout(
        db_session,
        athlete,
        sport=running,
        scheduled_date=date(2026, 9, 22),
        status=WorkoutStatus.completed,
    )
    db_session.add(
        PlanItem(
            microcycle_id=micro.id,
            ordinal=0,
            title="Early session",
            workout_id=workout.id,
        )
    )
    db_session.commit()
    assert microcycle_lock_state(db_session, micro, TODAY) == LockState.locked


def test_mesocycle_locked_when_any_microcycle_locked(db_session):
    athlete = make_user(db_session, role=UserRoleEnum.athlete)
    plan = _plan(db_session, athlete)
    meso = _meso(db_session, plan, date(2026, 9, 1), date(2026, 9, 21))
    _micro(db_session, meso, date(2026, 9, 1), date(2026, 9, 7), ordinal=0)
    _micro(db_session, meso, date(2026, 9, 15), date(2026, 9, 21), ordinal=1)
    db_session.commit()
    db_session.refresh(meso)
    assert mesocycle_lock_state(db_session, meso, TODAY) == LockState.locked


def test_bulk_evidence_is_one_query(db_session):
    athlete = make_user(db_session, role=UserRoleEnum.athlete)
    running = make_sport(db_session, "running")
    plan = _plan(db_session, athlete)
    meso = _meso(db_session, plan, date(2026, 9, 15), date(2026, 9, 28))
    m1 = _micro(db_session, meso, date(2026, 9, 15), date(2026, 9, 21), ordinal=0)
    m2 = _micro(db_session, meso, date(2026, 9, 22), date(2026, 9, 28), ordinal=1)
    workout = make_workout(
        db_session, athlete, sport=running, status=WorkoutStatus.skipped
    )
    db_session.add(
        PlanItem(microcycle_id=m1.id, ordinal=0, title="A", workout_id=workout.id)
    )
    db_session.commit()

    statements: list[str] = []

    def before_cursor(conn, cursor, statement, parameters, context, executemany):
        statements.append(statement)

    event.listen(db_session.bind, "before_cursor_execute", before_cursor)
    try:
        ids = bulk_evidence_microcycle_ids(db_session, [m1.id, m2.id])
    finally:
        event.remove(db_session.bind, "before_cursor_execute", before_cursor)

    assert ids == {m1.id}
    evidence_sql = [
        s for s in statements if "plan_items" in s.lower() or "workout_executions" in s.lower()
    ]
    assert len(evidence_sql) == 1


def test_permission_matrix_is_exhaustive():
    for state in LockState:
        for operation in PlanOperation:
            assert (state, operation) in PERMISSION_MATRIX


def test_locked_metadata_edit_allowed_with_reason():
    err, status = assert_mutable(LockState.locked, PlanOperation.metadata, "typo")
    assert err is None
    assert status == 200


def test_locked_metadata_edit_rejected_without_reason():
    err, status = assert_mutable(LockState.locked, PlanOperation.metadata, None)
    assert status == 400
    assert err == REASON_REQUIRED_MESSAGE
    err, status = assert_mutable(LockState.locked, PlanOperation.metadata, "   ")
    assert status == 400


def test_locked_structural_edit_rejected_even_with_reason():
    err, status = assert_mutable(LockState.locked, PlanOperation.structure, "please")
    assert status == 409
    assert err is not None


def test_planning_today_follows_plan_timezone(monkeypatch):
    from src.modules.planning import clock as clock_mod

    instant = datetime(2026, 9, 16, 2, 0, 0, tzinfo=timezone.utc)

    class FakeDateTime(datetime):
        @classmethod
        def now(cls, tz=None):
            if tz is None:
                return instant.replace(tzinfo=None)
            return instant.astimezone(tz)

    monkeypatch.setattr(clock_mod, "datetime", FakeDateTime)

    class FakePlan:
        def __init__(self, tz):
            self.planning_timezone = tz

    auckland = clock_mod.planning_today(FakePlan("Pacific/Auckland"))
    midway = clock_mod.planning_today(FakePlan("Pacific/Midway"))
    assert auckland != midway
    assert auckland == date(2026, 9, 16)
    assert midway == date(2026, 9, 15)


def test_planning_today_defaults_to_utc_when_timezone_null():
    from src.modules.planning.clock import planning_today, resolve_planning_timezone

    class FakePlan:
        planning_timezone = None

    tz = resolve_planning_timezone(FakePlan())
    assert str(tz) == "UTC"
    today = planning_today(FakePlan())
    assert today == datetime.now(tz).date()
