"""Integration tests for Memori with the conversation flow."""

import pytest
from unittest.mock import MagicMock, patch, AsyncMock
import uuid


class TestMemoriConversationIntegration:
    """Integration tests for Memori in the conversation flow.

    These tests verify that:
    1. Authenticated user_id flows from auth middleware to Memori
    2. Memory context is set correctly before LLM calls
    3. The full conversation pipeline works with Memori enabled
    """

    @pytest.fixture
    def mock_user(self):
        """Create a mock authenticated user."""
        user = MagicMock()
        user.id = uuid.uuid4()
        user.email = "test@example.com"
        user.display_name = "Test User"
        return user

    @pytest.fixture
    def mock_lesson(self):
        """Create a mock lesson."""
        lesson = MagicMock()
        lesson.id = 1
        lesson.number = 1
        lesson.title = "Greetings"
        lesson.vocabulary = ["hello", "goodbye"]
        lesson.patterns = ["Hello, my name is..."]
        return lesson

    @pytest.mark.asyncio
    @patch("app.routers.conversation.get_agent_response")
    @patch("app.routers.conversation.SessionService")
    @patch("app.routers.conversation.LessonService")
    @patch("app.routers.conversation.ConversationAgentFactory")
    @patch("app.routers.conversation.get_settings")
    async def test_conversation_passes_user_id_to_agent(
        self,
        mock_settings,
        mock_agent_factory,
        mock_lesson_service,
        mock_session_service,
        mock_agent_response,
        mock_user,
        mock_lesson,
    ):
        """Conversation endpoint passes authenticated user_id to get_agent_response()."""
        from app.routers.conversation import conversation
        from app.schemas.conversation import ConversationRequest

        # Setup mocks
        settings = MagicMock()
        settings.azure_openai_endpoint = "https://test.openai.azure.com/"
        settings.azure_openai_api_key = "test-key"
        mock_settings.return_value = settings

        lesson_service = AsyncMock()
        lesson_service.get_lesson_detail = AsyncMock(return_value=mock_lesson)
        mock_lesson_service.return_value = lesson_service

        # Mock the agent factory to return a simple system prompt
        mock_agent_factory.build_system_prompt.return_value = "You are an English tutor."

        session_service = AsyncMock()
        session_service.get_or_create_session = AsyncMock(return_value=MagicMock(id=uuid.uuid4()))
        session_service.record_exchange = AsyncMock()
        mock_session_service.return_value = session_service

        mock_agent_response.return_value = {
            "text": "Hello! Nice to meet you.",
            "tool_calls": [],
            "tool_results": [],
        }

        mock_db = AsyncMock()

        # Create request
        request = ConversationRequest(
            message="Hello!",
            lesson_number=1,
            history=[],
        )

        # Call conversation endpoint
        await conversation(request=request, current_user=mock_user, db=mock_db)

        # Verify get_agent_response was called with user_id
        mock_agent_response.assert_called_once()
        call_kwargs = mock_agent_response.call_args.kwargs
        assert call_kwargs["user_id"] == str(mock_user.id)

    @pytest.mark.asyncio
    async def test_memory_context_set_with_correct_user_id(self):
        """Memory context is set with the correct user_id before LLM calls."""
        import app.services.azure_openai as ao

        # Reset global state
        ao._memori = None
        ao._memori_enabled = False

        mock_memori = MagicMock()

        with patch("app.services.memory_service.get_memori", return_value=mock_memori):
            from app.services.azure_openai import _init_memori, set_memory_context

            # Initialize Memori
            _init_memori()

            # Set context
            user_id = "user-uuid-12345"
            set_memory_context(user_id=user_id, process_id="conversation-agent")

            # Verify attribution was called with correct user_id
            mock_memori.attribution.assert_called_with(
                entity_id=user_id,
                process_id="conversation-agent"
            )

    @pytest.mark.asyncio
    async def test_different_users_get_different_memory_contexts(self):
        """Different users get isolated memory contexts."""
        import app.services.azure_openai as ao

        # Reset global state
        ao._memori = None
        ao._memori_enabled = False

        mock_memori = MagicMock()

        with patch("app.services.memory_service.get_memori", return_value=mock_memori):
            from app.services.azure_openai import _init_memori, set_memory_context

            # Initialize Memori
            _init_memori()

            # Simulate User A's request
            set_memory_context(user_id="user-a-uuid", process_id="conversation-agent")

            # Simulate User B's request
            set_memory_context(user_id="user-b-uuid", process_id="conversation-agent")

            # Verify both users had attribution set
            calls = mock_memori.attribution.call_args_list
            assert len(calls) == 2
            assert calls[0].kwargs == {"entity_id": "user-a-uuid", "process_id": "conversation-agent"}
            assert calls[1].kwargs == {"entity_id": "user-b-uuid", "process_id": "conversation-agent"}


