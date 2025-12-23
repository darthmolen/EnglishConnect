"""User progress and practice session models."""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, Float, Integer, String, Text, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class UserProgress(Base):
    """Track user progress through lessons.

    Tracks both lesson-level status and current phase within the lesson.
    phase_state stores flexible state data like vocab_index, pattern_index.
    """

    __tablename__ = "user_progress"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))
    lesson_id: Mapped[int] = mapped_column(Integer, ForeignKey("lessons.id"))
    status: Mapped[str] = mapped_column(
        String(20), default="not_started"
    )  # not_started, in_progress, completed
    started_at: Mapped[datetime | None] = mapped_column(DateTime)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime)

    # Phase tracking
    phase_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("lesson_phases.id"), nullable=True
    )
    phase_state: Mapped[dict | None] = mapped_column(
        JSONB
    )  # {"vocab_index": 0, "pattern_index": 0, "items_completed": [], "can_skip_ahead": false}

    # Relationships
    user: Mapped["User"] = relationship(back_populates="progress")
    lesson: Mapped["Lesson"] = relationship()
    current_phase: Mapped["LessonPhase"] = relationship()

    __table_args__ = ({"sqlite_autoincrement": True},)


class VocabularyMastery(Base):
    """Track mastery of individual vocabulary items."""

    __tablename__ = "vocabulary_mastery"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))
    vocabulary_id: Mapped[int] = mapped_column(Integer, ForeignKey("vocabulary_items.id"))
    times_practiced: Mapped[int] = mapped_column(Integer, default=0)
    times_correct: Mapped[int] = mapped_column(Integer, default=0)
    last_practiced: Mapped[datetime | None] = mapped_column(DateTime)
    mastery_level: Mapped[int] = mapped_column(Integer, default=0)  # 0-5 scale


class PatternMastery(Base):
    """Track mastery of Q&A patterns."""

    __tablename__ = "pattern_mastery"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))
    pattern_id: Mapped[int] = mapped_column(Integer, ForeignKey("qa_patterns.id"))
    times_practiced: Mapped[int] = mapped_column(Integer, default=0)
    fluency_score: Mapped[float | None] = mapped_column(Float)  # 0-1 based on response time
    last_practiced: Mapped[datetime | None] = mapped_column(DateTime)


class PracticeSession(Base):
    """Track practice sessions (demo, conversation, etc.)."""

    __tablename__ = "practice_sessions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))
    lesson_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("lessons.id"))
    session_type: Mapped[str] = mapped_column(
        String(50)
    )  # 'demo', 'conversation_practice', 'vocabulary_drill'
    started_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    ended_at: Mapped[datetime | None] = mapped_column(DateTime)
    duration_seconds: Mapped[int | None] = mapped_column(Integer)
    exchanges_count: Mapped[int] = mapped_column(Integer, default=0)
    feedback_summary: Mapped[dict | None] = mapped_column(JSONB)

    # Relationships
    user: Mapped["User"] = relationship(back_populates="sessions")
    lesson: Mapped["Lesson"] = relationship()


class ConversationExchange(Base):
    """Individual exchanges within a practice session."""

    __tablename__ = "conversation_exchanges"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    session_id: Mapped[int] = mapped_column(Integer, ForeignKey("practice_sessions.id"))
    sequence_number: Mapped[int] = mapped_column(Integer, nullable=False)
    agent_utterance: Mapped[str | None] = mapped_column(Text)
    user_utterance: Mapped[str | None] = mapped_column(Text)
    user_audio_url: Mapped[str | None] = mapped_column(String(500))
    transcription_confidence: Mapped[float | None] = mapped_column(Float)
    pronunciation_feedback: Mapped[dict | None] = mapped_column(JSONB)
    grammar_feedback: Mapped[dict | None] = mapped_column(JSONB)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


# Import for type hints (avoid circular imports at runtime)
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.models.user import User
    from app.models.content import Lesson, LessonPhase
