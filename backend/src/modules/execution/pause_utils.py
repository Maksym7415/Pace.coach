"""Explicit activity pause intervals from device event markers (no inference)."""
from __future__ import annotations

from datetime import datetime

from src.modules.execution.domain import PauseInterval
from src.modules.fit_parser.models import FitEvent

_TIMER_EVENT = "timer"
_PAUSE_START_TYPES = frozenset({"stop_all", "stop"})
_PAUSE_END_TYPES = frozenset({"start"})


def extract_explicit_pause_intervals(markers: list[FitEvent]) -> list[PauseInterval]:
    """Pair Garmin FIT timer stop/start events into explicit pause intervals."""
    ordered = sorted(
        (m for m in markers if m.timestamp is not None),
        key=lambda m: m.timestamp,  # type: ignore[arg-type, return-value]
    )
    pauses: list[PauseInterval] = []
    pause_start: datetime | None = None

    for ev in ordered:
        if (ev.event or "").lower() != _TIMER_EVENT:
            continue
        event_type = (ev.event_type or "").lower()
        ts = ev.timestamp
        assert ts is not None

        if event_type in _PAUSE_START_TYPES and pause_start is None:
            pause_start = ts
        elif event_type in _PAUSE_END_TYPES and pause_start is not None:
            if ts > pause_start:
                pauses.append(PauseInterval(started_at=pause_start, ended_at=ts))
            pause_start = None

    return pauses


def pause_overlap_seconds(
    pauses: list[PauseInterval],
    window_start: datetime,
    window_end: datetime,
) -> float:
    """Seconds of explicit pause overlapping [window_start, window_end]."""
    if window_end <= window_start or not pauses:
        return 0.0
    total = 0.0
    for pause in pauses:
        lo = max(pause.started_at, window_start)
        hi = min(pause.ended_at, window_end)
        if hi > lo:
            total += (hi - lo).total_seconds()
    return total


def active_seconds_between(
    pauses: list[PauseInterval],
    interval_start: datetime,
    interval_end: datetime,
) -> float:
    """Wall-clock span minus explicit pause overlap."""
    if interval_end <= interval_start:
        return 0.0
    elapsed = (interval_end - interval_start).total_seconds()
    return max(0.0, elapsed - pause_overlap_seconds(pauses, interval_start, interval_end))


def timestamp_in_explicit_pause(
    timestamp: datetime,
    pauses: list[PauseInterval],
) -> bool:
    """True when timestamp falls strictly inside an explicit pause interval."""
    for pause in pauses:
        if pause.started_at < timestamp < pause.ended_at:
            return True
    return False
