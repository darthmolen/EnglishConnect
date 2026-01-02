"""Unit tests for TeachingHelpService."""

import pytest
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

from app.services.teaching_help_service import TeachingHelpService


@pytest.fixture
def mock_db():
    """Create a mock async database session."""
    db = AsyncMock()
    return db


@pytest.fixture
def mock_vocab_items():
    """Create mock vocabulary items from multiple lessons."""
    items = []
    # Lesson 5 vocab
    for word, spanish in [("shop", "comprar"), ("cook", "cocinar"), ("read", "leer")]:
        item = MagicMock()
        item.lesson_id = 5
        item.english_word = word
        item.spanish_translation = spanish
        item.category = "verb"
        items.append(item)

    # Lesson 6 vocab - family words
    for word, spanish in [("brother", "hermano"), ("sister", "hermana"), ("mother", "madre")]:
        item = MagicMock()
        item.lesson_id = 6
        item.english_word = word
        item.spanish_translation = spanish
        item.category = "noun"
        items.append(item)

    return items


@pytest.fixture
def mock_patterns():
    """Create mock Q&A patterns."""
    patterns = []

    # Pattern from lesson 5
    pattern1 = MagicMock()
    pattern1.lesson_id = 5
    pattern1.pattern_number = 1
    pattern1.question_template = "Why do you like to [verb]?"
    pattern1.answer_template = "I like to [verb] because it's [adjective]."
    pattern1.examples = [
        {"q": "Why do you like to cook?", "a": "I like to cook because it's fun."}
    ]
    patterns.append(pattern1)

    # Pattern from lesson 6
    pattern2 = MagicMock()
    pattern2.lesson_id = 6
    pattern2.pattern_number = 1
    pattern2.question_template = "Who is your [family member]?"
    pattern2.answer_template = "My [family member] is [name]."
    pattern2.examples = [
        {"q": "Who is your brother?", "a": "My brother is Miguel."}
    ]
    patterns.append(pattern2)

    return patterns


class TestTeachingHelpService:
    """Test TeachingHelpService methods."""

    @pytest.mark.asyncio
    async def test_search_cumulative_vocab_finds_matches(self, mock_db, mock_vocab_items):
        """Should find vocabulary matching query from lessons up to specified number."""
        # First call returns lesson IDs
        lesson_result = MagicMock()
        lesson_result.fetchall.return_value = [(5,), (6,)]

        # Second call returns matching vocab
        vocab_result = MagicMock()
        vocab_result.scalars.return_value.all.return_value = [
            item for item in mock_vocab_items if "brother" in item.english_word.lower()
        ]

        mock_db.execute.side_effect = [lesson_result, vocab_result]

        service = TeachingHelpService(mock_db)
        results = await service.search_cumulative_vocab("brother", up_to_lesson=10)

        assert len(results) == 1
        assert results[0].english_word == "brother"

    @pytest.mark.asyncio
    async def test_search_cumulative_vocab_respects_lesson_limit(self, mock_db, mock_vocab_items):
        """Should only return vocab from lessons up to the specified number."""
        # All items are from lessons 5-6, searching up to lesson 5 should exclude lesson 6 items
        lesson5_items = [item for item in mock_vocab_items if item.lesson_id <= 5]
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = lesson5_items
        mock_db.execute.return_value = mock_result

        service = TeachingHelpService(mock_db)
        results = await service.search_cumulative_vocab("cook", up_to_lesson=5)

        # Should find cook from lesson 5 but not family words from lesson 6
        assert all(r.lesson_id <= 5 for r in results)

    @pytest.mark.asyncio
    async def test_search_cumulative_vocab_empty_results(self, mock_db):
        """Should return empty list when no matches found."""
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_db.execute.return_value = mock_result

        service = TeachingHelpService(mock_db)
        results = await service.search_cumulative_vocab("nonexistent", up_to_lesson=10)

        assert results == []

    @pytest.mark.asyncio
    async def test_search_patterns_finds_matches(self, mock_db, mock_patterns):
        """Should find patterns matching query."""
        # First call returns lesson IDs
        lesson_result = MagicMock()
        lesson_result.fetchall.return_value = [(5,), (6,)]

        # Second call returns matching patterns
        pattern_result = MagicMock()
        pattern_result.scalars.return_value.all.return_value = mock_patterns[:1]

        mock_db.execute.side_effect = [lesson_result, pattern_result]

        service = TeachingHelpService(mock_db)
        results = await service.search_patterns("why like", up_to_lesson=10)

        assert len(results) >= 1
        assert "Why" in results[0].question_template

    @pytest.mark.asyncio
    async def test_search_patterns_respects_lesson_limit(self, mock_db, mock_patterns):
        """Should only return patterns from lessons up to specified number."""
        lesson5_patterns = [p for p in mock_patterns if p.lesson_id <= 5]
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = lesson5_patterns
        mock_db.execute.return_value = mock_result

        service = TeachingHelpService(mock_db)
        results = await service.search_patterns("family", up_to_lesson=5)

        assert all(r.lesson_id <= 5 for r in results)


