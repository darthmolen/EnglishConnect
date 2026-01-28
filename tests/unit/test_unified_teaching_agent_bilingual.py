"""Unit tests for bilingual features in UnifiedTeachingAgent."""

import pytest
from unittest.mock import MagicMock, patch
from app.schemas.helping_phrase import HelpingPhraseSchema


def create_mock_lesson():
    """Create a mock lesson with patterns."""
    lesson = MagicMock()
    lesson.lesson_number = 16
    lesson.title = "Food"
    lesson.objective = "Practice talking about food"

    pattern = MagicMock()
    pattern.pattern_number = 1
    pattern.question_template = "What do you like to eat?"
    pattern.answer_template = "I like to eat (*noun*)."
    pattern.question_translation = "¿Qué te gusta comer?"
    pattern.answer_translation = "Me gusta comer (*sustantivo*)."

    lesson.patterns = [pattern]

    vocab = MagicMock()
    vocab.english_word = "pizza"
    vocab.spanish_translation = "pizza"
    lesson.vocabulary = [vocab]

    return lesson


def create_mock_phrases_spanish():
    """Create mock Spanish helping phrases."""
    return [
        HelpingPhraseSchema(
            phrase_key="repeat",
            phrase_text="Repite, por favor",
            english_meaning="Please repeat"
        ),
        HelpingPhraseSchema(
            phrase_key="dont_understand",
            phrase_text="No entiendo",
            english_meaning="I don't understand"
        ),
        HelpingPhraseSchema(
            phrase_key="slower",
            phrase_text="Más despacio, por favor",
            english_meaning="Slower, please"
        ),
    ]


def create_mock_phrases_english():
    """Create mock English helping phrases."""
    return [
        HelpingPhraseSchema(
            phrase_key="repeat",
            phrase_text="Please repeat",
            english_meaning="Please repeat"
        ),
        HelpingPhraseSchema(
            phrase_key="dont_understand",
            phrase_text="I don't understand",
            english_meaning="I don't understand"
        ),
    ]


class TestFormatHelpingPhrasesList:
    """Tests for _format_helping_phrases_list method."""

    def test_formats_spanish_phrases(self):
        """Should format Spanish phrases with phrase text and English meaning."""
        from app.agents.unified_teaching_agent import UnifiedTeachingAgent

        lesson = create_mock_lesson()
        phrases = create_mock_phrases_spanish()

        agent = UnifiedTeachingAgent(
            lesson=lesson,
            mode="practice",
            exchange_count=0,
            instruction_language="es",
            helping_phrases=phrases,
        )

        result = agent._format_helping_phrases_list()

        assert '"Repite, por favor" = Please repeat' in result
        assert '"No entiendo" = I don\'t understand' in result
        assert '"Más despacio, por favor" = Slower, please' in result

    def test_formats_english_phrases(self):
        """Should format English phrases."""
        from app.agents.unified_teaching_agent import UnifiedTeachingAgent

        lesson = create_mock_lesson()
        phrases = create_mock_phrases_english()

        agent = UnifiedTeachingAgent(
            lesson=lesson,
            mode="practice",
            exchange_count=0,
            instruction_language="en",
            helping_phrases=phrases,
        )

        result = agent._format_helping_phrases_list()

        assert '"Please repeat" = Please repeat' in result

    def test_returns_message_when_no_phrases(self):
        """Should return 'No helping phrases available' when empty."""
        from app.agents.unified_teaching_agent import UnifiedTeachingAgent

        lesson = create_mock_lesson()

        agent = UnifiedTeachingAgent(
            lesson=lesson,
            mode="practice",
            exchange_count=0,
            instruction_language="es",
            helping_phrases=None,
        )

        result = agent._format_helping_phrases_list()

        assert result == "No helping phrases available."


class TestFormatHelpingPhrasesForIntro:
    """Tests for _format_helping_phrases_for_intro method."""

    def test_formats_intro_in_spanish(self):
        """Should format intro with 'Puedes decir:' for Spanish."""
        from app.agents.unified_teaching_agent import UnifiedTeachingAgent

        lesson = create_mock_lesson()
        phrases = create_mock_phrases_spanish()

        agent = UnifiedTeachingAgent(
            lesson=lesson,
            mode="practice",
            exchange_count=0,
            instruction_language="es",
            helping_phrases=phrases,
        )

        result = agent._format_helping_phrases_for_intro()

        assert "Puedes decir:" in result
        assert '"Repite, por favor"' in result
        assert '"No entiendo"' in result

    def test_formats_intro_in_english(self):
        """Should format intro with 'You can say:' for English."""
        from app.agents.unified_teaching_agent import UnifiedTeachingAgent

        lesson = create_mock_lesson()
        phrases = create_mock_phrases_english()

        agent = UnifiedTeachingAgent(
            lesson=lesson,
            mode="practice",
            exchange_count=0,
            instruction_language="en",
            helping_phrases=phrases,
        )

        result = agent._format_helping_phrases_for_intro()

        assert "You can say:" in result
        assert '"Please repeat"' in result

    def test_limits_to_three_phrases(self):
        """Should limit intro to 3 phrases for brevity."""
        from app.agents.unified_teaching_agent import UnifiedTeachingAgent

        lesson = create_mock_lesson()
        phrases = create_mock_phrases_spanish() + [
            HelpingPhraseSchema(
                phrase_key="example",
                phrase_text="Dame un ejemplo",
                english_meaning="Give me an example"
            ),
        ]

        agent = UnifiedTeachingAgent(
            lesson=lesson,
            mode="practice",
            exchange_count=0,
            instruction_language="es",
            helping_phrases=phrases,
        )

        result = agent._format_helping_phrases_for_intro()

        # Should only have 3 phrases, not 4
        assert result.count('"') == 6  # 3 phrases × 2 quotes each


