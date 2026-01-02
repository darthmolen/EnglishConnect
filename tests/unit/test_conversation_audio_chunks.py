"""Behavior tests for conversation router audio and vocabulary rendering.

These tests verify:
1. Multiple speak() calls return all audio chunks (not just first)
2. Listing vocabulary words should call render_vocabulary for each word
"""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock


class TestMultipleSpeakCalls:
    """Test that multiple speak() calls are collected in audio_chunks."""

    @pytest.mark.asyncio
    async def test_multiple_spanish_speak_calls_return_all_audio_chunks(self, mock_auth):
        """When agent makes 2 Spanish speak() calls, both should be in audio_chunks.

        Scenario: User asks "¿Cuáles son los sustantivos de lección 6 y 7?"
        Agent should speak lesson 6 nouns, then lesson 7 nouns - BOTH should play.
        """
        from app.main import app
        from app.schemas.lesson import LessonDetail
        from httpx import AsyncClient, ASGITransport

        # Mock agent response with 2 Spanish speak() tool results
        mock_agent_result = {
            "text": "Here are the nouns from lessons 6 and 7.",
            "tool_calls": [
                {"name": "speak", "arguments": {"text": "Lesson 6 nouns: cousin, uncle", "language": "es"}},
                {"name": "speak", "arguments": {"text": "Lesson 7 nouns: family, parents", "language": "es"}},
            ],
            "tool_results": [
                {
                    "tool": "speak",
                    "success": True,
                    "result": {
                        "spoken": True,
                        "text": "Los sustantivos de la lección 6 son: cousin, uncle, aunt.",
                        "language": "es",
                        "audio_base64": "AUDIO_CHUNK_1_BASE64_CONTENT",
                        "format": "wav",
                    },
                },
                {
                    "tool": "speak",
                    "success": True,
                    "result": {
                        "spoken": True,
                        "text": "Los sustantivos de la lección 7 son: family, parents, son.",
                        "language": "es",
                        "audio_base64": "AUDIO_CHUNK_2_BASE64_CONTENT",
                        "format": "wav",
                    },
                },
            ],
        }

        with patch("app.routers.conversation.LessonService") as mock_lesson_service:
            with patch("app.routers.conversation.SessionService") as mock_session_service:
                with patch("app.routers.conversation.get_agent_response", return_value=mock_agent_result):
                    mock_lesson_instance = AsyncMock()
                    mock_lesson_instance.get_lesson_detail.return_value = LessonDetail(
                        lesson_number=7,
                        title="Family",
                        objective="Learn family vocabulary",
                        vocabulary=[],
                        patterns=[],
                        evaluation_criteria=[],
                    )
                    mock_lesson_service.return_value = mock_lesson_instance

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
                                "message": "¿Cuáles son los sustantivos de lección 6 y 7?",
                                "lesson_number": 7,
                                "mode": "help",
                            },
                        )

        assert response.status_code == 200
        data = response.json()

        # CRITICAL: audio_chunks should contain BOTH speak() results
        assert "audio_chunks" in data, "Response should include audio_chunks field"
        assert data["audio_chunks"] is not None, "audio_chunks should not be None"
        assert len(data["audio_chunks"]) == 2, f"Expected 2 audio chunks, got {len(data['audio_chunks'])}"

        # Verify each chunk has required fields
        chunk1 = data["audio_chunks"][0]
        chunk2 = data["audio_chunks"][1]

        assert chunk1["audio_base64"] == "AUDIO_CHUNK_1_BASE64_CONTENT"
        assert chunk1["language"] == "es"
        assert "lección 6" in chunk1["text"]

        assert chunk2["audio_base64"] == "AUDIO_CHUNK_2_BASE64_CONTENT"
        assert chunk2["language"] == "es"
        assert "lección 7" in chunk2["text"]

    @pytest.mark.asyncio
    async def test_mixed_language_speak_calls_return_all_audio_chunks(self, mock_auth):
        """When agent makes English then Spanish speak() calls, both should be in audio_chunks.

        Order matters - chunks should be in call order for sequential playback.
        """
        from app.main import app
        from app.schemas.lesson import LessonDetail
        from httpx import AsyncClient, ASGITransport

        # Mock agent response with English then Spanish speak()
        mock_agent_result = {
            "text": "Let me explain in both languages.",
            "tool_calls": [
                {"name": "speak", "arguments": {"text": "The word 'cousin' means...", "language": "en"}},
                {"name": "speak", "arguments": {"text": "Cousin significa primo o prima.", "language": "es"}},
            ],
            "tool_results": [
                {
                    "tool": "speak",
                    "success": True,
                    "result": {
                        "spoken": True,
                        "text": "The word 'cousin' means a child of your aunt or uncle.",
                        "language": "en",
                        "audio_base64": "ENGLISH_AUDIO_CHUNK",
                        "format": "wav",
                    },
                },
                {
                    "tool": "speak",
                    "success": True,
                    "result": {
                        "spoken": True,
                        "text": "Cousin significa primo o prima en español.",
                        "language": "es",
                        "audio_base64": "SPANISH_AUDIO_CHUNK",
                        "format": "wav",
                    },
                },
            ],
        }

        with patch("app.routers.conversation.LessonService") as mock_lesson_service:
            with patch("app.routers.conversation.SessionService") as mock_session_service:
                with patch("app.routers.conversation.get_agent_response", return_value=mock_agent_result):
                    mock_lesson_instance = AsyncMock()
                    mock_lesson_instance.get_lesson_detail.return_value = LessonDetail(
                        lesson_number=6,
                        title="Relatives",
                        vocabulary=[],
                        patterns=[],
                        evaluation_criteria=[],
                    )
                    mock_lesson_service.return_value = mock_lesson_instance

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
                                "message": "What does cousin mean?",
                                "lesson_number": 6,
                                "mode": "help",
                            },
                        )

        assert response.status_code == 200
        data = response.json()

        # Both chunks should be present in order
        assert data.get("audio_chunks") is not None
        assert len(data["audio_chunks"]) == 2

        # Order must be preserved (English first, then Spanish)
        assert data["audio_chunks"][0]["language"] == "en"
        assert data["audio_chunks"][1]["language"] == "es"


