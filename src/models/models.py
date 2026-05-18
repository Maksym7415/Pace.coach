"""
SQLAlchemy models for Shoe Tracker.
"""
from datetime import datetime

from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import Index, text

db = SQLAlchemy()


class User(db.Model):
    """User account."""
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(255), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    name = db.Column(db.String(255), nullable=False)
    avatar_url = db.Column(db.String(512), nullable=True)
    preferred_distance_unit = db.Column(db.String(8), nullable=True, default="km")  # "km" or "miles"
    expo_push_token = db.Column(db.String(512), nullable=True)
    password_reset_token = db.Column(db.String(255), nullable=True, index=True)
    password_reset_expires_at = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    user_strava = db.relationship("UserStrava", back_populates="user", uselist=False)
    gear = db.relationship("Gear", back_populates="user", cascade="all, delete-orphan")
    activities = db.relationship("Activity", back_populates="user", cascade="all, delete-orphan")


class UserStrava(db.Model):
    """Strava OAuth tokens per user."""
    __tablename__ = "users_strava"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False)
    strava_athlete_id = db.Column(db.BigInteger, nullable=False, index=True)
    access_token = db.Column(db.String(255), nullable=False)
    refresh_token = db.Column(db.String(255), nullable=False)
    token_expires_at = db.Column(db.DateTime, nullable=False)

    user = db.relationship("User", back_populates="user_strava")


class Activity(db.Model):
    """Activity (run, etc.) for a user."""
    __tablename__ = "activities"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    name = db.Column(db.String(255), nullable=False)
    date = db.Column(db.Date, nullable=False)
    total_distance_km = db.Column(db.Float, nullable=False)
    total_hours = db.Column(db.Float, nullable=True)
    total_sessions = db.Column(db.Float, nullable=True)
    activity_type = db.Column(db.String(32), nullable=True)  # run, bike, swim, other
    source = db.Column(db.String(32), nullable=False)  # "manual" or "strava"
    strava_activity_id = db.Column(db.BigInteger, nullable=True, index=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    user = db.relationship("User", back_populates="activities")
    activity_gear_usages = db.relationship(
        "ActivityGearUsage", back_populates="activity", cascade="all, delete-orphan"
    )

    __table_args__ = (
        # One Strava activity id per user when imported (NULL strava_activity_id allowed for manual rows).
        Index(
            "uq_activities_user_strava_activity",
            "user_id",
            "strava_activity_id",
            unique=True,
            postgresql_where=text("strava_activity_id IS NOT NULL"),
        ),
    )


class Gear(db.Model):
    """Unified gear (shoes, bikes, components, etc.)."""
    __tablename__ = "gear"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    activity_type = db.Column(db.String(32), nullable=False)  # run, bike, swim, other
    gear_type = db.Column(db.String(32), nullable=False)  # shoe, bike, component, etc.
    brand = db.Column(db.String(128), nullable=False)
    model = db.Column(db.String(128), nullable=False)
    nick = db.Column(db.String(128), nullable=True)
    metric_type = db.Column(db.String(32), nullable=False, default="distance")  # distance, hours, sessions
    max_value = db.Column(db.Float, nullable=True)
    value_covered = db.Column(db.Float, default=0.0, nullable=False)
    is_default = db.Column(db.Boolean, default=False)
    status = db.Column(db.String(16), nullable=False, default="active")  # active, retired
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    user = db.relationship("User", back_populates="gear")
    activity_gear_usages = db.relationship(
        "ActivityGearUsage", back_populates="gear", cascade="all, delete-orphan"
    )
    as_parent_installations = db.relationship(
        "GearInstallation", foreign_keys="GearInstallation.parent_gear_id",
        back_populates="parent_gear", cascade="all, delete-orphan"
    )
    as_child_installations = db.relationship(
        "GearInstallation", foreign_keys="GearInstallation.child_gear_id",
        back_populates="child_gear", cascade="all, delete-orphan"
    )
    gear_services = db.relationship(
        "GearService", back_populates="gear", cascade="all, delete-orphan"
    )


class GearInstallation(db.Model):
    """Parent-child gear link with installation history."""
    __tablename__ = "gear_installations"

    id = db.Column(db.Integer, primary_key=True)
    child_gear_id = db.Column(db.Integer, db.ForeignKey("gear.id", ondelete="CASCADE"), nullable=False, index=True)
    parent_gear_id = db.Column(db.Integer, db.ForeignKey("gear.id", ondelete="CASCADE"), nullable=False, index=True)
    installed_at = db.Column(db.DateTime, default=datetime.utcnow)
    removed_at = db.Column(db.DateTime, nullable=True)  # NULL = currently installed

    child_gear = db.relationship("Gear", foreign_keys=[child_gear_id], back_populates="as_child_installations")
    parent_gear = db.relationship("Gear", foreign_keys=[parent_gear_id], back_populates="as_parent_installations")


class ActivityGearUsage(db.Model):
    """Usage for gear: from activity (activity_id set) or manual (activity_id null)."""
    __tablename__ = "activity_gear_usage"

    id = db.Column(db.Integer, primary_key=True)
    activity_id = db.Column(
        db.Integer, db.ForeignKey("activities.id", ondelete="CASCADE"), nullable=True, index=True
    )
    gear_id = db.Column(db.Integer, db.ForeignKey("gear.id", ondelete="CASCADE"), nullable=False, index=True)
    value = db.Column(db.Float, nullable=False)  # distance_km, hours, or sessions per gear.metric_type

    activity = db.relationship("Activity", back_populates="activity_gear_usages")
    gear = db.relationship("Gear", back_populates="activity_gear_usages")


class GearService(db.Model):
    """Service schedule for gear (user-defined name per row)."""
    __tablename__ = "gear_services"

    id = db.Column(db.Integer, primary_key=True)
    gear_id = db.Column(db.Integer, db.ForeignKey("gear.id", ondelete="CASCADE"), nullable=False, index=True)
    name = db.Column(db.String(128), nullable=False)  # user-defined, e.g. "Chain cleaning"
    interval_value = db.Column(db.Float, nullable=False)
    interval_unit = db.Column(db.String(32), nullable=False)  # km, hours, sessions
    early_warning_ratio = db.Column(db.Float, nullable=True)  # e.g. 0.9
    last_performed_value = db.Column(db.Float, nullable=True)  # value_covered at last service

    gear = db.relationship("Gear", back_populates="gear_services")
    logs = db.relationship("GearServiceLog", back_populates="gear_service", cascade="all, delete-orphan")


class GearServiceLog(db.Model):
    """Executed service log."""
    __tablename__ = "gear_service_logs"

    id = db.Column(db.Integer, primary_key=True)
    gear_service_id = db.Column(db.Integer, db.ForeignKey("gear_services.id", ondelete="CASCADE"), nullable=False, index=True)
    performed_at = db.Column(db.DateTime, default=datetime.utcnow)
    value_at_perform = db.Column(db.Float, nullable=False)

    gear_service = db.relationship("GearService", back_populates="logs")
