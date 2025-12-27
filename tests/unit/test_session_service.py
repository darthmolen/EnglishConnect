"""Unit tests for SessionService."""

import pytest
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4
from datetime import datetime, timedelta

from app.services.session_service import SessionService


@pytest.fixture
def mock_db():
    """Create a mock async database session."""
    db = AsyncMock()
    return db


@pytest.fixture
def mock_session():
    """Create a mock PracticeSession."""
    session = MagicMock()
    session.id = 1
    session.user_id = uuid4()
    session.lesson_id = 5
    session.session_type = "conversation_practice"
    session.started_at = datetime.utcnow() - timedelta(minutes=10)
    session.ended_at = None
    session.exchanges_count = 3
    return session


class TestSessionService:
    """Test SessionService methods."""

    @pytest.mark.asyncio
    async def test_get_or_create_session_creates_new_when_none_exists(self, mock_db):
        """Should create new session when no existing session found."""
        user_id = uuid4()

        # Mock: no existing session found
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute = AsyncMock(return_value=mock_result)
        mock_db.add = MagicMock()
        mock_db.flush = AsyncMock()

        service = SessionService(mock_db)
        session = await service.get_or_create_session(
            user_id=user_id,
            lesson_id=5,
            session_type="conversation_practice",
        )

        # Should have added a new session
        mock_db.add.assert_called_once()
        mock_db.flush.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_or_create_session_reuses_existing_within_window(
        self, mock_db, mock_session
    ):
        """Should reuse existing session if within time window."""
        # Mock: existing session found within window
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_session
        mock_db.execute = AsyncMock(return_value=mock_result)

        service = SessionService(mock_db)
        session = await service.get_or_create_session(
            user_id=mock_session.user_id,
            lesson_id=5,
            session_type="conversation_practice",
        )

        # Should return existing session, not create new
        assert session == mock_session
        mock_db.add.assert_not_called()

    @pytest.mark.asyncio
    async def test_get_or_create_session_creates_new_for_different_lesson(
        self, mock_db
    ):
        """Should create new session for different lesson even if recent session exists."""
        user_id = uuid4()

        # Mock: no matching session for this lesson
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute = AsyncMock(return_value=mock_result)
        mock_db.add = MagicMock()
        mock_db.flush = AsyncMock()

        service = SessionService(mock_db)
        session = await service.get_or_create_session(
            user_id=user_id,
            lesson_id=10,  # Different lesson
            session_type="conversation_practice",
        )

        # Should create new session
        mock_db.add.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_or_create_session_creates_new_for_anonymous(self, mock_db):
        """Should always create new session for anonymous users (no user_id)."""
        mock_db.add = MagicMock()
        mock_db.flush = AsyncMock()

        service = SessionService(mock_db)
        session = await service.get_or_create_session(
            user_id=None,  # Anonymous
            lesson_id=5,
            session_type="conversation_practice",
        )

        # Should create new session without checking for existing
        mock_db.add.assert_called_once()
        # execute should NOT be called (no query for anonymous)
        mock_db.execute.assert_not_called()

    @pytest.mark.asyncio
    async def test_record_exchange_increments_count(self, mock_db, mock_session):
        """Should record exchange and update session count."""
        # Mock for getting max sequence number
        mock_seq_result = MagicMock()
        mock_seq_result.scalar.return_value = 2

        # Mock for getting session
        mock_session_result = MagicMock()
        mock_session_result.scalar_one_or_none.return_value = mock_session

        mock_db.execute = AsyncMock(
            side_effect=[mock_seq_result, mock_session_result]
        )
        mock_db.add = MagicMock()
        mock_db.flush = AsyncMock()

        service = SessionService(mock_db)
        exchange = await service.record_exchange(
            session_id=mock_session.id,
            agent_utterance="Hello, how are you?",
            user_utterance="I'm good, thanks!",
        )

        # Should have added new exchange
        mock_db.add.assert_called_once()
        # Session count should be updated to 3 (max was 2, +1)
        assert mock_session.exchanges_count == 3
