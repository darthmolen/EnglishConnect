"""Unit tests for conversation router endpoints."""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from httpx import AsyncClient, ASGITransport


class TestConversationRouter:
    """Test conversation API endpoints."""

    @pytest.mark.asyncio
    async def test_conversation_returns_200(self, mock_auth):
        """POST /api/practice/conversation should return 200 with AI response."""
        from app.main import app
        from app.schemas.lesson import LessonDetail

        with patch("app.routers.conversation.LessonService") as mock_lesson_service:
            with patch("app.routers.conversation.SessionService") as mock_session_service:
                mock_lesson_instance = AsyncMock()
                mock_lesson_instance.get_lesson_detail.return_value = LessonDetail(
                    lesson_number=5,
                    title="Hobbies",
                    objective="Learn hobbies",
                    vocabulary=[],
                    patterns=[],
                    evaluation_criteria=[],
                )
                mock_lesson_service.return_value = mock_lesson_instance

                # Mock session service to avoid database operations
                mock_session_instance = AsyncMock()
                mock_session = MagicMock()
                mock_session.id = 1
                mock_session_instance.get_or_create_session.return_value = mock_session
                mock_session_service.return_value = mock_session_instance

                async with AsyncClient(
                    transport=ASGITransport(app=app), base_url="http://test"
                ) as client:
                    response = await client.post(
                        "/api/practice/conversation",
                        json={"message": "Hello", "lesson_number": 5},
                    )

        assert response.status_code == 200
        data = response.json()
        assert "text" in data
        assert data["lesson_number"] == 5

    @pytest.mark.asyncio
    async def test_conversation_returns_404_for_missing_lesson(self, mock_auth):
        """POST /api/practice/conversation should return 404 if lesson not found."""
        from app.main import app

        with patch("app.routers.conversation.LessonService") as mock_service:
            mock_instance = AsyncMock()
            mock_instance.get_lesson_detail.return_value = None
            mock_service.return_value = mock_instance

            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                response = await client.post(
                    "/api/practice/conversation",
                    json={"message": "Hello", "lesson_number": 999},
                )

        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_conversation_accepts_history(self, mock_auth):
        """POST /api/practice/conversation should accept conversation history."""
        from app.main import app
        from app.schemas.lesson import LessonDetail

        with patch("app.routers.conversation.LessonService") as mock_lesson_service:
            with patch("app.routers.conversation.SessionService") as mock_session_service:
                mock_lesson_instance = AsyncMock()
                mock_lesson_instance.get_lesson_detail.return_value = LessonDetail(
                    lesson_number=5,
                    title="Hobbies",
                    vocabulary=[],
                    patterns=[],
                    evaluation_criteria=[],
                )
                mock_lesson_service.return_value = mock_lesson_instance

                # Mock session service to avoid database operations
                mock_session_instance = AsyncMock()
                mock_session = MagicMock()
                mock_session.id = 1
                mock_session_instance.get_or_create_session.return_value = mock_session
                mock_session_service.return_value = mock_session_instance

                async with AsyncClient(
                    transport=ASGITransport(app=app), base_url="http://test"
                ) as client:
                    response = await client.post(
                        "/api/practice/conversation",
                        json={
                            "message": "I like soccer",
                            "lesson_number": 5,
                            "history": [
                                {"role": "user", "content": "Hello"},
                                {"role": "assistant", "content": "Hi! What do you like to do?"},
                            ],
                        },
                    )

        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_conversation_validates_request(self, mock_auth):
        """POST /api/practice/conversation should validate request body."""
        from app.main import app

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            # Missing required fields
            response = await client.post(
                "/api/practice/conversation",
                json={"message": "Hello"},  # Missing lesson_number
            )

        assert response.status_code == 422  # Validation error
