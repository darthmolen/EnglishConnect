"""WebSocket router for Azure OpenAI Realtime API integration.

Provides real-time voice conversation using the Realtime API which handles
STT, LLM reasoning, and TTS in a single WebSocket connection.
"""

import asyncio
import base64
import json
import logging
from typing import Optional

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.unified_teaching_agent import UnifiedTeachingAgent
from app.config import get_settings
from app.database import get_db
from app.services.lesson_service import LessonService
from app.services.realtime_session import RealtimeSessionManager

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ws", tags=["realtime"])


async def create_tool_handlers(db: AsyncSession, lesson_number: int) -> dict:
    """Create tool handler functions for the Realtime session.

    Args:
        db: Database session
        lesson_number: Current lesson number

    Returns:
        Dict mapping tool names to async handler functions
    """
    service = LessonService(db)
    lesson = await service.get_lesson_detail("ec1", lesson_number)

    async def get_teaching_help(query: str) -> dict:
        """Retrieve teaching help content."""
        # Return relevant vocabulary or pattern info based on query
        vocab_matches = [
            v for v in lesson.vocabulary
            if query.lower() in v.english.lower() or query.lower() in v.spanish.lower()
        ]
        pattern_matches = [
            p for p in lesson.patterns
            if query.lower() in p.question_template.lower()
            or query.lower() in p.answer_template.lower()
        ]

        return {
            "query": query,
            "vocabulary": [
                {"english": v.english, "spanish": v.spanish}
                for v in vocab_matches[:3]
            ],
            "patterns": [
                {
                    "number": p.pattern_number,
                    "question": p.question_template,
                    "answer": p.answer_template
                }
                for p in pattern_matches[:2]
            ],
            "tip": "Practice saying each word slowly and clearly."
        }

    async def record_attempt(
        expected: str, actual: str, is_correct: bool, feedback: str = ""
    ) -> dict:
        """Record a student attempt (placeholder for progress tracking)."""
        logger.info(f"Attempt recorded: expected='{expected}', actual='{actual}', correct={is_correct}")
        return {
            "recorded": True,
            "expected": expected,
            "actual": actual,
            "is_correct": is_correct,
            "feedback": feedback
        }

    async def render_vocabulary(english_word: str) -> dict:
        """Get vocabulary data for UI rendering."""
        vocab = next(
            (v for v in lesson.vocabulary if v.english.lower() == english_word.lower()),
            None
        )
        if vocab:
            return {
                "english": vocab.english,
                "spanish": vocab.spanish,
                "has_audio": bool(vocab.audio_url)
            }
        return {"english": english_word, "spanish": "", "has_audio": False}

    async def render_pattern(pattern_number: int, lesson_number: int | None = None) -> dict:
        """Get pattern data for UI rendering.

        Args:
            pattern_number: Pattern number to render
            lesson_number: Optional lesson number (ignored - lesson captured in closure)
        """
        pattern = next(
            (p for p in lesson.patterns if p.pattern_number == pattern_number),
            None
        )
        if pattern:
            return {
                "pattern_number": pattern.pattern_number,
                "question": pattern.question_template,
                "answer": pattern.answer_template
            }
        return {"pattern_number": pattern_number, "question": "", "answer": ""}

    return {
        "get_teaching_help": get_teaching_help,
        "record_attempt": record_attempt,
        "render_vocabulary": render_vocabulary,
        "render_pattern": render_pattern
    }


@router.websocket("/conversation/{lesson_number}")
async def realtime_conversation(
    websocket: WebSocket,
    lesson_number: int,
    mode: str = Query(default="practice", description="Agent mode: 'help' or 'practice'"),
    instruction_language: str = Query(default="es", description="Instruction language: 'es' or 'en'"),
    db: AsyncSession = Depends(get_db),
):
    """WebSocket endpoint for real-time voice conversation.

    Protocol:
    - Client sends: {"type": "audio", "data": "<base64 PCM16 audio>"}
    - Client sends: {"type": "text", "text": "..."} - Send text message
    - Client sends: {"type": "commit"} - Trigger processing
    - Client sends: {"type": "cancel"} - Cancel current response
    - Server sends: {"type": "audio", "data": "<base64 PCM16 audio>"}
    - Server sends: {"type": "transcript", "role": "user"|"assistant", "text": "..."}
    - Server sends: {"type": "rich_content", "tool": "...", "data": {...}}
    - Server sends: {"type": "speech_started"}
    - Server sends: {"type": "speech_stopped"}
    - Server sends: {"type": "response_done"}
    - Server sends: {"type": "error", "message": "..."}
    """
    settings = get_settings()

    # Check if Realtime API is enabled
    if not settings.use_realtime_api:
        await websocket.close(code=4000, reason="Realtime API not enabled")
        return

    await websocket.accept()
    logger.info(f"WebSocket connected: lesson={lesson_number}, mode={mode}")

    # Build system prompt using UnifiedTeachingAgent
    service = LessonService(db)
    lesson = await service.get_lesson_detail("ec1", lesson_number)
    agent = UnifiedTeachingAgent(
        lesson=lesson,
        mode=mode,
        instruction_language=instruction_language
    )
    system_prompt = agent.build_system_prompt()

    # Create tool handlers
    tool_handlers = await create_tool_handlers(db, lesson_number)

    # Create realtime session
    session = RealtimeSessionManager(
        system_prompt=system_prompt,
        tool_handlers=tool_handlers,
        voice="alloy",  # TODO: Make configurable
        language="en"
    )

    try:
        await session.connect()

        # Create tasks for bidirectional streaming
        async def receive_from_client():
            """Receive messages from WebSocket client."""
            try:
                while True:
                    message = await websocket.receive_json()
                    msg_type = message.get("type", "")

                    if msg_type == "audio":
                        # Decode base64 audio and send to Realtime API
                        audio_data = base64.b64decode(message.get("data", ""))
                        await session.send_audio(audio_data)

                    elif msg_type == "text":
                        # Send text message to Realtime API
                        text = message.get("text", "")
                        if text:
                            await session.send_text(text)

                    elif msg_type == "commit":
                        # Client explicitly commits audio buffer
                        await session.commit_audio()

                    elif msg_type == "cancel":
                        # Client wants to cancel current response
                        await session.cancel_response()

            except WebSocketDisconnect:
                logger.info("Client disconnected")

        async def send_to_client():
            """Process Realtime API events and send to client."""
            async for event in session.process_events():
                if event["type"] == "audio":
                    # Encode audio as base64 for WebSocket
                    await websocket.send_json({
                        "type": "audio",
                        "data": base64.b64encode(event["data"]).decode("utf-8")
                    })
                else:
                    # Forward other events directly
                    await websocket.send_json(event)

        # Run both tasks concurrently
        receive_task = asyncio.create_task(receive_from_client())
        send_task = asyncio.create_task(send_to_client())

        done, pending = await asyncio.wait(
            [receive_task, send_task],
            return_when=asyncio.FIRST_COMPLETED
        )

        # Cancel pending tasks
        for task in pending:
            task.cancel()

    except Exception as e:
        logger.error(f"Realtime session error: {e}")
        try:
            await websocket.send_json({"type": "error", "message": str(e)})
        except:
            pass

    finally:
        await session.disconnect()
        logger.info("Realtime session closed")
