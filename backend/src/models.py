"""Register all ORM models with Alembic metadata."""
from src.core.database import Base
from src.modules.gear_track.models import (  # noqa: F401
    Activity,
    ActivityGearUsage,
    ActivityType,
    Gear,
    GearInstallation,
    GearService,
    GearServiceLog,
)
from src.modules.athlete_profile.models import (  # noqa: F401
    AthleteBaseline,
    AthleteBodyMetric,
    AthleteSport,
    AthleteSportProfile,
    AthleteZone,
    Sport,
)
from src.modules.activity_import.models import (  # noqa: F401
    ActivityImport,
    ActivityLap,
    ActivitySource,
    ActivityTrackPoint,
    StoredFile,
)
from src.modules.coaching.models import CoachAthleteRelation  # noqa: F401
from src.modules.identity.models import User, UserRole  # noqa: F401
from src.modules.recovery.models import RecoveryEntry  # noqa: F401
from src.modules.training.models import Workout, WorkoutTemplate  # noqa: F401
from src.modules.third_party.strava.models import UserStrava  # noqa: F401
from src.modules.execution.models import (  # noqa: F401
    ExecutionIssue,
    WorkoutExecution,
    WorkoutPlanSnapshot,
    WorkoutStepExecution,
)

__all__ = ["Base"]
