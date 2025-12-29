"""Pydantic schemas for structured lesson conversation endpoints."""

from typing import Literal

from pydantic import BaseModel

from app.schemas.conversation import ChatMessage


class PhaseStateSchema(BaseModel):
    """Flexible state bag for phase-specific tracking.

    Tracks progress within a phase (e.g., which vocabulary word,
    which pattern) and mastery indicators.
    """

    vocab_index: int = 0
    pattern_index: int = 0
    items_completed: list[str] = []
    can_skip_ahead: bool = False


class LessonPhaseSchema(BaseModel):
    """Phase definition from database."""

    id: int
    phase_type: str  # 'intro', 'vocabulary', 'patterns', 'practice', 'wrapup'
    phase_name: str  # Display name
    sort_order: int

    model_config = {"from_attributes": True}


class PhaseProgressSchema(BaseModel):
    """Progress indicator within a phase."""

    current: int
    total: int


class LessonConversationRequest(BaseModel):
    """Request body for POST /api/lesson/conversation.

    Structured lesson conversation with phase tracking.
    """

    message: str
    lesson_number: int
    history: list[ChatMessage] = []
    section: str | None = None  # Optional: 'vocabulary', 'patterns', 'practice', etc.


class AudioChunkSchema(BaseModel):
    """Single audio chunk from a speak() tool call."""

    audio_base64: str
    format: str = "wav"
    language: str  # 'en' or 'es'
    text: str  # The text that was spoken


class LessonConversationResponse(BaseModel):
    """Response body for structured lesson conversation.

    Includes phase information for UI display and state management.
    """

    text: str
    lesson_number: int
    phase: LessonPhaseSchema
    phase_state: PhaseStateSchema
    phase_progress: PhaseProgressSchema | None = None  # e.g., {"current": 3, "total": 10}
    audio_base64: str | None = None  # Deprecated: use audio_chunks instead
    audio_format: str = "wav"  # Deprecated: use audio_chunks instead
    language: str = "en"  # Deprecated: use audio_chunks instead
    audio_chunks: list[AudioChunkSchema] | None = None  # All speak() audio in order


class AdvancePhaseRequest(BaseModel):
    """Request to advance to the next phase (used by agent tool)."""

    reason: str


class RecordAttemptRequest(BaseModel):
    """Request to record a student attempt (used by agent tool)."""

    item_type: Literal["vocab", "pattern"]
    correct: bool
