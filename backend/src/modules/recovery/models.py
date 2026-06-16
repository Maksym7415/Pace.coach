"""Recovery data models."""
from datetime import date, datetime

from sqlalchemy import Date, Float, ForeignKey, Integer, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.core.database import Base


class RecoveryEntry(Base):
    __tablename__ = "recovery_entries"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    entry_date: Mapped[date] = mapped_column(Date(), nullable=False)

    hrv_ms: Mapped[float | None] = mapped_column(Float(), nullable=True)
    resting_hr_bpm: Mapped[int | None] = mapped_column(Integer(), nullable=True)
    body_battery: Mapped[int | None] = mapped_column(Integer(), nullable=True)

    fatigue: Mapped[int | None] = mapped_column(Integer(), nullable=True)
    soreness: Mapped[int | None] = mapped_column(Integer(), nullable=True)
    mood: Mapped[int | None] = mapped_column(Integer(), nullable=True)
    sleep_quality: Mapped[int | None] = mapped_column(Integer(), nullable=True)
    sleep_hours: Mapped[float | None] = mapped_column(Float(), nullable=True)

    readiness_score: Mapped[int | None] = mapped_column(Integer(), nullable=True)

    notes: Mapped[str | None] = mapped_column(Text(), nullable=True)

    created_at: Mapped[datetime | None] = mapped_column(default=datetime.utcnow)
    updated_at: Mapped[datetime | None] = mapped_column(
        default=datetime.utcnow, onupdate=datetime.utcnow
    )

    __table_args__ = (
        UniqueConstraint("user_id", "entry_date", name="uq_recovery_user_date"),
    )

    user = relationship("User", back_populates="recovery_entries")
