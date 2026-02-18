"""Unit tests for memory_service.py - Memori integration."""

import pytest
from unittest.mock import MagicMock, patch, ANY
import os


class TestGetMemori:
    """Tests for get_memori() initialization."""

    def setup_method(self):
        """Reset global state before each test."""
        # Reset the global _memori instance
        import app.services.memory_service as ms
        ms._memori = None

    @patch("app.services.memory_service.psycopg2.connect")
    @patch("app.services.memory_service.Memori")
    def test_get_memori_initializes_with_azure_openai(self, mock_memori_class, mock_connect):
        """When Azure OpenAI credentials are set, Memori uses Azure compatibility endpoint."""
        from app.services.memory_service import get_memori

        mock_memori = MagicMock()
        mock_memori_class.return_value = mock_memori

        with patch("app.services.memory_service.get_settings") as mock_settings:
            settings = MagicMock()
            settings.use_local_memori_llm = False
            settings.memori_llm_url = None
            settings.azure_openai_endpoint = "https://test.openai.azure.com/"
            settings.azure_openai_api_key = "test-key"
            settings.openai_api_key = None
            settings.database_url = "postgresql+asyncpg://user:pass@localhost/db"
            mock_settings.return_value = settings

            result = get_memori()

            # Verify Memori was initialized
            mock_memori_class.assert_called_once()

            # Verify Azure OpenAI env vars were set
            assert os.environ.get("OPENAI_API_KEY") == "test-key"
            assert "openai/v1" in os.environ.get("OPENAI_BASE_URL", "")

            # Verify storage tables were built
            mock_memori.config.storage.build.assert_called_once()

            assert result == mock_memori

    @patch("app.services.memory_service.psycopg2.connect")
    @patch("app.services.memory_service.Memori")
    def test_get_memori_initializes_with_standard_openai(self, mock_memori_class, mock_connect):
        """When only standard OpenAI key is set, Memori uses standard API."""
        from app.services.memory_service import get_memori

        mock_memori = MagicMock()
        mock_memori_class.return_value = mock_memori

        with patch("app.services.memory_service.get_settings") as mock_settings:
            settings = MagicMock()
            settings.use_local_memori_llm = False
            settings.memori_llm_url = None
            settings.azure_openai_endpoint = None
            settings.azure_openai_api_key = None
            settings.openai_api_key = "sk-standard-key"
            settings.database_url = "postgresql+asyncpg://user:pass@localhost/db"
            mock_settings.return_value = settings

            result = get_memori()

            assert os.environ.get("OPENAI_API_KEY") == "sk-standard-key"
            assert result == mock_memori

    @patch("app.services.memory_service.psycopg2.connect")
    @patch("app.services.memory_service.Memori")
    def test_get_memori_singleton_pattern(self, mock_memori_class, mock_connect):
        """get_memori() returns the same instance on repeated calls."""
        from app.services.memory_service import get_memori

        mock_memori = MagicMock()
        mock_memori_class.return_value = mock_memori

        with patch("app.services.memory_service.get_settings") as mock_settings:
            settings = MagicMock()
            settings.use_local_memori_llm = False
            settings.memori_llm_url = None
            settings.azure_openai_endpoint = "https://test.openai.azure.com/"
            settings.azure_openai_api_key = "test-key"
            settings.openai_api_key = None
            settings.database_url = "postgresql+asyncpg://user:pass@localhost/db"
            mock_settings.return_value = settings

            result1 = get_memori()
            result2 = get_memori()

            # Should only initialize once
            mock_memori_class.assert_called_once()
            assert result1 is result2


class TestRegisterClient:
    """Tests for register_client() function."""

    def setup_method(self):
        """Reset global state before each test."""
        import app.services.memory_service as ms
        ms._memori = None

    @patch("app.services.memory_service.get_memori")
    def test_register_client_calls_llm_register(self, mock_get_memori):
        """register_client() calls memori.llm.register() with the client."""
        from app.services.memory_service import register_client

        mock_memori = MagicMock()
        mock_get_memori.return_value = mock_memori

        mock_client = MagicMock()
        result = register_client(mock_client)

        mock_memori.llm.register.assert_called_once_with(mock_client)
        assert result is mock_client

    @patch("app.services.memory_service.get_memori")
    def test_register_client_returns_same_client(self, mock_get_memori):
        """register_client() returns the same client passed in."""
        from app.services.memory_service import register_client

        mock_memori = MagicMock()
        mock_get_memori.return_value = mock_memori

        mock_client = MagicMock()
        result = register_client(mock_client)

        assert result is mock_client


