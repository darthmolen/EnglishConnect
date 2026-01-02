"""Unit tests for tool handlers.

These tests verify that tool handlers:
1. Accept the exact parameters defined in tool definitions
2. Return correct data structures
3. Handle edge cases (missing lessons, patterns, vocabulary)
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from pathlib import Path


class TestRenderPatternHandler:
    """Test create_render_pattern_handler and its returned handler."""

    @pytest.fixture
    def mock_db(self):
        """Create a mock async database session."""
        db = AsyncMock()
        return db

    @pytest.fixture
    def mock_lesson(self):
        """Create a mock lesson object."""
        lesson = MagicMock()
        lesson.id = 6
        lesson.course_id = "ec1"
        lesson.lesson_number = 6
        return lesson

    @pytest.fixture
    def mock_pattern(self):
        """Create a mock pattern object."""
        pattern = MagicMock()
        pattern.pattern_number = 1
        pattern.question_template = "How many (*noun*) are in your family?"
        pattern.answer_template = "There are (*number*) people in my family."
        return pattern

    @pytest.mark.asyncio
    async def test_render_pattern_with_explicit_lesson_number(
        self, mock_db, mock_lesson, mock_pattern
    ):
        """Handler should use explicit lesson_number parameter, not default.

        This is the bug that caused 6 iterations - the handler used
        lesson_number_override instead of lesson_number, causing the
        LLM's lesson_number=6 to be ignored.
        """
        from app.services.tool_handlers import create_render_pattern_handler

        # Setup mock DB responses
        mock_db.execute.side_effect = [
            # First call: get lesson
            MagicMock(scalar_one_or_none=MagicMock(return_value=mock_lesson)),
            # Second call: get pattern
            MagicMock(scalar_one_or_none=MagicMock(return_value=mock_pattern)),
        ]

        # Create handler with default lesson 7
        handler = create_render_pattern_handler(db=mock_db, lesson_number=7)

        # Call with explicit lesson_number=6 (as LLM would)
        with patch(
            "app.services.tool_handlers._get_pattern_demo_audio_url",
            return_value="/api/audio/demos/ec1?lesson_number=6",
        ):
            result = await handler(pattern_number=1, lesson_number=6)

        # Should succeed and return lesson 6, not default lesson 7
        assert result["success"] is True
        assert result["rich_content"]["data"]["lesson_number"] == 6
        assert result["rich_content"]["data"]["pattern_number"] == 1

    @pytest.mark.asyncio
    async def test_render_pattern_uses_default_when_no_lesson_number(
        self, mock_db, mock_lesson, mock_pattern
    ):
        """Handler should use default lesson when lesson_number not provided."""
        from app.services.tool_handlers import create_render_pattern_handler

        # Update mock_lesson to be lesson 7 (the default)
        mock_lesson.lesson_number = 7
        mock_lesson.id = 7

        mock_db.execute.side_effect = [
            MagicMock(scalar_one_or_none=MagicMock(return_value=mock_lesson)),
            MagicMock(scalar_one_or_none=MagicMock(return_value=mock_pattern)),
        ]

        handler = create_render_pattern_handler(db=mock_db, lesson_number=7)

        with patch(
            "app.services.tool_handlers._get_pattern_demo_audio_url",
            return_value="/api/audio/demos/ec1?lesson_number=7",
        ):
            # Call without lesson_number - should use default (7)
            result = await handler(pattern_number=1)

        assert result["success"] is True
        assert result["rich_content"]["data"]["lesson_number"] == 7

    @pytest.mark.asyncio
    async def test_render_pattern_returns_error_for_missing_lesson(self, mock_db):
        """Handler should return error when lesson not found."""
        from app.services.tool_handlers import create_render_pattern_handler

        mock_db.execute.return_value = MagicMock(
            scalar_one_or_none=MagicMock(return_value=None)
        )

        handler = create_render_pattern_handler(db=mock_db, lesson_number=7)
        result = await handler(pattern_number=1, lesson_number=99)

        assert result["success"] is False
        assert "Lesson 99 not found" in result["message"]

    @pytest.mark.asyncio
    async def test_render_pattern_returns_error_for_missing_pattern(
        self, mock_db, mock_lesson
    ):
        """Handler should return error when pattern not found."""
        from app.services.tool_handlers import create_render_pattern_handler

        mock_db.execute.side_effect = [
            MagicMock(scalar_one_or_none=MagicMock(return_value=mock_lesson)),
            MagicMock(scalar_one_or_none=MagicMock(return_value=None)),
        ]

        handler = create_render_pattern_handler(db=mock_db, lesson_number=7)
        result = await handler(pattern_number=3, lesson_number=6)

        assert result["success"] is False
        assert "Pattern 3 not found" in result["message"]

    @pytest.mark.asyncio
    async def test_render_pattern_returns_correct_structure(
        self, mock_db, mock_lesson, mock_pattern
    ):
        """Handler should return correct rich_content structure."""
        from app.services.tool_handlers import create_render_pattern_handler

        mock_db.execute.side_effect = [
            MagicMock(scalar_one_or_none=MagicMock(return_value=mock_lesson)),
            MagicMock(scalar_one_or_none=MagicMock(return_value=mock_pattern)),
        ]

        handler = create_render_pattern_handler(db=mock_db, lesson_number=7)

        with patch(
            "app.services.tool_handlers._get_pattern_demo_audio_url",
            return_value="/api/audio/demos/ec1?lesson_number=6",
        ):
            result = await handler(pattern_number=1, lesson_number=6)

        # Verify structure matches what frontend expects
        assert "rich_content" in result
        assert result["rich_content"]["type"] == "pattern_card"
        data = result["rich_content"]["data"]
        assert "pattern_number" in data
        assert "question_template" in data
        assert "answer_template" in data
        assert "lesson_number" in data
        assert "demo_audio_url" in data


class TestRenderVocabularyHandler:
    """Test create_render_vocabulary_handler and its returned handler."""

    @pytest.fixture
    def mock_db(self):
        """Create a mock async database session."""
        db = AsyncMock()
        return db

    @pytest.fixture
    def mock_vocab_result(self):
        """Create a mock vocabulary query result."""
        vocab = MagicMock()
        vocab.english_word = "family"
        vocab.spanish_translation = "familia"
        vocab.category = "noun"
        return vocab

    @pytest.mark.asyncio
    async def test_render_vocabulary_finds_word(self, mock_db, mock_vocab_result):
        """Handler should find and return vocabulary card for valid word."""
        from app.services.tool_handlers import create_render_vocabulary_handler

        # Mock the query result (returns tuple of vocab_item, lesson_number)
        mock_db.execute.return_value = MagicMock(
            first=MagicMock(return_value=(mock_vocab_result, 6))
        )

        handler = create_render_vocabulary_handler(db=mock_db, lesson_number=7)

        with patch(
            "app.services.tool_handlers._find_vocab_audio_url",
            return_value="/api/audio/stream/ec1/vocab/lesson-06/family.wav",
        ):
            result = await handler(english_word="family")

        assert result["success"] is True
        assert result["rich_content"]["type"] == "vocabulary_card"
        assert result["rich_content"]["data"]["english_word"] == "family"
        assert result["rich_content"]["data"]["spanish_translation"] == "familia"

    @pytest.mark.asyncio
    async def test_render_vocabulary_returns_not_in_curriculum(self, mock_db):
        """Handler should return not_in_curriculum for unknown words."""
        from app.services.tool_handlers import create_render_vocabulary_handler

        mock_db.execute.return_value = MagicMock(first=MagicMock(return_value=None))

        handler = create_render_vocabulary_handler(db=mock_db, lesson_number=7)
        result = await handler(english_word="serendipity")

        assert result["success"] is False
        assert result["not_in_curriculum"] is True
        assert "serendipity" in result["word"]

    @pytest.mark.asyncio
    async def test_render_vocabulary_returns_correct_structure(
        self, mock_db, mock_vocab_result
    ):
        """Handler should return correct rich_content structure."""
        from app.services.tool_handlers import create_render_vocabulary_handler

        mock_db.execute.return_value = MagicMock(
            first=MagicMock(return_value=(mock_vocab_result, 6))
        )

        handler = create_render_vocabulary_handler(db=mock_db, lesson_number=7)

        with patch(
            "app.services.tool_handlers._find_vocab_audio_url",
            return_value="/api/audio/stream/ec1/vocab/lesson-06/family.wav",
        ):
            result = await handler(english_word="family")

        # Verify structure matches what frontend expects
        assert "rich_content" in result
        assert result["rich_content"]["type"] == "vocabulary_card"
        data = result["rich_content"]["data"]
        assert "english_word" in data
        assert "spanish_translation" in data
        assert "category" in data
        assert "lesson_number" in data
        assert "audio_url" in data


class TestToolDefinitionParameterMatch:
    """Verify tool handler parameters match tool definitions.

    This test class exists because the bug that caused 6 iterations was
    a parameter name mismatch between tool definition and handler.
    """

    def test_render_pattern_handler_accepts_tool_definition_params(self):
        """Handler signature must accept exact params from RENDER_PATTERN_TOOL."""
        from app.services.azure_openai import UNIFIED_AGENT_TOOLS
        import inspect

        # Find render_pattern tool definition
        render_pattern_tool = next(
            (t for t in UNIFIED_AGENT_TOOLS if t["function"]["name"] == "render_pattern"),
            None,
        )
        assert render_pattern_tool is not None, "render_pattern tool not found in UNIFIED_AGENT_TOOLS"

        # Get parameter names from tool definition
        tool_params = set(
            render_pattern_tool["function"]["parameters"]["properties"].keys()
        )

        # Import and inspect handler factory
        from app.services.tool_handlers import create_render_pattern_handler

        # Create a mock handler to inspect its signature
        mock_db = AsyncMock()
        handler = create_render_pattern_handler(db=mock_db, lesson_number=7)

        # Get handler parameter names (excluding 'self')
        sig = inspect.signature(handler)
        handler_params = set(sig.parameters.keys())

        # Tool params should be subset of handler params
        # (handler can have additional optional params but must accept all tool params)
        missing_params = tool_params - handler_params
        assert not missing_params, f"Handler missing params from tool definition: {missing_params}"

    def test_render_vocabulary_handler_accepts_tool_definition_params(self):
        """Handler signature must accept exact params from RENDER_VOCABULARY_TOOL."""
        from app.services.azure_openai import UNIFIED_AGENT_TOOLS
        import inspect

        render_vocab_tool = next(
            (t for t in UNIFIED_AGENT_TOOLS if t["function"]["name"] == "render_vocabulary"),
            None,
        )
        assert render_vocab_tool is not None, "render_vocabulary tool not found"

        tool_params = set(
            render_vocab_tool["function"]["parameters"]["properties"].keys()
        )

        from app.services.tool_handlers import create_render_vocabulary_handler

        mock_db = AsyncMock()
        handler = create_render_vocabulary_handler(db=mock_db, lesson_number=7)

        sig = inspect.signature(handler)
        handler_params = set(sig.parameters.keys())

        missing_params = tool_params - handler_params
        assert not missing_params, f"Handler missing params: {missing_params}"
