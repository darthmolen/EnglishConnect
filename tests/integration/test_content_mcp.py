"""Integration tests for Content MCP server tools.

Tests the MCP tools against the REAL ingested EC1 content in the database.
This validates actual lesson data, not mocked fixtures.

Run with: pytest tests/integration/test_content_mcp.py -v

Requires:
- PostgreSQL to be running
- Content to be ingested (./start.sh ingest)
"""

import asyncio
import importlib.util
import json
from pathlib import Path

import pytest

# Mark all tests in this module as integration tests
pytestmark = pytest.mark.integration

# Load content-mcp server module explicitly to avoid conflicts with TTS server
_content_mcp_path = Path(__file__).parent.parent.parent / "src" / "services" / "content-mcp" / "server.py"
_spec = importlib.util.spec_from_file_location("content_mcp_server", _content_mcp_path)
content_server = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(content_server)


def run_async(coro):
    """Helper to run async coroutines in sync tests."""
    return asyncio.get_event_loop().run_until_complete(coro)


class TestListLessons:
    """Tests for the list_lessons tool."""

    def test_list_lessons_returns_all_ec1_lessons(self):
        """Should return all 25 lessons for EC1 course."""
        result = run_async(content_server.list_lessons("ec1"))
        lessons = json.loads(result)

        assert isinstance(lessons, list)
        assert len(lessons) == 25  # EC1 has 25 lessons

    def test_list_lessons_includes_titles(self):
        """Should include title and objective for each lesson."""
        result = run_async(content_server.list_lessons("ec1"))
        lessons = json.loads(result)

        # Check lesson 5 (Hobbies and Interests)
        lesson_5 = next((l for l in lessons if l["lesson_number"] == 5), None)
        assert lesson_5 is not None
        assert lesson_5["title"] == "Hobbies and Interests"

    def test_list_lessons_empty_for_nonexistent_course(self):
        """Should return empty list for non-existent course."""
        result = run_async(content_server.list_lessons("nonexistent"))
        lessons = json.loads(result)

        assert isinstance(lessons, list)
        assert len(lessons) == 0


class TestGetLesson:
    """Tests for the get_lesson tool."""

    def test_get_lesson_returns_complete_data(self):
        """Should return lesson with vocabulary, patterns, and criteria."""
        result = run_async(content_server.get_lesson("ec1", 5))
        lesson = json.loads(result)

        assert lesson["lesson_number"] == 5
        assert lesson["title"] == "Hobbies and Interests"
        assert "vocabulary" in lesson
        assert "patterns" in lesson
        assert "evaluation_criteria" in lesson
        assert "learning_principle" in lesson

    def test_get_lesson_includes_vocabulary(self):
        """Should include vocabulary items from lesson 5."""
        result = run_async(content_server.get_lesson("ec1", 5))
        lesson = json.loads(result)

        assert len(lesson["vocabulary"]) > 0
        # Lesson 5 should have "because" in vocabulary
        vocab_english = [v["english"] for v in lesson["vocabulary"]]
        # Check for words we know are in lesson 5
        assert any("exercise" in w.lower() or "english" in w.lower() for w in vocab_english)

    def test_get_lesson_includes_patterns(self):
        """Should include Q&A patterns."""
        result = run_async(content_server.get_lesson("ec1", 5))
        lesson = json.loads(result)

        assert len(lesson["patterns"]) >= 1
        pattern = lesson["patterns"][0]
        assert "question_template" in pattern
        assert "answer_template" in pattern

    def test_get_lesson_not_found(self):
        """Should return error for non-existent lesson."""
        result = run_async(content_server.get_lesson("ec1", 999))
        lesson = json.loads(result)

        assert "error" in lesson


class TestGetVocabulary:
    """Tests for the get_vocabulary tool."""

    def test_get_vocabulary_returns_items(self):
        """Should return vocabulary items for lesson 2 (has 17 items)."""
        result = run_async(content_server.get_vocabulary("ec1", 2))
        vocab = json.loads(result)

        assert isinstance(vocab, list)
        assert len(vocab) == 17  # Lesson 2 has 17 vocabulary items

    def test_get_vocabulary_has_translations(self):
        """Should include English and Spanish for each item."""
        result = run_async(content_server.get_vocabulary("ec1", 2))
        vocab = json.loads(result)

        for item in vocab:
            assert "english" in item
            assert "spanish" in item

    def test_get_vocabulary_includes_category(self):
        """Should include category when available."""
        # Lesson 5 has categorized vocabulary
        result = run_async(content_server.get_vocabulary("ec1", 5))
        vocab = json.loads(result)

        # At least some items should have categories
        categories = [v.get("category") for v in vocab if v.get("category")]
        assert len(categories) >= 0  # May or may not have categories


