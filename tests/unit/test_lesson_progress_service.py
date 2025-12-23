"""Unit tests for LessonProgressService."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

from app.services.lesson_progress_service import LessonProgressService
from app.schemas.lesson_session import PhaseStateSchema


@pytest.fixture
def mock_db():
    """Create a mock async database session."""
    db = AsyncMock()
    return db


@pytest.fixture
def mock_lesson_phases():
    """Create mock lesson phases."""
    phases = []
    for i, (phase_type, name) in enumerate([
        ("intro", "Introduction"),
        ("vocabulary", "Vocabulary Practice"),
        ("patterns", "Q&A Patterns"),
        ("practice", "Conversation Practice"),
        ("wrapup", "Lesson Summary"),
    ]):
        phase = MagicMock()
        phase.id = i + 1
        phase.phase_type = phase_type
        phase.phase_name = name
        phase.sort_order = i
        phases.append(phase)
    return phases


@pytest.fixture
def mock_progress():
    """Create a mock UserProgress object."""
    progress = MagicMock()
    progress.id = 1
    progress.user_id = uuid4()
    progress.lesson_id = 1
    progress.status = "in_progress"
    progress.phase_id = 1
    progress.phase_state = {"vocab_index": 0, "pattern_index": 0}
    progress.attempts = []
    return progress


class TestLessonProgressService:
    """Test LessonProgressService methods."""

    @pytest.mark.asyncio
    async def test_get_lesson_phases(self, mock_db, mock_lesson_phases):
        """Should return all phases for a lesson in order."""
        # Setup mock query result
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = mock_lesson_phases
        mock_db.execute = AsyncMock(return_value=mock_result)

        service = LessonProgressService(mock_db)
        phases = await service.get_lesson_phases(lesson_id=1)

        assert len(phases) == 5
        assert phases[0].phase_type == "intro"
        assert phases[4].phase_type == "wrapup"

    @pytest.mark.asyncio
    async def test_get_user_progress_existing(self, mock_db, mock_progress):
        """Should return existing progress for user/lesson."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_progress
        mock_db.execute = AsyncMock(return_value=mock_result)

        service = LessonProgressService(mock_db)
        progress = await service.get_user_progress(
            user_id=mock_progress.user_id,
            lesson_id=1,
        )

        assert progress is not None
        assert progress.status == "in_progress"

    @pytest.mark.asyncio
    async def test_get_user_progress_not_found(self, mock_db):
        """Should return None if no progress exists."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute = AsyncMock(return_value=mock_result)

        service = LessonProgressService(mock_db)
        progress = await service.get_user_progress(
            user_id=uuid4(),
            lesson_id=1,
        )

        assert progress is None

    @pytest.mark.asyncio
    async def test_get_or_create_progress_creates_new(
        self, mock_db, mock_lesson_phases
    ):
        """Should create new progress if none exists."""
        # First call returns None (no existing progress)
        mock_result_none = MagicMock()
        mock_result_none.scalar_one_or_none.return_value = None

        # Second call returns phases
        mock_result_phases = MagicMock()
        mock_result_phases.scalars.return_value.all.return_value = mock_lesson_phases

        mock_db.execute = AsyncMock(side_effect=[mock_result_none, mock_result_phases])
        mock_db.add = MagicMock()
        mock_db.flush = AsyncMock()
        mock_db.refresh = AsyncMock()

        service = LessonProgressService(mock_db)
        progress, is_new = await service.get_or_create_progress(
            user_id=uuid4(),
            lesson_id=1,
        )

        assert is_new is True
        mock_db.add.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_or_create_progress_returns_existing(
        self, mock_db, mock_progress
    ):
        """Should return existing progress without creating new."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_progress
        mock_db.execute = AsyncMock(return_value=mock_result)

        service = LessonProgressService(mock_db)
        progress, is_new = await service.get_or_create_progress(
            user_id=mock_progress.user_id,
            lesson_id=1,
        )

        assert is_new is False
        assert progress == mock_progress

    @pytest.mark.asyncio
    async def test_update_phase_state(self, mock_db, mock_progress):
        """Should update phase state on progress."""
        mock_db.flush = AsyncMock()

        service = LessonProgressService(mock_db)
        new_state = PhaseStateSchema(vocab_index=2, pattern_index=1)

        await service.update_phase_state(mock_progress, new_state)

        assert mock_progress.phase_state == new_state.model_dump()
        mock_db.flush.assert_called_once()

    @pytest.mark.asyncio
    async def test_advance_phase(self, mock_db, mock_progress, mock_lesson_phases):
        """Should advance to next phase."""
        # Setup - progress is at intro (phase_id=1)
        mock_progress.phase_id = 1

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = mock_lesson_phases
        mock_db.execute = AsyncMock(return_value=mock_result)
        mock_db.flush = AsyncMock()

        service = LessonProgressService(mock_db)
        new_progress = await service.advance_phase(mock_progress)

        # Should move to vocabulary (phase_id=2)
        assert new_progress.phase_id == 2
        # Phase state should be reset
        assert new_progress.phase_state == {"vocab_index": 0, "pattern_index": 0, "items_completed": [], "can_skip_ahead": False}

    @pytest.mark.asyncio
    async def test_advance_phase_at_last_completes(
        self, mock_db, mock_progress, mock_lesson_phases
    ):
        """Should mark complete when advancing from last phase."""
        # Setup - progress is at wrapup (last phase, id=5)
        mock_progress.phase_id = 5

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = mock_lesson_phases
        mock_db.execute = AsyncMock(return_value=mock_result)
        mock_db.flush = AsyncMock()

        service = LessonProgressService(mock_db)
        new_progress = await service.advance_phase(mock_progress)

        assert new_progress.status == "completed"
        assert new_progress.completed_at is not None

    @pytest.mark.asyncio
    async def test_advance_item_index_vocabulary(self, mock_db, mock_progress):
        """Should increment vocab_index within vocabulary phase."""
        mock_progress.phase_state = {"vocab_index": 0, "pattern_index": 0, "items_completed": [], "can_skip_ahead": False}
        mock_db.flush = AsyncMock()

        service = LessonProgressService(mock_db)
        new_index = await service.advance_item_index(
            mock_progress, item_type="vocab", max_items=3
        )

        assert new_index == 1
        assert mock_progress.phase_state["vocab_index"] == 1

    @pytest.mark.asyncio
    async def test_advance_item_index_at_last_returns_none(
        self, mock_db, mock_progress
    ):
        """Should return None when at last item."""
        mock_progress.phase_state = {"vocab_index": 2, "pattern_index": 0, "items_completed": [], "can_skip_ahead": False}

        service = LessonProgressService(mock_db)
        new_index = await service.advance_item_index(
            mock_progress, item_type="vocab", max_items=3
        )

        assert new_index is None  # At last item, can't advance

    @pytest.mark.asyncio
    async def test_record_attempt(self, mock_db, mock_progress):
        """Should record student attempt."""
        mock_db.flush = AsyncMock()

        service = LessonProgressService(mock_db)
        await service.record_attempt(
            progress=mock_progress,
            item_type="vocab",
            item_id="vocab_0",
            correct=True,
        )

        # Check that attempt was recorded
        assert len(mock_progress.attempts) == 1
        assert mock_progress.attempts[0]["item_type"] == "vocab"
        assert mock_progress.attempts[0]["correct"] is True
