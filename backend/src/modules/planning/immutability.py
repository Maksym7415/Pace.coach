"""Historical lock rule and permission matrix for planning mutations."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from src.modules.execution.enums import ALGORITHM_VERSION
from src.modules.execution.models import WorkoutExecution
from src.modules.planning.enums import LockState, PlanOperation
from src.modules.planning.models import Mesocycle, Microcycle, PlanItem
from src.modules.training.models import Workout, WorkoutStatus

REASON_REQUIRED_MESSAGE = "A reason is required when changing a completed training period"
LOCKED_OPERATION_MESSAGE = "{operation} is not allowed on a completed training period"


@dataclass(frozen=True)
class Rule:
    allowed: bool
    reason_required: bool = False
    status: int = 409
    message: str | None = None


PERMISSION_MATRIX: dict[tuple[LockState, PlanOperation], Rule] = {
    (LockState.locked, PlanOperation.metadata): Rule(allowed=True, reason_required=True),
    (LockState.locked, PlanOperation.structure): Rule(
        allowed=False, message=LOCKED_OPERATION_MESSAGE
    ),
    (LockState.locked, PlanOperation.dates): Rule(
        allowed=False, message=LOCKED_OPERATION_MESSAGE
    ),
    (LockState.locked, PlanOperation.association): Rule(
        allowed=False, message=LOCKED_OPERATION_MESSAGE
    ),
    (LockState.locked, PlanOperation.delete): Rule(
        allowed=False, message=LOCKED_OPERATION_MESSAGE
    ),
    (LockState.current, PlanOperation.metadata): Rule(allowed=True),
    (LockState.current, PlanOperation.structure): Rule(allowed=True),
    (LockState.current, PlanOperation.dates): Rule(allowed=True),
    (LockState.current, PlanOperation.association): Rule(allowed=True),
    (LockState.current, PlanOperation.delete): Rule(
        allowed=False, message=LOCKED_OPERATION_MESSAGE
    ),
    (LockState.future, PlanOperation.metadata): Rule(allowed=True),
    (LockState.future, PlanOperation.structure): Rule(allowed=True),
    (LockState.future, PlanOperation.dates): Rule(allowed=True),
    (LockState.future, PlanOperation.association): Rule(allowed=True),
    (LockState.future, PlanOperation.delete): Rule(allowed=True),
}


def _date_state(start: date | None, end: date | None, today: date) -> LockState:
    """Derive lock state from dates. Undated periods are always future."""
    if start is None or end is None:
        return LockState.future
    if end < today:
        return LockState.locked
    if start <= today <= end:
        return LockState.current
    return LockState.future


def bulk_evidence_microcycle_ids(
    db: Session, microcycle_ids: list[int]
) -> set[int]:
    """Microcycles that contain executed / completed / skipped / linked work."""
    if not microcycle_ids:
        return set()
    rows = db.execute(
        select(PlanItem.microcycle_id)
        .join(Workout, Workout.id == PlanItem.workout_id)
        .outerjoin(
            WorkoutExecution,
            (WorkoutExecution.workout_id == Workout.id)
            & (WorkoutExecution.algorithm_version == ALGORITHM_VERSION),
        )
        .where(
            PlanItem.microcycle_id.in_(microcycle_ids),
            (Workout.status != WorkoutStatus.scheduled)
            | (Workout.activity_id.is_not(None))
            | (WorkoutExecution.id.is_not(None)),
        )
        .distinct()
    ).all()
    return {row[0] for row in rows}


def microcycle_lock_state(
    db: Session,
    micro: Microcycle,
    today: date,
    evidence_ids: set[int] | None = None,
) -> LockState:
    if evidence_ids is None:
        evidence_ids = bulk_evidence_microcycle_ids(db, [micro.id])
    if micro.id in evidence_ids:
        return LockState.locked
    return _date_state(micro.start_date, micro.end_date, today)


def mesocycle_lock_state(
    db: Session,
    meso: Mesocycle,
    today: date,
    evidence_ids: set[int] | None = None,
    micro_states: dict[int, LockState] | None = None,
) -> LockState:
    micros = list(meso.microcycles) if meso.microcycles is not None else []
    if evidence_ids is None and micros:
        evidence_ids = bulk_evidence_microcycle_ids(db, [m.id for m in micros])
    evidence_ids = evidence_ids or set()

    child_states: list[LockState] = []
    for micro in micros:
        if micro_states is not None and micro.id in micro_states:
            child_states.append(micro_states[micro.id])
        else:
            child_states.append(microcycle_lock_state(db, micro, today, evidence_ids))

    if any(s == LockState.locked for s in child_states):
        return LockState.locked
    return _date_state(meso.start_date, meso.end_date, today)


def assert_mutable(
    lock_state: LockState,
    operation: PlanOperation,
    reason: str | None = None,
) -> tuple[str | None, int]:
    """Returns (None, 200) when allowed, or (error_message, 409|400)."""
    rule = PERMISSION_MATRIX.get((lock_state, operation))
    if rule is None:
        return f"{operation.value} is not allowed", 409
    if not rule.allowed:
        message = (rule.message or LOCKED_OPERATION_MESSAGE).format(
            operation=operation.value
        )
        return message, rule.status
    if rule.reason_required and not (reason and reason.strip()):
        return REASON_REQUIRED_MESSAGE, 400
    return None, 200


@dataclass(frozen=True)
class LockedPeriodSnapshot:
    kind: str
    id: int
    start_date: date | None
    end_date: date | None
    ordinal: int
    child_ids: frozenset[int]
    workout_ids: frozenset[int]


def snapshot_locked_periods(
    mesos: list[Mesocycle],
    micro_states: dict[int, LockState],
    meso_states: dict[int, LockState],
) -> list[LockedPeriodSnapshot]:
    snapshots: list[LockedPeriodSnapshot] = []
    for meso in mesos:
        micros = list(meso.microcycles or [])
        unlocked = [m for m in micros if micro_states.get(m.id) != LockState.locked]
        # A mesocycle with unlocked children may still shrink/grow as those
        # children move. Freeze the meso row only when every child is locked.
        if meso_states.get(meso.id) == LockState.locked and not unlocked:
            snapshots.append(
                LockedPeriodSnapshot(
                    kind="mesocycle",
                    id=meso.id,
                    start_date=meso.start_date,
                    end_date=meso.end_date,
                    ordinal=meso.ordinal,
                    child_ids=frozenset(m.id for m in micros),
                    workout_ids=frozenset(),
                )
            )
        for micro in micros:
            if micro_states.get(micro.id) != LockState.locked:
                continue
            items = list(micro.items or [])
            snapshots.append(
                LockedPeriodSnapshot(
                    kind="microcycle",
                    id=micro.id,
                    start_date=micro.start_date,
                    end_date=micro.end_date,
                    ordinal=micro.ordinal,
                    child_ids=frozenset(i.id for i in items),
                    workout_ids=frozenset(
                        i.workout_id for i in items if i.workout_id is not None
                    ),
                )
            )
    return snapshots


def assert_locked_structure_unchanged(
    before: list[LockedPeriodSnapshot],
    after: list[LockedPeriodSnapshot],
) -> str | None:
    after_by_key = {(s.kind, s.id): s for s in after}
    for snap in before:
        other = after_by_key.get((snap.kind, snap.id))
        if other is None:
            return f"Locked {snap.kind} {snap.id} is missing after mutation"
        if (
            other.start_date != snap.start_date
            or other.end_date != snap.end_date
            or other.ordinal != snap.ordinal
            or other.child_ids != snap.child_ids
            or other.workout_ids != snap.workout_ids
        ):
            return f"Locked {snap.kind} {snap.id} structure or dates would change"
    return None