class TestRenderVocabularyForWordList:
    """Test that listing vocabulary words calls render_vocabulary for each."""

    @pytest.mark.asyncio
    async def test_listing_nouns_should_call_render_vocabulary(self, mock_auth):
        """When user asks for list of nouns, agent should render_vocabulary for each.

        Scenario: "¿Cuáles son los sustantivos de lección 6?"
        Instead of just speaking the list, agent should render vocabulary cards.
        """
        from app.main import app
        from app.schemas.lesson import LessonDetail
        from httpx import AsyncClient, ASGITransport

        # Mock agent response where agent renders vocabulary cards
        mock_agent_result = {
            "text": "Here are the nouns from lesson 6:",
            "tool_calls": [
                {"name": "render_vocabulary", "arguments": {"english_word": "cousin"}},
                {"name": "render_vocabulary", "arguments": {"english_word": "uncle"}},
                {"name": "render_vocabulary", "arguments": {"english_word": "aunt"}},
            ],
            "tool_results": [
                {
                    "tool": "render_vocabulary",
                    "success": True,
                    "result": {
                        "rich_content": {
                            "type": "vocabulary_card",
                            "data": {
                                "english_word": "cousin",
                                "spanish_translation": "primo/prima",
                                "category": "noun",
                                "lesson_number": 6,
                                "audio_url": "/api/audio/vocab/ec1/lesson-06/cousin.wav",
                            },
                        }
                    },
                },
                {
                    "tool": "render_vocabulary",
                    "success": True,
                    "result": {
                        "rich_content": {
                            "type": "vocabulary_card",
                            "data": {
                                "english_word": "uncle",
                                "spanish_translation": "tío",
                                "category": "noun",
                                "lesson_number": 6,
                                "audio_url": "/api/audio/vocab/ec1/lesson-06/uncle.wav",
                            },
                        }
                    },
                },
                {
                    "tool": "render_vocabulary",
                    "success": True,
                    "result": {
                        "rich_content": {
                            "type": "vocabulary_card",
                            "data": {
                                "english_word": "aunt",
                                "spanish_translation": "tía",
                                "category": "noun",
                                "lesson_number": 6,
                                "audio_url": "/api/audio/vocab/ec1/lesson-06/aunt.wav",
                            },
                        }
                    },
                },
            ],
        }

        with patch("app.routers.conversation.LessonService") as mock_lesson_service:
            with patch("app.routers.conversation.SessionService") as mock_session_service:
                with patch("app.routers.conversation.get_agent_response", return_value=mock_agent_result):
                    mock_lesson_instance = AsyncMock()
                    mock_lesson_instance.get_lesson_detail.return_value = LessonDetail(
                        lesson_number=6,
                        title="Relatives",
                        vocabulary=[],
                        patterns=[],
                        evaluation_criteria=[],
                    )
                    mock_lesson_service.return_value = mock_lesson_instance

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
                                "message": "¿Cuáles son los sustantivos de lección 6?",
                                "lesson_number": 6,
                                "mode": "help",
                            },
                        )

        assert response.status_code == 200
        data = response.json()

        # Should have rich_content with all 3 vocabulary cards
        assert "rich_content" in data
        assert data["rich_content"] is not None
        assert len(data["rich_content"]) == 3, f"Expected 3 vocab cards, got {len(data['rich_content'])}"

        # Verify each card
        words = [card["data"]["english_word"] for card in data["rich_content"]]
        assert "cousin" in words
        assert "uncle" in words
        assert "aunt" in words

        # All cards should be vocabulary_card type
        for card in data["rich_content"]:
            assert card["type"] == "vocabulary_card"
            assert "audio_url" in card["data"]


