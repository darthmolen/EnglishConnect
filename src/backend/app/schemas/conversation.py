"""Pydantic schemas for conversation API endpoints."""

from typing import Literal

from pydantic import BaseModel


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


class ConversationResponse(BaseModel):
    """Response body for conversation endpoint."""

    text: str
    lesson_number: int
    audio_base64: str | None = None
    audio_format: str = "wav"
    language: str = "en"  # Language the agent chose to respond in
