"""Tests for Realtime API tool handlers.

TDD Task 1: Verify render_pattern accepts optional lesson_number parameter.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock


@pytest.mark.asyncio
async def test_render_pattern_accepts_lesson_number_param():
    """Handler should accept optional lesson_number without error.

    The Realtime API may pass lesson_number to render_pattern, but since
    the lesson is already captured in the closure, we just need to accept
    and ignore it.
    """
    # Import the function we're testing
    from app.routers.realtime import create_tool_handlers

    # Mock the database session and LessonService
    mock_db = AsyncMock()

    # Create a mock lesson with patterns
    mock_pattern = MagicMock()
    mock_pattern.pattern_number = 1
    mock_pattern.question_template = "What is ___?"
    mock_pattern.answer_template = "It is ___."

    mock_lesson = MagicMock()
    mock_lesson.patterns = [mock_pattern]
    mock_lesson.vocabulary = []

    # Patch LessonService to return our mock lesson
    with pytest.MonkeyPatch.context() as mp:
        mock_service = MagicMock()
        mock_service.get_lesson_detail = AsyncMock(return_value=mock_lesson)

        mp.setattr(
            "app.routers.realtime.LessonService",
            lambda db: mock_service
        )

        # Create handlers
        handlers = await create_tool_handlers(mock_db, lesson_number=7)

        # Call render_pattern WITH lesson_number parameter
        # This should NOT raise TypeError for unexpected keyword argument
        result = await handlers["render_pattern"](pattern_number=1, lesson_number=5)

        # Verify it returns the pattern data
        assert result["pattern_number"] == 1
        assert result["question"] == "What is ___?"
        assert result["answer"] == "It is ___."


@pytest.mark.asyncio
async def test_render_pattern_works_without_lesson_number():
    """Handler should still work when lesson_number is not provided."""
    from app.routers.realtime import create_tool_handlers

    mock_db = AsyncMock()

    mock_pattern = MagicMock()
    mock_pattern.pattern_number = 2
    mock_pattern.question_template = "Where is ___?"
    mock_pattern.answer_template = "It is in ___."

    mock_lesson = MagicMock()
    mock_lesson.patterns = [mock_pattern]
    mock_lesson.vocabulary = []

    with pytest.MonkeyPatch.context() as mp:
        mock_service = MagicMock()
        mock_service.get_lesson_detail = AsyncMock(return_value=mock_lesson)

        mp.setattr(
            "app.routers.realtime.LessonService",
            lambda db: mock_service
        )

        handlers = await create_tool_handlers(mock_db, lesson_number=7)

        # Call WITHOUT lesson_number - should still work
        result = await handlers["render_pattern"](pattern_number=2)

        assert result["pattern_number"] == 2
