"""Register all ORM models with Alembic metadata."""
from src.core.database import Base
from src.modules.gear_track.models import (  # noqa: F401
    Activity,
    ActivityGearUsage,
    Gear,
    GearInstallation,
    GearService,
    GearServiceLog,
)
from src.modules.identity.models import User  # noqa: F401
from src.modules.third_party.strava.models import UserStrava  # noqa: F401

__all__ = ["Base"]
