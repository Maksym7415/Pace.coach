"""ORM models for activity import and ingestion."""

from datetime import datetime

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    JSON,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.core.database import Base


class StoredFile(Base):
    __tablename__ = "stored_files"

    id: Mapped[int] = mapped_column(primary_key=True)
    provider: Mapped[str] = mapped_column(String(64), nullable=False)
    bucket: Mapped[str] = mapped_column(String(255), nullable=False)
    object_key: Mapped[str] = mapped_column(String(512), nullable=False)
    original_filename: Mapped[str] = mapped_column(String(512), nullable=False)
    mime_type: Mapped[str] = mapped_column(String(128), nullable=False)
    checksum: Mapped[str] = mapped_column(String(128), nullable=False)
    file_size: Mapped[int] = mapped_column(BigInteger, nullable=False)
    created_at: Mapped[datetime | None] = mapped_column(default=datetime.utcnow)

    activity_imports = relationship("ActivityImport", back_populates="stored_file")


class ActivityImport(Base):
    __tablename__ = "activity_imports"

    id: Mapped[int] = mapped_column(primary_key=True)
    athlete_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    stored_file_id: Mapped[int] = mapped_column(
        ForeignKey("stored_files.id", ondelete="CASCADE"), nullable=False, index=True
    )
    source: Mapped[str] = mapped_column(String(32), nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime | None] = mapped_column(default=datetime.utcnow)

    athlete = relationship("User")
    stored_file = relationship("StoredFile", back_populates="activity_imports")
    activity = relationship("Activity", back_populates="activity_import", uselist=False)

    __table_args__ = (
        CheckConstraint(
            "status IN ('pending', 'processing', 'completed', 'failed')",
            name="ck_activity_imports_status",
        ),
    )


class ActivityLap(Base):
    __tablename__ = "activity_laps"

    id: Mapped[int] = mapped_column(primary_key=True)
    activity_id: Mapped[int] = mapped_column(
        ForeignKey("activities.id", ondelete="CASCADE"), nullable=False, index=True
    )
    lap_number: Mapped[int] = mapped_column(Integer, nullable=False)
    duration: Mapped[float | None] = mapped_column(Float, nullable=True)
    timer_time: Mapped[float | None] = mapped_column(Float, nullable=True)
    distance: Mapped[float | None] = mapped_column(Float, nullable=True)
    avg_hr: Mapped[int | None] = mapped_column(Integer, nullable=True)
    max_hr: Mapped[int | None] = mapped_column(Integer, nullable=True)
    avg_power: Mapped[int | None] = mapped_column(Integer, nullable=True)
    avg_speed: Mapped[float | None] = mapped_column(Float, nullable=True)
    avg_pace: Mapped[float | None] = mapped_column(Float, nullable=True)
    start_time: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    message_index: Mapped[int | None] = mapped_column(Integer, nullable=True)
    wkt_step_index: Mapped[int | None] = mapped_column(Integer, nullable=True)
    lap_trigger: Mapped[str | None] = mapped_column(String(64), nullable=True)
    intensity: Mapped[str | None] = mapped_column(String(32), nullable=True)

    activity = relationship("Activity", back_populates="activity_laps")


class ActivityTrackPoint(Base):
    __tablename__ = "activity_track_points"

    id: Mapped[int] = mapped_column(primary_key=True)
    activity_id: Mapped[int] = mapped_column(
        ForeignKey("activities.id", ondelete="CASCADE"), nullable=False, index=True
    )
    timestamp: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    latitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    longitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    altitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    distance: Mapped[float | None] = mapped_column(Float, nullable=True)
    speed: Mapped[float | None] = mapped_column(Float, nullable=True)
    pace: Mapped[float | None] = mapped_column(Float, nullable=True)
    heart_rate: Mapped[int | None] = mapped_column(Integer, nullable=True)
    cadence: Mapped[int | None] = mapped_column(Integer, nullable=True)
    power: Mapped[int | None] = mapped_column(Integer, nullable=True)
    temperature: Mapped[float | None] = mapped_column(Float, nullable=True)
    running_power: Mapped[int | None] = mapped_column(Integer, nullable=True)
    stride_length: Mapped[float | None] = mapped_column(Float, nullable=True)
    vertical_oscillation: Mapped[float | None] = mapped_column(Float, nullable=True)
    ground_contact_time: Mapped[float | None] = mapped_column(Float, nullable=True)
    left_right_balance: Mapped[float | None] = mapped_column(Float, nullable=True)
    stamina: Mapped[float | None] = mapped_column(Float, nullable=True)

    activity = relationship("Activity", back_populates="activity_track_points")


class ActivitySource(Base):
    __tablename__ = "activity_sources"

    id: Mapped[int] = mapped_column(primary_key=True)
    activity_id: Mapped[int] = mapped_column(
        ForeignKey("activities.id", ondelete="CASCADE"), nullable=False, index=True
    )
    provider: Mapped[str] = mapped_column(String(64), nullable=False)
    external_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    raw_metadata: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    activity = relationship("Activity", back_populates="activity_sources")
