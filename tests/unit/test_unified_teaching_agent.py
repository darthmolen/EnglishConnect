"""Unit tests for UnifiedTeachingAgent.

Tests the unified agent with two modes:
- Help mode: Answer questions only (vocabulary page)
- Practice mode: Lead conversation, flip roles (practice page)
"""

import pytest

from app.agents.unified_teaching_agent import UnifiedTeachingAgent
from app.models.performance import PerformanceContext
from app.schemas.lesson import LessonDetail, VocabularyItemSchema, QAPatternSchema


@pytest.fixture
def sample_lesson():
    """Create a sample lesson for testing."""
    return LessonDetail(
        lesson_number=5,
        title="Hobbies and Interests",
        objective="Learn to talk about hobbies and free-time activities",
        vocabulary=[
            VocabularyItemSchema(english="exercise", spanish="hacer ejercicio"),
            VocabularyItemSchema(english="sing", spanish="cantar"),
            VocabularyItemSchema(english="play", spanish="jugar"),
        ],
        patterns=[
            QAPatternSchema(
                pattern_number=1,
                question_template="What do you like to do?",
                answer_template="I like to [activity].",
            ),
            QAPatternSchema(
                pattern_number=2,
                question_template="Do you like to [activity]?",
                answer_template="Yes, I do. / No, I don't.",
            ),
        ],
    )


class TestUnifiedTeachingAgentInit:
    """Test agent initialization."""

    def test_init_with_help_mode(self, sample_lesson):
        """Agent should initialize with help mode."""
        agent = UnifiedTeachingAgent(
            lesson=sample_lesson,
            mode="help",
        )

        assert agent.lesson == sample_lesson
        assert agent.mode == "help"
        assert agent.exchange_count == 0

    def test_init_with_practice_mode(self, sample_lesson):
        """Agent should initialize with practice mode."""
        agent = UnifiedTeachingAgent(
            lesson=sample_lesson,
            mode="practice",
        )

        assert agent.lesson == sample_lesson
        assert agent.mode == "practice"
        assert agent.exchange_count == 0

    def test_init_with_exchange_count(self, sample_lesson):
        """Agent should accept exchange count for practice mode."""
        agent = UnifiedTeachingAgent(
            lesson=sample_lesson,
            mode="practice",
            exchange_count=3,
        )

        assert agent.exchange_count == 3

    def test_init_with_performance_context(self, sample_lesson):
        """Agent should accept performance context."""
        ctx = PerformanceContext()
        ctx.record_attempt(correct=False)
        ctx.record_attempt(correct=False)

        agent = UnifiedTeachingAgent(
            lesson=sample_lesson,
            mode="help",
            performance_context=ctx,
        )

        assert agent.performance_context == ctx
        assert agent.performance_context.consecutive_errors == 2

    def test_init_creates_default_performance_context(self, sample_lesson):
        """Agent should create default performance context if not provided."""
        agent = UnifiedTeachingAgent(
            lesson=sample_lesson,
            mode="help",
        )

        assert agent.performance_context is not None
        assert agent.performance_context.consecutive_errors == 0


class TestHelpModePrompt:
    """Test help mode prompt generation."""

    def test_help_mode_prompt_includes_lesson_info(self, sample_lesson):
        """Help mode prompt should include lesson title."""
        agent = UnifiedTeachingAgent(
            lesson=sample_lesson,
            mode="help",
        )

        prompt = agent.build_system_prompt()

        assert "Hobbies and Interests" in prompt
        assert "5" in prompt or "Lesson 5" in prompt

    def test_help_mode_prompt_includes_vocabulary(self, sample_lesson):
        """Help mode prompt should include vocabulary list."""
        agent = UnifiedTeachingAgent(
            lesson=sample_lesson,
            mode="help",
        )

        prompt = agent.build_system_prompt()

        assert "exercise" in prompt
        assert "hacer ejercicio" in prompt

    def test_help_mode_prompt_wait_behavior(self, sample_lesson):
        """Help mode should instruct agent to wait for questions."""
        agent = UnifiedTeachingAgent(
            lesson=sample_lesson,
            mode="help",
        )

        prompt = agent.build_system_prompt()

        # Should indicate waiting/reactive behavior
        assert "wait" in prompt.lower() or "only respond" in prompt.lower()

    def test_help_mode_prompt_includes_get_teaching_help(self, sample_lesson):
        """Help mode should include get_teaching_help tool instructions."""
        agent = UnifiedTeachingAgent(
            lesson=sample_lesson,
            mode="help",
        )

        prompt = agent.build_system_prompt()

        assert "get_teaching_help" in prompt.lower()

    def test_help_mode_prompt_no_initiate_conversation(self, sample_lesson):
        """Help mode should not initiate conversation."""
        agent = UnifiedTeachingAgent(
            lesson=sample_lesson,
            mode="help",
        )

        prompt = agent.build_system_prompt()

        # Should explicitly say not to initiate
        assert "do not initiate" in prompt.lower() or "don't initiate" in prompt.lower()


