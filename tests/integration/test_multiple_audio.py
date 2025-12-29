"""Integration tests for multiple audio chunk handling.

These tests verify that when the agent calls speak() multiple times,
ALL audio chunks are returned to the frontend (not just the last one).

Currently FAILING because:
1. Backend loop overwrites audio_base64 instead of accumulating
2. Response schema only supports single audio, not array of chunks
"""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from httpx import AsyncClient, ASGITransport
from uuid import uuid4

from app.main import app
from app.schemas.lesson_session import LessonConversationResponse


class TestMultipleAudioIntegration:
    """Test that multiple speak() calls return multiple audio chunks."""

    @pytest.fixture
    def mock_user(self):
        """Create a mock authenticated user."""
        user = MagicMock()
        user.id = uuid4()
        user.email = "test@example.com"
        return user

    @pytest.mark.asyncio
    async def test_response_schema_supports_audio_chunks(self):
        """LessonConversationResponse should support audio_chunks array.

        This test will FAIL until we add audio_chunks field to the schema.
        """
        # Create response with audio_chunks (currently will fail)
        response = LessonConversationResponse(
            text="Hello in both languages",
            lesson_number=7,
            phase=MagicMock(id=1, phase_type="intro", phase_name="Introduction", sort_order=0),
            phase_state=MagicMock(vocab_index=0, pattern_index=0, items_completed=[], can_skip_ahead=False),
            audio_chunks=[  # NEW FIELD - currently will fail
                {
                    "audio_base64": "SPANISH_AUDIO",
                    "format": "wav",
                    "language": "es",
                    "text": "¡Hola! El patrón es...",
                },
                {
                    "audio_base64": "ENGLISH_AUDIO",
                    "format": "wav",
                    "language": "en",
                    "text": "Hello! The pattern is...",
                },
            ],
        )

        assert response.audio_chunks is not None
        assert len(response.audio_chunks) == 2

    @pytest.mark.asyncio
    async def test_two_speak_calls_return_two_audio_chunks(self, mock_user):
        """When agent calls speak() twice, response should have 2 audio chunks.

        This test simulates a bilingual response where the agent speaks
        in Spanish first, then English. Both audio files should be returned.

        Currently FAILS because backend overwrites instead of accumulates.
        """
        call_count = 0

        async def mock_get_agent_response(
            system_prompt, user_message, history, tool_handlers, user_id, tools
        ):
            nonlocal call_count

            # Agent calls speak() twice - Spanish first, then English
            spanish_result = await tool_handlers["speak"](
                text="¡Hola! El patrón uno es: Cuéntame sobre tu...",
                language="es",
                voice="speaker_b",
            )

            english_result = await tool_handlers["speak"](
                text="Hello! Pattern one is: Tell me about your...",
                language="en",
                voice="speaker_b",
            )

            return {
                "text": "Hello! Pattern one is: Tell me about your...",
                "tool_calls": [
                    {"name": "speak", "arguments": {"text": "¡Hola!...", "language": "es"}},
                    {"name": "speak", "arguments": {"text": "Hello!...", "language": "en"}},
                ],
                "tool_results": [
                    {
                        "tool": "speak",
                        "success": True,
                        "result": {
                            "spoken": True,
                            "text": "¡Hola! El patrón uno es: Cuéntame sobre tu...",
                            "language": "es",
                            "audio_base64": "SPANISH_AUDIO_BASE64_DATA",
                            "format": "wav",
                        }
                    },
                    {
                        "tool": "speak",
                        "success": True,
                        "result": {
                            "spoken": True,
                            "text": "Hello! Pattern one is: Tell me about your...",
                            "language": "en",
                            "audio_base64": "ENGLISH_AUDIO_BASE64_DATA",
                            "format": "wav",
                        }
                    },
                ],
            }

        async def mock_speak_tool_handler(text, language, voice="speaker_b"):
            # Return different audio based on language
            if language == "es":
                return {
                    "spoken": True,
                    "text": text,
                    "language": "es",
                    "audio_base64": "SPANISH_AUDIO_BASE64_DATA",
                    "format": "wav",
                }
            else:
                return {
                    "spoken": True,
                    "text": text,
                    "language": "en",
                    "audio_base64": "ENGLISH_AUDIO_BASE64_DATA",
                    "format": "wav",
                }

        with patch("app.routers.lesson.get_agent_response", mock_get_agent_response), \
             patch("app.routers.lesson.speak_tool_handler", mock_speak_tool_handler), \
             patch("app.routers.lesson.get_settings") as mock_settings:

            mock_settings.return_value.azure_openai_endpoint = "https://test.openai.azure.com"
            mock_settings.return_value.azure_openai_api_key = "test-key"

            async with AsyncClient(
                transport=ASGITransport(app=app),
                base_url="http://test"
            ) as client:
                response = await client.post(
                    "/api/lesson/conversation",
                    json={
                        "message": "Dígame patrón 1 en español e inglés",
                        "lesson_number": 7,
                        "history": [],
                    },
                    headers={"Authorization": "Bearer test-token"},
                )

        # This will FAIL until we implement audio_chunks accumulation
        response_data = response.json()

        # Should have audio_chunks array with BOTH audio files
        assert "audio_chunks" in response_data, \
            f"Response should have audio_chunks array. Got keys: {response_data.keys()}"

        assert response_data["audio_chunks"] is not None, \
            "audio_chunks should not be None"

        assert len(response_data["audio_chunks"]) >= 2, \
            f"Should have at least 2 audio chunks (Spanish + English). Got: {len(response_data.get('audio_chunks', []))}"

        # Verify we have both languages
        languages = [chunk["language"] for chunk in response_data["audio_chunks"]]
        assert "es" in languages, "Should have Spanish audio chunk"
        assert "en" in languages, "Should have English audio chunk"

        # Verify audio data is different for each chunk
        audio_data = [chunk["audio_base64"] for chunk in response_data["audio_chunks"]]
        assert audio_data[0] != audio_data[1], \
            "Spanish and English audio should be different files"

    @pytest.mark.asyncio
    async def test_single_speak_call_still_works(self, mock_user):
        """When agent calls speak() once, should still work (backward compat).

        This test ensures we don't break single-audio responses.
        """
        async def mock_get_agent_response(
            system_prompt, user_message, history, tool_handlers, user_id, tools
        ):
            await tool_handlers["speak"](
                text="Hello!",
                language="en",
                voice="speaker_b",
            )

            return {
                "text": "Hello!",
                "tool_calls": [{"name": "speak", "arguments": {}}],
                "tool_results": [{
                    "tool": "speak",
                    "success": True,
                    "result": {
                        "spoken": True,
                        "text": "Hello!",
                        "language": "en",
                        "audio_base64": "SINGLE_AUDIO_BASE64",
                        "format": "wav",
                    }
                }],
            }

        async def mock_speak_tool_handler(text, language, voice="speaker_b"):
            return {
                "spoken": True,
                "text": text,
                "language": language,
                "audio_base64": "SINGLE_AUDIO_BASE64",
                "format": "wav",
            }

        with patch("app.routers.lesson.get_agent_response", mock_get_agent_response), \
             patch("app.routers.lesson.speak_tool_handler", mock_speak_tool_handler), \
             patch("app.routers.lesson.get_settings") as mock_settings:

            mock_settings.return_value.azure_openai_endpoint = "https://test.openai.azure.com"
            mock_settings.return_value.azure_openai_api_key = "test-key"

            async with AsyncClient(
                transport=ASGITransport(app=app),
                base_url="http://test"
            ) as client:
                response = await client.post(
                    "/api/lesson/conversation",
                    json={
                        "message": "Hello",
                        "lesson_number": 7,
                        "history": [],
                    },
                    headers={"Authorization": "Bearer test-token"},
                )

        response_data = response.json()

        # Should have at least one audio chunk (or backward-compat audio_base64)
        has_audio = (
            ("audio_chunks" in response_data and len(response_data["audio_chunks"]) >= 1) or
            ("audio_base64" in response_data and response_data["audio_base64"])
        )

        assert has_audio, "Should have audio in response (either audio_chunks or audio_base64)"

    @pytest.mark.asyncio
    async def test_audio_chunks_preserve_order(self, mock_user):
        """Audio chunks should be returned in the order speak() was called.

        When agent speaks Spanish first, then English, chunks should be
        in that order so frontend plays them sequentially.
        """
        async def mock_get_agent_response(
            system_prompt, user_message, history, tool_handlers, user_id, tools
        ):
            # Order matters: Spanish FIRST, then English
            await tool_handlers["speak"](
                text="Primero en español",
                language="es",
                voice="speaker_b",
            )
            await tool_handlers["speak"](
                text="Second in English",
                language="en",
                voice="speaker_b",
            )

            return {
                "text": "Second in English",
                "tool_calls": [],
                "tool_results": [
                    {
                        "tool": "speak",
                        "success": True,
                        "result": {
                            "spoken": True,
                            "text": "Primero en español",
                            "language": "es",
                            "audio_base64": "SPANISH_FIRST",
                            "format": "wav",
                        }
                    },
                    {
                        "tool": "speak",
                        "success": True,
                        "result": {
                            "spoken": True,
                            "text": "Second in English",
                            "language": "en",
                            "audio_base64": "ENGLISH_SECOND",
                            "format": "wav",
                        }
                    },
                ],
            }

        async def mock_speak_tool_handler(text, language, voice="speaker_b"):
            return {
                "spoken": True,
                "text": text,
                "language": language,
                "audio_base64": f"{language.upper()}_AUDIO",
                "format": "wav",
            }

        with patch("app.routers.lesson.get_agent_response", mock_get_agent_response), \
             patch("app.routers.lesson.speak_tool_handler", mock_speak_tool_handler), \
             patch("app.routers.lesson.get_settings") as mock_settings:

            mock_settings.return_value.azure_openai_endpoint = "https://test.openai.azure.com"
            mock_settings.return_value.azure_openai_api_key = "test-key"

            async with AsyncClient(
                transport=ASGITransport(app=app),
                base_url="http://test"
            ) as client:
                response = await client.post(
                    "/api/lesson/conversation",
                    json={
                        "message": "Say something in both languages",
                        "lesson_number": 7,
                        "history": [],
                    },
                    headers={"Authorization": "Bearer test-token"},
                )

        response_data = response.json()

        # Should preserve order
        assert "audio_chunks" in response_data
        chunks = response_data["audio_chunks"]

        # First chunk should be Spanish (called first)
        assert chunks[0]["language"] == "es", \
            f"First chunk should be Spanish (called first). Got: {chunks[0]['language']}"

        # Second chunk should be English (called second)
        assert chunks[1]["language"] == "en", \
            f"Second chunk should be English (called second). Got: {chunks[1]['language']}"
