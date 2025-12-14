"""Conversation API router for AI-powered English practice."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.schemas.conversation import ConversationRequest, ConversationResponse
from app.services.lesson_service import LessonService
from app.services.azure_openai import get_chat_completion
from app.agents.conversation_agent import ConversationAgentFactory
from app.config import get_settings

router = APIRouter(prefix="/api/conversation", tags=["conversation"])


@router.post("", response_model=ConversationResponse)
async def conversation(
    request: ConversationRequest,
    db: AsyncSession = Depends(get_db),
):
    """Process a conversation message and get AI tutor response.

    The AI tutor uses the current lesson's vocabulary and patterns
    to guide the conversation practice.

    Args:
        request: ConversationRequest with message, lesson_number, and optional history
        db: Database session dependency

    Returns:
        ConversationResponse with AI-generated text

    Raises:
        HTTPException: 404 if lesson not found
    """
    # Get lesson context
    service = LessonService(db)
    lesson = await service.get_lesson_detail("ec1", request.lesson_number)

    if not lesson:
        raise HTTPException(status_code=404, detail="Lesson not found")

    # Build system prompt from lesson context
    system_prompt = ConversationAgentFactory.build_system_prompt(lesson)

    # Check if Azure OpenAI is configured
    settings = get_settings()
    if settings.azure_openai_endpoint and settings.azure_openai_api_key:
        # Call Azure OpenAI
        history = [{"role": m.role, "content": m.content} for m in request.history]
        response_text = await get_chat_completion(
            system_prompt=system_prompt,
            user_message=request.message,
            history=history,
        )
    else:
        # Fallback for development without Azure credentials
        response_text = f"[Azure OpenAI not configured - Lesson {request.lesson_number}]"

    return ConversationResponse(
        text=response_text,
        lesson_number=request.lesson_number,
    )
