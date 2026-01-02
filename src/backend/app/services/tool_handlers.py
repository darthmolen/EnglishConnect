"""Shared tool handlers for agent responses."""

import glob
import json
import logging
from pathlib import Path
from typing import Callable

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.tts_service import synthesize_speech
from app.services.teaching_help_service import TeachingHelpService
from app.models.performance import PerformanceContext
from app.models.content import VocabularyItem, Lesson, QAPattern

logger = logging.getLogger(__name__)

# Audio content base path (repo root / content / audio)
# From services/tool_handlers.py: up 5 levels to reach repo root
AUDIO_BASE = Path(__file__).parent.parent.parent.parent.parent / "content" / "audio"


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


def _find_vocab_audio_url(course_id: str, lesson_number: int, english_word: str) -> str | None:
    """Find the audio URL for a vocabulary word by scanning metadata files.

    Args:
        course_id: Course identifier (e.g., 'ec1')
        lesson_number: Lesson number to search in
        english_word: English word to find

    Returns:
        Stream URL if found, None otherwise
    """
    vocab_dir = AUDIO_BASE / course_id / "vocab" / f"lesson-{lesson_number:02d}"
    if not vocab_dir.exists():
        return None

    # Scan all JSON metadata files in the lesson directory
    for meta_path in glob.glob(str(vocab_dir / "*.json")):
        try:
            with open(meta_path) as f:
                meta = json.load(f)

            # Match by english_word (case-insensitive)
            if meta.get("english_word", "").lower() == english_word.lower():
                audio_path = Path(meta_path).with_suffix(".wav")
                relative_path = audio_path.relative_to(AUDIO_BASE)
                return f"/api/audio/stream/{relative_path}"
        except Exception:
            continue

    return None


def create_render_vocabulary_handler(
    db: AsyncSession,
    lesson_number: int,
    course_id: str = "ec1"
) -> Callable:
    """Create a render vocabulary handler bound to a specific lesson.

    Args:
        db: Database session for querying vocabulary
        lesson_number: Current lesson number (searches up to this lesson)
        course_id: Course identifier (default: 'ec1')

    Returns:
        Async function that handles render_vocabulary tool calls
    """
    async def render_vocabulary_handler(english_word: str) -> dict:
        """Handle render_vocabulary tool calls.

        Args:
            english_word: The English word to render

        Returns:
            Dict with rich_content (vocabulary card data) or not_in_curriculum flag
        """
        try:
            # Search vocabulary up to current lesson (case-insensitive)
            result = await db.execute(
                select(VocabularyItem, Lesson.lesson_number)
                .join(Lesson)
                .where(
                    VocabularyItem.english_word.ilike(f"%{english_word}%"),
                    Lesson.lesson_number <= lesson_number,
                    Lesson.course_id == course_id
                )
                .order_by(Lesson.lesson_number.desc())
                .limit(1)
            )
            row = result.first()

            if not row:
                # RED PATH: Word not in curriculum
                logger.info(f"Vocabulary '{english_word}' not found in lessons 1-{lesson_number}")
                return {
                    "success": False,
                    "not_in_curriculum": True,
                    "word": english_word,
                    "message": f"'{english_word}' is not in lessons 1-{lesson_number}. Explain the word directly using speak() - no card available."
                }

            vocab_item, item_lesson_number = row

            # Find pre-generated audio URL
            audio_url = _find_vocab_audio_url(course_id, item_lesson_number, vocab_item.english_word)

            logger.info(
                f"Vocabulary card rendered: '{vocab_item.english_word}' "
                f"(lesson {item_lesson_number}, audio={'yes' if audio_url else 'no'})"
            )

            return {
                "success": True,
                "rich_content": {
                    "type": "vocabulary_card",
                    "data": {
                        "english_word": vocab_item.english_word,
                        "spanish_translation": vocab_item.spanish_translation,
                        "category": vocab_item.category or "word",
                        "lesson_number": item_lesson_number,
                        "audio_url": audio_url
                    }
                }
            }

        except Exception as e:
            logger.error(f"Render vocabulary failed: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    return render_vocabulary_handler


def _get_pattern_demo_audio_url(course_id: str, lesson_number: int) -> str | None:
    """Get demo audio URL for a lesson's patterns.

    Args:
        course_id: Course identifier (e.g., 'ec1')
        lesson_number: Lesson number

    Returns:
        API endpoint URL for demo audio, or None if not available
    """
    # Demo audio endpoint returns metadata for all demos in a lesson
    demo_dir = AUDIO_BASE / course_id / "demos" / f"lesson-{lesson_number:02d}"
    if demo_dir.exists() and any(demo_dir.glob("*.wav")):
        return f"/api/audio/demos/{course_id}?lesson_number={lesson_number}"
    return None


def create_render_pattern_handler(
    db: AsyncSession,
    lesson_number: int,
    course_id: str = "ec1"
) -> Callable:
    """Create a render pattern handler bound to a specific lesson.

    Args:
        db: Database session for querying patterns
        lesson_number: Current lesson number (default for patterns)
        course_id: Course identifier (default: 'ec1')

    Returns:
        Async function that handles render_pattern tool calls
    """
    # Capture outer lesson_number before inner function shadows it
    default_lesson = lesson_number

    async def render_pattern_handler(
        pattern_number: int,
        lesson_number: int | None = None
    ) -> dict:
        """Handle render_pattern tool calls.

        Args:
            pattern_number: Pattern number (1 or 2) in the lesson
            lesson_number: Optional lesson number (defaults to current)

        Returns:
            Dict with rich_content (pattern card data) or error
        """
        target_lesson = lesson_number if lesson_number is not None else default_lesson

        try:
            # Get lesson
            lesson_result = await db.execute(
                select(Lesson).where(
                    Lesson.course_id == course_id,
                    Lesson.lesson_number == target_lesson
                )
            )
            lesson_obj = lesson_result.scalar_one_or_none()

            if not lesson_obj:
                logger.warning(f"Lesson {target_lesson} not found")
                return {
                    "success": False,
                    "message": f"Lesson {target_lesson} not found"
                }

            # Get pattern
            pattern_result = await db.execute(
                select(QAPattern).where(
                    QAPattern.lesson_id == lesson_obj.id,
                    QAPattern.pattern_number == pattern_number
                )
            )
            pattern_obj = pattern_result.scalar_one_or_none()

            if not pattern_obj:
                logger.warning(f"Pattern {pattern_number} not found in lesson {target_lesson}")
                return {
                    "success": False,
                    "message": f"Pattern {pattern_number} not found in lesson {target_lesson}"
                }

            # Find demo audio URL
            demo_audio_url = _get_pattern_demo_audio_url(course_id, target_lesson)

            logger.info(
                f"Pattern card rendered: pattern {pattern_number} "
                f"(lesson {target_lesson}, demo_audio={'yes' if demo_audio_url else 'no'})"
            )

            return {
                "success": True,
                "tool": "render_pattern",
                "rich_content": {
                    "type": "pattern_card",
                    "data": {
                        "pattern_number": pattern_obj.pattern_number,
                        "question_template": pattern_obj.question_template,
                        "answer_template": pattern_obj.answer_template,
                        "lesson_number": target_lesson,
                        "demo_audio_url": demo_audio_url
                    }
                }
            }

        except Exception as e:
            logger.error(f"Render pattern failed: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    return render_pattern_handler
