"""Unit tests for LessonBasedTeacherAgent."""

import pytest
from unittest.mock import MagicMock

from app.agents.lesson_teacher_agent import LessonBasedTeacherAgent
from app.schemas.lesson import LessonDetail, VocabularyItemSchema, QAPatternSchema
from app.schemas.lesson_session import PhaseStateSchema


@pytest.fixture
def sample_lesson():
    """Create a sample lesson for testing."""
    return LessonDetail(
        lesson_number=5,
        title="Hobbies and Interests",
        objective="Learn to talk about hobbies and free-time activities",
        learning_principle_title="Practice Makes Perfect",
        learning_principle_content="Regular practice helps build confidence.",
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
        evaluation_criteria=[
            "I can say what I like to do.",
            "I can ask others about their hobbies.",
        ],
    )


@pytest.fixture
def sample_phase():
    """Create a sample phase for testing."""
    phase = MagicMock()
    phase.id = 1
    phase.phase_type = "intro"
    phase.phase_name = "Introduction"
    phase.sort_order = 0
    return phase


@pytest.fixture
def sample_phase_state():
    """Create a sample phase state."""
    return PhaseStateSchema(
        vocab_index=0,
        pattern_index=0,
        items_completed=[],
        can_skip_ahead=False,
    )


class TestLessonBasedTeacherAgent:
    """Test LessonBasedTeacherAgent methods."""

    def test_init_creates_agent(self, sample_lesson, sample_phase, sample_phase_state):
        """Agent should initialize with lesson, phase, and state."""
        agent = LessonBasedTeacherAgent(
            lesson=sample_lesson,
            phase=sample_phase,
            phase_state=sample_phase_state,
        )

        assert agent.lesson == sample_lesson
        assert agent.phase == sample_phase
        assert agent.phase_state == sample_phase_state

    def test_build_system_prompt_includes_lesson_info(
        self, sample_lesson, sample_phase, sample_phase_state
    ):
        """System prompt should include lesson title and objective."""
        agent = LessonBasedTeacherAgent(
            lesson=sample_lesson,
            phase=sample_phase,
            phase_state=sample_phase_state,
        )

        prompt = agent.build_system_prompt()

        assert "Hobbies and Interests" in prompt
        assert "5" in prompt or "Lesson 5" in prompt

    def test_build_system_prompt_intro_phase(
        self, sample_lesson, sample_phase, sample_phase_state
    ):
        """Intro phase prompt should welcome student and introduce objective."""
        sample_phase.phase_type = "intro"
        sample_phase.phase_name = "Introduction"

        agent = LessonBasedTeacherAgent(
            lesson=sample_lesson,
            phase=sample_phase,
            phase_state=sample_phase_state,
        )

        prompt = agent.build_system_prompt()

        # Should have intro-specific instructions
        assert "welcome" in prompt.lower() or "introduce" in prompt.lower()

    def test_build_system_prompt_vocabulary_phase(
        self, sample_lesson, sample_phase, sample_phase_state
    ):
        """Vocabulary phase prompt should include current word."""
        sample_phase.phase_type = "vocabulary"
        sample_phase.phase_name = "Vocabulary Practice"
        sample_phase_state.vocab_index = 0

        agent = LessonBasedTeacherAgent(
            lesson=sample_lesson,
            phase=sample_phase,
            phase_state=sample_phase_state,
        )

        prompt = agent.build_system_prompt()

        # Should include current vocabulary word
        assert "exercise" in prompt
        assert "hacer ejercicio" in prompt

    def test_build_system_prompt_vocabulary_advances(
        self, sample_lesson, sample_phase, sample_phase_state
    ):
        """Vocabulary phase should show correct word based on index."""
        sample_phase.phase_type = "vocabulary"
        sample_phase.phase_name = "Vocabulary Practice"
        sample_phase_state.vocab_index = 1  # Second word

        agent = LessonBasedTeacherAgent(
            lesson=sample_lesson,
            phase=sample_phase,
            phase_state=sample_phase_state,
        )

        prompt = agent.build_system_prompt()

        # Should include second vocabulary word
        assert "sing" in prompt
        assert "cantar" in prompt

    def test_build_system_prompt_patterns_phase(
        self, sample_lesson, sample_phase, sample_phase_state
    ):
        """Patterns phase prompt should include current pattern."""
        sample_phase.phase_type = "patterns"
        sample_phase.phase_name = "Q&A Patterns"
        sample_phase_state.pattern_index = 0

        agent = LessonBasedTeacherAgent(
            lesson=sample_lesson,
            phase=sample_phase,
            phase_state=sample_phase_state,
        )

        prompt = agent.build_system_prompt()

        # Should include first pattern
        assert "What do you like to do?" in prompt
        assert "I like to" in prompt

    def test_build_system_prompt_practice_phase(
        self, sample_lesson, sample_phase, sample_phase_state
    ):
        """Practice phase prompt should include all vocabulary and patterns."""
        sample_phase.phase_type = "practice"
        sample_phase.phase_name = "Conversation Practice"

        agent = LessonBasedTeacherAgent(
            lesson=sample_lesson,
            phase=sample_phase,
            phase_state=sample_phase_state,
        )

        prompt = agent.build_system_prompt()

        # Should include all vocabulary
        assert "exercise" in prompt
        assert "sing" in prompt
        # Should include patterns
        assert "What do you like to do?" in prompt

    def test_build_system_prompt_wrapup_phase(
        self, sample_lesson, sample_phase, sample_phase_state
    ):
        """Wrapup phase prompt should encourage summary."""
        sample_phase.phase_type = "wrapup"
        sample_phase.phase_name = "Lesson Summary"

        agent = LessonBasedTeacherAgent(
            lesson=sample_lesson,
            phase=sample_phase,
            phase_state=sample_phase_state,
        )

        prompt = agent.build_system_prompt()

        # Should have wrapup-specific instructions
        assert "summary" in prompt.lower() or "congratul" in prompt.lower()

    def test_get_phase_progress_vocabulary(
        self, sample_lesson, sample_phase, sample_phase_state
    ):
        """Phase progress for vocabulary should show current/total."""
        sample_phase.phase_type = "vocabulary"
        sample_phase_state.vocab_index = 1

        agent = LessonBasedTeacherAgent(
            lesson=sample_lesson,
            phase=sample_phase,
            phase_state=sample_phase_state,
        )

        progress = agent.get_phase_progress()

        assert progress is not None
        assert progress.current == 2  # 0-indexed becomes 1-indexed
        assert progress.total == 3

    def test_get_phase_progress_patterns(
        self, sample_lesson, sample_phase, sample_phase_state
    ):
        """Phase progress for patterns should show current/total."""
        sample_phase.phase_type = "patterns"
        sample_phase_state.pattern_index = 0

        agent = LessonBasedTeacherAgent(
            lesson=sample_lesson,
            phase=sample_phase,
            phase_state=sample_phase_state,
        )

        progress = agent.get_phase_progress()

        assert progress is not None
        assert progress.current == 1
        assert progress.total == 2

    def test_get_phase_progress_intro_returns_none(
        self, sample_lesson, sample_phase, sample_phase_state
    ):
        """Intro phase should not have progress indicator."""
        sample_phase.phase_type = "intro"

        agent = LessonBasedTeacherAgent(
            lesson=sample_lesson,
            phase=sample_phase,
            phase_state=sample_phase_state,
        )

        progress = agent.get_phase_progress()

        assert progress is None

    def test_get_phase_progress_wrapup_returns_none(
        self, sample_lesson, sample_phase, sample_phase_state
    ):
        """Wrapup phase should not have progress indicator."""
        sample_phase.phase_type = "wrapup"

        agent = LessonBasedTeacherAgent(
            lesson=sample_lesson,
            phase=sample_phase,
            phase_state=sample_phase_state,
        )

        progress = agent.get_phase_progress()

        assert progress is None
