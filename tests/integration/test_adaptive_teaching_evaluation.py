"""Evaluation test scenarios for adaptive teaching behavior.

Tests the get_teaching_help tool integration with complexity-stratified
scenarios and multi-dimensional evaluation criteria:

- Student Understanding (40%): Did explanation help?
- Response Appropriateness (30%): Was help level-appropriate?
- Latency (20%): Under 2.5s total with retrieval?
- Tool Efficiency (10%): Called when needed, not excessively?
"""

import pytest
import time
from unittest.mock import AsyncMock, MagicMock, patch

from app.models.performance import PerformanceContext
from app.services.teaching_help_service import TeachingHelpService
from app.agents.lesson_teacher_agent import LessonBasedTeacherAgent
from app.models.content import LessonPhase
from app.schemas.lesson import LessonDetail, VocabularyItemSchema, QAPatternSchema
from app.schemas.lesson_session import PhaseStateSchema


@pytest.fixture
def mock_lesson():
    """Create a mock lesson with vocabulary and patterns."""
    return LessonDetail(
        lesson_number=10,
        title="Family and Relationships",
        objective="Learn to talk about family members",
        vocabulary=[
            VocabularyItemSchema(english="brother", spanish="hermano", category="noun"),
            VocabularyItemSchema(english="sister", spanish="hermana", category="noun"),
            VocabularyItemSchema(english="mother", spanish="madre", category="noun"),
        ],
        patterns=[
            QAPatternSchema(
                pattern_number=1,
                question_template="Who is your [family member]?",
                answer_template="My [family member] is [name].",
            ),
            QAPatternSchema(
                pattern_number=2,
                question_template="Do you have a [family member]?",
                answer_template="Yes, I have a [family member]. / No, I don't.",
            ),
        ],
    )


@pytest.fixture
def mock_phase():
    """Create a mock practice phase."""
    phase = MagicMock(spec=LessonPhase)
    phase.phase_type = "practice"
    phase.phase_name = "Practice"
    return phase


@pytest.fixture
def mock_phase_state():
    """Create a mock phase state."""
    return PhaseStateSchema(
        vocab_index=0,
        pattern_index=0,
        completed_vocab=[],
        completed_patterns=[],
    )


@pytest.fixture
def mock_db():
    """Create a mock async database session."""
    return AsyncMock()


class TestSimpleScenario:
    """Simple: Student asks 'What does X mean?' → retrieve vocabulary."""

    @pytest.mark.asyncio
    async def test_student_asks_word_meaning_retrieves_vocabulary(self, mock_db):
        """When student asks what a word means, should retrieve vocabulary."""
        # Setup: student in lesson 10 asks about word from earlier lesson
        vocab_item = MagicMock()
        vocab_item.lesson_id = 6
        vocab_item.english_word = "brother"
        vocab_item.spanish_translation = "hermano"
        vocab_item.category = "noun"

        lesson_result = MagicMock()
        lesson_result.fetchall.return_value = [(6,)]

        vocab_result = MagicMock()
        vocab_result.scalars.return_value.all.return_value = [vocab_item]

        pattern_result = MagicMock()
        pattern_result.fetchall.return_value = []

        pattern_query_result = MagicMock()
        pattern_query_result.scalars.return_value.all.return_value = []

        mock_db.execute.side_effect = [
            lesson_result, vocab_result,
            pattern_result, pattern_query_result
        ]

        service = TeachingHelpService(mock_db)
        result = await service.get_teaching_help("what does brother mean", lesson_number=10)

        # Evaluation: Should return vocabulary with the word
        assert len(result["vocabulary"]) > 0
        assert any("brother" in v["english"] for v in result["vocabulary"])
        assert result["source"] == "lesson-10"

    @pytest.mark.asyncio
    async def test_simple_query_response_is_appropriate(self, mock_db):
        """Simple word query should return focused, not overwhelming response."""
        vocab_item = MagicMock()
        vocab_item.lesson_id = 5
        vocab_item.english_word = "cook"
        vocab_item.spanish_translation = "cocinar"
        vocab_item.category = "verb"

        lesson_result = MagicMock()
        lesson_result.fetchall.return_value = [(5,)]

        vocab_result = MagicMock()
        vocab_result.scalars.return_value.all.return_value = [vocab_item]

        mock_db.execute.side_effect = [
            lesson_result, vocab_result,
            MagicMock(fetchall=MagicMock(return_value=[])),
            MagicMock(scalars=MagicMock(return_value=MagicMock(all=MagicMock(return_value=[]))))
        ]

        service = TeachingHelpService(mock_db)
        result = await service.get_teaching_help("cook", lesson_number=10)

        # Response appropriateness: not too many results for simple query
        assert len(result["vocabulary"]) <= 5  # Focused, not overwhelming


