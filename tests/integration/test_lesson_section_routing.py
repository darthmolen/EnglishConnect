"""Integration tests for lesson section routing.

These tests verify that when a section parameter is sent,
the backend uses the correct phase for the system prompt.

Currently FAILING because:
1. LessonConversationRequest doesn't accept 'section' parameter
2. lesson.py router doesn't use section to determine phase
"""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from httpx import AsyncClient, ASGITransport
from uuid import uuid4

from app.main import app
from app.schemas.lesson_session import LessonConversationRequest


class TestSectionRoutingIntegration:
    """Test that section parameter routes to correct phase."""

    @pytest.fixture
    def mock_user(self):
        """Create a mock authenticated user."""
        user = MagicMock()
        user.id = uuid4()
        user.email = "test@example.com"
        return user

    @pytest.fixture
    def mock_db_session(self):
        """Create a mock database session."""
        session = AsyncMock()
        return session

    @pytest.mark.asyncio
    async def test_request_schema_accepts_section_parameter(self):
        """LessonConversationRequest should accept optional section field.

        This test will FAIL until we add the section field to the schema.
        """
        # This should NOT raise a validation error
        request = LessonConversationRequest(
            message="Tell me pattern 1",
            lesson_number=7,
            section="patterns",  # NEW FIELD - currently will fail
            history=[],
        )

        assert request.section == "patterns"

    @pytest.mark.asyncio
    async def test_patterns_section_uses_patterns_phase_prompt(
        self, mock_user, mock_db_session
    ):
        """When section='patterns', system prompt should include actual patterns.

        This test verifies that:
        1. The section parameter is sent to the backend
        2. The backend uses it to determine the phase
        3. The system prompt includes pattern content

        Currently FAILS because section is ignored.
        """
        captured_system_prompt = None

        async def mock_get_agent_response(
            system_prompt, user_message, history, tool_handlers, user_id, tools
        ):
            nonlocal captured_system_prompt
            captured_system_prompt = system_prompt

            # Simulate agent calling speak() once
            await tool_handlers["speak"](
                text="Pattern 1 is: Tell me about your noun",
                language="en",
                voice="speaker_b",
            )

            return {
                "text": "Pattern 1 is: Tell me about your noun",
                "tool_calls": [{"name": "speak", "arguments": {}}],
                "tool_results": [{
                    "tool": "speak",
                    "success": True,
                    "result": {
                        "spoken": True,
                        "text": "Pattern 1 is: Tell me about your noun",
                        "language": "en",
                        "audio_base64": "MOCK_AUDIO",
                        "format": "wav",
                    }
                }],
            }

        # Mock the TTS service
        async def mock_speak_tool_handler(text, language, voice="speaker_b"):
            return {
                "spoken": True,
                "text": text,
                "language": language,
                "audio_base64": "MOCK_AUDIO_BASE64",
                "format": "wav",
            }

        with patch("app.routers.lesson.get_agent_response", mock_get_agent_response), \
             patch("app.routers.lesson.speak_tool_handler", mock_speak_tool_handler), \
             patch("app.routers.lesson.get_settings") as mock_settings:

            # Configure Azure OpenAI settings
            mock_settings.return_value.azure_openai_endpoint = "https://test.openai.azure.com"
            mock_settings.return_value.azure_openai_api_key = "test-key"

            # Make request with section parameter
            async with AsyncClient(
                transport=ASGITransport(app=app),
                base_url="http://test"
            ) as client:
                response = await client.post(
                    "/api/lesson/conversation",
                    json={
                        "message": "Tell me pattern 1",
                        "lesson_number": 7,
                        "section": "patterns",  # This should route to patterns phase
                        "history": [],
                    },
                    headers={"Authorization": "Bearer test-token"},
                )

        # The test should fail until we implement section routing
        # When fixed, the system prompt should contain pattern-specific content
        assert captured_system_prompt is not None, "Agent should have been called"

        # These assertions verify the system prompt is for PATTERNS phase, not INTRO
        assert "Pattern 1 of" in captured_system_prompt or "Current Focus: Q&A Pattern" in captured_system_prompt, \
            f"System prompt should be for patterns phase, got intro phase instead. Prompt starts with: {captured_system_prompt[:200]}"

        # Lesson 7 Pattern 1 is "Tell me about your (noun)"
        assert "Tell me about your" in captured_system_prompt, \
            f"System prompt should include actual Lesson 7 Pattern 1. Got: {captured_system_prompt[:500]}"

    @pytest.mark.asyncio
    async def test_vocabulary_section_uses_vocabulary_phase_prompt(
        self, mock_user, mock_db_session
    ):
        """When section='vocabulary', system prompt should include vocabulary content.

        Currently FAILS because section is ignored.
        """
        captured_system_prompt = None

        async def mock_get_agent_response(
            system_prompt, user_message, history, tool_handlers, user_id, tools
        ):
            nonlocal captured_system_prompt
            captured_system_prompt = system_prompt

            await tool_handlers["speak"](
                text="The word is: mother",
                language="en",
                voice="speaker_b",
            )

            return {
                "text": "The word is: mother",
                "tool_calls": [],
                "tool_results": [{
                    "tool": "speak",
                    "success": True,
                    "result": {
                        "spoken": True,
                        "text": "The word is: mother",
                        "language": "en",
                        "audio_base64": "MOCK_AUDIO",
                        "format": "wav",
                    }
                }],
            }

        async def mock_speak_tool_handler(text, language, voice="speaker_b"):
            return {
                "spoken": True,
                "text": text,
                "language": language,
                "audio_base64": "MOCK_AUDIO_BASE64",
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
                        "message": "What vocabulary words are we learning?",
                        "lesson_number": 7,
                        "section": "vocabulary",  # Should route to vocabulary phase
                        "history": [],
                    },
                    headers={"Authorization": "Bearer test-token"},
                )

        assert captured_system_prompt is not None

        # Vocabulary phase prompt should include vocab-specific content
        assert "Vocabulary Phase" in captured_system_prompt or "Word 1 of" in captured_system_prompt, \
            f"System prompt should be for vocabulary phase. Got: {captured_system_prompt[:300]}"

    @pytest.mark.asyncio
    async def test_no_section_defaults_to_user_progress_phase(self):
        """When section is not provided, should use user's saved progress phase.

        This is the current behavior and should continue to work.
        """
        # This test documents current (correct) behavior for backward compatibility
        request = LessonConversationRequest(
            message="Hello",
            lesson_number=7,
            history=[],
        )

        # Should work without section (backward compatible)
        assert request.message == "Hello"
        assert request.lesson_number == 7
        # section should default to None
        assert not hasattr(request, 'section') or getattr(request, 'section', None) is None
