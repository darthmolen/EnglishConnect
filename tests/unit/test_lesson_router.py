"""Unit tests for lesson router endpoints."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

from httpx import AsyncClient, ASGITransport

from app.main import app
from app.schemas.lesson import LessonDetail, VocabularyItemSchema, QAPatternSchema


@pytest.fixture
def sample_lesson_detail():
    """Create a sample lesson detail."""
    return LessonDetail(
        lesson_number=5,
        title="Hobbies and Interests",
        objective="Learn to talk about hobbies",
        vocabulary=[
            VocabularyItemSchema(english="exercise", spanish="hacer ejercicio"),
            VocabularyItemSchema(english="sing", spanish="cantar"),
        ],
        patterns=[
            QAPatternSchema(
                pattern_number=1,
                question_template="What do you like to do?",
                answer_template="I like to [activity].",
            )
        ],
        evaluation_criteria=["I can say what I like to do."],
    )


@pytest.fixture
def mock_lesson_phase():
    """Create a mock lesson phase."""
    phase = MagicMock()
    phase.id = 1
    phase.phase_type = "intro"
    phase.phase_name = "Introduction"
    phase.sort_order = 0
    phase.lesson_id = 1
    return phase


@pytest.fixture
def mock_lesson_model():
    """Create a mock Lesson model."""
    lesson = MagicMock()
    lesson.id = 1
    lesson.course_id = "ec1"
    lesson.lesson_number = 5
    lesson.title = "Hobbies and Interests"
    return lesson


@pytest.fixture
def mock_user_progress(mock_lesson_phase):
    """Create a mock UserProgress."""
    progress = MagicMock()
    progress.id = 1
    progress.user_id = uuid4()
    progress.lesson_id = 1
    progress.phase_id = 1
    progress.phase_state = {"vocab_index": 0, "pattern_index": 0, "items_completed": [], "can_skip_ahead": False}
    progress.status = "in_progress"
    progress.current_phase = mock_lesson_phase
    return progress


class TestLessonRouter:
    """Test lesson router endpoints."""

    @pytest.mark.asyncio
    async def test_lesson_conversation_requires_auth(self):
        """POST /api/lesson/conversation should require authentication."""
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            response = await client.post(
                "/api/lesson/conversation",
                json={
                    "message": "Hello",
                    "lesson_number": 5,
                    "history": [],
                },
            )

        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_lesson_conversation_lesson_not_found(
        self, mock_auth, mock_user
    ):
        """Should return 404 if lesson not found."""
        with patch(
            "app.routers.lesson.LessonService"
        ) as MockLessonService:
            mock_service = MockLessonService.return_value
            mock_service.get_lesson_detail = AsyncMock(return_value=None)

            async with AsyncClient(
                transport=ASGITransport(app=app),
                base_url="http://test",
            ) as client:
                response = await client.post(
                    "/api/lesson/conversation",
                    json={
                        "message": "Hello",
                        "lesson_number": 999,
                        "history": [],
                    },
                )

        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_lesson_conversation_no_azure_fallback(
        self,
        mock_auth,
        mock_user,
        sample_lesson_detail,
        mock_lesson_model,
        mock_user_progress,
    ):
        """Should return fallback response when Azure OpenAI not configured."""
        with (
            patch("app.routers.lesson.LessonService") as MockLessonService,
            patch("app.routers.lesson.get_settings") as mock_settings,
            patch("app.routers.lesson.LessonProgressService") as MockProgressService,
        ):
            # Setup mocks
            mock_service = MockLessonService.return_value
            mock_service.get_lesson_detail = AsyncMock(
                return_value=sample_lesson_detail
            )

            # Mock db execute for lesson model lookup
            with patch("app.routers.lesson.get_db") as mock_get_db:
                mock_db = AsyncMock()
                mock_result = MagicMock()
                mock_result.scalar_one_or_none.return_value = mock_lesson_model
                mock_db.execute = AsyncMock(return_value=mock_result)

                async def get_db_override():
                    yield mock_db

                app.dependency_overrides[
                    __import__("app.database", fromlist=["get_db"]).get_db
                ] = get_db_override

                # Progress service mock
                mock_progress_service = MockProgressService.return_value
                mock_progress_service.get_or_create_progress = AsyncMock(
                    return_value=(mock_user_progress, False)
                )

                # No Azure OpenAI configured
                settings = MagicMock()
                settings.azure_openai_endpoint = None
                settings.azure_openai_api_key = None
                mock_settings.return_value = settings

                try:
                    async with AsyncClient(
                        transport=ASGITransport(app=app),
                        base_url="http://test",
                    ) as client:
                        response = await client.post(
                            "/api/lesson/conversation",
                            json={
                                "message": "Hello",
                                "lesson_number": 5,
                                "history": [],
                            },
                        )

                    assert response.status_code == 200
                    data = response.json()
                    assert "Azure OpenAI not configured" in data["text"]
                    assert data["lesson_number"] == 5
                finally:
                    # Cleanup
                    from app.database import get_db
                    app.dependency_overrides.pop(get_db, None)

    @pytest.mark.asyncio
    async def test_lesson_conversation_returns_phase_info(
        self,
        mock_auth,
        mock_user,
        sample_lesson_detail,
        mock_lesson_model,
        mock_user_progress,
        mock_lesson_phase,
    ):
        """Response should include phase information."""
        with (
            patch("app.routers.lesson.LessonService") as MockLessonService,
            patch("app.routers.lesson.get_settings") as mock_settings,
            patch("app.routers.lesson.LessonProgressService") as MockProgressService,
            patch("app.routers.lesson.get_agent_response") as mock_agent,
        ):
            mock_service = MockLessonService.return_value
            mock_service.get_lesson_detail = AsyncMock(
                return_value=sample_lesson_detail
            )

            with patch("app.routers.lesson.get_db"):
                mock_db = AsyncMock()
                mock_result = MagicMock()
                mock_result.scalar_one_or_none.return_value = mock_lesson_model
                mock_db.execute = AsyncMock(return_value=mock_result)
                mock_db.commit = AsyncMock()

                from app.database import get_db

                async def get_db_override():
                    yield mock_db

                app.dependency_overrides[get_db] = get_db_override

                mock_progress_service = MockProgressService.return_value
                mock_progress_service.get_or_create_progress = AsyncMock(
                    return_value=(mock_user_progress, False)
                )

                # Azure configured
                settings = MagicMock()
                settings.azure_openai_endpoint = "https://test.openai.azure.com"
                settings.azure_openai_api_key = "test-key"
                mock_settings.return_value = settings

                # Mock agent response
                mock_agent.return_value = {
                    "text": "Welcome to the lesson!",
                    "tool_calls": [],
                    "tool_results": [],
                }

                try:
                    async with AsyncClient(
                        transport=ASGITransport(app=app),
                        base_url="http://test",
                    ) as client:
                        response = await client.post(
                            "/api/lesson/conversation",
                            json={
                                "message": "Hello",
                                "lesson_number": 5,
                                "history": [],
                            },
                        )

                    assert response.status_code == 200
                    data = response.json()

                    # Check phase info is included
                    assert "phase" in data
                    assert data["phase"]["phase_type"] == "intro"
                    assert "phase_state" in data
                finally:
                    app.dependency_overrides.pop(get_db, None)


class TestLessonRouterPhaseAdvancement:
    """Test phase advancement via tool calls."""

    @pytest.mark.asyncio
    async def test_advance_phase_tool_updates_state(
        self,
        mock_auth,
        mock_user,
        sample_lesson_detail,
        mock_lesson_model,
        mock_user_progress,
    ):
        """Agent calling advance_phase should update user progress."""
        with (
            patch("app.routers.lesson.LessonService") as MockLessonService,
            patch("app.routers.lesson.get_settings") as mock_settings,
            patch("app.routers.lesson.LessonProgressService") as MockProgressService,
            patch("app.routers.lesson.get_agent_response") as mock_agent,
        ):
            mock_service = MockLessonService.return_value
            mock_service.get_lesson_detail = AsyncMock(
                return_value=sample_lesson_detail
            )

            mock_db = AsyncMock()
            mock_result = MagicMock()
            mock_result.scalar_one_or_none.return_value = mock_lesson_model
            mock_db.execute = AsyncMock(return_value=mock_result)
            mock_db.commit = AsyncMock()
            mock_db.flush = AsyncMock()

            from app.database import get_db

            async def get_db_override():
                yield mock_db

            app.dependency_overrides[get_db] = get_db_override

            # Create phases list for advance_phase logic
            phases = []
            for i, (ptype, pname) in enumerate([
                ("intro", "Introduction"),
                ("vocabulary", "Vocabulary"),
            ]):
                p = MagicMock()
                p.id = i + 1
                p.phase_type = ptype
                p.phase_name = pname
                phases.append(p)

            mock_progress_service = MockProgressService.return_value
            mock_progress_service.get_or_create_progress = AsyncMock(
                return_value=(mock_user_progress, False)
            )
            mock_progress_service.get_lesson_phases = AsyncMock(return_value=phases)
            mock_progress_service.get_user_progress = AsyncMock(
                return_value=mock_user_progress
            )

            settings = MagicMock()
            settings.azure_openai_endpoint = "https://test.openai.azure.com"
            settings.azure_openai_api_key = "test-key"
            mock_settings.return_value = settings

            # Mock agent calling advance_phase tool
            mock_agent.return_value = {
                "text": "Great! Let's move on to vocabulary.",
                "tool_calls": [
                    {"name": "advance_phase", "arguments": {"reason": "intro complete"}}
                ],
                "tool_results": [
                    {"tool": "advance_phase", "success": True, "result": {"action": "next_phase"}}
                ],
            }

            try:
                async with AsyncClient(
                    transport=ASGITransport(app=app),
                    base_url="http://test",
                ) as client:
                    response = await client.post(
                        "/api/lesson/conversation",
                        json={
                            "message": "I'm ready!",
                            "lesson_number": 5,
                            "history": [],
                        },
                    )

                assert response.status_code == 200
            finally:
                app.dependency_overrides.pop(get_db, None)
