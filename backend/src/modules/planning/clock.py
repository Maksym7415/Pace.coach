"""Single source of 'today' for planning lock and reflow decisions.

Planning dates are civil dates. The lock boundary is the athlete's local date,
never the server's. UTC is the fallback when `planning_timezone` is NULL.
"""
from __future__ import annotations

from datetime import date, datetime
from zoneinfo import ZoneInfo, available_timezones

DEFAULT_PLANNING_TIMEZONE = "UTC"

_TIMEZONES = available_timezones()


def is_valid_timezone(name: str | None) -> bool:
    if name is None:
        return True
    return name in _TIMEZONES


def resolve_planning_timezone(plan: object) -> ZoneInfo:
    """`plan.planning_timezone`, falling back to UTC."""
    name = getattr(plan, "planning_timezone", None) or DEFAULT_PLANNING_TIMEZONE
    if name not in _TIMEZONES:
        name = DEFAULT_PLANNING_TIMEZONE
    return ZoneInfo(name)


def planning_today(plan: object) -> date:
    """The athlete's current civil date for this plan."""
    return datetime.now(resolve_planning_timezone(plan)).date()