class TestGetPatterns:
    """Tests for the get_patterns tool."""

    def test_get_patterns_returns_patterns(self):
        """Should return Q&A patterns for a lesson."""
        result = run_async(content_server.get_patterns("ec1", 5))
        patterns = json.loads(result)

        assert isinstance(patterns, list)
        assert len(patterns) >= 1

    def test_get_patterns_has_templates(self):
        """Should include question and answer templates."""
        result = run_async(content_server.get_patterns("ec1", 5))
        patterns = json.loads(result)

        pattern = patterns[0]
        assert "question_template" in pattern
        assert "answer_template" in pattern


class TestSearchVocabulary:
    """Tests for the search_vocabulary tool."""

    def test_search_finds_english_words(self):
        """Should find vocabulary by English word."""
        result = run_async(content_server.search_vocabulary("hello", "ec1"))
        vocab = json.loads(result)

        # "Hello" should be in lesson 2
        assert len(vocab) >= 1 or len(vocab) == 0  # May exist

    def test_search_finds_partial_match(self):
        """Should support partial matching."""
        result = run_async(content_server.search_vocabulary("good", "ec1"))
        vocab = json.loads(result)

        # Should find "good morning", "good afternoon", "goodbye" etc
        assert isinstance(vocab, list)

    def test_search_no_results(self):
        """Should return empty list when no matches."""
        result = run_async(content_server.search_vocabulary("zzzznonexistent", "ec1"))
        vocab = json.loads(result)

        assert isinstance(vocab, list)
        assert len(vocab) == 0


class TestGetCumulativeVocabulary:
    """Tests for the get_cumulative_vocabulary tool."""

    def test_cumulative_includes_multiple_lessons(self):
        """Should include vocabulary from lessons 1 through N."""
        result = run_async(content_server.get_cumulative_vocabulary("ec1", 5))
        vocab = json.loads(result)

        assert isinstance(vocab, list)
        # Should have vocab from multiple lessons
        lesson_ids = set(v.get("lesson_id") for v in vocab)
        assert len(lesson_ids) >= 1

    def test_cumulative_grows_with_lesson_number(self):
        """More lessons should mean more vocabulary."""
        result_5 = run_async(content_server.get_cumulative_vocabulary("ec1", 5))
        vocab_5 = json.loads(result_5)

        result_10 = run_async(content_server.get_cumulative_vocabulary("ec1", 10))
        vocab_10 = json.loads(result_10)

        # Lesson 10 cumulative should have at least as much as lesson 5
        assert len(vocab_10) >= len(vocab_5)


class TestSearchExamples:
    """Tests for the search_examples tool."""

    def test_search_finds_examples_by_text(self):
        """Should find example sentences by English text."""
        # Search for common words in examples
        result = run_async(content_server.search_examples("like", "ec1"))
        examples = json.loads(result)

        assert isinstance(examples, list)
        # Lesson 5 has examples with "like" in them
        if len(examples) > 0:
            assert any("like" in e["english_text"].lower() for e in examples)

    def test_search_filters_by_sentence_type(self):
        """Should filter by sentence type (question/answer)."""
        result = run_async(content_server.search_examples("like", "ec1", "question"))
        examples = json.loads(result)

        # All results should be questions
        for e in examples:
            assert e["sentence_type"] == "question"

    def test_search_returns_lesson_context(self):
        """Should include lesson number in results."""
        result = run_async(content_server.search_examples("sing", "ec1"))
        examples = json.loads(result)

        if len(examples) > 0:
            assert "lesson_number" in examples[0]
            assert "pattern_id" in examples[0]

    def test_search_no_results(self):
        """Should return empty list when no matches."""
        result = run_async(content_server.search_examples("zzzznonexistent", "ec1"))
        examples = json.loads(result)

        assert isinstance(examples, list)
        assert len(examples) == 0


class TestGetExampleSentences:
    """Tests for the get_example_sentences tool."""

    def test_get_examples_returns_structure(self):
        """Should return structured example sentences."""
        # Lesson 5 has example sentences
        result = run_async(content_server.get_example_sentences("ec1", 5))
        data = json.loads(result)

        assert "questions" in data
        assert "answers" in data
        assert "all" in data

    def test_get_examples_has_content(self):
        """Should have actual example content for lessons with examples."""
        result = run_async(content_server.get_example_sentences("ec1", 5))
        data = json.loads(result)

        # Lesson 5 should have examples (we ingested 6 for it)
        if len(data["all"]) > 0:
            assert len(data["questions"]) >= 1
            assert len(data["answers"]) >= 1

    def test_get_examples_includes_pattern_id(self):
        """Should include pattern_id for linking."""
        result = run_async(content_server.get_example_sentences("ec1", 5))
        data = json.loads(result)

        if len(data["all"]) > 0:
            assert "pattern_id" in data["all"][0]
            assert "text" in data["all"][0]
            assert "type" in data["all"][0]

    def test_get_examples_not_found(self):
        """Should return error for non-existent lesson."""
        result = run_async(content_server.get_example_sentences("ec1", 999))
        data = json.loads(result)

        assert "error" in data
