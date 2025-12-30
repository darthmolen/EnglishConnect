"""Lesson conversation API router for structured lesson flow."""

import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.middleware.auth import CurrentUser
from app.models.content import Lesson
from app.schemas.lesson_session import (
    AudioChunkSchema,
    LessonConversationRequest,
    LessonConversationResponse,
    LessonPhaseSchema,
    PhaseStateSchema,
)
from app.services.lesson_service import LessonService
from app.services.lesson_progress_service import LessonProgressService
from app.services.azure_openai import get_agent_response, LESSON_AGENT_TOOLS
from app.services.tts_service import synthesize_speech
from app.services.tool_handlers import speak_tool_handler
from app.agents.lesson_teacher_agent import LessonBasedTeacherAgent
from app.config import get_settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/lesson", tags=["lesson"])


@router.post("/conversation", response_model=LessonConversationResponse)
async def lesson_conversation(
    request: LessonConversationRequest,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
    """Process a structured lesson conversation message.

    The teacher agent guides the student through lesson phases:
    - Intro: Welcome and objective
    - Vocabulary: Present and practice words
    - Patterns: Explain Q&A patterns
    - Practice: Apply vocabulary in conversation
    - Wrap-up: Summary and encouragement

    Args:
        request: LessonConversationRequest with message and lesson_number
        current_user: Authenticated user
        db: Database session dependency

    Returns:
        LessonConversationResponse with phase info and audio

    Raises:
        HTTPException: 404 if lesson not found
    """
    # Get lesson details
    lesson_service = LessonService(db)
    lesson = await lesson_service.get_lesson_detail("ec1", request.lesson_number)

    if not lesson:
        raise HTTPException(status_code=404, detail="Lesson not found")

    # Get the lesson's database ID (needed for phase lookup)
    result = await db.execute(
        select(Lesson).where(
            Lesson.course_id == "ec1",
            Lesson.lesson_number == request.lesson_number,
        )
    )
    lesson_model = result.scalar_one_or_none()
    if not lesson_model:
        raise HTTPException(status_code=404, detail="Lesson not found")

    # Get or create user progress with phase tracking
    progress_service = LessonProgressService(db)
    try:
        progress, is_new = await progress_service.get_or_create_progress(
            user_id=current_user.id,
            lesson_id=lesson_model.id,
        )
    except ValueError as e:
        if "No phases defined" in str(e):
            raise HTTPException(
                status_code=500,
                detail=f"Lesson {request.lesson_number} has no phases configured. Please contact support."
            )
        raise

    # Get current phase and state
    phase = progress.current_phase
    phase_state = PhaseStateSchema.model_validate(progress.phase_state or {})

    if not phase:
        raise HTTPException(
            status_code=500,
            detail="Lesson has no phases configured"
        )

    # If section is specified, use that phase instead of user's progress phase
    if request.section:
        section_phase = await progress_service.get_phase_by_type(
            lesson_id=lesson_model.id,
            phase_type=request.section,
        )
        if section_phase:
            logger.info(f"Using section override: {request.section} (was {phase.phase_type})")
            phase = section_phase
            # Reset phase state for the overridden phase
            phase_state = PhaseStateSchema()

    # Build the teacher agent with current phase context
    agent = LessonBasedTeacherAgent(
        lesson=lesson,
        phase=phase,
        phase_state=phase_state,
        instruction_language=request.instruction_language,
    )
    system_prompt = agent.build_system_prompt()

    # Check if Azure OpenAI is configured
    settings = get_settings()
    if not settings.azure_openai_endpoint or not settings.azure_openai_api_key:
        # Fallback for development without Azure credentials
        return LessonConversationResponse(
            text=f"[Azure OpenAI not configured - Lesson {request.lesson_number}]",
            lesson_number=request.lesson_number,
            phase=LessonPhaseSchema.model_validate(phase),
            phase_state=phase_state,
            phase_progress=None,
        )

    # State to track phase changes during tool execution
    phase_advanced = False
    new_phase = phase
    new_phase_state = phase_state

    # Tool handlers with closure over progress service
    async def advance_phase_handler(reason: str) -> dict:
        """Handle advance_phase tool calls."""
        nonlocal phase_advanced, new_phase, new_phase_state

        logger.info(f"advance_phase called: {reason}")

        try:
            updated_progress, result = await progress_service.advance_phase(
                progress=progress,
                total_vocab=len(lesson.vocabulary),
                total_patterns=len(lesson.patterns),
            )

            # Update local state from service result
            if result.get("action") == "next_phase":
                new_phase = updated_progress.current_phase
                new_phase_state = PhaseStateSchema.model_validate(
                    updated_progress.phase_state or {}
                )
                phase_advanced = True
            elif result.get("action") in ("next_vocab", "next_pattern"):
                new_phase_state = PhaseStateSchema.model_validate(
                    updated_progress.phase_state or {}
                )

            return result
        except ValueError as e:
            return {"success": False, "error": str(e)}

    async def record_attempt_handler(item_type: str, correct: bool) -> dict:
        """Handle record_attempt tool calls."""
        logger.info(f"record_attempt called: type={item_type}, correct={correct}")

        # Determine item_id based on current index
        if item_type == "vocab":
            item_id = f"vocab_{new_phase_state.vocab_index}"
        else:
            item_id = f"pattern_{new_phase_state.pattern_index}"

        await progress_service.record_attempt(
            progress=progress,
            item_type=item_type,
            item_id=item_id,
            correct=correct,
        )

        return {"recorded": True, "item_type": item_type, "correct": correct}

    async def set_pattern_handler(pattern_index: int) -> dict:
        """Handle set_pattern tool calls to jump to a specific pattern."""
        nonlocal new_phase_state

        logger.info(f"set_pattern called: pattern_index={pattern_index}")

        # Validate index
        total_patterns = len(lesson.patterns)
        if pattern_index < 0 or pattern_index >= total_patterns:
            return {
                "success": False,
                "error": f"Invalid pattern index. Must be 0-{total_patterns - 1}"
            }

        # Update phase state with new pattern index
        new_phase_state.pattern_index = pattern_index
        progress.phase_state = new_phase_state.model_dump()

        # Persist the change
        await db.flush()

        # Get the pattern info for confirmation
        pattern = lesson.patterns[pattern_index]

        return {
            "success": True,
            "pattern_index": pattern_index,
            "pattern_number": pattern_index + 1,
            "question_template": pattern.question_template,
            "total_patterns": total_patterns
        }

    tool_handlers = {
        "speak": speak_tool_handler,
        "advance_phase": advance_phase_handler,
        "record_attempt": record_attempt_handler,
        "set_pattern": set_pattern_handler,
    }

    # Call the agent with lesson-specific tools
    history = [{"role": m.role, "content": m.content} for m in request.history]

    agent_result = await get_agent_response(
        system_prompt=system_prompt,
        user_message=request.message,
        history=history,
        tool_handlers=tool_handlers,
        user_id=str(current_user.id),
        tools=LESSON_AGENT_TOOLS,
    )

    # Extract audio from tool results - ACCUMULATE all chunks, not just last one
    audio_chunks: list[AudioChunkSchema] = []
    # Also keep last values for backward compatibility
    audio_base64 = None
    audio_format = "wav"
    language = "en"
    spoken_text = None

    for tool_result in agent_result.get("tool_results", []):
        if tool_result.get("tool") == "speak" and tool_result.get("success"):
            result_data = tool_result.get("result", {})
            if result_data.get("spoken"):
                # Accumulate audio chunk
                audio_chunks.append(AudioChunkSchema(
                    audio_base64=result_data.get("audio_base64", ""),
                    format=result_data.get("format", "wav"),
                    language=result_data.get("language", "en"),
                    text=result_data.get("text", ""),
                ))
                # Keep last values for backward compatibility
                audio_base64 = result_data.get("audio_base64")
                audio_format = result_data.get("format", "wav")
                language = result_data.get("language", "en")
                spoken_text = result_data.get("text")

    # Build response text from all audio chunks (bilingual support)
    # This ensures both Spanish and English spoken texts appear in the transcript
    # Use double newline for visual separation between utterances in UI
    if audio_chunks:
        response_text = "\n\n".join(chunk.text for chunk in audio_chunks)
    else:
        response_text = agent_result["text"]

    # Auto-synthesize if agent didn't call speak
    if not audio_chunks and response_text:
        logger.warning("Agent did NOT call speak() - auto-synthesizing response")
        try:
            tts_result = await synthesize_speech(text=response_text, voice="speaker_b")
            audio_base64 = tts_result["audio_base64"]
            audio_format = tts_result.get("format", "wav")
            language = "en"
            # Also add to chunks
            audio_chunks.append(AudioChunkSchema(
                audio_base64=tts_result["audio_base64"],
                format=tts_result.get("format", "wav"),
                language="en",
                text=response_text,
            ))
        except Exception as e:
            logger.error(f"Auto-synthesis failed: {e}")

    # Commit any state changes
    await db.commit()

    # Reload progress to get updated phase if advanced
    if phase_advanced:
        progress = await progress_service.get_user_progress(current_user.id, lesson_model.id)
        new_phase = progress.current_phase
        new_phase_state = PhaseStateSchema.model_validate(progress.phase_state or {})

    # Build response with updated phase info
    # Recreate agent with potentially new phase for progress calculation
    updated_agent = LessonBasedTeacherAgent(
        lesson=lesson,
        phase=new_phase,
        phase_state=new_phase_state,
        instruction_language=request.instruction_language,
    )

    return LessonConversationResponse(
        text=response_text,
        lesson_number=request.lesson_number,
        phase=LessonPhaseSchema.model_validate(new_phase),
        phase_state=new_phase_state,
        phase_progress=updated_agent.get_phase_progress(),
        audio_base64=audio_base64,  # Backward compat: last audio
        audio_format=audio_format,
        language=language,
        audio_chunks=audio_chunks if audio_chunks else None,  # All audio in order
    )
