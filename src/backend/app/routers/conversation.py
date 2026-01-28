"""Unified conversation API router for AI-powered English practice.

This router handles both modes via the UnifiedTeachingAgent:
- Help mode: Vocabulary page - agent answers questions only
- Practice mode: Practice page - agent leads conversation, flips roles

See ADR-005 for architecture decision.
"""

import logging
import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.utils.timing import log_timing, request_id_var

from app.database import get_db
from app.middleware.auth import CurrentUser
from app.schemas.conversation import ConversationRequest, ConversationResponse, AudioChunk
from app.services.lesson_service import LessonService
from app.services.azure_openai import get_agent_response, UNIFIED_AGENT_TOOLS
from app.services.tts_service import synthesize_speech
from app.services.tool_handlers import (
    speak_tool_handler,
    create_teaching_help_handler,
    create_record_attempt_handler,
    create_render_vocabulary_handler,
    create_render_vocabulary_list_handler,
    create_render_pattern_handler,
)
from app.schemas.conversation import RichContent
from app.services.session_service import SessionService
from app.services.helping_phrase_service import HelpingPhraseService
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
    # T1: Request received - start timing
    req_id = str(uuid.uuid4())[:8]
    request_id_var.set(req_id)
    log_timing("T1", "request_received", mode=request.mode, lesson=request.lesson_number)

    # Get lesson context
    service = LessonService(db)
    lesson = await service.get_lesson_detail("ec1", request.lesson_number)

    if not lesson:
        raise HTTPException(status_code=404, detail="Lesson not found")

    # Check if Azure OpenAI is configured
    # In Azure: uses managed identity (azure_client_id), no API key needed
    # In local dev: uses API key
    settings = get_settings()
    has_managed_identity = bool(settings.azure_client_id)
    has_api_key = bool(settings.azure_openai_api_key)
    if not settings.azure_openai_endpoint or (not has_managed_identity and not has_api_key):
        # Fallback for development without Azure credentials
        return ConversationResponse(
            text=f"[Azure OpenAI not configured - Lesson {request.lesson_number}]",
            lesson_number=request.lesson_number,
        )

    # Create performance context for tracking struggles
    performance_context = PerformanceContext()

    # Load helping phrases for the instruction language (practice mode only)
    helping_phrases = []
    if request.mode == "practice":
        phrase_service = HelpingPhraseService(db)
        helping_phrases = await phrase_service.get_phrases_for_language(
            request.instruction_language
        )

    # Build system prompt using UnifiedTeachingAgent
    agent = UnifiedTeachingAgent(
        lesson=lesson,
        mode=request.mode,
        exchange_count=request.exchange_count,
        instruction_language=request.instruction_language,
        performance_context=performance_context,
        focus_pattern=request.focus_pattern,
        helping_phrases=helping_phrases,
    )
    system_prompt = agent.build_system_prompt()

    # Prepare tool handlers
    tool_handlers = {
        "speak": speak_tool_handler,
        "get_teaching_help": create_teaching_help_handler(db, request.lesson_number),
        "record_attempt": create_record_attempt_handler(performance_context),
        "render_vocabulary": create_render_vocabulary_handler(db, request.lesson_number),
        "render_vocabulary_list": create_render_vocabulary_list_handler(db, request.lesson_number),
        "render_pattern": create_render_pattern_handler(db, request.lesson_number),
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

    # Extract audio, spoken text, and rich content from tool results
    # Collect ALL speak() calls in order for sequential playback
    audio_chunks: list[AudioChunk] = []
    rich_content_items: list[RichContent] = []

    for tool_result in agent_result.get("tool_results", []):
        if tool_result.get("tool") == "speak" and tool_result.get("success"):
            result_data = tool_result.get("result", {})
            if result_data.get("spoken") and result_data.get("audio_base64"):
                audio_chunks.append(AudioChunk(
                    audio_base64=result_data["audio_base64"],
                    format=result_data.get("format", "wav"),
                    language=result_data.get("language", "en"),
                    text=result_data.get("text", ""),
                ))

        # Collect rich content from render_vocabulary calls
        if tool_result.get("tool") == "render_vocabulary" and tool_result.get("success"):
            result_data = tool_result.get("result", {})
            if result_data.get("rich_content"):
                rich_content_items.append(RichContent(**result_data["rich_content"]))

        # Collect rich content from render_pattern calls
        if tool_result.get("tool") == "render_pattern" and tool_result.get("success"):
            result_data = tool_result.get("result", {})
            if result_data.get("rich_content"):
                rich_content_items.append(RichContent(**result_data["rich_content"]))

        # Collect rich content from render_vocabulary_list calls (batch)
        if tool_result.get("tool") == "render_vocabulary_list" and tool_result.get("success"):
            result_data = tool_result.get("result", {})
            for card in result_data.get("rich_content_list", []):
                rich_content_items.append(RichContent(**card))

    # Backward compatibility: set audio_base64/format/language from first chunk
    audio_base64 = None
    audio_format = "wav"
    language = "en"
    spoken_text = None
    if audio_chunks:
        first_chunk = audio_chunks[0]
        audio_base64 = first_chunk.audio_base64
        audio_format = first_chunk.format
        language = first_chunk.language
        spoken_text = first_chunk.text
        if len(audio_chunks) > 1:
            logger.info(f"Agent made {len(audio_chunks)} speak() calls - all captured in audio_chunks")

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

    # === CONVERSATION LOG (for debugging) ===
    print("\n" + "=" * 60)
    print(f"CONVERSATION [{request.mode.upper()}] Exchange #{request.exchange_count}")
    print("=" * 60)
    print(f"USER: {request.message if request.message else '(session start)'}")
    print("-" * 60)

    # Show all speak() calls with their languages
    if audio_chunks:
        for chunk in audio_chunks:
            lang_label = "🇪🇸 ES" if chunk.language == "es" else "🇺🇸 EN"
            print(f"AGENT [{lang_label}]: {chunk.text}")
    else:
        print(f"AGENT: {response_text}")

    # Show tool calls summary
    tool_calls = agent_result.get("tool_results", [])
    if tool_calls:
        tools_used = [t.get("tool") for t in tool_calls if t.get("tool") != "speak"]
        if tools_used:
            print(f"TOOLS: {', '.join(tools_used)}")
    print("=" * 60 + "\n")

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

    # T9: Response ready to send
    log_timing("T9", "response_sent", text_len=len(response_text), has_audio=bool(audio_base64))

    return ConversationResponse(
        text=response_text,
        lesson_number=request.lesson_number,
        audio_base64=audio_base64,
        audio_format=audio_format,
        language=language,
        rich_content=rich_content_items if rich_content_items else None,
        audio_chunks=audio_chunks if audio_chunks else None,
    )
