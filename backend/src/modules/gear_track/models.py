"""Gear, activities, and related domain models."""
from datetime import datetime

from sqlalchemy import BigInteger, Boolean, Date, Float, ForeignKey, Index, String, UniqueConstraint, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.core.database import Base


class ActivityType(Base):
    __tablename__ = "activity_types"

    id: Mapped[int] = mapped_column(primary_key=True)
    sport_id: Mapped[int] = mapped_column(
        ForeignKey("sports.id", ondelete="CASCADE"), nullable=False, index=True
    )
    code: Mapped[str] = mapped_column(String(50), nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean(), nullable=False, default=True)
    created_at: Mapped[datetime | None] = mapped_column(default=datetime.utcnow)
    updated_at: Mapped[datetime | None] = mapped_column(
        default=datetime.utcnow, onupdate=datetime.utcnow
    )

    sport = relationship("Sport")

    __table_args__ = (
        UniqueConstraint("sport_id", "code", name="uq_activity_types_sport_code"),
    )


class Activity(Base):
    __tablename__ = "activities"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    date: Mapped[datetime] = mapped_column(Date, nullable=False)
    start_time: Mapped[datetime | None] = mapped_column(nullable=True, index=True)
    total_distance_km: Mapped[float] = mapped_column(Float, nullable=False)
    total_hours: Mapped[float | None] = mapped_column(Float, nullable=True)
    total_sessions: Mapped[float | None] = mapped_column(Float, nullable=True)
    sport_id: Mapped[int | None] = mapped_column(
        ForeignKey("sports.id", ondelete="SET NULL"), nullable=True, index=True
    )
    activity_type_id: Mapped[int | None] = mapped_column(
        ForeignKey("activity_types.id", ondelete="SET NULL"), nullable=True, index=True
    )
    source: Mapped[str] = mapped_column(String(32), nullable=False)
    strava_activity_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True, index=True)
    activity_import_id: Mapped[int | None] = mapped_column(
        ForeignKey("activity_imports.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime | None] = mapped_column(default=datetime.utcnow)

    user = relationship("User", back_populates="activities")
    sport = relationship("Sport")
    activity_type = relationship("ActivityType")
    activity_import = relationship("ActivityImport", back_populates="activity")
    activity_gear_usages = relationship(
        "ActivityGearUsage", back_populates="activity", cascade="all, delete-orphan"
    )
    activity_laps = relationship(
        "ActivityLap", back_populates="activity", cascade="all, delete-orphan"
    )
    activity_track_points = relationship(
        "ActivityTrackPoint", back_populates="activity", cascade="all, delete-orphan"
    )
    activity_sources = relationship(
        "ActivitySource", back_populates="activity", cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index(
            "uq_activities_user_strava_activity",
            "user_id",
            "strava_activity_id",
            unique=True,
            postgresql_where=text("strava_activity_id IS NOT NULL"),
        ),
        Index(
            "uq_activities_activity_import_id",
            "activity_import_id",
            unique=True,
            postgresql_where=text("activity_import_id IS NOT NULL"),
        ),
    )


class Gear(Base):
    __tablename__ = "gear"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    activity_type: Mapped[str] = mapped_column(String(32), nullable=False)
    gear_type: Mapped[str] = mapped_column(String(32), nullable=False)
    brand: Mapped[str] = mapped_column(String(128), nullable=False)
    model: Mapped[str] = mapped_column(String(128), nullable=False)
    nick: Mapped[str | None] = mapped_column(String(128), nullable=True)
    metric_type: Mapped[str] = mapped_column(String(32), nullable=False, default="distance")
    max_value: Mapped[float | None] = mapped_column(Float, nullable=True)
    value_covered: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    is_default: Mapped[bool] = mapped_column(Boolean, default=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="active")
    created_at: Mapped[datetime | None] = mapped_column(default=datetime.utcnow)

    user = relationship("User", back_populates="gear")
    activity_gear_usages = relationship(
        "ActivityGearUsage", back_populates="gear", cascade="all, delete-orphan"
    )
    as_parent_installations = relationship(
        "GearInstallation",
        foreign_keys="GearInstallation.parent_gear_id",
        back_populates="parent_gear",
        cascade="all, delete-orphan",
    )
    as_child_installations = relationship(
        "GearInstallation",
        foreign_keys="GearInstallation.child_gear_id",
        back_populates="child_gear",
        cascade="all, delete-orphan",
    )
    gear_services = relationship(
        "GearService", back_populates="gear", cascade="all, delete-orphan"
    )


class GearInstallation(Base):
    __tablename__ = "gear_installations"

    id: Mapped[int] = mapped_column(primary_key=True)
    child_gear_id: Mapped[int] = mapped_column(
        ForeignKey("gear.id", ondelete="CASCADE"), nullable=False, index=True
    )
    parent_gear_id: Mapped[int] = mapped_column(
        ForeignKey("gear.id", ondelete="CASCADE"), nullable=False, index=True
    )
    installed_at: Mapped[datetime | None] = mapped_column(default=datetime.utcnow)
    removed_at: Mapped[datetime | None] = mapped_column(nullable=True)

    child_gear = relationship("Gear", foreign_keys=[child_gear_id], back_populates="as_child_installations")
    parent_gear = relationship("Gear", foreign_keys=[parent_gear_id], back_populates="as_parent_installations")


class ActivityGearUsage(Base):
    __tablename__ = "activity_gear_usage"

    id: Mapped[int] = mapped_column(primary_key=True)
    activity_id: Mapped[int | None] = mapped_column(
        ForeignKey("activities.id", ondelete="CASCADE"), nullable=True, index=True
    )
    gear_id: Mapped[int] = mapped_column(ForeignKey("gear.id", ondelete="CASCADE"), nullable=False, index=True)
    value: Mapped[float] = mapped_column(Float, nullable=False)

    activity = relationship("Activity", back_populates="activity_gear_usages")
    gear = relationship("Gear", back_populates="activity_gear_usages")


class GearService(Base):
    __tablename__ = "gear_services"

    id: Mapped[int] = mapped_column(primary_key=True)
    gear_id: Mapped[int] = mapped_column(ForeignKey("gear.id", ondelete="CASCADE"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    interval_value: Mapped[float] = mapped_column(Float, nullable=False)
    interval_unit: Mapped[str] = mapped_column(String(32), nullable=False)
    early_warning_ratio: Mapped[float | None] = mapped_column(Float, nullable=True)
    last_performed_value: Mapped[float | None] = mapped_column(Float, nullable=True)

    gear = relationship("Gear", back_populates="gear_services")
    logs = relationship("GearServiceLog", back_populates="gear_service", cascade="all, delete-orphan")


class GearServiceLog(Base):
    __tablename__ = "gear_service_logs"

    id: Mapped[int] = mapped_column(primary_key=True)
    gear_service_id: Mapped[int] = mapped_column(
        ForeignKey("gear_services.id", ondelete="CASCADE"), nullable=False, index=True
    )
    performed_at: Mapped[datetime | None] = mapped_column(default=datetime.utcnow)
    value_at_perform: Mapped[float] = mapped_column(Float, nullable=False)

    gear_service = relationship("GearService", back_populates="logs")