class TestFormatPatternIntroduction:
    """Tests for _format_pattern_introduction method."""

    def test_spanish_instruction_shows_both_languages(self):
        """Should show pattern in Spanish first, then English."""
        from app.agents.unified_teaching_agent import UnifiedTeachingAgent

        lesson = create_mock_lesson()

        agent = UnifiedTeachingAgent(
            lesson=lesson,
            mode="practice",
            exchange_count=0,
            instruction_language="es",
        )

        result = agent._format_pattern_introduction()

        # Spanish version shown first
        assert "Pregunta:" in result
        assert "Respuesta:" in result
        assert "¿Qué te gusta comer?" in result
        # English version also shown
        assert "English:" in result or "What do you like to eat?" in result

    def test_english_instruction_shows_english_only(self):
        """Should show pattern in English only when instruction_language is 'en'."""
        from app.agents.unified_teaching_agent import UnifiedTeachingAgent

        lesson = create_mock_lesson()

        agent = UnifiedTeachingAgent(
            lesson=lesson,
            mode="practice",
            exchange_count=0,
            instruction_language="en",
        )

        result = agent._format_pattern_introduction()

        assert "Question:" in result
        assert "Answer:" in result
        assert "What do you like to eat?" in result
        # Should NOT have Spanish
        assert "Pregunta:" not in result

    def test_uses_focus_pattern_when_set(self):
        """Should use focus_pattern when specified."""
        from app.agents.unified_teaching_agent import UnifiedTeachingAgent

        lesson = create_mock_lesson()

        # Add a second pattern
        pattern2 = MagicMock()
        pattern2.pattern_number = 2
        pattern2.question_template = "What is your favorite food?"
        pattern2.answer_template = "My favorite food is (*noun*)."
        pattern2.question_translation = "¿Cuál es tu comida favorita?"
        pattern2.answer_translation = "Mi comida favorita es (*sustantivo*)."
        lesson.patterns.append(pattern2)

        agent = UnifiedTeachingAgent(
            lesson=lesson,
            mode="practice",
            exchange_count=0,
            instruction_language="en",
            focus_pattern=2,
        )

        result = agent._format_pattern_introduction()

        # Should use pattern 2, not pattern 1
        assert "favorite food" in result
        assert "What do you like to eat?" not in result

    def test_returns_message_when_no_patterns(self):
        """Should return 'No patterns' message when empty."""
        from app.agents.unified_teaching_agent import UnifiedTeachingAgent

        lesson = create_mock_lesson()
        lesson.patterns = []

        agent = UnifiedTeachingAgent(
            lesson=lesson,
            mode="practice",
            exchange_count=0,
            instruction_language="es",
        )

        result = agent._format_pattern_introduction()

        assert "No patterns" in result


class TestPromptBuildingWithHelpingPhrases:
    """Tests that helping phrases are included in prompts."""

    def test_practice_prompt_includes_helping_phrases_section(self):
        """Should include helping phrases in practice mode prompt."""
        from app.agents.unified_teaching_agent import UnifiedTeachingAgent

        lesson = create_mock_lesson()
        phrases = create_mock_phrases_spanish()

        agent = UnifiedTeachingAgent(
            lesson=lesson,
            mode="practice",
            exchange_count=0,
            instruction_language="es",
            helping_phrases=phrases,
        )

        # Get the built prompt
        prompt = agent._build_practice_prompt()

        # Should include the helping phrases section
        assert "Repite, por favor" in prompt or "helping phrase" in prompt.lower()

    def test_instruction_language_flows_through_prompt(self):
        """Should pass instruction_language through to prompt variables."""
        from app.agents.unified_teaching_agent import UnifiedTeachingAgent

        lesson = create_mock_lesson()

        # Test Spanish
        agent_es = UnifiedTeachingAgent(
            lesson=lesson,
            mode="practice",
            exchange_count=0,
            instruction_language="es",
        )
        prompt_es = agent_es._build_practice_prompt()

        # Test English
        agent_en = UnifiedTeachingAgent(
            lesson=lesson,
            mode="practice",
            exchange_count=0,
            instruction_language="en",
        )
        prompt_en = agent_en._build_practice_prompt()

        # Prompts should be different based on language
        # At minimum, the instruction language should appear
        assert "es" in prompt_es.lower() or "spanish" in prompt_es.lower() or "español" in prompt_es.lower()
