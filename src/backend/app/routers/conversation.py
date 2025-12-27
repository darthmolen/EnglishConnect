"""Practice conversation API router for free-form AI-powered English practice.

This router handles unstructured conversation practice where students
can chat freely with the AI tutor. For structured lesson-based learning,
see the lesson router (/api/lesson).
"""

import logging
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.middleware.auth import CurrentUser
from app.schemas.conversation import ConversationRequest, ConversationResponse
from app.services.lesson_service import LessonService
from app.services.azure_openai import get_agent_response
from app.services.tts_service import synthesize_speech
from app.services.tool_handlers import speak_tool_handler
from app.services.session_service import SessionService
from app.agents.conversation_agent import ConversationAgentFactory
from app.config import get_settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/practice/conversation", tags=["practice"])


@router.post("", response_model=ConversationResponse)
async def conversation(
    request: ConversationRequest,
    current_user: CurrentUser,
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

    # Use authenticated user's ID
    user_id = str(current_user.id)

    agent_result = await get_agent_response(
        system_prompt=system_prompt,
        user_message=request.message,
        history=history,
        tool_handlers=tool_handlers,
        user_id=user_id,
    )

    # Extract audio and spoken text from tool results (use last successful speak call)
    audio_base64 = None
    audio_format = "wav"
    language = "en"
    spoken_text = None  # What was actually spoken

    for tool_result in agent_result.get("tool_results", []):
        if tool_result.get("tool") == "speak" and tool_result.get("success"):
            result_data = tool_result.get("result", {})
            if result_data.get("spoken"):
                audio_base64 = result_data.get("audio_base64")
                audio_format = result_data.get("format", "wav")
                language = result_data.get("language", "en")
                spoken_text = result_data.get("text")  # The actual spoken text

    # Use spoken text if available, otherwise fall back to agent's text response
    response_text = spoken_text if spoken_text else agent_result["text"]

    # If agent didn't call speak(), auto-synthesize the response
    if not spoken_text and response_text:
        logger.warning("Agent did NOT call speak() - auto-synthesizing response")
        try:
            tts_result = await synthesize_speech(text=response_text, voice="speaker_b")
            audio_base64 = tts_result["audio_base64"]
            audio_format = tts_result.get("format", "wav")
            language = "en"  # Default to English for auto-synthesis
        except Exception as e:
            logger.error(f"Auto-synthesis failed: {e}")
            # Continue without audio if synthesis fails

    # === LOGGING: Final response to frontend ===
    audio_size = len(audio_base64) if audio_base64 else 0
    logger.info("=" * 60)
    logger.info("RESPONSE TO FRONTEND")
    logger.info(f"  text: {response_text[:100]}{'...' if len(response_text) > 100 else ''}")
    logger.info(f"  audio: {'yes' if audio_base64 else 'NO'} ({audio_size} chars)")
    logger.info(f"  language: {language}")
    logger.info(f"  source: {'speak() tool' if spoken_text else 'auto-synthesis fallback'}")
    logger.info("=" * 60)

    # Record exchange for evaluation (async, non-blocking)
    try:
        session_service = SessionService(db)
        # Get or create session - reuses existing session within 30-minute window
        practice_session = await session_service.get_or_create_session(
            user_id=current_user.id,
            lesson_id=lesson.lesson_number,
            session_type="conversation_practice",
        )
        await session_service.record_exchange(
            session_id=practice_session.id,
            agent_utterance=response_text,
            user_utterance=request.message,
        )
        await db.commit()
    except Exception as e:
        logger.warning(f"Failed to record exchange (non-critical): {e}")
        # Don't fail the request if recording fails

    return ConversationResponse(
        text=response_text,
        lesson_number=request.lesson_number,
        audio_base64=audio_base64,
        audio_format=audio_format,
        language=language,
    )
