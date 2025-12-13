"""Conversation API router for AI-powered English practice."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.schemas.conversation import ConversationRequest, ConversationResponse
from app.services.lesson_service import LessonService
from app.agents.conversation_agent import ConversationAgentFactory

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

    # TODO: Integrate Azure OpenAI for actual AI response
    # For now, return a placeholder response
    response_text = f"[AI Response for lesson {request.lesson_number}]"

    return ConversationResponse(
        text=response_text,
        lesson_number=request.lesson_number,
    )
