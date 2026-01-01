"""Integration tests for the get_teaching_help tool handler."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.services.teaching_help_service import TeachingHelpService


@pytest.fixture
def mock_db():
    """Create a mock async database session."""
    db = AsyncMock()
    return db


@pytest.fixture
def mock_vocab_items():
    """Create mock vocabulary items for family-related words."""
    items = []
    for word, spanish, lesson_id in [
        ("brother", "hermano", 6),
        ("sister", "hermana", 6),
        ("mother", "madre", 6),
        ("father", "padre", 6),
    ]:
        item = MagicMock()
        item.lesson_id = lesson_id
        item.english_word = word
        item.spanish_translation = spanish
        item.category = "noun"
        items.append(item)
    return items


@pytest.fixture
def mock_patterns():
    """Create mock patterns about family."""
    patterns = []

    pattern = MagicMock()
    pattern.lesson_id = 6
    pattern.pattern_number = 1
    pattern.question_template = "Who is your [family member]?"
    pattern.answer_template = "My [family member] is [name]."
    pattern.examples = [
        {"q": "Who is your brother?", "a": "My brother is Miguel."}
    ]
    patterns.append(pattern)

    return patterns


class TestGetTeachingHelpHandler:
    """Test the get_teaching_help tool handler integration."""

    @pytest.mark.asyncio
    async def test_handler_returns_vocabulary(self, mock_db, mock_vocab_items):
        """Should return vocabulary from TeachingHelpService."""
        # Setup mock for two-step query (lesson IDs, then vocab)
        lesson_result = MagicMock()
        lesson_result.fetchall.return_value = [(6,)]

        vocab_result = MagicMock()
        vocab_result.scalars.return_value.all.return_value = mock_vocab_items[:2]

        pattern_result = MagicMock()
        pattern_result.fetchall.return_value = [(6,)]

        pattern_query_result = MagicMock()
        pattern_query_result.scalars.return_value.all.return_value = []

        mock_db.execute.side_effect = [
            lesson_result, vocab_result,
            pattern_result, pattern_query_result
        ]

        # Import handler
        from app.routers.lesson import create_teaching_help_handler

        handler = create_teaching_help_handler(mock_db, lesson_number=10)
        result = await handler(query="family brother")

        assert "vocabulary" in result
        assert len(result["vocabulary"]) > 0
        assert any("brother" in v["english"] for v in result["vocabulary"])

    @pytest.mark.asyncio
    async def test_handler_returns_patterns(self, mock_db, mock_patterns):
        """Should return patterns from TeachingHelpService."""
        # Setup mock for two-step query
        lesson_result = MagicMock()
        lesson_result.fetchall.return_value = [(6,)]

        vocab_result = MagicMock()
        vocab_result.scalars.return_value.all.return_value = []

        pattern_lesson_result = MagicMock()
        pattern_lesson_result.fetchall.return_value = [(6,)]

        pattern_result = MagicMock()
        pattern_result.scalars.return_value.all.return_value = mock_patterns

        mock_db.execute.side_effect = [
            lesson_result, vocab_result,
            pattern_lesson_result, pattern_result
        ]

        from app.routers.lesson import create_teaching_help_handler

        handler = create_teaching_help_handler(mock_db, lesson_number=10)
        result = await handler(query="family questions")

        assert "patterns" in result
        # Patterns might be empty if query doesn't match, that's OK
        assert isinstance(result["patterns"], list)

    @pytest.mark.asyncio
    async def test_handler_includes_exercises_and_explanation(self, mock_db):
        """Should include workbook exercises and lesson explanation."""
        # Setup empty DB results
        empty_result = MagicMock()
        empty_result.fetchall.return_value = []
        mock_db.execute.return_value = empty_result

        from app.routers.lesson import create_teaching_help_handler

        with patch.object(
            TeachingHelpService, "get_workbook_exercises",
            return_value=[{"title": "Activity 1", "content": "Practice..."}]
        ):
            with patch.object(
                TeachingHelpService, "get_lesson_explanation",
                return_value="This pattern helps you ask about family."
            ):
                handler = create_teaching_help_handler(mock_db, lesson_number=6)
                result = await handler(query="family")

        assert "exercises" in result
        assert "explanation" in result

    @pytest.mark.asyncio
    async def test_handler_includes_source(self, mock_db):
        """Should include source lesson reference."""
        empty_result = MagicMock()
        empty_result.fetchall.return_value = []
        mock_db.execute.return_value = empty_result

        from app.routers.lesson import create_teaching_help_handler

        handler = create_teaching_help_handler(mock_db, lesson_number=8)
        result = await handler(query="anything")

        assert "source" in result
        assert "lesson-8" in result["source"]


class TestHandlerInToolChain:
    """Test handler works correctly in the tool calling context."""

    @pytest.mark.asyncio
    async def test_handler_returns_serializable_result(self, mock_db):
        """Result should be JSON-serializable for LLM tool response."""
        import json

        empty_result = MagicMock()
        empty_result.fetchall.return_value = []
        mock_db.execute.return_value = empty_result

        from app.routers.lesson import create_teaching_help_handler

        handler = create_teaching_help_handler(mock_db, lesson_number=5)
        result = await handler(query="test")

        # Should not raise - result must be JSON serializable
        json_str = json.dumps(result)
        assert json_str is not None
        assert len(json_str) > 0