class TestGetSyncDbConnection:
    """Tests for get_sync_db_connection()."""

    @patch("app.services.memory_service.psycopg2.connect")
    def test_converts_async_url_to_sync(self, mock_connect):
        """Database URL is converted from asyncpg to sync psycopg2 format."""
        from app.services.memory_service import get_sync_db_connection

        with patch("app.services.memory_service.get_settings") as mock_settings:
            settings = MagicMock()
            settings.database_url = "postgresql+asyncpg://user:pass@localhost/db"
            mock_settings.return_value = settings

            get_sync_db_connection()

            # Should call psycopg2.connect with sync URL (no +asyncpg)
            mock_connect.assert_called_once_with("postgresql://user:pass@localhost/db")


class TestUserMemoryContext:
    """Tests for user_memory_context() context manager."""

    @patch("app.services.memory_service.get_memori")
    def test_sets_attribution_on_entry(self, mock_get_memori):
        """Context manager sets user attribution when entering."""
        from app.services.memory_service import user_memory_context

        mock_memori = MagicMock()
        mock_get_memori.return_value = mock_memori

        with user_memory_context(user_id="user-123", process_id="test-agent"):
            mock_memori.attribution.assert_called_once_with(
                entity_id="user-123",
                process_id="test-agent"
            )

    @patch("app.services.memory_service.get_memori")
    def test_uses_default_process_id(self, mock_get_memori):
        """Context manager uses 'conversation-agent' as default process_id."""
        from app.services.memory_service import user_memory_context

        mock_memori = MagicMock()
        mock_get_memori.return_value = mock_memori

        with user_memory_context(user_id="user-456"):
            mock_memori.attribution.assert_called_once_with(
                entity_id="user-456",
                process_id="conversation-agent"
            )

    @patch("app.services.memory_service.get_memori")
    def test_yields_memori_instance(self, mock_get_memori):
        """Context manager yields the Memori instance."""
        from app.services.memory_service import user_memory_context

        mock_memori = MagicMock()
        mock_get_memori.return_value = mock_memori

        with user_memory_context(user_id="user-789") as memori:
            assert memori is mock_memori


class TestGetUserMemories:
    """Tests for get_user_memories()."""

    @patch("app.services.memory_service.get_memori")
    def test_retrieves_memories_for_user(self, mock_get_memori):
        """get_user_memories() sets attribution and searches memories."""
        from app.services.memory_service import get_user_memories

        mock_memori = MagicMock()
        mock_memori.memory.search.return_value = [
            {"content": "memory 1"},
            {"content": "memory 2"},
        ]
        mock_get_memori.return_value = mock_memori

        result = get_user_memories(user_id="user-abc", limit=5)

        # Should set attribution
        mock_memori.attribution.assert_called_once_with(
            entity_id="user-abc",
            process_id="memory-retrieval"
        )

        # Should search with limit
        mock_memori.memory.search.assert_called_once_with(query="", limit=5)

        assert len(result) == 2
        assert result[0]["content"] == "memory 1"

    @patch("app.services.memory_service.get_memori")
    def test_returns_empty_list_on_error(self, mock_get_memori):
        """get_user_memories() returns empty list on error."""
        from app.services.memory_service import get_user_memories

        mock_memori = MagicMock()
        mock_memori.memory.search.side_effect = Exception("DB error")
        mock_get_memori.return_value = mock_memori

        result = get_user_memories(user_id="user-error")

        assert result == []

    @patch("app.services.memory_service.get_memori")
    def test_returns_empty_list_when_no_memories(self, mock_get_memori):
        """get_user_memories() returns empty list when search returns None."""
        from app.services.memory_service import get_user_memories

        mock_memori = MagicMock()
        mock_memori.memory.search.return_value = None
        mock_get_memori.return_value = mock_memori

        result = get_user_memories(user_id="user-new")

        assert result == []


class TestClearUserMemories:
    """Tests for clear_user_memories()."""

    @patch("app.services.memory_service.get_memori")
    def test_clears_memories_for_user(self, mock_get_memori):
        """clear_user_memories() sets attribution and clears memories."""
        from app.services.memory_service import clear_user_memories

        mock_memori = MagicMock()
        mock_get_memori.return_value = mock_memori

        result = clear_user_memories(user_id="user-xyz")

        # Should set attribution
        mock_memori.attribution.assert_called_once_with(
            entity_id="user-xyz",
            process_id="memory-management"
        )

        # Should clear memories
        mock_memori.memory.clear.assert_called_once()

        assert result is True

    @patch("app.services.memory_service.get_memori")
    def test_returns_false_on_error(self, mock_get_memori):
        """clear_user_memories() returns False on error."""
        from app.services.memory_service import clear_user_memories

        mock_memori = MagicMock()
        mock_memori.memory.clear.side_effect = Exception("Clear failed")
        mock_get_memori.return_value = mock_memori

        result = clear_user_memories(user_id="user-fail")

        assert result is False
