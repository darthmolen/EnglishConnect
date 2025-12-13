"""Unit tests for the LessonParser class.

Tests markdown parsing logic without database dependencies.
Run with: pytest tests/unit/test_lesson_parser.py -v
"""

import pytest
import sys
from pathlib import Path

# Add tools to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "tools"))
from content_ingestion import LessonParser


class TestLessonParserTitle:
    """Tests for title extraction."""

    def test_extracts_bold_title(self):
        """Should extract title from # **Title** format."""
        content = "**LESSON 5**\n\n# **Hobbies and Interests**\n\nSome content"
        parser = LessonParser(content, 5)
        assert parser._extract_title() == "Hobbies and Interests"

    def test_returns_default_when_no_title(self):
        """Should return default title when pattern not found."""
        content = "Some content without title"
        parser = LessonParser(content, 5)
        assert parser._extract_title() == "Lesson 5"


class TestLessonParserObjective:
    """Tests for objective extraction."""

    def test_extracts_objetivo(self):
        """Should extract Spanish objective text."""
        content = "**OBJETIVO: APRENDERÉ A HABLAR SOBRE PASATIEMPOS.**\n\nOther content"
        parser = LessonParser(content, 5)
        assert parser._extract_objective() == "APRENDERÉ A HABLAR SOBRE PASATIEMPOS."

    def test_returns_none_when_no_objective(self):
        """Should return None when no objective found."""
        content = "Content without objective"
        parser = LessonParser(content, 5)
        assert parser._extract_objective() is None


class TestLessonParserPrinciple:
    """Tests for learning principle extraction."""

    def test_extracts_principle_title(self):
        """Should extract the principle title."""
        content = "## **Study the Principle of Learning: Learn by Study and by Faith**\n\n*Content*"
        parser = LessonParser(content, 5)
        assert parser._extract_principle_title() == "Learn by Study and by Faith"

    def test_extracts_principle_content(self):
        """Should extract italicized principle content."""
        content = "## **Study the Principle of Learning: Test Principle**\n\n*In EnglishConnect, we learn together.*\n\nMore text"
        parser = LessonParser(content, 5)
        assert parser._extract_principle_content() == "In EnglishConnect, we learn together."


class TestLessonParserVocabulary:
    """Tests for vocabulary extraction."""

    def test_extracts_vocabulary_table(self, sample_lesson_markdown):
        """Should extract vocabulary from markdown tables."""
        parser = LessonParser(sample_lesson_markdown, 5)
        vocab = parser._extract_vocabulary()

        english_words = [v["english_word"] for v in vocab]
        assert "because" in english_words
        assert "exercise" in english_words
        assert "boring" in english_words
        assert "fun" in english_words

    def test_extracts_spanish_translations(self, sample_lesson_markdown):
        """Should extract Spanish translations correctly."""
        parser = LessonParser(sample_lesson_markdown, 5)
        vocab = parser._extract_vocabulary()

        vocab_dict = {v["english_word"]: v["spanish_translation"] for v in vocab}
        assert vocab_dict.get("because") == "porque"
        assert vocab_dict.get("exercise") == "hacer ejercicio"

    def test_skips_header_rows(self, sample_lesson_markdown):
        """Should skip table header rows (Verbs, Adjectives)."""
        parser = LessonParser(sample_lesson_markdown, 5)
        vocab = parser._extract_vocabulary()

        english_words = [v["english_word"] for v in vocab]
        assert "Verbs" not in english_words
        assert "---" not in english_words

    def test_extracts_vocabulary_from_minimal_content(self):
        """Should handle minimal vocabulary section."""
        content = '''## **Memorize Vocabulary**

| hello | hola |
|-------|------|
| goodbye | adiós |
'''
        parser = LessonParser(content, 1)
        vocab = parser._extract_vocabulary()

        assert len(vocab) == 2
        assert vocab[0]["english_word"] == "hello"
        assert vocab[1]["spanish_translation"] == "adiós"


class TestLessonParserPatterns:
    """Tests for Q&A pattern extraction."""

    def test_extracts_pattern_number(self, sample_lesson_markdown):
        """Should extract pattern numbers correctly."""
        parser = LessonParser(sample_lesson_markdown, 5)
        patterns = parser._extract_patterns()

        assert len(patterns) >= 1
        assert patterns[0]["pattern_number"] == 1

    def test_extracts_question_template(self, sample_lesson_markdown):
        """Should extract question template."""
        parser = LessonParser(sample_lesson_markdown, 5)
        patterns = parser._extract_patterns()

        assert patterns[0]["question_template"] == "What do you like to do?"

    def test_extracts_answer_template(self, sample_lesson_markdown):
        """Should extract answer template."""
        parser = LessonParser(sample_lesson_markdown, 5)
        patterns = parser._extract_patterns()

        assert "I like to" in patterns[0]["answer_template"]

    def test_handles_multiple_patterns(self):
        """Should extract multiple patterns from a lesson."""
        content = '''## **Practice Pattern 1**

Q: What is your name?

A: My name is (*name*).

## **Practice Pattern 2**

Q: Where are you from?

A: I am from (*place*).
'''
        parser = LessonParser(content, 1)
        patterns = parser._extract_patterns()

        assert len(patterns) == 2
        assert patterns[0]["pattern_number"] == 1
        assert patterns[1]["pattern_number"] == 2


