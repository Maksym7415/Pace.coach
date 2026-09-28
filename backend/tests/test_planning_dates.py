"""Pure unit tests for planning date reflow."""
from __future__ import annotations

from datetime import date, timedelta

from src.modules.planning.dates import MesoSpec, MicroSpec, duration_days, reflow


def _micro(
    mid: int,
    ordinal: int,
    start: date | None,
    days: int,
    locked: bool = False,
) -> MicroSpec:
    end = start + timedelta(days=days - 1) if start is not None else None
    return MicroSpec(
        id=mid,
        ordinal=ordinal,
        duration_days=days,
        start_date=start,
        end_date=end,
        locked=locked,
    )


def test_reflow_is_idempotent():
    start = date(2026, 9, 1)
    mesos = [
        MesoSpec(
            id=1,
            ordinal=0,
            start_date=start,
            end_date=date(2026, 9, 14),
            micros=[
                _micro(1, 0, start, 7),
                _micro(2, 1, date(2026, 9, 8), 7),
            ],
        )
    ]
    first, _, end1, _, _ = reflow(start, mesos)
    second, moves2, end2, _, _ = reflow(start, first)
    assert end1 == end2
    assert moves2 == []
    assert second[0].micros[0].start_date == start
    assert second[0].micros[1].start_date == date(2026, 9, 8)


def test_reflow_never_moves_locked_microcycles():
    start = date(2026, 9, 1)
    locked = _micro(1, 0, start, 7, locked=True)
    future = _micro(2, 1, date(2026, 9, 8), 7)
    mesos = [
        MesoSpec(
            id=1,
            ordinal=0,
            start_date=start,
            end_date=date(2026, 9, 14),
            micros=[locked, future],
        )
    ]
    # Shift plan start earlier — locked week must stay put.
    result, moves, _, _, _ = reflow(date(2026, 8, 25), mesos)
    locked_after = result[0].micros[0]
    assert locked_after.start_date == start
    assert locked_after.end_date == date(2026, 9, 7)
    assert not any(m.kind == "microcycle" and m.id == 1 for m in moves)


def test_reflow_shifts_subsequent_future_microcycles_when_duration_grows():
    start = date(2026, 9, 1)
    first = _micro(1, 0, start, 10)
    second = _micro(2, 1, date(2026, 9, 8), 7)
    mesos = [
        MesoSpec(
            id=1,
            ordinal=0,
            start_date=start,
            end_date=date(2026, 9, 14),
            micros=[first, second],
        )
    ]
    result, moves, plan_end, _, _ = reflow(start, mesos)
    assert result[0].micros[0].end_date == date(2026, 9, 10)
    assert result[0].micros[1].start_date == date(2026, 9, 11)
    assert result[0].micros[1].end_date == date(2026, 9, 17)
    assert plan_end == date(2026, 9, 17)
    shifted = [m for m in moves if m.id == 2]
    assert shifted and shifted[0].old_start == date(2026, 9, 8)
    assert shifted[0].new_start == date(2026, 9, 11)


def test_reflow_flows_future_periods_after_locked_prefix():
    start = date(2026, 9, 1)
    mesos = [
        MesoSpec(
            id=1,
            ordinal=0,
            start_date=start,
            end_date=date(2026, 9, 21),
            micros=[
                _micro(1, 0, start, 7, locked=True),
                _micro(2, 1, date(2026, 9, 8), 7, locked=True),
                _micro(3, 2, date(2026, 9, 15), 5),
            ],
        )
    ]
    result, _, _, _, _ = reflow(start, mesos)
    assert result[0].micros[0].start_date == start
    assert result[0].micros[1].start_date == date(2026, 9, 8)
    assert result[0].micros[2].start_date == date(2026, 9, 15)
    assert result[0].end_date == date(2026, 9, 19)


def test_reflow_empty_block_without_duration_stays_undated():
    start = date(2026, 9, 1)
    mesos = [
        MesoSpec(
            id=1,
            ordinal=0,
            start_date=None,
            end_date=None,
            micros=[],
            empty_duration_days=0,
        ),
        MesoSpec(
            id=2,
            ordinal=1,
            start_date=None,
            end_date=None,
            micros=[_micro(1, 0, None, 7)],
        ),
    ]
    result, _, plan_end, _, _ = reflow(start, mesos)
    assert result[0].start_date is None
    assert result[0].end_date is None
    assert result[1].micros[0].start_date == start
    assert plan_end == date(2026, 9, 7)


def test_reflow_returns_diff_naming_every_moved_period():
    start = date(2026, 9, 1)
    mesos = [
        MesoSpec(
            id=10,
            ordinal=0,
            start_date=date(2026, 9, 3),
            end_date=date(2026, 9, 9),
            micros=[_micro(1, 0, date(2026, 9, 3), 7)],
        )
    ]
    _, moves, _, _, _ = reflow(start, mesos)
    kinds = {(m.kind, m.id) for m in moves}
    assert ("microcycle", 1) in kinds
    assert ("mesocycle", 10) in kinds


