"""Tests for TeachingHelpService query parsing and lesson-specific search.

RED phase: These tests define the expected behavior for parsing natural language
queries like "sustantivos lección 6" into structured search parameters.

Bug: When student asks "¿Cuáles son los sustantivos de lección 6 y lección 7?",
the RAG searches for literal string "%sustantivos lección 6%" which never matches.

Fix: Parse query to extract lesson numbers and category keywords, then filter
by lesson_id and category instead of (or in addition to) keyword ILIKE search.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src" / "backend"))

from app.services.teaching_help_service import TeachingHelpService


class TestQueryParsing:
    """Test that natural language queries are parsed into search parameters."""

    def test_extracts_lesson_number_spanish(self):
        """'lección 6' extracts lesson_number=6."""
        service = TeachingHelpService(session=None)

        result = service._parse_query("sustantivos lección 6")

        assert result["lesson_filter"] == 6

    def test_extracts_lesson_number_spanish_accent(self):
        """'lección' with accent extracts lesson number."""
        service = TeachingHelpService(session=None)

        result = service._parse_query("vocabulario de la lección 10")

        assert result["lesson_filter"] == 10

    def test_extracts_lesson_number_english(self):
        """'lesson 6' extracts lesson_number=6."""
        service = TeachingHelpService(session=None)

        result = service._parse_query("nouns from lesson 6")

        assert result["lesson_filter"] == 6

    def test_no_lesson_number_returns_none(self):
        """Query without lesson number returns lesson_filter=None."""
        service = TeachingHelpService(session=None)

        result = service._parse_query("what does brother mean")

        assert result["lesson_filter"] is None

    def test_extracts_category_sustantivos(self):
        """'sustantivos' maps to category='noun'."""
        service = TeachingHelpService(session=None)

        result = service._parse_query("sustantivos lección 6")

        assert result["category"] == "noun"

    def test_extracts_category_verbos(self):
        """'verbos' maps to category='verb'."""
        service = TeachingHelpService(session=None)

        result = service._parse_query("verbos de lección 5")

        assert result["category"] == "verb"

    def test_extracts_category_nouns_english(self):
        """'nouns' maps to category='noun'."""
        service = TeachingHelpService(session=None)

        result = service._parse_query("nouns from lesson 6")

        assert result["category"] == "noun"

    def test_no_category_returns_none(self):
        """Query without category keyword returns category=None."""
        service = TeachingHelpService(session=None)

        result = service._parse_query("what does brother mean")

        assert result["category"] is None

    def test_extracts_remaining_keywords(self):
        """Keywords not matching lesson/category are preserved for ILIKE search."""
        service = TeachingHelpService(session=None)

        result = service._parse_query("brother lección 6")

        assert result["lesson_filter"] == 6
        assert "brother" in result["keywords"]

    def test_combined_lesson_and_category(self):
        """Can extract both lesson number and category."""
        service = TeachingHelpService(session=None)

        result = service._parse_query("sustantivos de lección 7")

        assert result["lesson_filter"] == 7
        assert result["category"] == "noun"


class TestLessonFilteredSearch:
    """Test that search_cumulative_vocab uses lesson filter when present."""

    @pytest.mark.asyncio
    async def test_lesson_filter_queries_specific_lesson(self):
        """When lesson_filter is set, query should filter by that lesson."""
        mock_db = AsyncMock()

        # Mock lesson ID lookup - lesson 6 has internal ID 6
        lesson_result = MagicMock()
        lesson_result.fetchall.return_value = [(6,)]

        # Mock vocabulary results
        vocab_item = MagicMock()
        vocab_item.lesson_id = 6
        vocab_item.english_word = "brother"
        vocab_item.spanish_translation = "hermano"
        vocab_item.category = "noun"

        vocab_result = MagicMock()
        vocab_result.scalars.return_value.all.return_value = [vocab_item]

        mock_db.execute.side_effect = [lesson_result, vocab_result]

        service = TeachingHelpService(mock_db)

        # Search with lesson filter
        result = await service.search_cumulative_vocab(
            query="sustantivos lección 6",
            up_to_lesson=7,
            lesson_filter=6  # New parameter
        )

        assert len(result) > 0
        assert result[0].english_word == "brother"


class TestCategoryFilteredSearch:
    """Test that search_cumulative_vocab uses category filter when present."""

    @pytest.mark.asyncio
    async def test_category_filter_queries_by_category(self):
        """When category is set, query should filter by vocabulary category."""
        mock_db = AsyncMock()

        # Mock lesson ID lookup
        lesson_result = MagicMock()
        lesson_result.fetchall.return_value = [(6,), (7,)]

        # Mock vocabulary results - only nouns
        noun1 = MagicMock()
        noun1.lesson_id = 6
        noun1.english_word = "brother"
        noun1.spanish_translation = "hermano"
        noun1.category = "noun"

        noun2 = MagicMock()
        noun2.lesson_id = 7
        noun2.english_word = "cousin"
        noun2.spanish_translation = "primo"
        noun2.category = "noun"

        vocab_result = MagicMock()
        vocab_result.scalars.return_value.all.return_value = [noun1, noun2]

        mock_db.execute.side_effect = [lesson_result, vocab_result]

        service = TeachingHelpService(mock_db)

        # Search with category filter
        result = await service.search_cumulative_vocab(
            query="sustantivos",
            up_to_lesson=7,
            category="noun"  # New parameter
        )

        assert len(result) >= 2
        assert all(v.category == "noun" for v in result)


class TestGetTeachingHelpIntegration:
    """Test that get_teaching_help uses parsed query parameters."""

    @pytest.mark.asyncio
    async def test_lesson_query_returns_filtered_vocab(self):
        """'sustantivos lección 6' should return nouns from lesson 6."""
        mock_db = AsyncMock()

        # Mock lesson ID lookup - returns lesson 6
        lesson_result = MagicMock()
        lesson_result.fetchall.return_value = [(6,)]

        # Mock vocabulary - lesson 6 nouns
        noun1 = MagicMock()
        noun1.lesson_id = 6
        noun1.english_word = "brother"
        noun1.spanish_translation = "hermano"
        noun1.category = "noun"

        noun2 = MagicMock()
        noun2.lesson_id = 6
        noun2.english_word = "sister"
        noun2.spanish_translation = "hermana"
        noun2.category = "noun"

        vocab_result = MagicMock()
        vocab_result.scalars.return_value.all.return_value = [noun1, noun2]

        # Mock patterns (empty)
        pattern_lesson_result = MagicMock()
        pattern_lesson_result.fetchall.return_value = [(6,)]

        pattern_result = MagicMock()
        pattern_result.scalars.return_value.all.return_value = []

        mock_db.execute.side_effect = [
            lesson_result, vocab_result,
            pattern_lesson_result, pattern_result
        ]

        service = TeachingHelpService(mock_db)

        # THE KEY TEST: This query currently returns 0 results
        result = await service.get_teaching_help(
            query="sustantivos lección 6",
            lesson_number=7
        )

        # Should return vocabulary from lesson 6
        assert len(result["vocabulary"]) >= 2, f"Expected >=2 vocab items, got {result['vocabulary']}"
        assert any(v["english"] == "brother" for v in result["vocabulary"])
        assert any(v["english"] == "sister" for v in result["vocabulary"])

    @pytest.mark.asyncio
    async def test_category_query_returns_filtered_vocab(self):
        """'sustantivos' alone should return nouns from all lessons up to current."""
        mock_db = AsyncMock()

        # Mock lesson ID lookup
        lesson_result = MagicMock()
        lesson_result.fetchall.return_value = [(5,), (6,), (7,)]

        # Mock vocabulary - nouns from multiple lessons
        nouns = [
            MagicMock(lesson_id=5, english_word="job", spanish_translation="trabajo", category="noun"),
            MagicMock(lesson_id=6, english_word="brother", spanish_translation="hermano", category="noun"),
            MagicMock(lesson_id=7, english_word="cousin", spanish_translation="primo", category="noun"),
        ]

        vocab_result = MagicMock()
        vocab_result.scalars.return_value.all.return_value = nouns

        # Mock patterns (empty)
        pattern_lesson_result = MagicMock()
        pattern_lesson_result.fetchall.return_value = [(5,), (6,), (7,)]

        pattern_result = MagicMock()
        pattern_result.scalars.return_value.all.return_value = []

        mock_db.execute.side_effect = [
            lesson_result, vocab_result,
            pattern_lesson_result, pattern_result
        ]

        service = TeachingHelpService(mock_db)

        result = await service.get_teaching_help(
            query="sustantivos",
            lesson_number=7
        )

        # Should return nouns from all lessons
        assert len(result["vocabulary"]) >= 3
        assert all(v["category"] == "noun" for v in result["vocabulary"])
