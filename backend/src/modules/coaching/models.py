"""Coach-athlete relationship models."""
import enum
from datetime import datetime

from sqlalchemy import JSON, Enum as SAEnum, ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.core.database import Base


class RelationStatus(str, enum.Enum):
    pending = "pending"
    active = "active"
    revoked = "revoked"
    rejected = "rejected"


class CoachAthleteRelation(Base):
    __tablename__ = "coach_athlete_relations"

    id: Mapped[int] = mapped_column(primary_key=True)
    coach_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    athlete_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    status: Mapped[RelationStatus] = mapped_column(
        SAEnum(RelationStatus, native_enum=False, length=32),
        nullable=False,
        default=RelationStatus.pending,
    )
    permissions: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime | None] = mapped_column(default=datetime.utcnow)
    updated_at: Mapped[datetime | None] = mapped_column(
        default=datetime.utcnow, onupdate=datetime.utcnow
    )

    __table_args__ = (
        UniqueConstraint("coach_id", "athlete_id", name="uq_coach_athlete"),
    )

    coach = relationship("User", foreign_keys=[coach_id])
    athlete = relationship("User", foreign_keys=[athlete_id])
