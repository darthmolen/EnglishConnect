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
        # Create a mock progress that will be "created"
        created_progress = MagicMock()
        created_progress.id = 1
        created_progress.user_id = uuid4()
        created_progress.lesson_id = 1
        created_progress.status = "in_progress"
        created_progress.phase_id = 1

        # First call: get_user_progress returns None (no existing)
        mock_result_none = MagicMock()
        mock_result_none.scalar_one_or_none.return_value = None

        # Second call: get_lesson_phases returns phases
        mock_result_phases = MagicMock()
        mock_result_phases.scalars.return_value.all.return_value = mock_lesson_phases

        # Third call: get_user_progress returns the created progress (after flush)
        mock_result_created = MagicMock()
        mock_result_created.scalar_one_or_none.return_value = created_progress

        mock_db.execute = AsyncMock(side_effect=[
            mock_result_none,      # get_user_progress (initial check)
            mock_result_phases,    # get_lesson_phases
            mock_result_created,   # get_user_progress (after flush)
        ])
        mock_db.add = MagicMock()
        mock_db.flush = AsyncMock()

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
        mock_progress.lesson_id = 1
        mock_progress.phase_state = {"vocab_index": 0, "pattern_index": 0, "items_completed": [], "can_skip_ahead": False}

        # Create a mock for the updated progress that will be returned
        updated_progress = MagicMock()
        updated_progress.phase_id = 2
        updated_progress.phase_state = {"vocab_index": 0, "pattern_index": 0, "items_completed": [], "can_skip_ahead": False}

        # First call: get_lesson_phases
        mock_result_phases = MagicMock()
        mock_result_phases.scalars.return_value.all.return_value = mock_lesson_phases

        # Second call: get_user_progress (after flush)
        mock_result_progress = MagicMock()
        mock_result_progress.scalar_one_or_none.return_value = updated_progress

        mock_db.execute = AsyncMock(side_effect=[mock_result_phases, mock_result_progress])
        mock_db.flush = AsyncMock()

        service = LessonProgressService(mock_db)
        # New signature returns tuple (progress, result_dict)
        new_progress, result = await service.advance_phase(
            mock_progress, total_vocab=5, total_patterns=3
        )

        # Should move to vocabulary (phase_id=2)
        assert new_progress.phase_id == 2
        # Result should indicate phase advancement
        assert result["success"] is True
        assert result["action"] == "next_phase"
        assert result["new_phase"] == "vocabulary"

    @pytest.mark.asyncio
    async def test_advance_phase_at_last_completes(
        self, mock_db, mock_progress, mock_lesson_phases
    ):
        """Should mark complete when advancing from last phase."""
        from datetime import datetime

        # Setup - progress is at wrapup (last phase, id=5)
        mock_progress.phase_id = 5
        mock_progress.lesson_id = 1
        mock_progress.phase_state = {"vocab_index": 0, "pattern_index": 0, "items_completed": [], "can_skip_ahead": False}

        # Create a mock for the completed progress
        completed_progress = MagicMock()
        completed_progress.status = "completed"
        completed_progress.completed_at = datetime.utcnow()

        # First call: get_lesson_phases
        mock_result_phases = MagicMock()
        mock_result_phases.scalars.return_value.all.return_value = mock_lesson_phases

        # Second call: get_user_progress (after flush)
        mock_result_progress = MagicMock()
        mock_result_progress.scalar_one_or_none.return_value = completed_progress

        mock_db.execute = AsyncMock(side_effect=[mock_result_phases, mock_result_progress])
        mock_db.flush = AsyncMock()

        service = LessonProgressService(mock_db)
        # New signature returns tuple (progress, result_dict)
        new_progress, result = await service.advance_phase(
            mock_progress, total_vocab=5, total_patterns=3
        )

        assert new_progress.status == "completed"
        assert new_progress.completed_at is not None
        assert result["success"] is True
        assert result["action"] == "lesson_complete"

    @pytest.mark.asyncio
    async def test_advance_item_index_vocabulary(self, mock_db, mock_progress):
        """Should increment vocab_index within vocabulary phase."""
        mock_progress.phase_state = {"vocab_index": 0, "pattern_index": 0, "items_completed": [], "can_skip_ahead": False}
        mock_db.flush = AsyncMock()

        service = LessonProgressService(mock_db)
        updated_progress, should_advance = await service.advance_item_index(
            mock_progress, item_type="vocab", total_items=3
        )

        assert mock_progress.phase_state["vocab_index"] == 1
        assert should_advance is False  # Not at last item yet

    @pytest.mark.asyncio
    async def test_advance_item_index_at_last_returns_should_advance(
        self, mock_db, mock_progress
    ):
        """Should return should_advance=True when reaching last item."""
        mock_progress.phase_state = {"vocab_index": 2, "pattern_index": 0, "items_completed": [], "can_skip_ahead": False}
        mock_db.flush = AsyncMock()

        service = LessonProgressService(mock_db)
        updated_progress, should_advance = await service.advance_item_index(
            mock_progress, item_type="vocab", total_items=3
        )

        assert should_advance is True  # At last item, should advance to next phase

    @pytest.mark.asyncio
    async def test_record_attempt(self, mock_db, mock_progress):
        """Should record correct attempt in items_completed."""
        mock_progress.phase_state = {"vocab_index": 0, "pattern_index": 0, "items_completed": [], "can_skip_ahead": False}
        mock_db.flush = AsyncMock()

        service = LessonProgressService(mock_db)
        await service.record_attempt(
            progress=mock_progress,
            item_type="vocab",
            item_id="vocab_0",
            correct=True,
        )

        # Check that item was added to items_completed
        assert "vocab_0" in mock_progress.phase_state["items_completed"]

    @pytest.mark.asyncio
    async def test_record_attempt_incorrect_not_added(self, mock_db, mock_progress):
        """Should not add incorrect attempt to items_completed."""
        mock_progress.phase_state = {"vocab_index": 0, "pattern_index": 0, "items_completed": [], "can_skip_ahead": False}
        mock_db.flush = AsyncMock()

        service = LessonProgressService(mock_db)
        await service.record_attempt(
            progress=mock_progress,
            item_type="vocab",
            item_id="vocab_0",
            correct=False,
        )

        # Check that item was NOT added (since it was incorrect)
        assert "vocab_0" not in mock_progress.phase_state["items_completed"]