class TestLessonParserCriteria:
    """Tests for evaluation criteria extraction."""

    def test_extracts_i_can_statements(self, sample_lesson_markdown):
        """Should extract 'I can' evaluation statements."""
        parser = LessonParser(sample_lesson_markdown, 5)
        criteria = parser._extract_criteria()

        assert len(criteria) >= 2
        assert "Say why I like something" in criteria[0]
        assert "Say why I don't like something" in criteria[1]

    def test_handles_empty_criteria(self):
        """Should return empty list when no criteria found."""
        content = "Content without evaluation section"
        parser = LessonParser(content, 1)
        criteria = parser._extract_criteria()

        assert criteria == []


class TestLessonParserExamples:
    """Tests for example sentence extraction from patterns."""

    def test_extracts_examples_from_separate_section(self, sample_lesson_markdown):
        """Should extract Q&A examples from separate ## **Examples** section."""
        parser = LessonParser(sample_lesson_markdown, 5)
        patterns = parser._extract_patterns()

        assert len(patterns) >= 1
        assert patterns[0]["examples"] is not None
        assert len(patterns[0]["examples"]) >= 1

    def test_example_has_question_and_answer(self, sample_lesson_markdown):
        """Should extract both Q and A from examples."""
        parser = LessonParser(sample_lesson_markdown, 5)
        patterns = parser._extract_patterns()

        example = patterns[0]["examples"][0]
        assert "q" in example
        assert "a" in example
        assert "Why do you like to sing" in example["q"]
        assert "fun" in example["a"]

    def test_extracts_multiple_examples(self):
        """Should extract multiple Q&A pairs from Examples section."""
        content = '''## **Practice Pattern 1**

Q: What do you like?

A: I like (*noun*).

## **Examples**

Q: What do you like?

A: I like pizza.

Q: What does she like?

A: She likes music.

Q: What do they like?

A: They like sports.
'''
        parser = LessonParser(content, 1)
        patterns = parser._extract_patterns()

        assert patterns[0]["examples"] is not None
        assert len(patterns[0]["examples"]) == 3

    def test_handles_no_examples_section(self):
        """Should return None for examples when no Examples section exists."""
        content = '''## **Practice Pattern 1**

Q: What is your name?

A: My name is (*name*).

## **Other Section**
'''
        parser = LessonParser(content, 1)
        patterns = parser._extract_patterns()

        assert len(patterns) == 1
        assert patterns[0]["examples"] is None

    def test_examples_associated_with_first_pattern(self):
        """Examples section should be associated with the first pattern."""
        content = '''## **Practice Pattern 1**

Q: First pattern question?

A: First pattern answer.

## **Practice Pattern 2**

Q: Second pattern question?

A: Second pattern answer.

## **Examples**

Q: Example question?

A: Example answer.
'''
        parser = LessonParser(content, 1)
        patterns = parser._extract_patterns()

        assert len(patterns) == 2
        # Examples are associated with first pattern
        assert patterns[0]["examples"] is not None
        assert patterns[1]["examples"] is None


class TestLessonParserParse:
    """Tests for the full parse() method."""

    def test_parse_returns_complete_structure(self, sample_lesson_markdown):
        """Should return dictionary with all expected keys."""
        parser = LessonParser(sample_lesson_markdown, 5)
        result = parser.parse()

        assert "lesson_number" in result
        assert "title" in result
        assert "objective" in result
        assert "learning_principle_title" in result
        assert "learning_principle" in result
        assert "vocabulary" in result
        assert "qa_patterns" in result
        assert "evaluation_criteria" in result

    def test_parse_has_correct_lesson_number(self, sample_lesson_markdown):
        """Should include the lesson number passed to constructor."""
        parser = LessonParser(sample_lesson_markdown, 5)
        result = parser.parse()

        assert result["lesson_number"] == 5

    def test_parse_real_lesson_file(self):
        """Test parsing an actual lesson file if available."""
        lesson_path = Path(__file__).parent.parent.parent / \
            "content/refined/ec1/books/englishconnect_1_para_los_alumnos/lessons/lesson-05.md"

        if not lesson_path.exists():
            pytest.skip("Lesson file not found")

        content = lesson_path.read_text()
        parser = LessonParser(content, 5)
        result = parser.parse()

        assert result["title"] == "Hobbies and Interests"
        assert len(result["vocabulary"]) > 0
        assert len(result["qa_patterns"]) > 0
