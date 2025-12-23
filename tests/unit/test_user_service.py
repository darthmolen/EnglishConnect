# tests/unit/test_user_service.py
import pytest
from unittest.mock import AsyncMock, MagicMock
from app.services.user_service import UserService
from app.models.user import User


@pytest.fixture
def mock_db():
    return AsyncMock()


@pytest.fixture
def user_service(mock_db):
    return UserService(mock_db)


@pytest.mark.asyncio
async def test_get_or_create_user_creates_new_user(user_service, mock_db):
    """When user doesn't exist, create new user."""
    # Mock: no existing user found
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    mock_db.execute.return_value = mock_result

    user = await user_service.get_or_create_user(
        oauth_provider="microsoft",
        oauth_id="12345",
        email="test@example.com",
        display_name="Test User",
    )

    assert user.email == "test@example.com"
    assert user.oauth_provider == "microsoft"
    assert user.oauth_id == "12345"
    mock_db.add.assert_called_once()
    mock_db.commit.assert_called_once()


@pytest.mark.asyncio
async def test_get_or_create_user_returns_existing(user_service, mock_db):
    """When user exists, return existing user."""
    existing_user = User(
        email="existing@example.com",
        oauth_provider="microsoft",
        oauth_id="existing-id",
    )
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = existing_user
    mock_db.execute.return_value = mock_result

    user = await user_service.get_or_create_user(
        oauth_provider="microsoft",
        oauth_id="existing-id",
        email="existing@example.com",
        display_name="Existing User",
    )

    assert user == existing_user
    mock_db.add.assert_not_called()
