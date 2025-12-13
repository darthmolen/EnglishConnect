"""Unit tests for lessons router endpoints."""

import pytest
from unittest.mock import AsyncMock, patch
from httpx import AsyncClient, ASGITransport


@pytest.fixture
def mock_lesson_service():
    """Create mock LessonService."""
    with patch("app.routers.lessons.LessonService") as mock:
        yield mock


class TestLessonsRouter:
    """Test lessons API endpoints."""

    @pytest.mark.asyncio
    async def test_list_lessons_returns_200(self, mock_lesson_service):
        """GET /api/lessons should return 200 with list of lessons."""
        from app.main import app
        from app.schemas.lesson import LessonSummary

        # Mock the service
        mock_instance = AsyncMock()
        mock_instance.list_lessons.return_value = [
            LessonSummary(lesson_number=1, title="Introduction", objective="Learn basics"),
            LessonSummary(lesson_number=2, title="Greetings", objective="Say hello"),
        ]
        mock_lesson_service.return_value = mock_instance

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.get("/api/lessons")

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2
        assert data[0]["lesson_number"] == 1

    @pytest.mark.asyncio
    async def test_list_lessons_accepts_course_id(self, mock_lesson_service):
        """GET /api/lessons should accept course_id query parameter."""
        from app.main import app
        from app.schemas.lesson import LessonSummary

        mock_instance = AsyncMock()
        mock_instance.list_lessons.return_value = []
        mock_lesson_service.return_value = mock_instance

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.get("/api/lessons?course_id=ec2")

        assert response.status_code == 200
        mock_instance.list_lessons.assert_called_once_with("ec2")

    @pytest.mark.asyncio
    async def test_get_lesson_returns_200_for_existing(self, mock_lesson_service):
        """GET /api/lessons/{lesson_number} should return 200 for existing lesson."""
        from app.main import app
        from app.schemas.lesson import LessonDetail

        mock_instance = AsyncMock()
        mock_instance.get_lesson_detail.return_value = LessonDetail(
            lesson_number=5,
            title="Hobbies",
            objective="Learn hobbies",
            vocabulary=[],
            patterns=[],
            evaluation_criteria=[],
        )
        mock_lesson_service.return_value = mock_instance

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.get("/api/lessons/5")

        assert response.status_code == 200
        data = response.json()
        assert data["lesson_number"] == 5
        assert data["title"] == "Hobbies"

    @pytest.mark.asyncio
    async def test_get_lesson_returns_404_for_missing(self, mock_lesson_service):
        """GET /api/lessons/{lesson_number} should return 404 if not found."""
        from app.main import app

        mock_instance = AsyncMock()
        mock_instance.get_lesson_detail.return_value = None
        mock_lesson_service.return_value = mock_instance

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.get("/api/lessons/999")

        assert response.status_code == 404