class TestWorkbookExercises:
    """Test workbook exercise extraction."""

    @pytest.fixture
    def sample_workbook_content(self):
        """Sample workbook markdown content."""
        return """### **ENGLISHCONNECT 1 LESSON 5: HOBBIES AND INTERESTS**

### **CONVERSATION: WHY DO YOU LIKE TO . . .**

### **ACTIVITY 2: SAM'S AND ROSIE'S LISTS**

### A. Read the lists.

| play sports  | fun       |
|--------------|-----------|
| sing         | difficult |

### B. Listen to 1–6, and repeat. C. Write the correct word.

- 1. Sam likes to play sports because it's fun.
- 2. Rosie likes to read books because it's interesting.

### **ACTIVITY 4: "WH-" QUESTIONS (WHAT, WHY)**

- A. Listen to the examples. Then repeat.
  - 1. What do you like to do? I like to run.
  - 2. What does he like to do? He likes to cook.
"""

    def test_parse_workbook_activities(self, sample_workbook_content):
        """Should extract activity sections from workbook."""
        service = TeachingHelpService(None)
        activities = service._parse_workbook_activities(sample_workbook_content)

        assert len(activities) >= 2
        assert any("SAM'S AND ROSIE'S LISTS" in a["title"] for a in activities)
        assert any("WH-" in a["title"] for a in activities)

    def test_get_workbook_exercises_with_topic_filter(self, sample_workbook_content):
        """Should filter activities by topic."""
        service = TeachingHelpService(None)

        with patch.object(service, "_load_workbook_content", return_value=sample_workbook_content):
            exercises = service.get_workbook_exercises(lesson=5, topic="questions")

        # Should find the WH-QUESTIONS activity
        assert any("WH-" in ex.get("title", "") or "question" in ex.get("content", "").lower()
                   for ex in exercises)

    def test_get_workbook_exercises_returns_empty_for_missing_file(self):
        """Should return empty list when workbook file doesn't exist."""
        service = TeachingHelpService(None)

        with patch.object(service, "_load_workbook_content", return_value=None):
            exercises = service.get_workbook_exercises(lesson=99, topic="anything")

        assert exercises == []


class TestLessonExplanations:
    """Test lesson explanation extraction."""

    @pytest.fixture
    def sample_lesson_content(self):
        """Sample lesson markdown content."""
        return """### Lesson 5: Hobbies and Interests

## Study the Principle of Learning

You Are a Child of God with Divine Potential. You are a beloved child of Heavenly Father.

## Memorize Vocabulary

Verbs: cook cocinar, read leer, shop comprar. Practice these verbs daily.

## Practice Pattern

Why do you like to verb? I like to verb because it's adjective. This pattern helps you explain your preferences.

Examples: Why do you like to cook? I like to cook because it's fun.
"""

    def test_get_lesson_explanation_for_pattern(self, sample_lesson_content):
        """Should extract pattern explanation from lesson."""
        service = TeachingHelpService(None)

        with patch.object(service, "_load_lesson_content", return_value=sample_lesson_content):
            explanation = service.get_lesson_explanation(lesson=5, topic="pattern")

        assert explanation is not None
        assert "like" in explanation.lower() or "pattern" in explanation.lower()

    def test_get_lesson_explanation_for_vocabulary(self, sample_lesson_content):
        """Should extract vocabulary section from lesson."""
        service = TeachingHelpService(None)

        with patch.object(service, "_load_lesson_content", return_value=sample_lesson_content):
            explanation = service.get_lesson_explanation(lesson=5, topic="vocabulary")

        assert explanation is not None
        assert "cook" in explanation.lower() or "vocab" in explanation.lower()

    def test_get_lesson_explanation_returns_none_for_missing(self):
        """Should return None when lesson file doesn't exist."""
        service = TeachingHelpService(None)

        with patch.object(service, "_load_lesson_content", return_value=None):
            explanation = service.get_lesson_explanation(lesson=99, topic="anything")

        assert explanation is None


