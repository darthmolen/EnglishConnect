"""Pydantic schemas for conversation API endpoints."""

from typing import Literal

from pydantic import BaseModel


class VocabularyCardData(BaseModel):
    """Data for rendering an inline vocabulary card."""

    english_word: str
    spanish_translation: str
    category: str
    lesson_number: int
    audio_url: str | None = None  # URL to bilingual audio file


class RichContent(BaseModel):
    """Structured content that frontend can render inline in conversation.

    Types:
    - vocabulary_card: Interactive vocab card with audio playback
    - pattern_card: Q&A pattern with demo audio (future)
    - lesson_link: Navigable link to a lesson (future)
    """

    type: Literal["vocabulary_card", "pattern_card", "lesson_link"]
    data: dict  # Type-specific data (VocabularyCardData, etc.)


class AudioChunk(BaseModel):
    """Single audio chunk from a speak() call.

    Multiple chunks enable sequential playback of bilingual responses
    (e.g., speak lesson 6 nouns in Spanish, then lesson 7 nouns).
    """

    audio_base64: str
    format: str = "wav"
    language: str  # "en" or "es"
    text: str  # The text that was spoken


class ChatMessage(BaseModel):
    """Single chat message in conversation history."""

    role: Literal["user", "assistant"]
    content: str


class ConversationRequest(BaseModel):
    """Request body for POST /api/conversation.

    The unified endpoint supports two modes:
    - "help": Vocabulary page - agent answers questions only
    - "practice": Practice page - agent leads conversation, flips roles
    """

    message: str
    lesson_number: int
    mode: Literal["help", "practice"] = "practice"  # Agent mode
    exchange_count: int = 0  # Number of exchanges (for flip detection in practice mode)
    instruction_language: Literal["es", "en"] = "es"  # Language for explanations
    history: list[ChatMessage] = []
    user_id: str | None = None  # Optional user ID for memory tracking
    focus_pattern: int | None = None  # Optional pattern number to focus practice on


class ConversationResponse(BaseModel):
    """Response body for conversation endpoint."""

    text: str
    lesson_number: int
    audio_base64: str | None = None  # Deprecated: use audio_chunks for new code
    audio_format: str = "wav"
    language: str = "en"  # Language the agent chose to respond in
    rich_content: list[RichContent] | None = None  # Inline cards/links to render
    audio_chunks: list[AudioChunk] | None = None  # All speak() audio in order
