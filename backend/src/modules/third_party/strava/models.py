"""Strava integration models."""
from datetime import datetime

from sqlalchemy import BigInteger, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.core.database import Base


class UserStrava(Base):
    __tablename__ = "users_strava"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False
    )
    strava_athlete_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)
    access_token: Mapped[str] = mapped_column(String(255), nullable=False)
    refresh_token: Mapped[str] = mapped_column(String(255), nullable=False)
    token_expires_at: Mapped[datetime] = mapped_column(nullable=False)

    user = relationship("User", back_populates="user_strava")
