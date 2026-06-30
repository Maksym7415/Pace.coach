"""Athlete performance profile models."""
import enum
from datetime import date, datetime

from sqlalchemy import Boolean, Date, Float, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.core.database import Base


class ZoneSourceEnum(str, enum.Enum):
    manual = "manual"
    garmin = "garmin"
    strava = "strava"
    ftp_calculation = "ftp_calculation"
    threshold_pace_calculation = "threshold_pace_calculation"
    threshold_hr_calculation = "threshold_hr_calculation"


class ZoneCategoryEnum(str, enum.Enum):
    hr = "hr"
    pace = "pace"
    power = "power"


class Sport(Base):
    __tablename__ = "sports"

    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean(), nullable=False, default=True)
    created_at: Mapped[datetime | None] = mapped_column(default=datetime.utcnow)


class AthleteSport(Base):
    __tablename__ = "athlete_sports"

    id: Mapped[int] = mapped_column(primary_key=True)
    athlete_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    sport_id: Mapped[int] = mapped_column(
        ForeignKey("sports.id", ondelete="CASCADE"), nullable=False
    )
    is_primary: Mapped[bool] = mapped_column(Boolean(), nullable=False, default=False)
    created_at: Mapped[datetime | None] = mapped_column(default=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint("athlete_id", "sport_id", name="uq_athlete_sports_athlete_sport"),
    )

    sport = relationship("Sport")


class AthleteSportProfile(Base):
    __tablename__ = "athlete_sport_profiles"

    id: Mapped[int] = mapped_column(primary_key=True)
    athlete_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    sport_id: Mapped[int] = mapped_column(
        ForeignKey("sports.id", ondelete="CASCADE"), nullable=False
    )

    threshold_pace_sec_per_km: Mapped[int | None] = mapped_column(Integer(), nullable=True)
    threshold_hr: Mapped[int | None] = mapped_column(Integer(), nullable=True)
    ftp_watts: Mapped[int | None] = mapped_column(Integer(), nullable=True)
    css_pace_sec_per_100m: Mapped[int | None] = mapped_column(Integer(), nullable=True)
    zone_source: Mapped[str | None] = mapped_column(String(50), nullable=True)

    created_at: Mapped[datetime | None] = mapped_column(default=datetime.utcnow)
    updated_at: Mapped[datetime | None] = mapped_column(
        default=datetime.utcnow, onupdate=datetime.utcnow
    )

    __table_args__ = (
        UniqueConstraint(
            "athlete_id", "sport_id", name="uq_athlete_sport_profiles_athlete_sport"
        ),
    )

    sport = relationship("Sport")
    zones = relationship(
        "AthleteZone", back_populates="sport_profile", cascade="all, delete-orphan"
    )


class AthleteZone(Base):
    __tablename__ = "athlete_zones"

    id: Mapped[int] = mapped_column(primary_key=True)
    athlete_sport_profile_id: Mapped[int] = mapped_column(
        ForeignKey("athlete_sport_profiles.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    zone_category: Mapped[str] = mapped_column(String(50), nullable=False)
    zone_name: Mapped[str] = mapped_column(String(50), nullable=False)
    min_value: Mapped[float] = mapped_column(Float(), nullable=False)
    max_value: Mapped[float] = mapped_column(Float(), nullable=False)
    created_at: Mapped[datetime | None] = mapped_column(default=datetime.utcnow)

    sport_profile = relationship("AthleteSportProfile", back_populates="zones")


class AthleteBaseline(Base):
    __tablename__ = "athlete_baselines"

    id: Mapped[int] = mapped_column(primary_key=True)
    athlete_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True
    )
    hrv_baseline_min: Mapped[float | None] = mapped_column(Float(), nullable=True)
    hrv_baseline_max: Mapped[float | None] = mapped_column(Float(), nullable=True)
    resting_hr_baseline: Mapped[float | None] = mapped_column(Float(), nullable=True)
    created_at: Mapped[datetime | None] = mapped_column(default=datetime.utcnow)
    updated_at: Mapped[datetime | None] = mapped_column(
        default=datetime.utcnow, onupdate=datetime.utcnow
    )


class AthleteBodyMetric(Base):
    __tablename__ = "athlete_body_metrics"

    id: Mapped[int] = mapped_column(primary_key=True)
    athlete_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    weight_kg: Mapped[float | None] = mapped_column(Float(), nullable=True)
    height_cm: Mapped[float | None] = mapped_column(Float(), nullable=True)
    measured_at: Mapped[date] = mapped_column(Date(), nullable=False)
    created_at: Mapped[datetime | None] = mapped_column(default=datetime.utcnow)
