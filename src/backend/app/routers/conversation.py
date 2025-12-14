"""Conversation API router for AI-powered English practice."""

import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.schemas.conversation import ConversationRequest, ConversationResponse
from app.services.lesson_service import LessonService
from app.services.azure_openai import get_agent_response
from app.services.tts_service import synthesize_speech
from app.agents.conversation_agent import ConversationAgentFactory
from app.config import get_settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/conversation", tags=["conversation"])


async def speak_tool_handler(
    text: str,
    language: str,
    voice: str = "speaker_b"
) -> dict:
    """Handle speak tool calls from the agent.

    This calls the TTS service to synthesize speech and returns
    the audio data.

    Args:
        text: Text to speak
        language: Language code (en or es)
        voice: Voice ID

    Returns:
        Dict with audio_base64 and metadata
    """
    try:
        result = await synthesize_speech(text=text, voice=voice)
        return {
            "spoken": True,
            "text": text,
            "language": language,
            "audio_base64": result["audio_base64"],
            "format": result["format"],
            "sample_rate": result["sample_rate"],
        }
    except Exception as e:
        logger.error(f"TTS synthesis failed: {e}")
        return {
            "spoken": False,
            "text": text,
            "language": language,
            "error": str(e),
        }


@router.post("", response_model=ConversationResponse)
async def conversation(
    request: ConversationRequest,
    db: AsyncSession = Depends(get_db),
):
    """Process a conversation message and get AI tutor response.

    The AI tutor is an intelligent agent that:
    - Uses the current lesson's vocabulary and patterns
    - Can flip between English and Spanish
    - Controls TTS via the speak() tool

    Args:
        request: ConversationRequest with message, lesson_number, and optional history
        db: Database session dependency

    Returns:
        ConversationResponse with AI-generated text and optional audio

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
    if not settings.azure_openai_endpoint or not settings.azure_openai_api_key:
        # Fallback for development without Azure credentials
        return ConversationResponse(
            text=f"[Azure OpenAI not configured - Lesson {request.lesson_number}]",
            lesson_number=request.lesson_number,
        )

    # Prepare tool handlers
    tool_handlers = {
        "speak": speak_tool_handler
    }

    # Call the agent with tool support
    history = [{"role": m.role, "content": m.content} for m in request.history]

    agent_result = await get_agent_response(
        system_prompt=system_prompt,
        user_message=request.message,
        history=history,
        tool_handlers=tool_handlers,
    )

    # Extract audio from tool results (use last successful speak call)
    audio_base64 = None
    audio_format = "wav"
    language = "en"

    for tool_result in agent_result.get("tool_results", []):
        if tool_result.get("tool") == "speak" and tool_result.get("success"):
            result_data = tool_result.get("result", {})
            if result_data.get("spoken"):
                audio_base64 = result_data.get("audio_base64")
                audio_format = result_data.get("format", "wav")
                language = result_data.get("language", "en")

    # Log agent activity for debugging
    if agent_result.get("tool_calls"):
        logger.info(f"Agent made {len(agent_result['tool_calls'])} tool calls")

    return ConversationResponse(
        text=agent_result["text"],
        lesson_number=request.lesson_number,
        audio_base64=audio_base64,
        audio_format=audio_format,
        language=language,
    )
