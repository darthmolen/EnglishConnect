"""Shared tool handlers for agent responses."""

import logging
from typing import Callable

from sqlalchemy.ext.asyncio import AsyncSession

from app.services.tts_service import synthesize_speech
from app.services.teaching_help_service import TeachingHelpService
from app.models.performance import PerformanceContext

logger = logging.getLogger(__name__)


async def speak_tool_handler(
    text: str,
    language: str,
    voice: str = "speaker_b"
) -> dict:
    """Handle speak tool calls from agents.

    Calls TTS service to synthesize speech and returns audio data.

    Args:
        text: Text to speak
        language: Language code (en or es)
        voice: Voice ID (default: speaker_b)

    Returns:
        Dict with spoken status, text, language, and audio data on success.
        On failure, includes error message instead of audio data.
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


def create_teaching_help_handler(
    db: AsyncSession,
    lesson_number: int
) -> Callable:
    """Create a teaching help handler bound to a specific lesson.

    Args:
        db: Database session for querying vocabulary/patterns
        lesson_number: Current lesson number (searches up to this lesson)

    Returns:
        Async function that handles get_teaching_help tool calls
    """
    async def teaching_help_handler(query: str) -> dict:
        """Handle get_teaching_help tool calls.

        Args:
            query: What the student is confused about

        Returns:
            Dict with vocabulary, patterns, exercises, explanation
        """
        try:
            service = TeachingHelpService(db)
            result = await service.get_teaching_help(query, lesson_number)
            logger.info(
                f"Teaching help retrieved: {len(result.get('vocabulary', []))} vocab, "
                f"{len(result.get('patterns', []))} patterns, "
                f"{len(result.get('exercises', []))} exercises"
            )
            return {
                "success": True,
                **result
            }
        except Exception as e:
            logger.error(f"Teaching help failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "vocabulary": [],
                "patterns": [],
                "exercises": [],
                "explanation": None,
            }

    return teaching_help_handler


def create_record_attempt_handler(
    performance_context: PerformanceContext
) -> Callable:
    """Create a record attempt handler bound to a performance context.

    Args:
        performance_context: PerformanceContext to update with attempts

    Returns:
        Async function that handles record_attempt tool calls
    """
    async def record_attempt_handler(item_type: str, correct: bool) -> dict:
        """Handle record_attempt tool calls.

        Args:
            item_type: "vocab" or "pattern"
            correct: Whether the attempt was correct

        Returns:
            Dict with updated struggle status
        """
        try:
            performance_context.record_attempt(correct=correct)
            logger.info(
                f"Attempt recorded: {item_type} {'correct' if correct else 'incorrect'}, "
                f"struggle_level={performance_context.struggle_level}"
            )
            return {
                "success": True,
                "item_type": item_type,
                "correct": correct,
                "struggle_level": performance_context.struggle_level,
                "consecutive_errors": performance_context.consecutive_errors,
                "needs_help": performance_context.needs_help,
            }
        except Exception as e:
            logger.error(f"Record attempt failed: {e}")
            return {
                "success": False,
                "error": str(e),
            }

    return record_attempt_handler
