"""
SQLAlchemy models for Shoe Tracker.
"""
from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
db = SQLAlchemy()


class User(db.Model):
    """User account."""
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(255), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    name = db.Column(db.String(255), nullable=False)
    avatar_url = db.Column(db.String(512), nullable=True)
    expo_push_token = db.Column(db.String(512), nullable=True)
    password_reset_token = db.Column(db.String(255), nullable=True, index=True)
    password_reset_expires_at = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    user_strava = db.relationship("UserStrava", back_populates="user", uselist=False)
    shoes = db.relationship("Shoe", back_populates="user", cascade="all, delete-orphan")
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


class Shoe(db.Model):
    """Shoe entry for a user."""
    __tablename__ = "shoes"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    activity_type = db.Column(db.String(64), nullable=False)  # e.g. "running", "walking"
    brand = db.Column(db.String(128), nullable=False)
    model = db.Column(db.String(128), nullable=False)
    nick = db.Column(db.String(128), nullable=True)
    max_distance_km = db.Column(db.Float, nullable=True)
    distance_covered_km = db.Column(db.Float, default=0.0, nullable=False)
    is_default = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    user = db.relationship("User", back_populates="shoes")
    activity_shoe_distances = db.relationship(
        "ActivityShoeDistance", back_populates="shoe", cascade="all, delete-orphan"
    )


class Activity(db.Model):
    """Activity (run, etc.) for a user."""
    __tablename__ = "activities"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    name = db.Column(db.String(255), nullable=False)
    date = db.Column(db.Date, nullable=False)
    total_distance_km = db.Column(db.Float, nullable=False)
    source = db.Column(db.String(32), nullable=False)  # "manual" or "strava"
    strava_activity_id = db.Column(db.BigInteger, nullable=True, index=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    user = db.relationship("User", back_populates="activities")
    activity_shoe_distances = db.relationship(
        "ActivityShoeDistance", back_populates="activity", cascade="all, delete-orphan"
    )


class ActivityShoeDistance(db.Model):
    """Distance for a shoe: either from an activity (activity_id set) or manual edit (activity_id null)."""
    __tablename__ = "activity_shoe_distance"

    id = db.Column(db.Integer, primary_key=True)
    activity_id = db.Column(
        db.Integer, db.ForeignKey("activities.id", ondelete="CASCADE"), nullable=True, index=True
    )
    shoe_id = db.Column(db.Integer, db.ForeignKey("shoes.id", ondelete="CASCADE"), nullable=False, index=True)
    distance_km = db.Column(db.Float, nullable=False)

    activity = db.relationship("Activity", back_populates="activity_shoe_distances")
    shoe = db.relationship("Shoe", back_populates="activity_shoe_distances")
