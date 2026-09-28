"""Append-only plan change log."""
from __future__ import annotations

from datetime import date

from sqlalchemy import select

from src.modules.identity.models import UserRoleEnum
from src.modules.planning.changelog import diff_fields, record_change
from src.modules.planning.enums import ChangeLogEntityType, LockState, PlanOperation
from src.modules.planning.models import Mesocycle, PlanChangeLog, TrainingPlan

from tests.conftest import make_user


def test_record_change_stores_only_changed_fields(db_session):
    athlete = make_user(db_session, role=UserRoleEnum.athlete)
    coach = make_user(db_session, role=UserRoleEnum.coach)
    plan = TrainingPlan(
        athlete_id=athlete.id,
        name="Autumn 10K",
        start_date=date(2026, 9, 1),
        end_date=date(2026, 11, 23),
    )
    db_session.add(plan)
    db_session.flush()
    meso = Mesocycle(
        training_plan_id=plan.id,
        name="Base",
        intent="Aerobic",
        start_date=date(2026, 9, 1),
        end_date=date(2026, 9, 28),
        ordinal=0,
    )
    db_session.add(meso)
    db_session.flush()

    before, after = diff_fields(meso, {"name": "Base Development", "intent": "Aerobic"})
    assert before == {"name": "Base"}
    assert after == {"name": "Base Development"}

    record_change(
        db_session,
        plan_id=plan.id,
        entity_type=ChangeLogEntityType.mesocycle,
        entity_id=meso.id,
        operation="update",
        lock_state=LockState.future,
        actor=coach,
        plan_operation=PlanOperation.metadata,
        before=before,
        after=after,
        reason=None,
    )
    db_session.commit()

    row = db_session.scalar(select(PlanChangeLog))
    assert row is not None
    assert row.before == {"name": "Base"}
    assert row.after == {"name": "Base Development"}
    assert row.lock_state_at_change == "future"
    assert row.changed_by_id == coach.id


def test_record_change_stamps_lock_state(db_session):
    athlete = make_user(db_session, role=UserRoleEnum.athlete)
    coach = make_user(db_session, role=UserRoleEnum.coach)
    plan = TrainingPlan(
        athlete_id=athlete.id,
        name="Autumn 10K",
        start_date=date(2026, 9, 1),
        end_date=date(2026, 11, 23),
    )
    db_session.add(plan)
    db_session.flush()
    record_change(
        db_session,
        plan_id=plan.id,
        entity_type=ChangeLogEntityType.training_plan,
        entity_id=plan.id,
        operation="update",
        lock_state=LockState.locked,
        actor=coach,
        plan_operation=PlanOperation.metadata,
        before={"name": "Old"},
        after={"name": "New"},
        reason="typo in title",
    )
    db_session.commit()
    row = db_session.scalar(select(PlanChangeLog))
    assert row.lock_state_at_change == "locked"
    assert row.reason == "typo in title"


def test_change_log_row_survives_entity_deletion(db_session):
    athlete = make_user(db_session, role=UserRoleEnum.athlete)
    plan = TrainingPlan(
        athlete_id=athlete.id,
        name="Autumn 10K",
        start_date=date(2026, 9, 1),
        end_date=date(2026, 11, 23),
    )
    db_session.add(plan)
    db_session.flush()
    meso = Mesocycle(
        training_plan_id=plan.id,
        name="Base",
        start_date=date(2026, 9, 1),
        end_date=date(2026, 9, 28),
        ordinal=0,
    )
    db_session.add(meso)
    db_session.flush()
    deleted_id = meso.id
    record_change(
        db_session,
        plan_id=plan.id,
        entity_type=ChangeLogEntityType.mesocycle,
        entity_id=deleted_id,
        operation="delete",
        lock_state=LockState.future,
        actor=None,
    )
    db_session.delete(meso)
    db_session.commit()

    row = db_session.scalar(
        select(PlanChangeLog).where(PlanChangeLog.entity_id == deleted_id)
    )
    assert row is not None
    assert row.operation == "delete"
    assert db_session.get(Mesocycle, deleted_id) is None


def test_change_log_has_no_update_or_delete_path():
    import src.modules.planning.changelog as changelog

    assert not hasattr(changelog, "update_change")
    assert not hasattr(changelog, "delete_change")
    assert not hasattr(changelog.PlanChangeLog, "update")
