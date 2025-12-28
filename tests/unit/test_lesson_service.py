"""Unit tests for LessonService."""

import pytest
from unittest.mock import AsyncMock, MagicMock
from sqlalchemy.ext.asyncio import AsyncSession


class TestLessonService:
    """Test LessonService methods."""

    @pytest.fixture
    def mock_session(self):
        """Create a mock async database session."""
        session = AsyncMock(spec=AsyncSession)
        return session

    @pytest.mark.asyncio
    async def test_list_lessons_returns_lesson_summaries(self, mock_session):
        """list_lessons should return list of LessonSummary objects."""
        from app.services.lesson_service import LessonService
        from app.schemas.lesson import LessonSummary

        # Mock the execute result
        mock_lesson1 = MagicMock()
        mock_lesson1.lesson_number = 1
        mock_lesson1.title = "Introduction"
        mock_lesson1.objective = "Learn basics"

        mock_lesson2 = MagicMock()
        mock_lesson2.lesson_number = 2
        mock_lesson2.title = "Greetings"
        mock_lesson2.objective = "Learn greetings"

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [mock_lesson1, mock_lesson2]
        mock_session.execute.return_value = mock_result

        service = LessonService(mock_session)
        lessons = await service.list_lessons("ec1")

        assert len(lessons) == 2
        assert isinstance(lessons[0], LessonSummary)
        assert lessons[0].lesson_number == 1
        assert lessons[0].title == "Introduction"

    @pytest.mark.asyncio
    async def test_get_lesson_detail_returns_none_for_missing(self, mock_session):
        """get_lesson_detail should return None if lesson not found."""
        from app.services.lesson_service import LessonService

        # Mock the execute result - lesson not found
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result

        service = LessonService(mock_session)
        detail = await service.get_lesson_detail("ec1", 999)

        assert detail is None

    @pytest.mark.asyncio
    async def test_get_lesson_detail_returns_full_data(self, mock_session):
        """get_lesson_detail should return LessonDetail with all fields."""
        from app.services.lesson_service import LessonService
        from app.schemas.lesson import LessonDetail

        # Mock lesson
        mock_lesson = MagicMock()
        mock_lesson.id = 5
        mock_lesson.lesson_number = 5
        mock_lesson.title = "Hobbies"
        mock_lesson.objective = "Learn hobbies"
        mock_lesson.learning_principle_title = "Faith"
        mock_lesson.learning_principle = "Learn by faith"
        mock_lesson.learning_principle_full = "Full text about faith and learning"
        mock_lesson.ponder_questions = ["What is faith?"]
        mock_lesson.pattern_images = ["_page_19_Figure_1.jpeg"]

        # Mock vocabulary
        mock_vocab = MagicMock()
        mock_vocab.english_word = "exercise"
        mock_vocab.spanish_translation = "hacer ejercicio"
        mock_vocab.category = "verb"

        # Mock pattern
        mock_pattern = MagicMock()
        mock_pattern.pattern_number = 1
        mock_pattern.question_template = "What do you like?"
        mock_pattern.answer_template = "I like..."
        mock_pattern.examples = []

        # Mock criterion
        mock_criterion = MagicMock()
        mock_criterion.criterion = "Say why I like something"

        # Configure mock session to return different results for each query
        lesson_result = MagicMock()
        lesson_result.scalar_one_or_none.return_value = mock_lesson

        vocab_result = MagicMock()
        vocab_result.scalars.return_value = [mock_vocab]

        pattern_result = MagicMock()
        pattern_result.scalars.return_value = [mock_pattern]

        criterion_result = MagicMock()
        criterion_result.scalars.return_value = [mock_criterion]

        mock_session.execute.side_effect = [
            lesson_result,
            vocab_result,
            pattern_result,
            criterion_result,
        ]

        service = LessonService(mock_session)
        detail = await service.get_lesson_detail("ec1", 5)

        assert detail is not None
        assert isinstance(detail, LessonDetail)
        assert detail.lesson_number == 5
        assert detail.title == "Hobbies"
        assert len(detail.vocabulary) == 1
        assert detail.vocabulary[0].english == "exercise"
        assert len(detail.patterns) == 1
        assert len(detail.evaluation_criteria) == 1