class TestPracticeModePrompt:
    """Test practice mode prompt generation."""

    def test_practice_mode_prompt_includes_lesson_info(self, sample_lesson):
        """Practice mode prompt should include lesson title."""
        agent = UnifiedTeachingAgent(
            lesson=sample_lesson,
            mode="practice",
        )

        prompt = agent.build_system_prompt()

        assert "Hobbies and Interests" in prompt

    def test_practice_mode_prompt_includes_patterns(self, sample_lesson):
        """Practice mode prompt should include patterns for practice."""
        agent = UnifiedTeachingAgent(
            lesson=sample_lesson,
            mode="practice",
        )

        prompt = agent.build_system_prompt()

        assert "What do you like to do?" in prompt
        assert "I like to" in prompt

    def test_practice_mode_prompt_includes_exchange_count(self, sample_lesson):
        """Practice mode should show current exchange count."""
        agent = UnifiedTeachingAgent(
            lesson=sample_lesson,
            mode="practice",
            exchange_count=2,
        )

        prompt = agent.build_system_prompt()

        # Exchange count should be visible
        assert "2" in prompt or "exchange" in prompt.lower()

    def test_practice_mode_prompt_lead_behavior_early(self, sample_lesson):
        """Practice mode with low exchange count should lead conversation."""
        agent = UnifiedTeachingAgent(
            lesson=sample_lesson,
            mode="practice",
            exchange_count=1,
        )

        prompt = agent.build_system_prompt()

        # Should indicate leading
        assert "lead" in prompt.lower() or "ask" in prompt.lower()

    def test_practice_mode_prompt_flip_suggestion(self, sample_lesson):
        """Practice mode should suggest flip after 3-5 exchanges."""
        agent = UnifiedTeachingAgent(
            lesson=sample_lesson,
            mode="practice",
            exchange_count=4,
        )

        prompt = agent.build_system_prompt()

        # Should prompt student to ask
        flip_indicators = ["you ask", "now you", "your turn", "flip"]
        assert any(ind in prompt.lower() for ind in flip_indicators)

    def test_practice_mode_prompt_includes_get_teaching_help(self, sample_lesson):
        """Practice mode should include get_teaching_help for struggles."""
        agent = UnifiedTeachingAgent(
            lesson=sample_lesson,
            mode="practice",
        )

        prompt = agent.build_system_prompt()

        assert "get_teaching_help" in prompt.lower()


class TestPerformanceContextIntegration:
    """Test performance context integration in prompts."""

    def test_help_mode_includes_struggle_level(self, sample_lesson):
        """Help mode should include struggle indicators."""
        ctx = PerformanceContext()
        ctx.record_attempt(correct=False)
        ctx.record_attempt(correct=False)

        agent = UnifiedTeachingAgent(
            lesson=sample_lesson,
            mode="help",
            performance_context=ctx,
        )

        prompt = agent.build_system_prompt()

        # Should include struggle context
        assert "medium" in prompt.lower() or "2" in prompt

    def test_practice_mode_includes_struggle_level(self, sample_lesson):
        """Practice mode should include struggle indicators."""
        ctx = PerformanceContext()
        ctx.record_attempt(correct=False)
        ctx.record_attempt(correct=False)
        ctx.record_attempt(correct=False)

        agent = UnifiedTeachingAgent(
            lesson=sample_lesson,
            mode="practice",
            performance_context=ctx,
        )

        prompt = agent.build_system_prompt()

        # Should include struggle context
        assert "high" in prompt.lower() or "3" in prompt


class TestToolInstructions:
    """Test that tool usage instructions are included."""

    def test_speak_tool_in_help_mode(self, sample_lesson):
        """Help mode should require speak tool."""
        agent = UnifiedTeachingAgent(
            lesson=sample_lesson,
            mode="help",
        )

        prompt = agent.build_system_prompt()

        assert "speak" in prompt.lower()

    def test_speak_tool_in_practice_mode(self, sample_lesson):
        """Practice mode should require speak tool."""
        agent = UnifiedTeachingAgent(
            lesson=sample_lesson,
            mode="practice",
        )

        prompt = agent.build_system_prompt()

        assert "speak" in prompt.lower()

    def test_record_attempt_in_practice_mode(self, sample_lesson):
        """Practice mode should include record_attempt tool."""
        agent = UnifiedTeachingAgent(
            lesson=sample_lesson,
            mode="practice",
        )

        prompt = agent.build_system_prompt()

        assert "record_attempt" in prompt.lower()


class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_empty_vocabulary(self):
        """Agent should handle lesson with no vocabulary."""
        lesson = LessonDetail(
            lesson_number=1,
            title="Introduction",
            objective="Welcome to the course",
            vocabulary=[],
            patterns=[],
        )

        agent = UnifiedTeachingAgent(
            lesson=lesson,
            mode="help",
        )

        # Should not raise
        prompt = agent.build_system_prompt()
        assert "Introduction" in prompt

    def test_empty_patterns(self):
        """Agent should handle lesson with no patterns."""
        lesson = LessonDetail(
            lesson_number=1,
            title="Vocabulary Only",
            objective="Learn words",
            vocabulary=[
                VocabularyItemSchema(english="hello", spanish="hola"),
            ],
            patterns=[],
        )

        agent = UnifiedTeachingAgent(
            lesson=lesson,
            mode="practice",
        )

        # Should not raise
        prompt = agent.build_system_prompt()
        assert "Vocabulary Only" in prompt

    def test_high_exchange_count(self, sample_lesson):
        """Agent should handle high exchange counts gracefully."""
        agent = UnifiedTeachingAgent(
            lesson=sample_lesson,
            mode="practice",
            exchange_count=50,
        )

        # Should not raise
        prompt = agent.build_system_prompt()
        assert len(prompt) > 0

    def test_instruction_language_spanish(self, sample_lesson):
        """Agent should respect instruction language preference."""
        agent = UnifiedTeachingAgent(
            lesson=sample_lesson,
            mode="help",
            instruction_language="es",
        )

        prompt = agent.build_system_prompt()

        # Should mention Spanish for explanations
        assert "spanish" in prompt.lower() or "español" in prompt.lower()

    def test_instruction_language_english(self, sample_lesson):
        """Agent should respect English instruction language."""
        agent = UnifiedTeachingAgent(
            lesson=sample_lesson,
            mode="help",
            instruction_language="en",
        )

        prompt = agent.build_system_prompt()

        # Should mention English for explanations
        assert "english" in prompt.lower()