def test_duration_mode_clears_dates():
    mesos = [
        MesoSpec(
            id=1,
            ordinal=0,
            start_date=date(2026, 9, 1),
            end_date=date(2026, 9, 14),
            micros=[
                _micro(1, 0, date(2026, 9, 1), 7),
                _micro(2, 1, date(2026, 9, 8), 7),
            ],
        )
    ]
    result, moves, plan_end, gaps, conflicts = reflow(None, mesos)
    assert plan_end is None
    assert gaps == []
    assert conflicts == []
    assert result[0].start_date is None
    assert result[0].micros[0].start_date is None
    assert result[0].micros[0].duration_days == 7
    assert any(m.kind == "microcycle" for m in moves)


def test_anchor_creates_unplanned_gap():
    start = date(2026, 9, 1)
    today = date(2026, 8, 15)
    mesos = [
        MesoSpec(
            id=1,
            ordinal=0,
            name="Base",
            start_date=None,
            end_date=None,
            micros=[_micro(1, 0, None, 7)],
        ),
        MesoSpec(
            id=2,
            ordinal=1,
            name="Threshold Development",
            start_date=None,
            end_date=None,
            anchor_date=date(2026, 9, 15),
            micros=[_micro(2, 0, None, 7)],
        ),
    ]
    result, _, _, gaps, conflicts = reflow(start, mesos, today=today)
    assert conflicts == []
    assert len(gaps) == 1
    assert gaps[0].days == 7  # Sep 8–14
    assert gaps[0].meso_id == 2
    assert result[1].start_date == date(2026, 9, 15)
    assert result[1].micros[0].start_date == date(2026, 9, 15)


def test_anchor_overlap_conflict_does_not_silently_move():
    start = date(2026, 9, 1)
    today = date(2026, 8, 15)
    mesos = [
        MesoSpec(
            id=1,
            ordinal=0,
            name="Base Development",
            start_date=None,
            end_date=None,
            micros=[_micro(1, 0, None, 14)],
        ),
        MesoSpec(
            id=2,
            ordinal=1,
            name="Threshold Development",
            start_date=None,
            end_date=None,
            anchor_date=date(2026, 9, 12),
            micros=[_micro(2, 0, None, 7)],
        ),
    ]
    result, _, _, gaps, conflicts = reflow(start, mesos, today=today)
    assert gaps == []
    assert len(conflicts) == 1
    assert conflicts[0].kind == "overlap"
    assert conflicts[0].overrun_days == 3
    assert "Sep 12" in conflicts[0].message
    assert "Threshold Development" in conflicts[0].message
    # Anchored block still starts on its anchor
    assert result[1].start_date == date(2026, 9, 12)
    assert result[1].micros[0].start_date == date(2026, 9, 12)


def test_historical_anchor_conflict():
    start = date(2026, 9, 1)
    today = date(2026, 9, 17)
    mesos = [
        MesoSpec(
            id=1,
            ordinal=0,
            name="Future Block",
            start_date=None,
            end_date=None,
            anchor_date=date(2026, 9, 10),
            micros=[_micro(1, 0, None, 7)],
        )
    ]
    _, _, _, _, conflicts = reflow(start, mesos, today=today)
    assert len(conflicts) == 1
    assert conflicts[0].kind == "historical"


def test_anchored_block_immune_to_upstream_reflow():
    start = date(2026, 9, 1)
    today = date(2026, 8, 1)
    mesos = [
        MesoSpec(
            id=1,
            ordinal=0,
            name="Base",
            start_date=None,
            end_date=None,
            micros=[_micro(1, 0, None, 7)],
        ),
        MesoSpec(
            id=2,
            ordinal=1,
            name="Threshold",
            start_date=None,
            end_date=None,
            anchor_date=date(2026, 9, 20),
            micros=[_micro(2, 0, None, 7)],
        ),
    ]
    # Grow the first block — anchored second block must stay on Sep 20
    mesos[0].micros[0].duration_days = 14
    result, _, _, gaps, conflicts = reflow(start, mesos, today=today)
    assert conflicts == []
    assert result[1].start_date == date(2026, 9, 20)
    assert result[1].micros[0].start_date == date(2026, 9, 20)
    # Gap shrinks because Base now ends Sep 14
    assert gaps[0].days == 5


def test_duration_days_includes_both_ends():
    assert duration_days(date(2026, 9, 1), date(2026, 9, 1)) == 1
    assert duration_days(date(2026, 9, 1), date(2026, 9, 7)) == 7
    assert duration_days(None, date(2026, 9, 7)) is None
