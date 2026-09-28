"""Pure date-reflow for mesocycles and microcycles.

Duration is the stored truth; dates are derived. Anchors are constraints that
may create gaps or conflicts — never silently rewritten.

No SQLAlchemy, no datetime coercion — operates on `date` only.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, timedelta


def duration_days(start: date | None, end: date | None) -> int | None:
    if start is None or end is None:
        return None
    return (end - start).days + 1


def _format_day(d: date) -> str:
    months = (
        "Jan", "Feb", "Mar", "Apr", "May", "Jun",
        "Jul", "Aug", "Sep", "Oct", "Nov", "Dec",
    )
    return f"{months[d.month - 1]} {d.day}"


def days_between(from_d: date, to_d: date) -> int:
    return (to_d - from_d).days


@dataclass
class MicroSpec:
    id: int
    ordinal: int
    duration_days: int
    start_date: date | None
    end_date: date | None
    locked: bool


@dataclass
class MesoSpec:
    id: int
    ordinal: int
    start_date: date | None
    end_date: date | None
    micros: list[MicroSpec] = field(default_factory=list)
    locked: bool = False
    anchor_date: date | None = None
    name: str = ""
    # Empty-block authored span used only when there are no micros and no dates yet.
    empty_duration_days: int = 0


@dataclass
class DateMove:
    kind: str
    id: int
    old_start: date | None
    new_start: date | None
    old_end: date | None
    new_end: date | None

    def to_dict(self) -> dict:
        return {
            "kind": self.kind,
            "id": self.id,
            "old_start": self.old_start.isoformat() if self.old_start else None,
            "new_start": self.new_start.isoformat() if self.new_start else None,
            "old_end": self.old_end.isoformat() if self.old_end else None,
            "new_end": self.new_end.isoformat() if self.new_end else None,
        }


@dataclass
class PlanGap:
    meso_id: int
    from_date: date
    to_date: date
    days: int

    def to_dict(self) -> dict:
        return {
            "meso_id": self.meso_id,
            "from": self.from_date.isoformat(),
            "to": self.to_date.isoformat(),
            "days": self.days,
        }


@dataclass
class AnchorConflict:
    meso_id: int
    meso_name: str
    anchor_date: date
    would_start: date
    overrun_days: int
    kind: str  # "overlap" | "historical"
    message: str

    def to_dict(self) -> dict:
        return {
            "meso_id": self.meso_id,
            "meso_name": self.meso_name,
            "anchor_date": self.anchor_date.isoformat(),
            "would_start": self.would_start.isoformat(),
            "overrun_days": self.overrun_days,
            "kind": self.kind,
            "message": self.message,
        }


def _record_move(
    moves: list[DateMove],
    kind: str,
    obj_id: int,
    old_start: date | None,
    old_end: date | None,
    new_start: date | None,
    new_end: date | None,
) -> None:
    if old_start != new_start or old_end != new_end:
        moves.append(
            DateMove(
                kind=kind,
                id=obj_id,
                old_start=old_start,
                new_start=new_start,
                old_end=old_end,
                new_end=new_end,
            )
        )


def _clear_dates(mesos: list[MesoSpec]) -> tuple[list[MesoSpec], list[DateMove]]:
    """Duration mode: clear all derived dates without changing structure."""
    moves: list[DateMove] = []
    for meso in mesos:
        for micro in meso.micros:
            if micro.locked:
                continue
            old_start, old_end = micro.start_date, micro.end_date
            micro.start_date = None
            micro.end_date = None
            _record_move(
                moves, "microcycle", micro.id, old_start, old_end, None, None
            )
        if not meso.locked:
            old_start, old_end = meso.start_date, meso.end_date
            meso.start_date = None
            meso.end_date = None
            _record_move(moves, "mesocycle", meso.id, old_start, old_end, None, None)
    return mesos, moves


def reflow(
    plan_start: date | None,
    mesos: list[MesoSpec],
    today: date | None = None,
) -> tuple[
    list[MesoSpec],
    list[DateMove],
    date | None,
    list[PlanGap],
    list[AnchorConflict],
]:
    """Retile the plan from stored durations and optional anchors.

    Locked periods are read, never written. Anchors are constraints: a gap is
    valid; an overlap is reported as a conflict without silently moving the
    anchored block.

    Returns (mesos, moves, new plan end_date, gaps, conflicts).
    """
    ordered = sorted(mesos, key=lambda m: m.ordinal)
    moves: list[DateMove] = []
    gaps: list[PlanGap] = []
    conflicts: list[AnchorConflict] = []
    one = timedelta(days=1)

    if plan_start is None:
        ordered, moves = _clear_dates(ordered)
        return ordered, moves, None, [], []

    cursor: date = plan_start

    for meso in ordered:
        meso.micros.sort(key=lambda m: m.ordinal)

        # Apply anchor constraint before tiling this block.
        if meso.anchor_date is not None and not meso.locked:
            anchor = meso.anchor_date
            if today is not None and anchor < today:
                conflicts.append(
                    AnchorConflict(
                        meso_id=meso.id,
                        meso_name=meso.name or f"Block {meso.id}",
                        anchor_date=anchor,
                        would_start=cursor,
                        overrun_days=days_between(anchor, cursor),
                        kind="historical",
                        message=(
                            f"{meso.name or 'Block'} is anchored to "
                            f"{_format_day(anchor)}, which is in the past."
                        ),
                    )
                )
            elif anchor > cursor:
                days = days_between(cursor, anchor)
                gaps.append(
                    PlanGap(
                        meso_id=meso.id,
                        from_date=cursor,
                        to_date=anchor - one,
                        days=days,
                    )
                )
                cursor = anchor
            elif anchor < cursor:
                overrun = days_between(anchor, cursor)
                conflicts.append(
                    AnchorConflict(
                        meso_id=meso.id,
                        meso_name=meso.name or f"Block {meso.id}",
                        anchor_date=anchor,
                        would_start=cursor,
                        overrun_days=overrun,
                        kind="overlap",
                        message=(
                            f"Preceding structure runs {overrun} day"
                            f"{'' if overrun == 1 else 's'} past the "
                            f"{_format_day(anchor)} anchor on "
                            f"{meso.name or 'Block'}."
                        ),
                    )
                )
                # Anchored block still starts on its anchor — nothing moves silently.
                cursor = anchor
            else:
                # anchor == cursor — clean fit
                pass

        if not meso.micros:
            if meso.locked:
                if meso.end_date is not None:
                    cursor = meso.end_date + one
                continue
            span = 0
            if meso.start_date is not None and meso.end_date is not None:
                span = duration_days(meso.start_date, meso.end_date) or 0
            elif meso.empty_duration_days > 0:
                span = meso.empty_duration_days
            if span <= 0:
                # Truly empty block — no dates, no cursor advance.
                old_start, old_end = meso.start_date, meso.end_date
                meso.start_date = None
                meso.end_date = None
                _record_move(
                    moves, "mesocycle", meso.id, old_start, old_end, None, None
                )
                continue
            old_start, old_end = meso.start_date, meso.end_date
            meso.start_date = cursor
            meso.end_date = cursor + timedelta(days=span - 1)
            _record_move(
                moves,
                "mesocycle",
                meso.id,
                old_start,
                old_end,
                meso.start_date,
                meso.end_date,
            )
            cursor = meso.end_date + one
            continue

        for micro in meso.micros:
            if micro.locked:
                if micro.end_date is not None:
                    cursor = micro.end_date + one
                continue
            old_start, old_end = micro.start_date, micro.end_date
            micro.start_date = cursor
            micro.end_date = cursor + timedelta(days=micro.duration_days - 1)
            _record_move(
                moves,
                "microcycle",
                micro.id,
                old_start,
                old_end,
                micro.start_date,
                micro.end_date,
            )
            cursor = micro.end_date + one

        dated_micros = [m for m in meso.micros if m.start_date and m.end_date]
        old_start, old_end = meso.start_date, meso.end_date
        if dated_micros:
            meso.start_date = min(m.start_date for m in dated_micros)  # type: ignore[type-var]
            meso.end_date = max(m.end_date for m in dated_micros)  # type: ignore[type-var]
            cursor = meso.end_date + one
        else:
            meso.start_date = None
            meso.end_date = None
        _record_move(
            moves, "mesocycle", meso.id, old_start, old_end, meso.start_date, meso.end_date
        )

    dated_ends = [m.end_date for m in ordered if m.end_date is not None]
    plan_end = max(dated_ends) if dated_ends else plan_start
    return ordered, moves, plan_end, gaps, conflicts
