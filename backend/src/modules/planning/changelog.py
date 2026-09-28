"""Append-only planning change log. Never commits — the caller owns the transaction."""
from __future__ import annotations

from datetime import date, datetime
from typing import Any

from sqlalchemy.orm import Session

from src.modules.identity.models import User
from src.modules.planning.enums import ChangeLogEntityType, LockState, PlanOperation
from src.modules.planning.models import PlanChangeLog


def _jsonable(value: Any) -> Any:
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, date):
        return value.isoformat()
    if hasattr(value, "value"):
        return value.value
    return value


def diff_fields(obj: object, payload: dict[str, Any]) -> tuple[dict, dict]:
    """Return (before, after) containing only fields that actually changed."""
    before: dict[str, Any] = {}
    after: dict[str, Any] = {}
    for key, new_value in payload.items():
        if not hasattr(obj, key):
            continue
        old_value = getattr(obj, key)
        old_j = _jsonable(old_value)
        new_j = _jsonable(new_value)
        if old_j != new_j:
            before[key] = old_j
            after[key] = new_j
    return before, after


def record_change(
    db: Session,
    *,
    plan_id: int,
    entity_type: ChangeLogEntityType,
    entity_id: int,
    operation: str,
    lock_state: LockState,
    actor: User | None,
    plan_operation: PlanOperation | None = None,
    before: dict | None = None,
    after: dict | None = None,
    reason: str | None = None,
) -> PlanChangeLog:
    """Append one audit row. Called inside the mutating transaction, never after it."""
    row = PlanChangeLog(
        training_plan_id=plan_id,
        entity_type=entity_type.value,
        entity_id=entity_id,
        operation=operation,
        plan_operation=plan_operation,
        lock_state_at_change=lock_state.value,
        changed_by_id=actor.id if actor is not None else None,
        changed_at=datetime.utcnow(),
        before=before,
        after=after,
        reason=reason,
    )
    db.add(row)
    return row
