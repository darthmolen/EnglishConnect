"""Memori integration for conversation memory.

Uses Memori SDK to provide cross-session memory for the conversation agent.
Each user has their own memory context via attribution.
"""

import logging
import os
from typing import Optional
from contextlib import contextmanager

import psycopg2
from memori import Memori

from app.config import get_settings

logger = logging.getLogger(__name__)

# Global Memori instance (initialized lazily)
_memori: Optional[Memori] = None


def get_sync_db_connection():
    """Get a synchronous PostgreSQL connection for Memori.

    Memori requires a sync DB-API 2.0 connection (psycopg2).
    """
    settings = get_settings()
    # Convert async URL to sync format
    # postgresql+asyncpg://user:pass@host/db -> postgresql://user:pass@host/db
    db_url = settings.database_url.replace("+asyncpg", "")
    return psycopg2.connect(db_url)


def get_memori() -> Memori:
    """Get or create the global Memori instance."""
    global _memori

    if _memori is None:
        settings = get_settings()

        # Configure OpenAI credentials for Memori
        # Priority: 1) Azure OpenAI (via compatibility endpoint), 2) Standard OpenAI
        if settings.azure_openai_endpoint and settings.azure_openai_api_key:
            # Use Azure OpenAI's compatibility endpoint
            base_url = settings.azure_openai_endpoint.rstrip('/') + "/openai/v1/"
            os.environ["OPENAI_BASE_URL"] = base_url
            os.environ["OPENAI_API_KEY"] = settings.azure_openai_api_key
            logger.info(f"Memori using Azure OpenAI: {base_url}")
        elif settings.openai_api_key or os.environ.get("OPENAI_API_KEY"):
            # Use standard OpenAI
            openai_key = settings.openai_api_key or os.environ.get("OPENAI_API_KEY", "")
            os.environ["OPENAI_API_KEY"] = openai_key
            logger.info("Memori using standard OpenAI API")
        else:
            logger.warning(
                "No OpenAI credentials configured - Memori memory extraction disabled. "
                "Set AZURE_OPENAI_ENDPOINT/AZURE_OPENAI_API_KEY or OPENAI_API_KEY."
            )

        try:
            _memori = Memori(
                conn=get_sync_db_connection,
                conscious_ingest=True,
                auto_ingest=True,
            )

            # Build storage tables if they don't exist
            _memori.config.storage.build()

            logger.info("Memori initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize Memori: {e}")
            raise

    return _memori


@contextmanager
def user_memory_context(user_id: str, process_id: str = "conversation-agent"):
    """Context manager for user-specific memory operations.

    Usage:
        with user_memory_context(user_id="123", process_id="conversation-agent"):
            # All LLM calls here will be attributed to this user
            response = client.chat.completions.create(...)

    Args:
        user_id: Unique identifier for the user (entity_id in Memori)
        process_id: Identifier for the agent/process (defaults to conversation-agent)
    """
    memori = get_memori()

    # Set attribution for this context
    memori.attribution(entity_id=user_id, process_id=process_id)

    logger.debug(f"Memory context set for user={user_id}, process={process_id}")

    try:
        yield memori
    finally:
        # Memori handles cleanup automatically
        pass


def get_user_memories(user_id: str, limit: int = 10) -> list[dict]:
    """Retrieve recent memories for a user.

    Args:
        user_id: The user's unique identifier
        limit: Maximum number of memories to retrieve

    Returns:
        List of memory dictionaries with content and metadata
    """
    memori = get_memori()
    memori.attribution(entity_id=user_id, process_id="memory-retrieval")

    try:
        # Query memories for this user
        # Note: Exact API depends on Memori version
        memories = memori.memory.search(
            query="",  # Empty query returns recent memories
            limit=limit,
        )
        return memories if memories else []
    except Exception as e:
        logger.error(f"Failed to retrieve memories for user {user_id}: {e}")
        return []


def clear_user_memories(user_id: str) -> bool:
    """Clear all memories for a user.

    Args:
        user_id: The user's unique identifier

    Returns:
        True if successful, False otherwise
    """
    memori = get_memori()
    memori.attribution(entity_id=user_id, process_id="memory-management")

    try:
        # Clear memories for this entity
        # Note: Exact API depends on Memori version
        memori.memory.clear()
        logger.info(f"Cleared memories for user {user_id}")
        return True
    except Exception as e:
        logger.error(f"Failed to clear memories for user {user_id}: {e}")
        return False
