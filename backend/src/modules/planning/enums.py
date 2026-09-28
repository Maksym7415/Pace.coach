"""Planning-domain enums (application-layer, stored as VARCHAR)."""
from __future__ import annotations

import enum


class TrainingPlanStatus(str, enum.Enum):
    draft = "draft"
    active = "active"
    completed = "completed"
    archived = "archived"


class MesocycleFocus(str, enum.Enum):
    base = "base"
    build = "build"
    peak = "peak"
    taper = "taper"
    recovery = "recovery"
    race = "race"
    other = "other"


class CoachReviewStatus(str, enum.Enum):
    draft = "draft"
    approved = "approved"


class PlanOperation(str, enum.Enum):
    """What a mutation is trying to do. Drives the lock permission matrix."""

    metadata = "metadata"
    structure = "structure"
    dates = "dates"
    association = "association"
    delete = "delete"


class ChangeLogEntityType(str, enum.Enum):
    training_plan = "training_plan"
    mesocycle = "mesocycle"
    microcycle = "microcycle"
    plan_item = "plan_item"
    coach_review = "coach_review"


class LockState(str, enum.Enum):
    locked = "locked"
    current = "current"
    future = "future"


class PlacementType(str, enum.Enum):
    relative_day = "relative_day"
    specific_date = "specific_date"
