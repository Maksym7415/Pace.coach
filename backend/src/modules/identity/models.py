"""User account and auth domain models."""
import enum
from datetime import datetime

from sqlalchemy import Enum as SAEnum, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.core.database import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(String(30), unique=True, nullable=False, index=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    avatar_url: Mapped[str | None] = mapped_column(String(512), nullable=True)
    preferred_distance_unit: Mapped[str | None] = mapped_column(String(8), nullable=True, default="km")
    expo_push_token: Mapped[str | None] = mapped_column(String(512), nullable=True)
    password_reset_token: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    password_reset_expires_at: Mapped[datetime | None] = mapped_column(nullable=True)
    created_at: Mapped[datetime | None] = mapped_column(default=datetime.utcnow)

    user_strava = relationship("UserStrava", back_populates="user", uselist=False)
    gear = relationship("Gear", back_populates="user", cascade="all, delete-orphan")
    activities = relationship("Activity", back_populates="user", cascade="all, delete-orphan")
    roles = relationship("UserRole", back_populates="user", cascade="all, delete-orphan")
    recovery_entries = relationship(
        "RecoveryEntry", back_populates="user", cascade="all, delete-orphan"
    )


class UserRoleEnum(str, enum.Enum):
    athlete = "athlete"
    coach = "coach"


class UserRole(Base):
    __tablename__ = "user_roles"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    role: Mapped[UserRoleEnum] = mapped_column(
        SAEnum(UserRoleEnum, native_enum=False, length=32), nullable=False
    )
    created_at: Mapped[datetime | None] = mapped_column(default=datetime.utcnow)

    __table_args__ = (UniqueConstraint("user_id", "role", name="uq_user_roles_user_role"),)

    user = relationship("User", back_populates="roles")
