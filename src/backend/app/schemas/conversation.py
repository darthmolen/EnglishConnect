"""Pydantic schemas for conversation API endpoints."""

from typing import Literal

from pydantic import BaseModel


class ChatMessage(BaseModel):
    """Single chat message in conversation history."""

    role: Literal["user", "assistant"]
    content: str


class ConversationRequest(BaseModel):
    """Request body for POST /api/conversation."""

    message: str
    lesson_number: int
    history: list[ChatMessage] = []


class ConversationResponse(BaseModel):
    """Response body for conversation endpoint."""

    text: str
    lesson_number: int
