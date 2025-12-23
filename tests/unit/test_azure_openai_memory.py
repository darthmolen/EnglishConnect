"""Unit tests for azure_openai.py - Memori integration functions."""

import pytest
from unittest.mock import MagicMock, patch, AsyncMock


class TestInitMemori:
    """Tests for _init_memori() lazy initialization."""

    def setup_method(self):
        """Reset global state before each test."""
        import app.services.azure_openai as ao
        ao._memori = None
        ao._memori_enabled = False

    @patch("app.services.memory_service.get_memori")
    def test_init_memori_enables_global_interception(self, mock_get_memori):
        """_init_memori() calls enable() on the Memori instance."""
        from app.services.azure_openai import _init_memori

        mock_memori = MagicMock()
        mock_get_memori.return_value = mock_memori

        result = _init_memori()

        mock_get_memori.assert_called_once()
        mock_memori.enable.assert_called_once()
        assert result is True

    @patch("app.services.memory_service.get_memori")
    def test_init_memori_handles_import_error(self, mock_get_memori):
        """_init_memori() returns False when Memori import fails."""
        from app.services.azure_openai import _init_memori

        mock_get_memori.side_effect = ImportError("memori not installed")

        result = _init_memori()

        assert result is False

    @patch("app.services.memory_service.get_memori")
    def test_init_memori_handles_initialization_error(self, mock_get_memori):
        """_init_memori() returns False when Memori initialization fails."""
        from app.services.azure_openai import _init_memori

        mock_get_memori.side_effect = Exception("DB connection failed")

        result = _init_memori()

        assert result is False

    @patch("app.services.memory_service.get_memori")
    def test_init_memori_only_runs_once(self, mock_get_memori):
        """_init_memori() only initializes Memori once."""
        import app.services.azure_openai as ao
        from app.services.azure_openai import _init_memori

        mock_memori = MagicMock()
        mock_get_memori.return_value = mock_memori

        # First call initializes
        result1 = _init_memori()
        assert result1 is True

        # Second call should return cached result without re-initializing
        result2 = _init_memori()
        assert result2 is True

        # get_memori should only be called once
        mock_get_memori.assert_called_once()


class TestSetMemoryContext:
    """Tests for set_memory_context()."""

    def setup_method(self):
        """Reset global state before each test."""
        import app.services.azure_openai as ao
        ao._memori = None
        ao._memori_enabled = False

    @patch("app.services.azure_openai._init_memori")
    def test_set_memory_context_sets_attribution(self, mock_init):
        """set_memory_context() sets attribution on the Memori instance."""
        import app.services.azure_openai as ao
        from app.services.azure_openai import set_memory_context

        mock_memori = MagicMock()
        ao._memori = mock_memori
        mock_init.return_value = True

        set_memory_context(user_id="user-123", process_id="test-agent")

        mock_memori.attribution.assert_called_once_with(
            entity_id="user-123",
            process_id="test-agent"
        )

    @patch("app.services.azure_openai._init_memori")
    def test_set_memory_context_uses_default_process_id(self, mock_init):
        """set_memory_context() uses 'conversation-agent' as default."""
        import app.services.azure_openai as ao
        from app.services.azure_openai import set_memory_context

        mock_memori = MagicMock()
        ao._memori = mock_memori
        mock_init.return_value = True

        set_memory_context(user_id="user-456")

        mock_memori.attribution.assert_called_once_with(
            entity_id="user-456",
            process_id="conversation-agent"
        )

    @patch("app.services.azure_openai._init_memori")
    def test_set_memory_context_skips_when_memori_disabled(self, mock_init):
        """set_memory_context() does nothing when Memori is not available."""
        import app.services.azure_openai as ao
        from app.services.azure_openai import set_memory_context

        mock_init.return_value = False
        ao._memori = None

        # Should not raise, just skip
        set_memory_context(user_id="user-789")

        # No attribution call since Memori is disabled
        mock_init.assert_called_once()

    @patch("app.services.azure_openai._init_memori")
    def test_set_memory_context_skips_when_no_user_id(self, mock_init):
        """set_memory_context() does nothing when user_id is None."""
        import app.services.azure_openai as ao
        from app.services.azure_openai import set_memory_context

        mock_memori = MagicMock()
        ao._memori = mock_memori
        mock_init.return_value = True

        set_memory_context(user_id=None)

        # No attribution call since user_id is None
        mock_memori.attribution.assert_not_called()


class TestGetAgentResponseMemoryIntegration:
    """Tests for get_agent_response() memory context integration."""

    def setup_method(self):
        """Reset global state before each test."""
        import app.services.azure_openai as ao
        ao._memori = None
        ao._memori_enabled = False

    @pytest.mark.asyncio
    @patch("app.services.azure_openai.set_memory_context")
    @patch("app.services.azure_openai.get_azure_client")
    @patch("app.services.azure_openai.get_settings")
    async def test_get_agent_response_sets_memory_context(
        self, mock_settings, mock_get_client, mock_set_context
    ):
        """get_agent_response() sets memory context before LLM call."""
        from app.services.azure_openai import get_agent_response

        # Setup mock settings
        settings = MagicMock()
        settings.azure_openai_deployment = "gpt-4o-mini"
        mock_settings.return_value = settings

        # Setup mock client
        mock_client = AsyncMock()
        mock_response = MagicMock()
        mock_message = MagicMock()
        mock_message.content = "Hello!"
        mock_message.tool_calls = None
        mock_response.choices = [MagicMock(message=mock_message)]
        mock_client.chat.completions.create = AsyncMock(return_value=mock_response)
        mock_get_client.return_value = mock_client

        # Call with user_id
        await get_agent_response(
            system_prompt="You are a tutor",
            user_message="Hello",
            history=[],
            tool_handlers={},
            user_id="test-user-123",
        )

        # Verify memory context was set
        mock_set_context.assert_called_once_with(
            user_id="test-user-123",
            process_id="conversation-agent"
        )

    @pytest.mark.asyncio
    @patch("app.services.azure_openai.set_memory_context")
    @patch("app.services.azure_openai.get_azure_client")
    @patch("app.services.azure_openai.get_settings")
    async def test_get_agent_response_skips_memory_without_user_id(
        self, mock_settings, mock_get_client, mock_set_context
    ):
        """get_agent_response() skips memory context when user_id is None."""
        from app.services.azure_openai import get_agent_response

        # Setup mock settings
        settings = MagicMock()
        settings.azure_openai_deployment = "gpt-4o-mini"
        mock_settings.return_value = settings

        # Setup mock client
        mock_client = AsyncMock()
        mock_response = MagicMock()
        mock_message = MagicMock()
        mock_message.content = "Hello!"
        mock_message.tool_calls = None
        mock_response.choices = [MagicMock(message=mock_message)]
        mock_client.chat.completions.create = AsyncMock(return_value=mock_response)
        mock_get_client.return_value = mock_client

        # Call without user_id
        await get_agent_response(
            system_prompt="You are a tutor",
            user_message="Hello",
            history=[],
            tool_handlers={},
            user_id=None,
        )

        # Memory context should not be set
        mock_set_context.assert_not_called()
