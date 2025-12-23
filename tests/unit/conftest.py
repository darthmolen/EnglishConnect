"""Shared fixtures for unit tests."""

import pytest
from unittest.mock import MagicMock
from uuid import uuid4


@pytest.fixture
def mock_user():
    """Create a mock authenticated user."""
    user = MagicMock()
    user.id = uuid4()
    user.email = "test@example.com"
    user.display_name = "Test User"
    user.oauth_provider = "microsoft"
    user.oauth_id = "test-oauth-id"
    return user


@pytest.fixture
def mock_auth(mock_user):
    """Override get_current_user dependency with mock user.

    Use this fixture to bypass authentication in router tests.

    Example:
        async def test_endpoint(mock_auth, mock_user):
            from app.main import app
            # mock_auth automatically adds dependency override
            async with AsyncClient(...) as client:
                response = await client.get("/api/protected")
    """
    from app.main import app
    from app.middleware.auth import get_current_user

    async def override_get_current_user():
        return mock_user

    app.dependency_overrides[get_current_user] = override_get_current_user
    yield
    # Cleanup after test
    app.dependency_overrides.pop(get_current_user, None)
