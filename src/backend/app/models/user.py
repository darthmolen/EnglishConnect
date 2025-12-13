"""User and user settings models."""

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, Integer, String, Text, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class User(Base):
    """User account model."""

    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    display_name: Mapped[str | None] = mapped_column(String(100))
    oauth_provider: Mapped[str | None] = mapped_column(String(50))  # 'google', 'microsoft'
    oauth_id: Mapped[str | None] = mapped_column(String(255))
    native_language: Mapped[str] = mapped_column(String(10), default="es")
    timezone: Mapped[str] = mapped_column(String(50), default="America/Los_Angeles")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    # Relationships
    settings: Mapped["UserSettings"] = relationship(back_populates="user", uselist=False)
    progress: Mapped[list["UserProgress"]] = relationship(back_populates="user")
    sessions: Mapped[list["PracticeSession"]] = relationship(back_populates="user")


class UserSettings(Base):
    """User preferences and settings."""

    __tablename__ = "user_settings"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), primary_key=True
    )
    daily_goal_minutes: Mapped[int] = mapped_column(Integer, default=15)
    notification_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    reminder_times: Mapped[dict] = mapped_column(JSONB, default=["08:00", "18:00"])
    voice_preference: Mapped[str] = mapped_column(String(50), default="neutral")
    tts_speed: Mapped[float] = mapped_column(Float, default=1.0)

    # Relationships
    user: Mapped["User"] = relationship(back_populates="settings")


# Import for type hints (avoid circular imports)
from app.models.progress import UserProgress, PracticeSession  # noqa: E402