class TestMediumScenario:
    """Medium: 2 consecutive errors → proactive help retrieval."""

    def test_two_errors_triggers_medium_struggle_level(self):
        """PerformanceContext should indicate medium struggle after 2 errors."""
        ctx = PerformanceContext()
        ctx.record_attempt(correct=False)
        ctx.record_attempt(correct=False)

        assert ctx.consecutive_errors == 2
        assert ctx.struggle_level == "medium"
        assert ctx.needs_help is True

    def test_prompt_includes_struggle_context(self, mock_lesson, mock_phase, mock_phase_state):
        """System prompt should include struggle level for LLM to detect."""
        ctx = PerformanceContext()
        ctx.record_attempt(correct=False)
        ctx.record_attempt(correct=False)

        agent = LessonBasedTeacherAgent(
            lesson=mock_lesson,
            phase=mock_phase,
            phase_state=mock_phase_state,
            performance_context=ctx,
        )

        prompt = agent.build_system_prompt()

        # Prompt should expose struggle indicators
        assert "medium" in prompt or "struggle" in prompt.lower()
        assert "2" in prompt or "consecutive" in prompt.lower()

    @pytest.mark.asyncio
    async def test_proactive_retrieval_returns_helpful_content(self, mock_db):
        """When struggling, retrieved content should include exercises."""
        # Empty vocab/pattern results but exercises available
        empty_result = MagicMock()
        empty_result.fetchall.return_value = []
        empty_result.scalars.return_value.all.return_value = []
        mock_db.execute.return_value = empty_result

        service = TeachingHelpService(mock_db)

        with patch.object(
            service, "get_workbook_exercises",
            return_value=[{"title": "Practice Activity", "content": "Listen and repeat..."}]
        ):
            result = await service.get_teaching_help("pattern practice", lesson_number=5)

        # Should include exercises for extra practice
        assert len(result["exercises"]) > 0
        assert "Practice" in result["exercises"][0]["title"]


class TestComplexScenario:
    """Complex: Student confused about pattern structure → retrieve pattern + exercises."""

    @pytest.mark.asyncio
    async def test_pattern_confusion_retrieves_patterns_and_exercises(self, mock_db):
        """Confusion about pattern should return pattern examples and exercises."""
        pattern = MagicMock()
        pattern.lesson_id = 6
        pattern.pattern_number = 1
        pattern.question_template = "Who is your [family member]?"
        pattern.answer_template = "My [family member] is [name]."
        pattern.examples = [{"q": "Who is your brother?", "a": "My brother is Miguel."}]

        # Setup mock returns
        lesson_result = MagicMock()
        lesson_result.fetchall.return_value = [(6,)]

        vocab_result = MagicMock()
        vocab_result.scalars.return_value.all.return_value = []

        pattern_lesson_result = MagicMock()
        pattern_lesson_result.fetchall.return_value = [(6,)]

        pattern_result = MagicMock()
        pattern_result.scalars.return_value.all.return_value = [pattern]

        mock_db.execute.side_effect = [
            lesson_result, vocab_result,
            pattern_lesson_result, pattern_result
        ]

        service = TeachingHelpService(mock_db)

        with patch.object(
            service, "get_workbook_exercises",
            return_value=[{"title": "Question Practice", "content": "Practice asking questions"}]
        ):
            result = await service.get_teaching_help("how to ask family questions", lesson_number=10)

        # Should return both patterns and exercises
        assert len(result["patterns"]) > 0
        assert "question" in result["patterns"][0]
        assert len(result["exercises"]) > 0

    def test_high_struggle_detected_after_three_errors(self):
        """Three consecutive errors should trigger high struggle level."""
        ctx = PerformanceContext()
        ctx.record_attempt(correct=False)
        ctx.record_attempt(correct=False)
        ctx.record_attempt(correct=False)

        assert ctx.struggle_level == "high"
        assert ctx.consecutive_errors == 3


class TestEdgeScenario:
    """Edge: Student asks about content from future lesson → graceful handling."""

    @pytest.mark.asyncio
    async def test_future_lesson_content_returns_empty_gracefully(self, mock_db):
        """Query about future lesson content should return empty, not error."""
        # No results because we only search up to current lesson
        empty_result = MagicMock()
        empty_result.fetchall.return_value = []
        empty_result.scalars.return_value.all.return_value = []
        mock_db.execute.return_value = empty_result

        service = TeachingHelpService(mock_db)
        result = await service.get_teaching_help("advanced grammar", lesson_number=5)

        # Should return structure with empty content, not crash
        assert "vocabulary" in result
        assert "patterns" in result
        assert result["vocabulary"] == []
        assert result["patterns"] == []
        assert result["source"] == "lesson-5"

    @pytest.mark.asyncio
    async def test_empty_query_handled_gracefully(self, mock_db):
        """Empty or minimal query should still return valid structure."""
        empty_result = MagicMock()
        empty_result.fetchall.return_value = []
        empty_result.scalars.return_value.all.return_value = []
        mock_db.execute.return_value = empty_result

        service = TeachingHelpService(mock_db)
        result = await service.get_teaching_help("", lesson_number=5)

        assert isinstance(result, dict)
        assert "vocabulary" in result
        assert "patterns" in result