class TestQueryParsing:
    """Test natural language query parsing."""

    def test_parse_query_detects_pattern_keywords_spanish(self):
        """Should detect 'frases' as a pattern request."""
        service = TeachingHelpService(None)
        parsed = service._parse_query("dame las frases de leccion 6")

        assert parsed["wants_patterns"] is True
        assert 6 in parsed["lesson_filters"]

    def test_parse_query_detects_pattern_keywords_english(self):
        """Should detect 'patterns' as a pattern request."""
        service = TeachingHelpService(None)
        parsed = service._parse_query("show me patterns from lesson 5")

        assert parsed["wants_patterns"] is True
        assert 5 in parsed["lesson_filters"]

    def test_parse_query_detects_multiple_lessons(self):
        """Should extract multiple lesson numbers from query."""
        service = TeachingHelpService(None)
        parsed = service._parse_query("frases de leccion 6 y 7")

        assert parsed["wants_patterns"] is True
        assert 6 in parsed["lesson_filters"]
        assert 7 in parsed["lesson_filters"]

    def test_parse_query_category_without_patterns(self):
        """Should detect category when not asking for patterns."""
        service = TeachingHelpService(None)
        parsed = service._parse_query("sustantivos de leccion 6")

        assert parsed["wants_patterns"] is False
        assert parsed["category"] == "noun"
        assert 6 in parsed["lesson_filters"]

    def test_parse_query_backward_compatibility(self):
        """Should maintain lesson_filter for backward compatibility."""
        service = TeachingHelpService(None)
        parsed = service._parse_query("what does brother mean")

        # lesson_filter should be None when no lesson specified
        assert parsed["lesson_filter"] is None
        assert "brother" in parsed["keywords"]


class TestGetTeachingHelp:
    """Test the main get_teaching_help method that combines all sources."""

    @pytest.mark.asyncio
    async def test_get_teaching_help_returns_mixed_content(self, mock_db, mock_vocab_items, mock_patterns):
        """Should return content from multiple sources."""
        # Setup vocab query
        vocab_result = MagicMock()
        vocab_result.scalars.return_value.all.return_value = mock_vocab_items[:2]

        # Setup pattern query
        pattern_result = MagicMock()
        pattern_result.scalars.return_value.all.return_value = mock_patterns[:1]

        mock_db.execute.side_effect = [vocab_result, pattern_result]

        service = TeachingHelpService(mock_db)

        with patch.object(service, "get_workbook_exercises", return_value=[{"title": "Activity 1"}]):
            with patch.object(service, "get_lesson_explanation", return_value="Example explanation"):
                result = await service.get_teaching_help(
                    query="how to ask about hobbies",
                    lesson_number=10
                )

        assert "vocabulary" in result
        assert "patterns" in result
        assert "exercises" in result
        assert "explanation" in result

    @pytest.mark.asyncio
    async def test_get_teaching_help_handles_partial_results(self, mock_db):
        """Should handle when some sources return no results."""
        # No vocab found
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_db.execute.return_value = mock_result

        service = TeachingHelpService(mock_db)

        with patch.object(service, "get_workbook_exercises", return_value=[]):
            with patch.object(service, "get_lesson_explanation", return_value=None):
                result = await service.get_teaching_help(
                    query="nonexistent topic",
                    lesson_number=5
                )

        # Should still return structure, just empty
        assert "vocabulary" in result
        assert result["vocabulary"] == []