class TestRenderPatternForPhrases:
    """Test that asking for 'frases' renders pattern cards correctly."""

    @pytest.mark.asyncio
    async def test_frases_request_renders_pattern_cards(self, mock_auth):
        """When user asks for patterns, agent should render pattern cards.

        Scenario: "Dame las frases de lección 6 y 7"
        Agent should render 4 pattern cards (2 per lesson).
        """
        from app.main import app
        from app.schemas.lesson import LessonDetail
        from httpx import AsyncClient, ASGITransport

        # Mock agent response with render_pattern calls
        mock_agent_result = {
            "text": "Aquí están los patrones de las lecciones 6 y 7.",
            "tool_calls": [
                {"name": "speak", "arguments": {"text": "Aquí están los patrones:", "language": "es"}},
                {"name": "render_pattern", "arguments": {"pattern_number": 1, "lesson_number": 6}},
                {"name": "render_pattern", "arguments": {"pattern_number": 2, "lesson_number": 6}},
                {"name": "render_pattern", "arguments": {"pattern_number": 1, "lesson_number": 7}},
                {"name": "render_pattern", "arguments": {"pattern_number": 2, "lesson_number": 7}},
            ],
            "tool_results": [
                {
                    "tool": "speak",
                    "success": True,
                    "result": {
                        "spoken": True,
                        "text": "Aquí están los patrones:",
                        "language": "es",
                        "audio_base64": "AUDIO_INTRO",
                        "format": "wav",
                    },
                },
                {
                    "tool": "render_pattern",
                    "success": True,
                    "result": {
                        "rich_content": {
                            "type": "pattern_card",
                            "data": {
                                "pattern_number": 1,
                                "question_template": "How many (*noun*) are in your family?",
                                "answer_template": "There are (*number*) people in my family.",
                                "lesson_number": 6,
                                "demo_audio_url": "/api/audio/demos/ec1?lesson_number=6",
                            },
                        }
                    },
                },
                {
                    "tool": "render_pattern",
                    "success": True,
                    "result": {
                        "rich_content": {
                            "type": "pattern_card",
                            "data": {
                                "pattern_number": 2,
                                "question_template": "Do you have (*noun*)?",
                                "answer_template": "Yes, I have (*noun*).",
                                "lesson_number": 6,
                                "demo_audio_url": "/api/audio/demos/ec1?lesson_number=6",
                            },
                        }
                    },
                },
                {
                    "tool": "render_pattern",
                    "success": True,
                    "result": {
                        "rich_content": {
                            "type": "pattern_card",
                            "data": {
                                "pattern_number": 1,
                                "question_template": "Tell me about your (*noun*).",
                                "answer_template": "They have (*adjective*) (*noun*).",
                                "lesson_number": 7,
                                "demo_audio_url": "/api/audio/demos/ec1?lesson_number=7",
                            },
                        }
                    },
                },
                {
                    "tool": "render_pattern",
                    "success": True,
                    "result": {
                        "rich_content": {
                            "type": "pattern_card",
                            "data": {
                                "pattern_number": 2,
                                "question_template": "Is your (*noun*) (*adjective*)?",
                                "answer_template": "Yes, he is (*adjective*).",
                                "lesson_number": 7,
                                "demo_audio_url": "/api/audio/demos/ec1?lesson_number=7",
                            },
                        }
                    },
                },
            ],
        }

        with patch("app.routers.conversation.LessonService") as mock_lesson_service:
            with patch("app.routers.conversation.SessionService") as mock_session_service:
                with patch("app.routers.conversation.get_agent_response", return_value=mock_agent_result):
                    mock_lesson_instance = AsyncMock()
                    mock_lesson_instance.get_lesson_detail.return_value = LessonDetail(
                        lesson_number=7,
                        title="Family",
                        vocabulary=[],
                        patterns=[],
                        evaluation_criteria=[],
                    )
                    mock_lesson_service.return_value = mock_lesson_instance

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
                                "message": "Dame las frases de lección 6 y 7",
                                "lesson_number": 7,
                                "mode": "help",
                            },
                        )

        assert response.status_code == 200
        data = response.json()

        # Should have 4 pattern cards (2 per lesson)
        assert "rich_content" in data
        assert data["rich_content"] is not None
        assert len(data["rich_content"]) == 4, f"Expected 4 pattern cards, got {len(data['rich_content'])}"

        # Verify all are pattern_card type
        for card in data["rich_content"]:
            assert card["type"] == "pattern_card"

        # Verify lesson numbers are correct (2 for lesson 6, 2 for lesson 7)
        lesson_numbers = [card["data"]["lesson_number"] for card in data["rich_content"]]
        assert lesson_numbers.count(6) == 2, "Should have 2 cards for lesson 6"
        assert lesson_numbers.count(7) == 2, "Should have 2 cards for lesson 7"

        # Verify pattern numbers (1 and 2 for each lesson)
        lesson_6_patterns = [c["data"]["pattern_number"] for c in data["rich_content"] if c["data"]["lesson_number"] == 6]
        lesson_7_patterns = [c["data"]["pattern_number"] for c in data["rich_content"] if c["data"]["lesson_number"] == 7]
        assert sorted(lesson_6_patterns) == [1, 2]
        assert sorted(lesson_7_patterns) == [1, 2]

    @pytest.mark.asyncio
    async def test_pattern_card_includes_demo_audio_url(self, mock_auth):
        """Pattern cards should include demo_audio_url for playback."""
        from app.main import app
        from app.schemas.lesson import LessonDetail
        from httpx import AsyncClient, ASGITransport

        mock_agent_result = {
            "text": "Here is the pattern.",
            "tool_calls": [
                {"name": "render_pattern", "arguments": {"pattern_number": 1, "lesson_number": 6}},
            ],
            "tool_results": [
                {
                    "tool": "render_pattern",
                    "success": True,
                    "result": {
                        "rich_content": {
                            "type": "pattern_card",
                            "data": {
                                "pattern_number": 1,
                                "question_template": "How many (*noun*)?",
                                "answer_template": "There are (*number*).",
                                "lesson_number": 6,
                                "demo_audio_url": "/api/audio/demos/ec1?lesson_number=6",
                            },
                        }
                    },
                },
            ],
        }

        with patch("app.routers.conversation.LessonService") as mock_lesson_service:
            with patch("app.routers.conversation.SessionService") as mock_session_service:
                with patch("app.routers.conversation.get_agent_response", return_value=mock_agent_result):
                    mock_lesson_instance = AsyncMock()
                    mock_lesson_instance.get_lesson_detail.return_value = LessonDetail(
                        lesson_number=7,
                        title="Family",
                        vocabulary=[],
                        patterns=[],
                        evaluation_criteria=[],
                    )
                    mock_lesson_service.return_value = mock_lesson_instance

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
                                "message": "Show me pattern 1",
                                "lesson_number": 7,
                                "mode": "help",
                            },
                        )

        assert response.status_code == 200
        data = response.json()

        assert data["rich_content"] is not None
        card = data["rich_content"][0]
        assert "demo_audio_url" in card["data"]
        assert card["data"]["demo_audio_url"] == "/api/audio/demos/ec1?lesson_number=6"