class TestLatencyRequirements:
    """Latency: Under 2.5s total with retrieval."""

    @pytest.mark.asyncio
    async def test_retrieval_completes_within_budget(self, mock_db):
        """Teaching help retrieval should complete within latency budget."""
        # Setup quick-returning mocks
        empty_result = MagicMock()
        empty_result.fetchall.return_value = []
        empty_result.scalars.return_value.all.return_value = []
        mock_db.execute.return_value = empty_result

        service = TeachingHelpService(mock_db)

        start = time.time()
        await service.get_teaching_help("test query", lesson_number=5)
        elapsed = time.time() - start

        # Retrieval itself should be well under 500ms (our budget)
        # With mocks this should be essentially instant
        assert elapsed < 0.5  # 500ms max for retrieval


class TestToolEfficiency:
    """Tool Efficiency: Called when needed, not excessively."""

    def test_low_struggle_does_not_require_help(self):
        """Low struggle level should not trigger needs_help."""
        ctx = PerformanceContext()
        ctx.record_attempt(correct=False)  # Just 1 error

        assert ctx.struggle_level == "low"
        assert ctx.needs_help is False

    def test_correct_answer_resets_struggle(self):
        """Correct answer should reset consecutive errors."""
        ctx = PerformanceContext()
        ctx.record_attempt(correct=False)
        ctx.record_attempt(correct=False)
        assert ctx.needs_help is True

        ctx.record_attempt(correct=True)
        assert ctx.consecutive_errors == 0
        assert ctx.needs_help is False

    def test_prompt_guides_tool_usage(self, mock_lesson, mock_phase, mock_phase_state):
        """Prompt should guide when to call vs not call the tool."""
        ctx = PerformanceContext()  # Low struggle

        agent = LessonBasedTeacherAgent(
            lesson=mock_lesson,
            phase=mock_phase,
            phase_state=mock_phase_state,
            performance_context=ctx,
        )

        prompt = agent.build_system_prompt()

        # Should include guidance about when NOT to call
        assert "do not call" in prompt.lower() or "don't call" in prompt.lower()


class TestMultiDimensionalEvaluation:
    """Combined evaluation across all dimensions."""

    @pytest.mark.asyncio
    async def test_complete_help_flow_meets_criteria(self, mock_db, mock_lesson, mock_phase, mock_phase_state):
        """Full help flow should meet all evaluation criteria."""
        # Setup performance context with struggle
        ctx = PerformanceContext()
        ctx.record_attempt(correct=False)
        ctx.record_attempt(correct=False)

        # Verify struggle detection
        assert ctx.needs_help is True  # Tool Efficiency: triggers when needed

        # Setup mock for retrieval
        vocab_item = MagicMock()
        vocab_item.lesson_id = 6
        vocab_item.english_word = "brother"
        vocab_item.spanish_translation = "hermano"
        vocab_item.category = "noun"

        lesson_result = MagicMock()
        lesson_result.fetchall.return_value = [(6,)]

        vocab_result = MagicMock()
        vocab_result.scalars.return_value.all.return_value = [vocab_item]

        mock_db.execute.side_effect = [
            lesson_result, vocab_result,
            MagicMock(fetchall=MagicMock(return_value=[])),
            MagicMock(scalars=MagicMock(return_value=MagicMock(all=MagicMock(return_value=[]))))
        ]

        # Verify retrieval works
        service = TeachingHelpService(mock_db)
        start = time.time()
        result = await service.get_teaching_help("brother", lesson_number=10)
        elapsed = time.time() - start

        # Latency: fast
        assert elapsed < 0.5

        # Response Appropriateness: returns relevant content
        assert len(result["vocabulary"]) > 0

        # Student Understanding: content is actionable (has translation)
        assert any("hermano" in v.get("spanish", "") for v in result["vocabulary"])

        # Build prompt with context
        agent = LessonBasedTeacherAgent(
            lesson=mock_lesson,
            phase=mock_phase,
            phase_state=mock_phase_state,
            performance_context=ctx,
        )
        prompt = agent.build_system_prompt()

        # Prompt includes struggle context for LLM
        assert "medium" in prompt or "struggle" in prompt.lower()
