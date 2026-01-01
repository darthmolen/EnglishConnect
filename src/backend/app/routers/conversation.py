"""Unified conversation API router for AI-powered English practice.

This router handles both modes via the UnifiedTeachingAgent:
- Help mode: Vocabulary page - agent answers questions only
- Practice mode: Practice page - agent leads conversation, flips roles

See ADR-005 for architecture decision.
"""

import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.middleware.auth import CurrentUser
from app.schemas.conversation import ConversationRequest, ConversationResponse
from app.services.lesson_service import LessonService
from app.services.azure_openai import get_agent_response, UNIFIED_AGENT_TOOLS
from app.services.tts_service import synthesize_speech
from app.services.tool_handlers import (
    speak_tool_handler,
    create_teaching_help_handler,
    create_record_attempt_handler,
)
from app.services.session_service import SessionService
from app.agents.unified_teaching_agent import UnifiedTeachingAgent
from app.models.performance import PerformanceContext
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

    The unified teaching agent operates in two modes:
    - "help": Vocabulary page - answers questions only, uses get_teaching_help
    - "practice": Practice page - leads conversation, flips roles after 3-5 exchanges

    Args:
        request: ConversationRequest with message, lesson_number, mode, exchange_count
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

    # Check if Azure OpenAI is configured
    settings = get_settings()
    if not settings.azure_openai_endpoint or not settings.azure_openai_api_key:
        # Fallback for development without Azure credentials
        return ConversationResponse(
            text=f"[Azure OpenAI not configured - Lesson {request.lesson_number}]",
            lesson_number=request.lesson_number,
        )

    # Create performance context for tracking struggles
    performance_context = PerformanceContext()

    # Build system prompt using UnifiedTeachingAgent
    agent = UnifiedTeachingAgent(
        lesson=lesson,
        mode=request.mode,
        exchange_count=request.exchange_count,
        instruction_language=request.instruction_language,
        performance_context=performance_context,
        focus_pattern=request.focus_pattern,
    )
    system_prompt = agent.build_system_prompt()

    # Prepare tool handlers
    tool_handlers = {
        "speak": speak_tool_handler,
        "get_teaching_help": create_teaching_help_handler(db, request.lesson_number),
        "record_attempt": create_record_attempt_handler(performance_context),
    }

    # Call the agent with tool support
    history = [{"role": m.role, "content": m.content} for m in request.history]

    # Use authenticated user's ID
    user_id = str(current_user.id)

    focus_info = f", focus_pattern={request.focus_pattern}" if request.focus_pattern else ""
    logger.info(f"Conversation request: mode={request.mode}, exchange_count={request.exchange_count}{focus_info}")

    agent_result = await get_agent_response(
        system_prompt=system_prompt,
        user_message=request.message,
        history=history,
        tool_handlers=tool_handlers,
        user_id=user_id,
        tools=UNIFIED_AGENT_TOOLS,
    )

    # Extract audio and spoken text from tool results
    # Collect all speak() calls for multi-audio support
    audio_base64 = None
    audio_format = "wav"
    language = "en"
    spoken_text = None
    english_speak = None
    spanish_speak = None

    for tool_result in agent_result.get("tool_results", []):
        if tool_result.get("tool") == "speak" and tool_result.get("success"):
            result_data = tool_result.get("result", {})
            if result_data.get("spoken"):
                result_lang = result_data.get("language", "en")
                # Capture first of each language type
                if result_lang == "en" and english_speak is None:
                    english_speak = result_data
                elif result_lang == "es" and spanish_speak is None:
                    spanish_speak = result_data

    # Prefer English, fall back to Spanish only if no English speak() was called
    chosen_speak = english_speak if english_speak else spanish_speak
    if chosen_speak:
        audio_base64 = chosen_speak.get("audio_base64")
        audio_format = chosen_speak.get("format", "wav")
        language = chosen_speak.get("language", "en")
        spoken_text = chosen_speak.get("text")
        if english_speak and spanish_speak:
            logger.info(
                "Agent made both EN and ES speak() calls - using English. "
                f"EN: {english_speak.get('text', '')[:50]}... "
                f"ES: {spanish_speak.get('text', '')[:50]}..."
            )

    # Use spoken text if available, otherwise fall back to agent's text response
    response_text = spoken_text if spoken_text else agent_result["text"]

    # If agent didn't call speak(), auto-synthesize the response
    if not spoken_text and response_text:
        logger.warning("Agent did NOT call speak() - auto-synthesizing response")
        try:
            tts_result = await synthesize_speech(text=response_text, voice="speaker_b")
            audio_base64 = tts_result["audio_base64"]
            audio_format = tts_result.get("format", "wav")
            language = "en"
        except Exception as e:
            logger.error(f"Auto-synthesis failed: {e}")

    # Log response summary
    audio_size = len(audio_base64) if audio_base64 else 0
    logger.info(
        f"Response: mode={request.mode}, text_len={len(response_text)}, "
        f"audio={'yes' if audio_base64 else 'no'} ({audio_size} chars), lang={language}"
    )

    # Record exchange for evaluation (non-blocking)
    try:
        session_service = SessionService(db)
        session_type = f"unified_{request.mode}"
        practice_session = await session_service.get_or_create_session(
            user_id=current_user.id,
            lesson_id=lesson.lesson_number,
            session_type=session_type,
        )
        await session_service.record_exchange(
            session_id=practice_session.id,
            agent_utterance=response_text,
            user_utterance=request.message,
        )
        await db.commit()
    except Exception as e:
        logger.warning(f"Failed to record exchange (non-critical): {e}")

    return ConversationResponse(
        text=response_text,
        lesson_number=request.lesson_number,
        audio_base64=audio_base64,
        audio_format=audio_format,
        language=language,
    )