class TestMemoriGracefulDegradation:
    """Tests for graceful degradation when Memori is unavailable."""

    def setup_method(self):
        """Reset global state before each test."""
        import app.services.azure_openai as ao
        ao._memori = None
        ao._memori_enabled = False

    @pytest.mark.asyncio
    @patch("app.services.azure_openai.get_azure_client")
    @patch("app.services.azure_openai.get_settings")
    async def test_agent_works_without_memori(self, mock_settings, mock_client):
        """Agent works normally when Memori is unavailable."""
        from app.services.azure_openai import get_agent_response

        # Setup settings
        settings = MagicMock()
        settings.azure_openai_deployment = "gpt-4o-mini"
        mock_settings.return_value = settings

        # Setup client
        client = AsyncMock()
        response = MagicMock()
        message = MagicMock()
        message.content = "Hello! I'm your English tutor."
        message.tool_calls = None
        response.choices = [MagicMock(message=message)]
        client.chat.completions.create = AsyncMock(return_value=response)
        mock_client.return_value = client

        # Mock Memori to raise an exception (simulating it being unavailable)
        with patch("app.services.memory_service.get_memori", side_effect=Exception("Memori unavailable")):
            # Call should still work
            result = await get_agent_response(
                system_prompt="You are a tutor",
                user_message="Hello",
                history=[],
                tool_handlers={},
                user_id="test-user",
            )

            assert result["text"] == "Hello! I'm your English tutor."

    @pytest.mark.asyncio
    async def test_set_memory_context_silent_when_disabled(self):
        """set_memory_context() is silent when Memori is disabled."""
        from app.services.azure_openai import set_memory_context

        # Mock _init_memori to return False (Memori disabled)
        with patch("app.services.azure_openai._init_memori", return_value=False):
            # Should not raise
            set_memory_context(user_id="user-123")


class TestMemoriUserIsolation:
    """Tests verifying user memory isolation."""

    @patch("app.services.memory_service.get_memori")
    def test_get_user_memories_uses_correct_user_id(self, mock_get_memori):
        """get_user_memories() queries memories for the correct user."""
        from app.services.memory_service import get_user_memories

        mock_memori = MagicMock()
        mock_memori.memory.search.return_value = [{"content": "test memory"}]
        mock_get_memori.return_value = mock_memori

        result = get_user_memories(user_id="user-specific-id", limit=5)

        # Verify attribution was set for this user
        mock_memori.attribution.assert_called_once_with(
            entity_id="user-specific-id",
            process_id="memory-retrieval"
        )

        assert len(result) == 1

    @patch("app.services.memory_service.get_memori")
    def test_clear_user_memories_clears_correct_user(self, mock_get_memori):
        """clear_user_memories() clears memories for the correct user."""
        from app.services.memory_service import clear_user_memories

        mock_memori = MagicMock()
        mock_get_memori.return_value = mock_memori

        clear_user_memories(user_id="user-to-clear")

        # Verify attribution was set for this user
        mock_memori.attribution.assert_called_once_with(
            entity_id="user-to-clear",
            process_id="memory-management"
        )

        mock_memori.memory.clear.assert_called_once()
